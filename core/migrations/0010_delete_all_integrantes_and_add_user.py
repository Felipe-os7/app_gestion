# Generated migration to delete all integrantes and connect with User

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def delete_all_integrantes(apps, schema_editor):
    """Elimina todos los integrantes existentes."""
    Integrante = apps.get_model('core', 'Integrante')
    Integrante.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0009_integrante_estado_integrante_fecha_actualizacion_and_more'),
    ]

    operations = [
        # Primero eliminamos todos los integrantes
        migrations.RunPython(delete_all_integrantes, migrations.RunPython.noop),
        
        # Eliminamos el campo nombre
        migrations.RemoveField(
            model_name='integrante',
            name='nombre',
        ),
        
        # Agregamos el campo usuario (OneToOne) - como null=True primero para evitar problemas
        migrations.AddField(
            model_name='integrante',
            name='usuario',
            field=models.OneToOneField(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='integrante',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Usuario'
            ),
        ),
    ]

