# Dashboards Documentación LABNL 2.0
## Idea Previa

---

### ¿Qué es este proyecto?

Un portal web público donde ciudadanos puedan consultar el avance de los proyectos documentados en la Wiki de LABNL, con gráficas interactivas, filtros y buscador — como reemplazo y evolución de los dashboards actuales en Power BI.

---

### Problema que resuelve

Actualmente el flujo de actualización de dashboards es manual:

1. Revisar datos en la Wiki de LABNL
2. Actualizar manualmente Google Sheets
3. Refrescar Power BI Desktop
4. Publicar los cambios

El objetivo es automatizar todo ese flujo y ofrecer un portal más accesible, flexible y sin costos de licencia.

---

### Stack tecnológico

| Herramienta | Rol |
|---|---|
| **Python** | Lógica, datos y automatización |
| **Django** | Framework del portal web |
| **MediaWiki API** | Fuente de datos (Wiki de LABNL) |
| **Plotly** | Gráficas interactivas |
| **HTML / CSS** | Apariencia del portal |

Todo el stack es **100% open source**.

---

### Usuarios

Ciudadanos en general (portal público).

---

### Funcionalidades del portal

- Ver avances de proyectos
- Filtrar por tipo de proyecto
- Ver gráficas e indicadores
- Buscar proyectos específicos
- Revisar mejoras pendientes por wiki

---

### Flujo automatizado (meta)

```
Wiki LABNL (MediaWiki API)
        ↓
    Python extrae y procesa datos
        ↓
    Django sirve el portal web
        ↓
    Ciudadanos consultan en tiempo real
```

---

### Herramientas por etapa

| Etapa | Herramienta |
|---|---|
| Planeación y dudas conceptuales | Claude.ai |
| Construcción del código | Claude Code |
| Automatización de tareas | Claude Cowork |

---

### Próximos pasos

- [ ] Definir estructura de carpetas del proyecto en Claude Code
- [ ] Identificar qué datos exactos se extraerán de la Wiki
- [ ] Diseñar las vistas principales del portal
- [ ] Construir el primer prototipo local con Django

---

*Proyecto iniciado: Marzo 2026*
