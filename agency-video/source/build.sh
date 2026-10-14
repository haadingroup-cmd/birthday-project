#!/usr/bin/env bash
# Rebuilds haadin-global-ad-edited.mp4 from the original 478x850 WhatsApp export.
# Needs: ffmpeg, node + playwright (Chromium), python3 with numpy + scipy,
# and the Montserrat / Bebas Neue woff2 files from @fontsource in ./fonts/.
#
#   ./build.sh path/to/original.mp4 [work_dir]
set -euo pipefail
SRC="$1"
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${2:-$HERE/build}"
mkdir -p "$WORK/frames" "$WORK/out" "$WORK/aud"

# 1. Upscale the footage to 1080x1920 (graphics are rendered natively at this size).
ffmpeg -v error -y -i "$SRC" -vf "scale=1080:1920:flags=lanczos,unsharp=5:5:0.55:5:5:0" -q:v 2 "$HERE/frames/%04d.jpg"

# 2. Render every output frame (footage + grade + motion graphics) in headless Chromium.
node "$HERE/render.js" "$WORK/out" all 4 jpg

# 3. Clean up the voice, then synthesize SFX + music and mix them under it.
ffmpeg -v error -y -i "$SRC" -vn -af "highpass=f=75,highpass=f=75,equalizer=f=3200:t=q:w=1.2:g=2,equalizer=f=250:t=q:w=1:g=-1.5,acompressor=threshold=-22dB:ratio=2.5:attack=6:release=120:makeup=2,afade=t=out:st=47.17:d=0.06,aresample=48000" -ac 2 -c:a pcm_s16le "$WORK/aud/voice.wav"
python3 "$HERE/audio.py" "$WORK/aud/voice.wav" "$WORK/aud/mix_src.wav"
# Play the wordless 15.6–18.6s stretch at 1.5x to match the video (see RT in gfx.js), with 10 ms crossfades at the joins.
ffmpeg -v error -y -i "$WORK/aud/mix_src.wav" -filter_complex "[0]atrim=0:15.61,asetpts=PTS-STARTPTS[a];[0]atrim=15.6:18.6,asetpts=PTS-STARTPTS,atempo=1.5,atrim=0:2.0,asetpts=PTS-STARTPTS[b];[0]atrim=18.59,asetpts=PTS-STARTPTS[c];[a][b]acrossfade=d=0.01:c1=qsin:c2=qsin[ab];[ab][c]acrossfade=d=0.01:c1=qsin:c2=qsin" -c:a pcm_s16le "$WORK/aud/mix.wav"

# 4. Two-pass loudness normalisation to -14 LUFS / -1.5 dBTP (Instagram / TikTok / YouTube Shorts).
MEAS=$(ffmpeg -v info -i "$WORK/aud/mix.wav" -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/{/,/}/p' |
  python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"measured_I={d['input_i']}:measured_TP={d['input_tp']}:measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}:offset={d['target_offset']}\")")
ffmpeg -v error -y -i "$WORK/aud/mix.wav" -af "loudnorm=I=-14:TP=-1.5:LRA=11:$MEAS:linear=true,aresample=48000" -c:a pcm_s16le "$WORK/aud/master.wav"

# 5. Encode.
ffmpeg -v error -y -framerate 30 -i "$WORK/out/%05d.jpg" -i "$WORK/aud/master.wav" \
  -vf "noise=alls=3:allf=t,format=yuv420p" -c:v libx264 -preset slow -crf 19 -profile:v high -level 4.1 \
  -r 30 -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart "$WORK/haadin-global-ad-edited.mp4"
echo "done: $WORK/haadin-global-ad-edited.mp4"
