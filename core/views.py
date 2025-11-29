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

        Proyecto.objects.create(
            nombre=request.POST.get("nombre", "").strip(),
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
    historial = CambioCuadrilla.objects.select_related("cuadrilla").order_by("-fecha")[:10]

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
            # Verificar si se están creando trabajadores nuevos sin usuario
            trabajadores_nuevos = []
            nombres_nuevos = request.POST.getlist("nombre_trabajador_nuevo")
            apellidos_nuevos = request.POST.getlist("apellido_trabajador_nuevo")
            cargos_nuevos = request.POST.getlist("cargo_trabajador_nuevo")
            
            for i in range(len(nombres_nuevos)):
                if nombres_nuevos[i].strip() and apellidos_nuevos[i].strip() and cargos_nuevos[i]:
                    trabajadores_nuevos.append({
                        'nombre': nombres_nuevos[i].strip(),
                        'apellido': apellidos_nuevos[i].strip(),
                        'cargo': cargos_nuevos[i]
                    })
            
            if not integrantes_ids and not trabajadores_nuevos:
                messages.error(request, "Debe seleccionar al menos un integrante o crear un trabajador nuevo.")
                return redirect("cuadrilla")

            cargo_validos = dict(Integrante.CARGO_CHOICES).keys()
            estado_validos = dict(Integrante.ESTADO_CHOICES).keys()
            integrantes_payload = []
            for integrante_id in integrantes_ids:
                integrante = get_object_or_404(Integrante, id=integrante_id)
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
                
                # Crear trabajadores nuevos sin usuario
                for trabajador_nuevo in trabajadores_nuevos:
                    cargo_trab = trabajador_nuevo['cargo']
                    if cargo_trab == 'lider':
                        lideres_count += 1
                    nuevo_integrante = Integrante.objects.create(
                        nombre_trabajador=trabajador_nuevo['nombre'],
                        apellido_trabajador=trabajador_nuevo['apellido'],
                        cargo=cargo_trab,
                        cuadrilla=cuadrilla,
                        estado='asignado'
                    )
                    integrantes_resumen.append(
                        f"{nuevo_integrante.get_nombre_completo()} ({nuevo_integrante.get_cargo_display()} · {nuevo_integrante.get_estado_display()})"
                    )
                    if cargo_trab == 'lider':
                        lider_asignado = nuevo_integrante
                
                # Procesar integrantes existentes
                for integrante, rol, estado_trabajador in integrantes_payload:
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

def editar_cuadrilla(request, cuadrilla_id):
    cuadrilla = get_object_or_404(Cuadrilla, id=cuadrilla_id)
    proyectos = Proyecto.objects.all()
    integrantes_disponibles = Integrante.objects.filter(cuadrilla__isnull=True) | cuadrilla.integrantes.all()

    if request.method == "POST":
        cuadrilla.nombre = request.POST.get("nombre", "").strip()
        cuadrilla.proyecto_id = request.POST.get("proyecto")
        cuadrilla.estado = request.POST.get("estado", "activa")
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
            integrante.cuadrilla = cuadrilla
            integrante.save()

        messages.success(request, "✅ Cuadrilla actualizada correctamente.")
        return redirect("cuadrilla")

    return render(request, "core/cuadrilla_form.html", {
        "cuadrilla": cuadrilla,
        "proyectos": proyectos,
        "integrantes_disponibles": integrantes_disponibles,
    })


# ======================
# ELIMINAR CUADRILLA
# ======================

def eliminar_cuadrilla(request, cuadrilla_id):
    cuadrilla = get_object_or_404(Cuadrilla, id=cuadrilla_id)
    if request.method == "POST":
        for integrante in cuadrilla.integrantes.all():
            integrante.cuadrilla = None
            integrante.save()
        cuadrilla.delete()
        messages.success(request, "✅ Cuadrilla eliminada correctamente.")
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
    cuadrillas = Cuadrilla.objects.select_related("proyecto").all()
    solicitudes = SolicitudReasignacion.objects.select_related(
        "trabajador", "cuadrilla_origen", "cuadrilla_destino", "respondido_por"
    ).order_by("-fecha_solicitud")
    
    # Filtrar solicitudes según el rol del usuario
    if hasattr(request.user, 'perfil') and request.user.perfil.rol == 'lider_cuadrilla':
        # Los líderes solo ven solicitudes de sus cuadrillas
        cuadrillas_lider = Cuadrilla.objects.filter(trabajador__usuario=request.user)
        solicitudes = solicitudes.filter(cuadrilla_destino__in=cuadrillas_lider)
    
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
            messages.success(request, "✅ Solicitud de reasignación enviada correctamente.")
            return redirect("reasignacion")
        
        elif accion == "responder_solicitud":
            solicitud_id = request.POST.get("solicitud_id")
            respuesta = request.POST.get("respuesta")  # 'aceptar' o 'rechazar'
            
            if not solicitud_id or not respuesta:
                messages.error(request, "Datos inválidos.")
                return redirect("reasignacion")
            
            solicitud = get_object_or_404(SolicitudReasignacion, id=solicitud_id)
            
            # Verificar que el usuario sea el líder de la cuadrilla destino
            if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'lider_cuadrilla':
                messages.error(request, "Solo los líderes de cuadrilla pueden responder solicitudes.")
                return redirect("reasignacion")
            
            cuadrilla_destino = solicitud.cuadrilla_destino
            if cuadrilla_destino.trabajador and cuadrilla_destino.trabajador.usuario != request.user:
                messages.error(request, "Solo el líder de la cuadrilla destino puede responder esta solicitud.")
                return redirect("reasignacion")
            
            if solicitud.estado != 'pendiente':
                messages.info(request, "Esta solicitud ya fue respondida.")
                return redirect("reasignacion")
            
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
    })


@login_required
def exportar_excel(request):
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
    response["Content-Disposition"] = 'attachment; filename="proyectos.xlsx"'
    df.to_excel(response, index=False, sheet_name="Proyectos")
    return response
