"""
Orden canónico de secciones y subsecciones de la wiki.

Fuente de verdad compartida entre `views.py` (render del dashboard) y
`admin.py` (orden del inline de EvaluacionWiki en el Prototipo).
"""

from django.db.models import Case, When, IntegerField


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
    """Clave para ordenar objetos EvaluacionWiki en Python (list comprehensions)."""
    sec_idx = SECCION_ORDER.index(ev.seccion) if ev.seccion in SECCION_ORDER else 99
    sub_list = SUBSECCION_ORDER.get(ev.seccion, [])
    sub_idx = sub_list.index(ev.subseccion) if ev.subseccion in sub_list else 99
    return (sec_idx, sub_idx)


def seccion_case():
    """Expresión SQL CASE WHEN para ordenar por sección según SECCION_ORDER."""
    return Case(
        *[When(seccion=s, then=i) for i, s in enumerate(SECCION_ORDER)],
        default=99,
        output_field=IntegerField(),
    )


def subseccion_case():
    """Expresión SQL CASE WHEN para ordenar por subsección dentro de cada sección."""
    whens = []
    for seccion, subs in SUBSECCION_ORDER.items():
        for i, sub in enumerate(subs):
            whens.append(When(seccion=seccion, subseccion=sub, then=i))
    return Case(*whens, default=99, output_field=IntegerField())
