# Word timings: notes

Output: `words.json` has 80 words in spoken order, `{w, s, e, src}`, in SOURCE seconds (frame n = (n-1)/30).
Helper: `phrases.json` groups the words into phrases at audio pauses of 80 ms or more (text, s, e, word indices).

## Conventions
- `s` is the moment the word audibly starts.
  - **After a pause** (phrase-initial words): `s` is the start of the main energy rise in the 200–7000 Hz band, measured at a 5 ms hop. It is the first frame within 15 dB of the word's peak, traced back down the steep rising edge.
  - Vowel-initial words have a faint breathy pre-voicing 70–100 ms earlier, about 18 dB below the peak and only about 7 dB above the floor. It is deliberately **not** used as `s`. The cases are And 13.72 (s=13.79), and 27.38 (s=27.47) and a 28.72 (s=28.81). "Book" has 55 ms of prevoicing: `s`=46.45 marks the prevoicing, and the burst comes at 46.51.
- **Mid-phrase words**: `s` is the pocketsphinx word boundary plus 15 ms (see the bias below). A word-initial stop's closure belongs to that word (standard phonetic segmentation). For example, "traffic" starts at the closure at 6.695, and its burst is at 6.735.
- `e` for a word before a pause is where the band energy falls back to the floor. Final bursts and fricative tails are included (traffic k-release 7.20, month th 41.49, worked t-release 14.53–14.60).
- `e` for a word followed directly by another word equals the next word's `s`. In connected speech, a word's audio ends where the next one starts.
- `src`:
  - `both`: an audio timing that the burned caption pop-in confirms within ±3 frames.
  - `audio`: either the word has no burned caption, or the caption disagreed by more than 3 frames. That is usually the caption tool's pre-roll on phrase-initial words, and the audio was trusted.
  - No word uses caption timing. Counts: both 52, audio 28.
- Display text uses sentence case: proper nouns plus the first word of each sentence (Haadin, Global, Meta, Google Ads, SEO, Dubai, London, I).
  - The burned captions misspell "Hardin" and "Seo". They are corrected here to "Haadin" and "SEO".
  - The audio is cut mid-phrase at 47.233 s, after "Book your free". A fragment of the next word starts at about 47.15, so "free" ends at 47.14.

## Method 1: burned-caption pop-in detection
- I decoded a 478x300 band (source y 520–820) to raw RGB. An automatic mask (magenta fill near the cream outline and the black outline) separates legible captions from the pink hologram UI cards that fill the background after 16 s.
- The pop-in START of each of the 75 captioned words was read frame by frame from contact sheets (`img/ov_*.jpg`, every frame with its timestamp). These are recorded in `cap_entrances.py`, giving `c/cap_entr.json`.
- The rule was the first frame showing the new word, blurred or not, after the previous word's exit blur. Uncertainty is ±1 frame where the exit and entrance blurs touch (Rings, We, From, Global).
- There is no caption for 15.4–19.0 or 19.9–22.55 ("I partnered with Haadin Global").

## Method 2: audio
- I extracted 16 kHz mono with ffmpeg and ran pocketsphinx 5 forced alignment per phrase chunk (`align.py`, `segs_chunk.json`). Chunking was needed: a single whole-file pass put "Then" on the 15.4 s whoosh.
- I added a pronunciation for "haadin" (HH AA D IH N). "SEO" aligned best as "see-oh".
- I computed band-energy envelopes (200–7000 Hz from 16 kHz audio, and 200–16000 Hz and 4–16 kHz from 44.1 kHz audio; 10 ms window, 5 ms hop) to snap onsets and offsets (`refine2.py`).
- **Aligner bias**: pocketsphinx boundaries are on average about 15 ms early. Against energy onsets for the 20 clean phrase-initial words the median gap was +17.5 ms; against fricative and burst landmarks it was +12.5 ms. So +15 ms was added to every mid-phrase boundary.
- I inspected every phrase-initial onset, every phrase-final offset and all 56 mid-phrase boundaries on zoomed spectrogram and energy tiles (`img/grid_on.png`, `img/grid_off.png`, `img/mid_*.png`, `img/fin_*.png`).
- Manual fixes:
  - Dubai/to/London: "Dubai" voicing ends 32.515, then a t-closure and a burst at 32.59, and the l-onset is at 32.665. The aligner had placed "to" about 50 ms early.
  - "that": starts at 29.405, the dh onset after the unreleased t of "website".
  - "everything": starts at 11.88, after the d-release of "tried".
  - "SEO": starts at 27.56, the s onset.
  - Offsets: traffic 7.205, Then 19.54, month 41.495, free 47.14.

## Caption vs audio offset (burned caption pop-in START minus audio `s`)
- **Mid-phrase words**: median +0.020 s (+0.6 frame) and SD 0.045 s (n=52). The old captions popped in about half a frame after the audio onset, so they were essentially in sync.
- **Phrase-initial words**: median −0.165 s and SD 0.084 s (n=23). The old caption tool pre-rolls the first word after each pause by about 5 frames (range −0.06 to −0.29).
- **Outliers**:
  - "and SEO": +0.16 and +0.17. The caption tool was late here (see the low-confidence region below).
  - "sells" +0.11 and "results" +0.15: the caption tool timed these to the vowel or the "z" rather than the word onset.
  - "And" at 13.79: −0.29 (pre-roll).
- So for new captions: the audio `s` values are the true onsets. Do not copy the old caption timing for phrase starts.

## Confidence per region
| Region (s) | Words | Confidence |
|---|---|---|
| 0.27–14.60 | My … worked | High (±1 frame). And 13.79: medium, because of the faint pre-voicing from 13.72. |
| 19.18–19.54 | Then | High. Loud whoosh and music floor; the dh onset at 19.18 is clear. |
| 20.16–21.84 | I partnered with Haadin Global | Audio only, no caption. Medium-high: all boundaries checked on the spectrogram. with→Haadin is the th→h transition (±1 frame). |
| 22.79–26.42 | And everything changed / Meta / and Google Ads | High. |
| 27.47–27.94 | and SEO | **Low-medium for the split.** The audio is vowel (27.47–27.56), s (27.56–27.71), then "ee-oh" (to 27.94). It fits "an' see-oh" and spelled "ess-ee-oh" equally well, so "and" may be barely articulated. SEO's start is ±1 frame either way. |
| 28.81–33.10 | a website that sells / Now customers … London | High after the fixes above. |
| 34.68–41.50 | Now my phone … every single month | High. |
| 42.79–47.14 | Want the same … Book your free | High. "the" is only 60 ms (42.995–43.055, 2 frames). |

## Files
- `a/align_chunk.json`: raw aligner output.
- `a/refine2_detail.json`: aligner plus energy snapping.
- `a/final_detail.json`: per word, including the caption time and the caption−audio difference.
- `c/cap_entr.json`: caption pop-in frames.
- `final.py`: rebuilds `words.json`. Run `python3 -I final.py <this dir>`.
