"""
FASE 2 — Scraper completo de wikis LABNL
==========================================
Evalúa automáticamente las 21 subsecciones de cada prototipo.

Modelo de datos:
    Actividad → Proyecto (wiki landing) → Prototipo (wiki con 21 criterios)

Fuentes:
    c_proyectos.csv   → metadata: actividad, status, año, enlace_wiki del proyecto
    c_prototipos.csv  → relación prototipo → proyecto (105 prototipos, 72 proyectos)

Uso:
    python scraper_wikis.py                      # Evalúa todos los prototipos
    python scraper_wikis.py --prototipo "Nombre" # Evalúa un solo prototipo
    python scraper_wikis.py --limite 5           # Evalúa los primeros N prototipos

Salida:
    results/evaluacion_wikis.csv  — una fila por criterio × prototipo
    results/resumen_wikis.csv     — una fila por prototipo con % de avance
"""

import requests
import csv
import sys
import time
import unicodedata
import logging
import argparse
import re
from pathlib import Path
from datetime import datetime

# ── Configuración ───────────────────────────────────────────────────────────────

API_URL = "https://wiki.labnuevoleon.mx/api.php"
HEADERS = {"User-Agent": "LABNL-Dashboard/2.0 (ricardo@labnuevoleon.mx)"}

BASE_DIR = Path(__file__).parent.parent
BASE_DATOS = BASE_DIR / "Bases de datos 1.0"
RESULTS_DIR = BASE_DIR / "results"

API_DELAY = 0.3           # segundos entre llamadas a la API
MIN_CONTENIDO_CHARS = 50  # mínimo para considerar una sección "con contenido"

# Las 21 subsecciones activas (sin "Receta")
SUBSECCIONES = {
    "Prototipo": [
        "Antecedentes",
        "Equipo",
        "Imagen de prototipo",
        "Descripción del prototipo",
    ],
    "Aprendizajes": [
        "Hito 1",
        "Hito 2",
        "Hito 3",
        "Hito 4",
    ],
    "Desarrollo": [
        "Validación",
        "Hoja de ruta",
        "Partes del Prototipo",
        "Ingredientes",
        "Consejos",
        "Pasos",
        "Referencias",
        "Archivos para replicar",
        "Continuidad",
        "Alianzas",
        "Sostenibilidad",
        "Medios",
        "Vinculaciones",
    ],
}

# ── Setup ────────────────────────────────────────────────────────────────────────

