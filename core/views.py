from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from decimal import Decimal, InvalidOperation
import pandas as pd

from .models import Proyecto, Cuadrilla, Integrante, CambioCuadrilla, SolicitudReasignacion
from .services import DashboardStatsService

# ======================
# PÁGINA PRINCIPAL
# ======================
@login_required
def index(request):
    dashboard_service = DashboardStatsService()
    context = dashboard_service.get_dashboard_context()
    return render(request, "core/index.html", context)


# ======================
# PROYECTO
# ======================
@login_required
def proyecto_view(request):
    if request.method == "POST":
        presupuesto_raw = request.POST.get("presupuesto", "0").strip() or "0"
        try:
            presupuesto = Decimal(presupuesto_raw)
        except (InvalidOperation, ValueError):
            messages.error(request, "El presupuesto debe ser un número válido.")
            return redirect("proyecto")

        fecha_inicio_raw = request.POST.get("fecha_inicio")
        fecha_termino_raw = request.POST.get("fecha_termino")
        fecha_inicio = timezone.now().date()
        fecha_termino = None
        try:
            if fecha_inicio_raw:
                fecha_inicio = timezone.datetime.strptime(fecha_inicio_raw, "%Y-%m-%d").date()
                # Validar que la fecha de inicio no sea anterior a la fecha actual
                if fecha_inicio < timezone.now().date():
                    messages.error(request, "La fecha de inicio no puede ser anterior a la fecha actual.")
                    return redirect("proyecto")
            if fecha_termino_raw:
                fecha_termino = timezone.datetime.strptime(fecha_termino_raw, "%Y-%m-%d").date()
                # Validar que la fecha de término no sea anterior a la fecha de inicio
                if fecha_termino < fecha_inicio:
                    messages.error(request, "La fecha de término no puede ser anterior a la fecha de inicio.")
                    return redirect("proyecto")
        except ValueError:
            messages.error(request, "Formato de fecha inválido. Use AAAA-MM-DD.")
            return redirect("proyecto")

        nombre = request.POST.get("nombre", "").strip()
        # Validación: evitar nombres duplicados (case-insensitive)
        if Proyecto.objects.filter(nombre__iexact=nombre).exists():
            messages.error(request, "Ya existe un proyecto con ese nombre. Elija otro nombre.")
            return redirect("proyecto")

        Proyecto.objects.create(
            nombre=nombre,
            cliente=request.POST.get("cliente", "").strip(),
            estado=request.POST.get("estado", "planificado"),
            fecha_inicio=fecha_inicio,
            fecha_termino=fecha_termino,
            presupuesto=presupuesto,
            direccion=request.POST.get("direccion", "").strip(),
            ciudad=request.POST.get("ciudad", "").strip(),
            descripcion=request.POST.get("descripcion", "").strip(),
        )
        messages.success(request, "✅ Proyecto registrado correctamente.")
        return redirect("proyecto")

    proyectos = Proyecto.objects.all()
    return render(request, "core/proyecto.html", {"proyectos": proyectos})


@login_required
def eliminar_proyecto(request, codigo):
    proyecto = get_object_or_404(Proyecto, codigo=codigo)
    if request.method == "POST":
        proyecto.delete()
        messages.success(request, "✅ Proyecto eliminado correctamente.")
    return redirect("proyecto")


