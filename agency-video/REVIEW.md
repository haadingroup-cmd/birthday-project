# Haadin Global agency ad: review and edit

**Deliverable:** `haadin-global-ad-edited.mp4` (1080×1920, 30 fps, 50.7 s, H.264 + AAC, mastered to −14 LUFS)

## What the video says

| Time | Shot | Voiceover |
|---|---|---|
| 0.0–6.0 | Standing in the store, holding a phone | "My store looks amazing, but my phone never rings. Nobody even knows we exist." |
| 6.0–15.3 | Seated at a laptop | "No traffic. No leads. No sales. I tried everything… and nothing worked." |
| 15.3–19.1 | Cool to warm colour shift, holograms appear | *(no voice, riser sound only)* |
| 19.1–24.2 | Seated, holographic UI around him | "Then I partnered with **Haadin Global**… and everything changed." |
| 24.2–34.2 | Standing, holographic charts and globe | "Meta and Google Ads, and SEO, and a website that sells. Now customers find me, from Dubai to London." |
| 34.2–42.5 | Busy store, phone in hand | "Now my phone never stops. More leads, more orders, real results, every single month." |
| 42.5–47.2 | Arms crossed | "Want the same for your business? Talk to Haadin Global. Book your free—" *(cut off)* |

The structure (problem, turning point, solution, proof, CTA) is right for an agency ad. The problems are in the finishing.

## What could be better (in priority order)

1. **The video ends mid-sentence.** The audio stops on "Book your free—", with no end card and no way to contact you. This is the biggest conversion leak in the ad.
2. **The brand moment has no captions.** "Then I partnered with Haadin Global" (20–22 s) is the only uncaptioned line in the video. Most viewers watch muted, so they never see the agency's name in the middle of the ad.
3. **The brand name is misspelled in the captions.** At 45 s the burned-in captions read "**Hardin** Global".
4. **The resolution is low.** The file is a 478×850 WhatsApp export at about 1.1 Mbps, so it looks soft on any phone. Export the original at 1080×1920 and send it as a *document* (or via Drive), not as a WhatsApp video.
5. **The audio is quiet and thin.** It measured −20.7 LUFS, while Reels, TikTok and Shorts normalise to about −14. There is no music bed and almost no sound design, so the problem section sounds no different from the success section.
6. **The services list is spoken but never shown.** "Meta and Google Ads, SEO, websites" goes by in 4 seconds; viewers won't remember it unless they also read it.
7. **3.8 s of dead air (15.3–19.1 s).** It's a nice visual transformation, but with no voice and no text it's where people swipe away.
8. **No proof.** "Real results every single month" is a claim. One real number from a client ("+212 % leads in 90 days"), a testimonial or client logos would make it far more convincing.
9. **The hook is soft.** "My store looks amazing" is a calm opener. The pain line ("My phone never rings") or an on-screen question in the first second would stop more scrolls.
10. **The CTA isn't specific.** Say exactly what to do and where: *"Book your free 15-minute strategy call — link in bio / WhatsApp +971…"*.

## What was done in this edit

**Fixes**
- Added captions in the original caption style for "I partnered with Haadin Global" (20.1–22.0 s).
- Added a CTA panel over the bottom from 44.2 s. It hides the "Hardin" misspelling and shows **HAADIN GLOBAL** correctly, then turns into a **BOOK YOUR FREE CONSULTATION** button.
- Added a 3.5 s branded end card that completes the cut-off sentence. It has the logo, the tagline "More leads. More orders. Real results.", the services, the CTA button, "Tap the link in bio • or send us a DM" and "Dubai → London".
- Upscaled to 1080×1920 with sharpening and light grain, and rendered all graphics natively at full resolution so the text stays crisp.
- Cleaned up the voice (high-pass, EQ, gentle compression) and mastered the final mix to −14 LUFS / −1.5 dBTP.

**Motion graphics** (all in brand colours taken from the existing captions and holograms)
- 1.0 s: sparkles on "looks amazing".
- 1.9 s: a "CALLS TODAY: 0" card with a struck-out phone.
- 4.0 s: a search bar that types "your store" and returns "0 results found".
- 6.4–11 s: TRAFFIC / LEADS / SALES tiles that drop in at **0** with dying red lines. The colour slowly drains from the footage.
- 11.4–14.2 s: "Flyers ✕ / Discounts ✕ / Posting daily ✕" tags get struck out and fall away, followed by an RGB glitch on "nothing worked".
- 15.5–19.1 s: a "GROWTH MODE" loader fills the dead air, runs 0→100 % as the colour comes back, then flips to "ON ✓".
- 21.0 s: **logo reveal** (a globe that draws itself, the wordmark rising letter by letter, a light sweep). It then shrinks into a corner logo that stays on screen until the CTA.
- 23.55 s: a flash and zoom punch on "everything changed", where the beat drops.
- 24.7–30 s: service chips pop in on each word: META ADS, GOOGLE ADS, SEO, WEBSITES THAT SELL.
- 31.3–33.9 s: a **Dubai → London** flight-path graphic, with the plane flying in sync with the words.
- 34.6–36.5 s: a stack of phone notifications on "my phone never stops" (new lead, new order, incoming call…).
- 36.8–40.3 s: the same three tiles come back for LEADS / ORDERS / RESULTS, now with rising bars (a callback to the 0 tiles).
- 40.5–42 s: JAN→DEC tick off one by one on "every single month".
- Throughout: subtle zoom punches and camera shake on key hits, a vignette, and a gradient behind the header area so the graphics read clearly.

**Sound design** (all synthesized, so there are no licensing issues)
- **Music bed:** a dark, sparse tension pad under the problem section. An arpeggio builds from "Then…", and an upbeat 120 BPM groove drops on "everything changed". It ducks automatically under the voice and swells on the end card.
- **SFX:** an opening boom, a sparkle shimmer, an error beep, keyboard typing, crickets on "nobody knows we exist", tile thuds, ✕ stamps, a glitch zap and power-down, a flash, a riser into a "ding", a brand boom with shimmer, a drop impact and crash, chip pops, map pings, a plane fly-by, notification pings, a ka-ching on "orders", 12 ascending month ticks, a button click and an end-card impact.

## Things I assumed (easy to change)

- **Brand spelling:** "Haadin Global". The captions said "Hardin" and the voice is ambiguous, so this comes from your GitHub org and account name. The name is one constant in `source/gfx.js` (`BRAND1`, `BRAND2`).
- **CTA wording:** "Book your free consultation". The voice is cut before the last word, so if you say "strategy call", "audit" or similar in the full script, that's a one-line change.
- **End-card contact line:** "Tap the link in bio • or send us a DM". Send me a phone/WhatsApp number, website or handle and I'll put it on the end card. That's the single most valuable addition left.
- The ✕-ed tactics ("Flyers / Discounts / Posting daily") and the notification texts are illustrative.
- There are no specific numbers anywhere, on purpose, so the ad makes no claim you can't back up.

## Re-building

`source/` has everything needed to re-render: `render.html` and `gfx.js` (the motion graphics), `render.js` (the headless-Chromium frame renderer), `audio.py` (SFX, music and the mix) and `build.sh` (the full pipeline).
