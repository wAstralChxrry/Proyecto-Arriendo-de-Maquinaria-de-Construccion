from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0004_contrato_codigo_uuid'),
    ]

    operations = [
        migrations.AddField(
            model_name='contrato',
            name='referencia_pago',
            field=models.CharField(blank=True, default='', max_length=32),
        ),
        migrations.AlterField(
            model_name='contrato',
            name='estado',
            field=models.CharField(
                choices=[
                    ('PENDIENTE', 'Pendiente'),
                    ('APROBADO', 'Aprobado'),
                    ('PAGADO', 'Pagado'),
                    ('ENTREGADO', 'Entregado'),
                    ('COMPLETADO', 'Completado'),
                    ('CANCELADO', 'Cancelado'),
                ],
                default='PENDIENTE',
                max_length=15,
            ),
        ),
    ]