@login_required
def editar_proyecto(request, codigo):
    proyecto = get_object_or_404(Proyecto, codigo=codigo)
    
    if request.method == "POST":
        # Validar nombre único (excluyendo el proyecto actual)
        nombre = request.POST.get("nombre", "").strip()
        if nombre and Proyecto.objects.filter(nombre__iexact=nombre).exclude(codigo=codigo).exists():
            messages.error(request, "Ya existe otro proyecto con ese nombre.")
            return redirect("editar_proyecto", codigo=codigo)
        
        # Actualizar campos
        proyecto.nombre = nombre
        proyecto.cliente = request.POST.get("cliente", "").strip()
        proyecto.estado = request.POST.get("estado", proyecto.estado)
        
        # Validar fechas
        try:
            fecha_inicio = request.POST.get("fecha_inicio")
            if fecha_inicio:
                proyecto.fecha_inicio = fecha_inicio
            
            fecha_termino = request.POST.get("fecha_termino")
            if fecha_termino:
                proyecto.fecha_termino = fecha_termino
                if proyecto.fecha_inicio and proyecto.fecha_termino and proyecto.fecha_termino < proyecto.fecha_inicio:
                    messages.error(request, "La fecha de término no puede ser anterior a la de inicio.")
                    return redirect("editar_proyecto", codigo=codigo)
        except ValueError:
            messages.error(request, "Las fechas ingresadas no son válidas.")
            return redirect("editar_proyecto", codigo=codigo)
        
        # Presupuesto
        try:
            presupuesto = request.POST.get("presupuesto", "0")
            if presupuesto:
                presupuesto = Decimal(presupuesto)
                if presupuesto <= 0:
                    messages.error(request, "El presupuesto debe ser mayor a 0.")
                    return redirect("editar_proyecto", codigo=codigo)
                proyecto.presupuesto = presupuesto
        except (ValueError, InvalidOperation):
            messages.error(request, "El presupuesto debe ser un número válido.")
            return redirect("editar_proyecto", codigo=codigo)
        
        proyecto.direccion = request.POST.get("direccion", "").strip()
        proyecto.ciudad = request.POST.get("ciudad", "").strip()
        proyecto.descripcion = request.POST.get("descripcion", "").strip()
        
        proyecto.save()
        messages.success(request, "✅ Proyecto actualizado correctamente.")
        return redirect("proyecto")
    
    context = {
        'proyecto': proyecto,
        'estados': Proyecto.ESTADO_CHOICES,
    }
    return render(request, 'core/editar_proyecto.html', context)


def registrar_cambio(cuadrilla, accion, descripcion):
    """
    Helper centralizado para registrar cualquier alteración a las cuadrillas.
    """
    if not cuadrilla:
        return
    CambioCuadrilla.objects.create(
        cuadrilla=cuadrilla,
        accion=accion,
        descripcion=descripcion.strip()
    )


# ======================
# CUADRILLA
# ======================

