"""Sound design for the Haadin Global ad: synthesized SFX + music bed, mixed under the original voice.

Usage: python3 audio.py <voice.wav (48k stereo)> <out.wav>
Times are seconds on the output timeline (identical to the source timeline up to 47.233s).
"""
import sys
import numpy as np
from scipy import signal
import wave

SR = 48000
TOTAL = 50.7
N = int(TOTAL * SR)
rng = np.random.default_rng(7)


def db(x):
    return 10 ** (x / 20)


def tt(d):
    return np.arange(int(d * SR)) / SR


def noise(d):
    return rng.standard_normal(int(d * SR))


def sos(kind, f, order=2):
    return signal.butter(order, f, btype=kind, fs=SR, output='sos')


def filt(x, kind, f, order=2):
    return signal.sosfilt(sos(kind, f, order), x)


def sweep_filter(x, f0, f1, kind='bandpass', q=1.5, curve='exp', block=256):
    """Time-varying filter: cutoff/centre moves from f0 to f1 across x (block-wise SVF)."""
    out = np.zeros_like(x)
    n = len(x)
    low = band = 0.0
    for s in range(0, n, block):
        u = s / max(1, n - 1)
        f = f0 * (f1 / f0) ** u if curve == 'exp' else f0 + (f1 - f0) * u
        F = 2 * np.sin(np.pi * min(f, SR / 6) / SR)
        Q = 1 / q
        seg = x[s:s + block]
        o = np.empty_like(seg)
        for i, v in enumerate(seg):
            low += F * band
            high = v - low - Q * band
            band += F * high
            o[i] = band if kind == 'bandpass' else (low if kind == 'lowpass' else high)
        out[s:s + block] = o
    return out


def env_ar(n, a, r, shape=2.0):
    """attack/release envelope over n samples, a and r in seconds."""
    t = np.arange(n) / SR
    e = np.ones(n)
    if a > 0:
        e *= np.clip(t / a, 0, 1)
    tail = np.clip((t - (n / SR - r)) / r, 0, 1) if r > 0 else 0
    return e * (1 - tail) ** shape


def norm(x, peak=1.0):
    m = np.max(np.abs(x)) + 1e-12
    return x / m * peak


def pan(x, p=0.0):
    """constant-power pan, p in [-1, 1]; x mono → (2, n)"""
    a = (p + 1) * np.pi / 4
    return np.vstack([x * np.cos(a), x * np.sin(a)])


def pan_sweep(x, p0, p1):
    pp = np.linspace(p0, p1, len(x))
    a = (pp + 1) * np.pi / 4
    return np.vstack([x * np.cos(a), x * np.sin(a)])


# ---------------- SFX ----------------

def whoosh(d=0.55, f0=300, f1=3500, peak_at=0.6, q=1.2):
    n = noise(d)
    x = sweep_filter(n, f0, f1, q=q)
    t = tt(d)
    pk = peak_at * d
    e = np.where(t < pk, (t / pk) ** 2.2, np.exp(-(t - pk) / (0.18 * d)))
    return norm(x * e, 0.9)


def reverse_whoosh(d=0.6):
    return whoosh(d, 400, 5000, peak_at=0.97, q=1.0)


def boom(d=1.6, f_hi=110, f_lo=38, decay=0.9):
    t = tt(d)
    f = f_lo + (f_hi - f_lo) * np.exp(-t * 9)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / decay * 2.2)
    click = filt(noise(d), 'lowpass', 2500) * np.exp(-t * 60) * 0.6
    rumble = filt(noise(d), 'lowpass', 160) * np.exp(-t * 3) * 0.5
    x = body + click + rumble
    return norm(np.tanh(x * 1.6), 0.95)


def thud(pitch=1.0):
    d = 0.4
    t = tt(d)
    f = (55 + 90 * np.exp(-t * 30)) * pitch
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 11)
    knock = filt(noise(d), 'bandpass', [300, 1800]) * np.exp(-t * 70) * 0.7
    return norm(np.tanh((body + knock) * 1.5), 0.9)


def pop(f=700, d=0.12):
    t = tt(d)
    fr = f * (1 + 0.6 * np.exp(-t * 60))
    x = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t * 38)
    click = filt(noise(d), 'highpass', 3000) * np.exp(-t * 400) * 0.25
    return norm(x + click, 0.8)


