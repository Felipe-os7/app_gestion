from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import SolicitudReasignacion


class Command(BaseCommand):
    help = "Elimina solicitudes de reasignación con más de 1 día de antigüedad"

    def handle(self, *args, **options):
        # Fecha límite: solicitudes anteriores a 1 día
        fecha_limite = timezone.now() - timedelta(days=1)
        qs = SolicitudReasignacion.objects.filter(fecha_solicitud__lt=fecha_limite)
        cantidad = qs.count()

        if cantidad:
            qs.delete()
            self.stdout.write(self.style.SUCCESS(f"✓ Se eliminaron {cantidad} solicitudes de reasignación antiguas"))
        else:
            self.stdout.write(self.style.WARNING("No hay solicitudes de reasignación antiguas para eliminar"))
