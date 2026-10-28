"""Pruebas unitarias e integración para validación backend de cédulas.

Ejecutar desde la raíz del proyecto:
    python -m unittest discover -s tests -v
"""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.constants import PERSON_NATURAL, ROLE_IMPORTER
from app.database import Base
from app.models import User
from app.user_validation import es_cedula_ecuatoriana_valida, validate_user_profile


class TestCedulaEcuatoriana(unittest.TestCase):
    def test_rechaza_texto_letras_y_longitud(self):
        for cedula in ("ABC", "123", "12345678901", "123456789X", "１７０００００００１"):
            with self.subTest(cedula=cedula):
                self.assertFalse(es_cedula_ecuatoriana_valida(cedula))

    def test_rechaza_provincia_invalida(self):
        self.assertFalse(es_cedula_ecuatoriana_valida("0000000000"))
        self.assertFalse(es_cedula_ecuatoriana_valida("2500000000"))

    def test_rechaza_tercer_digito_invalido(self):
        self.assertFalse(es_cedula_ecuatoriana_valida("1760000000"))
        self.assertFalse(es_cedula_ecuatoriana_valida("3000000000"))

    def test_rechaza_digito_verificador_erroneo(self):
        self.assertFalse(es_cedula_ecuatoriana_valida("1700000002"))

    def test_serie_30_exterior(self):
        # Número sintético matemáticamente correcto de serie 30.
        self.assertTrue(es_cedula_ecuatoriana_valida("3040000006"))

    def test_acepta_formato_y_modulo_10_correctos(self):
        # Número sintético: supera la comprobación matemática, no acredita identidad.
        self.assertTrue(es_cedula_ecuatoriana_valida("1700000001"))

    def test_impide_guardar_perfil_con_cedula_incorrecta(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            values, errors = validate_user_profile(
                db,
                role=ROLE_IMPORTER,
                person_type=PERSON_NATURAL,
                username="usuario_prueba",
                full_name="Persona de prueba",
                cedula="ABC",
            )
            self.assertTrue(any("dígito" in error for error in errors))
            self.assertEqual(db.query(User).count(), 0)

    def test_mantiene_validacion_de_duplicados(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add(User(
                username="primero", password_hash="hash_de_prueba",
                role=ROLE_IMPORTER, person_type=PERSON_NATURAL,
                full_name="Persona inicial", cedula="1700000001",
            ))
            db.commit()
            _, errors = validate_user_profile(
                db,
                role=ROLE_IMPORTER,
                person_type=PERSON_NATURAL,
                username="segundo",
                full_name="Otra persona",
                cedula="1700000001",
            )
            self.assertIn("La cédula ya está registrada.", errors)


if __name__ == "__main__":
    unittest.main()
