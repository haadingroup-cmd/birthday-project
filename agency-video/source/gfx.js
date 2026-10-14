'use strict';
// Motion graphics for the Haadin Global agency ad.
// Every timing below is in seconds on the source timeline (source runs 0 → 47.233s,
// the end card runs on after it until TOTAL).

const W = 1080, H = 1920, FPS = 30;
const SRC_N = 1417, SRC_END = SRC_N / FPS;
const TOTAL = 50.7;
// The wordless transformation (source 15.6–18.6s) plays at 1.5x. Everything else is 1:1.
const RT = { a: 15.6, b: 18.6, k: 1.5 };
const CUT = (RT.b - RT.a) * (1 - 1 / RT.k);
const TOTAL_OUT = TOTAL - CUT;
function srcOf(o) {
  if (o < RT.a) return o;
  const d = (RT.b - RT.a) / RT.k;
  return o < RT.a + d ? RT.a + (o - RT.a) * RT.k : o + CUT;
}
const BRAND1 = 'HAADIN', BRAND2 = 'GLOBAL';
const COL = {
  ink: '#0E0F15', ink2: '#191B27', cream: '#F6EEDF', rasp: '#A8325C',
  pink: '#FF4F8B', coral: '#FF8A66', red: '#FF4057', green: '#35D69A',
};

const cv = document.getElementById('c');
const ctx = cv.getContext('2d');
const mk = (w, h) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; };
const blurCv = mk(270, 480), bctx = blurCv.getContext('2d');
const tmpCv = mk(W, H), tctx = tmpCv.getContext('2d');
const tmp2 = mk(W, H), t2ctx = tmp2.getContext('2d');
const layer = mk(W, H), lctx = layer.getContext('2d');

// ---------- math ----------
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, t) => a + (b - a) * t;
const p = (t, a, b) => clamp((t - a) / (b - a));
const eOutC = x => 1 - Math.pow(1 - x, 3);
const eInC = x => x * x * x;
const eIOC = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
const eOutBack = (x, s = 1.70158) => { const c3 = s + 1; return 1 + c3 * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2); };
const rnd = s => { const x = Math.sin(s * 12.9898 + 78.233) * 43758.5453; return x - Math.floor(x); };
// fade-in over [a, a+din], fade-out over [b, b+dout]
const vis = (t, a, b, din = .3, dout = .25) => Math.min(p(t, a, a + din), 1 - p(t, b, b + dout));

// ---------- icons (24x24 stroke paths, Feather-style) ----------
const P = s => new Path2D(s);
const ICONS = {
  phone: [P('M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z')],
  slash: [P('M2 2L22 22')],
  search: [P('M11 3a8 8 0 1 0 0 16a8 8 0 1 0 0-16z'), P('M21 21l-4.35-4.35')],
  mail: [P('M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z'), P('M22 6l-10 7L2 6')],
  cart: [P('M9 20a1 1 0 1 0 0 2a1 1 0 1 0 0-2z'), P('M20 20a1 1 0 1 0 0 2a1 1 0 1 0 0-2z'), P('M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6')],
  chat: [P('M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z')],
  target: [P('M12 2a10 10 0 1 0 0 20a10 10 0 1 0 0-20z'), P('M12 6a6 6 0 1 0 0 12a6 6 0 1 0 0-12z'), P('M12 10a2 2 0 1 0 0 4a2 2 0 1 0 0-4z')],
  megaphone: [P('M3 11l18-5v12L3 14v-3z'), P('M11.6 16.8a3 3 0 1 1-5.8-1.6')],
  browser: [P('M3 3h18a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z'), P('M1 8h22'), P('M5 5.5h.01M8 5.5h.01')],
  trend: [P('M23 6l-9.5 9.5-5-5L1 18'), P('M17 6h6v6')],
  down: [P('M12 5v14'), P('M19 12l-7 7-7-7')],
  up: [P('M12 19V5'), P('M5 12l7-7 7 7')],
  check: [P('M20 6L9 17l-5-5')],
  x: [P('M18 6L6 18'), P('M6 6l12 12')],
  pin: [P('M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z'), P('M12 7a3 3 0 1 0 0 6a3 3 0 1 0 0-6z')],
  arrowR: [P('M5 12h14'), P('M12 5l7 7-7 7')],
};
const PLANE = P('M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z');

function icon(c, name, cx, cy, size, color, lw = 2.2) {
  c.save();
  c.translate(cx - size / 2, cy - size / 2);
  c.scale(size / 24, size / 24);
  c.strokeStyle = color; c.lineWidth = lw; c.lineCap = 'round'; c.lineJoin = 'round';
  for (const path of ICONS[name]) c.stroke(path);
  c.restore();
}

// ---------- drawing helpers ----------
const font = (w, s, fam = 'Montserrat', st = 'normal') => `${st} ${w} ${s}px ${fam}`;
function rr(c, x, y, w, h, r) { c.beginPath(); c.roundRect(x, y, w, h, r); }

function grad(c, x0, y0, x1, y1, a = COL.pink, b = COL.coral) {
  const g = c.createLinearGradient(x0, y0, x1, y1); g.addColorStop(0, a); g.addColorStop(1, b); return g;
}

// Frosted glass card. Works under any transform: the backdrop is drawn in screen space.
function glass(c, x, y, w, h, r, o = {}) {
  const tint = o.tint || 'rgba(14,15,21,0.58)';
  c.save();
  if (o.shadow !== false) {
    c.save();
    c.shadowColor = 'rgba(0,0,0,0.45)'; c.shadowBlur = 40; c.shadowOffsetY = 16;
    rr(c, x, y, w, h, r); c.fillStyle = 'rgba(0,0,0,0.5)'; c.fill();
    c.restore();
  }
  c.save();
  rr(c, x, y, w, h, r); c.clip();
  const m = c.getTransform();
  c.setTransform(1, 0, 0, 1, 0, 0);
  c.drawImage(blurCv, 0, 0, W, H);
  c.setTransform(m);
  c.fillStyle = tint; c.fillRect(x, y, w, h);
  if (o.sheen !== false) {
    const g = c.createLinearGradient(x, y, x, y + h);
    g.addColorStop(0, 'rgba(255,255,255,0.10)'); g.addColorStop(0.5, 'rgba(255,255,255,0.0)');
    c.fillStyle = g; c.fillRect(x, y, w, h);
  }
  c.restore();
  rr(c, x + .75, y + .75, w - 1.5, h - 1.5, r);
  c.lineWidth = o.borderW || 1.5;
  c.strokeStyle = o.border || 'rgba(255,255,255,0.18)';
  c.stroke();
  c.restore();
}

// Caption word in the same style as the captions already burned into the footage.
function captionWord(c, word, cx, cy, size, k) {
  const s = k < 1 ? lerp(0.55, 1, eOutBack(k, 2.4)) : 1;
  c.save();
  c.globalAlpha *= clamp(k * 3);
  c.translate(cx, cy); c.scale(s, s);
  c.font = font(900, size, 'Montserrat', 'italic');
  c.textAlign = 'center'; c.textBaseline = 'middle'; c.lineJoin = 'round';
  c.strokeStyle = '#000'; c.lineWidth = size * 0.36;
  c.strokeText(word, size * 0.05, size * 0.08);
  c.strokeStyle = '#0b0b0b'; c.lineWidth = size * 0.34; c.strokeText(word, 0, 0);
  c.strokeStyle = COL.cream; c.lineWidth = size * 0.19; c.strokeText(word, 0, 0);
  c.fillStyle = COL.rasp; c.fillText(word, 0, 0);
  c.restore();
}

function globeIcon(c, cx, cy, r, k = 1, color = COL.cream, accent = COL.pink, lw) {
  lw = lw || r * 0.13;
  c.save(); c.translate(cx, cy); c.lineCap = 'round'; c.strokeStyle = color; c.lineWidth = lw;
  const k1 = eOutC(p(k, 0, .6));
  if (k1 > 0) { c.beginPath(); c.arc(0, 0, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * k1); c.stroke(); }
  const k2 = eOutC(p(k, .25, .85));
  if (k2 > 0) {
    c.beginPath(); c.ellipse(0, 0, r * .45, r, 0, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * k2); c.stroke();
    c.beginPath(); c.moveTo(-r * k2, 0); c.lineTo(r * k2, 0); c.stroke();
  }
  const k3 = eOutC(p(k, .45, 1));
  if (k3 > 0) {
    c.save(); c.rotate(-0.42); c.strokeStyle = accent; c.lineWidth = lw * .85;
    const a0 = Math.PI * .1, a1 = a0 + Math.PI * 1.75 * k3;
    c.beginPath(); c.ellipse(0, 0, r * 1.5, r * .42, 0, a0, a1); c.stroke();
    c.fillStyle = accent; c.beginPath(); c.arc(r * 1.5 * Math.cos(a1), r * .42 * Math.sin(a1), lw * 1.15, 0, 7); c.fill();
    c.restore();
  }
  c.restore();
}

