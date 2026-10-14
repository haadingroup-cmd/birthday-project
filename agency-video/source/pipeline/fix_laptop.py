#!/usr/bin/env python3
"""Laptop-lid fix: replace the camera-facing screen+bezel of the open laptop
(seated shot, frames 179-403 of the 30 fps source) with the BACK of the lid.

usage:  python3 -I fix_laptop.py IN_DIR OUT_DIR [PLATE_DIR] [--retrack]

IN_DIR    1080x1920 frames named 0001.jpg ... (dev lanczos set or the
          Real-ESRGAN sr1080 set - same geometry).
OUT_DIR   receives ONLY the frames this script changes (same names, JPEG q97).
PLATE_DIR optional: RGBA PNG "clean plate" of the lid layer per frame (lid
          colour + alpha incl. hand occlusion and crossfade/fade weights, but
          WITHOUT caption occlusion) - handy for the caption-removal step.

Tracking (per-frame homography of the lid plane, master frame 230) is stored in
track.json next to this script and reused on every run, so re-runs on other
frame sets are geometrically identical.  --retrack recomputes it from IN_DIR.

Deterministic: no randomness except per-frame grain seeded by frame number.
"""
import sys, os, json, math
import numpy as np
import cv2
from scipy.signal import savgol_filter
from scipy.special import erfc

cv2.setNumThreads(2)
HERE = os.path.dirname(os.path.abspath(__file__))
TRACK_PATH = os.path.join(HERE, 'track.json')

W, H = 1080, 1920
MASTER = 230
# Outer boundary of the lid face (black bezel outer edge) in master frame 230,
# TL, TR, BR, BL.  Top/left/right from sub-pixel edge fits, bottom = inner
# screen edge + 15 px bezel (the area under the hinge is dark, no usable edge).
Q_OUTER_M = np.float64([[14.7, 1063.7], [388.5, 1088.5], [423.12, 1468.09], [51.85, 1400.34]])
# Inner screen boundary in master frame (used for QA / edge-softness estimate).
Q_INNER_M = np.float64([[22.8, 1082.3], [384.7, 1107.3], [416.3, 1451.6], [56.3, 1385.9]])
XF_A, XF_B = 178, 189          # crossfade: frames 179..188 = (1-w)*F178 + w*F189 (both shots frozen)
TRACK_FIRST, TRACK_LAST = 189, 403
FADE_OUT = {401: 0.9, 402: 0.62, 403: 0.28}   # morph into the real lid back (404+: original)
CAP_Y0, CAP_Y1 = 1240, 1760    # vertical band where burned captions can appear
HAND_FROM, HAND_REF, HAND_YMAX = 372, 352, 1330   # fingers over the lid top edge from ~378; 352 = hand-free reference

# canonical lid space (physical lid aspect ~1.41)
CW, CH = 1410.0, 1000.0
R_TOP, R_BOT = 26.0, 12.0      # corner radii (canonical units)


# --------------------------------------------------------------------------- utils
def fpath(d, n):
    return os.path.join(d, f'{n:04d}.jpg')


def load(d, n):
    im = cv2.imread(fpath(d, n), cv2.IMREAD_COLOR)
    if im is None:
        raise FileNotFoundError(fpath(d, n))
    return im


def tq(Hm, q):
    return cv2.perspectiveTransform(np.float64(q)[None], Hm)[0]


def Tm(dx, dy):
    return np.array([[1, 0, dx], [0, 1, dy], [0, 0, 1]], np.float64)


def disk(r):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def quad_mask(q, shape, grow=0):
    m = np.zeros(shape[:2], np.uint8)
    cv2.fillPoly(m, [np.round(np.float64(q) * 4).astype(np.int32)], 255, cv2.LINE_8, shift=2)
    if grow > 0:
        m = cv2.dilate(m, disk(grow))
    elif grow < 0:
        m = cv2.erode(m, disk(-grow))
    return m


