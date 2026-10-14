"""Remove the burned-in one-word captions.

usage: python3 -I remove.py IN_DIR[:OVERRIDE_DIR] OUT_DIR MASKS.npz [A-B]
(frames present in OVERRIDE_DIR, e.g. the laptop-fixed ones, are read from there instead of IN_DIR)

Masks: (N, 325, 540) half-res caption masks of the band y 1150-1800 (from the caption stream).
Fill: each masked pixel takes the nearest earlier/later frame (<= K frames away, same shot) in which
that pixel is uncovered (distance-weighted when both exist); pixels never uncovered nearby are
inpainted spatially. These leftovers sit at the centre of the band, which the new caption cards cover.
"""
import sys, os, shutil
import numpy as np
import cv2

cv2.setNumThreads(3)
IN, OUT, MPATH = sys.argv[1:4]
IN, OVR = (IN.split(':') + [None])[:2]


def src_path(n):
    name = f'{n:04d}.jpg'
    if OVR and os.path.exists(os.path.join(OVR, name)):
        return os.path.join(OVR, name)
    return os.path.join(IN, name)
rng = sys.argv[4] if len(sys.argv) > 4 else None
os.makedirs(OUT, exist_ok=True)
Y0, Y1 = 1150, 1800
K = 8
# shots and crossfades (1-based inclusive); never borrow across these boundaries
SEGS = [(1, 178), (179, 187), (188, 458), (459, 464), (465, 721), (722, 729), (730, 1018),
        (1019, 1032), (1033, 1274), (1275, 1284), (1285, 1417)]


def seg_of(n):
    for a, b in SEGS:
        if a <= n <= b:
            return a, b
    raise ValueError(n)


raw = np.load(MPATH)['masks']
N = raw.shape[0]


def pinkish(band):
    b = band.astype(np.int16)
    B, G, R = b[..., 0], b[..., 1], b[..., 2]
    return (R - G > 14) & (B - G > 1) & (R > 90)


HOLO = (465, 1018)   # shots with pink holograms near the band


def raw_full(i):
    return cv2.resize(raw[i] * 255, (1080, Y1 - Y0), interpolation=cv2.INTER_NEAREST)


def clean_mask(i):
    """full-res band mask (650x1080 bool) for frame index i (0-based).
    Union with the neighbours' masks (same shot): the detector occasionally misses a
    pop-animation frame almost entirely, and captions barely move between frames."""
    sa, sb = seg_of(i + 1)
    m = raw_full(i)
    for j in (i - 1, i + 1):
        if sa <= j + 1 <= sb:
            m = m | raw_full(j)
    if not m.any():
        return m > 0
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    keep = np.zeros(n, bool)
    for c in range(1, n):
        x, y, w, h, a = st[c]
        # pieces lying wholly above the caption zone are hologram false-positives
        if Y0 + y + h < 1290 or a < 40:
            continue
        keep[c] = True
    m = keep[lab].astype(np.uint8) * 255
    if m.any():
        # faint motion-blur streaks of the pop animations: magenta pixels near the caption
        r = 61 if HOLO[0] <= i + 1 <= HOLO[1] else 121
        near = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (r, r))) > 0
        pk = (pinkish(get_band(i + 1)) & near).astype(np.uint8) * 255
        m = cv2.dilate(m | pk, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13)))
    return m > 0


masks = {}


def get_mask(i):
    if i not in masks:
        masks[i] = clean_mask(i)
    return masks[i]


bands = {}


def get_band(n):
    if n not in bands:
        im = cv2.imread(src_path(n))
        bands[n] = im[Y0:Y1].astype(np.float32)
        if len(bands) > 4 * K + 8:
            bands.pop(next(iter(bands)))
    return bands[n]


a0, b0 = (1, N) if not rng else map(int, rng.split('-'))
done = copied = 0
info = {}   # per frame: bbox of the whole mask and of the spatially inpainted (never uncovered) part
for n in range(a0, b0 + 1):
    name = f'{n:04d}.jpg'
    m = get_mask(n - 1)
    if not m.any():
        shutil.copyfile(src_path(n), os.path.join(OUT, name))
        copied += 1
        continue
    sa, sb = seg_of(n)
    full = cv2.imread(src_path(n))
    band = full[Y0:Y1].astype(np.float32)
    acc = np.zeros_like(band)
    wsum = np.zeros(m.shape, np.float32)
    for direction in (-1, 1):
        need = m.copy()
        for k in range(1, K + 1):
            j = n + direction * k
            if j < sa or j > sb or not need.any():
                break
            ok = need & ~get_mask(j - 1) & ~pinkish(get_band(j))
            if ok.any():
                w = 1.0 / k
                acc[ok] += get_band(j)[ok] * w
                wsum[ok] += w
                need &= ~ok
    have = wsum > 0
    fill = band.copy()
    fill[have] = acc[have] / wsum[have][:, None]
    rest = m & ~have
    bb = lambda q: None if not q.any() else [int(np.nonzero(q.any(0))[0][[0, -1]][0]), int(np.nonzero(q.any(0))[0][-1]),
                                             int(np.nonzero(q.any(1))[0][0] + Y0), int(np.nonzero(q.any(1))[0][-1] + Y0)]
    info[n] = {'mask': bb(m), 'rest': bb(rest)}
    fill8 = np.clip(fill, 0, 255).astype(np.uint8)
    if rest.any():
        # spatial inpaint of what no nearby frame uncovers (half-res for smoothness/speed)
        small = cv2.resize(fill8, (540, 325), interpolation=cv2.INTER_AREA)
        rm = cv2.resize(rest.astype(np.uint8) * 255, (540, 325), interpolation=cv2.INTER_NEAREST)
        rm = cv2.dilate(rm, np.ones((3, 3), np.uint8))
        inp = cv2.inpaint(small, rm, 6, cv2.INPAINT_TELEA)
        inp = cv2.resize(inp, (1080, Y1 - Y0), interpolation=cv2.INTER_CUBIC)
        fill8[rest] = inp[rest]
    # feathered composite: fill fully inside the mask, soft 3 px blend outward
    alpha = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 2.0)
    alpha = np.maximum(alpha, m.astype(np.float32))[:, :, None]
    out = band * (1 - alpha) + fill8.astype(np.float32) * alpha
    full[Y0:Y1] = np.clip(out + 0.5, 0, 255).astype(np.uint8)
    cv2.imwrite(os.path.join(OUT, name), full, [cv2.IMWRITE_JPEG_QUALITY, 97])
    done += 1
    if done % 100 == 0:
        print(f'{n} processed {done} copied {copied}', flush=True)
import json
json.dump(info, open(os.path.join(OUT, '..', f'fillinfo_{a0}_{b0}.json'), 'w'))
print(f'DONE processed {done} copied {copied}')