RESULTS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    handlers=[
        logging.FileHandler(RESULTS_DIR / "log_scraper.txt", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ── Carga de catálogos ──────────────────────────────────────────────────────────


def cargar_proyectos() -> dict:
    """
    Devuelve dict: nombre_proyecto → {tipo_actividades, status, enlace_wiki, año_inicio, año_fin}
    """
    proyectos = {}
    with open(BASE_DATOS / "Diagnóstico_Wikis - c_proyectos.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            nombre = row["proyectos"].strip()
            proyectos[nombre] = {
                "tipo_actividades": row["tipo_actividades"].strip(),
                "status": row["Status"].strip(),
                "enlace_wiki_proyecto": row["Enlace a wiki"].strip(),
                "año_inicio": row["año de inicio"].strip(),
                "año_fin": row["año fin"].strip(),
            }
    return proyectos


def cargar_prototipos() -> list[dict]:
    """
    Devuelve lista de {prototipo, proyecto} desde el catálogo.
    """
    prototipos = []
    with open(BASE_DATOS / "Diagnóstico_Wikis - c_prototipos.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            prototipos.append({
                "prototipo": row["prototipo"].strip(),
                "proyecto": row["proyecto"].strip(),
            })
    return prototipos


# ── Funciones de API ────────────────────────────────────────────────────────────


def api_get(params: dict) -> dict:
    params["format"] = "json"
    params["formatversion"] = "2"
    try:
        r = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        log.error(f"Error en API: {e}")
        raise


def obtener_url_wiki(titulo: str) -> str:
    data = api_get({"action": "query", "titles": titulo, "prop": "info", "inprop": "url"})
    pages = data.get("query", {}).get("pages", [])
    if isinstance(pages, list):
        for p in pages:
            return p.get("fullurl", "")
    else:
        for p in pages.values():
            return p.get("fullurl", "")
    return ""


def pagina_existe(titulo: str) -> tuple[bool, str]:
    """Devuelve (existe, fullurl)."""
    data = api_get({"action": "query", "titles": titulo, "prop": "info", "inprop": "url"})
    pages = data.get("query", {}).get("pages", [])
    items = pages if isinstance(pages, list) else list(pages.values())
    for p in items:
        pageid = p.get("pageid")
        exists = pageid is not None and pageid > 0
        return exists, p.get("fullurl", "")
    return False, ""


def obtener_secciones(titulo: str) -> list[dict]:
    data = api_get({"action": "parse", "page": titulo, "prop": "sections"})
    if "error" in data:
        return []
    return data.get("parse", {}).get("sections", [])


def obtener_contenido_seccion(titulo: str, seccion_index) -> str:
    data = api_get({
        "action": "parse",
        "page": titulo,
        "prop": "wikitext",
        "section": seccion_index,
    })
    if "error" in data:
        return ""
    wikitext = data.get("parse", {}).get("wikitext", "")
    # formatversion=2 → string directo; v1 → {"*": "..."}
    if isinstance(wikitext, dict):
        return wikitext.get("*", "")
    return wikitext


# ── Normalización ───────────────────────────────────────────────────────────────


def normalizar(texto: str) -> str:
    """Lowercase sin tildes ni tags HTML, para matching flexible."""
    texto = re.sub(r"<[^>]+>", "", texto).strip().lower()
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# ── Evaluación ──────────────────────────────────────────────────────────────────


def evaluar_prototipo(nombre_prototipo: str) -> dict:
    """
    Evalúa las 21 subsecciones de un prototipo en su página wiki.
    """
    existe, url_wiki = pagina_existe(nombre_prototipo)
    time.sleep(API_DELAY)

    criterios_vacios = {
        f"{sec} > {sub}": {"status": "Incompleta", "encontrada": False, "contenido_chars": 0}
        for sec, subs in SUBSECCIONES.items()
        for sub in subs
    }

    if not existe:
        log.warning(f"  Sin página wiki: '{nombre_prototipo}'")
        return {
            "prototipo": nombre_prototipo,
            "url_wiki_prototipo": url_wiki,
            "criterios": criterios_vacios,
            "completas": 0,
            "total": 21,
            "avance": 0.0,
            "sin_pagina": True,
        }

    secciones_raw = obtener_secciones(nombre_prototipo)
    time.sleep(API_DELAY)

    # Mapa: título_normalizado → index
    mapa = {normalizar(s["line"]): s["index"] for s in secciones_raw}

    criterios = {}
    for seccion, subsecciones in SUBSECCIONES.items():
        for sub in subsecciones:
            clave = f"{seccion} > {sub}"
            norm = normalizar(sub)
            if norm in mapa:
                contenido = obtener_contenido_seccion(nombre_prototipo, mapa[norm])
                time.sleep(API_DELAY)
                chars = len(contenido.strip())
                criterios[clave] = {
                    "status": "Completa" if chars >= MIN_CONTENIDO_CHARS else "Vacía",
                    "encontrada": True,
                    "contenido_chars": chars,
                }
            else:
                criterios[clave] = {
                    "status": "Incompleta",
                    "encontrada": False,
                    "contenido_chars": 0,
                }

    completas = sum(1 for v in criterios.values() if v["status"] == "Completa")
    return {
        "prototipo": nombre_prototipo,
        "url_wiki_prototipo": url_wiki,
        "criterios": criterios,
        "completas": completas,
        "total": 21,
        "avance": round(completas / 21 * 100, 2),
        "sin_pagina": False,
    }


# ── Escritura de resultados ─────────────────────────────────────────────────────


def guardar_resultados(evaluaciones: list[dict], proyectos: dict, proto_proyecto: dict, fecha: str):
    """
    Escribe dos CSVs:
    - evaluacion_wikis.csv: detalle por criterio (prototipo × criterio)
    - resumen_wikis.csv: una fila por prototipo con metadata del proyecto
    """
    # 1. Detalle por criterio
    with open(RESULTS_DIR / "evaluacion_wikis.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "Proyecto", "tipo_actividades", "status_proyecto",
            "Prototipo", "url_wiki_prototipo",
            "Sección", "Subsección", "Status", "Encontrada", "Chars", "Fecha",
        ])
        for ev in evaluaciones:
            proyecto = proto_proyecto.get(ev["prototipo"], ev["prototipo"])
            meta = proyectos.get(proyecto, {})
            for clave, info in ev["criterios"].items():
                seccion, subseccion = clave.split(" > ", 1)
                w.writerow([
                    proyecto,
                    meta.get("tipo_actividades", ""),
                    meta.get("status", ""),
                    ev["prototipo"],
                    ev["url_wiki_prototipo"],
                    seccion,
                    subseccion,
                    info["status"],
                    info["encontrada"],
                    info["contenido_chars"],
                    fecha,
                ])
    log.info(f"Detalle guardado en {RESULTS_DIR / 'evaluacion_wikis.csv'}")

    # 2. Resumen por prototipo
    with open(RESULTS_DIR / "resumen_wikis.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "Proyecto", "tipo_actividades", "status_proyecto", "año_inicio",
            "enlace_wiki_proyecto",
            "Prototipo", "url_wiki_prototipo",
            "Criterios_Completos", "Total_Criterios", "Avance_Pct",
            "Sin_Pagina_Wiki", "Fecha",
        ])
        for ev in evaluaciones:
            proyecto = proto_proyecto.get(ev["prototipo"], ev["prototipo"])
            meta = proyectos.get(proyecto, {})
            w.writerow([
                proyecto,
                meta.get("tipo_actividades", ""),
                meta.get("status", ""),
                meta.get("año_inicio", ""),
                meta.get("enlace_wiki_proyecto", ""),
                ev["prototipo"],
                ev["url_wiki_prototipo"],
                ev["completas"],
                ev["total"],
                ev["avance"],
                ev["sin_pagina"],
                fecha,
            ])
    log.info(f"Resumen guardado en {RESULTS_DIR / 'resumen_wikis.csv'}")


