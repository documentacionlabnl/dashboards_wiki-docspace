from django.contrib import admin
from django.utils import timezone
from django.db.models import Count, Q

from .models import (
    Actividad, Proyecto, Prototipo,
    EvaluacionWiki, EvaluacionDocSpace, ActualizacionDashboard,
)


# ── Actividad ───────────────────────────────────────────────────────────────────

@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    list_display = ["nombre", "total_proyectos"]

    def total_proyectos(self, obj):
        return obj.proyectos.count()
    total_proyectos.short_description = "Proyectos"


# ── Proyecto ────────────────────────────────────────────────────────────────────

@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "actividad", "status", "año_inicio", "total_prototipos"]
    list_filter = ["actividad", "status", "año_inicio"]
    search_fields = ["nombre"]

    def total_prototipos(self, obj):
        return obj.prototipos.count()
    total_prototipos.short_description = "Prototipos"


# ── EvaluacionWiki inline (para ver desde Prototipo) ───────────────────────────

class EvaluacionWikiInline(admin.TabularInline):
    model = EvaluacionWiki
    fields = [
        "seccion", "subseccion",
        "status_scraper", "contenido_chars",
        "verificado", "status_override", "notas_mejora",
    ]
    readonly_fields = ["seccion", "subseccion", "status_scraper", "contenido_chars"]
    extra = 0

    def get_queryset(self, request):
        return super().get_queryset(request).order_by("seccion", "subseccion")


# ── Prototipo ───────────────────────────────────────────────────────────────────

@admin.register(Prototipo)
class PrototipoAdmin(admin.ModelAdmin):
    list_display = [
        "nombre", "proyecto", "avance_verificado_pct",
        "pendientes_verificacion", "url_wiki",
    ]
    list_filter = ["proyecto__actividad", "proyecto__status"]
    search_fields = ["nombre", "proyecto__nombre"]
    inlines = [EvaluacionWikiInline]

    def avance_verificado_pct(self, obj):
        avance = obj.avance_verificado
        return f"{avance}%" if avance is not None else "—"
    avance_verificado_pct.short_description = "Avance verificado"

    def pendientes_verificacion(self, obj):
        n = obj.evaluaciones.filter(verificado=False).count()
        return f"⚠️ {n}" if n > 0 else "✓"
    pendientes_verificacion.short_description = "Pendientes"


# ── EvaluacionWiki (vista directa con filtros de verificación) ──────────────────

@admin.action(description="Marcar seleccionadas como verificadas")
def verificar_evaluaciones(modeladmin, request, queryset):
    queryset.update(verificado=True, fecha_verificacion=timezone.now())
    # Recalcular status_final_cache
    for ev in queryset:
        ev.save()


@admin.register(EvaluacionWiki)
class EvaluacionWikiAdmin(admin.ModelAdmin):
    list_display = [
        "prototipo", "seccion", "subseccion",
        "status_scraper", "status_override", "status_final_cache",
        "verificado", "notas_mejora_corta",
    ]
    list_filter = [
        "verificado", "status_scraper", "seccion",
        "prototipo__proyecto__actividad",
    ]
    search_fields = ["prototipo__nombre", "prototipo__proyecto__nombre", "notas_mejora"]
    readonly_fields = ["status_scraper", "contenido_chars", "fecha_scraper", "status_final_cache"]
    fields = [
        "prototipo", "seccion", "subseccion",
        "status_scraper", "contenido_chars", "fecha_scraper",
        "verificado", "status_override", "notas_mejora", "fecha_verificacion",
        "status_final_cache",
    ]
    actions = [verificar_evaluaciones]

    def notas_mejora_corta(self, obj):
        return obj.notas_mejora[:60] + "…" if len(obj.notas_mejora) > 60 else obj.notas_mejora
    notas_mejora_corta.short_description = "Notas"

    def get_queryset(self, request):
        # Por defecto mostrar primero las no verificadas
        return super().get_queryset(request).select_related(
            "prototipo", "prototipo__proyecto"
        ).order_by("verificado", "prototipo__nombre", "seccion", "subseccion")


# ── EvaluacionDocSpace ──────────────────────────────────────────────────────────

@admin.register(EvaluacionDocSpace)
class EvaluacionDocSpaceAdmin(admin.ModelAdmin):
    list_display = ["proyecto", "seccion", "status", "evaluado_por", "fecha_evaluacion"]
    list_filter = ["status", "seccion", "proyecto__actividad"]
    search_fields = ["proyecto__nombre", "notas_mejora"]


# ── ActualizacionDashboard ──────────────────────────────────────────────────────

@admin.register(ActualizacionDashboard)
class ActualizacionDashboardAdmin(admin.ModelAdmin):
    list_display = [
        "fecha", "prototipos_evaluados",
        "cambios_detectados", "cambios_verificados", "notas",
    ]
    readonly_fields = ["fecha"]
