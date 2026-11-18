"""Comprobación básica del login visual sin base de datos ni servicios externos."""
import unittest
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]

class LoginVisualTests(unittest.TestCase):
    def test_login_template_uses_existing_form_contract(self):
        s = (ROOT / 'app/templates/auth/login.html').read_text(encoding='utf-8')
        for expected in ['action="/login"', 'name="username"', 'name="password"', 'href="/register"', 'data-auth-slider', 'slide-1.svg', 'slide-2.svg', 'slide-3.svg']:
            self.assertIn(expected, s)
    def test_registration_keeps_existing_fields(self):
        s = (ROOT / 'app/templates/auth/register.html').read_text(encoding='utf-8')
        for field in ['full_name', 'cedula', 'email', 'password']:
            self.assertIn('name="'+field+'"', s)
    def test_templates_compile(self):
        env = Environment(loader=FileSystemLoader(ROOT / 'app/templates'))
        env.get_template('auth/login.html'); env.get_template('auth/register.html')

if __name__ == '__main__': unittest.main()