// Brand lockup centred on (0,0) in the current transform. k = reveal 0..1, sweep = 0..1 light sweep.
function lockup(c, k = 1, sweep = -1, big = 92) {
  const R = big * 0.55;
  c.font = font(900, big);
  c.letterSpacing = '0px';
  const wH = c.measureText(BRAND1).width;
  const gap = big * 0.42;
  const totalW = R * 2 + gap + wH;
  const x0 = -totalW / 2;
  globeIcon(c, x0 + R, -big * 0.05, R, p(k, 0, .7), COL.cream, COL.pink, R * 0.14);
  const tx = x0 + 2 * R + gap;
  // HAADIN letters rise out of a mask
  c.save();
  c.beginPath(); c.rect(tx - 20, -big * 0.95, wH + 40, big * 1.0); c.clip();
  c.textBaseline = 'alphabetic'; c.textAlign = 'left';
  let x = tx;
  for (let i = 0; i < BRAND1.length; i++) {
    const ch = BRAND1[i];
    const ki = eOutC(p(k, .1 + i * .06, .1 + i * .06 + .4));
    c.fillStyle = COL.cream;
    c.fillText(ch, x, big * 0.0 + (1 - ki) * big);
    x += c.measureText(ch).width;
  }
  c.restore();
  // GLOBAL, letter-spaced to the width of HAADIN
  const gs = big * 0.42;
  c.font = font(800, gs);
  const w0 = c.measureText(BRAND2).width;
  const sp = clamp((wH - w0) / (BRAND2.length - 1), 0, gs * 0.42);
  const kg = eOutC(p(k, .45, .95));
  c.save();
  c.globalAlpha *= kg;
  c.fillStyle = COL.pink; c.textAlign = 'left';
  let gx = tx;
  for (const ch of BRAND2) { c.fillText(ch, gx + (1 - kg) * 30, big * 0.52); gx += c.measureText(ch).width + sp; }
  c.restore();
  return { w: totalW, h: big * 1.5 };
}

function sweepOver(c, x, y, w, h, s) {
  if (s <= 0 || s >= 1) return;
  c.save();
  c.globalCompositeOperation = 'source-atop';
  const sx = lerp(x - 200, x + w + 200, s);
  const g = c.createLinearGradient(sx - 140, y, sx + 140, y + h);
  g.addColorStop(0, 'rgba(255,255,255,0)'); g.addColorStop(.5, 'rgba(255,255,255,0.85)'); g.addColorStop(1, 'rgba(255,255,255,0)');
  c.fillStyle = g; c.fillRect(x, y, w, h);
  c.restore();
}

function clearLayer() { lctx.setTransform(1, 0, 0, 1, 0, 0); lctx.globalAlpha = 1; lctx.clearRect(0, 0, W, H); }

// ---------- camera: zoom punches, shake, grade ----------
const PUNCHES = [[2.45, .035], [6.45, .03], [8.25, .03], [10.0, .035], [14.34, .06], [21.05, .04], [23.55, .075], [38.2, .03]];
const SHAKES = [[2.45, 7, .3], [14.34, 16, .35], [23.55, 14, .4], [10.0, 5, .25]];

function zoomAt(t) {
  let z = 1 + 0.12 * (1 - eOutC(p(t, 0, .55)));
  for (const [t0, a] of PUNCHES) {
    const u = t - t0; if (u < 0 || u > 1.6) continue;
    z += a * (u < .07 ? eOutC(u / .07) : Math.exp(-(u - .07) / .32));
  }
  return z;
}
function shakeAt(t) {
  let dx = 0, dy = 0;
  for (const [t0, amp, dur] of SHAKES) {
    const u = t - t0; if (u < 0 || u > dur) continue;
    const d = amp * (1 - u / dur);
    dx += d * Math.sin(u * 95 + t0); dy += d * Math.cos(u * 77 + t0 * 3);
  }
  return [dx, dy];
}
function satAt(t) {
  if (t < 6) return 1.04;
  if (t < 15.3) return lerp(1.04, 0.55, eIOC(p(t, 6, 14.6)));
  return lerp(0.55, 1.1, eOutC(p(t, 15.3, 17.6)));
}

function drawVideo(img, t, img2 = null, frac = 0) {
  let z = zoomAt(t);
  const [dx, dy] = shakeAt(t);
  z = Math.max(z, 1 + 2.4 * Math.max(Math.abs(dx) / W, Math.abs(dy) / H));
  ctx.save();
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
  ctx.translate(W / 2 + dx, H * 0.42 + dy); ctx.scale(z, z); ctx.translate(-W / 2, -H * 0.42);
  ctx.filter = `saturate(${satAt(t).toFixed(3)}) contrast(1.06)`;
  ctx.drawImage(img, 0, 0, W, H);
  if (img2 && frac > 0.01) { ctx.globalAlpha = frac; ctx.drawImage(img2, 0, 0, W, H); ctx.globalAlpha = 1; }
  ctx.restore();
  ctx.filter = 'none';
  // vignette + top shade for header legibility
  const v = ctx.createRadialGradient(W / 2, H * .45, 420, W / 2, H * .45, 1250);
  v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(0,0,0,0.42)');
  ctx.fillStyle = v; ctx.fillRect(0, 0, W, H);
  const tg = ctx.createLinearGradient(0, 0, 0, 560);
  tg.addColorStop(0, 'rgba(0,0,0,0.30)'); tg.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = tg; ctx.fillRect(0, 0, W, 560);
}

function glitch(t, f) {
  if (t < 14.3 || t > 14.64) return;
  tctx.setTransform(1, 0, 0, 1, 0, 0); tctx.clearRect(0, 0, W, H); tctx.drawImage(cv, 0, 0);
  // colour fringes
  for (const [col, off] of [['#ff2d6f', 16], ['#22e6ff', -16]]) {
    t2ctx.globalCompositeOperation = 'source-over'; t2ctx.clearRect(0, 0, W, H); t2ctx.drawImage(tmpCv, 0, 0);
    t2ctx.globalCompositeOperation = 'multiply'; t2ctx.fillStyle = col; t2ctx.fillRect(0, 0, W, H);
    ctx.save(); ctx.globalCompositeOperation = 'screen'; ctx.globalAlpha = .45; ctx.drawImage(tmp2, off + (rnd(f) - .5) * 10, 0); ctx.restore();
  }
  // displaced slices
  for (let i = 0; i < 7; i++) {
    const y = Math.floor(rnd(f * 7 + i) * H), h = 18 + Math.floor(rnd(f * 13 + i) * 110);
    const off = (rnd(f * 3 + i * 5) - .5) * 90;
    ctx.drawImage(tmpCv, 0, y, W, h, off, y, W, h);
  }
  ctx.fillStyle = 'rgba(0,0,0,0.12)';
  for (let y = 0; y < H; y += 6) ctx.fillRect(0, y, W, 2);
}

// ---------- scene components ----------

// 0.95–1.9 "looks amazing": sparkle glints
function sparkles(t) {
  const pts = [[150, 640, 46, 0], [935, 560, 38, .08], [890, 960, 30, .16], [190, 1010, 34, .12], [800, 330, 26, .2]];
  for (const [x, y, s, d] of pts) {
    const u = p(t, .95 + d, 1.75 + d);
    if (u <= 0 || u >= 1) continue;
    const k = Math.sin(u * Math.PI);
    ctx.save(); ctx.translate(x, y); ctx.rotate(u * 1.2); ctx.scale(k, k);
    ctx.shadowColor = COL.pink; ctx.shadowBlur = 24;
    ctx.fillStyle = COL.cream;
    ctx.beginPath();
    for (let i = 0; i < 8; i++) {
      const a = i * Math.PI / 4, r = i % 2 ? s * .18 : s;
      ctx.lineTo(Math.cos(a) * r, Math.sin(a) * r);
    }
    ctx.closePath(); ctx.fill();
    ctx.restore();
  }
}

// 0–1.9 hook: a viewer-facing question, complete on frame 0 so it also works as the thumbnail
function hook(t) {
  if (t > 1.92) return;
  const out = eInC(p(t, 1.6, 1.88));
  const settle = 1 + 0.07 * (1 - eOutC(p(t, 0, .5)));
  const cy = 1100;
  ctx.save();
  ctx.globalAlpha = 1 - out;
  ctx.translate(W / 2, cy + out * 70);
  ctx.scale(settle * (1 - .12 * out), settle * (1 - .12 * out));
  ctx.rotate(-0.035 + 0.006 * Math.sin(t * 7));
  // line 1: dark block
  const l1 = 'WHY ISN\u2019T YOUR';
  ctx.font = font(800, 50); ctx.letterSpacing = '3px';
  const w1 = ctx.measureText(l1).width + 60, h1 = 86;
  ctx.save(); ctx.shadowColor = 'rgba(0,0,0,0.45)'; ctx.shadowBlur = 30; ctx.shadowOffsetY = 12;
  rr(ctx, -w1 / 2, -h1 - 8, w1, h1, 16); ctx.fillStyle = 'rgba(14,15,21,0.92)'; ctx.fill(); ctx.restore();
  ctx.fillStyle = COL.cream; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText(l1, 1.5, -h1 / 2 - 6);
  ctx.letterSpacing = '0px';
  // line 2: brand-gradient block
  const l2 = 'PHONE RINGING?';
  let fs = 92;
  ctx.font = font(900, fs, 'Montserrat', 'italic');
  const mw = ctx.measureText(l2).width;
  if (mw > 900) { fs = Math.floor(fs * 900 / mw); ctx.font = font(900, fs, 'Montserrat', 'italic'); }
  const w2 = ctx.measureText(l2).width + 70, h2 = fs * 1.42;
  ctx.save(); ctx.shadowColor = 'rgba(255,79,139,0.55)'; ctx.shadowBlur = 36; ctx.shadowOffsetY = 10;
  rr(ctx, -w2 / 2, 0, w2, h2, 20); ctx.fillStyle = grad(ctx, -w2 / 2, 0, w2 / 2, h2); ctx.fill(); ctx.restore();
  ctx.fillStyle = 'rgba(80,10,40,0.35)'; ctx.fillText(l2, 3, h2 / 2 + 6);
  ctx.fillStyle = '#fff'; ctx.fillText(l2, 0, h2 / 2 + 2);
  ctx.restore();
}

