# Scraper de Wikis — Ejecución manual

El scraper consulta la API de `wiki.labnuevoleon.mx`, evalua las 21 subsecciones de cada proyecto y actualiza la base de datos con el avance.

---

## En PythonAnywhere (produccion)

### 1. Abrir consola Bash

PythonAnywhere > **Consoles** > **Bash**

### 2. Activar virtualenv y ejecutar

```bash
workon labnl
cd ~/dashboards_wiki-docspace/labnl_dashboards
python manage.py evaluar_wikis
```

### 3. Reload del sitio

Despues de correr el scraper, ve a la pestana **Web** y haz click en **Reload** para que el sitio refleje los datos actualizados.

---

## En local (Mac)

```bash
cd /Users/ricardoburnes/Desktop/2026/26_03_Dashboards_LABNL_2.0/labnl_dashboards
source venv/bin/activate
python3 manage.py evaluar_wikis
```

Si quieres subir los datos actualizados a produccion:
```bash
# Subir db.sqlite3 desde Files tab en PythonAnywhere
# O hacer git push si solo cambiaste codigo
```

---

## Frecuencia recomendada

Los datos de las wikis no cambian muy seguido. Correr el scraper **1-2 veces por semana** es suficiente.

---

## Que hace el scraper

1. Consulta la MediaWiki API para obtener la lista de proyectos
2. Para cada proyecto, parsea las secciones del wikitext
3. Evalua 21 subsecciones (3 secciones principales):
   - **Prototipo** (4 subsecciones)
   - **Aprendizajes** (4 subsecciones)
   - **Desarrollo** (13 subsecciones, sin "Receta")
4. Guarda el resultado en la base de datos
5. Calcula `status_final_cache` = `status_override` (si existe) o `status_scraper`

---

## Si el scraper falla en PythonAnywhere

El free tier de PythonAnywhere limita las conexiones HTTP salientes a un whitelist de dominios. Si ves un error como:

```
ConnectionError: HTTPSConnectionPool(host='wiki.labnuevoleon.mx')
```

Significa que `wiki.labnuevoleon.mx` no esta en el whitelist. Opciones:

1. **Solicitar que lo agreguen** — manda email a `support@pythonanywhere.com` pidiendo que agreguen `wiki.labnuevoleon.mx` al whitelist. Lo hacen gratis.
2. **Correr el scraper en local** — ejecutalo en tu Mac y luego sube el `db.sqlite3` actualizado a PythonAnywhere desde la pestana Files.
3. **Upgrade a cuenta de pago** ($5/mes) — desbloquea HTTP saliente y scheduled tasks.

---

## Otros comandos utiles

```bash
# Importar datos historicos desde CSV (solo primera vez)
python manage.py importar_historico

# Importar evaluaciones de DocSpaces desde CSV
python manage.py importar_docspaces

# Ver cambios pendientes del scraper sin aplicar
python manage.py verificar_pendientes --dry-run

# Aprobar todos los cambios del scraper
python manage.py verificar_pendientes
```
