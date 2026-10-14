#!/usr/bin/env python3
"""Remove the burned-in one-word captions from the Haadin Global ad frames.

usage: python3 -I remove_captions.py IN_DIR OUT_DIR [--frames A-B] [--cache DIR]

IN_DIR holds 1080x1920 frames 0001.jpg ... NNNN.jpg (30 fps).  Every frame in
the requested range is written to OUT_DIR (frames without captions are copied
byte-for-byte, processed frames are re-encoded as JPEG q97).

Pipeline
 1. caption masks (half-res analysis of the band y 1150-1800):
    strict  = raspberry fill components that carry a cream ring and a black ring
              (the caption's two outlines) -> closed, then dilated by an
              outline+shadow structuring element scaled by the measured
              outline width of the word
    loose   = in frames where the strict mask is not stable (pop-in / pop-out
              motion blur) also the faint pinkish smear near the caption
              position, minus anything that is pink in the neighbouring
              frames too (holograms), dilated generously (blurred outlines)
 2. temporal fill: for every masked pixel the nearest frame before and after
    (same shot) in which that pixel - after motion compensation - is not
    covered is found; DIS optical flow between the caption-free surroundings,
    completed inside the masks by push-pull interpolation, aligns the source.
    The two sources are cross-faded linearly in time (so the fill evolves
    smoothly from frame to frame), soft-edged between source frames.
 3. pixels never uncovered within +-KMAX frames: spatial inpainting.
 4. seam correction: the colour difference on a ring around the mask is
    interpolated into the hole (membrane), then a 3 px feathered composite.
 5. crossfade frames: alpha-blend of the filled neighbouring shots with the
    blend factor solved by least squares on the unmasked band pixels.
 6. temporal stabilisation: fill of t is averaged with motion-compensated fills
    of t-1 and t+1 (inside the mask only).
"""
import sys, os, time, argparse, shutil, json
from collections import OrderedDict
import numpy as np
import cv2

cv2.setNumThreads(2)

Y0, Y1 = 1150, 1800          # analysed band (full-res rows)
BH, BW = Y1 - Y0, 1080
H2, W2 = BH // 2, BW // 2     # half-res band
KMAX = 90                     # max temporal distance of a source frame

# shots / transitions of this video (frame numbers, 1-based, inclusive)
SHOTS_1417 = [(1, 178), (188, 458), (465, 721), (730, 1018), (1033, 1274), (1285, 1417)]
FADES_1417 = [(179, 187, 178, 188), (459, 464, 458, 465), (722, 729, 721, 730),
              (1019, 1032, 1018, 1033), (1275, 1284, 1274, 1285)]


# ----------------------------------------------------------------------------- utils
def disk(r):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def ellipse(rx, ry):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rx + 1, 2 * ry + 1))


def shift_union(se, dx, dy):
    """SE = union of `se` swept from (0,0) to (dx,dy); reflected so that
    cv2.dilate grows the mask towards +dx,+dy (drop shadow direction)."""
    h, w = se.shape
    out = np.zeros((h + 2 * abs(dy), w + 2 * abs(dx)), np.uint8)
    n = max(abs(dx), abs(dy), 1)
    for k in range(n + 1):
        ox = abs(dx) + round(dx * k / n)
        oy = abs(dy) + round(dy * k / n)
        out[oy:oy + h, ox:ox + w] |= se
    return out[::-1, ::-1].copy()


def iou(a, b):
    u = np.count_nonzero(a | b)
    return np.count_nonzero(a & b) / u if u else 1.0