// 1.9–3.9 "my phone never rings": calls-today card
function phoneCard(t) {
  const a = 1.9, b = 3.7;
  const v = vis(t, a, b, .35, .22); if (v <= 0) return;
  const kin = eOutBack(p(t, a, a + .35), 1.6);
  const cw = 640, ch = 230, x = (W - cw) / 2, y = 1010;
  ctx.save();
  ctx.globalAlpha = v;
  ctx.translate(W / 2, y + ch / 2); ctx.scale(lerp(.9, 1, kin), lerp(.9, 1, kin));
  ctx.translate(0, (1 - kin) * 50 - (t > b ? eInC(p(t, b, b + .22)) * 40 : 0));
  ctx.translate(-W / 2, -(y + ch / 2));
  glass(ctx, x, y, cw, ch, 40);
  // icon bubble
  const ix = x + 125, iy = y + ch / 2;
  ctx.fillStyle = 'rgba(255,64,87,0.16)'; ctx.beginPath(); ctx.arc(ix, iy, 72, 0, 7); ctx.fill();
  ctx.strokeStyle = 'rgba(255,64,87,0.55)'; ctx.lineWidth = 3; ctx.stroke();
  icon(ctx, 'phone', ix, iy, 64, COL.cream, 2);
  const ks = eOutC(p(t, 2.5, 2.8));
  if (ks > 0) {
    ctx.save(); ctx.strokeStyle = COL.red; ctx.lineWidth = 8; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(ix - 46, iy - 46); ctx.lineTo(ix - 46 + 92 * ks, iy - 46 + 92 * ks); ctx.stroke(); ctx.restore();
  }
  ctx.fillStyle = 'rgba(246,238,223,0.72)'; ctx.font = font(700, 30); ctx.letterSpacing = '4px';
  ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'left';
  ctx.fillText('CALLS TODAY', x + 245, y + 82);
  ctx.letterSpacing = '0px';
  const k0 = p(t, 2.42, 2.62);
  ctx.save();
  ctx.translate(x + 245, y + 192);
  const s0 = k0 < 1 ? lerp(1.6, 1, eOutC(k0)) : 1;
  ctx.globalAlpha *= clamp(k0 * 2);
  ctx.scale(s0, s0);
  ctx.fillStyle = COL.red; ctx.font = font(900, 120); ctx.fillText('0', 0, 0);
  ctx.restore();
  ctx.fillStyle = 'rgba(246,238,223,0.55)'; ctx.font = font(600, 28);
  ctx.globalAlpha = v * clamp(k0 * 2);
  ctx.fillText('No new calls', x + 345, y + 178);
  ctx.restore();
}

// 4.0–6.0 "nobody even knows we exist": empty search result
function searchCard(t) {
  const a = 3.98, b = 5.75;
  const v = vis(t, a, b, .3, .25); if (v <= 0) return;
  const kin = eOutBack(p(t, a, a + .3), 1.6);
  const cw = 760, ch = 250, x = (W - cw) / 2, y = 1000;
  ctx.save();
  ctx.globalAlpha = v;
  ctx.translate(0, (1 - kin) * 60);
  glass(ctx, x, y, cw, ch, 40);
  // search bar
  const bx = x + 30, by = y + 30, bw = cw - 60, bh = 92;
  rr(ctx, bx, by, bw, bh, 46); ctx.fillStyle = 'rgba(255,255,255,0.94)'; ctx.fill();
  icon(ctx, 'search', bx + 56, by + bh / 2, 40, '#5b5f6e', 2.4);
  const q = 'your store';
  const n = Math.floor(clamp((t - 4.1) / .06, 0, q.length));
  ctx.fillStyle = '#16171f'; ctx.font = font(600, 38, 'Inter'); ctx.textBaseline = 'middle'; ctx.textAlign = 'left';
  ctx.fillText(q.slice(0, n), bx + 100, by + bh / 2 + 2);
  if (Math.floor(t * 3) % 2 === 0 || n < q.length) {
    const cx = bx + 100 + ctx.measureText(q.slice(0, n)).width + 4;
    ctx.fillStyle = COL.pink; ctx.fillRect(cx, by + 26, 4, bh - 52);
  }
  // result
  const kr = p(t, 4.85, 5.1);
  if (kr > 0) {
    ctx.save();
    ctx.globalAlpha *= kr;
    ctx.translate(0, (1 - eOutC(kr)) * 20);
    const ry = by + bh + 70;
    icon(ctx, 'x', x + 72, ry, 40, COL.red, 3);
    ctx.fillStyle = COL.cream; ctx.font = font(800, 40); ctx.textBaseline = 'middle';
    ctx.fillText('0 results found', x + 118, ry + 2);
    ctx.restore();
  }
  ctx.restore();
}

// Stat tile used for "no traffic / leads / sales" and later "more leads / orders / results".
function statTile(x, y, w, h, label, mode, k, t, seed) {
  glass(ctx, x, y, w, h, 34);
  ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'left';
  ctx.fillStyle = 'rgba(246,238,223,0.75)'; ctx.font = font(800, 25); ctx.letterSpacing = '3px';
  ctx.fillText(label, x + 26, y + 52);
  ctx.letterSpacing = '0px';
  const good = mode === 'up';
  const bc = good ? COL.green : COL.red;
  // badge
  ctx.fillStyle = good ? 'rgba(53,214,154,0.18)' : 'rgba(255,64,87,0.18)';
  ctx.beginPath(); ctx.arc(x + w - 46, y + 44, 26, 0, 7); ctx.fill();
  icon(ctx, good ? 'up' : 'down', x + w - 46, y + 44, 30, bc, 3);
  const gx = x + 24, gw = w - 48, gy = y + h - 34;
  if (!good) {
    ctx.fillStyle = COL.cream; ctx.font = font(900, 104);
    ctx.fillText('0', x + 26, y + 160);
    // dying flat line
    const kl = eOutC(clamp(k));
    ctx.save(); ctx.strokeStyle = COL.red; ctx.lineWidth = 5; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    ctx.beginPath();
    for (let i = 0; i <= 24 * kl; i++) {
      const xx = gx + gw * i / 24;
      const yy = gy - 26 + Math.min(24, i * 2.4) + (rnd(seed + i) - .5) * 6;
      i ? ctx.lineTo(xx, yy) : ctx.moveTo(xx, yy);
    }
    ctx.stroke(); ctx.restore();
  } else {
    // rising bars
    const n = 5, bw = (gw - (n - 1) * 12) / n, maxH = h - 110;
    for (let i = 0; i < n; i++) {
      const kb = eOutBack(p(k, i * .12, i * .12 + .45), 1.3);
      const bh = maxH * (0.25 + 0.75 * (i + 1) / n) * kb;
      if (bh <= 0) continue;
      rr(ctx, gx + i * (bw + 12), gy - bh + 10, bw, bh, 8);
      ctx.fillStyle = grad(ctx, 0, gy - maxH, 0, gy, COL.pink, COL.coral); ctx.fill();
    }
    const kl = eOutC(p(k, .3, 1));
    if (kl > 0) {
      ctx.save(); ctx.strokeStyle = COL.cream; ctx.lineWidth = 5; ctx.lineCap = 'round'; ctx.shadowColor = COL.pink; ctx.shadowBlur = 14;
      ctx.beginPath();
      for (let i = 0; i <= 20 * kl; i++) {
        const xx = gx + gw * i / 20, yy = gy - 10 - (maxH * .9) * Math.pow(i / 20, 1.6);
        i ? ctx.lineTo(xx, yy) : ctx.moveTo(xx, yy);
      }
      ctx.stroke(); ctx.restore();
    }
  }
}

function tilesRow(t, items, exitAt, mode) {
  const w = 300, h = 236, gap = 30, x0 = (W - (3 * w + 2 * gap)) / 2, y = 128;
  items.forEach(([label, tin], i) => {
    const v = vis(t, tin, exitAt + i * .05, .3, .25); if (v <= 0) return;
    const kin = p(t, tin, tin + .38);
    const x = x0 + i * (w + gap);
    ctx.save();
    ctx.globalAlpha = v;
    const out = eInC(p(t, exitAt + i * .05, exitAt + i * .05 + .25));
    ctx.translate(x + w / 2, y + h / 2 + (1 - eOutBack(kin, 1.8)) * -90 - out * 80);
    ctx.rotate((1 - eOutC(kin)) * -0.12);
    ctx.translate(-(x + w / 2), -(y + h / 2));
    statTile(x, y, w, h, label, mode, p(t, tin + .1, tin + .9), t, i * 31);
    ctx.restore();
  });
}

