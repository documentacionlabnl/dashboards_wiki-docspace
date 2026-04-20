# Plan Maestro: Dashboards Documentación LABNL 2.0

**Fecha:** Marzo 2026
**Autor:** Ricardo (con apoyo de Claude)
**Versión:** 1.6 (Fase 6 en progreso — mejoras de admin, scraper y timestamp de dashboard)

---

## 0. Referencia de trabajo

| Dato | Valor |
|---|---|
| **Carpeta del proyecto** | `/Users/ricardoburnes/Desktop/2026/26_03_Dashboards_LABNL_2.0` |
| **Wiki fuente** | `https://wiki.labnuevoleon.mx` |
| **API MediaWiki** | `https://wiki.labnuevoleon.mx/api.php` |
| **Bases de datos actuales** | `<carpeta del proyecto>/Bases de datos 1.0/` |

> ⚠️ **Para Claude Code:** Todos los archivos del proyecto viven en `/Users/ricardoburnes/Desktop/2026/26_03_Dashboards_LABNL_2.0`. Iniciar siempre desde ahí.

---

## 1. Diagnóstico del estado actual

### Datos que tenemos

| Base de datos | Proyectos | Criterios por proyecto | Valor por criterio | Total posible |
|---|---|---|---|---|
| **Wikis** | ~77 proyectos | 21 subsecciones (se excluye "Receta") | 4.761% c/u | 100% |
| **DocSpaces** | ~21 proyectos | 7 secciones | 14.285% c/u | 100% |

### Criterios de la Wiki (21 subsecciones activas)

Las wikis se evalúan en 3 secciones principales con sus subsecciones:

- **Prototipo** (4): Antecedentes, Equipo, Imagen de prototipo, Descripción del prototipo
- **Aprendizajes** (4): Hito 1, Hito 2, Hito 3, Hito 4
- **Desarrollo** (13, se excluye "Receta"): Validación, Hoja de ruta, Partes del Prototipo, Ingredientes, Consejos, Pasos, Referencias, Archivos para replicar, Continuidad, Alianzas, Sostenibilidad, Medios, Vinculaciones

### Criterios de DocSpaces (7 secciones)

- Nombre de proyecto
- Descripción de proyecto
- Trazas del proceso de prototipado
- El prototipo y/o partes de él
- Fotografías del prototipo a lo largo del proceso y en su estado actual
- Fotografías de las personas colaboradoras en el proyecto o comunidad
- QR o enlace a la wiki

### Flujo actual (manual)

```
Revisar wiki por wiki (navegador) → Anotar en Google Sheets → Refrescar Power BI → Publicar
Revisar docspace por docspace (físico) → Anotar en Google Sheets → Refrescar Power BI → Publicar
```

### Potencial de automatización

| Fuente | ¿Automatizable? | Razón |
|---|---|---|
| **Wikis** | SÍ (alto) | MediaWiki tiene API pública. Se puede verificar si cada sección existe y tiene contenido |
| **DocSpaces** | PARCIAL (bajo) | Son espacios físicos. Solo se puede automatizar el registro/dashboard, no la revisión in situ |

---

## 1.5. Análisis de los dashboards actuales en Power BI

### Requerimientos identificados (acumulados)

1. **Un solo enlace:** Todo el portal (wikis + docspaces + vistas globales) debe estar disponible desde una sola URL base.
2. **Excluir "Receta":** La subsección "Receta" de Desarrollo se elimina de los criterios. Los criterios pasan de 22 a 21.
3. **Vistas globales:** Visualizaciones de avance agregado por actividad y sección (como la gráfica de área de Power BI).
4. **Botón de enlace a la wiki:** En cada vista de proyecto debe haber un botón/enlace que abra directamente la página wiki del proyecto analizado en `wiki.labnuevoleon.mx`. Esto permite ir de la métrica al contenido real con un solo clic.

### Anatomía del dashboard actual de Wikis (Power BI)

El dashboard actual tiene un diseño de tema oscuro con acento amarillo/dorado. Sus componentes son:

