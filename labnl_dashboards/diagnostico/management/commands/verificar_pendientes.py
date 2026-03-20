"""
Marca como verificadas todas las evaluaciones que el scraper generó
y que aún no han sido revisadas manualmente.

Esto es equivalente a "aceptar" los resultados del scraper tal como están.
Útil para poner el dashboard al día sin revisar una por una en el admin.

Uso:
    python manage.py verificar_pendientes
    python manage.py verificar_pendientes --dry-run   # solo muestra cuántas hay
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from diagnostico.models import EvaluacionWiki, ActualizacionDashboard


class Command(BaseCommand):
    help = "Verifica en lote todas las evaluaciones pendientes del scraper"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo muestra cuántas evaluaciones se verificarían, sin modificar la BD",
        )

    def handle(self, *args, **options):
        pendientes = EvaluacionWiki.objects.filter(verificado=False)
        total = pendientes.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS("✓ No hay evaluaciones pendientes de verificar."))
            return

        self.stdout.write(f"Evaluaciones pendientes: {total}")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("  [dry-run] No se realizaron cambios."))
            return

        ahora = timezone.now()
        actualizadas = pendientes.update(
            verificado=True,
            fecha_verificacion=ahora,
        )

        # Recalcular status_final_cache para cada registro actualizado
        # (update() no llama save(), necesitamos iterar)
        for ev in EvaluacionWiki.objects.filter(
            verificado=True, fecha_verificacion=ahora
        ):
            ev.save()  # dispara el cálculo de status_final_cache

        # Registrar la actualización
        ActualizacionDashboard.objects.create(
            fecha=ahora,
            prototipos_evaluados=EvaluacionWiki.objects.values("prototipo").distinct().count(),
            cambios_detectados=actualizadas,
            cambios_verificados=actualizadas,
            notas=f"Verificación en lote: {actualizadas} evaluaciones aceptadas",
        )

        self.stdout.write(
            self.style.SUCCESS(f"✓ {actualizadas} evaluaciones verificadas.")
        )