# ── Main ────────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Scraper de wikis LABNL — nivel prototipo")
    parser.add_argument("--prototipo", help="Evalúa solo este prototipo")
    parser.add_argument("--limite", type=int, help="Evalúa solo los primeros N prototipos")
    args = parser.parse_args()

    fecha = datetime.now().strftime("%Y-%m-%d")
    proyectos = cargar_proyectos()
    prototipos_lista = cargar_prototipos()

    # Mapa prototipo → proyecto para lookup rápido
    proto_proyecto = {p["prototipo"]: p["proyecto"] for p in prototipos_lista}

    if args.prototipo:
        items = [p for p in prototipos_lista if p["prototipo"] == args.prototipo]
        if not items:
            log.error(f"Prototipo '{args.prototipo}' no encontrado en el catálogo.")
            sys.exit(1)
    else:
        items = prototipos_lista
        if args.limite:
            items = items[: args.limite]

    log.info(f"Evaluando {len(items)} prototipo(s) — {fecha}")

    evaluaciones = []
    for i, item in enumerate(items, 1):
        nombre = item["prototipo"]
        proyecto = item["proyecto"]
        log.info(f"[{i}/{len(items)}] {nombre[:60]}  (→ {proyecto[:40]})")
        try:
            ev = evaluar_prototipo(nombre)
            evaluaciones.append(ev)
            flag = "SIN PÁGINA" if ev["sin_pagina"] else "OK"
            log.info(f"  Avance: {ev['avance']}% ({ev['completas']}/21) | {flag}")
        except Exception as e:
            log.error(f"  Error: {e}")

    guardar_resultados(evaluaciones, proyectos, proto_proyecto, fecha)

    if evaluaciones:
        con_pagina = [e for e in evaluaciones if not e["sin_pagina"]]
        promedio = sum(e["avance"] for e in con_pagina) / len(con_pagina) if con_pagina else 0
        sin_pagina = len(evaluaciones) - len(con_pagina)
        log.info(f"\n{'='*50}")
        log.info(f"RESUMEN FINAL")
        log.info(f"  Prototipos evaluados:  {len(evaluaciones)}")
        log.info(f"  Sin página wiki:       {sin_pagina}")
        log.info(f"  Avance promedio:       {promedio:.1f}%  (solo los que tienen página)")
        log.info(f"{'='*50}")


if __name__ == "__main__":
    main()