def blip_up(f=520, d=0.22):
    t = tt(d)
    fr = f * (1 + 1.0 * t / d)
    x = np.sin(2 * np.pi * np.cumsum(fr) / SR) + 0.3 * np.sin(4 * np.pi * np.cumsum(fr) / SR)
    return norm(x * np.exp(-t * 14) * np.clip(t / 0.005, 0, 1), 0.7)


def error_beep():
    out = []
    for f in (392, 294):
        t = tt(0.13)
        x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) + 0.15 * np.sin(2 * np.pi * 3 * f * t)
        x *= env_ar(len(t), 0.005, 0.05, 1.5)
        out += [x, np.zeros(int(0.03 * SR))]
    return norm(np.concatenate(out), 0.6)


def bonk():
    d = 0.3
    t = tt(d)
    f = 300 * np.exp(-t * 5)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14)
    return norm(x, 0.7)


def key_click(seed):
    d = 0.05
    r = np.random.default_rng(seed)
    t = tt(d)
    x = filt(r.standard_normal(len(t)), 'bandpass', [1800 + r.random() * 1500, 6000]) * np.exp(-t * 180)
    x += 0.4 * np.sin(2 * np.pi * (180 + r.random() * 60) * t) * np.exp(-t * 120)
    return norm(x, 0.7)


def crickets(d=1.6):
    t = tt(d)
    out = np.zeros((2, len(t)))
    for p, f, off in ((-0.6, 4600, 0.0), (0.6, 4300, 0.27)):
        chirp_env = np.zeros(len(t))
        c = off
        while c < d - 0.25:
            for k in range(4):
                s = int((c + k * 0.034) * SR)
                L = int(0.022 * SR)
                if s + L < len(t):
                    chirp_env[s:s + L] += np.sin(np.linspace(0, np.pi, L)) ** 2
            c += 0.62
        x = np.sin(2 * np.pi * f * t) * chirp_env
        out += pan(x, p)
    out *= env_ar(len(t), 0.25, 0.4)[None, :]
    return out / (np.max(np.abs(out)) + 1e-9) * 0.6


def stamp():
    x = thud(1.3) * 0.8
    d = len(x) / SR
    t = tt(d)
    tsk = filt(noise(d), 'bandpass', [2500, 7000]) * np.exp(-t * 45) * 0.35
    return norm(x + tsk, 0.9)


def glitch_zap(d=0.34):
    t = tt(d)
    x = np.zeros(len(t))
    pos = 0
    r = np.random.default_rng(3)
    while pos < len(t):
        L = int(r.uniform(0.012, 0.045) * SR)
        f = r.choice([180, 360, 720, 1440, 95])
        seg = np.sign(np.sin(2 * np.pi * f * np.arange(L) / SR)) * r.uniform(0.3, 1)
        if r.random() < 0.3:
            seg = r.standard_normal(L) * 0.6
        x[pos:pos + L] = seg[:max(0, min(L, len(t) - pos))]
        pos += L
    x = np.round(x * 6) / 6  # bit-crush
    x = filt(x, 'lowpass', 6000)
    return norm(x * env_ar(len(t), 0.003, 0.08), 0.6)


def power_down(d=0.75):
    t = tt(d)
    f = 420 * np.exp(-t * 2.8) + 40
    ph = 2 * np.pi * np.cumsum(f * (1 + 0.03 * np.sin(2 * np.pi * 9 * t))) / SR
    x = np.sin(ph) + 0.4 * np.sign(np.sin(ph)) * 0.3
    x = filt(x, 'lowpass', 1500)
    return norm(x * env_ar(len(t), 0.01, 0.3), 0.7)


def fwoosh(d=0.6):
    t = tt(d)
    x = filt(noise(d), 'highpass', 1500) * np.exp(-t * 7) * np.clip(t / 0.01, 0, 1)
    return norm(x, 0.7)


def riser(d=3.4):
    t = tt(d)
    nz = sweep_filter(noise(d), 300, 6000, q=2.5)
    f = 180 * (8 ** (t / d))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.5 * np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR)
    e = (t / d) ** 2.4
    x = (nz * 0.8 + tone * 0.25) * e
    x[-int(0.01 * SR):] *= np.linspace(1, 0, int(0.01 * SR))
    return norm(x, 0.8)


