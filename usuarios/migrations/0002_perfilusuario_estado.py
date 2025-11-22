# Generated migration to add estado field to PerfilUsuario

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='perfilusuario',
            name='estado',
            field=models.CharField(
                choices=[('activo', 'Activo'), ('inactivo', 'Inactivo'), ('suspendido', 'Suspendido')],
                default='activo',
                max_length=15,
                verbose_name='Estado de la cuenta'
            ),
        ),
    ]

