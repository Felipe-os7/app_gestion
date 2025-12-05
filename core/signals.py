from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import CambioCuadrilla


@receiver(post_save, sender=CambioCuadrilla)
def limpiar_cambios_antiguos(sender, instance, created, **kwargs):
    """
    Elimina automáticamente los cambios con más de 5 días de antigüedad
    cada vez que se crea uno nuevo
    """
    if created:
        fecha_limite = timezone.now() - timedelta(days=5)
        CambioCuadrilla.objects.filter(fecha__lt=fecha_limite).delete()
