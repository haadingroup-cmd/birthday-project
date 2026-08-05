# 🎂 Birthday Universe

A cinematic, futuristic birthday website built with **Next.js 15.5** (security-patched), **React 19**, and **TypeScript**.

Features: animated space intro with a glowing portal, a spinning 3D birthday cake, a live countdown to 13 May (auto-celebrates on the day), a 3D-tilt photo gallery with a full-screen lightbox, an editable 2005→now memory timeline, a wish wall that saves messages on the visitor's device, click-anywhere hearts, fireworks, ambient sound, and typing easter eggs (`birthday`, `2005`).

---

## 🚀 Run it locally

You need [Node.js](https://nodejs.org) 18.18+ installed.

```bash
npm install
npm run dev
```

Then open **http://localhost:3000**.

To make a production build:

```bash
npm run build
npm start
```

---

## ✏️ Personalize it

Everything you'd want to change lives in **one file**: `src/data/content.ts`

- **Your name / date** — edit the `BIRTHDAY` object.
- **Photos** — drop image files into `public/photos/`, then list them in the `PHOTOS` array with a caption each.
- **Timeline** — edit the `MILESTONES` array (years + text). You can also edit captions live in the browser by clicking them.

Colors live as CSS variables at the top of `src/app/globals.css` (`--accent`, `--purple`, `--pink`, `--gold`, etc.).

---

## ☁️ Deploy

### Option A — Vercel (recommended, easiest)

1. Push this project to a **GitHub** repo (see below).
2. Go to [vercel.com](https://vercel.com) and sign in with GitHub.
3. Click **Add New → Project**, import your repo.
4. Vercel auto-detects Next.js — just click **Deploy**. Done. You'll get a live URL.

### Push to GitHub

```bash
git init
git add .
git commit -m "Birthday Universe"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

(Create the empty repo first at github.com → New repository, then use its URL above.)

---

## 🌐 Custom domain (optional)

After deploying on Vercel: **Project → Settings → Domains → Add**, then point your
domain (e.g. `happybirthdayhaseeb.com`) at Vercel following their DNS instructions.

---

## 📁 Structure

```
src/
  app/
    layout.tsx      root layout + fonts + metadata
    page.tsx        composes all sections
    globals.css     all styles
  components/       one file per section / feature
  data/content.ts  ← EDIT THIS to personalize
  lib/effects.ts   fireworks + hearts engine
public/photos/     your images
```

Made with ❤️
