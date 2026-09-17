# =========================================================
# wifi_manager.py
# =========================================================

import network
import time
import config

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    
    # Matikan WiFi sejenak untuk me-reset state jaringan sebelumnya
    wlan.active(False)
    time.sleep(0.5)
    wlan.active(True)

    if not wlan.isconnected():
        print("Menghubungkan ke WiFi: {}".format(config.WIFI_SSID))
        wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)

        start = time.time()
        while not wlan.isconnected():
            if time.time() - start > config.WIFI_CONNECT_TIMEOUT:
                print("\nGagal konek WiFi (timeout). Cek SSID/password.")
                wlan.active(False)
                return None
            time.sleep(0.5)
            print(".", end="")

    ip = wlan.ifconfig()[0]
    print("\nWiFi tersambung! IP address:", ip)
    return ip