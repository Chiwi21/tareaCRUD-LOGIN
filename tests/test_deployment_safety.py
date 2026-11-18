"""Pruebas del inicializador seguro de Render (sin conexión a la nube)."""
import os
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, text

import prepare_production


class DeploymentSafetyTests(unittest.TestCase):
    def test_rejects_insecure_production_configuration(self):
        env = {
            "APP_ENV": "production",
            "DATABASE_URL": "postgresql://owner:password@example.test/db",
            "SECRET_KEY": "x" * 40,
            "ADMIN_PASSWORD": "admin123",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SystemExit):
                prepare_production.check_production_settings()

    def test_accepts_valid_production_settings(self):
        env = {
            "APP_ENV": "production",
            "DATABASE_URL": "postgresql://owner:password@example.test/db",
            "SECRET_KEY": "x" * 40,
            "ADMIN_PASSWORD": "EstaEsUnaClaveDePruebaSegura!123",
        }
        with patch.dict(os.environ, env, clear=True):
            prepare_production.check_production_settings()

    def test_rejects_legacy_schema_without_deleting_users(self):
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(50))"))
            conn.execute(text("INSERT INTO users (id, username) VALUES (1, 'usuario_conservado')"))
        with patch.object(prepare_production, "engine", engine):
            with self.assertRaises(SystemExit) as error:
                prepare_production.ensure_schema_is_compatible()
        self.assertIn("esquema anterior", str(error.exception))
        with engine.connect() as conn:
            value = conn.execute(text("SELECT username FROM users WHERE id=1")).scalar_one()
        self.assertEqual(value, "usuario_conservado")

    def test_empty_database_passes_schema_check(self):
        engine = create_engine("sqlite:///:memory:")
        with patch.object(prepare_production, "engine", engine):
            prepare_production.ensure_schema_is_compatible()


if __name__ == "__main__":
    unittest.main()
