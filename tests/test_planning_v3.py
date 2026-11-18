"""Pruebas unitarias y de integración del módulo V3; SQLite temporal."""
from __future__ import annotations
import tempfile, unittest
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.core.import_estimator import calculate_import_costs
from app.core.freight_estimator import compare_freight
from app.core.regulatory import diagnose, CATEGORY_LABELS
from app.database import Base, get_db
from app.main import app
from app.models import User, Operation, OperationTradeProfile, FreightComparison
from app.security import hash_password

class PlanningMathTests(unittest.TestCase):
    def test_budget_and_taxes(self):
        result=calculate_import_costs({'budget':'7000','quantity':'1000','unit_price':'5','freight':'1000',
            'insurance_pct':'1','duty_pct':'10','fodinfa_pct':'.5','vat_pct':'15',
            'destination_charges':'200','broker':'150','delivery':'100','other':'50'})
        self.assertEqual(str(result['cif']),'6060.00')
        self.assertEqual(str(result['duty']),'606.00')
        self.assertEqual(str(result['fodinfa']),'30.30')
        self.assertEqual(str(result['vat']),'1004.45')
        self.assertEqual(str(result['total']),'8200.75')
        self.assertFalse(result['within_budget'])
        self.assertEqual(str(result['budget_shortfall']),'1200.75')
        self.assertEqual(str(result['unit_total']),'8.20')
    def test_policy_user_supplied_insurance(self):
        obj=calculate_import_costs({'quantity':'1','unit_price':'100','budget':'200',
            'freight':'10','insurance_pct':'10','insurance_amount':'2','duty_pct':'0','vat_pct':'0','fodinfa_pct':'0'})
        self.assertEqual(str(obj['insurance']),'2.00')
        self.assertEqual(str(obj['total']),'112.00')
    def test_freight_chargeable_by_mode(self):
        base={'quantity':'100','unit_price':'10','budget':'2000','packages':'10', 'weight_kg':'5',
            'length_cm':'50','width_cm':'40','height_cm':'30','freight_rate':'10',
            'duty_pct':'0','vat_pct':'0','fodinfa_pct':'0','insurance_pct':'0'}
        air=compare_freight({**base,'mode':'AIR'})
        lcl=compare_freight({**base,'mode':'LCL'})
        fcl=compare_freight({**base,'mode':'FCL'})
        self.assertEqual(str(air['chargeable']),'100.00')  # 0,6 CBM * 166.67 kg/m³
        self.assertEqual(str(lcl['chargeable']),'1.00')  # mínimo simulado 1 W/M
        self.assertEqual(str(fcl['chargeable']),'1.00')
        self.assertEqual(str(air['freight']),'1000.00')
        self.assertEqual(str(lcl['freight']),'10.00')
    def test_regulation_no_false_approval(self):
        self.assertTrue('cosmetics' in CATEGORY_LABELS)
        cosmetic=diagnose('cosmetics')
        self.assertTrue(any(entry.agency=='ARCSA' for entry in cosmetic))
        self.assertTrue(any('subpartida' in entry.title.lower() for entry in cosmetic))
        self.assertTrue(all(entry.level!='aprobado' for entry in cosmetic))
        self.assertTrue(any(entry.agency.startswith('INEN') for entry in diagnose('textiles')))
        self.assertTrue(any(entry.agency=='AGROCALIDAD' for entry in diagnose('agro')))

class PlanningHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.engine=create_engine('sqlite:///'+str(Path(cls.tmp.name)/'test.db'),connect_args={'check_same_thread':False})
        @event.listens_for(cls.engine,'connect')
        def fk(conn,_): conn.execute('PRAGMA foreign_keys=ON')
        Base.metadata.create_all(cls.engine)
        cls.Session=sessionmaker(bind=cls.engine,autoflush=False,autocommit=False)
        with cls.Session() as db:
            cls.user_a=User(username='plan_a', password_hash=hash_password('pass123456'), role='IMPORTER', full_name='Plan A',is_active=True)
            cls.user_b=User(username='plan_b', password_hash=hash_password('pass123456'), role='IMPORTER',full_name='Plan B',is_active=True)
            db.add_all([cls.user_a,cls.user_b]);db.commit()
            cls.user_a_id=cls.user_a.id;cls.user_b_id=cls.user_b.id
        def override():
            db=cls.Session()
            try:yield db
            finally:db.close()
        app.dependency_overrides[get_db]=override
        cls.client=TestClient(app,follow_redirects=False,raise_server_exceptions=False)
    @classmethod
    def tearDownClass(cls):
        cls.client.close();app.dependency_overrides.pop(get_db,None);cls.engine.dispose();cls.tmp.cleanup()
    def test_01_create_as_importer_and_regulatory(self):
        login=self.client.post('/login',data={'username':'plan_a','password':'pass123456'})
        self.assertEqual(login.status_code,303)
        self.assertEqual(self.client.get('/operations/new').status_code,200)
        create=self.client.post('/operations/new',data={
            'type':'IMPORT','status':'DONE','user_id':str(self.user_b_id),  # tampering must be ignored
            'company_id':'','operation_date':'2026-11-18',
            'product_category':'cosmetics','product_name':'Champú',
            'product_description':'Champú cosmético','hs_code':'',
            'project_quantity':'1000','project_unit_price':'5','project_budget':'10000'
        })
        self.assertEqual(create.status_code,303,create.text[:600]);cls=type(self)
        db=self.Session()
        try:
            op=db.query(Operation).order_by(Operation.id.desc()).first()
            cls.op_id=op.id
            self.assertEqual(op.user_id,self.user_a_id)
            self.assertEqual(op.status,'PENDING')
            profile=db.query(OperationTradeProfile).filter_by(operation_id=op.id).one()
            self.assertEqual(profile.category,'cosmetics')
            self.assertEqual(profile.product_name,'Champú')
        finally:db.close()
        detail=self.client.get(f'/operations/{self.op_id}')
        self.assertEqual(detail.status_code,200,detail.text[:800]);self.assertIn('ARCSA',detail.text)
    def test_02_compare_and_scope(self):
        op_id=self.op_id
        page=self.client.get(f'/operations/{op_id}/comparar')
        self.assertEqual(page.status_code,200,page.text[:800])
        inputs={'name':'Escenario A aéreo','mode':'AIR','quantity':'1000','unit_price':'5',
           'budget':'10000','packages':'10','weight_kg':'5','length_cm':'50','width_cm':'40',
           'height_cm':'30','freight_rate':'6','insurance_pct':'1','duty_pct':'10','fodinfa_pct':'0.5',
           'vat_pct':'15','destination_charges':'200','broker':'100','delivery':'100'}
        post=self.client.post(f'/operations/{op_id}/comparar',data=inputs)
        self.assertEqual(post.status_code,303,post.text[:800])
        post2=self.client.post(f'/operations/{op_id}/comparar',data={**inputs,'name':'Escenario B LCL','mode':'LCL','freight_rate':'250'})
        self.assertEqual(post2.status_code,303,post2.text[:800])
        view=self.client.get(f'/operations/{op_id}/comparar')
        self.assertEqual(view.status_code,200,view.text[:800])
        self.assertIn('Escenario A aéreo',view.text);self.assertIn('Escenario B LCL',view.text)
        with self.Session() as db:
            self.assertEqual(db.query(FreightComparison).filter_by(operation_id=op_id).count(),2)
        self.client.post('/logout')
        self.client.post('/login',data={'username':'plan_b','password':'pass123456'})
        self.assertEqual(self.client.get(f'/operations/{op_id}/comparar').status_code,403)
        self.assertEqual(self.client.post(f'/operations/{op_id}/comparar',data=inputs).status_code,403)
        self.assertEqual(self.client.get(f'/operations/{op_id}').status_code,403)
