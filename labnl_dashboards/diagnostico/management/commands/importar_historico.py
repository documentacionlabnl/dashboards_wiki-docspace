"""
Importa los datos históricos de los CSV de la versión 1.0 a la base de datos Django.

Fuentes:
    c_actividades.csv  → Actividad
    c_proyectos.csv    → Proyecto (con actividad, status, año, enlace_wiki)
    c_prototipos.csv   → Prototipo (con relación a proyecto)
    r_wikis.csv        → EvaluacionWiki (estado base verificado)

Uso:
    python manage.py importar_historico
    python manage.py importar_historico --reset   # borra todo antes de importar
"""

import csv
from pathlib import Path
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from diagnostico.models import (
    Actividad, Proyecto, Prototipo,
    EvaluacionWiki, ActualizacionDashboard,
)

BASE_DATOS = Path(__file__).parent.parent.parent.parent.parent / "Bases de datos 1.0"

# Fecha de los datos históricos (los CSVs son de antes del sistema nuevo)
FECHA_HISTORICO = timezone.make_aware(datetime(2025, 12, 31))

# Subsecciones a excluir (Receta está en los CSVs pero no en los 21 criterios)
SUBSECCIONES_EXCLUIDAS = {"receta", "receta "}


class Command(BaseCommand):
    help = "Importa datos históricos de los CSV 1.0 a la base de datos Django"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Borra todos los datos existentes antes de importar",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write("Borrando datos existentes...")
            EvaluacionWiki.objects.all().delete()
            Prototipo.objects.all().delete()
            Proyecto.objects.all().delete()
            Actividad.objects.all().delete()
            self.stdout.write(self.style.WARNING("  Datos borrados."))

        self._importar_actividades()
        self._importar_proyectos()
        self._importar_prototipos()
        self._importar_evaluaciones()
        self._registrar_actualizacion()

        self.stdout.write(self.style.SUCCESS("\n✓ Importación completada."))

    # ── Actividades ─────────────────────────────────────────────────────────────

    def _importar_actividades(self):
        self.stdout.write("\n[1/4] Importando actividades...")
        creadas = 0
        with open(BASE_DATOS / "Diagnóstico_Wikis - c_actividades.csv", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                nombre = row["tipo_actividades"].strip()
                if nombre:
                    _, created = Actividad.objects.get_or_create(nombre=nombre)
                    if created:
                        creadas += 1
        self.stdout.write(f"  {creadas} actividades creadas. Total: {Actividad.objects.count()}")

    # ── Proyectos ────────────────────────────────────────────────────────────────

    def _importar_proyectos(self):
        self.stdout.write("\n[2/4] Importando proyectos...")
        creados, omitidos = 0, 0
        with open(BASE_DATOS / "Diagnóstico_Wikis - c_proyectos.csv", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                nombre = row["proyectos"].strip()
                if not nombre:
                    continue

                tipo = row["tipo_actividades"].strip()
                actividad = Actividad.objects.filter(nombre=tipo).first()
                if not actividad:
                    self.stdout.write(
                        self.style.WARNING(f"  ⚠ Actividad '{tipo}' no encontrada para '{nombre}'")
                    )
                    omitidos += 1
                    continue

                año_inicio = self._parse_año(row.get("año de inicio", ""))
                año_fin = self._parse_año(row.get("año fin", ""))

                _, created = Proyecto.objects.update_or_create(
                    nombre=nombre,
                    defaults={
                        "actividad": actividad,
                        "status": row["Status"].strip(),
                        "año_inicio": año_inicio,
                        "año_fin": año_fin,
                        "enlace_wiki_proyecto": row["Enlace a wiki"].strip(),
                    },
                )
                if created:
                    creados += 1

        self.stdout.write(f"  {creados} proyectos creados, {omitidos} omitidos. Total: {Proyecto.objects.count()}")

    # ── Prototipos ───────────────────────────────────────────────────────────────

    def _importar_prototipos(self):
        self.stdout.write("\n[3/4] Importando prototipos...")
        creados, omitidos = 0, 0
        with open(BASE_DATOS / "Diagnóstico_Wikis - c_prototipos.csv", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                nombre_proto = row["prototipo"].strip()
                nombre_proj = row["proyecto"].strip()
                if not nombre_proto:
                    continue

                proyecto = Proyecto.objects.filter(nombre=nombre_proj).first()
                if not proyecto:
                    self.stdout.write(
                        self.style.WARNING(f"  ⚠ Proyecto '{nombre_proj}' no encontrado para prototipo '{nombre_proto}'")
                    )
                    omitidos += 1
                    continue

                _, created = Prototipo.objects.get_or_create(
                    nombre=nombre_proto,
                    defaults={"proyecto": proyecto},
                )
                if created:
                    creados += 1

        self.stdout.write(f"  {creados} prototipos creados, {omitidos} omitidos. Total: {Prototipo.objects.count()}")

    # ── Evaluaciones históricas ──────────────────────────────────────────────────

    def _importar_evaluaciones(self):
        self.stdout.write("\n[4/4] Importando evaluaciones históricas (r_wikis.csv)...")
        creadas, omitidas, excluidas = 0, 0, 0

        with open(BASE_DATOS / "Diagnóstico_Wikis - r_wikis.csv", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                nombre_proto = row["Prototipo"].strip()
                seccion = row["Sección de wiki"].strip()
                subseccion = row["Subsección de wiki"].strip()
                status_raw = row["Status"].strip()
                notas = row.get("notas de mejora", "").strip()

                # Excluir "Receta"
                if subseccion.lower().strip() in SUBSECCIONES_EXCLUIDAS:
                    excluidas += 1
                    continue

                prototipo = Prototipo.objects.filter(nombre=nombre_proto).first()
                if not prototipo:
                    omitidas += 1
                    continue

                # Normalizar status: el CSV usa "Completa" / "Incompleta"
                # Los datos históricos se importan como ya verificados
                status = status_raw if status_raw in ("Completa", "Incompleta", "Vacía") else "Incompleta"

                _, created = EvaluacionWiki.objects.update_or_create(
                    prototipo=prototipo,
                    seccion=seccion,
                    subseccion=subseccion,
                    defaults={
                        "status_scraper": status,
                        "contenido_chars": 0,  # no tenemos este dato en el histórico
                        "fecha_scraper": FECHA_HISTORICO,
                        "verificado": True,
                        "status_override": status,  # fijar el status manual como override
                        "notas_mejora": notas,      # para que el scraper no lo borre
                        "fecha_verificacion": FECHA_HISTORICO,
                    },
                )
                if created:
                    creadas += 1

        # update_or_create usa SQL UPDATE (no llama save()), así que
        # recalculamos status_final_cache en bulk con F expressions.
        from django.db.models import F
        EvaluacionWiki.objects.exclude(status_override="").update(
            status_final_cache=F("status_override")
        )
        EvaluacionWiki.objects.filter(status_override="").update(
            status_final_cache=F("status_scraper")
        )

        self.stdout.write(
            f"  {creadas} evaluaciones importadas, {omitidas} omitidas, {excluidas} excluidas (Receta).\n"
            f"  Total evaluaciones: {EvaluacionWiki.objects.count()}"
        )

    # ── Registro de actualización ────────────────────────────────────────────────

    def _registrar_actualizacion(self):
        total = EvaluacionWiki.objects.count()
        ActualizacionDashboard.objects.create(
            fecha=FECHA_HISTORICO,
            prototipos_evaluados=Prototipo.objects.count(),
            cambios_detectados=0,
            cambios_verificados=total,
            notas="Importación inicial desde CSV histórico 1.0",
        )
        self.stdout.write(f"\n  Registro de actualización creado con fecha {FECHA_HISTORICO.date()}")

    # ── Helpers ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_año(valor: str):
        try:
            return int(valor.strip())
        except (ValueError, AttributeError):
            return None
