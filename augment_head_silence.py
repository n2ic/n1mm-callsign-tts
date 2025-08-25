# augment_head_silence.py
# Creates wavs_aug/ with random 120–300 ms head silence + 15 ms fade-in.
# Writes metadata_aug.csv pointing to wavs_aug/<file>.wav (texts unchanged).
import os, json
from pathlib import Path
import numpy as np
import soundfile as sf
import random

SR = 22050
SIL_MIN = 0.12   # seconds
SIL_MAX = 0.30   # seconds
FADE_SEC = 0.015 # seconds

root = Path(".")
wavs_in  = root / "wavs"
wavs_out = root / "wavs_aug"
wavs_out.mkdir(exist_ok=True)

meta_in  = root / "metadata.csv"
meta_out = root / "metadata_aug.csv"

def process(src, dst):
    audio, sr = sf.read(src, always_2d=False)
    if sr != SR:
        raise RuntimeError(f"{src} must be {SR} Hz, got {sr}")
    if audio.ndim > 1:  # mono
        audio = audio[:,0]
    sil_len = random.uniform(SIL_MIN, SIL_MAX)
    n_head = int(SR * sil_len)
    head = np.zeros(n_head, dtype=audio.dtype)
    out = np.concatenate([head, audio])

    # 15 ms fade-in after t=0 (protects against clicks)
    n_fade = int(SR * FADE_SEC)
    if 0 < n_fade < len(out):
        ramp = np.linspace(0.0, 1.0, n_fade, dtype=np.float32)
        out[:n_fade] = (out[:n_fade].astype(np.float32) * ramp).astype(out.dtype)

    sf.write(dst, out, SR, subtype="PCM_16")

rows = []
with meta_in.open("r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or "|" not in line: continue
        left, text = line.split("|", 1)

        if "/" in left:
            name = Path(left).name
            src = root / left
        else:
            name = f"{left}.wav"
            src = wavs_in / name

        dst = wavs_out / name
        process(src, dst)
        rows.append(f"wavs_aug/{name}|{text}")

with meta_out.open("w", encoding="utf-8") as f:
    f.write("\n".join(rows))

print(f"Augmented {len(rows)} files -> wavs_aug/, wrote metadata_aug.csv")