@login_required
def cuadrilla_view(request):
    proyectos = Proyecto.objects.all()
    cuadrillas = Cuadrilla.objects.select_related("proyecto", "trabajador").prefetch_related("integrantes").all()
    historial = CambioCuadrilla.objects.select_related("cuadrilla").order_by("-fecha")[:5]

    cuadrilla = None  # Para edición en el mismo form
    integrantes_qs = Integrante.objects.select_related("cuadrilla", "usuario").order_by("nombre_trabajador", "apellido_trabajador", "usuario__first_name", "usuario__last_name")
    integrantes_form = integrantes_qs.filter(cuadrilla__isnull=True)
    integrantes_cuadrilla_ids = set()
    integrantes_reubicables = integrantes_qs.filter(cuadrilla__isnull=False)

    if request.method == "POST":
        editar_id = request.POST.get("editar_cuadrilla")
        if editar_id:
            cuadrilla = get_object_or_404(Cuadrilla, id=editar_id)
            integrantes_form = integrantes_qs.filter(Q(cuadrilla__isnull=True) | Q(cuadrilla=cuadrilla))
            integrantes_cuadrilla_ids = set(cuadrilla.integrantes.values_list("id", flat=True))
        else:
            accion = request.POST.get("accion", "guardar")
            if accion == "reubicar":
                integrante_id = request.POST.get("integrante_id")
                destino_id = request.POST.get("cuadrilla_destino")
                if not integrante_id or not destino_id:
                    messages.error(request, "Debe seleccionar el trabajador y la cuadrilla destino.")
                    return redirect("cuadrilla")
                integrante = get_object_or_404(Integrante, id=integrante_id)
                destino = get_object_or_404(Cuadrilla, id=destino_id)
                origen = integrante.cuadrilla
                if origen == destino:
                    messages.info(request, "El trabajador ya pertenece a la cuadrilla seleccionada.")
                    return redirect("cuadrilla")
                integrante.cuadrilla = destino
                integrante.estado = 'asignado'
                integrante.save()
                descripcion = f"{integrante.nombre} fue reasignado"
                if origen:
                    descripcion += f" desde {origen.nombre}"
                descripcion += f" a {destino.nombre}."
                registrar_cambio(destino, "reasignacion", descripcion)
                messages.success(request, "✅ Trabajador reasignado correctamente.")
                return redirect("cuadrilla")

            # Crear o actualizar cuadrilla
            nombre = request.POST.get("nombre", "").strip()
            proyecto_id = request.POST.get("proyecto")
            estado = request.POST.get("estado", "activa")
            integrantes_ids = request.POST.getlist("integrantes")
            cuadrilla_id = request.POST.get("cuadrilla_id")

            if not nombre:
                messages.error(request, "Debe indicar el nombre de la cuadrilla.")
                return redirect("cuadrilla")
            if not proyecto_id:
                messages.error(request, "Debe seleccionar un proyecto.")
                return redirect("cuadrilla")

            # Validaciones: nombre único y un proyecto sólo puede tener una cuadrilla
            # Excluir la cuadrilla actual (si se está editando)
            existing_nombre_qs = Cuadrilla.objects.filter(nombre__iexact=nombre)
            if cuadrilla_id:
                existing_nombre_qs = existing_nombre_qs.exclude(id=cuadrilla_id)
            if existing_nombre_qs.exists():
                messages.error(request, "Ya existe una cuadrilla con ese nombre. Elija otro nombre.")
                return redirect("cuadrilla")

            # Nota: permitimos múltiples cuadrillas por proyecto — no validar proyecto único
            # Nota: La creación de trabajadores nuevos se ha movido a la vista específica
            # `agregar_trabajador`. Si se envían campos de trabajadores nuevos aquí,
            # pedir al usuario que use la vista dedicada.
            nombres_nuevos = request.POST.getlist("nombre_trabajador_nuevo")
            apellidos_nuevos = request.POST.getlist("apellido_trabajador_nuevo")
            cargos_nuevos = request.POST.getlist("cargo_trabajador_nuevo")
            trabajadores_nuevos_presentes = any(x.strip() for x in nombres_nuevos + apellidos_nuevos + cargos_nuevos)

            if not integrantes_ids and not trabajadores_nuevos_presentes:
                messages.error(request, "Debe seleccionar al menos un integrante o crear un trabajador nuevo.")
                return redirect("cuadrilla")
            if trabajadores_nuevos_presentes:
                messages.info(request, "Para agregar trabajadores sin usuario, use la página 'Agregar Trabajador'.")
                return redirect('agregar_trabajador')

            cargo_validos = dict(Integrante.CARGO_CHOICES).keys()
            estado_validos = dict(Integrante.ESTADO_CHOICES).keys()
            integrantes_payload = []
            for integrante_id in integrantes_ids:
                integrante = get_object_or_404(Integrante, id=integrante_id)
                # No permitir seleccionar trabajadores que estén en licencia
                if integrante.estado == 'licencia' and not (cuadrilla and integrante.cuadrilla and integrante.cuadrilla.id == cuadrilla.id):
                    messages.error(request, f"No se puede seleccionar a {integrante.get_nombre_completo()} porque está en licencia.")
                    return redirect("cuadrilla")
                rol = request.POST.get(f"rol_{integrante_id}", integrante.cargo)
                estado_trabajador = request.POST.get(f"estado_{integrante_id}", 'asignado')
                if rol not in cargo_validos:
                    messages.error(request, f"El rol seleccionado para {integrante.nombre} no es válido.")
                    return redirect("cuadrilla")
                if estado_trabajador not in estado_validos:
                    messages.error(request, f"El estado seleccionado para {integrante.nombre} no es válido.")
                    return redirect("cuadrilla")
                integrantes_payload.append((integrante, rol, estado_trabajador))

            crear = False
            with transaction.atomic():
                if cuadrilla_id:
                    cuadrilla = get_object_or_404(Cuadrilla, id=cuadrilla_id)
                    cuadrilla.nombre = nombre
                    cuadrilla.proyecto_id = proyecto_id
                    cuadrilla.estado = estado
                    cuadrilla.save()
                else:
                    cuadrilla = Cuadrilla.objects.create(
                        nombre=nombre,
                        proyecto_id=proyecto_id,
                        estado=estado
                    )
                    crear = True

                seleccionados = set(integrantes_ids)
                for integrante in cuadrilla.integrantes.all():
                    if str(integrante.id) not in seleccionados:
                        integrante.cuadrilla = None
                        integrante.estado = 'disponible'
                        integrante.save()

                integrantes_resumen = []
                lider_asignado = None
                lideres_count = 0

                # Procesar integrantes existentes
                for integrante, rol, estado_trabajador in integrantes_payload:
                    # Manejo especial: si se está marcando a un trabajador registrado en 'licencia',
                    # exigir rango de fechas y evitar que sea Felipe Chamorro.
                    if estado_trabajador == 'licencia' and integrante.usuario:
                        # Verificar nombre Felipe Chamorro
                        user = integrante.usuario
                        if (user.first_name == 'Felipe' and user.last_name == 'Chamorro') or integrante.get_nombre_completo() == 'Felipe Chamorro':
                            messages.error(request, f"El usuario {integrante.get_nombre_completo()} no puede ser puesto en licencia.")
                            return redirect('cuadrilla')

                        inicio = request.POST.get(f"licencia_inicio_{integrante.id}")
                        fin = request.POST.get(f"licencia_fin_{integrante.id}")
                        if not inicio or not fin:
                            messages.error(request, f"Debe indicar rango de fecha de licencia para {integrante.get_nombre_completo()}.")
                            return redirect('cuadrilla')
                        try:
                            fecha_inicio = timezone.datetime.strptime(inicio, "%Y-%m-%d").date()
                            fecha_fin = timezone.datetime.strptime(fin, "%Y-%m-%d").date()
                        except ValueError:
                            messages.error(request, f"Formato de fecha inválido para licencia de {integrante.get_nombre_completo()}.")
                            return redirect('cuadrilla')
                        if fecha_inicio < timezone.now().date():
                            messages.error(request, "La fecha de inicio de la licencia debe ser a partir de la fecha actual.")
                            return redirect('cuadrilla')
                        if fecha_fin < fecha_inicio:
                            messages.error(request, "La fecha de fin de la licencia no puede ser anterior a la fecha de inicio.")
                            return redirect('cuadrilla')
                        integrante.licencia_inicio = fecha_inicio
                        integrante.licencia_fin = fecha_fin
                        estado_final = 'licencia'
                    else:
                        estado_final = estado_trabajador if estado_trabajador != 'disponible' else 'asignado'

                    integrante.cargo = rol
                    integrante.estado = estado_final
                    integrante.cuadrilla = cuadrilla
                    integrante.save()
                    integrantes_resumen.append(
                        f"{integrante.nombre} ({integrante.get_cargo_display()} · {integrante.get_estado_display()})"
                    )
                    if rol == 'lider':
                        lideres_count += 1
                        lider_asignado = integrante
                
                # Validar que solo haya un líder por cuadrilla
                if lideres_count > 1:
                    messages.error(request, "Solo se permite un líder de cuadrilla por cuadrilla.")
                    return redirect("cuadrilla")
                if lideres_count == 0:
                    messages.error(request, "Debe asignar un líder de cuadrilla.")
                    return redirect("cuadrilla")
                
                # Asignar el líder a la cuadrilla
                if lider_asignado:
                    cuadrilla.trabajador = lider_asignado
                    cuadrilla.save()

                accion_log = "creacion" if crear else "actualizacion"
                descripcion = f"Cuadrilla {'creada' if crear else 'actualizada'}: {nombre}. "
                descripcion += "Integrantes: " + ", ".join(integrantes_resumen)
                registrar_cambio(cuadrilla, accion_log, descripcion)

            messages.success(request, "✅ Cuadrilla registrada correctamente." if crear else "✅ Cuadrilla actualizada correctamente.")
            return redirect("cuadrilla")

    if cuadrilla and not integrantes_cuadrilla_ids:
        integrantes_cuadrilla_ids = set(cuadrilla.integrantes.values_list("id", flat=True))
    if cuadrilla:
        integrantes_form = integrantes_qs.filter(Q(cuadrilla__isnull=True) | Q(cuadrilla=cuadrilla))

    return render(request, "core/cuadrilla.html", {
        "proyectos": proyectos,
        "integrantes_form": integrantes_form,
        "integrantes_reubicables": integrantes_reubicables,
        "integrantes_cuadrilla_ids": integrantes_cuadrilla_ids,
        "cuadrillas": cuadrillas,
        "cuadrilla": cuadrilla,
        "historial": historial,
        "cargo_choices": Integrante.CARGO_CHOICES,
        "estado_choices": Integrante.ESTADO_CHOICES,
    })