**Filtros superiores:**
- Actividades (Comunidad, MIC, Sesiones de prototipado — ⚠️ este campo NO está en el CSV actual, viene de otra fuente o es un catálogo aparte)
- Proyecto (dropdown con todos los proyectos)
- Status (Activo/Inactivo)
- Año de inicio
- Buscador de texto con toggles "proyecto" / "prototipo"
- Botón "Restablecer"

**Visualizaciones:**
- **Gráfica de barras apiladas** "Avance de Wikis por Proyecto": muestra Completa vs Incompleta por proyecto (eje X = proyecto, eje Y = %)
- **Gráfica de barras horizontales** "Avance de Wikis por Prototipo": muestra conteo de secciones completas e incompletas por prototipo individual
- **Tabla de detalle**: Sección de wiki, Subsección, Status, notas de mejora (se filtra al seleccionar un proyecto)
- **Gauge semicircular** "Avance": muestra el valor sumado del avance (escala 0-100)
- **Vista global** (página separada): gráfica de área "Avance Global por actividad y sección de Wiki" con 4 categorías de Actividades cruzadas con las subsecciones

### Anatomía del dashboard actual de DocSpaces (Power BI)

Mismo layout pero con acento azul:
- **Gráfica de barras apiladas** "Avance de DocSpaces por Proyecto"
- **Tabla de detalle**: Sección de docSPACE, Status, notas de mejora
- Filtros equivalentes

### ⚠️ Dato pendiente: campo "Actividades"

Los dashboards filtran por un campo "Actividades" con valores: Comunidad, MIC, Proyectos ciudadanos, Sesiones de prototipado. **Este campo no existe en los CSV proporcionados.**

**ACCIÓN PENDIENTE:** Ricardo debe confirmar de dónde viene este campo (probablemente otra pestaña del Google Sheet) y exportarlo para incorporarlo al modelo de datos de la v2.0.

### Lo que se conserva del diseño actual

- Estructura general de filtros + gráficas + tabla de detalle
- Concepto de barras apiladas para vista comparativa
- Gauge de avance por proyecto
- Tabla con notas de mejora
- Vista global de avance por sección

### Lo que mejora en la v2.0

- Un solo portal (1 URL) en vez de 2 dashboards separados
- **Botón de enlace directo a la wiki del proyecto** desde el dashboard
- Navegación entre wikis, docspaces y vistas globales desde el mismo sitio
- Sin licencia Power BI
- Actualización automática de wikis (sin revisión manual)
- Interactividad nativa (Plotly permite hover, zoom, click para filtrar)
- Acceso público sin necesidad de cuenta Microsoft

---

## 2. Arquitectura propuesta

### Stack tecnológico

| Capa | Herramienta | Justificación |
|---|---|---|
| Lenguaje | **Python 3.11+** | Objetivo de aprendizaje + ecosistema de datos |
| Framework web | **Django 5.x** | Batteries-included, ORM, admin panel gratis |
| Base de datos | **SQLite → PostgreSQL** | SQLite para desarrollo, PostgreSQL para producción |
| Gráficas | **Plotly** | Interactivas, open source, se integra con Django |
| API fuente | **MediaWiki API** | API REST nativa de wiki.labnuevoleon.mx |
| Librería Python para wiki | **`requests`** + **`mwparserfromhell`** | requests para llamadas HTTP, mwparserfromhell para parsear wikitext |
| Frontend | **HTML/CSS + Tailwind** | Limpio, responsive, sin dependencias pesadas |
| Automatización | **Django management commands** + **cron** | Scripts programables desde terminal |

### Estructura de carpetas del proyecto

```
/Users/ricardoburnes/Desktop/2026/26_03_Dashboards_LABNL_2.0/
│
├── Bases de datos 1.0/          ← datos históricos (CSV actuales)
│   ├── Diagnóstico_Wikis.csv
│   └── Diagnostico_DOCSPACES.csv
│
├── labnl_dashboards/            ← proyecto Django (se crea en Fase 3)
│   ├── manage.py
│   ├── labnl_dashboards/        ← configuración Django
│   ├── diagnostico/             ← app principal
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── templates/
│   │   └── management/commands/
│   └── requirements.txt
│
├── scripts/                     ← scripts Python de exploración (Fases 1-2)
│   ├── explorar_api.py
│   ├── scraper_wikis.py
│   └── importar_historico.py
│
├── Plan_Dashboards_LABNL_2.0.md ← este documento
└── README.md
```

