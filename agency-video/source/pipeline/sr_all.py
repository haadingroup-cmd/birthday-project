"""AI-upscale every source frame with Real-ESRGAN (general x4v3, ONNX on CPU).
Writes sr1080/NNNN.jpg (1080x1920, 85% ESRGAN + 15% lanczos) and sr4k/NNNN.jpg (raw x4 output)."""
import sys, os, time, subprocess, numpy as np, onnxruntime as ort, cv2
model, src, out1080, out4k = sys.argv[1:5]
start = int(sys.argv[5]) if len(sys.argv) > 5 else 0
W0, H0 = 478, 850
so = ort.SessionOptions(); so.intra_op_num_threads = 4
sess = ort.InferenceSession(model, so, providers=['CPUExecutionProvider'])
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', src, '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], stdout=subprocess.PIPE)
fs = W0 * H0 * 3
i, t0 = 0, time.time()
while True:
    buf = p.stdout.read(fs)
    if len(buf) < fs:
        break
    i += 1
    name = f'{i:04d}.jpg'
    if i < start or os.path.exists(os.path.join(out1080, name)):
        continue
    bgr = np.frombuffer(buf, np.uint8).reshape(H0, W0, 3)
    x = (bgr[:, :, ::-1].astype(np.float32) / 255).transpose(2, 0, 1)[None].copy()
    y = sess.run(None, {'x': x})[0][0].transpose(1, 2, 0)
    sr = (np.clip(y, 0, 1) * 255 + .5).astype(np.uint8)[:, :, ::-1]
    cv2.imwrite(os.path.join(out4k, name), sr, [cv2.IMWRITE_JPEG_QUALITY, 95])
    a = cv2.resize(sr, (1080, 1920), interpolation=cv2.INTER_AREA)
    b = cv2.resize(bgr, (1080, 1920), interpolation=cv2.INTER_LANCZOS4)
    cv2.imwrite(os.path.join(out1080, name), cv2.addWeighted(a, 0.85, b, 0.15, 0), [cv2.IMWRITE_JPEG_QUALITY, 97])
    if i % 20 == 0:
        el = time.time() - t0
        print(f'{i}/1417 {el/ max(1, i - start + 1):.2f}s/frame elapsed {el/60:.1f}m', flush=True)
print('DONE', i, flush=True)
