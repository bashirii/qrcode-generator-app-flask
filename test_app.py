
import unittest
import json
from app import app, create_database

class TestQRCodeGenerator(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        create_database()

    def test_generate_qr_code(self):
        response = self.app.post('/generate', data={'content': 'https://example.com'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('id', data)
        self.assertIn('filename', data)

    def test_list_qr_codes(self):
        response = self.app.get('/list')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIsInstance(data, list)

    def test_increment_scan_count(self):
        # First, generate a QR code
        generate_response = self.app.post('/generate', data={'content': 'https://example.com'})
        generate_data = json.loads(generate_response.data)
        qr_id = generate_data['id']

        # Now, increment the scan count
        response = self.app.get(f'/increment/{qr_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])

    def test_swagger_documentation(self):
        response = self.app.get('/apidocs/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Swagger UI', response.data)

if __name__ == '__main__':
    unittest.main()

