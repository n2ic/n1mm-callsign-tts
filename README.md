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

---

## 4. Running the script
```bash
python callsign_tts.py
```
When N1MM receives a callsign, a `callsign.wav` will be generated in the current folder.

---

## 5. Sending audio to radio
You can map the WAV file to a message button in N1MM or use an external audio interface.  
Like this in the message editor:  
F5 His Call,\callsign.wav
