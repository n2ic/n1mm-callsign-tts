# N1MM Callsign TTS with Piper

This project takes **N1MM Logger+ UDP LookupInfo packets**, extracts the `call` field, converts it into **phonetics**, and uses the **Piper TTS engine** to generate a WAV file for SSB contest messages.

## Features
- Works alongside other N1MM UDP tools (custom port)
- Dynamic TTS — no need to pre-record callsigns
- Uses [Piper](https://github.com/rhasspy/piper) for fast, offline, natural-sounding voices

---

## 1. Installation

### Prerequisites
- **Windows 10/11**
- **Python 3.10+**
- [Piper TTS binary](https://github.com/rhasspy/piper/releases) (Windows .zip)

### Python script
```bash
git clone https://github.com/oh2xx/n1mm-callsign-tts.git
cd n1mm-callsign-tts
pip install -r requirements.txt
```

---

## 2. Piper Setup
1. Download Piper from: [Piper Releases](https://github.com/rhasspy/piper/releases)
2. Extract somewhere like `C:\piper\`
3. Download a voice model, e.g.:
   - [en_US-amy-medium](https://github.com/rhasspy/piper/releases/tag/v0.0.2)
4. Place model file (`.onnx`) into Piper folder

---

## 3. N1MM UDP Configuration
- In N1MM, go to **Config → Configure Ports, Mode Control, Winkey, etc.**
- Select **Broadcast Data** tab
- Enable **LookupInfo** broadcast
- Set **IP** to `127.0.0.1`
- Set **Port** to `12061`
- Click **OK**
<img width="723" height="588" alt="Näyttökuva 2025-08-09 213234" src="https://github.com/user-attachments/assets/04e51615-c025-4a04-8972-c4639a55506b" />

---

## 4. Running the script
```bash
python callsign_tts.py
```
When N1MM receives a callsign, a `callsign.wav` will be generated in the current folder.


## New versions

### `callsign_nr_tts.py`
- Listens for N1MM LookupInfo UDP packets.
- Generates `callsign.wav` with the calling station in phonetics.
- Extracts `<sntnr>` (sent number) from the packet.
- Creates:
  - `report_nr.wav` → `"you are five nine ###"` (with ### formatted with leading zeros)
  - `nr.wav` → just the ### number (leading zeros kept)
- Leading zero rules:
  - `<10` → `"00#"` (e.g., `5` → `"005"`)
  - `<100` → `"0##"` (e.g., `10` → `"010"`)
  - Otherwise → `"###"`

### `callsign_slownr_tts.py`
- Same features as `callsign_nr_tts.py`
- Sent number is spoken **digit-by-digit** with extra pauses for clarity:
  - `"005"` → `"Zero  Zero  Five"`
  - `"010"` → `"Zero  One  Zero"`
  - `"123"` → `"One  Two  Three"`
- Designed for better intelligibility.


---

## 5. Sending audio to radio
You can map the WAV file to a message button in N1MM or use an external audio interface.  
Like this in the message editor:  
F2 Exch,\report_nr.wav  
And with callsign_nr_tts.py and callsign_slownr_tts.py you have these two additional wav files:  
F5 His Call,\callsign.wav  
F6 NR,\nr.wav  


Here’s a copy-paste **cookbook** you can drop into your repo’s README. It’s the exact flow we refined together, kept simple and robust.

---

# Piper “your personal contest voice” – end-to-end cookbook

If you want the Piper ONNX model to have your own voice this walks you from **recordings → trained Piper voice** using RunPod and the `ifansnek/piper-train-docker:latest` image.

---

## 1) Record + prepare locally

**Format:** mono WAV, 22050 Hz, PCM-16.

## 🎙️ Recording Setup Instructions

Follow these steps to test your microphone and begin recording using the provided scripts.

### 1. ✅ Test Your Microphone
Run the `mic_test.py` script to ensure your microphone is working correctly.

### 2. 📁 Prepare Your Environment
Copy the `metadata.csv` and `prompts.csv` files into the same directory as `record_simple.py`.

### 3. 🔴 Start Recording
Execute the `record_simple.py` script to begin recording.

- You can stop recording at any time.
- When you restart the script, it will automatically resume from where you left off.
- The next unfinished line from `metadata.csv` will be prompted for recording.

  Your working folder should end up like:
  
```
dataset/
  wavs/                 # your .wav files
  metadata.csv          # lines: wavs/<file>.wav|transcript
```

### For best on-air clarity, you need to   add a tiny head-silence to each clip to eliminate the little “khi/thi” at the start of synth.

### (Recommended) Add 120–300 ms of head silence + 15 ms fade-in

Save `augment_head_silence.py` next to `dataset/` and run it once:

After this you have: dataset/wavs_aug/ + dataset/metadata_aug.csv

---

## 🛠️ 2) Prepare and Upload to RunPod (Staging Pod)

Before uploading, follow these cleanup steps:

1. **📦 Backup Your Audio Files**
   - Open File Explorer and navigate to `dataset\wavs_aug\`.
   - Select all `.wav` files, right-click, and choose **Send to > Compressed (zipped) folder**.
   - Name the archive something like `wavs_backup.zip` and store it safely.

   Alternatively, you can copy the files to a separate backup folder manually.

2. **🧹 Clean Up File and Directory Names**
   - Rename the folder `wavs_aug` to `wavs`:
     - Right-click the folder > **Rename** > type `wavs`.
   - Rename the file `metadata_aug.csv` to `metadata.csv`:
     - Right-click the file > **Rename** > type `metadata.csv`.
   - To remove `_aug` from all `.wav` filenames inside `dataset\wavs`, you can use a PowerShell command:
     ```powershell
     Get-ChildI

---

## 3) Upload to RunPod.io (staging pod)

* Create a **Network Volume** (e.g., 40 GB).
* Launch a temporary pod just to transfer files:

  * Image: **RunPod PyTorch 2.8.0**
  * GPU: **NVIDIA L4** (any CUDA GPU is fine)
  * Mount the network volume at `/dataset`.  
 
Here is a short video demonstrating the process of launching a network storage with a temporary pod (for transferring files), terminating the pod, and then deploying a new pod with the same storage for training:  
👉 [Deploying RunPod for Piper voice model training](https://youtu.be/msE6hX_bocw?si=Ea2aIbn19x6Z7ljj)


I found it easiest to use `runpodctl` to copy the local `dataset/` to the runpod volume:

> ```bash
> runpodctl send "c:\piper\dataset\wavs"
> runpodctl send "c:\piper\dataset\metadata.csv"
> ```
got to runpod's web terminal in /dataset direcrtory and type
> ```bash
> runpodctl receive xyz(=whatever the runpodctl asked you to type)
> ```


> **Note:** some `runpodctl` versions nest the uploaded folder (e.g. `/dataset/dataset/...`).
> Inside the pod you can flatten it:
>
> ```bash
> cd /dataset && rsync -a dataset/ ./ && rm -rf dataset
> ```

Verify:

```bash
ls -R /dataset | head
```

Terminate this staging pod.

---

## 4) Launch the **training** pod

From your **Network Volume** page → “Deploy Pod with Volume”.

* **Docker image:** `ifansnek/piper-train-docker:latest`
* **Volume Mount Path:** `/dataset`
* **Expose HTTP Port:** `6006` (TensorBoard)
* **Environment variables:**

  ```
  CHECKPOINT=en/en_US/ryan/medium/epoch=4641-step=3104302.ckpt
  QUALITY=medium
  TRAIN_ARGS=--batch-size 32 --validation-split 0.02 --num-test-examples 0 --checkpoint-epochs 50 --default_root_dir /cache
  ```

  (If VRAM is tight, use `--batch-size 16`.)

> **Do not set a Start Command.** The image autostarts.

### Make outputs persistent (do this once per new pod)

As soon as the pod is up, open its Terminal and run:

```bash
# stop the autostart briefly so /cache isn't busy
pkill -f piper_train || true
sleep 2

# persist logs/checkpoints on the mounted volume
mkdir -p /dataset/cache
rm -rf /cache && ln -sfn /dataset/cache /cache
mkdir -p /cache/cache

# restart the pod so training restarts with the persistent /cache
```

> After the restart, the container will auto-preprocess (CPU heavy), then train (GPU).
> Preprocess may peg CPU for a while; that’s normal.

---

## 5) Monitor training

Open the pod’s **6006** link → **Scalars**.

* If `TRAIN_ARGS` took effect, you’ll see **`val/*`** metrics. Filter tags with `^val/` and watch `val/loss_gen_all` trend down/flatten.
* If there are no `val/*` tags, filter `loss_` and watch `loss_gen_all`. When it flattens, export a checkpoint and listen.

Quick terminal helpers:

```bash
# newest checkpoints as they arrive
ls -1t /cache/lightning_logs/version_*/checkpoints/*.ckpt | head

# (optional) if TB didn’t start, launch it yourself:
tensorboard --logdir /cache/lightning_logs --bind_all --port 6006 >/tmp/tb.log 2>&1 &
```

---

## 6) Export ONNX (you can do this while it trains)

```bash
LATEST=$(ls -1t /cache/lightning_logs/version_*/checkpoints/*.ckpt | head -n 1)
OUT="/dataset/export_$(date +%Y%m%d_%H%M%S)"; mkdir -p "$OUT"
python3 -m piper_train.export_onnx "$LATEST" "$OUT/voice.onnx"
ls -lh "$OUT"
```

Download with `runpodctl` (or copy to your S3-compatible storage if you use one):

---

## 7) Use the model on Windows

Place your **`voice.onnx`** next to the **Ryan medium JSON** (download from Hugging Face) and synthesize:

```powershell
.\piper.exe -m .\voice.onnx -c .\en_US-ryan-medium.onnx.json -f out.wav `
  -t "kilo lima seven radio hotel five nine zero one two" `
  --noise_scale 0.40 --noise_w 0.55 --length_scale 0.96
```

> Keep call sign + report as one sentence (no punctuation) to preserve flow.

---

## 8) Troubleshooting (fast fixes)

* **6006 not available, CPU 100%:** preprocessing is running. It completes, then training (GPU) starts and TB appears.
* **Checkpoints disappear after reboot:** you forgot to persist `/cache`. Run:

  ```bash
  pkill -f piper_train || true
  mkdir -p /dataset/cache
  rm -rf /cache && ln -sfn /dataset/cache /cache
  restart the pod
  ```
* **Thread error (`pthread_create failed`) during preprocess:**
  Stop the trainer, then rebuild the cache with fewer workers:

  ```bash
  export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
  rm -f /cache/dataset.jsonl && rm -rf /cache/cache/*
  python3 -m piper_train.preprocess \
    --language en-us --input-dir /dataset --output-dir /cache \
    --dataset-format ljspeech --dataset-name metadata_lj.csv \
    --single-speaker --sample-rate 22050 --cache-dir /cache/cache --max-workers 1
  restart the pod
  ```

  (To make `metadata_lj.csv` from your `metadata.csv`, see the snippet below.)
* **`EOFError: Ran out of input` while training:** a corrupt spec file from an interrupted preprocess. Wipe cache (`/cache/dataset.jsonl` and `/cache/cache/*`), rebuild preprocess (as above), then restart.
* **No `val/*` curves:** the very first autostart may ignore `TRAIN_ARGS`. You can still watch `loss_gen_all`. To force validation in a new run, stop, clear `/cache/lightning_logs`, ensure envs are set, and let it autostart again.

---

## (Appendix) Convert to LJSpeech metadata if needed

Some tools prefer `id|text` (LJSpeech). This creates `metadata_lj.csv` from your existing `metadata.csv`:

```bash
python - <<'PY'
import os
inp="dataset/metadata.csv"; out="dataset/metadata_lj.csv"; n=0
with open(inp,"r",encoding="utf-8") as f, open(out,"w",encoding="utf-8") as g:
  for line in f:
    if "|" not in line: continue
    left,text = line.strip().split("|",1)
    base = os.path.splitext(os.path.basename(left))[0]
    g.write(f"{base}|{text.strip()}\n"); n+=1
print(f"Wrote {out} with {n} lines")
PY
```

---

### Credits / Notes

* Base checkpoint: **`en/en_US/ryan/medium/epoch=4641-step=3104302.ckpt`** (great English co-articulation for small sets).
* The head-silence augmentation is what eliminates the tiny onset artifact on contest phrases without adding any runtime delay.
* Always persist `/cache` to your mounted volume before training so logs & checkpoints survive restarts.