def bell(f=1046.5, d=1.6, decay=1.0):
    t = tt(d)
    x = np.zeros(len(t))
    for ratio, amp, dk in ((1, 1, 1), (2.0, 0.45, 1.6), (2.76, 0.35, 2.2), (5.4, 0.18, 3.5), (8.93, 0.08, 5)):
        x += amp * np.sin(2 * np.pi * f * ratio * t) * np.exp(-t * dk / decay * 2.5)
    x *= np.clip(t / 0.002, 0, 1)
    return norm(x, 0.7)


def ding():
    a = bell(1318.5, 1.6, 0.9)
    b = bell(1975.5, 1.6, 0.9)
    out = np.zeros(len(a) + int(0.09 * SR))
    out[:len(a)] += a
    out[int(0.09 * SR):] += b * 0.8
    return norm(out, 0.7)


def shimmer(d=1.2, n=28, lo=2500, hi=7500, seed=1):
    r = np.random.default_rng(seed)
    t = tt(d)
    out = np.zeros((2, len(t)))
    for _ in range(n):
        f = r.uniform(lo, hi)
        s = r.uniform(0, d * 0.5)
        tt_ = t - s
        x = np.where(tt_ > 0, np.sin(2 * np.pi * f * tt_) * np.exp(-np.clip(tt_, 0, None) * r.uniform(5, 10)), 0)
        out += pan(x * r.uniform(0.3, 1), r.uniform(-0.8, 0.8))
    out *= env_ar(len(t), 0.01, 0.5, 1)[None, :]
    return out / (np.max(np.abs(out)) + 1e-9) * 0.6


def notif(alt=0):
    fs = (1318.5, 1760.0) if alt == 0 else (1568.0, 2093.0)
    out = np.zeros(int(0.5 * SR))
    for i, f in enumerate(fs):
        t = tt(0.4)
        x = (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t * 11) * np.clip(t / 0.004, 0, 1)
        s = int(i * 0.085 * SR)
        out[s:s + len(x)] += x
    return norm(out, 0.7)


def loc_ping(f=880):
    t = tt(0.7)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 7) + 0.3 * np.sin(2 * np.pi * f * 1.5 * t) * np.exp(-t * 10)
    x *= np.clip(t / 0.003, 0, 1)
    return norm(x, 0.7)


def kaching():
    d = 1.4
    t = tt(d)
    ka = filt(noise(0.06), 'bandpass', [1500, 6000]) * np.exp(-tt(0.06) * 60)
    ching = np.zeros(len(t))
    for f, a in ((2093, 1), (2637, 0.7), (3136, 0.5), (4186, 0.35), (5274, 0.2)):
        ching += a * np.sin(2 * np.pi * f * t) * np.exp(-t * 3.2)
    rattle = filt(noise(d), 'bandpass', [4000, 9000]) * np.exp(-t * 18) * 0.25
    out = np.zeros(len(t) + int(0.07 * SR))
    out[:len(ka)] += ka * 0.8
    s = int(0.07 * SR)
    out[s:s + len(t)] += (ching + rattle) * np.clip(t / 0.002, 0, 1)
    return norm(out, 0.75)


def tick(f=1200):
    t = tt(0.09)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 55) + filt(noise(0.09), 'highpass', 4000) * np.exp(-t * 300) * 0.3
    return norm(x, 0.6)


def click():
    t = tt(0.06)
    x = filt(noise(0.06), 'bandpass', [1500, 7000]) * np.exp(-t * 250) + 0.5 * np.sin(2 * np.pi * 2200 * t) * np.exp(-t * 120)
    return norm(x, 0.8)


def crash(d=2.2):
    t = tt(d)
    x = filt(noise(d), 'highpass', 3500) * np.exp(-t * 2.2) * np.clip(t / 0.003, 0, 1)
    return norm(x, 0.6)


def reverse_cymbal(d=1.5):
    return crash(d)[::-1].copy()


