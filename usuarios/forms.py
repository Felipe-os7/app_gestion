from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import PerfilUsuario
from core.models import Integrante
from django import forms
from django.contrib.auth.forms import AuthenticationForm


class CustomAuthenticationForm(AuthenticationForm):
    """Bloquea el login de usuarios que estén en licencia."""
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        try:
            integrante = user.integrante
            if integrante.estado == 'licencia':
                raise forms.ValidationError(
                    "Tu cuenta se encuentra en licencia y no puede iniciar sesión.",
                    code='inactive',
                )
        except Integrante.DoesNotExist:
            pass


class RegistroUsuarioForm(UserCreationForm):
    """
    Formulario de registro de usuarios con selección de rol.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa tu correo electrónico'
        }),
        label="Correo electrónico"
    )
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa tu nombre'
        }),
        label="Nombre"
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa tu apellido'
        }),
        label="Apellido"
    )
    rol = forms.ChoiceField(
        choices=[('lider_cuadrilla', 'Líder de Cuadrilla')],
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label="Rol en el sistema",
        help_text="Solo se permite registro como Líder de Cuadrilla",
        initial='lider_cuadrilla'
    )
    cargo = forms.ChoiceField(
        choices=[('lider', 'Líder de cuadrilla')],
        required=False,
        widget=forms.HiddenInput(),
        initial='lider'
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'rol')

    def clean_username(self):
        username = self.cleaned_data['username']
        if not self.validar_rut(username):
            raise forms.ValidationError("El nombre de usuario debe ser un RUT chileno válido (formato: 12345678-9)")
        return username

    @staticmethod
    def validar_rut(rut):
        """
        Valida el RUT chileno (formato: XXXXXXXX-Y)
        """
        import re
        rut = rut.replace(".", "").replace("-", "-")
        match = re.match(r'^([0-9]{7,8})-([0-9Kk])$', rut)
        if not match:
            return False
        cuerpo, dv = match.groups()
        suma = 0
        multiplo = 2
        for c in reversed(cuerpo):
            suma += int(c) * multiplo
            multiplo = 9 if multiplo == 7 else multiplo + 1
            if multiplo > 7:
                multiplo = 2
        resto = suma % 11
        dv_calculado = 11 - resto
        if dv_calculado == 11:
            dv_final = '0'
        elif dv_calculado == 10:
            dv_final = 'K'
        else:
            dv_final = str(dv_calculado)
        return dv_final.lower() == dv.lower()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Ingresa tu RUT(ej: 12345678-9)'
        })
        self.fields['username'].help_text = 'El nombre de usuario debe ser un RUT válido (ejemplo: 12345678-9) y se usará para iniciar sesión.'
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Ingresa tu contraseña'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirma tu contraseña'
        })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            # Crear o actualizar el perfil con el rol seleccionado (solo lider_cuadrilla)
            perfil, created = PerfilUsuario.objects.get_or_create(usuario=user)
            perfil.rol = 'lider_cuadrilla'  # Forzar a lider_cuadrilla
            perfil.save()
            
            # Crear el Integrante asociado (solo líder de cuadrilla)
            Integrante.objects.get_or_create(
                usuario=user,
                defaults={
                    'cargo': 'lider',  # Solo líder de cuadrilla
                    'estado': 'disponible'
                }
            )
        
        return user