# ======================
# VER UNA CUADRILLA
# ======================
@login_required
def ver_cuadrilla(request, cuadrilla_id):
    cuadrilla = get_object_or_404(Cuadrilla, id=cuadrilla_id)
    return render(request, "core/ver_cuadrilla.html", {"cuadrilla": cuadrilla})


# ======================
# EDITAR CUADRILLA
# ======================

@login_required
def editar_cuadrilla(request, cuadrilla_id):
    cuadrilla = get_object_or_404(Cuadrilla, id=cuadrilla_id)
    proyectos = Proyecto.objects.all()
    integrantes_disponibles = Integrante.objects.filter(cuadrilla__isnull=True) | cuadrilla.integrantes.all()

    if request.method == "POST":
        cuadrilla.nombre = request.POST.get("nombre", "").strip()
        cuadrilla.proyecto_id = request.POST.get("proyecto")
        cuadrilla.estado = request.POST.get("estado", "activa")
        # Validaciones: evitar duplicados de nombre y de proyecto
        if Cuadrilla.objects.filter(nombre__iexact=cuadrilla.nombre).exclude(id=cuadrilla.id).exists():
            messages.error(request, "Ya existe una cuadrilla con ese nombre. Elija otro nombre.")
            return redirect('editar_cuadrilla', cuadrilla_id=cuadrilla.id)
        # Permitimos múltiples cuadrillas por proyecto — no validar proyecto único

        cuadrilla.save()

        seleccionados_ids = request.POST.getlist("integrantes")
        # Quitar integrantes no seleccionados
        for integrante in cuadrilla.integrantes.all():
            if str(integrante.id) not in seleccionados_ids:
                integrante.cuadrilla = None
                integrante.save()
        # Asignar integrantes seleccionados
        for integrante_id in seleccionados_ids:
            integrante = Integrante.objects.get(id=integrante_id)
            # No permitir agregar a la cuadrilla un trabajador que esté en licencia
            if integrante.estado == 'licencia' and not (integrante.cuadrilla and integrante.cuadrilla.id == cuadrilla.id):
                messages.error(request, f"No se puede seleccionar a {integrante.get_nombre_completo()} porque está en licencia.")
                return redirect('editar_cuadrilla', cuadrilla_id=cuadrilla.id)
            # Si se coloca en licencia a un usuario registrado, validar fechas y proteger a Felipe Chamorro
            estado_trabajador = request.POST.get(f"estado_{integrante_id}", integrante.estado)
            if estado_trabajador == 'licencia' and integrante.usuario:
                user = integrante.usuario
                if (user.first_name == 'Felipe' and user.last_name == 'Chamorro') or integrante.get_nombre_completo() == 'Felipe Chamorro':
                    messages.error(request, f"El usuario {integrante.get_nombre_completo()} no puede ser puesto en licencia.")
                    return redirect('editar_cuadrilla', cuadrilla_id=cuadrilla.id)

                inicio = request.POST.get(f"licencia_inicio_{integrante_id}")
                fin = request.POST.get(f"licencia_fin_{integrante_id}")
                if not inicio or not fin:
                    messages.error(request, f"Debe indicar rango de fecha de licencia para {integrante.get_nombre_completo()}.")
                    return redirect('editar_cuadrilla', cuadrilla_id=cuadrilla.id)
                try:
                    fecha_inicio = timezone.datetime.strptime(inicio, "%Y-%m-%d").date()
                    fecha_fin = timezone.datetime.strptime(fin, "%Y-%m-%d").date()
                except ValueError:
                    messages.error(request, f"Formato de fecha inválido para licencia de {integrante.get_nombre_completo()}.")
                    return redirect('editar_cuadrilla', cuadrilla_id=cuadrilla.id)
                if fecha_inicio < timezone.now().date():
                    messages.error(request, "La fecha de inicio de la licencia debe ser a partir de la fecha actual.")
                    return redirect('editar_cuadrilla', cuadrilla_id=cuadrilla.id)
                if fecha_fin < fecha_inicio:
                    messages.error(request, "La fecha de fin de la licencia no puede ser anterior a la fecha de inicio.")
                    return redirect('editar_cuadrilla', cuadrilla_id=cuadrilla.id)
                integrante.licencia_inicio = fecha_inicio
                integrante.licencia_fin = fecha_fin
                integrante.estado = 'licencia'

            integrante.cuadrilla = cuadrilla
            integrante.save()

        messages.success(request, "✅ Cuadrilla actualizada correctamente.")
        return redirect("cuadrilla")

    return render(request, "core/cuadrilla_form.html", {
        "cuadrilla": cuadrilla,
        "proyectos": proyectos,
        "integrantes_disponibles": integrantes_disponibles,
    })


