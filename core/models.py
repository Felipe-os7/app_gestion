from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Proyecto(models.Model):
    ESTADO_CHOICES = [
        ('planificado', 'Planificado'),
        ('en_progreso', 'En progreso'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    ]

    codigo = models.AutoField(primary_key=True)
    nombre = models.CharField("Nombre del proyecto", max_length=100)
    cliente = models.CharField("Cliente", max_length=100)
    estado = models.CharField("Estado", max_length=20, choices=ESTADO_CHOICES, default='planificado')
    fecha_inicio = models.DateField("Fecha de inicio", default=timezone.now)
    fecha_termino = models.DateField("Fecha de término", null=True, blank=True)
    presupuesto = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    direccion = models.CharField("Dirección", max_length=255)
    ciudad = models.CharField("Ciudad", max_length=100)
    descripcion = models.TextField("Descripción", blank=True)

    class Meta:
        verbose_name = "Proyecto"
        verbose_name_plural = "Proyectos"
        ordering = ["-fecha_inicio"]

    def __str__(self):
        return self.nombre


class Cuadrilla(models.Model):
    ESTADO_CHOICES = [
        ('activa', 'Activa'),
        ('inactiva', 'Inactiva'),
    ]

    nombre = models.CharField("Nombre de la cuadrilla", max_length=100)
    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.CASCADE,
        related_name="cuadrillas",  
        verbose_name="Proyecto asignado"
    )
    estado = models.CharField("Estado", max_length=10, choices=ESTADO_CHOICES, default='activa')
    trabajador = models.ForeignKey(
        'Integrante',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cuadrillas_lideradas",
        verbose_name="Líder de cuadrilla",
        limit_choices_to={'cargo': 'lider'}
    )

    class Meta:
        verbose_name = "Cuadrilla"
        verbose_name_plural = "Cuadrillas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

class Integrante(models.Model):
    CARGO_CHOICES = [
        ('operario', 'Operario'),
        ('ayudante', 'Ayudante'),
        ('supervisor', 'Supervisor'),
        ('lider', 'Líder de cuadrilla'),
    ]
    ESTADO_CHOICES = [
        ('disponible', 'Disponible'),
        ('asignado', 'Asignado'),
        ('licencia', 'En licencia'),
        ('suspendido', 'Suspendido'),
    ]

    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="integrante",
        verbose_name="Usuario",
        null=True,
        blank=True
    )
    nombre_trabajador = models.CharField("Nombre", max_length=100, blank=True)
    apellido_trabajador = models.CharField("Apellido", max_length=100, blank=True)
    cargo = models.CharField("Cargo", max_length=20, choices=CARGO_CHOICES)
    cuadrilla = models.ForeignKey(
        'Cuadrilla',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="integrantes"
    )
    estado = models.CharField("Estado del trabajador", max_length=15, choices=ESTADO_CHOICES, default='disponible')
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    notas = models.TextField("Notas internas", blank=True)

    class Meta:
        verbose_name = "Integrante"
        verbose_name_plural = "Integrantes"
        ordering = ["nombre_trabajador", "apellido_trabajador", "usuario__first_name", "usuario__last_name"]

    def get_nombre_completo(self):
        """Retorna el nombre completo del trabajador."""
        if self.usuario:
            return self.usuario.get_full_name() or self.usuario.username
        else:
            return f"{self.nombre_trabajador} {self.apellido_trabajador}".strip() or "Sin nombre"

    @property
    def nombre(self):
        """Retorna el nombre completo del trabajador (compatibilidad)."""
        return self.get_nombre_completo()

    def __str__(self):
        return f"{self.get_nombre_completo()} — {self.get_cargo_display()}"


class CambioCuadrilla(models.Model):
    ACCION_CHOICES = [
        ('creacion', 'Creación'),
        ('actualizacion', 'Actualización'),
        ('reasignacion', 'Reasignación'),
        ('estado', 'Cambio de estado'),
    ]

    cuadrilla = models.ForeignKey(Cuadrilla, on_delete=models.CASCADE, related_name="cambios")
    accion = models.CharField("Tipo de acción", max_length=20, choices=ACCION_CHOICES)
    descripcion = models.TextField("Detalle del cambio")
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cambio de cuadrilla"
        verbose_name_plural = "Cambios de cuadrilla"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.get_accion_display()} · {self.cuadrilla.nombre} ({self.fecha:%d/%m %H:%M})"


class SolicitudReasignacion(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aceptada', 'Aceptada'),
        ('rechazada', 'Rechazada'),
    ]

    trabajador = models.ForeignKey(
        Integrante,
        on_delete=models.CASCADE,
        related_name="solicitudes_reasignacion",
        verbose_name="Trabajador"
    )
    cuadrilla_origen = models.ForeignKey(
        Cuadrilla,
        on_delete=models.CASCADE,
        related_name="solicitudes_salida",
        verbose_name="Cuadrilla origen"
    )
    cuadrilla_destino = models.ForeignKey(
        Cuadrilla,
        on_delete=models.CASCADE,
        related_name="solicitudes_entrada",
        verbose_name="Cuadrilla destino"
    )
    estado = models.CharField("Estado", max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    motivo = models.TextField("Motivo de la solicitud", blank=True)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)
    respondido_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_respondidas",
        verbose_name="Respondido por"
    )

    class Meta:
        verbose_name = "Solicitud de Reasignación"
        verbose_name_plural = "Solicitudes de Reasignación"
        ordering = ["-fecha_solicitud"]

    def __str__(self):
        return f"Solicitud de {self.trabajador.get_nombre_completo()} - {self.get_estado_display()}"
