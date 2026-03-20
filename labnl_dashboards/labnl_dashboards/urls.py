from django.contrib import admin
from django.urls import path
from diagnostico import views

admin.site.site_header = "LABNL — Panel de verificación"
admin.site.site_title = "LABNL Admin"
admin.site.index_title = "Panel de verificación"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("wikis/", views.wikis, name="wikis"),
    path("wikis/<int:proyecto_id>/", views.detalle_proyecto, name="detalle_proyecto"),
    path("docspaces/", views.docspaces, name="docspaces"),
    path("global/", views.vista_global, name="vista_global"),
]
