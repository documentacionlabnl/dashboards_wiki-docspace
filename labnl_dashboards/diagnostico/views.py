from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Max

from .models import (
    Actividad, Proyecto, Prototipo,
    EvaluacionWiki, EvaluacionDocSpace, ActualizacionDashboard,
)

# ── Orden canónico de la wiki ────────────────────────────────────────────────
SECCION_ORDER = ["Prototipo", "Aprendizajes", "Desarrollo"]

SUBSECCION_ORDER = {
    "Prototipo": [
        "Descripción del prototipo", "Antecedentes", "Equipo", "Imagen de prototipo",
    ],
    "Aprendizajes": [
        "Hito 1", "Hito 2", "Hito 3", "Hito 4",
    ],
    "Desarrollo": [
        "Validación", "Hoja de ruta", "Partes del Prototipo", "Ingredientes",
        "Pasos", "Consejos", "Referencias", "Archivos para replicar",
        "Alianzas", "Sostenibilidad", "Medios", "Vinculaciones",
    ],
}

SUBSECCIONES_EXCLUIDAS = {"Continuidad"}


def _sort_key(ev):
    sec_idx = SECCION_ORDER.index(ev.seccion) if ev.seccion in SECCION_ORDER else 99
    sub_list = SUBSECCION_ORDER.get(ev.seccion, [])
    sub_idx = sub_list.index(ev.subseccion) if ev.subseccion in sub_list else 99
    return (sec_idx, sub_idx)


def _evals_wiki(prototipo):
    """Evaluaciones de un prototipo excluidas las subsecciones eliminadas, en orden canónico."""
    qs = prototipo.evaluaciones.exclude(subseccion__in=SUBSECCIONES_EXCLUIDAS)
    return sorted(qs, key=_sort_key)


def _avance_proto(prototipo):
    """% completo de un prototipo basado en status_final_cache (excluye Continuidad)."""
    evals = prototipo.evaluaciones.exclude(subseccion__in=SUBSECCIONES_EXCLUIDAS)
    total = evals.count()
    if not total:
        return None
    completas = evals.filter(status_final_cache="Completa").count()
    return completas / total * 100


def _contexto_base():
    """Última actualización = edit manual más reciente (wiki o DocSpace) desde el admin."""
    wiki_max = EvaluacionWiki.objects.aggregate(m=Max("updated_at"))["m"]
    ds_max = EvaluacionDocSpace.objects.aggregate(m=Max("updated_at"))["m"]
    candidatos = [d for d in (wiki_max, ds_max) if d]
    return {"ultima_actualizacion": max(candidatos) if candidatos else None}


def home(request):
    ctx = _contexto_base()

    total_proyectos = Proyecto.objects.count()
    total_prototipos = Prototipo.objects.count()

    avances = [a for p in Prototipo.objects.prefetch_related("evaluaciones")
               if (a := _avance_proto(p)) is not None]
    avance_wikis = round(sum(avances) / len(avances), 1) if avances else 0

    total_ds = EvaluacionDocSpace.objects.count()
    completas_ds = EvaluacionDocSpace.objects.filter(status="Completa").count()
    avance_docspaces = round(completas_ds / total_ds * 100, 1) if total_ds else 0

    ctx.update({
        "total_proyectos": total_proyectos,
        "total_prototipos": total_prototipos,
        "avance_wikis": avance_wikis,
        "avance_docspaces": avance_docspaces,
    })
    return render(request, "diagnostico/home.html", ctx)


