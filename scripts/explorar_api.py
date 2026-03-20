"""
FASE 1 — Exploración de la MediaWiki API
=========================================
Objetivo: Entender qué datos podemos extraer de wiki.labnuevoleon.mx
y cómo mapearlos a los 21 criterios de evaluación.

Uso:
    python explorar_api.py                  # Corre todos los experimentos
    python explorar_api.py --proyecto "Nombre del Proyecto"  # Explora 1 proyecto
"""

import requests
import json
import sys
import time
from pprint import pprint

# ── Configuración ──────────────────────────────────────────────────────────────

API_URL = "https://wiki.labnuevoleon.mx/api.php"
HEADERS = {"User-Agent": "LABNL-Dashboard/2.0 (ricardo@labnuevoleon.mx)"}

# Las 21 subsecciones activas (sin "Receta")
SUBSECCIONES_ACTIVAS = {
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

# ── Funciones de consulta ──────────────────────────────────────────────────────

def api_get(params: dict) -> dict:
    """Hace una llamada GET a la API de MediaWiki y devuelve el JSON."""
    params["format"] = "json"
    params["formatversion"] = "2"
    response = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
    response.raise_for_status()
    return response.json()


def listar_todas_las_paginas(prefijo: str = "", limite: int = 500) -> list[dict]:
    """
    Lista todas las páginas del wiki.
    Devuelve una lista de dicts con {pageid, title, fullurl}.
    """
    paginas = []
    params = {
        "action": "query",
        "list": "allpages",
        "aplimit": limite,
        "apnamespace": 0,  # Solo namespace principal
    }
    if prefijo:
        params["apfrom"] = prefijo

    print(f"\n[1] Listando páginas del wiki (límite: {limite})...")
    data = api_get(params)
    paginas_raw = data.get("query", {}).get("allpages", [])

    # También obtener las URLs completas con una segunda query
    if paginas_raw:
        titles = "|".join(p["title"] for p in paginas_raw[:50])  # batch de 50
        url_data = api_get({
            "action": "query",
            "titles": titles,
            "prop": "info",
            "inprop": "url",
        })
        url_map = {}
        pages_data = url_data.get("query", {}).get("pages", [])
        # formatversion=2 returns pages as a list; v1 returns a dict
        if isinstance(pages_data, list):
            for page_info in pages_data:
                url_map[page_info.get("title")] = page_info.get("fullurl", "")
        else:
            for page_id, page_info in pages_data.items():
                url_map[page_info.get("title")] = page_info.get("fullurl", "")

        for p in paginas_raw:
            paginas.append({
                "pageid": p["pageid"],
                "title": p["title"],
                "fullurl": url_map.get(p["title"], f"https://wiki.labnuevoleon.mx/wiki/{p['title'].replace(' ', '_')}"),
            })

    print(f"   → {len(paginas)} páginas encontradas")
    return paginas


def obtener_secciones(titulo_pagina: str) -> list[dict]:
    """
    Obtiene las secciones de una página wiki.
    Devuelve lista de dicts con {index, level, line (título de sección)}.
    """
    data = api_get({
        "action": "parse",
        "page": titulo_pagina,
        "prop": "sections",
    })
    if "error" in data:
        print(f"   ✗ Error al obtener secciones de '{titulo_pagina}': {data['error'].get('info')}")
        return []
    return data.get("parse", {}).get("sections", [])


def obtener_contenido_seccion(titulo_pagina: str, seccion_index: int) -> str:
    """
    Obtiene el wikitext de una sección específica de una página.
    section=0 obtiene el contenido antes de la primera sección.
    """
    data = api_get({
        "action": "parse",
        "page": titulo_pagina,
        "prop": "wikitext",
        "section": seccion_index,
    })
    if "error" in data:
        return ""
    return data.get("parse", {}).get("wikitext", {}).get("*", "")


def obtener_url_wiki(titulo_pagina: str) -> str:
    """Obtiene la URL canónica de una página wiki."""
    data = api_get({
        "action": "query",
        "titles": titulo_pagina,
        "prop": "info",
        "inprop": "url",
    })
    pages = data.get("query", {}).get("pages", {})
    # formatversion=2 returns a list, v1 returns a dict
    if isinstance(pages, list):
        for page_info in pages:
            return page_info.get("fullurl", "")
    else:
        for page_info in pages.values():
            return page_info.get("fullurl", "")
    return ""


# ── Lógica de evaluación ───────────────────────────────────────────────────────

def normalizar(texto: str) -> str:
    """Normaliza un título para comparación flexible (sin tildes, lowercase, sin espacios extra)."""
    import unicodedata
    texto = texto.strip().lower()
    # Quitar tildes
    nfkd = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in nfkd if not unicodedata.combining(c))
    return texto


