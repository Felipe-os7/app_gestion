from django.contrib import admin
from .models import Proyecto, Cuadrilla, Integrante, CambioCuadrilla


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "cliente", "estado", "fecha_inicio")
    list_filter = ("estado", "fecha_inicio")
    search_fields = ("nombre", "cliente", "descripcion")


@admin.register(Cuadrilla)
class CuadrillaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "proyecto", "estado")
    list_filter = ("estado", "proyecto")
    search_fields = ("nombre",)


@admin.register(Integrante)
class IntegranteAdmin(admin.ModelAdmin):
    list_display = ("get_nombre", "cargo", "estado", "cuadrilla", "fecha_actualizacion")
    list_filter = ("cargo", "estado", "cuadrilla")
    search_fields = ("usuario__username", "usuario__first_name", "usuario__last_name", "usuario__email")
    
    def get_nombre(self, obj):
        """Retorna el nombre del integrante."""
        return obj.nombre
    get_nombre.short_description = "Nombre"


@admin.register(CambioCuadrilla)
class CambioCuadrillaAdmin(admin.ModelAdmin):
    list_display = ("cuadrilla", "accion", "fecha")
    list_filter = ("accion", "fecha")
    search_fields = ("cuadrilla__nombre", "descripcion")