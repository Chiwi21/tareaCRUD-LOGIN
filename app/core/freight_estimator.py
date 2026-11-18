"""Comparador con precios introducidos por el usuario. No consulta tarifas en vivo."""
from __future__ import annotations
from decimal import Decimal
from app.core.import_estimator import money, number, calculate_import_costs

MODES = {'AIR': 'Aéreo', 'LCL': 'Marítimo consolidado (LCL)', 'FCL': 'Contenedor completo (FCL)'}


def compare_freight(data: dict) -> dict:
    mode = data.get('mode', 'AIR')
    if mode not in MODES:
        raise ValueError('Modalidad logística no válida.')
    packages = number(data.get('packages','1'), 'Bultos', allow_zero=False)
    if packages != packages.to_integral_value() or packages > 100000:
        raise ValueError('Bultos: ingrese un entero válido.')
    dimensions = {k: number(data.get(k,''), k, allow_zero=False) for k in ('length_cm','width_cm','height_cm','weight_kg')}
    gross_weight = packages * dimensions['weight_kg']
    cbm = packages * dimensions['length_cm'] * dimensions['width_cm'] * dimensions['height_cm'] / Decimal('1000000')
    volume_weight_air = cbm * Decimal('1000000') / Decimal('6000')  # divisor 6000 cm³/kg
    if mode == 'AIR':
        chargeable = max(gross_weight, volume_weight_air)
        unit = 'kg cobrable'
    elif mode == 'LCL':
        chargeable = max(Decimal('1'), cbm, gross_weight / Decimal('1000'))
        unit = 'W/M (mínimo supuesto 1)'
    else:
        chargeable = Decimal('1')
        unit = 'contenedor'
    rate = number(data.get('freight_rate', ''), 'Tarifa de transporte', allow_zero=False)
    min_freight = number(data.get('minimum_freight') or '0', 'Flete mínimo')
    freight = money(max(rate * chargeable, min_freight))
    # Incluye recargos y gastos en origen en valor aduanero del escenario según supuesto FOB.
    args = dict(data)
    args['freight'] = str(freight)
    args['origin_charges'] = str(money(number(data.get('origin_charges') or '0', 'Origen') + number(data.get('freight_surcharges') or '0', 'Recargos')))
    args.setdefault('other','0')
    result = calculate_import_costs(args)
    result.update({
        'mode':mode, 'mode_name':MODES[mode], 'packages':int(packages),
        'gross_weight':money(gross_weight), 'cbm':cbm.quantize(Decimal('0.001')),
        'volumetric_weight':money(volume_weight_air),
        'chargeable':money(chargeable), 'chargeable_unit':unit,
        'freight_rate':money(rate), 'transit_days':str(data.get('transit_days','') or ''), 'freight_surcharges':money(number(data.get('freight_surcharges') or '0', 'Recargos')),
    })
    return result
