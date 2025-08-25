# record_prompts_simple.py
# Enter to START immediately; auto-stops on ~1 s of silence (+300 ms hang) or at 8 s max.
# Resume-aware: starts at next "missing" or too-short file and skips existing good takes.

import csv, os, sys, time, queue
import numpy as np
import sounddevice as sd
import soundfile as sf

# -------- Settings --------
CSV_PATH        = "prompts.csv"
OUTDIR          = "wavs"
SAMPLE_RATE     = 22050
MAX_SECONDS     = 5.0             # hard cap
AUTO_TRIM       = True
SILENCE_DB      = -40.0           # RMS threshold in dBFS (use -38 / -35 to be less strict)
FRAME_MS        = 10.0            # analysis frame size
MIN_SPEECH_MS   = 80.0            # require this much voiced audio to mark start
SILENCE_STOP_MS = 1000.0          # stop after this much continuous silence
HANG_TAIL_MS    = 300.0           # keep recording this long *after* silence detected
PAD_MS          = 150             # re-add head/tail pad after trim
PEAK_DB         = -3.0            # peak normalize target
FADE_MS         = 10.0            # fade in/out to avoid clicks
TRIM_START_SLOP_MS = 20.0         # include a bit extra at the start
TRIM_END_SLOP_MS   = 160.0        # include a bit extra at the end was 120
MIN_GOOD_SEC    = 0.20            # treat files shorter than this as "missing" (e.g., 44-byte empties)
OVERWRITE       = False           # set True to re-record everything regardless of existing files
# --------------------------

def db_to_linear(db): return 10.0 ** (db / 20.0)

def rms(x):
    if x.size == 0: return 0.0
    return float(np.sqrt(np.mean(np.square(x), axis=0)).max())

def is_good_wav(path, min_sec=MIN_GOOD_SEC):
    """Return True if WAV exists and duration >= min_sec."""
    try:
        if not os.path.isfile(path):
            return False
        info = sf.info(path)
        if info.samplerate <= 0: 
            return False
        dur = info.frames / float(info.samplerate)
        return dur >= min_sec
    except Exception:
        return False

def trim_silence_rms(audio, sr=SAMPLE_RATE, thresh_db=SILENCE_DB, frame_ms=FRAME_MS,
                     min_speech_ms=MIN_SPEECH_MS,
                     start_slop_ms=TRIM_START_SLOP_MS, end_slop_ms=TRIM_END_SLOP_MS):
    # mono analyze
    if audio.ndim == 2: a = audio[:, 0]
    else: a = audio
    n = a.size
    if n == 0: return audio.reshape(-1, 1)

    frame_len = max(1, int(sr * (frame_ms / 1000.0)))
    thr = db_to_linear(thresh_db)

    starts = np.arange(0, n, frame_len)
    rms_vals = np.empty(starts.size, dtype=np.float32)
    for i, s in enumerate(starts):
        e = min(s + frame_len, n)
        # smaller helper RMS to keep speed
        v = a[s:e]
        rms_vals[i] = float(np.sqrt(np.mean(v*v))) if v.size else 0.0

    above = rms_vals > thr
    need = max(1, int(round(min_speech_ms / frame_ms)))

    # first >= need True run
    run = 0; start_frame = None
    for i, v in enumerate(above):
        run = run + 1 if v else 0
        if run >= need:
            start_frame = i - need + 1
            break
    if start_frame is None:
        return np.zeros((0, 1), dtype=np.float32)

    # last >= need True run
    run = 0; end_frame = None
    for i in range(len(above) - 1, -1, -1):
        v = above[i]
        run = run + 1 if v else 0
        if run >= need:
            end_frame = i
            break

    start_idx = int(start_frame * frame_len)
    end_idx   = int(min((end_frame + 1) * frame_len, n))

    # add slop
    start_idx = max(0, start_idx - int(sr * (start_slop_ms / 1000.0)))
    end_idx   = min(n, end_idx + int(sr * (end_slop_ms   / 1000.0)))

    trimmed = a[start_idx:end_idx].astype(np.float32, copy=False)
    return trimmed.reshape(-1, 1)

def add_pad(audio, sr=SAMPLE_RATE, pad_ms=PAD_MS):
    n = int(sr * (pad_ms / 1000.0))
    if n <= 0: return audio
    pad = np.zeros((n, audio.shape[1]), dtype=np.float32)
    return np.concatenate([pad, audio, pad], axis=0)

def peak_normalize(audio, target_db=PEAK_DB):
    if audio.size == 0: return audio
    peak = float(np.max(np.abs(audio)))
    if peak <= 0.0: return audio
    target = db_to_linear(target_db)
    if peak <= target: return audio
    return (audio * (target / peak)).astype(np.float32, copy=False)