// 11.35–14.2 "I tried everything ... nothing worked"
function triedPills(t) {
  if (t < 11.3 || t > 14.4) return;
  const items = [['Flyers', 11.45, 12.55], ['Discounts', 11.75, 12.8], ['Posting daily', 12.05, 13.05]];
  ctx.font = font(800, 34);
  const ws = items.map(([s]) => ctx.measureText(s).width + 64 + 50);
  const gap = 18, total = ws.reduce((a, b) => a + b, 0) + gap * 2;
  let x = (W - total) / 2;
  const y = 160, h = 86;
  items.forEach(([s, tin, tx], i) => {
    const w = ws[i];
    const kin = p(t, tin, tin + .3);
    const fall = p(t, 13.62 + i * .06, 14.15 + i * .06);
    if (kin <= 0 || fall >= 1) { x += w + gap; return; }
    ctx.save();
    ctx.globalAlpha = clamp(kin * 2) * (1 - fall);
    ctx.translate(x + w / 2, y + h / 2 + eInC(fall) * 260);
    ctx.rotate(eInC(fall) * (i - 1) * 0.5);
    const s0 = lerp(.6, 1, eOutBack(kin, 2));
    ctx.scale(s0, s0);
    ctx.translate(-(x + w / 2), -(y + h / 2));
    glass(ctx, x, y, w, h, h / 2);
    ctx.fillStyle = COL.cream; ctx.textBaseline = 'middle'; ctx.textAlign = 'left'; ctx.font = font(800, 34);
    ctx.fillText(s, x + 30, y + h / 2 + 2);
    // X stamp
    const ks = p(t, tx, tx + .16);
    if (ks > 0) {
      const tw = ctx.measureText(s).width;
      ctx.strokeStyle = COL.red; ctx.lineWidth = 6; ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(x + 24, y + h / 2 + 2); ctx.lineTo(x + 24 + (tw + 12) * eOutC(ks), y + h / 2 + 2); ctx.stroke();
      const sx = x + w - 42, sy = y + h / 2;
      ctx.save(); ctx.translate(sx, sy); const sc = lerp(1.8, 1, eOutC(ks)); ctx.scale(sc, sc);
      ctx.fillStyle = COL.red; ctx.beginPath(); ctx.arc(0, 0, 22, 0, 7); ctx.fill();
      icon(ctx, 'x', 0, 0, 26, '#fff', 3.4);
      ctx.restore();
    }
    ctx.restore();
    x += w + gap;
  });
}

// 15.55–19.3 transformation: "growth mode" loader fills the wordless stretch
function growthLoader(t) {
  const a = 15.55, b = 19.05;
  const v = vis(t, a, b, .35, .25); if (v <= 0) return;
  const kin = eOutBack(p(t, a, a + .4), 1.5);
  const cw = 780, ch = 176, x = (W - cw) / 2, y = 150;
  const pr = eIOC(p(t, 15.8, 18.85));
  const done = t >= 18.85;
  ctx.save();
  ctx.globalAlpha = v;
  const sc = lerp(.88, 1, kin) * (t > b ? 1 + .08 * p(t, b, b + .25) : 1) * (done ? 1 + .04 * Math.exp(-(t - 18.85) * 8) : 1);
  ctx.translate(W / 2, y + ch / 2); ctx.scale(sc, sc); ctx.translate(-W / 2, -(y + ch / 2));
  glass(ctx, x, y, cw, ch, 36, { border: done ? 'rgba(255,79,139,0.8)' : 'rgba(255,255,255,0.18)', borderW: done ? 3 : 1.5 });
  ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'left';
  ctx.font = font(800, 34); ctx.letterSpacing = '5px'; ctx.fillStyle = COL.cream;
  ctx.fillText(done ? 'GROWTH MODE: ON' : 'GROWTH MODE', x + 40, y + 72);
  ctx.letterSpacing = '0px';
  ctx.textAlign = 'right';
  if (done) {
    ctx.fillStyle = COL.pink; ctx.beginPath(); ctx.arc(x + cw - 64, y + 60, 28, 0, 7); ctx.fill();
    icon(ctx, 'check', x + cw - 64, y + 60, 32, '#fff', 3.4);
  } else {
    ctx.font = font(400, 64, 'Bebas'); ctx.fillStyle = COL.cream;
    ctx.fillText(Math.round(pr * 100) + '%', x + cw - 40, y + 82);
  }
  const bx = x + 40, by = y + 112, bw = cw - 80, bh = 22;
  rr(ctx, bx, by, bw, bh, 11); ctx.fillStyle = 'rgba(255,255,255,0.12)'; ctx.fill();
  if (pr > 0) {
    ctx.save(); ctx.shadowColor = COL.pink; ctx.shadowBlur = 22;
    rr(ctx, bx, by, Math.max(bh, bw * pr), bh, 11); ctx.fillStyle = grad(ctx, bx, 0, bx + bw, 0); ctx.fill();
    ctx.restore();
  }
  ctx.restore();
}

// ---------- captions: phrase cards with a moving active-word highlight ----------
// Phrases are split from the spoken words; *word* marks an emphasis word (brand colour).
const PHRASES = [
  'My store looks *amazing*', 'But my phone *never* *rings*', '*Nobody* even knows we *exist*',
  'No *traffic.*', 'No *leads.*', 'No *sales.*', 'I tried *everything*', 'And *nothing* *worked.*',
  'Then I partnered with', '*Haadin* *Global*', 'And everything *changed.*',
  '*Meta* and *Google* *Ads*', 'and *SEO*,', 'a *website* that *sells.*',
  'Now customers find me', 'from *Dubai* to *London.*', 'Now my phone *never* *stops.*',
  'More *leads.*', 'More *orders.*', 'Real *results.*', 'Every *single* *month.*',
  'Want the same for your *business?*',
];
const CAP = { y: 1488, size: 60, lineH: 78, maxW: 880, padX: 38, padY: 24, end: 44.18 };
let CAPS = [];
const norm = w => w.toLowerCase().replace(/[^a-z0-9]/g, '');

function buildCaptions(words, fill) {
  // Match phrase tokens to the timed words in order. A token that isn't spoken within the
  // next few words is dropped, so captions always show exactly what is said.
  let wi = 0;
  CAPS = PHRASES.map(ph => {
    const toks = [];
    for (const tok of ph.split(' ')) {
      const emph = tok.startsWith('*');
      const text = tok.replace(/\*/g, '');
      let j = wi;
      while (j < Math.min(words.length, wi + 4) && norm(words[j].w) !== norm(text)) j++;
      if (j >= words.length || norm(words[j].w) !== norm(text)) { console.error('caption token not spoken:', text); continue; }
      wi = j + 1;
      toks.push({ text, emph, s: words[j].s, e: words[j].e });
    }
    return { toks, s: toks[0].s - 0.08, e: toks[toks.length - 1].e + 0.3 };
  }).filter(c => c.toks.length);
  for (let i = 0; i < CAPS.length - 1; i++) CAPS[i].e = Math.min(CAPS[i].e, CAPS[i + 1].s - 0.02);
  CAPS[CAPS.length - 1].e = Math.min(CAPS[CAPS.length - 1].e, CAP.end);
  coverFill(fill || {});
}

// The burned-in captions were removed by filling from neighbouring frames; where no nearby
// frame showed the background, the fill is spatial (soft). Every such frame must sit under a
// caption card, so phrases are stretched in time and cards grown to cover those areas
// (in screen space, i.e. after the camera zoom of drawVideo).
function coverFill(fill) {
  for (const c of CAPS) c.req = null;
  for (const [nStr, fi] of Object.entries(fill)) {
    if (!fi.rest) continue;
    const n = +nStr, t = (n - 1) / FPS;
    if (t >= CAP.end) continue;
    // the most recently started phrase that is on screen owns the frame
    let c = [...CAPS].reverse().find(c => t >= c.s && t < c.e + 0.12);
    if (!c) {
      const prev = [...CAPS].reverse().find(c => c.e <= t), next = CAPS.find(c => c.s > t);
      if (prev && t - prev.e < 0.7 && (!next || t - prev.e <= next.s - t)) { prev.e = t + 0.04; c = prev; }
      else if (next && next.s - t < 0.7) { next.s = t - 0.04; c = next; }
      else { console.error('uncovered fill at frame', n); continue; }
    }
    // keep the card fully opaque (past its fade-in, before its fade-out) on this frame
    const ci = CAPS.indexOf(c);
    c.s = Math.min(c.s, Math.max(ci > 0 ? CAPS[ci - 1].e + 0.17 : 0, t - 0.13));
    const nx = CAPS[ci + 1];
    c.e = Math.max(c.e, Math.min(t + 0.03, nx ? nx.s - 0.02 : Infinity));
    const z = zoomAt(t), cy = H * 0.42;
    const [x0, x1, y0, y1] = fi.rest;
    const X0 = W / 2 + (x0 - W / 2) * z, X1 = W / 2 + (x1 - W / 2) * z;
    const Y0 = cy + (y0 - cy) * z, Y1 = cy + (y1 - cy) * z;
    const r = c.req || (c.req = { hw: 0, top: Infinity, bot: -Infinity });
    r.hw = Math.max(r.hw, W / 2 - X0, X1 - W / 2);
    // 6 frames have a sliver of fill near the holograms above the band; it is invisible, so ignore it
    r.top = Math.min(r.top, Math.max(Y0, 1330)); r.bot = Math.max(r.bot, Y1);
  }
}