def evaluar_wiki_proyecto(titulo_pagina: str) -> dict:
    """
    Evalúa las 21 subsecciones de un proyecto.
    Devuelve un dict con el resultado de cada criterio.
    """
    print(f"\n[→] Evaluando: '{titulo_pagina}'")
    url_wiki = obtener_url_wiki(titulo_pagina)
    secciones_wiki = obtener_secciones(titulo_pagina)

    if not secciones_wiki:
        print("   ✗ No se encontraron secciones.")
        return {"titulo": titulo_pagina, "url_wiki": url_wiki, "criterios": {}, "avance": 0}

    print(f"   Secciones encontradas en la wiki ({len(secciones_wiki)}):")
    for s in secciones_wiki:
        print(f"     [{s['index']}] nivel {s['toclevel']} — {s['line']}")

    # Crear mapa de secciones normalizadas → index
    mapa_secciones = {normalizar(s["line"]): s["index"] for s in secciones_wiki}

    resultados = {}
    for seccion, subsecciones in SUBSECCIONES_ACTIVAS.items():
        for subseccion in subsecciones:
            clave = f"{seccion} > {subseccion}"
            nombre_norm = normalizar(subseccion)

            if nombre_norm in mapa_secciones:
                # La sección existe, verificar si tiene contenido
                idx = mapa_secciones[nombre_norm]
                contenido = obtener_contenido_seccion(titulo_pagina, idx)
                tiene_contenido = len(contenido.strip()) > 50  # Mínimo 50 chars
                resultados[clave] = {
                    "status": "Completa" if tiene_contenido else "Vacía",
                    "encontrada": True,
                    "contenido_chars": len(contenido.strip()),
                }
            else:
                resultados[clave] = {
                    "status": "Incompleta",
                    "encontrada": False,
                    "contenido_chars": 0,
                }
            time.sleep(0.2)  # Rate limiting: 200ms entre llamadas

    completas = sum(1 for v in resultados.values() if v["status"] == "Completa")
    total = len(resultados)
    avance = (completas / total * 100) if total > 0 else 0

    return {
        "titulo": titulo_pagina,
        "url_wiki": url_wiki,
        "criterios": resultados,
        "completas": completas,
        "total": total,
        "avance": round(avance, 2),
    }


# ── Experimentos de exploración ────────────────────────────────────────────────

def experimento_1_listar_paginas():
    """Lista las primeras 50 páginas para ver qué hay en el wiki."""
    print("\n" + "="*60)
    print("EXPERIMENTO 1: Listado de páginas del wiki")
    print("="*60)
    paginas = listar_todas_las_paginas(limite=50)
    print("\nPrimeras 20 páginas:")
    for p in paginas[:20]:
        print(f"  [{p['pageid']}] {p['title']}")
        print(f"       {p['fullurl']}")
    return paginas


def experimento_2_explorar_proyecto(titulo: str):
    """Explora un proyecto específico."""
    print("\n" + "="*60)
    print(f"EXPERIMENTO 2: Exploración de '{titulo}'")
    print("="*60)
    resultado = evaluar_wiki_proyecto(titulo)

    print(f"\n  URL: {resultado['url_wiki']}")
    print(f"  Avance: {resultado['avance']}% ({resultado.get('completas', 0)}/{resultado.get('total', 0)} criterios)")
    print("\n  Detalle por criterio:")
    for criterio, info in resultado.get("criterios", {}).items():
        icono = "✓" if info["status"] == "Completa" else ("~" if info["encontrada"] else "✗")
        print(f"  {icono} {criterio} [{info['contenido_chars']} chars]")

    return resultado


def experimento_3_buscar_proyectos_csv():
    """
    Intenta encontrar en la wiki los proyectos que están en el CSV.
    Útil para detectar discrepancias de nombres.
    """
    print("\n" + "="*60)
    print("EXPERIMENTO 3: Verificar proyectos del CSV en la wiki")
    print("="*60)

    import csv
    csv_path = "/Users/ricardoburnes/Desktop/2026/26_03_Dashboards_LABNL_2.0/Bases de datos 1.0/Diagnóstico_Wikis - r_wikis.csv"

    proyectos_csv = set()
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            proyectos_csv.add(row["Proyecto"])

    print(f"  Proyectos en CSV: {len(proyectos_csv)}")

    # Buscar cada proyecto en la API
    encontrados = []
    no_encontrados = []
    for proyecto in sorted(proyectos_csv)[:10]:  # Probamos los primeros 10
        data = api_get({
            "action": "query",
            "titles": proyecto,
            "prop": "info",
            "inprop": "url",
        })
        pages = data.get("query", {}).get("pages", {})
        for pid, info in pages.items():
            if pid == "-1":
                no_encontrados.append(proyecto)
                print(f"  ✗ NO encontrado: {proyecto}")
            else:
                encontrados.append({"titulo": proyecto, "url": info.get("fullurl")})
                print(f"  ✓ Encontrado: {proyecto}")
        time.sleep(0.3)

    print(f"\n  Resultado (muestra de 10): {len(encontrados)} encontrados, {len(no_encontrados)} no encontrados")
    return encontrados, no_encontrados


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    proyecto_prueba = None
    if len(sys.argv) > 2 and sys.argv[1] == "--proyecto":
        proyecto_prueba = sys.argv[2]

    if proyecto_prueba:
        experimento_2_explorar_proyecto(proyecto_prueba)
    else:
        # Correr todos los experimentos de exploración
        paginas = experimento_1_listar_paginas()

        # Tomar el primer proyecto de la lista para el experimento 2
        if paginas:
            primer_proyecto = paginas[0]["title"]
            print(f"\nUsando '{primer_proyecto}' para el experimento de evaluación...")
            experimento_2_explorar_proyecto(primer_proyecto)

        experimento_3_buscar_proyectos_csv()

    print("\n✓ Exploración completada.")
