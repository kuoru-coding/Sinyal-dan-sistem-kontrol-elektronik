# =========================================================
# config.py (VERSI ESP32 MINI TANPA DAC)
# =========================================================

DEVICE_MODE = "GENERATOR"   # Pilihan: "GENERATOR" atau "SCOPE"

# --- WiFi (Station Mode) ---
WIFI_SSID = "Holding On You"
WIFI_PASSWORD = "danudanu"
WIFI_CONNECT_TIMEOUT = 15

# --- Pin Hardware ESP32 MINI ---
# Karena tidak ada DAC, kita pakai PWM_PIN.
# (Disarankan pakai GPIO angka kecil, pastikan tertulis di board)
PWM_PIN = 5   # Pin untuk GENERATOR (Gunakan GPIO 5)

# Gunakan pin ADC1 (Untuk ESP32-C3 biasanya GPIO 0, 1, 2, 3, atau 4)
ADC_PIN = 0   # Pin untuk SCOPE (Gunakan GPIO 3)

# --- Parameter default sinyal (GENERATOR) ---
DEFAULT_WAVEFORM = "sine"
DEFAULT_FREQUENCY = 10       # Hz (PWM via Timer sedikit lambat, ideal di frekuensi rendah)
DEFAULT_AMPLITUDE = 150      # Input web 0-255 (akan dikonversi ke resolusi PWM otomatis)
WAVE_TABLE_SIZE = 64         # Resolusi gelombang

# --- Parameter default pembacaan (SCOPE) ---
SAMPLE_RATE_HZ = 2000
BUFFER_SIZE = 200

# --- Web server ---
WEB_PORT = 80