def pushpull(v, w, conf_gain=2.0):
    """smooth scattered-data interpolation: v (H,W,C) float32, w (H,W) weights in [0,1]."""
    squeeze = v.ndim == 2
    if squeeze:
        v = v[..., None]
    levels = []
    cv_ = v * w[..., None]
    cw = w.astype(np.float32)
    while min(cw.shape) > 6:
        levels.append((cv_, cw))
        cv_ = cv2.pyrDown(cv_)
        if cv_.ndim == 2:
            cv_ = cv_[..., None]
        cw = cv2.pyrDown(cw)
    res = cv_ / np.maximum(cw, 1e-6)[..., None]
    # coarsest level may still have empty cells: fill with global mean
    if (cw < 1e-6).any():
        tot = cw.sum()
        gm = (cv_.reshape(-1, cv_.shape[-1]).sum(0) / tot) if tot > 1e-6 else np.zeros(cv_.shape[-1], np.float32)
        res[cw < 1e-6] = gm
    for lv, lw in reversed(levels):
        up = cv2.resize(res, (lw.shape[1], lw.shape[0]), interpolation=cv2.INTER_LINEAR)
        if up.ndim == 2:
            up = up[..., None]
        a = np.clip(lw * conf_gain, 0, 1)[..., None]
        cur = lv / np.maximum(lw, 1e-6)[..., None]
        res = a * cur + (1 - a) * up
    return res[..., 0] if squeeze else res


# ----------------------------------------------------------------------------- frame io
class Frames:
    def __init__(self, ind, cap=260):
        self.ind = ind
        self.cache = OrderedDict()
        self.cap = cap

    def path(self, f):
        return os.path.join(self.ind, f"{f:04d}.jpg")

    def full(self, f):
        im = cv2.imread(self.path(f), cv2.IMREAD_COLOR)
        if im is None:
            raise IOError(self.path(f))
        return im

    def band(self, f):
        """full-res band crop, uint8 (BH,BW,3)"""
        if f in self.cache:
            self.cache.move_to_end(f)
            return self.cache[f]
        b = self.full(f)[Y0:Y1].copy()
        self.cache[f] = b
        if len(self.cache) > self.cap:
            self.cache.popitem(last=False)
        return b


# ----------------------------------------------------------------------------- masks
def lab_feats(band_small):
    f = band_small.astype(np.float32) / 255.0
    lab = cv2.cvtColor(f, cv2.COLOR_BGR2LAB)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    s = a - 0.8 * np.maximum(b, 0)
    return L, a, b, s


def strict_components(L, a, b, s):
    """raspberry fill components that are wrapped in a cream ring and a black ring"""
    fill = ((s > 17) & (L > 14)).astype(np.uint8)
    cream = ((L > 70) & (np.abs(a) < 15) & (b > -8) & (b < 28)).astype(np.uint8)
    dark = (L < 24).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(fill, connectivity=8)
    acc = np.zeros_like(fill)
    H, W = fill.shape
    fc = fill | cream
    for i in range(1, n):
        x, y, w, h, area = st[i]
        if area < 18:
            continue
        x0, y0 = max(0, x - 14), max(0, y - 14)
        x1, y1 = min(W, x + w + 14), min(H, y + h + 14)
        comp = (lab[y0:y1, x0:x1] == i).astype(np.uint8)
        d1 = cv2.dilate(comp, disk(1))
        d6 = cv2.dilate(comp, disk(6))
        d8 = cv2.dilate(comp, disk(8))
        d12 = cv2.dilate(comp, disk(12))
        ring_c = (d6 > 0) & (d1 == 0)
        ring_d = (d12 > 0) & (d8 == 0)
        cf = cream[y0:y1, x0:x1][ring_c].mean() if ring_c.any() else 0
        other = ring_d & (fc[y0:y1, x0:x1] == 0)
        no = other.sum()
        df = dark[y0:y1, x0:x1][other].mean() if no > 0 else 0
        if cf >= 0.35 and no >= 0.12 * ring_d.sum() and df >= 0.45:
            acc[y0:y1, x0:x1] |= comp
    return acc


def outline_scale(F, L):
    """caption scale from the distance (fill edge -> black outline); 1.0 = typical word"""
    if np.count_nonzero(F) < 300:
        return np.nan
    d = cv2.distanceTransform((1 - F).astype(np.uint8), cv2.DIST_L2, 5)
    dark = L < 12
    prev = 0.0
    for k in range(4, 16):
        sel = (d > k) & (d <= k + 1)
        fr = dark[sel].mean() if sel.any() else 0
        if fr >= 0.3:
            x = k + (0.3 - prev) / max(fr - prev, 1e-3)
            return float(np.clip(x / 8.3, 0.9, 1.5))
        prev = fr
    return np.nan


