# Setup local — Dashboards LABNL 2.0

## Arrancar el servidor

> ⚠️ El entorno virtual debe estar activo antes de correr el servidor.

```bash
cd /Users/ricardoburnes/Desktop/2026/26_03_Dashboards_LABNL_2.0/labnl_dashboards
source venv/bin/activate
python3 manage.py runserver
```

El servidor queda en `http://127.0.0.1:8000/`

El prompt de la terminal cambia a `(venv)` cuando el entorno está activo. Si no aparece, activarlo primero.

---

## Primera vez (configuración del entorno virtual)

Solo se hace una vez:

```bash
cd /Users/ricardoburnes/Desktop/2026/26_03_Dashboards_LABNL_2.0/labnl_dashboards
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Páginas del portal

| URL | Vista |
|---|---|
| `http://127.0.0.1:8000/` | Home — acceso a Wikis y DocSpaces |
| `http://127.0.0.1:8000/wikis/` | Lista de proyectos con filtros y gráfica resumen |
| `http://127.0.0.1:8000/wikis/<id>/` | Detalle de un proyecto (acordeón por prototipo + gráfica) |
| `http://127.0.0.1:8000/docspaces/` | Lista de proyectos DocSpace con criterios expandibles |
| `http://127.0.0.1:8000/global/` | Vista global: métricas y gráficas de avance |
| `http://127.0.0.1:8000/admin/` | Panel de administración (requiere superusuario) |

---

## Admin — primera vez

```bash
python3 manage.py createsuperuser
# Ingresa usuario, email (opcional) y contraseña
```

Luego entrar a `http://127.0.0.1:8000/admin/`

---

## Comandos de datos

### Importar todo desde cero

```bash
# 1. Importar datos históricos de wikis (CSV → DB)
python3 manage.py importar_historico

# 2. Importar evaluaciones de DocSpaces (CSV → DB)
python3 manage.py importar_docspaces

# 3. Si el scraper ya corrió y hay evaluaciones pendientes de aprobar
python3 manage.py verificar_pendientes
```

### Reimportar solo DocSpaces (sin borrar wikis)

```bash
python3 manage.py importar_docspaces --reset
```

### Reimportar todo desde cero (⚠️ borra todo)

```bash
python3 manage.py importar_historico --reset
python3 manage.py importar_docspaces --reset
```

### Correr el scraper de wikis

```bash
python3 manage.py evaluar_wikis
# Genera results/evaluacion_wikis.csv

python3 manage.py actualizar_desde_scraper
# Carga el CSV a la DB. Cambios quedan como pendientes de verificar.

python3 manage.py verificar_pendientes --dry-run
# Muestra cuántos cambios hay pendientes sin modificar nada

python3 manage.py verificar_pendientes
# Aprueba todos los cambios del scraper en lote
```

---

## Archivos clave

| Archivo | Qué hace |
|---|---|
| `diagnostico/views.py` | Lógica de cada vista (filtros, cálculos de avance) |
| `diagnostico/models.py` | Modelos de datos (Proyecto, Prototipo, EvaluacionWiki, EvaluacionDocSpace) |
| `templates/diagnostico/base.html` | Layout base con nav, header y estilos globales |
| `templates/diagnostico/wikis.html` | Lista de proyectos con filtros |
| `templates/diagnostico/detalle_proyecto.html` | Acordeón de prototipos + gráfica por sección |
| `templates/diagnostico/docspaces.html` | Criterios expandibles por proyecto |
| `templates/diagnostico/global.html` | Métricas y gráficas de avance global |
| `Bases de datos 1.0/` | CSVs originales (fuente de verdad histórica) |

---

## Producción — PythonAnywhere

**URL:** `documentacionlabnl.pythonanywhere.com`

### Ciclo de desarrollo

1. Hacer cambios localmente y probar con `python3 manage.py runserver`
2. Commit y push:
   ```bash
   git add -A
   git commit -m "descripción del cambio"
   git push
   ```
3. En la Bash de PythonAnywhere:
   ```bash
   workon labnl
   cd ~/dashboards_wiki-docspace/labnl_dashboards
   git pull
   ```
4. Según lo que hayas cambiado:

| Cambié... | Comando extra en PythonAnywhere |
|---|---|
| Templates HTML | Ninguno |
| Views/URLs (Python) | Ninguno |
| CSS/JS/imágenes | `python manage.py collectstatic --noinput` |
| Models.py | `python manage.py migrate` |

5. Ir a **Web** tab → click **Reload**

### Notas de producción

- **Django 5.2 LTS** (no 6.0) — PythonAnywhere free tier tiene Python 3.10
- **Virtualenv:** `workon labnl` para activar (usa `virtualenvwrapper`)
- **Variables de entorno:** archivo `.env` en el servidor (no en git)
- Si abres una nueva consola Bash, siempre ejecuta `workon labnl` primero
- Para crear superusuario en producción: `python manage.py createsuperuser`

---

## Notas de diseño

- **status_override** en `EvaluacionWiki`: guarda el status verificado manualmente desde el CSV. El scraper no lo sobreescribe — es la fuente de verdad. Si el scraper detecta un cambio, el dashboard sigue mostrando el status del CSV hasta que se re-verifique.
- **status_final_cache**: campo calculado = `status_override` si tiene valor, si no `status_scraper`. Es el que usa el dashboard para mostrar el avance.
- Las secciones de la wiki se muestran en el orden canónico definido en `views.py`: Prototipo → Aprendizajes → Desarrollo (no alfabético).
- La subsección "Continuidad" está excluida del cálculo y visualización.
