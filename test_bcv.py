import unittest
from main import obtener_datos_bcv

class TestBCV(unittest.TestCase):
    def test_obtener_datos(self):
        print("\nProbando conexión con el BCV...")
        # Ahora devuelve 5 valores: usd, eur, prev_usd, prev_eur, offline
        usd, eur, _, _, _ = obtener_datos_bcv()
        
        print(f"Tasa USD obtenida: {usd}")
        print(f"Tasa EUR obtenida: {eur}")
        
        # Verificamos que los valores sean números positivos
        self.assertIsInstance(usd, float)
        self.assertIsInstance(eur, float)
        
        # Si el sitio está caído, devuelve 0.0, pero idealmente queremos valores reales
        if usd == 0.0:
            print("⚠️ Advertencia: No se pudo obtener la tasa (posible bloqueo o caída del sitio).")
        else:
            self.assertGreater(usd, 0.0)
            self.assertGreater(eur, 0.0)

if __name__ == "__main__":
    unittest.main()
