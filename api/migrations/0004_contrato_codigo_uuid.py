import uuid
from django.db import migrations, models


def assign_contract_uuids(apps, schema_editor):
    """Asigna un folio UUID a cada contrato que ya existe."""
    contrato_model = apps.get_model('api', 'Contrato')
    for contrato in contrato_model.objects.filter(codigo_uuid__isnull=True).iterator():
        contrato.codigo_uuid = uuid.uuid4()
        contrato.save(update_fields=['codigo_uuid'])


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0003_itemcarro_item_carro_unico_por_periodo'),
    ]

    operations = [
        migrations.AddField(
            model_name='contrato',
            name='codigo_uuid',
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.RunPython(assign_contract_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='contrato',
            name='codigo_uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
