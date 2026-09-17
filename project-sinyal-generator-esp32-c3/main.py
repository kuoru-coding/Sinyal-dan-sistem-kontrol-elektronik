# =========================================================
# main.py
# =========================================================

import config
from wifi_manager import connect_wifi
from signal import SignalGenerator, SignalScope
from web import run_server

def main():
    ip = connect_wifi()
    if ip is None:
        print("Tidak bisa lanjut tanpa koneksi WiFi. Cek config.py.")
        return

    gen = None
    scope = None

    try:
        if config.DEVICE_MODE == "GENERATOR":
            gen = SignalGenerator()
            gen.start()
            print("Signal generator (PWM) aktif.")
            print("Buka http://{}/ di browser untuk mengatur sinyal.".format(ip))
            run_server("GENERATOR", generator=gen)

        elif config.DEVICE_MODE == "SCOPE":
            scope = SignalScope()
            scope.start()
            print("Osiloskop aktif.")
            print("Buka http://{}/ di browser untuk melihat grafik sinyal.".format(ip))
            run_server("SCOPE", scope=scope)

        else:
            print("DEVICE_MODE tidak dikenali:", config.DEVICE_MODE)

    except KeyboardInterrupt:
        print("\nProgram dihentikan oleh user.")
        if gen: gen.stop()
        if scope: scope.stop()
    except Exception as e:
        print("Error sistem:", e)
        if gen: gen.stop()
        if scope: scope.stop()

if __name__ == '__main__':
    main()