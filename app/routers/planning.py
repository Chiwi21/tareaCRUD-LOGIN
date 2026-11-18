"""Diagnóstico aduanero preliminar y comparación de alternativas de transporte."""
from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.freight_estimator import compare_freight, MODES
from app.core.import_estimator import number
from app.core.regulatory import CATEGORY_LABELS, diagnose
from app.database import get_db
from app.flash import flash
from app.models import User, OperationTradeProfile, FreightComparison, Operation
from app.security import require_login
from app.templating import templates
from app.constants import ROLE_ADMIN

router = APIRouter(tags=['planificacion'])
SCENARIO_FIELDS = ('name','mode','quantity','unit_price','budget','packages','weight_kg','length_cm','width_cm','height_cm',
 'freight_rate','minimum_freight','freight_surcharges','origin_charges','insurance_pct','insurance_amount',
 'duty_pct','fodinfa_pct','vat_pct','ice','isd','destination_charges','broker','delivery','other','transit_days')

def get_owned_operation(db: Session, operation_id: int, user: User) -> Operation:
    operation = db.get(Operation, operation_id)
    if operation is None:
        raise HTTPException(404, 'Operación inexistente.')
    if user.role != ROLE_ADMIN and operation.user_id != user.id:
        raise HTTPException(403, 'No tiene acceso a esta operación.')
    return operation

def parse_profile(form) -> dict:
    cat = str(form.get('product_category', 'general') or 'general')
    if cat not in CATEGORY_LABELS:
        raise ValueError('Seleccione una categoría válida.')
    hs = str(form.get('hs_code', '') or '').strip()
    normalized = ''.join(c for c in hs if c.isdigit())
    if hs and (not all(c.isdigit() or c in '.- ' for c in hs) or len(normalized) not in (6,8,10)):
        raise ValueError('Subpartida: use un código de 6, 8 o 10 dígitos (solo numérico).')
    q = number(form.get('project_quantity', '1'), 'Unidades', allow_zero=False)
    if q != q.to_integral_value() or q > 10000000:
        raise ValueError('Unidades: ingrese un número entero válido.')
    name = str(form.get('product_name','') or '').strip()
    desc = str(form.get('product_description','') or '').strip()
    if len(name)>160 or len(desc)>2000:
        raise ValueError('La descripción del producto es demasiado larga.')
    return {'category':cat, 'product_name':name,'product_description':desc,
       'hs_code':normalized, 'quantity':int(q),
       'unit_price':number(form.get('project_unit_price','0'), 'Precio unitario'),
       'budget':number(form.get('project_budget','0'), 'Presupuesto')}

def save_profile(db:Session, operation_id:int, payload:dict) -> None:
    existing=db.query(OperationTradeProfile).filter_by(operation_id=operation_id).first()
    if not existing:
        existing=OperationTradeProfile(operation_id=operation_id)
        db.add(existing)
    for field, value in payload.items():
        setattr(existing, field, value)
    db.commit()

def detail_context(db: Session, operation_id:int) -> dict:
    profile=db.query(OperationTradeProfile).filter_by(operation_id=operation_id).first()
    return {
        'trade_profile':profile,
        'regulatory_checklist':diagnose(profile.category, profile.hs_code) if profile else diagnose('general'),
        'category_labels':CATEGORY_LABELS,
        'freight_comparison_count':db.query(FreightComparison).filter_by(operation_id=operation_id).count(),
    }

def defaults_for(profile:OperationTradeProfile | None) -> dict:
    return {
        'name':'Escenario A','mode':'AIR','quantity':str(profile.quantity if profile else 100),
        'unit_price':str(profile.unit_price if profile else 0), 'budget':str(profile.budget if profile else 0),
        'packages':'10','weight_kg':'5','length_cm':'50','width_cm':'40','height_cm':'30',
        'freight_rate':'','minimum_freight':'0','freight_surcharges':'0','origin_charges':'0',
        'insurance_pct':'1','insurance_amount':'','duty_pct':'10','fodinfa_pct':'0.5','vat_pct':'15',
        'ice':'0','isd':'0','destination_charges':'0','broker':'0','delivery':'0','other':'0',
        'transit_days':'',
    }

def comparison_context(db:Session, operation_id:int, values:dict, error=None):
    profile=db.query(OperationTradeProfile).filter_by(operation_id=operation_id).first()
    scenarios=db.query(FreightComparison).filter_by(operation_id=operation_id).order_by(FreightComparison.id).all()
    compiled=[]
    for scenario in scenarios:
        try:
            calculation=compare_freight(json.loads(scenario.inputs_json))
        except (ValueError, KeyError, TypeError):
            calculation=None
        compiled.append({'scenario':scenario,'result':calculation})
    valid=[v for v in compiled if v['result']]
    cheapest=min(valid,key=lambda v:v['result']['total']) if valid else None
    return {'trade_profile':profile,'scenarios':compiled,'cheapest_id':cheapest['scenario'].id if cheapest else None,
            'values':values,'error':error,'modes':MODES}

@router.get('/operations/{operation_id}/comparar')
def show_comparison(request:Request, operation_id:int, user:User=Depends(require_login), db:Session=Depends(get_db)):
    operation=get_owned_operation(db,operation_id,user)
    profile=db.query(OperationTradeProfile).filter_by(operation_id=operation_id).first()
    return templates.TemplateResponse(request,'operations/comparator.html',{'user':user,'operation':operation,
     **comparison_context(db,operation_id,defaults_for(profile))})

@router.post('/operations/{operation_id}/comparar')
async def create_comparison(request:Request, operation_id:int, user:User=Depends(require_login),db:Session=Depends(get_db)):
    operation=get_owned_operation(db,operation_id,user)
    form=await request.form()
    values={key:str(form.get(key,'') or '') for key in SCENARIO_FIELDS}
    try:
        name=values['name'].strip()
        if not 2<=len(name)<=100:
            raise ValueError('Ingrese un nombre de escenario de 2 a 100 caracteres.')
        if values['mode'] not in MODES:
            raise ValueError('Seleccione transporte aéreo, LCL o FCL.')
        compare_freight(values)
        if values['transit_days']:
            transit=number(values['transit_days'],'Días de tránsito',allow_zero=False)
            if transit!=transit.to_integral_value() or transit>365:
                raise ValueError('Días de tránsito: número entero entre 1 y 365.')
        else:
            transit=None
    except ValueError as exc:
        return templates.TemplateResponse(request,'operations/comparator.html',{'user':user,'operation':operation,
         **comparison_context(db,operation_id,values,str(exc))},status_code=400)
    db.add(FreightComparison(operation_id=operation_id,name=name,mode=values['mode'],inputs_json=json.dumps(values)))
    db.commit()
    flash(request,f'Escenario «{name}» guardado. Compara el desembolso y costo unitario.', 'success')
    return RedirectResponse(f'/operations/{operation_id}/comparar',status_code=303)

@router.post('/operations/{operation_id}/comparar/{scenario_id}/delete')
def delete_comparison(operation_id:int, scenario_id:int, user:User=Depends(require_login),db:Session=Depends(get_db)):
    get_owned_operation(db,operation_id,user)
    scenario=db.get(FreightComparison,scenario_id)
    if not scenario or scenario.operation_id!=operation_id:
        raise HTTPException(404,'Escenario inexistente.')
    db.delete(scenario); db.commit()
    return RedirectResponse(f'/operations/{operation_id}/comparar',status_code=303)
