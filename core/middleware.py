"""
Middleware para verificar la integridad de la sesión del usuario.
Si se detectan cambios en el usuario (como desactivación, eliminación, etc.),
la sesión se cierra automáticamente por seguridad.
"""

import hashlib
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.urls import reverse
from usuarios.models import PerfilUsuario
from core.models import Integrante


class SessionSecurityMiddleware:
    """
    Middleware que verifica la integridad de la sesión del usuario.
    
    Si el usuario ha sido modificado, desactivado o eliminado desde que inició sesión,
    la sesión se cierra automáticamente por seguridad.
    
    Utiliza un hash de los datos críticos del usuario almacenado en la sesión
    para detectar cambios.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def _get_user_hash(self, user):
        """
        Genera un hash de los datos críticos del usuario para detectar cambios.
        Incluye el estado del perfil y del integrante.
        """
        critical_data = f"{user.pk}:{user.username}:{user.is_active}:{user.is_superuser}:{user.is_staff}"

        # Estado del perfil
        try:
            perfil = PerfilUsuario.objects.get(usuario=user)
            critical_data += f":{perfil.estado}:{perfil.rol}"
        except PerfilUsuario.DoesNotExist:
            critical_data += ":no_perfil"

        # Estado del integrante
        try:
            integrante = Integrante.objects.get(usuario=user)
            critical_data += f":{integrante.estado}:{integrante.cargo}"
        except Integrante.DoesNotExist:
            critical_data += ":no_integrante"

        return hashlib.md5(critical_data.encode()).hexdigest()

    def __call__(self, request):

        # ❗ IMPORTANTE: Ignorar /admin para que no redirija al login de la app
        if request.path.startswith('/admin'):
            return self.get_response(request)
        
        # Ignorar actualizaciones de cuadrilla para evitar redirección al login
        if request.path.startswith('/cuadrilla') and request.method == 'POST':
            # No verificar hash cuando se actualiza una cuadrilla
            response = self.get_response(request)
            # Actualizar el hash después de la respuesta para evitar problemas
            if request.user.is_authenticated:
                try:
                    current_user = User.objects.get(pk=request.user.pk)
                    request.session['user_security_hash'] = self._get_user_hash(current_user)
                except:
                    pass
            return response

        # Solo verificar si el usuario está autenticado
        if request.user.is_authenticated:
            try:
                current_user = User.objects.get(pk=request.user.pk)

                if not current_user.is_active:
                    logout(request)
                    if hasattr(request, 'session'):
                        request.session.flush()
                    return redirect('login')

                # Verificar perfil
                try:
                    perfil = PerfilUsuario.objects.get(usuario=current_user)
                    if perfil.estado != 'activo':
                        logout(request)
                        if hasattr(request, 'session'):
                            request.session.flush()
                        return redirect('login')
                except PerfilUsuario.DoesNotExist:
                    logout(request)
                    if hasattr(request, 'session'):
                        request.session.flush()
                    return redirect('login')

                # Verificar integrante
                try:
                    integrante = Integrante.objects.get(usuario=current_user)
                    if integrante.estado == 'suspendido':
                        logout(request)
                        if hasattr(request, 'session'):
                            request.session.flush()
                        return redirect('login')
                except Integrante.DoesNotExist:
                    pass

                # Verificar hash
                current_hash = self._get_user_hash(current_user)
                stored_hash = request.session.get('user_security_hash')

                if stored_hash is None:
                    request.session['user_security_hash'] = current_hash
                elif stored_hash != current_hash:
                    logout(request)
                    if hasattr(request, 'session'):
                        request.session.flush()
                    return redirect('login')

                # Verificación adicional de username
                if request.user.username != current_user.username:
                    logout(request)
                    if hasattr(request, 'session'):
                        request.session.flush()
                    return redirect('login')

                request.user = current_user

            except User.DoesNotExist:
                logout(request)
                if hasattr(request, 'session'):
                    request.session.flush()
                return redirect('login')

            except Exception:
                logout(request)
                if hasattr(request, 'session'):
                    request.session.flush()
                return redirect('login')

        return self.get_response(request)