@login_required
def agregar_trabajador(request):
    """Vista para agregar un trabajador sin usuario (operario/ayudante/supervisor)."""
    if request.method == 'POST':
        nombre = request.POST.get('nombre_trabajador', '').strip()
        apellido = request.POST.get('apellido_trabajador', '').strip()
        cargo = request.POST.get('cargo', 'operario')
        especialidad = request.POST.get('especialidad', 'otro') # Default to otro
        cuadrilla_id = request.POST.get('cuadrilla')

        if not nombre or not apellido:
            messages.error(request, 'Debe indicar nombre y apellido.')
            return redirect('agregar_trabajador')

        cuadrilla = None
        if cuadrilla_id:
            cuadrilla = get_object_or_404(Cuadrilla, id=cuadrilla_id)

        integrante = Integrante.objects.create(
            nombre_trabajador=nombre,
            apellido_trabajador=apellido,
            cargo=cargo,
            especialidad=especialidad,
            cuadrilla=cuadrilla,
            estado='asignado' if cuadrilla else 'disponible'
        )
        messages.success(request, f"✅ Trabajador {integrante.get_nombre_completo()} creado correctamente.")
        return redirect('cuadrilla')

    proyectos = Proyecto.objects.all()
    cuadrillas = Cuadrilla.objects.all()
    return render(request, 'core/trabajador_form.html', {'cuadrillas': cuadrillas, 'proyectos': proyectos})