def shadow_se(r, dx, dy):
    return shift_union(disk(r), dx, dy)


def analyse_frames(frames, N, log):
    acc_all = np.zeros((N, H2, W2), np.uint8)
    s_all = np.zeros((N, H2, W2), np.int8)
    a_all = np.zeros((N, H2, W2), np.int8)
    b_all = np.zeros((N, H2, W2), np.int8)
    scales = np.full(N, np.nan)
    t0 = time.time()
    for f in range(1, N + 1):
        band = cv2.resize(frames.full(f)[Y0:Y1], (W2, H2), interpolation=cv2.INTER_AREA)
        L, a, b, s = lab_feats(band)
        acc = strict_components(L, a, b, s)
        acc_all[f - 1] = acc
        s_all[f - 1] = np.clip(np.round(s), -127, 127)
        a_all[f - 1] = np.clip(np.round(a), -127, 127)
        b_all[f - 1] = np.clip(np.round(b), -127, 127)
        scales[f - 1] = outline_scale(cv2.morphologyEx(acc, cv2.MORPH_CLOSE, disk(5)), L)
        if f % 200 == 0:
            log(f"  analysed {f}/{N} ({time.time() - t0:.0f}s)")
    return acc_all, s_all, a_all, b_all, scales


def build_masks(acc_all, s_all, a_all, b_all, scales, gate_dx=80, gate_up=100, gate_dn=70, win=6):
    N, H, W = acc_all.shape
    bbs = []
    for i in range(N):
        ys, xs = np.nonzero(acc_all[i])
        bbs.append((xs.min(), ys.min(), xs.max(), ys.max()) if len(xs) else None)
    sc = scales.copy()
    valid = np.nonzero(~np.isnan(sc))[0]
    for i in range(N):
        if np.isnan(sc[i]):
            sc[i] = sc[valid[np.argmin(np.abs(valid - i))]] if len(valid) else 1.0
    scs = np.array([np.median(sc[max(0, i - 3):i + 4]) for i in range(N)])
    se_cache = {}
    Wc = np.zeros_like(acc_all)
    strict_d = np.zeros_like(acc_all)
    for i in range(N):
        Wc[i] = cv2.morphologyEx(acc_all[i], cv2.MORPH_CLOSE, disk(5))
        key = int(round(max(1.0, scs[i]) * 10))
        if key not in se_cache:
            kk = key / 10.0
            se_cache[key] = shadow_se(int(round(15 * kk)) + 1, int(round(7 * kk)), int(round(8 * kk)))
        strict_d[i] = cv2.dilate(Wc[i], se_cache[key])
    se_l = shift_union(ellipse(36, 18), 8, 9)
    Wd = [cv2.dilate(Wc[i], disk(2)) > 0 for i in range(N)]
    stable = np.zeros(N, bool)
    for i in range(N):
        if not Wd[i].any():
            continue
        ok = True
        for j in (i - 1, i + 1):
            if 0 <= j < N and iou(Wd[i], Wd[j]) < 0.75:
                ok = False
        stable[i] = ok
    masks = strict_d.copy()
    nloose = 0
    for i in range(N):
        if stable[i]:
            continue
        gate = np.zeros((H, W), np.uint8)
        for j in range(max(0, i - win), min(N, i + win + 1)):
            if bbs[j] is None:
                continue
            x0, y0, x1, y1 = bbs[j]
            gate[max(0, y0 - gate_up):min(H, y1 + gate_dn + 1), max(0, x0 - gate_dx):min(W, x1 + gate_dx + 1)] = 1
        if not gate.any():
            continue
        s = cv2.GaussianBlur(s_all[i].astype(np.float32), (3, 3), 0)
        a = cv2.GaussianBlur(a_all[i].astype(np.float32), (3, 3), 0)
        b = cv2.GaussianBlur(b_all[i].astype(np.float32), (3, 3), 0)
        loose = (s > 9) & (a > 8) & (b < 0.45 * a) & (gate > 0)
        if not loose.any():
            continue
        # holograms etc.: pink that persists in the past or in the future (outside caption masks)
        persistent = np.zeros_like(loose)
        for side in ((-10, -7, -4), (4, 7, 10)):
            vals = []
            for kk in side:
                j = i + kk
                if 0 <= j < N:
                    sj = cv2.dilate(s_all[j].astype(np.float32), disk(3))
                    vals.append(np.where(strict_d[j] > 0, np.nan, sj))
            if not vals:
                continue
            V = np.stack(vals)
            cnt = np.sum(~np.isnan(V), 0)
            with np.errstate(all='ignore'):
                med = np.nanmedian(np.where(cnt[None] > 0, V, 0), 0)
            persistent |= (cnt >= 2) & (med > 0.6 * s) & (med > 6)
        loose &= ~persistent
        loose = (loose & (strict_d[i] == 0)).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(loose)
        keep = np.zeros_like(loose)
        for c in range(1, n):
            if st[c, 4] >= 25:
                keep[lab == c] = 1
        if keep.any():
            nloose += 1
            keep = cv2.morphologyEx(keep, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (15, 7)))
            masks[i] |= cv2.dilate(keep, se_l)
    return masks, stable, nloose