def fade_edges(audio, sr=SAMPLE_RATE, ms=FADE_MS):
    if audio.size == 0 or ms <= 0: return audio
    n = min(int(sr * (ms / 1000.0)), max(1, audio.shape[0] // 2))
    ramp = np.linspace(0.0, 1.0, n, dtype=np.float32).reshape(-1, 1)
    audio[:n]  *= ramp
    audio[-n:] *= ramp[::-1]
    return audio

def ensure_mono(audio):
    return audio if audio.ndim == 2 else audio.reshape(-1, 1)

def record_until_silence(sr=SAMPLE_RATE, max_seconds=MAX_SECONDS,
                         thresh_db=SILENCE_DB, frame_ms=FRAME_MS,
                         silence_stop_ms=SILENCE_STOP_MS, min_speech_ms=MIN_SPEECH_MS,
                         hang_tail_ms=HANG_TAIL_MS):
    """VOX with hang tail; keep full captured buffer."""
    frame_len = max(1, int(sr * (frame_ms / 1000.0)))
    thr = db_to_linear(thresh_db)
    need_speech_frames  = max(1, int(round(min_speech_ms   / frame_ms)))
    need_silence_frames = max(1, int(round(silence_stop_ms / frame_ms)))
    hang_tail_samples   = int(sr * (hang_tail_ms / 1000.0))

    q = queue.Queue()
    captured_chunks = []
    pending = np.zeros((0, 1), dtype=np.float32)

    have_speech = False
    consec_speech = 0
    consec_silence = 0
    start_t = time.time()

    tail_mode = False
    tail_left = hang_tail_samples

    def cb(indata, frames_count, time_info, status):
        q.put(indata.copy())

    with sd.InputStream(samplerate=sr, channels=1, dtype="float32",
                        callback=cb, blocksize=frame_len):
        print("Recording… (auto-stops on ~1 s silence + 300 ms hang, or at 8 s max)")
        while True:
            if (time.time() - start_t) >= max_seconds:
                break
            try:
                chunk = q.get(timeout=0.1)
            except queue.Empty:
                continue

            captured_chunks.append(chunk)
            x = chunk if chunk.ndim == 2 else chunk.reshape(-1, 1)

            if tail_mode:
                tail_left -= x.shape[0]
                if tail_left <= 0:
                    break
                continue

            pending = np.vstack((pending, x))
            while pending.shape[0] >= frame_len:
                frm = pending[:frame_len, 0]
                pending = pending[frame_len:, :]
                # fast RMS
                val = float(np.sqrt(np.mean(frm*frm))) if frm.size else 0.0
                if val > thr:
                    consec_speech += 1
                    consec_silence = 0
                    if not have_speech and consec_speech >= need_speech_frames:
                        have_speech = True
                else:
                    consec_silence += 1
                    if have_speech and consec_silence >= need_silence_frames:
                        tail_mode = True
                        tail_left = hang_tail_samples
                        break

    audio = np.concatenate(captured_chunks, axis=0) if captured_chunks else np.zeros((0, 1), dtype=np.float32)
    return ensure_mono(audio)

def main():
    if not os.path.exists(CSV_PATH):
        print(f"ERROR: {CSV_PATH} not found.", file=sys.stderr); sys.exit(1)
    os.makedirs(OUTDIR, exist_ok=True)

    try:
        sd.check_input_settings(samplerate=SAMPLE_RATE, channels=1)
    except Exception as e:
        print("WARNING: input settings check failed:", e, file=sys.stderr)

    # Load prompts
    with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        if "filename" not in r.fieldnames or "transcript" not in r.fieldnames:
            print("ERROR: CSV must have headers: filename,transcript", file=sys.stderr); sys.exit(1)
        rows = list(r)

    # Build the todo list (resume): indices of rows that need recording
    todo_indices = []
    for idx, row in enumerate(rows):
        out_path = os.path.join(OUTDIR, row["filename"].strip())
        if OVERWRITE or not is_good_wav(out_path, MIN_GOOD_SEC):
            todo_indices.append(idx)

    total = len(rows)
    need  = len(todo_indices)
    if need == 0:
        print(f"All {total} prompts already recorded (≥ {MIN_GOOD_SEC:.2f}s). Nothing to do.")
        return

    first_idx = todo_indices[0]
    print(f"Loaded {total} prompts from {CSV_PATH}")
    print(f"Found {total-need} existing good files; {need} left to record. Starting at row #{first_idx+1}.")
    print("Flow: shows transcript ➜ Enter to START ➜ auto-stops on 1 s silence (+300 ms hang) or 8 s max.")
    print("After save: Enter=keep, R=redo, Q=quit.\n")

    pos = 0
    while pos < len(todo_indices):
        i = todo_indices[pos]
        row = rows[i]
        fname = row["filename"].strip()
        text  = row["transcript"].strip()
        out_path = os.path.join(OUTDIR, fname)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        print("-"*80)
        print(f"{i+1}/{total}  Next: {fname}")
        print(f"Say: '{text}'")
        cmd = input("Press Enter to START (S=skip, Q=quit) > ").strip().lower()
        if cmd == "q":
            print("Quitting."); break
        if cmd == "s":
            print("Skipped."); pos += 1; continue

        audio = record_until_silence(SAMPLE_RATE, MAX_SECONDS, SILENCE_DB, FRAME_MS,
                                     SILENCE_STOP_MS, MIN_SPEECH_MS, HANG_TAIL_MS)

        if AUTO_TRIM and audio.size:
            audio = trim_silence_rms(audio, SAMPLE_RATE, SILENCE_DB, FRAME_MS,
                                     MIN_SPEECH_MS, TRIM_START_SLOP_MS, TRIM_END_SLOP_MS)
            audio = add_pad(audio, SAMPLE_RATE, PAD_MS)
            audio = fade_edges(audio, SAMPLE_RATE, FADE_MS)
            audio = peak_normalize(audio, PEAK_DB)

        sf.write(out_path, audio, SAMPLE_RATE, subtype="PCM_16")
        print(f"Saved: {out_path}")

        post = input("Keep? Enter=yes, R=redo, Q=quit > ").strip().lower()
        if post == "r":
            try: os.remove(out_path)
            except OSError: pass
            print("Redoing this line…")
            continue
        if post == "q":
            print("Quitting."); break

        pos += 1

    print("\nAll done (or stopped). 73!")

if __name__ == "__main__":
    main()
