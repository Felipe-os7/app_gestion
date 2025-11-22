# Generated migration to make integrante.usuario required

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0010_delete_all_integrantes_and_add_user'),
    ]

    operations = [
        # Hacer el campo usuario obligatorio
        migrations.AlterField(
            model_name='integrante',
            name='usuario',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='integrante',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Usuario'
            ),
        ),
    ]

