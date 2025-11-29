from django.conf import settings
settings.ALLOWED_HOSTS = list(getattr(settings, 'ALLOWED_HOSTS', [])) + ['testserver']
from django.test import Client
from django.contrib.auth.models import User
from core.models import Proyecto,Cuadrilla,Integrante,SolicitudReasignacion

print('== test script start ==')

p = Proyecto.objects.filter(nombre='P-Test').first()
if not p:
    p = Proyecto.objects.create(nombre='P-Test', cliente='C', direccion='', ciudad='', descripcion='')

c1 = Cuadrilla.objects.filter(nombre='C1', proyecto=p).first()
if not c1:
    c1 = Cuadrilla.objects.create(nombre='C1', proyecto=p)

c2 = Cuadrilla.objects.filter(nombre='C2', proyecto=p).first()
if not c2:
    c2 = Cuadrilla.objects.create(nombre='C2', proyecto=p)

i_av = Integrante.objects.filter(nombre_trabajador='Juan', apellido_trabajador='Perez').first()
if not i_av:
    i_av = Integrante.objects.create(nombre_trabajador='Juan', apellido_trabajador='Perez', cargo='operario')

u = User.objects.get(username='testuser')
i_le, created = Integrante.objects.get_or_create(
    usuario=u,
    defaults={'nombre_trabajador':'Lider','apellido_trabajador':'Uno','cargo':'lider','cuadrilla':c2,'estado':'asignado'}
)
if i_le.cuadrilla is None:
    i_le.cuadrilla = c2
    i_le.estado = 'asignado'
    i_le.save()

c2.trabajador = i_le
c2.save()

client = Client()
login_ok = client.login(username='testuser', password='TestPass123')
print('login', login_ok)

resp = client.post(f'/cuadrilla/editar/{c1.id}/', {'nombre':'C1_mod','proyecto':p.codigo,'estado':'activa','integrantes':[str(i_av.id)]}, follow=True, HTTP_HOST='testserver')
print('edit_status', resp.status_code)
print('edit_content', resp.content[:400])

i_av.refresh_from_db()
print('i_av_cuadrilla', i_av.cuadrilla.id if i_av.cuadrilla else None)

resp2 = client.post('/reasignacion/', {'accion':'crear_solicitud','trabajador_id':str(i_av.id),'cuadrilla_destino':str(c2.id),'motivo':'prueba'}, follow=True, HTTP_HOST='testserver')
print('create_solicitud_status', resp2.status_code)

s = SolicitudReasignacion.objects.filter(trabajador=i_av, cuadrilla_destino=c2, estado='pendiente').first()
print('solicitud', bool(s), s.id if s else None)

if s:
    resp3 = client.post('/reasignacion/', {'accion':'responder_solicitud','solicitud_id':s.id,'respuesta':'aceptar'}, follow=True, HTTP_HOST='testserver')
    print('responder_status', resp3.status_code)
    i_av.refresh_from_db()
    print('i_av_new_cuadrilla', i_av.cuadrilla.id if i_av.cuadrilla else None)
else:
    print('No solicitud creada')

print('== test script end ==')
