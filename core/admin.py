from django.contrib import admin
from .models import Proyecto, Cuadrilla, Integrante, SolicitudReasignacion, CambioCuadrilla


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "cliente", "estado", "fecha_inicio")
    list_filter = ("estado", "fecha_inicio")
    search_fields = ("nombre", "cliente", "descripcion")


@admin.register(Cuadrilla)
class CuadrillaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "proyecto", "trabajador", "estado")
    list_filter = ("estado", "proyecto")
    search_fields = ("nombre",)


@admin.register(Integrante)
class IntegranteAdmin(admin.ModelAdmin):
    list_display = ("get_nombre", "cargo", "estado", "cuadrilla", "fecha_actualizacion")
    list_filter = ("cargo", "estado", "cuadrilla")
    search_fields = ("usuario__username", "usuario__first_name", "usuario__last_name", "usuario__email", "nombre_trabajador", "apellido_trabajador")
    
    def get_nombre(self, obj):
        """Retorna el nombre del integrante."""
        return obj.get_nombre_completo()
    get_nombre.short_description = "Nombre"


@admin.register(CambioCuadrilla)
class CambioCuadrillaAdmin(admin.ModelAdmin):
    list_display = ("cuadrilla", "accion", "fecha")
    list_filter = ("accion", "fecha")
    search_fields = ("cuadrilla__nombre", "descripcion")


@admin.register(SolicitudReasignacion)
class SolicitudReasignacionAdmin(admin.ModelAdmin):
    list_display = ("trabajador", "cuadrilla_origen", "cuadrilla_destino", "estado", "fecha_solicitud")
    list_filter = ("estado", "fecha_solicitud")
    search_fields = ("trabajador__nombre_trabajador", "trabajador__apellido_trabajador", "cuadrilla_origen__nombre", "cuadrilla_destino__nombre")
    readonly_fields = ("fecha_solicitud", "fecha_respuesta", "respondido_por")