# --------------------------------------------------------------- occluder masks
def caption_exclusion(im):
    """generous binary mask (255) of burned-caption pixels, for tracking only"""
    b, g, r = [im[..., i].astype(np.int16) for i in range(3)]
    pink = ((r > 110) & (r - g > 45) & (r - b > 25)).astype(np.uint8) * 255
    pink = cv2.morphologyEx(pink, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    m = cv2.dilate(pink, disk(38))
    m = np.maximum(m, np.roll(np.roll(m, 12, 0), 6, 1))
    # pop-in / pop-out smears are paler: drop the whole caption band where pink-ish
    bb, gg, rr = [im[CAP_Y0 + 60:CAP_Y1 - 40, :, i].astype(np.int16) for i in range(3)]
    pk = (rr > 100) & (rr - gg > 30) & (rr - bb > 12)
    ys, xs = np.nonzero(pk)
    if len(xs) > 150:
        x0 = int(np.percentile(xs, 0.5)) - 70
        x1 = int(np.percentile(xs, 99.5)) + 70
        m[CAP_Y0 + 80:CAP_Y1 - 70, max(x0, 0):max(x1, 0)] = 255
    return m


def skin_soft(im):
    """soft skin probability (fingers over the lid) 0..1, float32"""
    f = im.astype(np.float32)
    b, g, r = f[..., 0], f[..., 1], f[..., 2]
    L = 0.299 * r + 0.587 * g + 0.114 * b
    s = np.clip((r - b - 9.0) / 12.0, 0, 1) * np.clip((r - g - 1.0) / 7.0, 0, 1) * np.clip((L - 30.0) / 15.0, 0, 1)
    return s


def skin_exclusion(im):
    m = (skin_soft(im) > 0.3).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return cv2.dilate(m, disk(10))


def caption_keep(im):
    """soft 0..1 mask of burned-caption pixels to keep untouched (fill, cream
    outline, black outline + drop shadow, motion-blur smears)."""
    f = im.astype(np.float32)
    b, g, r = f[..., 0], f[..., 1], f[..., 2]
    L = 0.299 * r + 0.587 * g + 0.114 * b
    pink = np.clip((r - g - 28.0) / 22.0, 0, 1) * np.clip((r - b - 8.0) / 16.0, 0, 1) * np.clip((r - 90.0) / 20.0, 0, 1)
    pb = (pink > 0.5).astype(np.uint8)
    pb = cv2.morphologyEx(pb, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    if pb.sum() < 30:
        return np.zeros(L.shape, np.float32)
    # cream outline only where it hugs the pink fill (no stray bright halo pixels)
    cream = np.clip((L - 203.0) / 14.0, 0, 1) * np.clip((r - b + 4.0) / 10.0, 0, 1)
    cream *= cv2.GaussianBlur(cv2.dilate(pb, disk(15)).astype(np.float32), (0, 0), 1.0)
    core = np.maximum(pink, cream)
    cb = (core > 0.5).astype(np.uint8)
    cbc = cv2.morphologyEx(cb, cv2.MORPH_CLOSE, disk(4))            # glyph interiors / speckle
    near = cv2.dilate(cbc, disk(11))
    sh = np.zeros_like(near)
    sh[13:, 5:] = near[:-13, :-5]                                     # drop shadow (down-right)
    near = np.maximum(near, sh).astype(np.float32)
    near = cv2.GaussianBlur(near, (0, 0), 1.2)
    dark = np.clip((105.0 - L) / 55.0, 0, 1)                          # black outline / shadow
    keep = np.maximum(np.maximum(core, cbc.astype(np.float32)), near * dark)
    return keep


def finger_matte(im, ref_warp, lid_alpha):
    """hand/fingers in front of the lid.  Returns (alpha_f, S, zone):
    alpha_f  finger coverage 0..1 (soft, from projecting each pixel between the
             expected lid-face colour S and the local finger colour F),
    S        expected (hand-free) screen/bezel colour = hand-free reference frame
             warped into this frame, gain/offset matched,
    zone     0..1 weight of the neighbourhood where the matte is used.
    None if no hand is present."""
    sk = skin_soft(im)
    sb = (sk > 0.35).astype(np.uint8)
    sb = cv2.morphologyEx(sb, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    if sb.sum() < 40:
        return None
    f = im.astype(np.float32)
    inside = (cv2.erode((lid_alpha > 0.5).astype(np.uint8), disk(5)) > 0) & (ref_warp.min(2) > 0)
    fit = inside & (cv2.dilate(sb, disk(14)) == 0)
    gn, off = 1.0, 0.0
    if fit.sum() > 2000:
        X = ref_warp[fit].reshape(-1)
        Y = f[fit].reshape(-1)
        sel = np.ones(X.shape, bool)
        for _ in range(3):
            A = np.stack([X[sel], np.ones(sel.sum())], 1)
            (gn, off), *_ = np.linalg.lstsq(A, Y[sel], rcond=None)
            res = np.abs(Y - (gn * X + off))
            sel = res < max(6.0, np.percentile(res, 80))
    S = ref_warp * gn + off
    # local finger colour: normalised convolution of confident skin pixels
    conf = cv2.erode((sk > 0.6).astype(np.uint8), disk(2)).astype(np.float32)
    wsum = cv2.GaussianBlur(conf, (0, 0), 5.0)
    Fc = cv2.GaussianBlur(f * conf[..., None], (0, 0), 5.0) / np.maximum(wsum, 1e-4)[..., None]
    dFS = Fc - S
    den = (dFS ** 2).sum(2)
    a_proj = np.clip(((f - S) * dFS).sum(2) / np.maximum(den, 900.0), 0, 1)
    ok = (wsum > 0.01) & inside & (den > 900.0)
    alpha_f = np.where(ok, np.maximum(a_proj, cv2.erode(sk, disk(1))), sk)
    zone = cv2.dilate(sb, disk(16)).astype(np.float32)
    zone = cv2.GaussianBlur(zone, (0, 0), 3.0) * inside
    alpha_f = alpha_f * np.maximum(zone, (sk > 0.5))
    # fill thin dips (where expected colour ~ finger colour, e.g. on the
    # bezel/screen boundary) so the finger interior stays intact
    alpha_f = np.maximum(alpha_f, cv2.morphologyEx(alpha_f, cv2.MORPH_CLOSE, disk(3)))
    return alpha_f.astype(np.float32), S.astype(np.float32), Fc.astype(np.float32), zone.astype(np.float32)


# ----------------------------------------------------------------- ECC tracking
class Frame:
    def __init__(self, d, n):
        im = load(d, n)
        self.n = n
        self.g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
        inv = cv2.bitwise_or(caption_exclusion(im), skin_exclusion(im))
        self.valid = cv2.bitwise_not(inv)


def ecc_align(tf, q_t, cf, H0, iters=100, blur=5):
    """refine H0 (template frame -> current frame) with masked ECC on the lid region"""
    x0, y0 = np.floor(q_t.min(0) - 12).astype(int)
    x1, y1 = np.ceil(q_t.max(0) + 12).astype(int)
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    tmpl = tf.g[y0:y1, x0:x1]
    tmask = cv2.bitwise_and(quad_mask(q_t, tf.g.shape, 3), tf.valid)[y0:y1, x0:x1]
    cq = tq(H0, q_t)
    X0, Y0 = np.floor(cq.min(0) - 60).astype(int)
    X1, Y1 = np.ceil(cq.max(0) + 60).astype(int)
    X0, Y0, X1, Y1 = max(X0, 0), max(Y0, 0), min(X1, W), min(Y1, H)
    inp = cf.g[Y0:Y1, X0:X1]
    imask = cf.valid[Y0:Y1, X0:X1]
    Hc = Tm(-X0, -Y0) @ H0 @ Tm(x0, y0)
    Hc = (Hc / Hc[2, 2]).astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, iters, 1e-6)
    try:
        cc, Hc = cv2.findTransformECCWithMask(tmpl, inp, tmask, imask, Hc, cv2.MOTION_HOMOGRAPHY, crit, blur)
    except cv2.error:
        return H0, -1.0
    Hn = Tm(X0, Y0) @ Hc.astype(np.float64) @ Tm(-x0, -y0)
    return Hn / Hn[2, 2], float(cc)


def lid_diff(d, a, b, q):
    """mean abs difference of two frames inside the lid quad, captions/skin excluded"""
    ia, ib = load(d, a), load(d, b)
    m = quad_mask(q, ia.shape, 2)
    m = cv2.bitwise_and(m, cv2.bitwise_not(cv2.bitwise_or(caption_exclusion(ia), caption_exclusion(ib))))
    m = cv2.bitwise_and(m, cv2.bitwise_not(cv2.bitwise_or(skin_exclusion(ia), skin_exclusion(ib))))
    ga = cv2.cvtColor(ia, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gb = cv2.cvtColor(ib, cv2.COLOR_BGR2GRAY).astype(np.float32)
    sel = m > 0
    if sel.sum() < 500:
        return 99.0
    return float(np.abs(ga - gb)[sel].mean())


def crossfade_weights(d):
    def L(n):
        return cv2.GaussianBlur(load(d, n).astype(np.float32), (0, 0), 6)[200:1700]
    A, B = L(XF_A), L(XF_B)
    dlt = (B - A).ravel()
    out = {}
    for n in range(XF_A + 1, XF_B):
        w = float(np.dot(L(n).ravel() - A.ravel(), dlt) / np.dot(dlt, dlt))
        out[n] = min(max(w, 0.0), 1.0)
    return out


def crossfade_register(d, w, q189, log=print):
    """the incoming laptop shot drifts ~2 px during the dissolve: register F189
    to the incoming component E_B = (F_n - (1-w) F178) / w of every dissolve
    frame (ECC homography on the lid region).  Returns {n: H 189->n}."""
    gA = cv2.cvtColor(load(d, XF_A), cv2.COLOR_BGR2GRAY).astype(np.float32)
    gB = cv2.cvtColor(load(d, XF_B), cv2.COLOR_BGR2GRAY).astype(np.float32)
    mB = quad_mask(q189, gB.shape, 7)
    full = np.full(gB.shape, 255, np.uint8)
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-7)
    out, Hprev = {}, np.eye(3)
    for n in range(XF_B - 1, XF_A, -1):
        wn = w[n]
        if wn >= 0.28:
            gI = cv2.cvtColor(load(d, n), cv2.COLOR_BGR2GRAY).astype(np.float32)
            EB = ((gI - (1.0 - wn) * gA) / wn).astype(np.float32)
            try:
                cc, Hn = cv2.findTransformECCWithMask(gB, EB, mB, full, Hprev.astype(np.float32),
                                                      cv2.MOTION_HOMOGRAPHY, crit, 5)
                Hn = Hn.astype(np.float64)
            except cv2.error:
                cc, Hn = -1.0, Hprev
            log(f'crossfade {n} w {wn:.3f} cc {cc:.4f}')
            Hprev = Hn
        out[n] = Hprev / Hprev[2, 2]
    return out


def track(d, log=print):
    frames = {}

    def F(n):
        if n not in frames:
            frames[n] = Frame(d, n)
        return frames[n]

    Hs = {MASTER: np.eye(3)}
    ccs = {MASTER: 1.0}
    for direction, stop in [(1, TRACK_LAST - 1), (-1, TRACK_FIRST)]:
        K, Hk = MASTER, np.eye(3)
        prev = [np.eye(3), np.eye(3)]          # K->n-1, K->n-2
        n = MASTER + direction
        while (n <= stop) if direction > 0 else (n >= stop):
            qK = tq(Hk, Q_OUTER_M)
            Hp = prev[0] @ np.linalg.inv(prev[1]) @ prev[0]
            Hr, cc = ecc_align(F(K), qK, F(n), Hp)
            if cc < 0.9:
                H2, cc2 = ecc_align(F(K), qK, F(n), prev[0])
                if cc2 > cc:
                    Hr, cc = H2, cc2
            Hs[n] = Hr @ Hk
            ccs[n] = cc
            log(f'track {n} key {K} cc {cc:.4f}')
            prev = [Hr, prev[0]]
            if abs(n - K) >= 8:                # re-key
                prev = [np.eye(3), np.linalg.inv(Hr) @ prev[1]]
                K, Hk = n, Hs[n]
                for k in list(frames):
                    if abs(k - n) > 1 and k != MASTER:
                        del frames[k]
            n += direction
    # duplicated frames (24->30 fps pulldown + held AI frames): copy exact geometry
    ns = list(range(TRACK_FIRST, TRACK_LAST))
    dup = {}
    for n in ns[1:]:
        q = tq(Hs[n], Q_OUTER_M)
        dd = lid_diff(d, n - 1, n, q)
        if dd < 0.6:
            dup[n] = dd
    corners = {}
    for n in ns:
        src = n
        while src in dup:
            src -= 1
        corners[n] = tq(Hs[src], Q_OUTER_M)
    # light temporal smoothing on unique frames, clamped so it never deviates
    # more than 0.4 px from the measurement (removes sub-pixel jitter, no lag)
    uniq = [n for n in ns if n not in dup]
    U = np.array([corners[n].ravel() for n in uniq])
    S = savgol_filter(U, 5, 2, axis=0, mode='interp')
    S = U + np.clip(S - U, -0.4, 0.4)
    sm = {n: S[i].reshape(4, 2) for i, n in enumerate(uniq)}
    for n in ns:
        src = n
        while src in dup:
            src -= 1
        corners[n] = sm[src]
    # 403: lid back (logo) replaces the screen -> ECC meaningless; damped extrapolation
    corners[TRACK_LAST] = corners[TRACK_LAST - 1] + 0.5 * (corners[TRACK_LAST - 1] - corners[TRACK_LAST - 2])
    xf = crossfade_weights(d)
    xfH = crossfade_register(d, xf, corners[XF_B], log)
    return {
        'master': MASTER, 'Q_outer_master': Q_OUTER_M.tolist(), 'Q_inner_master': Q_INNER_M.tolist(),
        'H_master_to_frame': {str(k): v.tolist() for k, v in sorted(Hs.items())},
        'ecc_cc': {str(k): v for k, v in sorted(ccs.items())},
        'duplicates': {str(k): v for k, v in sorted(dup.items())},
        'corners': {str(k): np.round(v, 3).tolist() for k, v in sorted(corners.items())},
        'crossfade': {'from': XF_A, 'to': XF_B, 'w': {str(k): round(v, 4) for k, v in xf.items()},
                      'H_189_to_n': {str(k): v.tolist() for k, v in sorted(xfH.items())}},
        'fade_out': {str(k): v for k, v in FADE_OUT.items()},
        'canonical': {'w': CW, 'h': CH, 'r_top': R_TOP, 'r_bot': R_BOT},
    }


# --------------------------------------------------------------- appearance
def measure_edge_sigma(d):
    """softness of real lid edges in this frame set: 10-90% rise of the inner
    screen/bezel edge in the master frame -> gaussian sigma (px)"""
    g = cv2.cvtColor(load(d, MASTER), cv2.COLOR_BGR2GRAY).astype(np.float32)
    a, b = Q_INNER_M[0], Q_INNER_M[1]
    dvec = (b - a) / np.linalg.norm(b - a)
    nrm = np.array([dvec[1], -dvec[0]])
    if nrm[1] > 0:
        nrm = -nrm                                  # pointing up = outward (towards bezel)
    rises = []
    for t in np.linspace(0.25, 0.85, 13):
        p = a + (b - a) * t
        offs = np.arange(-8, 8.01, 0.1)
        xs = (p[0] + nrm[0] * offs).astype(np.float32)[None]
        ys = (p[1] + nrm[1] * offs).astype(np.float32)[None]
        prof = cv2.remap(g, xs, ys, cv2.INTER_CUBIC)[0]
        hi, lo = np.median(prof[:25]), np.median(prof[-25:])
        if hi - lo < 60:
            continue
        nv = (prof - lo) / (hi - lo)
        i90 = np.argmax(nv < 0.9)
        i10 = np.argmax(nv < 0.1)
        if i10 > i90:
            rises.append((i10 - i90) * 0.1)
    rise = float(np.median(rises)) if rises else 3.0
    return float(np.clip(rise / 2.563, 0.5, 2.0))


def measure_lid_back(d):
    """colour (BGR) and grain of the real lid back after the morph (frames 406/412)"""
    pts = {406: [(60, 1250), (150, 1220), (400, 1240), (80, 1400), (150, 1500), (60, 1550)],
           412: [(120, 1300), (150, 1450), (300, 1500), (200, 1600)]}
    cols, noise = [], []
    for n, pp in pts.items():
        im = load(d, n).astype(np.float32)
        hp = im - cv2.GaussianBlur(im, (0, 0), 2.0)
        for x, y in pp:
            cols.append(np.median(im[y - 6:y + 7, x - 6:x + 7].reshape(-1, 3), 0))
            noise.append(hp[y - 6:y + 7, x - 6:x + 7].std())
    return np.median(np.array(cols), 0), float(np.median(noise))


def render_lid(Hc2f, x0, y0, x1, y1, base_bgr, sigma_e):
    """lid-back layer for the pixel box [x0,x1)x[y0,y1): returns colour (h,w,3)
    float32 BGR and coverage alpha (h,w) float32"""
    Hi = np.linalg.inv(Hc2f)
    xs, ys = np.meshgrid(np.arange(x0, x1, dtype=np.float64), np.arange(y0, y1, dtype=np.float64))
    den = Hi[2, 0] * xs + Hi[2, 1] * ys + Hi[2, 2]
    u = (Hi[0, 0] * xs + Hi[0, 1] * ys + Hi[0, 2]) / den
    v = (Hi[1, 0] * xs + Hi[1, 1] * ys + Hi[1, 2]) / den
    # rounded-rectangle SDF in canonical units (top corners rounder than hinge corners)
    r = np.where(v < CH / 2, R_TOP, R_BOT)
    qx = np.abs(u - CW / 2) - (CW / 2 - r)
    qy = np.abs(v - CH / 2) - (CH / 2 - r)
    sdf = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r
    gy, gx = np.gradient(sdf)
    dpx = sdf / np.maximum(np.hypot(gx, gy), 1e-6)          # signed distance in pixels (+ outside)
    alpha = 0.5 * erfc(dpx / (math.sqrt(2) * sigma_e))
    # distances (px) to individual edges, for the chamfer highlight
    vy_, vx_ = np.gradient(v)
    uy_, ux_ = np.gradient(u)
    d_top = v / np.maximum(np.hypot(vx_, vy_), 1e-6)
    d_right = (CW - u) / np.maximum(np.hypot(ux_, uy_), 1e-6)
    d_left = u / np.maximum(np.hypot(ux_, uy_), 1e-6)
    s, t = u / CW, v / CH
    # large-scale shading: soft window light from the right/back, faint bounce from the table
    shade = 1.0 + 0.16 * (s - 0.5) + 0.07 * (t - 0.5)
    shade += 0.07 * np.exp(-((0.75 * s + 0.55 * t - 0.95) / 0.28) ** 2)     # broad soft sheen
    shade -= 0.05 * np.exp(-((s - 0.0) / 0.18) ** 2)                          # far (left) side falls off
    col = base_bgr[None, None, :] * shade[..., None]
    # thin lighter chamfer just inside the edges (strongest on the top/right, lit side)
    def line(dd, w=0.9, c=1.1):
        return np.exp(-((dd - c) / w) ** 2)
    hl = 26.0 * line(d_top) * np.clip(0.55 + 0.6 * s, 0, 1) + 20.0 * line(d_right) + 9.0 * line(d_left)
    hl *= np.clip(-dpx + 0.5, 0, 1)                                            # only inside
    col = col + hl[..., None] * np.array([1.0, 1.0, 0.97])[None, None, :]
    return col.astype(np.float32), alpha.astype(np.float32)


def add_grain(col, sigma, seed):
    if sigma <= 0.05:
        return col
    rng = np.random.default_rng(seed)
    nz = rng.standard_normal(col.shape[:2]).astype(np.float32)
    nz = cv2.GaussianBlur(nz, (0, 0), 0.7)
    nz *= sigma / max(float(nz.std()), 1e-6)
    return col + nz[..., None]


# --------------------------------------------------------------------- main
def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    retrack = '--retrack' in sys.argv
    only = None                                    # dev option --frames=a:b
    for a in sys.argv[1:]:
        if a.startswith('--frames='):
            fa, fb = map(int, a.split('=')[1].split(':'))
            only = set(range(fa, fb + 1))
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)
    in_dir, out_dir = args[0], args[1]
    plate_dir = args[2] if len(args) > 2 else None
    os.makedirs(out_dir, exist_ok=True)
    if plate_dir:
        os.makedirs(plate_dir, exist_ok=True)

    if retrack or not os.path.exists(TRACK_PATH):
        tr = track(in_dir)
        with open(TRACK_PATH, 'w') as fh:
            json.dump(tr, fh, indent=1)
        print('wrote', TRACK_PATH)
    tr = json.load(open(TRACK_PATH))
    corners = {int(k): np.float64(v) for k, v in tr['corners'].items()}
    xf = {int(k): float(v) for k, v in tr['crossfade']['w'].items()}
    xfH = {int(k): v for k, v in tr['crossfade']['H_189_to_n'].items()}
    fade = dict(FADE_OUT)

    sigma_e = measure_edge_sigma(in_dir)
    base, grain = measure_lid_back(in_dir)
    base = base * 1.12                       # open lid sits a touch brighter than the closing one at 406-412
    print(f'edge sigma {sigma_e:.2f}px  lid base BGR {np.round(base, 1).tolist()}  grain {grain:.2f}')
    rect = np.float64([[0, 0], [CW, 0], [CW, CH], [0, CH]])

    def c2f(n):
        return cv2.getPerspectiveTransform(rect.astype(np.float32), corners[n].astype(np.float32)).astype(np.float64)
    ref_im = load(in_dir, HAND_REF).astype(np.float32)
    todo = sorted(corners)
    if only is not None:
        todo = [n for n in todo if n in only]
    for n in todo:
        q = corners[n]
        Hc2f = c2f(n)
        x0, y0 = np.floor(q.min(0) - 6).astype(int)
        x1, y1 = np.ceil(q.max(0) + 6).astype(int)
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
        im = load(in_dir, n)
        roi = im[y0:y1, x0:x1].astype(np.float32)
        col, alpha = render_lid(Hc2f, x0, y0, x1, y1, base, sigma_e)
        col = add_grain(col, grain, 1000 + n)
        f = fade.get(n, 1.0)
        A = alpha * f                                   # lid coverage (incl. morph fade)
        ck = np.zeros_like(alpha)
        cy0, cy1 = max(y0, CAP_Y0), min(y1, CAP_Y1)
        if cy1 > cy0:
            ck[cy0 - y0:cy1 - y0] = caption_keep(im[cy0:cy1, x0:x1])
        a = A * (1.0 - ck)
        out_roi = roi * (1.0 - a[..., None]) + col * a[..., None]
        a_plate = A.copy()
        if n >= HAND_FROM and y0 < HAND_YMAX:
            hy1 = min(y1, HAND_YMAX)
            Href = Tm(-x0, -y0) @ Hc2f @ np.linalg.inv(c2f(HAND_REF))
            rw = cv2.warpPerspective(ref_im, Href, (x1 - x0, hy1 - y0), flags=cv2.INTER_LINEAR,
                                     borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            fm = finger_matte(im[y0:hy1, x0:x1], rw, alpha[:hy1 - y0])
            if fm is not None:
                af, S, Fc, zone = fm
                ramp = np.clip((HAND_YMAX - np.arange(y0, hy1)) / 20.0, 0, 1)[:, None]
                af = af * ramp
                ah = a[:hy1 - y0]                       # lid coverage incl. caption keep
                lid = col[:hy1 - y0]
                o = roi[:hy1 - y0]
                # pixels that are mostly finger keep the original, with the screen
                # contribution of their blurred edge swapped for the lid colour
                # (clamped to the finger..lid range -> no dark blobs from hand shadows)
                dec = o + ((1.0 - af) * ah)[..., None] * (lid - S)
                lo = np.minimum(Fc, lid) - 8.0
                hi = np.maximum(Fc, lid) + 8.0
                dec = np.where(zone[..., None] > 0.05, np.clip(dec, lo, hi), o)
                keep = np.clip((af - 0.3) / 0.3, 0, 1)
                keep = keep * keep * (3 - 2 * keep)
                keep = cv2.GaussianBlur(keep, (0, 0), 0.6)
                std = o * (1.0 - ah[..., None]) + lid * ah[..., None]
                out_roi[:hy1 - y0] = std * (1.0 - keep[..., None]) + dec * keep[..., None]
                af = keep
                a_plate[:hy1 - y0] = A[:hy1 - y0] * (1.0 - af)
        out = im.copy()
        out[y0:y1, x0:x1] = np.clip(np.round(out_roi), 0, 255).astype(np.uint8)
        cv2.imwrite(os.path.join(out_dir, f'{n:04d}.jpg'), out, [cv2.IMWRITE_JPEG_QUALITY, 97])
        if plate_dir:
            pl = np.zeros((H, W, 4), np.uint8)
            pl[y0:y1, x0:x1, :3] = np.clip(np.round(col), 0, 255).astype(np.uint8)
            pl[y0:y1, x0:x1, 3] = np.clip(np.round(a_plate * 255), 0, 255).astype(np.uint8)
            cv2.imwrite(os.path.join(plate_dir, f'{n:04d}.png'), pl)
        print('frame', n, 'fade', f, flush=True)

    # dissolve frames 179-188: F_n = (1-w) A_n + w B_n.  The lid is rendered at
    # the incoming shot's registered position and swapped into the B layer only:
    # out = F_n + w * a * (lid - B_est), B_est = F189 warped by the registration.
    # The outgoing shot (A) stays untouched.
    b189 = load(in_dir, XF_B).astype(np.float32)
    for n in sorted(xf):
        if only is not None and n not in only:
            continue
        w = xf[n]
        if w <= 0.002:
            continue
        Hb = np.array(xfH[n])
        q = tq(Hb, corners[XF_B])
        Hc2f = Hb @ c2f(XF_B)
        x0, y0 = np.floor(q.min(0) - 6).astype(int)
        x1, y1 = np.ceil(q.max(0) + 6).astype(int)
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
        im = load(in_dir, n)
        roi = im[y0:y1, x0:x1].astype(np.float32)
        col, alpha = render_lid(Hc2f, x0, y0, x1, y1, base, sigma_e)
        col = add_grain(col, grain, 1000 + n)
        best = cv2.warpPerspective(b189, Tm(-x0, -y0) @ Hb, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR,
                                   borderMode=cv2.BORDER_REPLICATE)
        # A-layer estimate inside the lid: R0 = F_n - w*B_est.  Its fine detail
        # holds both the outgoing shot's texture and ghosts of the screen where
        # the dissolve frame's B content differs from F189 (compression, AI
        # flicker, sub-pixel drift); the ghosts sit on B's own edges, so the high
        # frequencies of R0 are suppressed there (low frequencies kept exactly).
        r0 = roi - w * best
        lp = cv2.GaussianBlur(r0, (0, 0), 2.5)
        gb = cv2.cvtColor(best, cv2.COLOR_BGR2GRAY)
        gm = cv2.magnitude(cv2.Sobel(gb, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(gb, cv2.CV_32F, 0, 1, ksize=3))
        gm = cv2.GaussianBlur(cv2.dilate(gm, disk(2)), (0, 0), 1.5)
        k = 1.0 - np.clip(w * gm / 40.0, 0, 1)
        k *= min(1.0, (1.0 - w) / 0.5)          # late in the dissolve the A layer is faint: keep less fine detail
        r = lp + (r0 - lp) * k[..., None]
        out_roi = roi * (1.0 - alpha[..., None]) + (r + w * col) * alpha[..., None]
        out = im.copy()
        out[y0:y1, x0:x1] = np.clip(np.round(out_roi), 0, 255).astype(np.uint8)
        cv2.imwrite(os.path.join(out_dir, f'{n:04d}.jpg'), out, [cv2.IMWRITE_JPEG_QUALITY, 97])
        if plate_dir:
            pl = np.zeros((H, W, 4), np.uint8)
            pl[y0:y1, x0:x1, :3] = np.clip(np.round(col), 0, 255).astype(np.uint8)
            pl[y0:y1, x0:x1, 3] = np.clip(np.round(alpha * w * 255), 0, 255).astype(np.uint8)
            cv2.imwrite(os.path.join(plate_dir, f'{n:04d}.png'), pl)
        print('frame', n, 'crossfade w', round(w, 3), flush=True)


if __name__ == '__main__':
    main()
