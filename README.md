# N1MM with Piper TTS for AI generated messages

N1MM [latest version](https://n1mmwp.hamdocs.com/) supports now piper TTS natively. 

## Piper “your personal contest voice” – end-to-end cookbook

If you want the Piper ONNX model to have your own voice this walks you from **recordings → trained Piper voice** 

You will need some knowledge of Linux concepts and use of the Linux command line. There are many sources on the internet to learn this. In addtion the use of AI, such as Chatgpt, can be very helpful in answering questions.

---
For recording your speech samples, you can use either Windows or Linux.\
Most Linux distributions have the tools needed, already installed. If you are using Windows, you will need to set up your computer to work with Python files. 

For Windows:\
Download and install python for windows https://www.python.org/ . When you run the installer, watch for the option to add python to the path or enviroment. 

For both Linux and Windows, create a folder (directory) to work in, such as C:\Ham\PiperModel.

Download the *csv and *py files from Kari's GitHub location:\
https://github.com/oh2xx/n1mm-callsign-tts/blob/main/README.md#piper-your-personal-contest-voice--end-to-end-cookbook
and copy them to your working folder (i.e. C:\Ham\PiperModel ).

More special instructions for Windows:

Open a PowerShell window (a cmd window should also work). It doesn't need to be run as as Administrator.\
cd to the directory with the *.py files and enter these commands:
```
python -m venv myenv
myenv\Scripts\activate
python -m pip install sounddevice
pip install soundfile
```

Run the mic_test with:
python mic_test.py
If it works, you are ready to record.

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

---

## 🛠️ 2) Prepare for use of RunPod

In the next steps, you will be using a powerful remote server to create a voice model file from the wav files you previously recorded.

A few definitions:\
A "Pod" is where programs execute on the remote server. Think of the Pod as a powerful computer dedicated to running your application. It may actually be part of a server farm, with many simultaneous users, that you don't know or care about.

A "Docker Image" is a complete package consisting of everthing needed to run your application on your Pod. This may include the operating system, and application software, and needed files. A Docker Image can be very large in size.

"RunPod.io" is a web site that allows you to reserve a Pod, store your files that are needed by the Docker image, set up your Pod, monitor the execution of your application, etc.

Using RunPod.io does incur costs to you, the user. You pay for storage of your files, and for time that the Pod is deployed (i.e. the Pod is running). Here's the costs I incurred to create my voice model:\
US $2.80 per month for storing files, including the wav files.\
US $0.39 per hour for Pod deployment.\
The total for creating my voice model was US $1.55, which included many missteps in getting the Pod configured correctly.

Create an account on RunPod.io and fund it with the minimum amount of US $10.

Before uploading, follow these cleanup steps:

1. **📦 Backup Your Audio Files**
   - Open File Explorer and navigate to `dataset\wavs\`.
   - Select all `.wav` files, right-click, and choose **Send to > Compressed (zipped) folder**.
   - Name the archive something like `wavs_backup.zip` and store it safely.

   Alternatively, you can copy the files to a separate backup folder manually.

---

## 1) Upload to RunPod.io (staging pod)

The purpose of this staging pod is to upload your wav files to your network volume on RunPod.io. Install runpodctl on your local computer. Runpodctl is needed to transfer files between your local computer and the RunPod servers.

On Linux:
```
sudo snap install go
sudo snap install go --classic
go install github.com/runpod/runpodctl@latest
```

On Windows:\
Use chatgpt.com, entering the query: "installing runpodctl on windows". Chatgpt will give you detailed instructions.

Log into your RunPod.io account. 

Select Manage->Storage, then New Network Volume

* Create a **Network Volume** of 40 GB.
* Launch a temporary pod just to transfer files by selecting "Deploy Pod With Volume".
 
  * GPU: **NVIDIA Latest Gen L4** (any CUDA GPU is fine)\
    Select "Edit Template"  
  * Image: **RunPod PyTorch 2.8.0**
  * Volume Mount Path: `/dataset`.

Scroll down to the bottom, and select "Deploy On-Demand". This deploys (i.e. starts) your Pod. You will be charged for use of the Pod beginning now.\
Turn on "Enable Web Terminal", then select "Open Web Terminal". This will open a Linux-like Bash shell.  
When you are done, go back to the "My Pod" tab and select "Terminate". If you do not select Terminate, you will continue to be charged for Pod usage.
 
Here is a short video demonstrating the process of launching a network storage with a temporary pod (for transferring files), terminating the pod, and then deploying a new pod with the same storage for training:  
👉 [Deploying RunPod for Piper voice model training](https://www.youtube.com/watch?v=IowMcf1rIJ0)


From your local computer, use `runpodctl` to copy the local `dataset/` to the runpod volume:

> ```bash
> runpodctl send "c:\piper\dataset\wavs"
> runpodctl send "c:\piper\dataset\metadata.csv"
>
>  ```

Go back to your RunPod Linux bash tab:
> ```bash
> runpodctl receive xyz(=whatever the local runpodctl asked you to type)
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

This is where your voice model is created and "trained". From your RunPod.io **Network Volume** page → “Deploy Pod with Volume”.

* **Docker image:** `ifansnek/piper-train-docker:latest`
* **Volume Mount Path:** `/dataset`
* **Expose HTTP Ports:** `6006` (TensorBoard)
* **Environment variables:**

  ```
  CHECKPOINT=en/en_US/ryan/medium/epoch=4641-step=3104302.ckpt
  QUALITY=medium
  TRAIN_ARGS=--batch-size 32 --validation-split 0.02 --num-test-examples 0 --checkpoint-epochs 50 --default_root_dir /cache
  ```

  (If VRAM is tight, use `--batch-size 16`.)
> **Do not set a Start Command.** The image autostarts.
>
  Select "Set Overrides"\
  Select "Deploy On-Demand"

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
./start.sh
```

> After the restart, the container will auto-preprocess (CPU heavy), then train (GPU).
> Preprocess may peg CPU for a while; that’s normal.

---

## 5) Monitor training

Open Tensorboard at Port 6006->HTTP Services\
Select the **Scalars** tab.

* Watch `loss_gen_all`. When it flattens, export a checkpoint and listen.

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

```

### Credits / Notes

* Base checkpoint: **`en/en_US/ryan/medium/epoch=4641-step=3104302.ckpt`** (great English co-articulation for small sets).
* The head-silence augmentation is what eliminates the tiny onset artifact on contest phrases without adding any runtime delay.
* Always persist `/cache` to your mounted volume before training so logs & checkpoints survive restarts.


---