@login_required
def eliminar_integrante(request, integrante_id):
    integrante = get_object_or_404(Integrante, id=integrante_id)
    if integrante.usuario is not None:
        messages.error(request, 'Solo se pueden eliminar trabajadores sin usuario desde esta acción.')
        return redirect('cuadrilla')
    if request.method == 'POST':
        integrante.delete()
        messages.success(request, '✅ Trabajador eliminado correctamente.')
    return redirect('cuadrilla')


# ======================
# ELIMINAR CUADRILLA
# ======================

@login_required
def eliminar_cuadrilla(request, cuadrilla_id):
    from .models import CambioCuadrilla
    cuadrilla = get_object_or_404(Cuadrilla, id=cuadrilla_id)
    if request.method == "POST":
        # Registrar eliminación en cambios de cuadrilla
        integrantes_cantidad = cuadrilla.integrantes.count()
        lider_nombre = cuadrilla.trabajador.get_nombre_completo() if cuadrilla.trabajador else "Sin líder"
        
        CambioCuadrilla.objects.create(
            cuadrilla=cuadrilla,
            accion='eliminacion',
            descripcion=f"Cuadrilla eliminada. Líder: {lider_nombre}. Integrantes desasignados: {integrantes_cantidad}. Eliminado por: {request.user.username}"
        )
        
        # Desasignar integrantes
        for integrante in cuadrilla.integrantes.all():
            integrante.cuadrilla = None
            integrante.save()
        
        cuadrilla.delete()
        messages.success(request, "✅ Cuadrilla eliminada correctamente y registrada en cambios.")
    return redirect("cuadrilla")


