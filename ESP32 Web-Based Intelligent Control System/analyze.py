"""
Analisis respons sistem dari CSV yang diunduh lewat tombol "Download CSV" di GUI.

Pemakaian:
    pip install pandas numpy matplotlib
    python analyze.py data_praktikum.csv            # semua perubahan setpoint
    python analyze.py data_praktikum.csv --tol 0.02 # toleransi settling (default 2%)

Keluaran:
    hasil_metrik.csv   -> tabel metrik per pengujian (masuk ke BAB 4/5)
    grafik_respons.png -> Setpoint vs ADC (+ error & DAC)
    grafik_stepN.png   -> grafik tiap segmen setpoint
"""
import sys
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TS = 0.5  # detik


def first_crossing(t, y, level, rising):
    """Waktu pertama y melewati 'level' (interpolasi linear)."""
    for i in range(1, len(y)):
        a, b = y[i - 1], y[i]
        hit = (a < level <= b) if rising else (a > level >= b)
        if hit:
            return t[i - 1] + (level - a) / (b - a) * (t[i] - t[i - 1])
    return np.nan


def analyze_segment(t, sp, pv, pv0, tol, floor=0.03):
    """t dimulai dari 0 saat setpoint berubah. pv0 = nilai PV sebelum step."""
    target = sp[-1]
    n_tail = max(4, len(pv) // 10)
    final = float(np.mean(pv[-n_tail:]))               # nilai steady (rata-rata ekor)
    step = final - pv0
    rising = target >= pv0
    ess = target - final

    if target != 0:
        mp = ((pv.max() - target) / target * 100) if rising else ((target - pv.min()) / target * 100)
        mp = max(0.0, mp)
    else:
        mp = np.nan

    # rise time 10% -> 90% dari perubahan menuju nilai akhir
    if abs(step) > 1e-6:
        t10 = first_crossing(t, pv, pv0 + 0.1 * step, rising)
        t90 = first_crossing(t, pv, pv0 + 0.9 * step, rising)
        tr = t90 - t10
    else:
        tr = np.nan

    # settling time: waktu terakhir keluar dari pita +-tol
    band = max(tol * abs(target), floor)
    out = np.where(np.abs(pv - target) > band)[0]
    if len(out) == 0:
        ts = 0.0
    elif out[-1] >= len(pv) - 1:
        ts = np.nan                                     # belum settle di dalam data
    else:
        ts = t[out[-1] + 1]

    return dict(setpoint_V=target, PV_awal_V=pv0, PV_akhir_V=final,
                ess_V=ess, ess_persen=(ess / target * 100) if target else np.nan,
                overshoot_persen=mp, rise_time_s=tr, settling_time_s=ts,
                pita_toleransi_V=band)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--tol", type=float, default=0.02)
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    df = df[df["running"] == 1].reset_index(drop=True) if (df["running"] == 1).any() else df
    t_all = df["time_s"].to_numpy()
    sp = df["setpoint_V"].to_numpy()
    pv = df["adc_V"].to_numpy()

    # deteksi perubahan setpoint
    idx = [0] + [i for i in range(1, len(sp)) if abs(sp[i] - sp[i - 1]) > 1e-6] + [len(sp)]
    rows = []
    for n in range(len(idx) - 1):
        a, b = idx[n], idx[n + 1]
        if b - a < 6:
            continue
        pv0 = pv[a - 1] if a > 0 else pv[a]
        t = t_all[a:b] - t_all[a]
        m = analyze_segment(t, sp[a:b], pv[a:b], pv0, args.tol)
        m = {"pengujian": len(rows) + 1, **m}
        rows.append(m)

        plt.figure(figsize=(7, 3.4))
        plt.step(t, sp[a:b], where="post", label="Set Point", color="tab:orange")
        plt.plot(t, pv[a:b], label="ADC GPIO33", color="tab:blue")
        plt.axhline(m["setpoint_V"] + m["pita_toleransi_V"], ls=":", c="gray", lw=0.8)
        plt.axhline(m["setpoint_V"] - m["pita_toleransi_V"], ls=":", c="gray", lw=0.8)
        plt.xlabel("Waktu (s)"); plt.ylabel("Tegangan (V)")
        plt.title("Pengujian %d: SP = %.2f V" % (m["pengujian"], m["setpoint_V"]))
        plt.grid(alpha=0.3); plt.legend(); plt.tight_layout()
        plt.savefig("grafik_step%d.png" % m["pengujian"], dpi=150); plt.close()

    res = pd.DataFrame(rows).round(3)
    res.to_csv("hasil_metrik.csv", index=False)
    print(res.to_string(index=False))

    fig, ax = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    ax[0].step(t_all, sp, where="post", label="Set Point", color="tab:orange")
    ax[0].plot(t_all, pv, label="ADC GPIO33", color="tab:blue")
    ax[0].set_ylabel("Tegangan (V)"); ax[0].legend(); ax[0].grid(alpha=0.3)
    ax[1].plot(t_all, df["error_V"], label="Error", color="tab:green")
    ax[1].plot(t_all, df["dac_V"], label="Output DAC", color="tab:purple")
    ax[1].set_xlabel("Waktu (s)"); ax[1].set_ylabel("Tegangan (V)")
    ax[1].legend(); ax[1].grid(alpha=0.3)
    plt.tight_layout(); plt.savefig("grafik_respons.png", dpi=150)
    print("\nTersimpan: hasil_metrik.csv, grafik_respons.png, grafik_step*.png")


if __name__ == "__main__":
    main()
    