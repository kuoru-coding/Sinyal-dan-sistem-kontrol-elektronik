# =====================================================================
#  ESP32 Web-Based Intelligent Control System  (MicroPython)
#  Controller : PID (anti-windup, derivative on measurement, output limit)
#  DAC output : GPIO25 (DAC1)      ADC feedback : GPIO33 (ADC1_CH5)
#  Sampling   : 500 ms
#  GUI        : index.html (disajikan oleh web server ESP32)
# =====================================================================
import network, time, json, gc
from machine import Pin, ADC, DAC
from array import array
import uasyncio as asyncio

# ---------------------------- KONFIGURASI ----------------------------
WIFI_SSID = "NAMA_WIFI_ANDA"      # <-- ganti
WIFI_PASS = "PASSWORD_WIFI_ANDA"  # <-- ganti
AP_SSID   = "ESP32-CONTROL"       # dipakai jika gagal konek WiFi (mode AP)
AP_PASS   = "12345678"

TS_MS   = 500          # periode sampling (ms)
VREF    = 3.3          # tegangan referensi DAC (V)
SP_MIN  = 0.0
SP_MAX  = 3.3          # sesuaikan dengan batas aman rangkaian
HIST_N  = 300          # jumlah sampel yang disimpan di ESP32 (untuk CSV)

# --------------------------- HARDWARE I/O ----------------------------
adc = ADC(Pin(33))
adc.atten(ADC.ATTN_11DB)          # rentang ~0 - 3.3 V
try:
    adc.width(ADC.WIDTH_12BIT)
except AttributeError:
    pass
dac = DAC(Pin(25))                # 8-bit: 0..255 -> 0..3.3 V


def read_adc_volt():
    """Rata-rata 16 pembacaan untuk menekan noise ADC."""
    n = 16
    s = 0
    try:
        for _ in range(n):
            s += adc.read_uv()
        return (s / n) / 1e6
    except AttributeError:        # firmware lama tanpa read_uv()
        for _ in range(n):
            s += adc.read()
        return (s / n) * VREF / 4095.0


def write_dac_volt(v):
    """Tulis tegangan ke DAC, kembalikan tegangan aktual (terkuantisasi)."""
    code = int(v / VREF * 255 + 0.5)
    code = 0 if code < 0 else (255 if code > 255 else code)
    dac.write(code)
    return code * VREF / 255.0


# ------------------------------ PID ----------------------------------
class PID:
    def __init__(self, kp, ki, kd, umin, umax):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.umin, self.umax = umin, umax
        self.reset()

    def reset(self):
        self.integral = 0.0
        self.prev_pv = None
        self.d_filt = 0.0

    def update(self, sp, pv, dt):
        e = sp - pv
        # ---- Integral + anti-windup (clamping pada suku integral) ----
        self.integral += e * dt
        if self.ki > 0:
            lo, hi = self.umin / self.ki, self.umax / self.ki
            if self.integral < lo:
                self.integral = lo
            elif self.integral > hi:
                self.integral = hi
        # ---- Derivative pada pengukuran (tanpa derivative kick) ----
        if self.prev_pv is None:
            d = 0.0
        else:
            d = -(pv - self.prev_pv) / dt
        self.prev_pv = pv
        self.d_filt = 0.7 * self.d_filt + 0.3 * d      # low-pass sederhana
        # ---- Output PID + pembatasan ----
        u = self.kp * e + self.ki * self.integral + self.kd * self.d_filt
        if u < self.umin:
            u = self.umin
        elif u > self.umax:
            u = self.umax
        return e, u


# ------------------------------ STATE --------------------------------
class S:
    sp = 0.0
    pv = 0.0
    err = 0.0
    u = 0.0
    running = False
    k = 0                 # nomor sampel
    ip = "0.0.0.0"


pid = PID(kp=1.0, ki=0.5, kd=0.0, umin=0.0, umax=VREF)

# ring buffer riwayat (array 'f' hemat RAM)
h_t = array('f', [0.0] * HIST_N)
h_sp = array('f', [0.0] * HIST_N)
h_pv = array('f', [0.0] * HIST_N)
h_u = array('f', [0.0] * HIST_N)
h_e = array('f', [0.0] * HIST_N)
h_run = array('b', [0] * HIST_N)
h_count = 0


def log_sample(t):
    global h_count
    i = h_count % HIST_N
    h_t[i], h_sp[i], h_pv[i] = t, S.sp, S.pv
    h_u[i], h_e[i], h_run[i] = S.u, S.err, 1 if S.running else 0
    h_count += 1


# --------------------------- LOOP KONTROL ----------------------------
async def control_loop():
    dt = TS_MS / 1000.0
    nxt = time.ticks_ms()
    while True:
        S.pv = read_adc_volt()
        if S.running:
            S.err, u = pid.update(S.sp, S.pv, dt)
            S.u = write_dac_volt(u)
        else:
            S.err = S.sp - S.pv
            S.u = write_dac_volt(0.0)
        log_sample(S.k * dt)
        S.k += 1
        nxt = time.ticks_add(nxt, TS_MS)
        wait = time.ticks_diff(nxt, time.ticks_ms())
        await asyncio.sleep_ms(wait if wait > 0 else 0)