function layoutPhrase(ph) {
  ctx.font = font(800, CAP.size); ctx.letterSpacing = '0px';
  const space = ctx.measureText(' ').width;
  for (const tk of ph.toks) tk.w = ctx.measureText(tk.text).width;
  const span = (a, b) => ph.toks.slice(a, b).reduce((acc, tk, i) => acc + tk.w + (i ? space : 0), 0);
  let lines = [ph.toks];
  if (span(0, ph.toks.length) > CAP.maxW && ph.toks.length > 1) {
    // two lines, split where the longer line is shortest
    let best = 1, bestW = Infinity;
    for (let k = 1; k < ph.toks.length; k++) {
      const m = Math.max(span(0, k), span(k, ph.toks.length));
      if (m < bestW) { bestW = m; best = k; }
    }
    lines = [ph.toks.slice(0, best), ph.toks.slice(best)];
  }
  const widths = lines.map(l => l.reduce((a, tk, i) => a + tk.w + (i ? space : 0), 0));
  const W0 = Math.max(...widths);
  let cw = W0 + CAP.padX * 2, ch = lines.length * CAP.lineH + CAP.padY * 2;
  let top = CAP.y - ch / 2;
  if (ph.req) {
    const m = 18;
    cw = Math.max(cw, 2 * (ph.req.hw + m));
    const t2 = Math.min(top, ph.req.top - m), b2 = Math.max(top + ch, ph.req.bot + m);
    top = t2; ch = b2 - t2;
  }
  const textTop = top + (ch - lines.length * CAP.lineH) / 2;
  lines.forEach((l, li) => {
    let x = W / 2 - widths[li] / 2;
    const y = textTop + CAP.lineH * (li + 0.5);
    for (const tk of l) { tk.x = x; tk.y = y; x += tk.w + space; }
  });
  return { cw, ch, top };
}

function captions(t) {
  if (!CAPS.length || t >= CAP.end + 0.2) return;
  const ph = [...CAPS].reverse().find(c => t >= c.s && t < c.e + 0.16);
  if (!ph) return;
  const { cw, ch, top } = layoutPhrase(ph);
  const kin = p(t, ph.s, ph.s + 0.2), kout = p(t, ph.e, ph.e + 0.16);
  const a = clamp(kin * 1.6) * (1 - kout);
  if (a <= 0) return;
  const sc = lerp(0.94, 1, eOutBack(kin, 1.6)) * lerp(1, 0.97, kout);
  ctx.save();
  ctx.globalAlpha = a;
  const ccy = top + ch / 2;
  ctx.translate(W / 2, ccy + (1 - eOutC(kin)) * 14); ctx.scale(sc, sc); ctx.translate(-W / 2, -ccy);
  glass(ctx, W / 2 - cw / 2, top, cw, ch, 30, { tint: 'rgba(10,10,16,0.56)', border: 'rgba(255,255,255,0.14)' });
  // active word = last word whose start has passed (held until the next word starts)
  let ai = -1;
  ph.toks.forEach((tk, i) => { if (t >= tk.s) ai = i; });
  if (ai >= 0 && t > ph.toks[ai].e + 0.35 && ai === ph.toks.length - 1) ai = -1;
  if (ai >= 0) {
    const cur = ph.toks[ai], prev = ph.toks[Math.max(0, ai - 1)];
    const m = ai > 0 ? eOutC(p(t, cur.s, cur.s + 0.11)) : 1;
    const px = lerp(prev.x, cur.x, m) - 14, pw = lerp(prev.w, cur.w, m) + 28;
    const py = lerp(prev.y, cur.y, m) - CAP.size * 0.62, phh = CAP.size * 1.24;
    ctx.save(); ctx.shadowColor = 'rgba(255,79,139,0.55)'; ctx.shadowBlur = 22;
    rr(ctx, px, py, pw, phh, 14); ctx.fillStyle = grad(ctx, px, py, px + pw, py + phh); ctx.fill();
    ctx.restore();
  }
  ctx.font = font(800, CAP.size); ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  ph.toks.forEach((tk, i) => {
    const spoken = t >= tk.s;
    let col = tk.emph ? '#FF7AA6' : '#FFFFFF';
    if (i === ai) col = '#FFFFFF';
    ctx.save();
    ctx.globalAlpha *= spoken ? 1 : 0.5;
    if (i !== ai) { ctx.shadowColor = 'rgba(0,0,0,0.45)'; ctx.shadowBlur = 10; ctx.shadowOffsetY = 3; }
    ctx.fillStyle = col;
    if (i === ai) {
      const k = p(t, tk.s, tk.s + 0.12), s2 = 1 + 0.05 * Math.sin(Math.PI * k);
      ctx.translate(tk.x + tk.w / 2, tk.y); ctx.scale(s2, s2); ctx.fillText(tk.text, -tk.w / 2, 2);
    } else ctx.fillText(tk.text, tk.x, tk.y + 2);
    ctx.restore();
  });
  ctx.restore();
}

// 21.0–24.3 brand reveal, then docks into a corner bug
const BUG = { x: 196, y: 82, s: 0.36 };
function brandReveal(t) {
  if (t < 21.0 || t > 24.35) return;
  const k = p(t, 21.02, 22.0);
  const dock = eIOC(p(t, 23.9, 24.3));
  const cx = lerp(W / 2, BUG.x, dock), cy = lerp(262, BUG.y, dock), s = lerp(1, BUG.s, dock);
  clearLayer();
  lctx.save();
  lctx.translate(cx, cy); lctx.scale(s, s);
  // soft dark halo behind the lockup for legibility
  const hg = lctx.createRadialGradient(0, 0, 40, 0, 0, 420);
  hg.addColorStop(0, `rgba(10,10,16,${0.5 * (1 - dock)})`); hg.addColorStop(1, 'rgba(10,10,16,0)');
  lctx.fillStyle = hg; lctx.fillRect(-460, -260, 920, 520);
  lockup(lctx, k, -1, 104);
  lctx.restore();
  sweepOver(lctx, 0, 0, W, 520, p(t, 21.6, 22.3));
  ctx.drawImage(layer, 0, 0);
  // glow burst on reveal
  const g = p(t, 21.02, 21.5);
  if (g > 0 && g < 1) {
    ctx.save(); ctx.globalCompositeOperation = 'screen';
    const rg = ctx.createRadialGradient(W / 2, 262, 0, W / 2, 262, 520 * eOutC(g) + 1);
    rg.addColorStop(0, `rgba(255,79,139,${0.45 * (1 - g)})`); rg.addColorStop(1, 'rgba(255,79,139,0)');
    ctx.fillStyle = rg; ctx.fillRect(0, 0, W, 800); ctx.restore();
  }
}

function brandBug(t) {
  if (t < 24.3 || t > 44.45) return;
  const v = 1 - p(t, 44.15, 44.4);
  ctx.save(); ctx.globalAlpha = v;
  const w = 392, h = 92;
  glass(ctx, BUG.x - w / 2 + 6, BUG.y - h / 2 + 2, w, h, 46, { tint: 'rgba(14,15,21,0.5)' });
  ctx.translate(BUG.x, BUG.y); ctx.scale(BUG.s, BUG.s);
  lockup(ctx, 1, -1, 104);
  ctx.restore();
}

