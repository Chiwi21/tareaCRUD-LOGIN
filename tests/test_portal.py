"""Pruebas de la versión local International Trade, sin tocar Neon ni la DB real."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app
from app.models import SupportTicket, User, UserEmail
from app.core.import_estimator import calculate_import_costs
from app.user_validation import es_cedula_ecuatoriana_valida


class PortalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.engine = create_engine('sqlite:///' + str(Path(cls.tmp.name) / 'db.sqlite'), connect_args={'check_same_thread':False})
        @event.listens_for(cls.engine,'connect')
        def fk(conn,_):
            conn.execute('PRAGMA foreign_keys=ON')
        Base.metadata.create_all(cls.engine)
        cls.Factory = sessionmaker(bind=cls.engine)
        def override():
            db=cls.Factory()
            try:
                yield db
            finally:
                db.close()
        app.dependency_overrides[get_db]=override
        cls.client=TestClient(app,follow_redirects=False,raise_server_exceptions=False)
        cls.valid_cedula=next(f'{i:010d}' for i in range(1700000000,1700000300) if es_cedula_ecuatoriana_valida(f'{i:010d}'))
    @classmethod
    def tearDownClass(cls):
        cls.client.close();app.dependency_overrides.pop(get_db,None);cls.engine.dispose();cls.tmp.cleanup()

    def test_01_signup_and_email_login(self):
        resp=self.client.get('/register')
        self.assertEqual(resp.status_code,200,resp.text[:500]);self.assertIn('International Trade',resp.text)
        invalid=self.client.post('/register',data={'full_name':'Ana Pérez','cedula':'ABC','email':'ana@example.com','password':'abcdefghi'})
        self.assertEqual(invalid.status_code,400)
        resp=self.client.post('/register',data={'full_name':'Ana Pérez','cedula':self.valid_cedula,'email':'Ana@Example.com','password':'abcdefghi'})
        self.assertEqual(resp.status_code,303,resp.text[:500]);self.assertEqual(resp.headers['location'],'/login')
        db=self.Factory()
        try:
            acct=db.query(UserEmail).filter_by(email='ana@example.com').one()
            user=db.get(User,acct.user_id)
            self.assertEqual(user.full_name,'Ana Pérez');self.assertEqual(user.role,'IMPORTER')
        finally: db.close()
        duplicate=self.client.post('/register',data={'full_name':'Otra Persona','cedula':self.valid_cedula,'email':'ana@example.com','password':'abcdefghi'})
        self.assertEqual(duplicate.status_code,400)
        resp=self.client.post('/login',data={'username':'ana@example.com','password':'abcdefghi'})
        self.assertEqual(resp.status_code,303,resp.text[:500]);self.assertEqual(resp.headers['location'],'/dashboard')
    def test_02_dashboard_and_resources(self):
        dash=self.client.get('/dashboard')
        self.assertEqual(dash.status_code,200,dash.text[:700]);self.assertIn('International Trade',dash.text)
        self.assertIn('Calculadora de importación',dash.text)
        for route in ['/herramientas/calculadora','/informacion','/ayuda']:
            response=self.client.get(route)
            self.assertEqual(response.status_code,200,response.text[:700])
    def test_03_calculator(self):
        values={'quantity':'1000','unit_price':'5','freight':'1000','insurance_pct':'1','duty_pct':'10','fodinfa_pct':'0.5','vat_pct':'15','other':'500'}
        result=calculate_import_costs(values)
        self.assertEqual(str(result['total']),'8200.75')
        resp=self.client.post('/herramientas/calculadora',data=values)
        self.assertEqual(resp.status_code,200,resp.text[:700]);self.assertIn('8,200.75',resp.text)
        bad=self.client.post('/herramientas/calculadora',data={**values,'quantity':'-12'})
        self.assertEqual(bad.status_code,400)
    def test_04_help_ticket(self):
        resp=self.client.post('/ayuda',data={'subject':'Consulta de importación','message':'Necesito información sobre documentos para importar.'})
        self.assertEqual(resp.status_code,303,resp.text[:700]);self.assertEqual(resp.headers['location'],'/ayuda')
        db=self.Factory()
        try:
            self.assertEqual(db.query(SupportTicket).count(),1)
        finally: db.close()
        inbox=self.client.get('/admin/soporte')
        self.assertEqual(inbox.status_code,403)
