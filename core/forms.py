from django import forms
from .models import Proyecto, Cuadrilla

class ProyectoForm(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = ['nombre', 'cliente', 'estado', 'fecha_inicio', 'fecha_termino',
                  'presupuesto', 'direccion', 'ciudad', 'descripcion']
    
    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        # Si estamos editando, excluir el proyecto actual de la validación
        qs = Proyecto.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise forms.ValidationError('Ya existe un proyecto con este nombre. Los nombres de proyectos deben ser únicos.')
        return nombre

class CuadrillaForm(forms.ModelForm):
    class Meta:
        model = Cuadrilla
        fields = ['nombre', 'proyecto', 'estado']