# ======================
# EXPORTAR PROYECTOS A EXCEL
# ======================
@login_required
def reasignacion_view(request):
    """
    Vista para gestionar reasignaciones de trabajadores con sistema de solicitudes.
    """
    trabajadores = Integrante.objects.select_related("cuadrilla", "usuario").filter(cuadrilla__isnull=False)
    trabajadores_noasignados = Integrante.objects.select_related("usuario").filter(cuadrilla__isnull=True)
    cuadrillas = Cuadrilla.objects.select_related("proyecto").all()
    solicitudes = SolicitudReasignacion.objects.select_related(
        "trabajador", "cuadrilla_origen", "cuadrilla_destino", "respondido_por"
    ).order_by("-fecha_solicitud")[:5]

    # Flag informativo para la plantilla (sin filtrar resultados)
    user_is_lider = bool(
        request.user.is_authenticated
        and hasattr(request.user, 'perfil')
        and request.user.perfil.rol == 'lider_cuadrilla'
    )
    
    if request.method == "POST":
        accion = request.POST.get("accion")
        
        if accion == "crear_solicitud":
            trabajador_id = request.POST.get("trabajador_id")
            cuadrilla_destino_id = request.POST.get("cuadrilla_destino")
            motivo = request.POST.get("motivo", "").strip()
            
            if not trabajador_id or not cuadrilla_destino_id:
                messages.error(request, "Debe seleccionar el trabajador y la cuadrilla destino.")
                return redirect("reasignacion")
            
            trabajador = get_object_or_404(Integrante, id=trabajador_id)
            cuadrilla_destino = get_object_or_404(Cuadrilla, id=cuadrilla_destino_id)
            cuadrilla_origen = trabajador.cuadrilla
            
            if not cuadrilla_origen:
                messages.error(request, "El trabajador no está asignado a ninguna cuadrilla.")
                return redirect("reasignacion")
            
            if cuadrilla_origen == cuadrilla_destino:
                messages.info(request, "El trabajador ya pertenece a la cuadrilla seleccionada.")
                return redirect("reasignacion")
            
            # Verificar si ya existe una solicitud pendiente
            solicitud_existente = SolicitudReasignacion.objects.filter(
                trabajador=trabajador,
                cuadrilla_destino=cuadrilla_destino,
                estado='pendiente'
            ).first()
            
            if solicitud_existente:
                messages.info(request, "Ya existe una solicitud pendiente para este trabajador y cuadrilla.")
                return redirect("reasignacion")
            
            SolicitudReasignacion.objects.create(
                trabajador=trabajador,
                cuadrilla_origen=cuadrilla_origen,
                cuadrilla_destino=cuadrilla_destino,
                motivo=motivo
            )
            messages.success(request, "✅ Solicitud de reasignación enviada correctamente. Se enviará un correo electrónico con el detalle.")
            return redirect("reasignacion")

        elif accion == "agregar_noasignado":
            trabajador_id = request.POST.get("trabajador_id")
            cuadrilla_destino_id = request.POST.get("cuadrilla_destino")

            if not trabajador_id or not cuadrilla_destino_id:
                messages.error(request, "Debe seleccionar el trabajador y la cuadrilla destino.")
                return redirect("reasignacion")

            trabajador = get_object_or_404(Integrante, id=trabajador_id)
            cuadrilla_destino = get_object_or_404(Cuadrilla, id=cuadrilla_destino_id)

            if trabajador.cuadrilla is not None:
                messages.error(request, "El trabajador ya está asignado a una cuadrilla.")
                return redirect("reasignacion")

            trabajador.cuadrilla = cuadrilla_destino
            trabajador.estado = 'asignado'
            trabajador.save()

            descripcion = f"{trabajador.get_nombre_completo()} fue agregado a {cuadrilla_destino.nombre} desde estado no asignado."
            registrar_cambio(cuadrilla_destino, "agregar_noasignado", descripcion)

            messages.success(request, "✅ Trabajador no asignado agregado correctamente a la cuadrilla.")
            return redirect("reasignacion")
        
        elif accion == "responder_solicitud":
            solicitud_id = request.POST.get("solicitud_id")
            respuesta = request.POST.get("respuesta")  # 'aceptar' o 'rechazar'
            
            if not solicitud_id or not respuesta:
                messages.error(request, "Datos inválidos.")
                return redirect("reasignacion")
            
            solicitud = get_object_or_404(SolicitudReasignacion, id=solicitud_id)
            
            if not request.user.is_authenticated:
                messages.error(request, "Debe iniciar sesión para responder solicitudes.")
                return redirect("reasignacion")
            
            if solicitud.estado != 'pendiente':
                messages.info(request, "Esta solicitud ya fue respondida.")
                return redirect("reasignacion")
            
            cuadrilla_destino = solicitud.cuadrilla_destino
            if respuesta == 'aceptar':
                solicitud.estado = 'aceptada'
                solicitud.respondido_por = request.user
                solicitud.fecha_respuesta = timezone.now()
                solicitud.save()
                
                # Realizar la reasignación
                trabajador = solicitud.trabajador
                trabajador.cuadrilla = cuadrilla_destino
                trabajador.estado = 'asignado'
                trabajador.save()
                
                descripcion = f"{trabajador.get_nombre_completo()} fue reasignado desde {solicitud.cuadrilla_origen.nombre} a {cuadrilla_destino.nombre} (solicitud aceptada)."
                registrar_cambio(cuadrilla_destino, "reasignacion", descripcion)
                
                messages.success(request, "✅ Solicitud aceptada y trabajador reasignado correctamente.")
            else:
                solicitud.estado = 'rechazada'
                solicitud.respondido_por = request.user
                solicitud.fecha_respuesta = timezone.now()
                solicitud.save()
                messages.info(request, "Solicitud rechazada.")
            
            return redirect("reasignacion")
    
    return render(request, "core/reasignacion.html", {
        "trabajadores": trabajadores,
        "cuadrillas": cuadrillas,
        "solicitudes": solicitudes,
        "user_is_lider": user_is_lider,
        "trabajadores_noasignados": trabajadores_noasignados,
    })


