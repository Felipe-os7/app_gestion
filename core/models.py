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
        verbose_name="Usuario"
    )
    cargo = models.CharField("Cargo", max_length=20, choices=CARGO_CHOICES)
    cuadrilla = models.ForeignKey(
        Cuadrilla,
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
        ordering = ["usuario__first_name", "usuario__last_name"]

    @property
    def nombre(self):
        """Retorna el nombre completo del usuario asociado."""
        return self.usuario.get_full_name() or self.usuario.username

    def __str__(self):
        return f"{self.nombre} — {self.get_cargo_display()}"


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
