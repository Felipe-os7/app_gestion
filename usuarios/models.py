from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class PerfilUsuario(models.Model):
    """
    Perfil extendido del usuario que incluye el rol dentro del sistema.
    """
    ROL_CHOICES = [
        ('lider_cuadrilla', 'Líder de Cuadrilla'),
        ('supervisor', 'Supervisor'),
    ]
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('suspendido', 'Suspendido'),
    ]

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    rol = models.CharField(
        "Rol en el sistema",
        max_length=20,
        choices=ROL_CHOICES,
        default='lider_cuadrilla'
    )
    estado = models.CharField(
        "Estado de la cuenta",
        max_length=15,
        choices=ESTADO_CHOICES,
        default='activo'
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"
        ordering = ["-fecha_registro"]

    def __str__(self):
        return f"{self.usuario.username} - {self.get_rol_display()}"

    @receiver(post_save, sender=User)
    def crear_perfil_usuario(sender, instance, created, **kwargs):
        """
        Crea automáticamente un perfil cuando se crea un nuevo usuario.
        """
        if created:
            PerfilUsuario.objects.get_or_create(usuario=instance)