def plane_flyby(d=1.3):
    t = tt(d)
    nz = sweep_filter(noise(d), 500, 2400, q=1.8, curve='lin')
    tone = np.sin(2 * np.pi * np.cumsum(220 * (1.25 - 0.4 * t / d)) / SR) * 0.15
    e = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 1.5
    return pan_sweep(norm((nz + tone) * e, 0.8), -0.85, 0.85)


# ---------------- reverb ----------------

def make_ir(d=1.8, seed=11):
    r = np.random.default_rng(seed)
    t = tt(d)
    e = np.exp(-t * 3.6)
    L = filt(r.standard_normal(len(t)), 'lowpass', 6000) * e
    R = filt(r.standard_normal(len(t)), 'lowpass', 6000) * e
    L[:int(0.01 * SR)] = 0
    R[:int(0.013 * SR)] = 0
    return L / np.sqrt(np.sum(L ** 2)), R / np.sqrt(np.sum(R ** 2))


IR = make_ir()


def reverb(st, wet=0.25):
    L = signal.fftconvolve(st[0], IR[0])[:st.shape[1]]
    R = signal.fftconvolve(st[1], IR[1])[:st.shape[1]]
    return st + wet * np.vstack([L, R]) * 3


# ---------------- music ----------------
BPM = 120
BEAT = 60 / BPM
DROP = 23.55  # bar line where the groove drops


def midi(n):
    return 440 * 2 ** ((n - 69) / 12)


def polyblep_saw(f, n, phase0=0.0):
    dt = f / SR
    ph = (phase0 + np.arange(n) * dt) % 1.0
    s = 2 * ph - 1
    m1 = ph < dt
    x = ph[m1] / dt
    s[m1] -= x + x - x * x - 1
    m2 = ph > 1 - dt
    x = (ph[m2] - 1) / dt
    s[m2] -= x * x + x + x + 1
    return s


def pad_note(notes, d, cutoff=1600, detune=(-0.09, 0, 0.11)):
    n = int(d * SR)
    x = np.zeros(n)
    for m in notes:
        for dc in detune:
            x += polyblep_saw(midi(m + dc), n, rng.random())
    x = filt(x, 'lowpass', cutoff, 2)
    return x / (len(notes) * len(detune))


def pluck(f, d=0.45, bright=1.0):
    t = tt(d)
    x = np.zeros(len(t))
    for k in range(1, 18):
        if f * k > 12000:
            break
        x += (1 / k) * np.sin(2 * np.pi * f * k * t) * np.exp(-t * (6 + 2.2 * k / bright))
    return x * np.clip(t / 0.002, 0, 1)


def kick():
    d = 0.42
    t = tt(d)
    f = 48 + 110 * np.exp(-t * 32)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7.5)
    x += filt(noise(d), 'highpass', 2000) * np.exp(-t * 300) * 0.15
    return np.tanh(x * 1.4)


def clap():
    d = 0.25
    t = tt(d)
    base = filt(noise(d), 'bandpass', [900, 3200])
    e = np.zeros(len(t))
    for o in (0, 0.011, 0.022):
        e += np.where(t >= o, np.exp(-(t - o) * 140), 0)
    e += np.where(t >= 0.03, np.exp(-(t - 0.03) * 22), 0) * 0.7
    return base * e * 0.6


def hat(open_=False):
    d = 0.22 if open_ else 0.06
    t = tt(d)
    return filt(noise(d), 'highpass', 7500) * np.exp(-t * (14 if open_ else 80)) * 0.5


def place(buf, x, t0, gain=1.0):
    """add mono or stereo x into stereo buf at t0 seconds."""
    if x.ndim == 1:
        x = np.vstack([x, x]) * 0.7071
    s = int(round(t0 * SR))
    if s < 0:
        x = x[:, -s:]
        s = 0
    e = min(buf.shape[1], s + x.shape[1])
    if e > s:
        buf[:, s:e] += x[:, :e - s] * gain


