"""
Importa las evaluaciones de DocSpace desde el CSV histórico.

Fuente:
    Bases de datos 1.0/Diagnostico_DOCSPACES - r_DocSpaces.csv

Uso:
    python manage.py importar_docspaces
    python manage.py importar_docspaces --reset   # borra docspaces antes de importar
"""

import csv
from pathlib import Path
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from diagnostico.models import Proyecto, EvaluacionDocSpace

BASE_DATOS = Path(__file__).parent.parent.parent.parent.parent / "Bases de datos 1.0"
CSV_FILE = BASE_DATOS / "Diagnostico_DOCSPACES - r_DocSpaces.csv"

FECHA_HISTORICO = timezone.make_aware(datetime(2025, 12, 31))

# Mapa: texto del CSV → clave del modelo
# Correcciones de nombre: CSV → DB (cuando no coinciden exactamente)
NOMBRE_FIXES = {
    "Rayones: Archivo experimental de tatuaje":       "Rayones: Archivo experimental del tatuaje local",
    "Raíces: una herramienta para la tradición":      "Raíces: Una herramienta para la tradición",
}

SECCION_MAP = {
    "Nombre de proyecto":                                        "nombre_proyecto",
    "Descripción de proyecto":                                   "descripcion_proyecto",
    "Trazas del proceso de prototipado":                        "trazas_proceso",
    "El prototipo y/o partes de él":                            "prototipo_partes",
    "Fotografías del prototipo a lo largo del proceso y en su estado actual": "fotos_prototipo",
    "Fotografías de las personas colaboradoras en el proyecto o comunidad":   "fotos_personas",
    "QR o enlace a la wiki":                                     "qr_enlace_wiki",
}


class Command(BaseCommand):
    help = "Importa evaluaciones DocSpace desde el CSV histórico"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Borra todas las EvaluacionDocSpace antes de importar",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            deleted, _ = EvaluacionDocSpace.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"  {deleted} evaluaciones borradas."))

        creadas, actualizadas, omitidas = 0, 0, 0

        with open(CSV_FILE, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                nombre_proyecto = row["Proyecto"].strip().replace("\n", "").replace("\r", "")
                nombre_proyecto = NOMBRE_FIXES.get(nombre_proyecto, nombre_proyecto)
                seccion_label   = row["Sección de docSPACE"].strip()
                status_raw      = row["Status"].strip()
                notas           = row.get("notas de mejora", "").strip()

                # Mapear sección
                seccion_key = SECCION_MAP.get(seccion_label)
                if not seccion_key:
                    self.stdout.write(
                        self.style.WARNING(f"  ⚠ Sección desconocida: '{seccion_label}' — omitida")
                    )
                    omitidas += 1
                    continue

                # Buscar proyecto
                proyecto = Proyecto.objects.filter(nombre=nombre_proyecto).first()
                if not proyecto:
                    self.stdout.write(
                        self.style.WARNING(f"  ⚠ Proyecto no encontrado: '{nombre_proyecto}' — omitido")
                    )
                    omitidas += 1
                    continue

                # Normalizar status
                status = status_raw if status_raw in ("Completa", "Incompleta") else "Incompleta"

                _, created = EvaluacionDocSpace.objects.update_or_create(
                    proyecto=proyecto,
                    seccion=seccion_key,
                    defaults={
                        "status": status,
                        "notas_mejora": notas,
                        "fecha_evaluacion": FECHA_HISTORICO,
                        "evaluado_por": "Importación histórica",
                    },
                )
                if created:
                    creadas += 1
                else:
                    actualizadas += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ DocSpaces importados: {creadas} nuevos, {actualizadas} actualizados, {omitidas} omitidos.\n"
                f"  Total EvaluacionDocSpace: {EvaluacionDocSpace.objects.count()}"
            )
        )
