from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_contrato_codigo_uuid'),
    ]

    operations = [
        migrations.AddField(
            model_name='contrato',
            name='fecha_pago',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='contrato',
            name='metodo_pago',
            field=models.CharField(
                blank=True,
                choices=[('DEMO', 'Pago demo'), ('MANUAL', 'Confirmado por ejecutivo')],
                default='',
                max_length=10,
            ),
        ),
    ]
