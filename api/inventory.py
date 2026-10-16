"""Reglas compartidas para disponibilidad, pago y devolución de inventario."""

from collections import defaultdict

from django.db.models import F, QuerySet

from .models import DetalleContrato, Maquinaria


ACTIVE_CONTRACT_STATES = ('PAGADO', 'ENTREGADO')
RESERVED_CONTRACT_STATES = ('PENDIENTE', 'PAGADO', 'ENTREGADO')


class InventoryUnavailable(Exception):
    """Indica que una solicitud no puede reservar el inventario disponible."""


def contract_details_for_machine(
    maquinaria_id: int,
    states: tuple[str, ...],
    *,
    exclude_contract_id: int | None = None,
) -> QuerySet:
    """Devuelve los detalles que ocupan una máquina en los estados indicados."""
    details = DetalleContrato.objects.filter(
        maquinaria_id=maquinaria_id,
        contrato__estado__in=states,
    )
    if exclude_contract_id is not None:
        details = details.exclude(contrato_id=exclude_contract_id)
    return details


def available_units_for_period(
    maquinaria: Maquinaria,
    fecha_inicio,
    fecha_fin,
    *,
    extra_units: int = 0,
) -> int:
    """Calcula cuántas unidades quedan para un período concreto.

    Las solicitudes pendientes también reservan capacidad. El stock físico se
    mantiene sin descontar hasta que se confirma un pago, pero una solicitud
    pendiente ya no puede ser usada para sobre-reservar la misma máquina.
    """
    active = contract_details_for_machine(maquinaria.id, ACTIVE_CONTRACT_STATES)
    reserved = contract_details_for_machine(maquinaria.id, RESERVED_CONTRACT_STATES)
    active_overlap = active.filter(
        fecha_inicio__lt=fecha_fin,
        fecha_fin__gt=fecha_inicio,
    ).count()
    pending_overlap = reserved.filter(
        contrato__estado='PENDIENTE',
        fecha_inicio__lt=fecha_fin,
        fecha_fin__gt=fecha_inicio,
    ).count()
    total_units = maquinaria.stock_disponible + active.count()
    return total_units - active_overlap - pending_overlap - extra_units


def validate_contract_availability(contract, *, exclude_pending_contracts=False):
    """Valida que un contrato pueda ocupar sus máquinas en sus fechas."""
    details = list(contract.detalles.select_related('maquinaria').order_by('maquinaria_id'))
    grouped = defaultdict(list)
    for detail in details:
        if detail.maquinaria_id:
            grouped[detail.maquinaria_id].append(detail)

    for maquinaria_id, contract_details in grouped.items():
        maquinaria = Maquinaria.objects.select_for_update().get(pk=maquinaria_id)
        active = contract_details_for_machine(maquinaria_id, ACTIVE_CONTRACT_STATES)
        if exclude_pending_contracts:
            reserved = contract_details_for_machine(
                maquinaria_id,
                ('PENDIENTE',),
                exclude_contract_id=contract.pk,
            )
        else:
            reserved = contract_details_for_machine(maquinaria_id, ('PENDIENTE',))

        total_units = maquinaria.stock_disponible + active.count()
        required_units = len(contract_details)
        if maquinaria.stock_disponible < required_units:
            raise InventoryUnavailable(
                f"Stock insuficiente para {maquinaria.nombre}."
            )

        for detail in contract_details:
            active_overlap = active.filter(
                fecha_inicio__lt=detail.fecha_fin,
                fecha_fin__gt=detail.fecha_inicio,
            ).count()
            pending_overlap = reserved.filter(
                fecha_inicio__lt=detail.fecha_fin,
                fecha_fin__gt=detail.fecha_inicio,
            ).count()
            current_overlap = sum(
                1
                for other in contract_details
                if other.fecha_inicio < detail.fecha_fin
                and other.fecha_fin > detail.fecha_inicio
            )
            if active_overlap + pending_overlap + current_overlap > total_units:
                raise InventoryUnavailable(
                    f"No hay unidades de {maquinaria.nombre} disponibles para las fechas solicitadas."
                )


def reserve_contract_inventory(contract):
    """Descuenta el stock al confirmar un pago y devuelve las máquinas afectadas."""
    details = list(contract.detalles.select_related('maquinaria').order_by('maquinaria_id'))
    grouped = defaultdict(list)
    for detail in details:
        if detail.maquinaria_id:
            grouped[detail.maquinaria_id].append(detail)

    locked_machines = {}
    for maquinaria_id in grouped:
        locked_machines[maquinaria_id] = Maquinaria.objects.select_for_update().get(pk=maquinaria_id)

    # La validación se hace con las filas bloqueadas para evitar dos pagos
    # simultáneos que consuman la misma unidad.
    validate_contract_availability(contract, exclude_pending_contracts=True)

    for maquinaria_id, contract_details in grouped.items():
        maquinaria = locked_machines[maquinaria_id]
        cantidad = len(contract_details)
        Maquinaria.objects.filter(pk=maquinaria_id).update(
            stock_disponible=maquinaria.stock_disponible - cantidad,
        )

    return locked_machines


def release_contract_inventory(contract):
    """Devuelve al stock las unidades descontadas de un contrato pagado."""
    details = list(contract.detalles.filter(maquinaria_id__isnull=False))
    quantities = defaultdict(int)
    for detail in details:
        quantities[detail.maquinaria_id] += 1
    for maquinaria_id, cantidad in quantities.items():
        Maquinaria.objects.filter(pk=maquinaria_id).update(
            stock_disponible=F('stock_disponible') + cantidad,
        )
