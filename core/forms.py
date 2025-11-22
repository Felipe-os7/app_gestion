from django import forms
from .models import Proyecto, Cuadrilla

class ProyectoForm(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = ['nombre', 'cliente', 'estado', 'fecha_inicio', 'fecha_termino',
                  'presupuesto', 'direccion', 'ciudad', 'descripcion']

class CuadrillaForm(forms.ModelForm):
    class Meta:
        model = Cuadrilla
        fields = ['nombre', 'proyecto', 'estado']