// 24.7–30.8 service chips
function chip(x, y, label, iconName, k, glow) {
  ctx.font = font(800, 37); ctx.letterSpacing = '1px';
  const tw = ctx.measureText(label).width;
  const h = 100, w = tw + 100 + 42;
  const s = lerp(.5, 1, eOutBack(k, 2.2));
  ctx.save();
  ctx.globalAlpha *= clamp(k * 3);
  ctx.translate(x, y + h / 2); ctx.scale(s, s); ctx.translate(-x, -(y + h / 2));
  const x0 = x - w / 2;
  if (glow > 0) { ctx.save(); ctx.shadowColor = COL.pink; ctx.shadowBlur = 40 * glow; rr(ctx, x0, y, w, h, h / 2); ctx.fillStyle = 'rgba(255,79,139,0.35)'; ctx.fill(); ctx.restore(); }
  glass(ctx, x0, y, w, h, h / 2, { border: grad(ctx, x0, 0, x0 + w, 0), borderW: 3 });
  ctx.fillStyle = grad(ctx, x0 + 12, y + 12, x0 + 80, y + 80);
  ctx.beginPath(); ctx.arc(x0 + 13 + 37, y + h / 2, 37, 0, 7); ctx.fill();
  icon(ctx, iconName, x0 + 50, y + h / 2, 40, '#fff', 2.4);
  ctx.fillStyle = COL.cream; ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  ctx.fillText(label, x0 + 104, y + h / 2 + 2);
  ctx.letterSpacing = '0px';
  ctx.restore();
  return w;
}
function serviceChips(t) {
  if (t < 24.6 || t > 31.0) return;
  const rows = [
    [['META ADS', 'megaphone', 24.85], ['GOOGLE ADS', 'target', 25.73]],
    [['SEO', 'search', 27.54], ['WEBSITES THAT SELL', 'browser', 28.87]],
  ];
  ctx.font = font(800, 37); ctx.letterSpacing = '1px';
  rows.forEach((row, ri) => {
    const ws = row.map(([l]) => ctx.measureText(l).width + 142);
    const gap = 22, total = ws[0] + ws[1] + gap;
    let x = (W - total) / 2;
    row.forEach(([l, ic, tin], i) => {
      const out = p(t, 30.45 + (ri * 2 + i) * .05, 30.75 + (ri * 2 + i) * .05);
      const k = p(t, tin, tin + .32);
      if (k > 0 && out < 1) {
        ctx.save();
        ctx.globalAlpha = 1 - out;
        ctx.translate(0, -eInC(out) * 120);
        chip(x + ws[i] / 2, 140 + ri * 120, l, ic, k, Math.exp(-(t - tin) * 3) * (t >= tin ? 1 : 0));
        ctx.restore();
      }
      x += ws[i] + gap;
    });
  });
  ctx.letterSpacing = '0px';
}

// 31.3–34.25 Dubai → London route
function route(t) {
  const v = vis(t, 31.3, 33.95, .3, .3); if (v <= 0) return;
  const A = [190, 318], B = [890, 318], C = [540, 120];
  const q = (u) => [(1 - u) * (1 - u) * A[0] + 2 * (1 - u) * u * C[0] + u * u * B[0], (1 - u) * (1 - u) * A[1] + 2 * (1 - u) * u * C[1] + u * u * B[1]];
  const kp = eIOC(p(t, 32.05, 32.92));
  ctx.save(); ctx.globalAlpha = v;
  // dashed full path
  ctx.setLineDash([4, 16]); ctx.lineCap = 'round'; ctx.lineWidth = 5; ctx.strokeStyle = 'rgba(246,238,223,0.55)';
  const kd = eOutC(p(t, 31.35, 31.9));
  ctx.beginPath(); for (let i = 0; i <= 60 * kd; i++) { const [x, y] = q(i / 60); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); } ctx.stroke();
  ctx.setLineDash([]);
  // travelled path
  if (kp > 0) {
    ctx.save(); ctx.shadowColor = COL.pink; ctx.shadowBlur = 18; ctx.lineWidth = 7; ctx.strokeStyle = grad(ctx, A[0], 0, B[0], 0);
    ctx.beginPath(); for (let i = 0; i <= 80 * kp; i++) { const [x, y] = q(i / 80); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); } ctx.stroke(); ctx.restore();
  }
  // pins + labels
  const pin = ([x, y], label, tin) => {
    const k = p(t, tin, tin + .3); if (k <= 0) return;
    ctx.save(); ctx.globalAlpha *= clamp(k * 2);
    const s = lerp(.4, 1, eOutBack(k, 2.4));
    ctx.translate(x, y); ctx.scale(s, s);
    const rp = p(t, tin, tin + .9);
    if (rp < 1) { ctx.strokeStyle = `rgba(255,79,139,${1 - rp})`; ctx.lineWidth = 4; ctx.beginPath(); ctx.arc(0, 0, 18 + 70 * eOutC(rp), 0, 7); ctx.stroke(); }
    ctx.fillStyle = COL.pink; ctx.beginPath(); ctx.arc(0, 0, 16, 0, 7); ctx.fill();
    ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(0, 0, 6, 0, 7); ctx.fill();
    ctx.font = font(800, 32); ctx.letterSpacing = '5px';
    const tw = ctx.measureText(label).width + 44;
    glass(ctx, -tw / 2, 34, tw, 60, 30);
    ctx.fillStyle = COL.cream; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(label, 2.5, 66);
    ctx.letterSpacing = '0px';
    ctx.restore();
  };
  pin(A, 'DUBAI', 31.38);
  pin(B, 'LONDON', 32.86);
  // plane
  if (t >= 31.9 && t < 33.1) {
    const u = Math.max(0.001, kp);
    const [x, y] = q(u), [x2, y2] = q(Math.min(1, u + .01));
    const ang = Math.atan2(y2 - y, x2 - x) + Math.PI / 2;
    const fade = 1 - p(t, 32.9, 33.1);
    ctx.save(); ctx.globalAlpha *= fade * clamp((t - 31.9) * 6);
    ctx.translate(x, y); ctx.rotate(ang); ctx.scale(2.6, 2.6); ctx.translate(-12, -12);
    ctx.shadowColor = 'rgba(0,0,0,0.5)'; ctx.shadowBlur = 8; ctx.fillStyle = '#fff'; ctx.fill(PLANE);
    ctx.restore();
  }
  ctx.restore();
}

// 34.6–36.8 "my phone never stops": notification stack
const NOTES = [
  [34.68, 'mail', ['#FF4F8B', '#FF8A66'], 'New lead', 'Asked for a quote'],
  [35.03, 'cart', ['#35D69A', '#1FB57E'], 'New order', 'Paid online'],
  [35.38, 'phone', ['#3EA6FF', '#2B7BFF'], 'Incoming call', 'New customer'],
  [35.73, 'chat', ['#9B6BFF', '#6C4BFF'], 'New message', 'Are you open today?'],
  [36.08, 'mail', ['#FF4F8B', '#FF8A66'], 'New lead', 'Booked a visit'],
];
function banner(x, y, w, h, n, tAge) {
  const [, ic, cols, title, body] = n;
  glass(ctx, x, y, w, h, 34, { tint: 'rgba(250,247,242,0.86)', border: 'rgba(255,255,255,0.6)', sheen: false });
  const ix = x + 24, iy = y + (h - 76) / 2;
  rr(ctx, ix, iy, 76, 76, 20); ctx.fillStyle = grad(ctx, ix, iy, ix + 76, iy + 76, cols[0], cols[1]); ctx.fill();
  icon(ctx, ic, ix + 38, iy + 38, 40, '#fff', 2.3);
  ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
  ctx.fillStyle = '#15161d'; ctx.font = font(700, 32, 'Inter'); ctx.fillText(title, ix + 100, y + 54);
  ctx.fillStyle = '#5e6170'; ctx.font = font(500, 28, 'Inter'); ctx.fillText(body, ix + 100, y + 94);
  ctx.textAlign = 'right'; ctx.fillStyle = '#8a8d99'; ctx.font = font(500, 24, 'Inter'); ctx.fillText('now', x + w - 28, y + 50);
}
function notifications(t) {
  if (t < 34.6 || t > 36.9) return;
  const w = 880, h = 124, x = (W - w) / 2, y0 = 132;
  const exit = eInC(p(t, 36.5, 36.8));
  NOTES.forEach((n, idx) => {
    if (t < n[0]) return;
    // depth = how many newer banners have arrived (animated), newest sits on top
    let d = 0;
    for (let j = idx + 1; j < NOTES.length; j++) d += eOutC(p(t, NOTES[j][0], NOTES[j][0] + .28));
    if (d >= 2) return;
    const kin = p(t, n[0], n[0] + .3);
    const sc = 1 - .07 * d;
    const yy = y0 + 138 * Math.min(d, 1) + 110 * Math.max(0, d - 1) + (1 - eOutBack(kin, 1.4)) * -210 - exit * 300;
    const a = d <= 1 ? 1 - .15 * d : .85 * (2 - d);
    ctx.save();
    ctx.globalAlpha = clamp(kin * 2.5) * a * (1 - exit);
    ctx.translate(W / 2, yy + h / 2); ctx.scale(sc, sc); ctx.translate(-W / 2, -(yy + h / 2));
    banner(x, yy, w, h, n, t - n[0]);
    ctx.restore();
  });
}

