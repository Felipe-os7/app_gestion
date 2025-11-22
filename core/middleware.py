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
        # Campos críticos que si cambian, deberían cerrar la sesión
        critical_data = f"{user.pk}:{user.username}:{user.is_active}:{user.is_superuser}:{user.is_staff}"
        
        # Agregar estado del perfil
        try:
            perfil = PerfilUsuario.objects.get(usuario=user)
            critical_data += f":{perfil.estado}:{perfil.rol}"
        except PerfilUsuario.DoesNotExist:
            critical_data += ":no_perfil"
        
        # Agregar estado del integrante
        try:
            integrante = Integrante.objects.get(usuario=user)
            critical_data += f":{integrante.estado}:{integrante.cargo}"
        except Integrante.DoesNotExist:
            critical_data += ":no_integrante"
        
        return hashlib.md5(critical_data.encode()).hexdigest()

    def __call__(self, request):
        # Solo verificar si el usuario está autenticado
        if request.user.is_authenticated:
            try:
                # Obtener el usuario actual desde la base de datos
                current_user = User.objects.get(pk=request.user.pk)
                
                # Verificar si el usuario está activo
                if not current_user.is_active:
                    # Usuario desactivado, cerrar sesión
                    logout(request)
                    if hasattr(request, 'session'):
                        request.session.flush()
                    return redirect('login')
                
                # Verificar estado del perfil
                try:
                    perfil = PerfilUsuario.objects.get(usuario=current_user)
                    if perfil.estado != 'activo':
                        # Perfil inactivo o suspendido, cerrar sesión
                        logout(request)
                        if hasattr(request, 'session'):
                            request.session.flush()
                        return redirect('login')
                except PerfilUsuario.DoesNotExist:
                    # No tiene perfil, cerrar sesión por seguridad
                    logout(request)
                    if hasattr(request, 'session'):
                        request.session.flush()
                    return redirect('login')
                
                # Verificar estado del integrante (si existe)
                try:
                    integrante = Integrante.objects.get(usuario=current_user)
                    if integrante.estado == 'suspendido':
                        # Integrante suspendido, cerrar sesión
                        logout(request)
                        if hasattr(request, 'session'):
                            request.session.flush()
                        return redirect('login')
                except Integrante.DoesNotExist:
                    # No tiene integrante, pero puede seguir usando la app
                    pass
                
                # Calcular hash actual del usuario
                current_hash = self._get_user_hash(current_user)
                
                # Obtener hash almacenado en la sesión (si existe)
                stored_hash = request.session.get('user_security_hash')
                
                # Si no hay hash almacenado, es una sesión nueva, guardarlo
                if stored_hash is None:
                    request.session['user_security_hash'] = current_hash
                # Si el hash cambió, significa que el usuario fue modificado
                elif stored_hash != current_hash:
                    # Los datos críticos del usuario cambiaron, cerrar sesión por seguridad
                    logout(request)
                    if hasattr(request, 'session'):
                        request.session.flush()
                    return redirect('login')
                
                # Verificar si el username cambió (doble verificación)
                stored_user = request.user
                if stored_user.username != current_user.username:
                    logout(request)
                    if hasattr(request, 'session'):
                        request.session.flush()
                    return redirect('login')
                
                # Actualizar el objeto user en la request con los datos más recientes
                # Esto asegura que siempre tengamos la versión más actualizada
                request.user = current_user
                
            except User.DoesNotExist:
                # El usuario fue eliminado, cerrar sesión
                logout(request)
                if hasattr(request, 'session'):
                    request.session.flush()
                return redirect('login')
            except Exception as e:
                # En caso de cualquier error, por seguridad cerramos la sesión
                logout(request)
                if hasattr(request, 'session'):
                    request.session.flush()
                return redirect('login')

        response = self.get_response(request)
        return response

