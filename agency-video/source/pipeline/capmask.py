"""Caption mask detection (development module; merged into remove_captions.py)."""
import cv2, numpy as np

Y0, Y1 = 1150, 1800          # band analysed (full-res rows)
SC = 0.5                     # mask analysis scale


def disk(r):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def shadow_se(r, dx, dy):
    """union of a disk at (0,0) and a disk shifted by (dx,dy) (bottom-right shadow)"""
    h = 2 * r + 1 + abs(dy)
    w = 2 * r + 1 + abs(dx)
    se = np.zeros((h * 2, w * 2), np.uint8)
    cy, cx = h, w
    cv2.circle(se, (cx, cy), r, 1, -1)
    # include intermediate disks so the hull is continuous
    n = max(abs(dx), abs(dy))
    for i in range(1, n + 1):
        cv2.circle(se, (cx + round(dx * i / n), cy + round(dy * i / n)), r, 1, -1)
    # dilate() uses the SE centred on its anchor: reflect so that the mask grows towards +dx,+dy
    se = se[::-1, ::-1].copy()
    return se


def lab_feats(band_small):
    f = band_small.astype(np.float32) / 255.0
    lab = cv2.cvtColor(f, cv2.COLOR_BGR2LAB)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    s = a - 0.8 * np.maximum(b, 0)
    return L, a, b, s


def strict_components(L, a, b, s):
    fill = ((s > 17) & (L > 14)).astype(np.uint8)
    cream = ((L > 70) & (np.abs(a) < 15) & (b > -8) & (b < 28)).astype(np.uint8)
    dark = (L < 24).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(fill, connectivity=8)
    acc = np.zeros_like(fill)
    H, W = fill.shape
    fc = fill | cream
    info = []
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
        ok = cf >= 0.35 and no >= 0.12 * ring_d.sum() and df >= 0.45
        info.append((i, area, round(float(cf), 2), round(float(df), 2), int(no), ok))
        if ok:
            acc[y0:y1, x0:x1] |= comp
    return acc, fill, cream, info


def ellipse(rx, ry):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rx + 1, 2 * ry + 1))


def shift_union(se, dx, dy):
    h, w = se.shape
    out = np.zeros((h + 2 * abs(dy), w + 2 * abs(dx)), np.uint8)
    n = max(abs(dx), abs(dy), 1)
    for k in range(n + 1):
        ox = abs(dx) + round(dx * k / n); oy = abs(dy) + round(dy * k / n)
        out[oy:oy + h, ox:ox + w] |= se
    return out[::-1, ::-1].copy()


def iou(a, b):
    u = np.count_nonzero(a | b)
    return np.count_nonzero(a & b) / u if u else 1.0


def outline_scale(F, L):
    """estimate caption scale from where the black outline starts (distance from fill)"""
    if np.count_nonzero(F) < 300:
        return None
    d = cv2.distanceTransform((1 - F).astype(np.uint8), cv2.DIST_L2, 5)
    dark = L < 12
    prev = 0.0
    for k in range(4, 16):
        sel = (d > k) & (d <= k + 1)
        fr = dark[sel].mean() if sel.any() else 0
        if fr >= 0.3:
            x = k + (0.3 - prev) / max(fr - prev, 1e-3)   # crossing between k and k+1 (bin centre ~k+0.5)
            return float(np.clip(x / 8.3, 0.9, 1.5))
        prev = fr
    return None


def build_masks(acc_all, s_all, a_all, b_all, scales, gate_dx=80, gate_up=100, gate_dn=70, win=6):
    N, H, W = acc_all.shape
    bbs = []
    for i in range(N):
        ys, xs = np.nonzero(acc_all[i])
        bbs.append((xs.min(), ys.min(), xs.max(), ys.max()) if len(xs) else None)
    # fill missing scales from nearest valid
    sc = np.array([np.nan if v is None else v for v in scales], float)
    valid = np.nonzero(~np.isnan(sc))[0]
    for i in range(N):
        if np.isnan(sc[i]):
            sc[i] = sc[valid[np.argmin(np.abs(valid - i))]] if len(valid) else 1.0
    # smooth scale over time (median of 7)
    scs = np.array([np.median(sc[max(0, i - 3):i + 4]) for i in range(N)])
    se_cache = {}
    Wc = np.zeros_like(acc_all)
    strict_d = np.zeros_like(acc_all)
    for i in range(N):
        Wc[i] = cv2.morphologyEx(acc_all[i], cv2.MORPH_CLOSE, disk(5))
        k = max(1.0, scs[i])
        key = round(k * 10)
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
    loose_dbg = {}
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
        vals = []
        for kk in (-10, -7, -4, 4, 7, 10):
            j = i + kk
            if j < 0 or j >= N:
                continue
            sj = cv2.dilate(s_all[j].astype(np.float32), disk(3))
            vals.append(np.where(strict_d[j] > 0, np.nan, sj))
        if vals:
            V = np.stack(vals)
            cnt = np.sum(~np.isnan(V), 0)
            with np.errstate(all='ignore'):
                med = np.nanmedian(np.where(cnt[None] > 0, V, 0), 0)
            persistent = (cnt >= 2) & (med > 0.6 * s) & (med > 6)
            loose &= ~persistent
        loose = (loose & (strict_d[i] == 0)).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(loose)
        keep = np.zeros_like(loose)
        for c in range(1, n):
            if st[c, 4] >= 25:
                keep[lab == c] = 1
        if keep.any():
            keep = cv2.morphologyEx(keep, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (15, 7)))
            loose_dbg[i] = keep
            masks[i] |= cv2.dilate(keep, se_l)
    return masks, stable, loose_dbg, scs