def groove(mus, pump, t0, t1, prog, roots, fade=None):
    bar = 4 * BEAT
    tb = t0
    bi = 0
    gain_at = (lambda t: 1.0) if fade is None else (lambda t: float(np.clip((fade[1] - t) / (fade[1] - fade[0]), 0, 1)))
    while tb < t1 - 0.01:
        ch = prog[bi % len(prog)]
        d = min(bar, t1 - tb)
        p_ = pad_note(ch, d + 0.4, cutoff=2200)
        ep = env_ar(len(p_), 0.05, 0.4, 1)
        if fade is not None:
            ep = ep * np.clip((fade[1] - (tb + np.arange(len(p_)) / SR)) / (fade[1] - fade[0]), 0, 1)
        place(mus, pan(p_ * ep, -0.2), tb, db(-20))
        place(mus, pan(np.roll(p_, 700) * ep, 0.2), tb, db(-20))
        for q in range(4):
            bt = tb + q * BEAT
            if bt >= t1 - 0.01:
                break
            gk = gain_at(bt)
            if gk <= 0:
                break
            place(mus, kick(), bt, db(-9) * gk)
            s0 = int(bt * SR)
            L = int(0.35 * SR)
            if s0 + L < N:
                pump[s0:s0 + L] = np.minimum(pump[s0:s0 + L], 1 - 0.45 * np.exp(-np.arange(L) / SR * 9))
            if q in (1, 3):
                place(mus, pan(clap(), 0.05), bt, db(-15) * gk)
            place(mus, pan(hat(True), 0.25), bt + BEAT / 2, db(-24) * gk)
            for h in range(4):
                place(mus, pan(hat(), -0.3), bt + h * BEAT / 4, db(-31 if h % 2 else -28) * gk)
            for e8 in range(2):
                tb8 = bt + e8 * BEAT / 2
                tn = tt(BEAT / 2 * 0.9)
                f = midi(roots[bi % len(roots)])
                bs = np.sin(2 * np.pi * f * tn) + 0.35 * np.sin(4 * np.pi * f * tn)
                bs = np.tanh(bs * 1.5) * env_ar(len(tn), 0.004, 0.06, 1)
                place(mus, bs, tb8, db(-16) * gk)
            for st in range(4):
                ts = bt + st * BEAT / 4
                idx = q * 4 + st
                note = ch[idx % 4] + 12 + (12 if idx % 8 >= 6 else 0)
                place(mus, pan(pluck(midi(note), 0.3, 1.4), 0.35 if st % 2 else -0.35), ts, db(-25) * gk)
        tb += bar
        bi += 1


