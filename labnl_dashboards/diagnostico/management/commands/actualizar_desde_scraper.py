"""
Carga los resultados del scraper a la base de datos, detectando cambios
vs el último estado verificado.

Solo crea registros pendientes de verificación cuando el status cambió.

Uso:
    python manage.py actualizar_desde_scraper
    python manage.py actualizar_desde_scraper --csv /ruta/al/evaluacion_wikis.csv
"""

import csv
from pathlib import Path
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from diagnostico.models import Prototipo, EvaluacionWiki, ActualizacionDashboard

RESULTS_DIR = Path(__file__).parent.parent.parent.parent.parent / "results"


class Command(BaseCommand):
    help = "Actualiza evaluaciones desde el CSV del scraper, detectando cambios"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            default=str(RESULTS_DIR / "evaluacion_wikis.csv"),
            help="Ruta al CSV generado por el scraper",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv"])
        if not csv_path.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró el CSV: {csv_path}"))
            return

        self.stdout.write(f"Procesando {csv_path.name}...")

        actualizados = 0
        sin_cambio = 0
        sin_prototipo = 0
        nuevos = 0
        fecha_scraper = timezone.now()

        with open(csv_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                nombre_proto = row["Prototipo"].strip()
                seccion = row["Sección"].strip()
                subseccion = row["Subsección"].strip()
                status_scraper = row["Status"].strip()
                chars = int(row.get("Chars", 0) or 0)
                url_wiki = row.get("url_wiki_prototipo", "").strip()

                prototipo = Prototipo.objects.filter(nombre=nombre_proto).first()
                if not prototipo:
                    sin_prototipo += 1
                    continue

                # Actualizar URL si el scraper la encontró
                if url_wiki and not prototipo.url_wiki:
                    prototipo.url_wiki = url_wiki
                    prototipo.save(update_fields=["url_wiki"])

                eval_existente = EvaluacionWiki.objects.filter(
                    prototipo=prototipo,
                    seccion=seccion,
                    subseccion=subseccion,
                ).first()

                if eval_existente is None:
                    # Nuevo criterio que no estaba en el histórico
                    EvaluacionWiki.objects.create(
                        prototipo=prototipo,
                        seccion=seccion,
                        subseccion=subseccion,
                        status_scraper=status_scraper,
                        contenido_chars=chars,
                        fecha_scraper=fecha_scraper,
                        verificado=False,
                    )
                    nuevos += 1

                elif eval_existente.status_final_cache != status_scraper:
                    # El status cambió vs el último estado conocido → pendiente de verificación
                    eval_existente.status_scraper = status_scraper
                    eval_existente.contenido_chars = chars
                    eval_existente.fecha_scraper = fecha_scraper
                    eval_existente.verificado = False
                    eval_existente.status_override = ""  # resetear override anterior
                    eval_existente.fecha_verificacion = None
                    eval_existente.save()
                    actualizados += 1

                else:
                    # Sin cambio — solo actualizar fecha y chars
                    eval_existente.status_scraper = status_scraper
                    eval_existente.contenido_chars = chars
                    eval_existente.fecha_scraper = fecha_scraper
                    eval_existente.save(update_fields=[
                        "status_scraper", "contenido_chars", "fecha_scraper"
                    ])
                    sin_cambio += 1

        cambios_total = actualizados + nuevos
        ActualizacionDashboard.objects.create(
            fecha=fecha_scraper,
            prototipos_evaluados=Prototipo.objects.count(),
            cambios_detectados=cambios_total,
            cambios_verificados=0,
            notas=f"Scraper automático — {cambios_total} cambios detectados",
        )

        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Procesado:\n"
            f"  Sin cambio:            {sin_cambio}\n"
            f"  Cambios detectados:    {actualizados}\n"
            f"  Criterios nuevos:      {nuevos}\n"
            f"  Sin prototipo en BD:   {sin_prototipo}\n"
            f"\n  Pendientes de verificación en el admin: {cambios_total}"
        ))
