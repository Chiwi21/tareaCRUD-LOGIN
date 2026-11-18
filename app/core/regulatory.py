"""Diagnóstico preliminar por categoría. Nunca determina autorización aduanera."""
from __future__ import annotations
from dataclasses import dataclass

CATEGORY_LABELS = {
    'general': 'Hogar / mercancías generales',
    'electronics': 'Electrónica y telecomunicaciones',
    'cosmetics': 'Cosméticos, cuidado personal y salud',
    'textiles': 'Textiles, ropa y calzado',
    'machinery': 'Maquinaria y equipos',
    'food': 'Alimentos procesados',
    'agro': 'Productos vegetales o animales',
    'automotive': 'Repuestos y autopartes',
}

@dataclass(frozen=True)
class Requirement:
    agency: str
    title: str
    explanation: str
    step: str
    source: str
    level: str = 'revisar'  # revisar o pendiente; sin falsos positivos de aprobación.


def diagnose(category: str, hs_code: str = '') -> list[Requirement]:
    results = [
        Requirement('SENAE', 'Confirmar subpartida arancelaria y controles previos',
                    'Consulta el Arancel Nacional en ECUAPASS. La categoría comercial no determina por sí sola aranceles o permisos.',
                    'Antes de comprar / embarcar', 'https://www.aduana.gob.ec/servicio-al-ciudadano/para-importar/'),
        Requirement('SENAE', 'Registro de importador y documentación aduanera',
                    'Revisa registro en ECUAPASS, factura comercial, documento de transporte y documentos de acompañamiento cuando apliquen.',
                    'Antes de embarcar y nacionalizar', 'https://www.aduana.gob.ec/servicio-al-ciudadano/para-importar/'),
    ]
    if category == 'cosmetics':
        results.append(Requirement('ARCSA', 'Revisar Notificación Sanitaria Obligatoria (NSO) o Registro Sanitario',
                   'Los cosméticos pueden requerir NSO; medicamentos y dispositivos médicos siguen regímenes diferentes. Define la función y composición exactas.',
                   'Verificar ANTES del embarque', 'https://www.controlsanitario.gob.ec/notificacion-sanitaria-obligatoria-de-productos-cosmeticos/'))
    elif category == 'food':
        results.append(Requirement('ARCSA', 'Verificar notificación o registro sanitario según el alimento',
                  'La condición depende del tipo de alimento, procesamiento, presentación y régimen aplicable.',
                  'Antes de importar', 'https://www.controlsanitario.gob.ec/documentos-vigentes/'))
    elif category == 'textiles':
        results.append(Requirement('INEN / CAN', 'Revisar requisitos de etiquetado de textiles y calzado',
                  'Identifica el reglamento vigente aplicable al artículo. La inspección de etiquetas puede ser voluntaria; no presupongas certificado obligatorio.',
                  'Antes de comercializar / según control', 'https://www.normalizacion.gob.ec/conoce-los-requisitos-generales-que-establece-el-reglamento-tecnico-andino-para-el-etiquetado-de-confecciones/'))
    elif category == 'agro':
        results.append(Requirement('AGROCALIDAD', 'Verificar permisos fitosanitarios o zoosanitarios',
                   'Plantas, mercancías vegetales y productos de origen animal pueden tener controles específicos según especie y país de origen.',
                   'Consultar antes del embarque', 'https://www.agrocalidad.gob.ec/direccion-de-control-fitosanitario/'))
    elif category == 'electronics':
        results.append(Requirement('INEN / ARCOTEL', 'Comprobar reglamentos técnicos y homologación, si aplica',
                   'Depende de la función del equipo, conectividad radioeléctrica, subpartida y alcance de los reglamentos aplicables.',
                   'Antes de la compra', 'https://www.normalizacion.gob.ec/preguntas-frecuentes/'))
        results.append(Requirement('TRANSPORTISTA', 'Confirmar restricciones sobre baterías de litio',
                   'Si contiene baterías, solicita ficha técnica, especificación de batería y condiciones de aceptación aérea o marítima.',
                   'Antes de cotizar el flete', 'https://www.freightos.com/freight-resources/air-freight-rates-cost-prices/'))
    elif category in ('machinery', 'automotive'):
        results.append(Requirement('INEN / SENAE', 'Revisar regulaciones técnicas y características del equipo',
                   'Máquinas, vehículos, repuestos y equipos eléctricos pueden tener requisitos diferenciados. La subpartida es indispensable.',
                   'Antes de la orden de compra', 'https://www.normalizacion.gob.ec/preguntas-frecuentes/'))
    else:
        results.append(Requirement('SENAE / INEN', 'Comprobar si hay controles específicos para el producto',
                   'No se puede certificar libre importación solo porque el artículo sea de uso general. Revisa uso, materiales y subpartida.',
                   'Antes de embarcar', 'https://www.aduana.gob.ec/servicio-al-ciudadano/para-importar/'))
    if hs_code:
        results.append(Requirement('SENAE', 'Verificar la subpartida ingresada: ' + hs_code,
                    'El sistema recibió este código del usuario, pero NO comprobó su correspondencia con el producto ni las restricciones.',
                    'Consulta oficial pendiente', 'https://mesadeservicios.aduana.gob.ec/arancel/'))
    else:
        results.append(Requirement('SENAE', 'Falta identificar la subpartida nacional',
                    'Sin código arancelario validado no es posible determinar automáticamente la tasa de arancel ni el conjunto definitivo de permisos.',
                    'Pendiente de clasificación', 'https://mesadeservicios.aduana.gob.ec/arancel/', 'pendiente'))
    return results