// 40.45–42.6 "every single month": 12 months ticking
function months(t) {
  const v = vis(t, 40.42, 42.3, .3, .3); if (v <= 0) return;
  const M = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
  const cw = 960, ch = 232, x = (W - cw) / 2, y = 120;
  const kin = eOutBack(p(t, 40.42, 40.75), 1.5);
  ctx.save(); ctx.globalAlpha = v;
  ctx.translate(W / 2, y + ch / 2); ctx.scale(lerp(.9, 1, kin), lerp(.9, 1, kin)); ctx.translate(-W / 2, -(y + ch / 2));
  glass(ctx, x, y, cw, ch, 36);
  const pad = 22, gap = 12, cellW = (cw - pad * 2 - gap * 5) / 6, cellH = (ch - pad * 2 - gap) / 2;
  M.forEach((m, i) => {
    const r = Math.floor(i / 6), c = i % 6;
    const cx = x + pad + c * (cellW + gap), cy = y + pad + r * (cellH + gap);
    const tk = 40.6 + i * .115;
    const k = p(t, tk, tk + .18);
    rr(ctx, cx, cy, cellW, cellH, 18);
    ctx.fillStyle = k > 0 ? grad(ctx, cx, cy, cx + cellW, cy + cellH) : 'rgba(255,255,255,0.08)';
    ctx.save(); ctx.globalAlpha *= k > 0 ? lerp(.3, 1, eOutC(k)) : 1; ctx.fill(); ctx.restore();
    ctx.fillStyle = COL.cream; ctx.font = font(800, 28); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(m, cx + cellW / 2, cy + cellH / 2 - (k > 0 ? 16 * eOutC(k) : 0));
    if (k > 0) {
      ctx.save(); ctx.translate(cx + cellW / 2, cy + cellH / 2 + 20); const s = lerp(1.8, 1, eOutC(k)); ctx.scale(s, s); ctx.globalAlpha *= k;
      icon(ctx, 'check', 0, 0, 26, '#fff', 3.6); ctx.restore();
    }
  });
  ctx.restore();
}

// 44.22–47.45 CTA panel (also hides the misspelt brand caption underneath) → end card
const PANEL = { x: 60, y: 1318, w: 960, h: 350, r: 46 };
function ctaButton(c, cx, cy, bw, bh, t, words, pulse) {
  c.save();
  c.shadowColor = 'rgba(255,79,139,0.65)'; c.shadowBlur = 30 + 20 * pulse;
  rr(c, cx - bw / 2, cy - bh / 2, bw, bh, bh / 2); c.fillStyle = grad(c, cx - bw / 2, 0, cx + bw / 2, 0); c.fill();
  c.restore();
  // fit text
  const full = words.map(w => w[0]).join(' ');
  let fs = 46;
  c.font = font(900, fs, 'Montserrat', 'italic');
  const mw = c.measureText(full).width;
  if (mw > bw - 90) { fs = Math.floor(fs * (bw - 90) / mw); c.font = font(900, fs, 'Montserrat', 'italic'); }
  let x = cx - c.measureText(full).width / 2;
  c.textAlign = 'left'; c.textBaseline = 'middle';
  for (const [w, tin] of words) {
    const k = p(t, tin, tin + .14);
    const ww = c.measureText(w + ' ').width;
    if (k > 0) {
      c.save(); c.globalAlpha *= k; c.fillStyle = '#fff';
      c.translate(x, cy + 3 + (1 - eOutC(k)) * 22);
      c.fillText(w, 0, 0); c.restore();
    }
    x += ww;
  }
}
function tapRipple(c, x, y, t, t0) {
  const u = p(t, t0 - .25, t0 + .55); if (u <= 0 || u >= 1) return;
  c.save();
  const press = t < t0 ? eOutC(p(t, t0 - .25, t0)) : 1 - eOutC(p(t, t0, t0 + .2));
  c.fillStyle = `rgba(255,255,255,${0.85 * (1 - p(t, t0 + .2, t0 + .55))})`;
  c.beginPath(); c.arc(x, y, 34 - 8 * press, 0, 7); c.fill();
  if (t > t0) { const r = p(t, t0, t0 + .55); c.strokeStyle = `rgba(255,255,255,${1 - r})`; c.lineWidth = 5; c.beginPath(); c.arc(x, y, 34 + 90 * eOutC(r), 0, 7); c.stroke(); }
  c.restore();
}

function ctaPanel(t, lastImg) {
  if (t < 44.2) return;
  const kin = eOutBack(p(t, 44.18, 44.34), 1.3);
  const ex = eIOC(p(t, 47.15, 47.45));
  const x = lerp(PANEL.x, 0, ex), y = lerp(PANEL.y, 0, ex), w = lerp(PANEL.w, W, ex), h = lerp(PANEL.h, H, ex), r = lerp(PANEL.r, 0, ex);
  ctx.save();
  if (ex === 0) { const s = lerp(.86, 1, kin); ctx.translate(W / 2, y + h / 2); ctx.scale(s, s); ctx.translate(-W / 2, -(y + h / 2)); }
  ctx.globalAlpha = clamp(p(t, 44.18, 44.24));
  // opaque so the burned-in caption never shows through
  ctx.save(); ctx.shadowColor = 'rgba(0,0,0,0.5)'; ctx.shadowBlur = 50; ctx.shadowOffsetY = 18;
  rr(ctx, x, y, w, h, r); ctx.fillStyle = COL.ink; ctx.fill(); ctx.restore();
  ctx.save(); rr(ctx, x, y, w, h, r); ctx.clip();
  endBackground(ctx, t, x, y, w, h);
  ctx.restore();
  ctx.save(); rr(ctx, x + 1.5, y + 1.5, w - 3, h - 3, r); ctx.lineWidth = 3; ctx.strokeStyle = grad(ctx, x, y, x + w, y + h); ctx.globalAlpha *= 1 - ex; ctx.stroke(); ctx.restore();

  // panel content (fades as the panel opens into the end card)
  const cf = 1 - p(t, 47.2, 47.3);
  if (cf > 0) {
    ctx.save(); ctx.globalAlpha *= cf;
    const toB = eIOC(p(t, 46.3, 46.6));
    // "TALK TO"
    const kt = p(t, 44.3, 44.5) * (1 - toB);
    if (kt > 0) {
      ctx.save(); ctx.globalAlpha *= kt; ctx.fillStyle = COL.pink; ctx.font = font(800, 34); ctx.letterSpacing = '10px';
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText('TALK TO', W / 2 + 5, PANEL.y + 72 - (1 - eOutC(kt)) * -16); ctx.letterSpacing = '0px'; ctx.restore();
    }
    // lockup: big centred, then shrinks to the top of the panel
    const ly = lerp(PANEL.y + 205, PANEL.y + 82, toB), ls = lerp(1.0, .52, toB);
    ctx.save(); ctx.translate(W / 2, ly); ctx.scale(ls, ls);
    clearLayer(); lctx.setTransform(ctx.getTransform());
    lockup(lctx, p(t, 44.92, 45.75), -1, 112);
    lctx.setTransform(1, 0, 0, 1, 0, 0);
    sweepOver(lctx, 0, PANEL.y, W, PANEL.h, p(t, 45.55, 46.1));
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.drawImage(layer, 0, 0);
    ctx.restore();
    // button
    if (toB > 0) {
      const bk = eOutBack(p(t, 46.32, 46.6), 1.6);
      ctx.save(); ctx.globalAlpha *= clamp(bk * 2);
      const by = PANEL.y + 238;
      ctx.translate(W / 2, by); ctx.scale(lerp(.7, 1, bk), lerp(.7, 1, bk)); ctx.translate(-W / 2, -by);
      const press = 1 - .05 * Math.sin(Math.PI * p(t, 46.95, 47.15));
      ctx.translate(W / 2, by); ctx.scale(press, press); ctx.translate(-W / 2, -by);
      ctaButton(ctx, W / 2, by, 880, 132, t, [['BOOK', 46.45], ['YOUR', 46.64], ['FREE', 46.95], ['CONSULTATION', 47.05]], 0);
      ctx.restore();
      tapRipple(ctx, W / 2 + 330, PANEL.y + 262, t, 47.0);
    }
    ctx.restore();
  }
  ctx.restore();
  if (t >= 47.25) endCard(t);
}

function endBackground(c, t, x, y, w, h) {
  const g = c.createLinearGradient(0, y, 0, y + h);
  g.addColorStop(0, '#12131c'); g.addColorStop(1, '#0a0a10');
  c.fillStyle = g; c.fillRect(x, y, w, h);
  // drifting brand-colour glows
  const blobs = [[0.25, 0.3, COL.pink, 0.30, 0.0], [0.8, 0.62, COL.coral, 0.22, 2.1], [0.4, 0.9, COL.rasp, 0.30, 4.0]];
  for (const [bx, by, col, a, ph] of blobs) {
    const cx = bx * W + Math.sin(t * .6 + ph) * 80, cy = by * H + Math.cos(t * .5 + ph) * 90;
    const rg = c.createRadialGradient(cx, cy, 0, cx, cy, 620);
    rg.addColorStop(0, hexA(col, a)); rg.addColorStop(1, hexA(col, 0));
    c.fillStyle = rg; c.fillRect(x, y, w, h);
  }
  // fine dot grid
  c.fillStyle = 'rgba(255,255,255,0.05)';
  for (let gy = 40; gy < H; gy += 60) for (let gx = 30; gx < W; gx += 60) if (gy > y && gy < y + h && gx > x && gx < x + w) c.fillRect(gx, gy, 3, 3);
}
function hexA(hex, a) { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; }