### Flujo automatizado (meta final)

```
┌─────────────────────────────────────────────────────────┐
│  WIKIS (automatizado)                                    │
│                                                          │
│  cron job (diario/semanal)                               │
│       ↓                                                  │
│  Python script consulta MediaWiki API                    │
│       ↓                                                  │
│  Parsea secciones de cada wiki                           │
│       ↓                                                  │
│  Evalúa 21 criterios (sin Receta) → calcula % avance     │
│       ↓                                                  │
│  Guarda en base de datos Django (SQLite/PostgreSQL)      │
│       ↓                                                  │
│  Portal web muestra dashboards + botón → wiki real       │
│                                                          │
├─────────────────────────────────────────────────────────┤
│  DOCSPACES (semi-automatizado)                           │
│                                                          │
│  Ricardo revisa docspaces físicos                        │
│       ↓                                                  │
│  Registra avance en formulario web (Django admin/form)   │
│       ↓                                                  │
│  Se guarda en la misma base de datos                     │
│       ↓                                                  │
│  Portal web muestra dashboards con Plotly                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Fases del proyecto

### FASE 0 — Planeación y exploración ✅ COMPLETADA

**Responsable:** Claude Cowork
**Duración estimada:** 1 sesión
**Entregables:**
- Este documento de plan
- Análisis de la estructura actual de datos
- Mapeo de endpoints de la MediaWiki API necesarios
- Mockup del dashboard en HTML (prototipo visual)

**¿Por qué Cowork?** Planeación, análisis de datos, documentos, y prototipos visuales rápidos son el fuerte de Cowork.

---

### FASE 1 — Exploración de la MediaWiki API ✅ COMPLETADA

**Responsable:** Claude Code
**Directorio de trabajo:** `/Users/ricardoburnes/Desktop/2026/26_03_Dashboards_LABNL_2.0/scripts/`
**Duración estimada:** 1-2 sesiones
**Objetivo:** Entender qué datos se pueden extraer y cómo

**Tareas:**
1. Crear script `explorar_api.py` que se conecte a `wiki.labnuevoleon.mx/api.php`
2. Listar todas las páginas de proyectos existentes
3. Para un proyecto de prueba, extraer sus secciones y verificar contenido
4. Mapear las 21 subsecciones del CSV (sin Receta) a las secciones reales de la wiki
5. Extraer la `url_wiki` de cada proyecto para el botón de enlace
6. Identificar casos edge (secciones vacías, nombradas diferente, etc.)

**Endpoints clave de MediaWiki API:**
```
action=query&list=allpages          → Listar todas las páginas
action=parse&page=X&prop=sections   → Obtener secciones de una página
action=parse&page=X&prop=wikitext   → Obtener contenido completo
action=query&titles=X&prop=images   → Verificar si tiene imágenes
```

**Lo que aprenderás de Python:** `requests`, JSON, diccionarios, loops, funciones básicas.

---

### FASE 2 — Scraper completo ✅ COMPLETADA

**Responsable:** Claude Code
**Directorio de trabajo:** `/Users/ricardoburnes/Desktop/2026/26_03_Dashboards_LABNL_2.0/scripts/`
**Duración estimada:** 2-3 sesiones
**Objetivo:** Script que evalúe automáticamente todas las wikis

**Tareas:**
1. Script `scraper_wikis.py` que recorra los ~77 proyectos y evalúe las 21 subsecciones
2. Lógica de evaluación: ¿la sección existe? ¿tiene contenido mínimo? → Completa/Incompleta
3. Registro de la URL de la wiki de cada proyecto (para el botón de enlace en el dashboard)
4. Cálculo de % de avance por proyecto
5. Almacenamiento de resultados en CSV
6. Logging y manejo de errores

**Lo que aprenderás de Python:** `pandas`, funciones con retorno, manejo de errores (`try/except`), escritura de archivos.

---

### FASE 3 — Proyecto Django: modelos y admin ✅ COMPLETADA

**Responsable:** Claude Code
**Directorio de trabajo:** `/Users/ricardoburnes/Desktop/2026/26_03_Dashboards_LABNL_2.0/`
**Duración estimada:** 2-3 sesiones
**Objetivo:** Estructura del proyecto web con base de datos

**Tareas:**
1. Crear proyecto Django: `labnl_dashboards`
2. Definir modelos:
   - `Actividad` (nombre: Comunidad / MIC / Proyectos ciudadanos / Sesiones de prototipado)
   - `Proyecto` (nombre, actividad [FK], año_inicio, status_activo, **url_wiki**)
   - `EvaluacionWiki` (proyecto, sección, subsección, status, valor, notas, fecha_evaluación)
   - `EvaluacionDocSpace` (proyecto, sección, status, valor, notas, fecha_evaluación)
3. El campo `url_wiki` en el modelo `Proyecto` alimenta el botón de enlace en el frontend
4. Configurar Django Admin para registro manual de docspaces
5. Management command `python manage.py evaluar_wikis` que ejecute el scraper
6. Script `importar_historico.py` para cargar datos de los CSV actuales

**Lo que aprenderás de Python/Django:** ORM, modelos, migraciones, admin panel, management commands.

---

### FASE 4 — Dashboard web ✅ COMPLETADA (12–13 marzo 2026)

**Responsable:** Claude Code
**Objetivo:** Portal público con gráficas interactivas — todo desde 1 sola URL

**Lo que se construyó:**

| Template | URL | Estado |
|---|---|---|
| `home.html` | `/` | ✅ Cards de acceso a Wikis y DocSpaces |
| `wikis.html` | `/wikis/` | ✅ Filtros + tabla ordenada por avance + gráfica donut |
| `detalle_proyecto.html` | `/wikis/<id>/` | ✅ Acordeón `<details>` por prototipo + gráfica apilada por sección + notas_mejora |
| `docspaces.html` | `/docspaces/` | ✅ Lista expandible con 7 criterios + notas_mejora homologadas |
| `global.html` | `/global/` | ✅ 4 métricas + 2 gráficas horizontales (actividad + sección) |

**Decisiones técnicas adoptadas:**
- Gráficas con **Chart.js** (CDN) en lugar de Plotly — más ligero, sin dependencias Python
- CSS custom (no Tailwind) — sistema de diseño MemoriLABNL: Inter, Space Mono, blanco/gris
- Acordeones con `<details>`/`<summary>` HTML nativo — sin JS extra
- `status_override` como campo "pin" del status manual del CSV: el scraper no lo sobreescribe
- `status_final_cache` como fuente de verdad del dashboard (override > scraper)
- Orden canónico de secciones definido en `views.py`: Prototipo → Aprendizajes → Desarrollo
- Subsección "Continuidad" excluida del cálculo y visualización

**Datos importados:**
- 2,205 evaluaciones wiki (105 prototipos, 73 proyectos) — todas verificadas
- 147 evaluaciones DocSpace (21 proyectos, 7 criterios c/u)

**Comandos nuevos creados:**
- `importar_docspaces` — importa CSV de DocSpaces con mapeo de secciones y corrección de nombres
- `verificar_pendientes` — aprueba en lote evaluaciones del scraper sin pasar por admin

**Bugs resueltos:**
- Wikis mostraban datos parciales → causa: filtro `verificado=True` ocultaba datos del scraper no revisados en admin → solución: quitar filtro, usar `status_final_cache`
- DocSpaces sin datos → causa: CSV nunca importado → solución: comando `importar_docspaces`
- Gráficas Chart.js crecían al infinito → causa: canvas sin contenedor de altura fija → solución: wrapper `position: relative; height: Npx`
- `update_or_create` no recalculaba `status_final_cache` → causa: usa SQL UPDATE, no llama `save()` → solución: bulk update con F expressions al final del import

**Mejoras de UX (13 marzo 2026):**
- `detalle_proyecto.html`: barra de avance total del proyecto en el header (calculado en `views.py` como promedio de prototipos)
- `wikis.html`: stats completas/incompletas/vacías movidas a Vista Global; reemplazadas por texto instructivo "Selecciona tu iniciativa…"; columnas Proyecto/Actividad/Prototipos/Avance ahora son clicables para ordenar (sorting client-side JS)
- `global.html`: nueva sección "Estado de subsecciones Wiki" con leyenda y gráfica donut
- Entorno virtual (`venv/`) configurado con `requirements.txt` — base para despliegue

---

### FASE 5 — Deploy open source ✅ COMPLETADA (19 marzo 2026)

**Responsable:** Claude Code
**Objetivo:** Portal público en internet con código abierto

**Lo que se hizo:**

| Tarea | Estado |
|---|---|
| `.gitignore` + `requirements.txt` + `.env.example` | ✅ |
| `settings.py` con `python-decouple` + WhiteNoise | ✅ |
| Repo público en GitHub: `documentacionlabnl/dashboards_wiki-docspace` | ✅ |
| LICENSE MIT | ✅ |
| Deploy en PythonAnywhere (free tier) | ✅ |
| Archivos estáticos servidos con WhiteNoise | ✅ |
| Base de datos SQLite subida con datos reales | ✅ |

**Decisiones técnicas:**
- **PythonAnywhere** sobre Railway/Render/Fly.io — filesystem persistente = SQLite funciona sin migrar a PostgreSQL
- **Django 5.2 LTS** en lugar de 6.0 — PythonAnywhere free tier tiene Python 3.10, Django 6.0 requiere 3.12+
- **WhiteNoise** para archivos estáticos — 1 línea de middleware, sin configurar Nginx
- **python-decouple** para variables de entorno — 1 import, 1 función
- **Sin Docker, sin CI/CD, sin Celery** — `git pull` + Reload es suficiente para un solo developer

**URL pública:** `documentacionlabnl.pythonanywhere.com`

**Limitación conocida:** El free tier de PythonAnywhere no incluye scheduled tasks ni HTTP saliente libre. El scraper se ejecuta manualmente desde la consola Bash. Ver `SCRAPER.md` para instrucciones.

---

### FASE 6 — Iteración y mejoras (Cowork + Claude Code)

**Responsable:** Ambos
**Objetivo:** Refinar con base en uso real

**Mejoras implementadas (23 marzo 2026):**
- ✅ **Inline de DocSpaces en admin:** Al editar un Proyecto en Django Admin, se ven las 7 evaluaciones DocSpace en una tabla editable (sin ir una por una)
- ✅ **Columna DocSpaces en lista de Proyectos:** Muestra cuántas evaluaciones DocSpace tiene cada proyecto para identificar rápido cuáles tienen y cuáles no
- ✅ **Filtro `--actividad` en el scraper:** `python manage.py evaluar_wikis --actividad Comunidad` permite correr el scraper solo para un tipo de actividad

**Mejoras implementadas (20 abril 2026):**
- ✅ **Aviso "Actualizado…" refleja edits manuales:** Antes la fecha salía de `ActualizacionDashboard` (solo se creaba tras correr el scraper). Ahora se calcula desde un nuevo campo `updated_at` en `EvaluacionWiki` y `EvaluacionDocSpace`, que se actualiza **únicamente** al editar desde el Django Admin (directo o inline). Imports y scraper no lo tocan.
- **Implementación:** Migración `0002` agrega `updated_at` (nullable). `admin.py` setea la fecha en `save_model` y `save_formset`. `views.py::_contexto_base` hace `Max("updated_at")` de ambos modelos.
- **Estado inicial:** todos los `updated_at` arrancan en `NULL` → el aviso queda oculto hasta el primer edit manual.

**Posibles mejoras futuras:**
- Histórico de avance (gráfica de progreso en el tiempo)
- Exportar reportes en PDF
- Comparativa entre periodos
- API pública para consumir los datos
- Formulario web dedicado para DocSpaces (reemplazar Django admin)

---

## 4. División de responsabilidades

### ¿Qué hace Cowork (Claude en modo escritorio)?

| Tarea | Fase |
|---|---|
| Planeación y documentación del proyecto | 0 |
| Análisis exploratorio de los CSV actuales | 0 |
| Mockups HTML del dashboard | 0, 4 |
| Prototipos visuales de gráficas | 4 |
| Revisión de diseño y UX | 4 |
| Documentación de usuario final | 6 |
| Análisis de datos y reportes puntuales | Cualquiera |

### ¿Qué hace Claude Code?

| Tarea | Fase |
|---|---|
| Exploración interactiva de la MediaWiki API | 1 |
| Escribir el scraper en Python | 1, 2 |
| Crear el proyecto Django completo | 3 |
| Modelos, vistas, templates | 3, 4 |
| Integración de Plotly + botón wiki | 4 |
| Testing y debugging | 2-5 |
| Configuración de cron/automatización | 5 |
| Despliegue a servidor | 5 |
| Refactoring y optimización | 6 |

### ¿Por qué esta división?

**Cowork** es ideal para trabajo de documentos, análisis visual, y prototipado rápido. Funciona en un entorno aislado sin acceso persistente al sistema de archivos — perfecto para planear y diseñar, pero no para mantener un proyecto de código vivo.

**Claude Code** opera directamente en la terminal y el sistema de archivos de Ricardo. Puede crear proyectos en `/Users/ricardoburnes/Desktop/2026/26_03_Dashboards_LABNL_2.0`, instalar dependencias, correr servidores locales, ejecutar tests, y hacer commits a git. Es donde vive el código real del proyecto.

---

## 5. Estimación de tiempo

| Fase | Sesiones estimadas | Herramienta |
|---|---|---|
| 0 - Planeación | 1 | Cowork |
| 1 - Exploración API | 1-2 | Claude Code |
| 2 - Scraper completo | 2-3 | Claude Code |
| 3 - Django + modelos | 2-3 | Claude Code |
| 4 - Dashboard + Plotly | 2-3 | Claude Code + Cowork |
| 5 - Automatización + deploy | 1-2 | Claude Code |
| 6 - Iteración | Continua | Ambos |
| **Total** | **~10-15 sesiones** | |

---

## 6. Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| La API de MediaWiki tiene rate limits | Media | Implementar delays entre llamadas, cachear resultados |
| Las secciones de la wiki no coinciden 1:1 con los criterios del CSV | Alta | Mapeo manual en Fase 1, regex flexible |
| Algunos proyectos tienen nombres diferentes en wiki vs CSV | Media | Crear diccionario de mapeo de nombres |
| URL de la wiki no siempre predecible (tildes, espacios) | Media | Usar el campo `fullurl` de la API, no construir la URL manualmente |
| Django es complejo para un principiante | Baja | Claude Code guía paso a paso; Django Admin simplifica mucho |
| DocSpaces no se pueden automatizar | Certeza | Formulario web amigable para captura manual rápida |
| Campo "Actividades" faltante en los datos | Alta | ⚠️ Pendiente que Ricardo confirme la fuente de este campo |

---

## 7. Acciones pendientes antes de pasar a Claude Code

- [ ] **Ricardo:** Confirmar y exportar el campo "Actividades" (Comunidad, MIC, Proyectos ciudadanos, Sesiones de prototipado) y la relación de cada proyecto con su actividad
- [ ] **Ricardo:** Confirmar si la carpeta del proyecto ya tiene una estructura inicial o si Claude Code parte de cero
- [ ] **Cowork (opcional):** Generar mockup HTML del portal antes de codificar

---

## 8. Próximo paso inmediato

**Ahora mismo en Cowork podemos:**
1. Crear un mockup HTML del dashboard propuesto (con el botón "Ver wiki →" incluido)
2. Hacer un análisis exploratorio de los datos actuales (% de avance por proyecto desde los CSV)

**Cuando pasemos a Claude Code:**
```bash
cd /Users/ricardoburnes/Desktop/2026/26_03_Dashboards_LABNL_2.0
mkdir scripts
cd scripts
# Crear primer script: explorar_api.py
```

---

*Este plan es un documento vivo — versión 1.5, Marzo 2026.*
