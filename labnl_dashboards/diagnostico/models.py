from django.db import models
from django.utils import timezone


class Actividad(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name_plural = "Actividades"
        ordering = ["nombre"]


class Proyecto(models.Model):
    nombre = models.CharField(max_length=300, unique=True)
    actividad = models.ForeignKey(Actividad, on_delete=models.PROTECT, related_name="proyectos")
    status = models.CharField(max_length=50)  # Activo / Finalizado
    año_inicio = models.PositiveSmallIntegerField(null=True, blank=True)
    año_fin = models.PositiveSmallIntegerField(null=True, blank=True)
    enlace_wiki_proyecto = models.URLField(max_length=500, blank=True)  # landing page de la comunidad

    def __str__(self):
        return self.nombre

    class Meta:
        ordering = ["nombre"]


class Prototipo(models.Model):
    nombre = models.CharField(max_length=300, unique=True)
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="prototipos")
    url_wiki = models.URLField(max_length=500, blank=True)  # página wiki del prototipo

    def __str__(self):
        return self.nombre

    @property
    def avance_verificado(self):
        """% de avance basado solo en evaluaciones verificadas."""
        evals = self.evaluaciones.filter(verificado=True)
        if not evals.exists():
            return None
        completas = evals.filter(status_final_cache="Completa").count()
        return round(completas / evals.count() * 100, 2)

    class Meta:
        ordering = ["nombre"]


class EvaluacionWiki(models.Model):
    STATUS_CHOICES = [
        ("Completa", "Completa"),
        ("Vacía", "Vacía"),
        ("Incompleta", "Incompleta"),
    ]

    prototipo = models.ForeignKey(Prototipo, on_delete=models.CASCADE, related_name="evaluaciones")
    seccion = models.CharField(max_length=100)       # Prototipo / Aprendizajes / Desarrollo
    subseccion = models.CharField(max_length=100)    # Antecedentes, Hito 1, Validación, etc.

    # Lo que detectó el scraper
    status_scraper = models.CharField(max_length=20, choices=STATUS_CHOICES)
    contenido_chars = models.PositiveIntegerField(default=0)
    fecha_scraper = models.DateTimeField()

    # Verificación humana
    verificado = models.BooleanField(default=False)
    status_override = models.CharField(
        max_length=20, choices=STATUS_CHOICES, blank=True,
        help_text="Dejar vacío para aceptar lo que detectó el scraper"
    )
    notas_mejora = models.TextField(blank=True)
    fecha_verificacion = models.DateTimeField(null=True, blank=True)

    # Campo calculado para queries eficientes en el dashboard
    # Se actualiza al guardar: es status_override si existe, si no status_scraper
    status_final_cache = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True)

    # Fecha del último edit manual desde el admin (no se toca en imports/scraper)
    updated_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.status_final_cache = self.status_override if self.status_override else self.status_scraper
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.prototipo} | {self.seccion} > {self.subseccion}"

    class Meta:
        unique_together = ("prototipo", "seccion", "subseccion")
        ordering = ["seccion", "subseccion"]
        verbose_name = "Evaluación Wiki"
        verbose_name_plural = "Evaluaciones Wiki"


class ActualizacionDashboard(models.Model):
    """
    Registro de cada vez que se verifican cambios.
    La fecha más reciente es la que aparece en el dashboard público
    como 'Última actualización'.
    """
    fecha = models.DateTimeField(default=timezone.now)
    prototipos_evaluados = models.PositiveIntegerField(default=0)
    cambios_detectados = models.PositiveIntegerField(default=0)
    cambios_verificados = models.PositiveIntegerField(default=0)
    notas = models.TextField(blank=True)

    def __str__(self):
        return f"Actualización {self.fecha.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Actualización de Dashboard"
        verbose_name_plural = "Actualizaciones de Dashboard"


class EvaluacionDocSpace(models.Model):
    STATUS_CHOICES = [
        ("Completa", "Completa"),
        ("Incompleta", "Incompleta"),
    ]

    SECCIONES = [
        ("nombre_proyecto", "Nombre de proyecto"),
        ("descripcion_proyecto", "Descripción de proyecto"),
        ("trazas_proceso", "Trazas del proceso de prototipado"),
        ("prototipo_partes", "El prototipo y/o partes de él"),
        ("fotos_prototipo", "Fotografías del prototipo"),
        ("fotos_personas", "Fotografías de las personas colaboradoras"),
        ("qr_enlace_wiki", "QR o enlace a la wiki"),
    ]

    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="docspaces")
    seccion = models.CharField(max_length=50, choices=SECCIONES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    notas_mejora = models.TextField(blank=True)
    fecha_evaluacion = models.DateTimeField(default=timezone.now)
    evaluado_por = models.CharField(max_length=100, blank=True)

    # Fecha del último edit manual desde el admin (no se toca en imports)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.proyecto} | {self.get_seccion_display()}"

    class Meta:
        unique_together = ("proyecto", "seccion")
        ordering = ["seccion"]
        verbose_name = "Evaluación DocSpace"
        verbose_name_plural = "Evaluaciones DocSpace"