# ----------------------------- WEB SERVER ----------------------------
def parse_qs(path):
    q = {}
    if "?" in path:
        for pair in path.split("?", 1)[1].split("&"):
            if "=" in pair:
                a, b = pair.split("=", 1)
                q[a] = b
    return q


def fnum(q, key, default):
    try:
        return float(q[key])
    except (KeyError, ValueError):
        return default


def snapshot():
    return json.dumps({
        "k": S.k, "t": round(S.k * TS_MS / 1000.0, 2),
        "sp": round(S.sp, 3), "pv": round(S.pv, 3),
        "e": round(S.err, 3), "u": round(S.u, 3),
        "run": 1 if S.running else 0,
        "kp": pid.kp, "ki": pid.ki, "kd": pid.kd,
        "ctrl": "PID", "ip": S.ip, "ts": TS_MS,
    })


async def send(w, status, ctype, body, extra=""):
    if isinstance(body, str):
        body = body.encode()
    w.write(("HTTP/1.1 %s\r\nContent-Type: %s\r\nContent-Length: %d\r\n"
             "Cache-Control: no-store\r\nConnection: close\r\n%s\r\n"
             % (status, ctype, len(body), extra)).encode())
    w.write(body)
    await w.drain()


async def send_file(w, fname):
    try:
        f = open(fname, "rb")
    except OSError:
        await send(w, "404 Not Found", "text/plain", "index.html tidak ada di ESP32")
        return
    import os
    size = os.stat(fname)[6]
    w.write(("HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n"
             "Content-Length: %d\r\nConnection: close\r\n\r\n" % size).encode())
    while True:
        chunk = f.read(512)
        if not chunk:
            break
        w.write(chunk)
        await w.drain()
    f.close()


def csv_rows():
    yield "k,time_s,setpoint_V,adc_V,error_V,dac_V,running\n"
    n = h_count if h_count < HIST_N else HIST_N
    start = 0 if h_count < HIST_N else h_count % HIST_N
    for j in range(n):
        i = (start + j) % HIST_N
        yield "%d,%.2f,%.3f,%.3f,%.3f,%.3f,%d\n" % (
            h_count - n + j, h_t[i], h_sp[i], h_pv[i], h_e[i], h_u[i], h_run[i])


async def handle(r, w):
    try:
        line = await r.readline()
        if not line:
            return
        parts = line.decode().split()
        path = parts[1] if len(parts) > 1 else "/"
        while True:                                  # buang header
            h = await r.readline()
            if not h or h == b"\r\n":
                break
        route = path.split("?")[0]
        q = parse_qs(path)

        if route == "/":
            await send_file(w, "index.html")
        elif route == "/data":
            await send(w, "200 OK", "application/json", snapshot())
        elif route == "/set":
            v = fnum(q, "sp", S.sp)
            S.sp = max(SP_MIN, min(SP_MAX, v))
            await send(w, "200 OK", "application/json", snapshot())
        elif route == "/params":
            pid.kp = max(0.0, fnum(q, "kp", pid.kp))
            pid.ki = max(0.0, fnum(q, "ki", pid.ki))
            pid.kd = max(0.0, fnum(q, "kd", pid.kd))
            await send(w, "200 OK", "application/json", snapshot())
        elif route == "/ctl":
            S.running = (q.get("run", "0") == "1")
            if S.running:
                pid.reset()
            await send(w, "200 OK", "application/json", snapshot())
        elif route == "/reset":
            global h_count
            S.running = False
            S.sp = 0.0
            pid.reset()
            h_count = 0
            S.k = 0
            await send(w, "200 OK", "application/json", snapshot())
        elif route == "/csv":
            body = "".join(csv_rows())
            await send(w, "200 OK", "text/csv", body,
                       'Content-Disposition: attachment; filename="data_praktikum.csv"\r\n')
        else:
            await send(w, "404 Not Found", "text/plain", "Not found")
    except Exception as ex:
        print("handler error:", ex)
    finally:
        try:
            await w.wait_closed()
        except Exception:
            pass
        gc.collect()


# ------------------------------- WIFI --------------------------------
def start_wifi():
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.connect(WIFI_SSID, WIFI_PASS)
    t0 = time.ticks_ms()
    while not sta.isconnected() and time.ticks_diff(time.ticks_ms(), t0) < 15000:
        time.sleep_ms(250)
    if sta.isconnected():
        return sta.ifconfig()[0]
    sta.active(False)
    ap = network.WLAN(network.AP_IF)       # fallback: ESP32 jadi Access Point
    ap.active(True)
    ap.config(essid=AP_SSID, password=AP_PASS)
    return ap.ifconfig()[0]


async def main():
    S.ip = start_wifi()
    print("Buka di browser:  http://%s/" % S.ip)
    asyncio.create_task(control_loop())
    await asyncio.start_server(handle, "0.0.0.0", 80)
    while True:
        await asyncio.sleep(3600)


try:
    asyncio.run(main())
finally:
    try:
        dac.write(0)                       # aman: DAC ke 0 V saat program berhenti
    except Exception:
        pass
    asyncio.new_event_loop()