# ----------------------------------------------------------------------------- shots
def detect_shots(frames, N):
    if N == 1417:
        return SHOTS_1417, FADES_1417
    # generic fallback: consecutive-frame difference outside the caption band
    prev, d = None, np.zeros(N + 2)
    for f in range(1, N + 1):
        im = cv2.imread(frames.path(f), cv2.IMREAD_REDUCED_GRAYSCALE_8)
        im = np.vstack([im[:140], im[230:]]).astype(np.float32)
        if prev is not None:
            d[f] = np.abs(im - prev).mean()
        prev = im
    med = np.median(d[2:N + 1])
    trans = d > max(2.5 * med, 2.0)
    shots, fades, f = [], [], 1
    start = 1
    while f <= N:
        if trans[f]:
            g = f
            while g + 1 <= N and trans[g + 1]:
                g += 1
            # frames f..g-1 are blends, g is the first frame of the new shot
            if g - 1 >= f:
                fades.append((f, g - 1, f - 1, g))
            shots.append((start, f - 1))
            start = g
            f = g + 1
        else:
            f += 1
    shots.append((start, N))
    return shots, fades


# ----------------------------------------------------------------------------- filler
class Filler:
    def __init__(self, frames, masks_half, shots, log):
        self.fr = frames
        self.mh = masks_half          # (N,H2,W2) uint8
        self.shots = shots
        self.log = log
        self.dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
        self.gcache = OrderedDict()
        gy, gx = np.mgrid[0:BH, 0:BW].astype(np.float32)
        self.gx, self.gy = gx, gy
        hy, hx = np.mgrid[0:H2, 0:W2].astype(np.float32)
        self.hx, self.hy = hx, hy
        self.outband = {}             # filled bands (for stabilisation / fades)

    def shot_of(self, f):
        for a, b in self.shots:
            if a <= f <= b:
                return a, b
        return None

    def mask_half(self, f):
        return self.mh[f - 1] > 0

    def mask_full(self, f):
        return cv2.resize(self.mh[f - 1], (BW, BH), interpolation=cv2.INTER_NEAREST) > 0

    def gray(self, f):
        """half-res grey band with the caption pre-inpainted (for optical flow)"""
        if f in self.gcache:
            self.gcache.move_to_end(f)
            return self.gcache[f]
        b = cv2.resize(self.fr.band(f), (W2, H2), interpolation=cv2.INTER_AREA)
        g = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY)
        m = self.mh[f - 1]
        if m.any():
            g = cv2.inpaint(g, cv2.dilate(m, disk(2)), 3, cv2.INPAINT_TELEA)
        self.gcache[f] = g
        if len(self.gcache) > 400:
            self.gcache.popitem(last=False)
        return g

    def flow(self, t, s):
        """half-res flow t->s (pixel p of t is at p+F(p) in s), completed inside caption masks"""
        F = self.dis.calc(self.gray(t), self.gray(s), None)
        inval = cv2.dilate(((self.mh[t - 1] | self.mh[s - 1]) > 0).astype(np.uint8), disk(4)) > 0
        if inval.any():
            w = (~inval).astype(np.float32)
            if w.sum() < 50:
                return np.zeros_like(F)
            Fi = pushpull(F, w)
            F = np.where(inval[..., None], Fi, F).astype(np.float32)
        return F

    def warp_half(self, img, F, border=0):
        return cv2.remap(img, self.hx + F[..., 0], self.hy + F[..., 1], cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=border)

    def select_sources(self, t, Mext):
        """greedy nearest-uncovered source search in both directions (half-res)"""
        sa, sb = self.shot_of(t)
        out = []
        for dirn in (-1, 1):
            remaining = Mext.copy()
            tot = remaining.sum()
            k = 0
            while remaining.sum() > max(8, 0.002 * tot) and k < KMAX:
                k += 1
                s = t + dirn * k
                if s < sa or s > sb:
                    break
                Ms = self.mh[s - 1]
                if k > 2:
                    approx = remaining & (cv2.dilate(Ms, disk(4)) == 0)
                    if approx.sum() < max(25, 0.04 * remaining.sum()):
                        continue
                F = self.flow(t, s)
                vs = self.warp_half((1 - cv2.dilate(Ms, disk(1))).astype(np.float32), F) > 0.99
                newly = remaining & vs
                if newly.sum() < max(10, 0.02 * remaining.sum()) and k > 2:
                    continue
                if newly.sum() == 0:
                    continue
                out.append(dict(s=s, k=k, dir=dirn, F=F, newly=newly, valid=vs))
                remaining &= ~newly
        return out

    def composite(self, t, layers, Mext_h):
        """blend source layers at full res; returns fill (BH,BW,3) float32, weight sum"""
        # distance maps per direction
        INF = 1e9
        D = {-1: np.full((H2, W2), INF, np.float32), 1: np.full((H2, W2), INF, np.float32)}
        for L in layers:
            D[L['dir']][L['newly']] = L['k']
        acc = np.zeros((BH, BW, 3), np.float32)
        wsum = np.zeros((BH, BW), np.float32)
        for L in layers:
            dself = float(L['k'])
            doth = D[-L['dir']]
            wt = np.where(doth >= INF, 1.0, doth / (doth + dself)).astype(np.float32)
            w = (L['newly'].astype(np.float32) * wt)
            w = cv2.GaussianBlur(w, (0, 0), 2.0)
            w *= L['valid']
            if w.max() < 1e-4:
                continue
            Ff = cv2.resize(L['F'], (BW, BH), interpolation=cv2.INTER_LINEAR) * 2.0
            mx, my = self.gx + Ff[..., 0], self.gy + Ff[..., 1]
            src = self.fr.band(L['s'])
            col = cv2.remap(src, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
            Ms = self.mask_full(L['s']).astype(np.uint8)
            vfull = cv2.remap((1 - cv2.dilate(Ms, disk(2))).astype(np.float32), mx, my, cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=0) > 0.99
            wf = cv2.resize(w, (BW, BH), interpolation=cv2.INTER_LINEAR) * vfull
            acc += col * wf[..., None]
            wsum += wf
        return acc, wsum

    def fill_frame(self, t):
        band = self.fr.band(t).astype(np.float32)
        Mh = self.mask_half(t)
        Mext_h = cv2.dilate(Mh.astype(np.uint8), disk(5)) > 0
        layers = self.select_sources(t, Mext_h)
        acc, wsum = self.composite(t, layers, Mext_h)
        M = self.mask_full(t)
        Mext = cv2.resize(Mext_h.astype(np.uint8), (BW, BH), interpolation=cv2.INTER_NEAREST) > 0
        ok = wsum > 1e-3
        fill = np.where(ok[..., None], acc / np.maximum(wsum, 1e-6)[..., None], 0).astype(np.float32)
        hole = M & ~ok
        nhole = int(hole.sum())
        if nhole:
            fill = self.spatial_fill(band, fill, M, hole)
            ok = ok | hole
        # seam correction on ring (Mext \ M)
        ring = Mext & ~M & ok
        fill = self.seam_correct(band, fill, M, ring)
        nl = len(layers)
        far = max([L['k'] for L in layers], default=0)
        return fill, M, dict(t=t, layers=nl, far=far, hole=nhole, area=int(M.sum()),
                             srcs=sorted(set(L['s'] for L in layers)))

    def spatial_fill(self, band, fill, M, hole):
        """inpaint pixels with no temporal source (half-res Telea on the partially filled band)"""
        known = np.where((M & ~hole)[..., None], fill, band)
        kh = cv2.resize(np.clip(known, 0, 255).astype(np.uint8), (W2, H2), interpolation=cv2.INTER_AREA)
        hh = cv2.resize(hole.astype(np.uint8), (W2, H2), interpolation=cv2.INTER_AREA)
        hh = cv2.dilate((hh > 0).astype(np.uint8), disk(2))
        inp = cv2.inpaint(kh, hh, 6, cv2.INPAINT_TELEA)
        up = cv2.resize(inp, (BW, BH), interpolation=cv2.INTER_CUBIC).astype(np.float32)
        return np.where(hole[..., None], up, fill)

    def seam_correct(self, band, fill, M, ring):
        if ring.sum() < 50:
            return fill
        D = (band - fill)
        Dh = cv2.resize(np.where(ring[..., None], D, 0).astype(np.float32), (W2, H2), interpolation=cv2.INTER_AREA)
        wh = cv2.resize(ring.astype(np.float32), (W2, H2), interpolation=cv2.INTER_AREA)
        Dh = Dh / np.maximum(wh, 1e-6)[..., None]
        Di = pushpull(Dh, (wh > 0.5).astype(np.float32), conf_gain=4.0)
        Di = cv2.resize(Di, (BW, BH), interpolation=cv2.INTER_LINEAR)
        return fill + Di


def compose(band, fill, M):
    """final composite with a 3 px feather outside the mask"""
    Md = cv2.dilate(M.astype(np.uint8), disk(2))
    alpha = cv2.GaussianBlur(Md.astype(np.float32), (0, 0), 1.5)
    alpha = np.maximum(alpha, M.astype(np.float32))[..., None]
    out = band.astype(np.float32) * (1 - alpha) + fill * alpha
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)


