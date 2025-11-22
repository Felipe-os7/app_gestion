from threading import Lock
from django.db.models import Count, Q

from .models import Proyecto, Cuadrilla, Integrante


class SingletonMeta(type):
    """
    Metaclase para crear singletons thread-safe.
    """

    _instances = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        # Garantiza que solo se cree una instancia incluso en entornos multi-hilo.
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class DashboardStatsService(metaclass=SingletonMeta):
    """
    Servicio centralizado para obtener datos y métricas del dashboard.
    Implementado como singleton para reutilizar la misma instancia y facilitar
    la incorporación de cachés o mecanismos de memoización en el futuro.
    """

    def get_collections(self):
        proyectos = Proyecto.objects.all()
        cuadrillas = Cuadrilla.objects.select_related("proyecto").prefetch_related("integrantes")
        integrantes = Integrante.objects.select_related("cuadrilla")
        return proyectos, cuadrillas, integrantes

    def get_summary(self, proyectos, cuadrillas, integrantes):
        resumen_proyectos = proyectos.aggregate(
            total=Count("codigo"),
            planificados=Count("codigo", filter=Q(estado="planificado")),
            en_progreso=Count("codigo", filter=Q(estado="en_progreso")),
            completados=Count("codigo", filter=Q(estado="completado")),
            cancelados=Count("codigo", filter=Q(estado="cancelado")),
        )
        resumen_cuadrillas = cuadrillas.aggregate(
            total=Count("id"),
            activas=Count("id", filter=Q(estado="activa")),
            inactivas=Count("id", filter=Q(estado="inactiva")),
        )
        resumen_integrantes = integrantes.aggregate(
            total=Count("id"),
            asignados=Count("id", filter=Q(cuadrilla__isnull=False)),
            sin_cuadrilla=Count("id", filter=Q(cuadrilla__isnull=True)),
        )
        return {
            "proyectos": resumen_proyectos,
            "cuadrillas": resumen_cuadrillas,
            "integrantes": resumen_integrantes,
        }

    def get_dashboard_context(self):
        proyectos, cuadrillas, integrantes = self.get_collections()
        resumen = self.get_summary(proyectos, cuadrillas, integrantes)
        return {
            "proyectos": proyectos,
            "cuadrillas": cuadrillas,
            "integrantes": integrantes,
            "resumen": resumen,
        }