function endCard(t) {
  const up = (tin, dur = .45) => { const k = p(t, tin, tin + dur); return [eOutC(k), (1 - eOutC(k)) * 40]; };
  // lockup, stacked
  const kG = p(t, 47.28, 48.0);
  globeIcon(ctx, W / 2, 540, 92, kG, COL.cream, COL.pink, 13);
  ctx.save();
  ctx.font = font(900, 156); ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
  const wH = ctx.measureText(BRAND1).width;
  ctx.beginPath(); ctx.rect(0, 640, W, 175); ctx.clip();
  let x = W / 2 - wH / 2; ctx.textAlign = 'left';
  for (let i = 0; i < BRAND1.length; i++) {
    const ki = eOutC(p(t, 47.34 + i * .05, 47.34 + i * .05 + .45));
    ctx.fillStyle = COL.cream; ctx.fillText(BRAND1[i], x, 800 + (1 - ki) * 170);
    x += ctx.measureText(BRAND1[i]).width;
  }
  ctx.restore();
  {
    const [a, dy] = up(47.75);
    ctx.save(); ctx.globalAlpha = a; ctx.font = font(800, 64); ctx.fillStyle = COL.pink; ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
    const w0 = ctx.measureText(BRAND2).width; const sp = clamp((wH - w0) / (BRAND2.length - 1), 0, 64 * 0.42);
    let gx = W / 2 - (w0 + sp * (BRAND2.length - 1)) / 2; for (const ch of BRAND2) { ctx.fillText(ch, gx, 884 + dy); gx += ctx.measureText(ch).width + sp; }
    ctx.restore();
  }
  // divider
  const kd = eOutC(p(t, 47.95, 48.4));
  if (kd > 0) { ctx.save(); ctx.fillStyle = grad(ctx, W / 2 - 160, 0, W / 2 + 160, 0); rr(ctx, W / 2 - 160 * kd, 938, 320 * kd, 6, 3); ctx.fill(); ctx.restore(); }
  const line = (txt, y, f, col, tin, ls = 0) => {
    const [a, dy] = up(tin);
    if (a <= 0) return;
    ctx.save(); ctx.globalAlpha = a; ctx.font = f; ctx.fillStyle = col; ctx.letterSpacing = ls + 'px';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(txt, W / 2 + ls / 2, y + dy); ctx.letterSpacing = '0px'; ctx.restore();
  };
  line('More leads. More orders. Real results.', 1024, font(700, 42), COL.cream, 48.05);
  line('META ADS  •  GOOGLE ADS  •  SEO  •  WEBSITES', 1098, font(700, 27), 'rgba(255,138,102,0.95)', 48.2, 2);
  // CTA
  const bk = eOutBack(p(t, 48.35, 48.75), 1.7);
  if (bk > 0) {
    ctx.save(); ctx.globalAlpha = clamp(bk * 2);
    const pulse = t > 48.8 ? .5 + .5 * Math.sin((t - 48.8) * 5) : 0;
    const press = 1 - .05 * Math.sin(Math.PI * p(t, 49.55, 49.75));
    const s = lerp(.6, 1, bk) * press * (1 + .015 * pulse);
    ctx.translate(W / 2, 1262); ctx.scale(s, s); ctx.translate(-W / 2, -1262);
    ctaButton(ctx, W / 2, 1262, 920, 146, 99, [['BOOK', 0], ['YOUR', 0], ['FREE', 0], ['CONSULTATION', 0]], pulse);
    ctx.restore();
    tapRipple(ctx, W / 2 + 330, 1290, t, 49.6);
  }
  contactChip('web', 'www.haadinglobal.com', 1420, 48.55);
  contactChip('wa', '+92 305 4782677', 1516, 48.7);
  // footer
  {
    const [a, dy] = up(48.8);
    if (a > 0) {
      ctx.save(); ctx.globalAlpha = a;
      ctx.font = font(800, 32); ctx.letterSpacing = '6px';
      const t1 = 'DUBAI', t2 = 'LONDON';
      const w1 = ctx.measureText(t1).width, w2 = ctx.measureText(t2).width;
      const total = 44 + w1 + 90 + w2;
      let fx = W / 2 - total / 2; const fy = 1760 + dy;
      icon(ctx, 'pin', fx + 16, fy, 34, COL.pink, 2.4);
      ctx.fillStyle = COL.cream; ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
      ctx.fillText(t1, fx + 44, fy + 2);
      icon(ctx, 'arrowR', fx + 44 + w1 + 40, fy, 34, COL.pink, 2.6);
      ctx.fillText(t2, fx + 44 + w1 + 90, fy + 2);
      ctx.letterSpacing = '0px';
      ctx.restore();
    }
  }
}

// contact chip on the end card: icon disc + text on a glass pill
function contactChip(kind, text, cy, tin) {
  const t = curT;
  const k = p(t, tin, tin + .45); if (k <= 0) return;
  ctx.save();
  ctx.globalAlpha = eOutC(k);
  ctx.translate(0, (1 - eOutC(k)) * 30);
  ctx.font = font(800, 40); ctx.letterSpacing = '1px';
  const tw = ctx.measureText(text).width;
  const h = 84, w = tw + 84 + 56, x = W / 2 - w / 2, y = cy - h / 2;
  glass(ctx, x, y, w, h, h / 2, { tint: 'rgba(255,255,255,0.08)', border: 'rgba(255,255,255,0.22)' });
  const ix = x + 14 + 29, iy = cy;
  if (kind === 'wa') {
    ctx.fillStyle = '#25D366'; ctx.beginPath(); ctx.arc(ix, iy, 29, 0, 7); ctx.fill();
    icon(ctx, 'phone', ix, iy, 30, '#fff', 2.4);
  } else {
    ctx.fillStyle = grad(ctx, ix - 29, iy - 29, ix + 29, iy + 29); ctx.beginPath(); ctx.arc(ix, iy, 29, 0, 7); ctx.fill();
    globeIcon(ctx, ix, iy, 13, 1, '#fff', '#fff', 2.6);
  }
  ctx.fillStyle = COL.cream; ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  ctx.fillText(text, ix + 29 + 22, cy + 2);
  ctx.letterSpacing = '0px';
  ctx.restore();
}

function flash(t) {
  const F = [[23.55, .22, .6], [21.03, .14, .22], [47.15, .2, .3]];
  for (const [t0, d, a] of F) {
    const u = p(t, t0, t0 + d); if (u <= 0 || u >= 1) continue;
    ctx.fillStyle = `rgba(255,248,240,${a * (1 - u)})`; ctx.fillRect(0, 0, W, H);
  }
}

// ---------- frame loop ----------
let curT = 0;
const imgCache = new Map();
async function getImg(n) {
  if (imgCache.has(n)) return imgCache.get(n);
  const img = new Image();
  img.src = `frames/${String(n).padStart(4, '0')}.jpg`;
  await img.decode();
  if (imgCache.size > 4) imgCache.delete(imgCache.keys().next().value);
  imgCache.set(n, img);
  return img;
}

window.renderFrame = async function (f, type = 'image/jpeg', q = 0.93) {
  const t = srcOf(f / FPS);
  curT = t;
  const fi = Math.floor(t * FPS + 1e-6);
  const frac = t * FPS - fi;
  const n = Math.min(SRC_N, fi + 1);
  const img = await getImg(n);
  const img2 = frac > 0.01 && n < SRC_N ? await getImg(n + 1) : null;
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
  drawVideo(img, t, img2, frac);
  glitch(t, f);
  // backdrop for glass cards
  bctx.filter = 'blur(6px)'; bctx.drawImage(cv, 0, 0, 270, 480); bctx.filter = 'none';

  sparkles(t);
  hook(t);
  phoneCard(t);
  searchCard(t);
  tilesRow(t, [['TRAFFIC', 6.45], ['LEADS', 8.25], ['SALES', 10.0]], 11.15, 'down');
  triedPills(t);
  growthLoader(t);
  brandReveal(t);
  brandBug(t);
  serviceChips(t);
  route(t);
  notifications(t);
  tilesRow(t, [['LEADS', 36.85], ['ORDERS', 38.15], ['RESULTS', 39.45]], 40.2, 'up');
  months(t);
  captions(t);
  ctaPanel(t, img);
  flash(t);
  return cv.toDataURL(type, q);
};

window.ready = (async () => {
  try {
    const words = await (await fetch('words.json', { cache: 'no-store' })).json();
    let fill = {};
    try { fill = await (await fetch('fillinfo.json', { cache: 'no-store' })).json(); } catch (e) { console.error('fillinfo.json', e.message); }
    buildCaptions(words, fill);
    window.CAPS_DEBUG = CAPS.map(c => [c.toks.map(t => t.text).join(' '), +c.s.toFixed(2), +c.e.toFixed(2), c.req ? [Math.round(c.req.hw), Math.round(c.req.top), Math.round(c.req.bot)] : null]);
  } catch (e) { console.error('words.json', e.message); }
  await Promise.all([
    document.fonts.load(font(900, 40, 'Montserrat', 'italic')), document.fonts.load(font(900, 40)),
    document.fonts.load(font(800, 40)), document.fonts.load(font(700, 40)), document.fonts.load(font(600, 40)),
    document.fonts.load('400 40px Bebas'), document.fonts.load('700 40px Inter'), document.fonts.load('600 40px Inter'), document.fonts.load('500 40px Inter'),
  ]);
  return { total: Math.round(TOTAL_OUT * FPS), fonts: [...document.fonts].filter(f => f.status === 'loaded').length };
})();
