from django.contrib import admin
from .models import PerfilUsuario


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rol', 'fecha_registro', 'fecha_actualizacion')
    list_filter = ('rol', 'fecha_registro')
    search_fields = ('usuario__username', 'usuario__email', 'usuario__first_name', 'usuario__last_name')
    readonly_fields = ('fecha_registro', 'fecha_actualizacion')
    fieldsets = (
        ('Información del Usuario', {
            'fields': ('usuario',)
        }),
        ('Rol en el Sistema', {
            'fields': ('rol',)
        }),
        ('Fechas', {
            'fields': ('fecha_registro', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
