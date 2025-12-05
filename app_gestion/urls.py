from django.contrib import admin
from django.urls import path, include
from core import views

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Usuarios
    path('usuarios/', include('usuarios.urls')),

    # Página principal
    path('', views.index, name='index'),

    # Proyectos
    path('proyecto/', views.proyecto_view, name='proyecto'),
    path('proyecto/editar/<int:codigo>/', views.editar_proyecto, name='editar_proyecto'),
    path('proyecto/eliminar/<int:codigo>/', views.eliminar_proyecto, name='eliminar_proyecto'),

    # Cuadrillas
    path('cuadrilla/', views.cuadrilla_view, name='cuadrilla'),
    path('cuadrilla/ver/<int:cuadrilla_id>/', views.ver_cuadrilla, name='ver_cuadrilla'),
    path('cuadrilla/editar/<int:cuadrilla_id>/', views.editar_cuadrilla, name='editar_cuadrilla'),
    path('cuadrilla/eliminar/<int:cuadrilla_id>/', views.eliminar_cuadrilla, name='eliminar_cuadrilla'),
    path('cuadrilla/historial/', views.historial_cambios_view, name='historial_cambios'),
    path('integrante/agregar/', views.agregar_trabajador, name='agregar_trabajador'),
    path('integrante/eliminar/<int:integrante_id>/', views.eliminar_integrante, name='eliminar_integrante'),

    # Reasignación
    path('reasignacion/', views.reasignacion_view, name='reasignacion'),

    # Exportar Excel
    path('exportar_excel/', views.exportar_excel, name='exportar_excel'),
    path('exportar_cuadrillas/', views.exportar_cuadrillas_excel, name='exportar_cuadrillas'),
]
