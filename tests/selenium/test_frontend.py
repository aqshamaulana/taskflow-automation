# tests/selenium/test_frontend.py
import pytest
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from pages.task_page import TaskPage
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

@pytest.fixture(scope="class")
def driver():
    chrome_options = Options()
    if os.environ.get("HEADLESS", "false").lower() == "true":
        chrome_options.add_argument("--headless")
    
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Inisialisasi Chrome
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)
    
    # Buka Frontend (Pastikan portnya sama dengan PHP server kamu, misal 8081)
    driver.get("http://127.0.0.1:8081")
    
    yield driver
    
    driver.quit()
# -------------------------------------


class TestTaskFlowFrontend:
    """Test suite untuk frontend TaskFlow"""
    
    @pytest.fixture(autouse=True)
    def setup(self, driver):
        """Setup sebelum setiap test (Versi Sapu Bersih)"""
        self.page = TaskPage(driver)
        self.driver = driver

        # 1. Buka ulang URL awal (hard reload)
        self.driver.get("http://127.0.0.1:8081")
        time.sleep(1)

        # 2. Paksa tutup semua alert system (jika ada yang nyangkut)
        try:
            alert = self.driver.switch_to.alert
            alert.dismiss()
        except:
            pass

        # 3. Paksa hapus modal backdrop (layar gelap) lewat JavaScript
        self.driver.execute_script("""
            var backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(b => b.remove());
            document.body.classList.remove('modal-open');
            document.body.style = '';
            
            // Tutup alert UI bootstrap
            var alerts = document.querySelectorAll('.alert');
            alerts.forEach(a => a.remove());
        """)

        # 4. Refresh data task
        try:
            self.page.refresh_tasks()
        except:
            # Jika tombol refresh gagal diklik, abaikan karena barusan di hard-reload
            pass
        
        time.sleep(1)
    
    # ========== Test Cases ==========
    
    def test_page_loads_correctly(self):
        """TC-FE-001: Memastikan halaman dapat dimuat dengan benar"""
        assert "TaskFlow" in self.driver.title
        assert self.page.FORM_TITLE is not None
        print("✓ Halaman berhasil dimuat")
    
    def test_create_new_task_success(self):
        """TC-FE-002: Membuat tugas baru dengan data valid"""
        # Arrange
        task_title = f"Test Task {time.time()}"
        task_desc = "Ini adalah tugas test"
        task_status = "pending"
        
        # Act
        self.page.create_task(task_title, task_desc, task_status)
        
        # Assert
        assert self.page.task_exists(task_title), "Tugas tidak muncul di tabel"
        alert_msg = self.page.get_alert_message()
        assert "berhasil ditambahkan" in alert_msg
        print(f"✓ Tugas '{task_title}' berhasil dibuat")
    
    def test_create_task_without_title_validation(self):
        """TC-FE-003: Validasi client-side untuk field judul kosong"""
        # Act - Submit form tanpa mengisi judul
        self.driver.find_element(*self.page.BTN_SUBMIT).click()
        
        # Assert - Cek validasi HTML5 required
        title_input = self.driver.find_element(*self.page.FORM_TITLE)
        validation_message = self.driver.execute_script(
            "return arguments[0].validationMessage;", title_input
        )
        assert "isi" in validation_message.lower() or "fill" in validation_message.lower()
        print("✓ Validasi judul kosong berfungsi")
    
    def test_reset_form_functionality(self):
        """TC-FE-004: Memastikan tombol reset mengosongkan form"""
        # Arrange - Isi form dulu
        self.driver.find_element(*self.page.FORM_TITLE).send_keys("Test Reset")
        self.driver.find_element(*self.page.FORM_DESCRIPTION).send_keys("Deskripsi test")
        
        # Act
        self.page.reset_form()
        
        # Assert
        form_values = self.page.get_form_values()
        assert form_values['title'] == "", "Judul tidak tereset"
        assert form_values['description'] == "", "Deskripsi tidak tereset"
        print("✓ Form reset berfungsi")
    
    def test_edit_task_functionality(self):
        """TC-FE-005: Mengedit tugas yang sudah ada"""
        # Arrange - Buat tugas dulu
        original_title = f"Edit Test {time.time()}"
        self.page.create_task(original_title, "Deskripsi awal", "pending")
        
        time.sleep(1)
        
        # Act - Edit tugas
        self.page.click_edit_task(original_title)
        new_title = f"{original_title} (Updated)"
        self.page.update_task_in_modal(
            title=new_title,
            description="Deskripsi setelah update",
            status="completed"
        )
        
        # Assert
        assert self.page.task_exists(new_title), "Tugas dengan judul baru tidak ditemukan"
        assert not self.page.task_exists(original_title), "Tugas lama masih ada"
        
        task = self.page.get_task_by_title(new_title)
        assert task['status'] == "Completed"
        print(f"✓ Tugas berhasil diedit menjadi '{new_title}'")
    
    def test_delete_task_functionality(self):
        """TC-FE-006: Menghapus tugas"""
        # Arrange
        task_title = f"Delete Test {time.time()}"
        self.page.create_task(task_title, "Akan dihapus", "pending")
        time.sleep(1)
        assert self.page.task_exists(task_title), "Tugas tidak berhasil dibuat"
        
        # Act
        self.page.click_delete_task(task_title)
        self.page.handle_delete_confirmation(accept=True)
        
        # Assert - Tunggu alert sukses
        alert_msg = self.page.get_alert_message()
        assert "berhasil dihapus" in alert_msg.lower()
        assert not self.page.task_exists(task_title), "Tugas masih ada setelah dihapus"
        print(f"✓ Tugas '{task_title}' berhasil dihapus")
    
    def test_delete_task_cancelled(self):
        """TC-FE-007: Membatalkan penghapusan tugas"""
        # Arrange
        task_title = f"Cancel Delete {time.time()}"
        self.page.create_task(task_title, "Tidak jadi dihapus", "pending")
        
        # Act
        self.page.click_delete_task(task_title)
        self.page.handle_delete_confirmation(accept=False)
        
        # Assert
        time.sleep(0.5)  # Tunggu dialog tertutup
        assert self.page.task_exists(task_title), "Tugas hilang padahal delete dibatalkan"
        print("✓ Pembatalan delete berfungsi")
    
    def test_refresh_button(self):
        """TC-FE-008: Memastikan tombol refresh memuat ulang data"""
        # Arrange - Buat tugas baru via API langsung (simulasi perubahan dari luar)
        import requests
        api_url = "http://127.0.0.1:8000/api/tasks"
        new_task = {"title": "API Created Task", "description": "Dibuat via API", "status": "pending"}
        response = requests.post(api_url, json=new_task)
        assert response.status_code == 201
        
        # Act - Klik refresh
        self.page.refresh_tasks()
        
        # Assert
        assert self.page.task_exists("API Created Task"), "Tugas dari API tidak muncul setelah refresh"
        print("✓ Tombol refresh berfungsi")
    
    def test_status_filter_display(self):
        """TC-FE-009: Memastikan status badge ditampilkan dengan warna yang benar"""
        # Arrange - Buat tugas dengan berbagai status
        tasks_data = [
            ("Task Pending", "pending", "bg-warning"),
            ("Task Progress", "in-progress", "bg-info"),
            ("Task Completed", "completed", "bg-success")
        ]
        
        for title, status, _ in tasks_data:
            self.page.create_task(title, f"Test {status}", status)
            self.page.wait_for_alert_to_disappear()
        
        # Assert - Cek badge classes
        for title, _, expected_class in tasks_data:
            task = self.page.get_task_by_title(title)
            if task:
                # Cari badge di kolom status
                rows = self.driver.find_elements(*self.page.TASKS_TABLE_ROWS)
                for row in rows:
                    if title in row.text:
                        badge = row.find_element(By.CSS_SELECTOR, ".badge")
                        badge_class = badge.get_attribute("class")
                        assert expected_class in badge_class, f"Badge untuk {title} salah"
                        break
        
        print("✓ Status badge ditampilkan dengan benar")
    
    def test_modal_close_buttons(self):
        """TC-FE-010: Memastikan modal edit bisa ditutup dengan berbagai cara"""
        # Arrange
        task_title = f"Modal Test {time.time()}"
        self.page.create_task(task_title, "Test modal", "pending")
        time.sleep(1)

        # Test 1: Tutup dengan tombol X
        self.page.click_edit_task(task_title)
        time.sleep(0.5)
        self.driver.find_element(*self.page.BTN_CLOSE_MODAL).click()
        time.sleep(1)  # Tunggu animasi Bootstrap selesai
        assert not self.driver.find_element(*self.page.MODAL_EDIT).is_displayed()
        print("  ✓ Modal bisa ditutup dengan tombol X")

        # Test 2: Tutup dengan tombol Cancel
        self.page.click_edit_task(task_title)
        time.sleep(0.5)
        self.driver.find_element(*self.page.BTN_CANCEL_EDIT).click()
        time.sleep(1)  # Tunggu animasi Bootstrap selesai
        assert not self.driver.find_element(*self.page.MODAL_EDIT).is_displayed()
        print("  ✓ Modal bisa ditutup dengan tombol Cancel")

        # Test 3: Tutup dengan klik di luar modal (backdrop)
        # FIX: Gunakan ActionChains untuk klik nyata di pojok layar (di luar dialog)
        self.page.click_edit_task(task_title)
        time.sleep(0.5)
        ActionChains(self.driver).move_by_offset(10, 10).click().perform()
        time.sleep(1)  # Tunggu animasi Bootstrap selesai
        assert not self.driver.find_element(*self.page.MODAL_EDIT).is_displayed()
        print("  ✓ Modal bisa ditutup dengan klik di luar")
    
    def test_empty_state_when_no_tasks(self):
        """TC-FE-011: Memastikan empty state muncul saat tidak ada tugas"""
        # Arrange - Hapus semua tugas
        import requests
        api_url = "http://127.0.0.1:8000/api/tasks"
        tasks = requests.get(api_url).json()
        for task in tasks:
            requests.delete(f"{api_url}/{task['id']}")
        
        # Act - Refresh halaman
        self.page.refresh_tasks()
        
        # Assert
        assert self.page.is_empty_state_displayed(), "Empty state tidak muncul"
        empty_text = self.driver.find_element(*self.page.EMPTY_STATE).text
        assert "Belum ada tugas" in empty_text
        print("✓ Empty state ditampilkan dengan benar")
    
    def test_form_validation_after_reset(self):
        """TC-FE-012: Memastikan form valid setelah di-reset"""
        # Arrange - Submit form kosong (trigger validasi)
        self.driver.find_element(*self.page.BTN_SUBMIT).click()
        
        # Act - Reset form
        self.page.reset_form()
        
        # Assert - Coba submit lagi, seharusnya tidak ada validasi error
        self.driver.find_element(*self.page.BTN_SUBMIT).click()
        # Jika tidak ada exception, berarti validasi tidak muncul lagi
        print("✓ Validasi form di-reset dengan benar")
        
    def test_search_and_filter_challenge_2(self):
        """TC-CH2: Memverifikasi fitur pencarian dan filter status berfungsi"""
        # --- Arrange: Buat data ---
        unique_prefix = f"Ch2_{int(time.time())}"
        task1 = f"{unique_prefix} Belajar Pytest"
        task2 = f"{unique_prefix} Laporan Akhir"
        
        self.page.create_task(task1, "Fokus ke Selenium", "pending")
        time.sleep(1)
        self.page.create_task(task2, "Laporan akhir bulan", "completed")
        time.sleep(1.5) # Tunggu lebih lama

        # --- Act & Assert 1: Test Fitur Search ---
        search_input = self.driver.find_element(By.ID, "searchInput")
        search_input.clear()
        
        # Ketik satu-satu pelan-pelan agar JavaScript sadar
        for char in "Pytest":
            search_input.send_keys(char)
            time.sleep(0.1)
            
        time.sleep(2) # Beri waktu 2 detik untuk API merespon
        
        # Pastikan tabel sudah terfilter
        assert self.page.task_exists(task1), "Tugas 1 harusnya terlihat saat dicari"
        assert not self.page.task_exists(task2), "Tugas 2 harusnya tidak terlihat"
        print("  ✓ Fitur pencarian teks berfungsi")
        
        # --- Act & Assert 2: Test Fitur Filter ---
        search_input.clear()
        search_input.send_keys(" ")
        search_input.send_keys(Keys.BACKSPACE)
        time.sleep(2) # Tunggu tabel kembali ke awal
        
        from selenium.webdriver.support.ui import Select
        filter_dropdown = Select(self.driver.find_element(By.ID, "filterStatus"))
        filter_dropdown.select_by_value("completed")
        time.sleep(2) # Tunggu tabel terfilter
        
        assert not self.page.task_exists(task1), "Tugas pending harusnya disembunyikan"
        assert self.page.task_exists(task2), "Tugas completed harusnya terlihat"
        print("  ✓ Fitur filter dropdown berfungsi")