# ----------------------------------------------------------------------------- main
def parse_range(s, N):
    if not s:
        return 1, N
    a, b = s.split('-')
    return max(1, int(a)), min(N, int(b))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('in_dir')
    ap.add_argument('out_dir')
    ap.add_argument('--frames', default=None)
    ap.add_argument('--cache', default=None, help='directory for the mask cache (default OUT_DIR_cache)')
    ap.add_argument('--no-stab', action='store_true')
    args = ap.parse_args()
    ind, outd = args.in_dir, args.out_dir
    os.makedirs(outd, exist_ok=True)
    cache = args.cache or (outd.rstrip('/') + '_cache')
    os.makedirs(cache, exist_ok=True)
    N = 0
    while os.path.exists(os.path.join(ind, f"{N + 1:04d}.jpg")):
        N += 1
    if N == 0:
        sys.exit('no frames')
    A, B = parse_range(args.frames, N)
    logf = open(os.path.join(cache, 'log.txt'), 'a')

    def log(msg):
        print(msg, flush=True)
        logf.write(msg + '\n'); logf.flush()

    log(f"== remove_captions {ind} -> {outd} frames {A}-{B} of {N}")
    frames = Frames(ind)
    T0 = time.time()
    # ---- masks
    mpath = os.path.join(cache, 'masks.npz')
    sig = f"{os.path.abspath(ind)}|{N}|{os.path.getsize(frames.path(1))}|{os.path.getsize(frames.path(N))}"
    masks = None
    if os.path.exists(mpath):
        z = np.load(mpath, allow_pickle=False)
        if str(z['sig']) == sig:
            masks = z['masks']
            log('masks loaded from cache')
    if masks is None:
        acc, s, a, b, scales = analyse_frames(frames, N, log)
        masks, stable, nloose = build_masks(acc, s, a, b, scales)
        del acc, s, a, b
        np.savez_compressed(mpath, masks=masks, sig=np.array(sig))
        log(f"masks built in {time.time() - T0:.0f}s, stable {int(stable.sum())}, loose-frames {nloose}")
    shots, fades = detect_shots(frames, N)
    fade_frames = {f: fd for fd in fades for f in range(fd[0], fd[1] + 1)}
    filler = Filler(frames, masks, shots, log)
    stats = []
    T1 = time.time()
    nproc = 0

    # frames needed: requested range; stabilisation needs fills of t-1/t+1 too
    want = list(range(A, B + 1))
    fill_cache = OrderedDict()

    def get_fill(t):
        if t in fill_cache:
            return fill_cache[t]
        if not masks[t - 1].any():
            r = None
        elif t in fade_frames:
            r = fade_fill(t)
        else:
            fill, M, st = filler.fill_frame(t)
            stats.append(st)
            r = (fill, M)
        fill_cache[t] = r
        if len(fill_cache) > 8:
            fill_cache.popitem(last=False)
        return r

    def plain_fill_band(t):
        """band of frame t after caption removal (no stabilisation)"""
        r = get_fill(t)
        band = frames.band(t)
        if r is None:
            return band.astype(np.float32)
        return compose(band, r[0], r[1]).astype(np.float32)

    def fade_fill(t):
        f0, f1, fa, fb = fade_frames[t]
        band = frames.band(t).astype(np.float32)
        M = filler.mask_full(t)
        Ab = plain_fill_band(fa)
        Bb = plain_fill_band(fb)
        sel = ~cv2.dilate(M.astype(np.uint8), disk(6)).astype(bool)
        dA = (Ab - Bb)[sel].reshape(-1)
        dI = (band - Bb)[sel].reshape(-1)
        alpha = float(np.clip((dA * dI).sum() / max((dA * dA).sum(), 1e-6), 0, 1))
        fill = alpha * Ab + (1 - alpha) * Bb
        Mext = cv2.dilate(M.astype(np.uint8), disk(10)) > 0
        fill = filler.seam_correct(band, fill, M, Mext & ~M)
        stats.append(dict(t=t, fade_alpha=round(alpha, 3), area=int(M.sum())))
        return (fill, M)

    for t in want:
        dst = os.path.join(outd, f"{t:04d}.jpg")
        r = get_fill(t)
        if r is None:
            shutil.copyfile(frames.path(t), dst)
            continue
        fill, M = r
        if not args.no_stab and t not in fade_frames:
            # temporal stabilisation: average with motion-compensated neighbouring results
            sa, sb = filler.shot_of(t)
            accf = fill * 2.0
            wsum = 2.0
            for n in (t - 1, t + 1):
                if n < sa or n > sb:
                    continue
                nb = plain_fill_band(n)
                F = filler.flow(t, n)
                Ff = cv2.resize(F, (BW, BH), interpolation=cv2.INTER_LINEAR) * 2.0
                w = cv2.remap(nb, filler.gx + Ff[..., 0], filler.gy + Ff[..., 1], cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_REPLICATE)
                accf += w
                wsum += 1.0
            fill = accf / wsum
        band = frames.band(t)
        outband = compose(band, fill, M)
        full = frames.full(t)
        full[Y0:Y1] = outband
        cv2.imwrite(dst, full, [cv2.IMWRITE_JPEG_QUALITY, 97])
        nproc += 1
        if nproc % 25 == 0:
            el = time.time() - T1
            log(f"  {t}: {nproc} processed, {el / nproc:.2f}s/frame")
    el = time.time() - T1
    log(f"done: {nproc} frames inpainted, {len(want) - nproc} copied; fill time {el:.0f}s "
        f"({el / max(nproc, 1):.2f}s/processed frame); total {time.time() - T0:.0f}s")
    with open(os.path.join(cache, f'stats_{A}_{B}.json'), 'w') as fh:
        json.dump(stats, fh, default=lambda o: o if not isinstance(o, np.generic) else o.item())


if __name__ == '__main__':
    main()
