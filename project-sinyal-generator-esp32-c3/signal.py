# =========================================================
# signal.py (VERSI ESP32 MINI)
# =========================================================

import math
import micropython
from machine import Pin, PWM, ADC, Timer
import config

micropython.alloc_emergency_exception_buf(100)

def _build_table(waveform, amplitude, size):
    table = []
    # Amplitude dari web adalah 0-255.
    # PWM duty_u16 di MicroPython butuh nilai 0 - 65535.
    for i in range(size):
        phase = i / size
        if waveform == "sine":
            val = (math.sin(2 * math.pi * phase) + 1) / 2 * amplitude
        elif waveform == "square":
            val = amplitude if phase < 0.5 else 0
        elif waveform == "triangle":
            val = amplitude * (1 - abs(2 * phase - 1))
        else:
            val = 0
            
        # Konversi skala 0-255 menjadi 0-65535
        val_u16 = int((val / 255) * 65535)
        # Pastikan tidak keluar batas
        val_u16 = max(0, min(65535, val_u16))
        table.append(val_u16)
    return table

class SignalGenerator:
    """Membangkitkan sinyal lewat PWM (Simulasi DAC)"""
    def __init__(self):
        # Setup PWM dengan frekuensi carrier tinggi (misal 50kHz) agar mudah di-filter
        self.pwm = PWM(Pin(config.PWM_PIN))
        self.pwm.freq(50000) 
        self.pwm.duty_u16(0)
        
        self.waveform = config.DEFAULT_WAVEFORM
        self.frequency = config.DEFAULT_FREQUENCY
        self.amplitude = config.DEFAULT_AMPLITUDE
        self.table_size = config.WAVE_TABLE_SIZE
        self._index = 0
        self._table = _build_table(self.waveform, self.amplitude, self.table_size)
        self._timer = Timer(0)
        self._running = False

    def _tick(self, t):
        # Update nilai tegangan PWM secara berkala
        self.pwm.duty_u16(self._table[self._index])
        self._index = (self._index + 1) % self.table_size

    def start(self):
        self._apply_timer()
        self._running = True

    def stop(self):
        self._timer.deinit()
        self.pwm.duty_u16(0)
        self._running = False

    def set_params(self, waveform=None, frequency=None, amplitude=None):
        was_running = self._running
        if was_running:
            self._timer.deinit()
            
        if waveform is not None: self.waveform = waveform
        if frequency is not None: self.frequency = frequency
        if amplitude is not None: self.amplitude = amplitude
        
        self._table = _build_table(self.waveform, self.amplitude, self.table_size)
        self._index = 0
        
        if was_running:
            self._apply_timer()

    def _apply_timer(self):
        timer_freq = max(1, int(self.frequency * self.table_size))
        self._timer.init(freq=timer_freq, mode=Timer.PERIODIC, callback=self._tick)

    def get_status(self):
        return {
            "waveform": self.waveform,
            "frequency": self.frequency,
            "amplitude": self.amplitude,
            "running": self._running,
        }

class SignalScope:
    """Membaca sinyal analog (Sama seperti sebelumnya)"""
    def __init__(self):
        self.adc = ADC(Pin(config.ADC_PIN))
        self.adc.atten(ADC.ATTN_11DB)
        self.adc.width(ADC.WIDTH_12BIT)
        self.buffer_size = config.BUFFER_SIZE
        self._buffer = [0] * self.buffer_size
        self._index = 0
        self._timer = Timer(1)
        self._running = False

    def _tick(self, t):
        self._buffer[self._index] = self.adc.read()
        self._index = (self._index + 1) % self.buffer_size

    def start(self):
        self._timer.init(freq=config.SAMPLE_RATE_HZ, mode=Timer.PERIODIC, callback=self._tick)
        self._running = True

    def stop(self):
        self._timer.deinit()
        self._running = False

    def get_buffer(self):
        idx = self._index
        return self._buffer[idx:] + self._buffer[:idx]