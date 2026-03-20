"""
Comando principal de actualización automática.
Corre el scraper completo y actualiza la base de datos en un solo paso.

Uso manual:
    python manage.py evaluar_wikis
    python manage.py evaluar_wikis --limite 5   # para pruebas

Cron (cada lunes a las 6am):
    0 6 * * 1 cd /ruta/proyecto && python manage.py evaluar_wikis >> /ruta/logs/cron.log 2>&1
"""

import sys
import csv
import time
import unicodedata
import re
import logging
from pathlib import Path
from datetime import datetime

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from diagnostico.models import Prototipo, EvaluacionWiki, ActualizacionDashboard

# ── Configuración ────────────────────────────────────────────────────────────────

API_URL = "https://wiki.labnuevoleon.mx/api.php"
HEADERS = {"User-Agent": "LABNL-Dashboard/2.0 (ricardo@labnuevoleon.mx)"}
API_DELAY = 0.3
MIN_CHARS = 50

SUBSECCIONES = {
    "Prototipo": ["Antecedentes", "Equipo", "Imagen de prototipo", "Descripción del prototipo"],
    "Aprendizajes": ["Hito 1", "Hito 2", "Hito 3", "Hito 4"],
    "Desarrollo": [
        "Validación", "Hoja de ruta", "Partes del Prototipo", "Ingredientes",
        "Consejos", "Pasos", "Referencias", "Archivos para replicar",
        "Continuidad", "Alianzas", "Sostenibilidad", "Medios", "Vinculaciones",
    ],
}

log = logging.getLogger(__name__)


# ── API ──────────────────────────────────────────────────────────────────────────

def api_get(params):
    params["format"] = "json"
    params["formatversion"] = "2"
    r = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


def pagina_existe(titulo):
    data = api_get({"action": "query", "titles": titulo, "prop": "info", "inprop": "url"})
    pages = data.get("query", {}).get("pages", [])
    items = pages if isinstance(pages, list) else list(pages.values())
    for p in items:
        pid = p.get("pageid")
        return pid is not None and pid > 0, p.get("fullurl", "")
    return False, ""


def obtener_secciones(titulo):
    data = api_get({"action": "parse", "page": titulo, "prop": "sections"})
    if "error" in data:
        return []
    return data.get("parse", {}).get("sections", [])


def obtener_contenido_seccion(titulo, idx):
    data = api_get({"action": "parse", "page": titulo, "prop": "wikitext", "section": idx})
    if "error" in data:
        return ""
    wikitext = data.get("parse", {}).get("wikitext", "")
    return wikitext.get("*", "") if isinstance(wikitext, dict) else wikitext


def normalizar(texto):
    texto = re.sub(r"<[^>]+>", "", texto).strip().lower()
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# ── Evaluación ───────────────────────────────────────────────────────────────────

def evaluar_prototipo_desde_wiki(nombre):
    existe, url = pagina_existe(nombre)
    time.sleep(API_DELAY)

    if not existe:
        return {"url": url, "criterios": {}, "sin_pagina": True}

    secciones_raw = obtener_secciones(nombre)
    time.sleep(API_DELAY)
    mapa = {normalizar(s["line"]): s["index"] for s in secciones_raw}

    criterios = {}
    for seccion, subsecciones in SUBSECCIONES.items():
        for sub in subsecciones:
            clave = f"{seccion}|{sub}"
            norm = normalizar(sub)
            if norm in mapa:
                contenido = obtener_contenido_seccion(nombre, mapa[norm])
                time.sleep(API_DELAY)
                chars = len(contenido.strip())
                criterios[clave] = {
                    "status": "Completa" if chars >= MIN_CHARS else "Vacía",
                    "chars": chars,
                }
            else:
                criterios[clave] = {"status": "Incompleta", "chars": 0}

    return {"url": url, "criterios": criterios, "sin_pagina": False}


# ── Actualización en BD ──────────────────────────────────────────────────────────

def actualizar_bd(prototipo_obj, resultado, fecha):
    cambios = 0

    if resultado["sin_pagina"]:
        return 0

    # Actualizar URL si se obtuvo
    if resultado["url"] and not prototipo_obj.url_wiki:
        prototipo_obj.url_wiki = resultado["url"]
        prototipo_obj.save(update_fields=["url_wiki"])

    for clave, info in resultado["criterios"].items():
        seccion, subseccion = clave.split("|", 1)
        status_nuevo = info["status"]

        ev = EvaluacionWiki.objects.filter(
            prototipo=prototipo_obj, seccion=seccion, subseccion=subseccion
        ).first()

        if ev is None:
            EvaluacionWiki.objects.create(
                prototipo=prototipo_obj,
                seccion=seccion, subseccion=subseccion,
                status_scraper=status_nuevo,
                contenido_chars=info["chars"],
                fecha_scraper=fecha,
                verificado=False,
            )
            cambios += 1
        else:
            # Actualizar fecha y chars siempre
            ev.status_scraper = status_nuevo
            ev.contenido_chars = info["chars"]
            ev.fecha_scraper = fecha

            if ev.status_final_cache != status_nuevo:
                # Cambio real → marcar como pendiente de verificación
                ev.verificado = False
                ev.status_override = ""
                ev.fecha_verificacion = None
                cambios += 1

            ev.save()

    return cambios


# ── Comando ──────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Evalúa todas las wikis y actualiza la BD detectando cambios"

    def add_arguments(self, parser):
        parser.add_argument("--limite", type=int, help="Evalúa solo los primeros N prototipos (pruebas)")

    def handle(self, *args, **options):
        fecha = timezone.now()
        prototipos = Prototipo.objects.all().order_by("nombre")

        if options["limite"]:
            prototipos = prototipos[: options["limite"]]

        total = prototipos.count()
        self.stdout.write(f"Iniciando evaluación de {total} prototipos — {fecha.strftime('%Y-%m-%d %H:%M')}\n")

        evaluados = 0
        sin_pagina = 0
        cambios_total = 0

        for i, proto in enumerate(prototipos, 1):
            self.stdout.write(f"[{i}/{total}] {proto.nombre[:60]}")
            try:
                resultado = evaluar_prototipo_desde_wiki(proto.nombre)
                cambios = actualizar_bd(proto, resultado, fecha)
                cambios_total += cambios
                evaluados += 1

                if resultado["sin_pagina"]:
                    sin_pagina += 1
                    self.stdout.write("  → SIN PÁGINA\n")
                else:
                    flag = f" ({cambios} cambios)" if cambios else ""
                    self.stdout.write(f"  → OK{flag}\n")

            except Exception as e:
                self.stdout.write(f"  → ERROR: {e}\n")

        # Registrar la actualización
        ActualizacionDashboard.objects.create(
            fecha=fecha,
            prototipos_evaluados=evaluados,
            cambios_detectados=cambios_total,
            cambios_verificados=0,
            notas=f"Ejecución automática — {cambios_total} cambios detectados",
        )

        self.stdout.write(self.style.SUCCESS(
            f"\n{'='*50}\n"
            f"RESUMEN\n"
            f"  Prototipos evaluados:     {evaluados}\n"
            f"  Sin página wiki:          {sin_pagina}\n"
            f"  Cambios detectados:       {cambios_total}\n"
            f"{'='*50}\n"
        ))