def build_music():
    mus = np.zeros((2, N))
    pump = np.ones(N)

    # Section A — tension (0 → 15.3): dark Am pad + soft heartbeat
    a_end = 15.3
    pad = pad_note([45, 52, 57, 60], a_end + 0.5, cutoff=900)
    e = env_ar(len(pad), 1.2, 1.0, 1.5)
    place(mus, pan(pad * e, -0.15) + pan(np.roll(pad, 900) * e, 0.15), 0.0, db(-14))
    sub = np.sin(2 * np.pi * midi(33) * tt(a_end)) * env_ar(int(a_end * SR), 1.5, 1.2)
    place(mus, sub, 0.0, db(-21))
    beat = DROP % BEAT
    b = beat
    i = 0
    while b < a_end - 0.6:
        if i % 2 == 0 and b > 0.3:
            place(mus, kick() * 0.6, b, db(-15))
            place(mus, kick() * 0.35, b + 0.22, db(-15))
        place(mus, hat(), b + BEAT / 2, db(-30))
        b += BEAT
        i += 1

    # Section B — hope build (19.1 → 23.55): rising arpeggio in C major
    prog_b = [[60, 64, 67, 71], [57, 60, 64, 67], [53, 57, 60, 64]]
    s16 = BEAT / 4
    tb = 19.15
    k = 0
    while tb < DROP - 0.02:
        u = (tb - 19.15) / (DROP - 19.15)
        chord = prog_b[min(2, int(u * 3))]
        nnote = chord[k % 4] + (12 if (k // 4) % 2 else 0)
        place(mus, pan(pluck(midi(nnote), 0.35, 0.4 + 1.6 * u), 0.3 * np.sin(k)), tb, db(-22 + 9 * u))
        tb += s16
        k += 1
    padb = pad_note([48, 55, 60, 64], DROP - 19.0, cutoff=700)
    padb = sweep_filter(padb, 500, 4000, kind='lowpass', q=0.9)
    place(mus, padb * env_ar(len(padb), 1.5, 0.05), 19.0, db(-14))
    place(mus, reverse_cymbal(1.6), DROP - 1.6, db(-14))

    # Section C — groove (23.55 → 47.2), then a fresh phrase on the end card (47.2 → end)
    prog = [[48, 52, 55, 59], [43, 50, 55, 59], [45, 52, 57, 60], [41, 48, 53, 57]]  # Cmaj7 G Am F
    roots = [36, 31, 33, 29]
    groove(mus, pump, DROP, 47.2, prog, roots)
    groove(mus, pump, 47.2, TOTAL, [[48, 52, 55, 60], [41, 48, 53, 57]], [36, 29], fade=(49.7, TOTAL))
    # end-card hit: chord stab + sparkle arpeggio
    end_ch = [36, 48, 55, 60, 64, 67, 72]
    fin = pad_note(end_ch, 2.2, cutoff=3200)
    fin *= env_ar(len(fin), 0.01, 2.0, 1.4)
    place(mus, pan(fin, -0.1) + pan(np.roll(fin, 800), 0.1), 47.2, db(-12))
    for i, n_ in enumerate([60, 64, 67, 72, 76, 79]):
        place(mus, pan(pluck(midi(n_ + 12), 1.2, 2.0), -0.5 + i * 0.2), 47.25 + i * 0.07, db(-22))

    # sidechain pump on the groove
    mus *= pump[None, :]
    mus = reverb(mus, 0.18)
    return mus


# ---------------- SFX timeline ----------------

def build_sfx():
    fx = np.zeros((2, N))
    P = lambda x, t, g, p=0.0: place(fx, pan(x, p) if x.ndim == 1 else x, t, db(g))
    # hook
    P(boom(1.4), 0.02, -9)
    P(shimmer(1.1, seed=2), 0.95, -15)
    P(whoosh(0.4, 400, 3000), 1.72, -18)
    P(error_beep(), 2.44, -15)
    P(thud(0.8), 2.43, -14)
    P(whoosh(0.3, 2000, 600), 3.68, -22)
    P(whoosh(0.4, 400, 3000), 3.8, -18)
    for i in range(10):
        P(key_click(i), 4.1 + i * 0.06 + (0.01 if i % 3 == 0 else 0), -17, 0.1)
    P(bonk(), 4.85, -15)
    P(crickets(1.5), 4.95, -16)
    # problem
    P(whoosh(0.6, 300, 2500), 5.75, -17)
    for t0, pt in ((6.45, 1.0), (8.25, 0.94), (10.0, 0.88)):
        P(thud(pt), t0, -10)
        P(whoosh(0.25, 800, 3000), t0 - 0.22, -24)
    P(whoosh(0.35, 3000, 900), 11.12, -19)
    for i, t0 in enumerate((11.45, 11.75, 12.05)):
        P(pop(620 + 90 * i), t0, -15, -0.3 + 0.3 * i)
    for i, t0 in enumerate((12.55, 12.8, 13.05)):
        P(stamp(), t0, -12, -0.3 + 0.3 * i)
    P(whoosh(0.5, 2500, 300), 13.6, -18)
    P(glitch_zap(), 14.3, -14)
    P(power_down(0.8), 14.35, -15)
    # transformation
    P(fwoosh(0.7), 15.27, -14)
    P(riser(3.4), 15.5, -17)
    P(ding(), 18.85, -13)
    P(whoosh(0.35, 800, 4000), 19.0, -21)
    # brand
    P(reverse_whoosh(0.55), 20.48, -17)
    P(boom(1.8, 90, 34, 1.1), 21.02, -11)
    P(shimmer(1.4, n=40, seed=5), 21.04, -13)
    P(shimmer(1.0, n=24, seed=6), 21.6, -19)
    # drop
    P(boom(2.0, 130, 36, 1.2), DROP, -9)
    P(crash(2.4), DROP, -17)
    P(whoosh(0.3, 3000, 800), 23.9, -22)
    # services
    P(whoosh(0.55, 300, 3000), 23.85, -18)
    for i, t0 in enumerate((24.85, 25.73, 27.54, 28.87)):
        P(pop(700 + 110 * i), t0, -12, (-0.25, 0.25)[i % 2])
        P(blip_up(900 + 150 * i, 0.15), t0 + 0.02, -21, (-0.25, 0.25)[i % 2])
    P(whoosh(0.4, 900, 4000), 30.42, -19)
    # route
    P(loc_ping(880), 31.38, -14, -0.6)
    P(plane_flyby(1.1), 31.95, -12)
    P(loc_ping(1174.7), 32.86, -13, 0.6)
    # payoff
    P(whoosh(0.6, 300, 2500), 33.9, -18)
    for i, t0 in enumerate((34.68, 35.03, 35.38, 35.73, 36.08)):
        P(notif(i % 2), t0, -12, (-0.15, 0.15)[i % 2])
    P(whoosh(0.35, 900, 4000), 36.45, -20)
    for i, t0 in enumerate((36.85, 38.15, 39.45)):
        P(blip_up(500 + 120 * i, 0.3), t0, -14, -0.3 + 0.3 * i)
        P(pop(600 + 120 * i), t0, -16)
    P(kaching(), 38.18, -12, 0.15)
    P(whoosh(0.35, 3000, 900), 40.18, -21)
    P(whoosh(0.4, 400, 3000), 40.3, -20)
    scale = [72, 74, 76, 77, 79, 81, 83, 84, 86, 88, 89, 91]
    for i in range(12):
        P(tick(midi(scale[i])), 40.6 + i * 0.115, -19, -0.5 + i / 11)
    P(whoosh(0.35, 3000, 900), 42.25, -21)
    # CTA
    P(whoosh(0.6, 300, 2500), 42.3, -19)
    P(whoosh(0.35, 500, 4000), 44.05, -16)
    P(thud(1.2), 44.2, -16)
    P(shimmer(1.2, n=30, seed=9), 44.95, -15)
    P(pop(820), 46.33, -13)
    P(click(), 47.0, -10, 0.3)
    # end card
    P(whoosh(0.5, 300, 5000), 46.95, -12)
    P(boom(2.4, 120, 34, 1.3), 47.22, -8)
    P(shimmer(1.6, n=44, seed=12), 47.3, -13)
    P(click(), 49.6, -16, 0.3)
    return reverb(fx, 0.12)


def read_wav(path):
    with wave.open(path, 'rb') as w:
        assert w.getframerate() == SR and w.getnchannels() == 2 and w.getsampwidth() == 2
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    return x.reshape(-1, 2).T


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x.T * 32767).astype(np.int16).tobytes())


