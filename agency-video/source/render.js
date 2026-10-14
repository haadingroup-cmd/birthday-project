// Usage: node render.js <outDir> [frames=all|comma list|a-b] [workers=4] [ext=jpg|png]
const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = __dirname;
const OUT = path.resolve(process.argv[2] || 'out');
const SPEC = process.argv[3] || 'all';
const WORKERS = +(process.argv[4] || 4);
const EXT = process.argv[5] || 'jpg';
fs.mkdirSync(OUT, { recursive: true });

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.jpg': 'image/jpeg', '.woff2': 'font/woff2', '.json': 'application/json' };
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0]);
  // FRAMES_DIR lets the final render read cleaned/upscaled footage instead of ./frames
  const base = process.env.FRAMES_DIR && u.startsWith('/frames/') ? process.env.FRAMES_DIR : ROOT;
  const f = path.join(base, base === ROOT ? u : u.slice('/frames'.length));
  if (!f.startsWith(base) || !fs.existsSync(f)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
});

(async () => {
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  const port = server.address().port;
  const browser = await chromium.launch();
  const pages = [];
  let total = 0;
  for (let i = 0; i < WORKERS; i++) {
    const pg = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
    pg.on('pageerror', e => console.error('pageerror', e.message));
    pg.on('console', m => { if (m.type() === 'error') console.error('console', m.text()); });
    await pg.goto(`http://127.0.0.1:${port}/render.html`);
    const info = await pg.evaluate(() => window.ready);
    total = info.total;
    if (i === 0) console.log('ready', JSON.stringify(info));
    pages.push(pg);
  }
  let frames;
  if (SPEC === 'all') frames = [...Array(total).keys()];
  else if (SPEC.includes('-')) { const [a, b] = SPEC.split('-').map(Number); frames = []; for (let f = a; f <= b; f++) frames.push(f); }
  else frames = SPEC.split(',').map(Number);

  const type = EXT === 'png' ? 'image/png' : 'image/jpeg';
  let next = 0, done = 0;
  const t0 = Date.now();
  await Promise.all(pages.map(async pg => {
    while (next < frames.length) {
      const f = frames[next++];
      const data = await pg.evaluate(([f, type]) => window.renderFrame(f, type, 0.94), [f, type]);
      fs.writeFileSync(path.join(OUT, `${String(f).padStart(5, '0')}.${EXT}`), Buffer.from(data.split(',')[1], 'base64'));
      if (++done % 100 === 0) console.log(`${done}/${frames.length} ${((Date.now() - t0) / done).toFixed(0)}ms/frame`);
    }
  }));
  console.log(`done ${done} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  await browser.close();
  server.close();
})().catch(e => { console.error(e); process.exit(1); });