@login_required
def historial_cambios_view(request):
    """Vista completa del historial de cambios de cuadrillas."""
    historial = CambioCuadrilla.objects.select_related("cuadrilla").order_by("-fecha")
    return render(request, "core/historial_cambios.html", {
        "historial": historial,
    })


@login_required
def exportar_excel(request):
    from datetime import datetime
    
    proyectos = Proyecto.objects.all().values(
        "nombre",
        "cliente",
        "estado",
        "fecha_inicio",
        "fecha_termino",
        "presupuesto",
        "direccion",
        "ciudad",
        "descripcion"
    )

    df = pd.DataFrame(proyectos)

    if not df.empty:
        for col in ["fecha_inicio", "fecha_termino"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%d/%m/%Y")

    df.rename(columns={
        "nombre": "Nombre del Proyecto",
        "cliente": "Cliente",
        "estado": "Estado",
        "fecha_inicio": "Fecha de Inicio",
        "fecha_termino": "Fecha de Término",
        "presupuesto": "Presupuesto ($)",
        "direccion": "Dirección",
        "ciudad": "Ciudad",
        "descripcion": "Descripción"
    }, inplace=True)

    df.fillna("—", inplace=True)

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    response["Content-Disposition"] = f'attachment; filename="proyectos_{timestamp}.xlsx"'
    df.to_excel(response, index=False, sheet_name="Proyectos")
    return response


@login_required
def exportar_cuadrillas_excel(request):
    from datetime import datetime
    
    cuadrillas = Cuadrilla.objects.select_related("proyecto", "trabajador").all()
    
    data = []
    for cuadrilla in cuadrillas:
        data.append({
            "nombre": cuadrilla.nombre,
            "proyecto": cuadrilla.proyecto.nombre,
            "estado": cuadrilla.get_estado_display(),
            "lider": cuadrilla.trabajador.get_nombre_completo() if cuadrilla.trabajador else "Sin líder",
            "integrantes": cuadrilla.integrantes.count(),
        })
    
    df = pd.DataFrame(data)

    df.rename(columns={
        "nombre": "Nombre de Cuadrilla",
        "proyecto": "Proyecto",
        "estado": "Estado",
        "lider": "Líder",
        "integrantes": "Cantidad de Integrantes"
    }, inplace=True)

    df.fillna("—", inplace=True)

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    response["Content-Disposition"] = f'attachment; filename="cuadrillas_{timestamp}.xlsx"'
    df.to_excel(response, index=False, sheet_name="Cuadrillas")
    return response


