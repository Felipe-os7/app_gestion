from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import CambioCuadrilla


class Command(BaseCommand):
    help = 'Elimina los cambios de cuadrilla que tienen 5 días o más de antigüedad'

    def handle(self, *args, **options):
        # Calcular la fecha límite 
        fecha_limite = timezone.now() - timedelta(days=5)
        
        # Contar cambios a eliminar
        cambios_a_eliminar = CambioCuadrilla.objects.filter(fecha__lt=fecha_limite)
        cantidad = cambios_a_eliminar.count()
        
        if cantidad > 0:
            cambios_a_eliminar.delete()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Se eliminaron {cantidad} cambios con más de 5 días de antigüedad')
            )
        else:
            self.stdout.write(
                self.style.WARNING('No hay cambios para eliminar')
            )