def wikis(request):
    ctx = _contexto_base()

    actividad_filtro = request.GET.get("actividad", "")
    status_filtro    = request.GET.get("status", "")
    año_filtro       = request.GET.get("año", "")
    busqueda         = request.GET.get("q", "").strip()

    proyectos = Proyecto.objects.prefetch_related("prototipos__evaluaciones")

    if actividad_filtro:
        proyectos = proyectos.filter(actividad__nombre=actividad_filtro)
    if status_filtro:
        proyectos = proyectos.filter(status=status_filtro)
    if año_filtro:
        proyectos = proyectos.filter(año_inicio=año_filtro)
    if busqueda:
        proyectos = proyectos.filter(
            Q(nombre__icontains=busqueda) |
            Q(prototipos__nombre__icontains=busqueda)
        ).distinct()

    datos_proyectos = []
    for proyecto in proyectos:
        avances_proto = [a for p in proyecto.prototipos.all()
                         if (a := _avance_proto(p)) is not None]
        avance = round(sum(avances_proto) / len(avances_proto), 1) if avances_proto else 0
        datos_proyectos.append({
            "proyecto": proyecto,
            "avance": avance,
            "num_prototipos": proyecto.prototipos.count(),
        })

    datos_proyectos.sort(key=lambda x: x["avance"], reverse=True)

    # Estadísticas globales para gráfica resumen (todos los proyectos filtrados)
    proyecto_ids = [d["proyecto"].id for d in datos_proyectos]
    evals_filtradas = EvaluacionWiki.objects.filter(
        prototipo__proyecto_id__in=proyecto_ids
    ).exclude(subseccion__in=SUBSECCIONES_EXCLUIDAS)
    total_evals = evals_filtradas.count()
    completas_total = evals_filtradas.filter(status_final_cache="Completa").count()
    incompletas_total = evals_filtradas.filter(status_final_cache="Incompleta").count()
    vacias_total = evals_filtradas.filter(status_final_cache="Vacía").count()

    ctx.update({
        "datos_proyectos": datos_proyectos,
        "actividades": Actividad.objects.all(),
        "años": (Proyecto.objects.exclude(año_inicio=None)
                 .values_list("año_inicio", flat=True).distinct().order_by("-año_inicio")),
        "filtros": {
            "actividad": actividad_filtro,
            "status": status_filtro,
            "año": año_filtro,
            "q": busqueda,
        },
        "stats_resumen": {
            "total": total_evals,
            "completas": completas_total,
            "incompletas": incompletas_total,
            "vacias": vacias_total,
        },
    })
    return render(request, "diagnostico/wikis.html", ctx)


def detalle_proyecto(request, proyecto_id):
    ctx = _contexto_base()
    proyecto = get_object_or_404(Proyecto, pk=proyecto_id)

    prototipos_data = []
    for proto in proyecto.prototipos.all():
        # _evals_wiki devuelve lista (no QS) ordenada y sin Continuidad
        evals = _evals_wiki(proto)
        total = len(evals)
        completas = sum(1 for e in evals if e.status_final_cache == "Completa")
        avance = round(completas / total * 100, 1) if total else 0

        # Construir secciones en orden canónico (dict preserva inserción en Python 3.7+)
        secciones = {}
        for seccion in SECCION_ORDER:
            evs_seccion = [e for e in evals if e.seccion == seccion]
            if evs_seccion:
                secciones[seccion] = evs_seccion

        # Stats por sección para la gráfica (ya en orden canónico)
        seccion_stats = []
        for seccion, evs in secciones.items():
            n_completas = sum(1 for e in evs if e.status_final_cache == "Completa")
            n_incompletas = sum(1 for e in evs if e.status_final_cache == "Incompleta")
            n_vacias = sum(1 for e in evs if e.status_final_cache == "Vacía")
            seccion_stats.append({
                "seccion": seccion,
                "completas": n_completas,
                "incompletas": n_incompletas,
                "vacias": n_vacias,
                "total": len(evs),
            })

        prototipos_data.append({
            "prototipo": proto,
            "avance": avance,
            "completas": completas,
            "total": total,
            "secciones": secciones,
            "seccion_stats": seccion_stats,
        })

    avances_all = [item["avance"] for item in prototipos_data]
    avance_proyecto = round(sum(avances_all) / len(avances_all), 1) if avances_all else 0

    ctx.update({
        "proyecto": proyecto,
        "prototipos_data": prototipos_data,
        "avance_proyecto": avance_proyecto,
    })
    return render(request, "diagnostico/detalle_proyecto.html", ctx)


def docspaces(request):
    ctx = _contexto_base()

    actividad_filtro = request.GET.get("actividad", "")
    status_filtro    = request.GET.get("status", "")
    año_filtro       = request.GET.get("año", "")
    busqueda         = request.GET.get("q", "").strip()

    proyectos = Proyecto.objects.prefetch_related("docspaces")

    if actividad_filtro:
        proyectos = proyectos.filter(actividad__nombre=actividad_filtro)
    if status_filtro:
        proyectos = proyectos.filter(status=status_filtro)
    if año_filtro:
        proyectos = proyectos.filter(año_inicio=año_filtro)
    if busqueda:
        proyectos = proyectos.filter(nombre__icontains=busqueda).distinct()

    datos = []
    for proyecto in proyectos:
        evals = proyecto.docspaces.all()
        total = evals.count()
        completas = evals.filter(status="Completa").count()
        if total:
            datos.append({
                "proyecto": proyecto,
                "avance": round(completas / total * 100, 1),
                "completas": completas,
                "total": total,
            })

    datos.sort(key=lambda x: x["avance"], reverse=True)
    ctx.update({
        "datos_proyectos": datos,
        "actividades": Actividad.objects.all(),
        "años": (Proyecto.objects.exclude(año_inicio=None)
                 .values_list("año_inicio", flat=True).distinct().order_by("-año_inicio")),
        "filtros": {
            "actividad": actividad_filtro,
            "status": status_filtro,
            "año": año_filtro,
            "q": busqueda,
        },
    })
    return render(request, "diagnostico/docspaces.html", ctx)