def envelope(x, att=0.01, rel=0.25):
    m = np.abs(x).max(axis=0)
    m = signal.sosfilt(sos('lowpass', 30), m)
    m = np.maximum(m, 0)
    # asymmetric smoothing on a decimated grid
    hop = 240
    v = m[::hop]
    out = np.zeros_like(v)
    a, r = np.exp(-hop / (att * SR)), np.exp(-hop / (rel * SR))
    s = 0.0
    for i, val in enumerate(v):
        s = a * s + (1 - a) * val if val > s else r * s + (1 - r) * val
        out[i] = s
    return np.repeat(out, hop)[:x.shape[1]]


if __name__ == '__main__':
    voice_path, out_path = sys.argv[1], sys.argv[2]
    v = read_wav(voice_path)
    voice = np.zeros((2, N))
    voice[:, :v.shape[1]] = v[:, :N]
    music = build_music()
    sfx = build_sfx()
    # duck music under speech (~8 dB)
    ve = envelope(voice)
    thr = 0.02
    duck = 1 - 0.6 * np.clip(ve / thr, 0, 1)
    music *= duck[None, :]
    mix = voice * 1.0 + music * db(-8.5) + sfx * db(-1)
    # gentle bus limiter
    peak = np.max(np.abs(mix))
    print('pre-limit peak', round(20 * np.log10(peak), 2), 'dBFS')
    mix = np.tanh(mix * 1.1) / 1.1 if peak > 0.9 else mix
    write_wav(out_path, mix * 0.95)
    write_wav(out_path.replace('.wav', '_music.wav'), music * db(-8.5))
    write_wav(out_path.replace('.wav', '_sfx.wav'), sfx * db(-1))
    print('written', out_path)
