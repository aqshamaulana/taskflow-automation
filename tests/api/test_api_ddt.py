import pytest
import requests
import json
import os

# --- Konfigurasi URL dan Path ---
API_URL = "http://127.0.0.1:8000/api/tasks"

# Mendapatkan path absolut ke file JSON agar tidak error saat dipanggil dari root folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, "task_test_data.json")

def load_test_data():
    """Fungsi untuk membaca data dari file JSON"""
    with open(JSON_FILE, 'r', encoding='utf-8') as file:
        return json.load(file)

class TestTaskAPI_DataDriven:
    """Test Suite untuk Challenge 3: Data-Driven Testing"""
    
    @pytest.mark.parametrize("test_case", load_test_data())
    def test_create_task_dynamic(self, test_case):
        # Ekstrak data dari JSON
        test_name = test_case["name"]
        payload = test_case["payload"]
        expected_status = test_case["expected_status"]
        
        # 1. Eksekusi Request API (Kirim Data)
        response = requests.post(API_URL, json=payload)
        
        # 2. Verifikasi Hasil
        assert response.status_code == expected_status, \
            f"Gagal di {test_name}. Harapannya {expected_status}, tapi dapat {response.status_code}. Detail: {response.text}"
        
        # 3. Validasi tambahan jika testnya Valid (201)
        if expected_status == 201:
            json_resp = response.json()
            assert "id" in json_resp, "Response sukses tidak memiliki ID task"
            assert json_resp["title"] == payload["title"], "Judul task tidak sesuai dengan yang dikirim"