def vista_global(request):
    ctx = _contexto_base()

    actividad_filtro = request.GET.get("actividad", "")
    año_filtro       = request.GET.get("año", "")
    status_filtro    = request.GET.get("status", "")

    proyectos_qs = Proyecto.objects.all()
    if actividad_filtro:
        proyectos_qs = proyectos_qs.filter(actividad__nombre=actividad_filtro)
    if año_filtro:
        proyectos_qs = proyectos_qs.filter(año_inicio=año_filtro)
    if status_filtro:
        proyectos_qs = proyectos_qs.filter(status=status_filtro)

    proyecto_ids = list(proyectos_qs.values_list("id", flat=True))

    total_proyectos = proyectos_qs.count()
    total_prototipos = Prototipo.objects.filter(proyecto_id__in=proyecto_ids).count()

    avances_wiki = [a for p in Prototipo.objects.filter(proyecto_id__in=proyecto_ids)
                    .prefetch_related("evaluaciones")
                    if (a := _avance_proto(p)) is not None]
    avance_wikis = round(sum(avances_wiki) / len(avances_wiki), 1) if avances_wiki else 0

    total_ds = EvaluacionDocSpace.objects.filter(proyecto_id__in=proyecto_ids).count()
    completas_ds = EvaluacionDocSpace.objects.filter(proyecto_id__in=proyecto_ids, status="Completa").count()
    avance_docspaces = round(completas_ds / total_ds * 100, 1) if total_ds else 0

    # Avance por actividad (filtrado)
    actividades_data = []
    for actividad in Actividad.objects.all():
        proyectos = actividad.proyectos.filter(id__in=proyecto_ids).prefetch_related("prototipos__evaluaciones")
        avances = [a for proyecto in proyectos
                   for proto in proyecto.prototipos.all()
                   if (a := _avance_proto(proto)) is not None]
        if avances:
            actividades_data.append({
                "actividad": actividad.nombre,
                "avance": round(sum(avances) / len(avances), 1),
                "num_proyectos": proyectos.count(),
            })

    # Avance por sección de wiki (para la gráfica)
    secciones_data = []
    for seccion in SECCION_ORDER:
        evals = EvaluacionWiki.objects.filter(
            prototipo__proyecto_id__in=proyecto_ids,
            seccion=seccion,
        )
        total = evals.count()
        completas = evals.filter(status_final_cache="Completa").count()
        if total:
            secciones_data.append({
                "seccion": seccion,
                "avance": round(completas / total * 100, 1),
            })

    # Avance por subsección de wiki (para la tabla de detalle)
    subsecciones_data = []
    for seccion, subsecciones in SUBSECCION_ORDER.items():
        for subseccion in subsecciones:
            evals = EvaluacionWiki.objects.filter(
                prototipo__proyecto_id__in=proyecto_ids,
                seccion=seccion,
                subseccion=subseccion,
            )
            total = evals.count()
            completas = evals.filter(status_final_cache="Completa").count()
            if total:
                subsecciones_data.append({
                    "seccion": seccion,
                    "subseccion": subseccion,
                    "avance": round(completas / total * 100, 1),
                })

    evals_todas = EvaluacionWiki.objects.filter(
        prototipo__proyecto_id__in=proyecto_ids
    ).exclude(subseccion__in=SUBSECCIONES_EXCLUIDAS)
    total_evals = evals_todas.count()
    stats_wikis = {
        "total": total_evals,
        "completas": evals_todas.filter(status_final_cache="Completa").count(),
        "incompletas": evals_todas.filter(status_final_cache="Incompleta").count(),
        "vacias": evals_todas.filter(status_final_cache="Vacía").count(),
    }

    ctx.update({
        "total_proyectos": total_proyectos,
        "total_prototipos": total_prototipos,
        "avance_wikis": avance_wikis,
        "avance_docspaces": avance_docspaces,
        "actividades_data": actividades_data,
        "secciones_data": secciones_data,
        "subsecciones_data": subsecciones_data,
        "stats_wikis": stats_wikis,
        "actividades": Actividad.objects.all(),
        "años": (Proyecto.objects.exclude(año_inicio=None)
                 .values_list("año_inicio", flat=True).distinct().order_by("-año_inicio")),
        "filtros": {
            "actividad": actividad_filtro,
            "año": año_filtro,
            "status": status_filtro,
        },
    })
    return render(request, "diagnostico/global.html", ctx)
