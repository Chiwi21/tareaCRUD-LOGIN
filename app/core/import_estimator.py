"""Simulador financiero educativo. Los porcentajes son entradas, NO aranceles verificados."""
from __future__ import annotations
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENT = Decimal('0.01')


def money(v: Decimal) -> Decimal:
    return v.quantize(CENT, rounding=ROUND_HALF_UP)


def number(value, name: str, *, allow_zero=True) -> Decimal:
    try:
        amount = Decimal(str(value).strip().replace(',', '.'))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f'{name}: ingrese un número válido.') from None
    if not amount.is_finite() or amount < 0 or (not allow_zero and amount == 0):
        raise ValueError(f'{name}: ingrese un valor positivo.')
    if amount > Decimal('1000000000'):
        raise ValueError(f'{name}: valor fuera del rango admitido.')
    return amount


def calculate_import_costs(data: dict[str, str]) -> dict:
    """Presupuesto en USD, supuesto FOB. IVA como desembolso, no costo definitivo."""
    qty = number(data.get('quantity', ''), 'Cantidad', allow_zero=False)
    if qty != qty.to_integral_value() or qty > 10000000:
        raise ValueError('Cantidad: debe ser un entero entre 1 y 10.000.000.')
    quantity = int(qty)
    unit = number(data.get('unit_price', ''), 'Precio unitario')
    budget = number(data.get('budget') or '0', 'Presupuesto')
    freight = number(data.get('freight') or '0', 'Flete internacional')
    origin_charges = number(data.get('origin_charges') or '0', 'Gastos en origen')
    other = number(data.get('other') or '0', 'Otros gastos')
    destination_charges = number(data.get('destination_charges') or '0', 'Gastos portuarios/aeroportuarios')
    broker = number(data.get('broker') or '0', 'Agente aduanero')
    delivery = number(data.get('delivery') or '0', 'Transporte interno')
    ice = number(data.get('ice') or '0', 'ICE estimado')
    isd = number(data.get('isd') or '0', 'ISD informado')
    rates = {}
    for key, label in [('insurance_pct','Seguro'), ('duty_pct','Arancel'), ('fodinfa_pct','FODINFA'), ('vat_pct','IVA')]:
        rate = number(data.get(key) or '0', label)
        if rate > 100:
            raise ValueError(f'{label}: el porcentaje debe estar entre 0 y 100.')
        rates[key] = rate
    # Póliza cotizada: si se introduce un monto prevalece sobre el porcentaje.
    insurance_amount = data.get('insurance_amount', '')
    merchandise = money(qty * unit)
    insurance_basis = money(merchandise + origin_charges + freight)
    if str(insurance_amount).strip():
        insurance = money(number(insurance_amount, 'Seguro fijo'))
        insurance_source = 'Monto de póliza indicado'
    else:
        insurance = money(insurance_basis * rates['insurance_pct'] / 100)
        insurance_source = 'Porcentaje sobre mercancía + gastos en origen + flete'
    cif = money(merchandise + origin_charges + freight + insurance)
    duty = money(cif * rates['duty_pct'] / 100)
    fodinfa = money(cif * rates['fodinfa_pct'] / 100)
    vat_base = money(cif + duty + fodinfa + ice)
    vat = money(vat_base * rates['vat_pct'] / 100)
    taxes = money(duty + fodinfa + ice + vat)
    local_charges = money(destination_charges + broker + delivery + other)
    total = money(cif + taxes + local_charges + isd)
    # Aproximación sin IVA si fuese crédito tributario recuperable; no afirmar su recuperabilidad.
    economic_total_without_vat = money(total - vat)
    return {
        'quantity': quantity, 'unit_price': money(unit), 'budget': money(budget),
        'merchandise': merchandise, 'origin_charges': money(origin_charges),
        'freight': money(freight), 'insurance': insurance, 'insurance_source': insurance_source,
        'insurance_basis': insurance_basis, 'cif': cif, 'duty': duty, 'fodinfa': fodinfa,
        'ice': money(ice), 'vat_base': vat_base, 'vat': vat, 'taxes': taxes,
        'destination_charges': money(destination_charges), 'broker': money(broker),
        'delivery': money(delivery), 'other': money(other), 'isd': money(isd),
        'local_charges': local_charges, 'total': total,
        'unit_total': money(total / qty), 'economic_total_without_vat': economic_total_without_vat,
        'budget_difference': money(budget - total), 'within_budget': budget >= total,
        'budget_shortfall': money(max(Decimal(0), total - budget)),
        'budget_remaining': money(max(Decimal(0), budget - total)),
    }
