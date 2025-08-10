import socket
import xml.etree.ElementTree as ET
import subprocess
import os

# === CONFIG ===
UDP_IP = ""
UDP_PORT = 12061  # N1MM second broadcast port

# Output WAV paths
N1MM_WAV_PATH_CALL = r"C:\Users\kleht\Documents\N1MM Logger+\Wav\callsign.wav"
N1MM_WAV_PATH_REPORT = r"C:\Users\kleht\Documents\N1MM Logger+\Wav\report_nr.wav"
N1MM_WAV_PATH_NR = r"C:\Users\kleht\Documents\N1MM Logger+\Wav\nr.wav"

PIPER_PATH = r"C:\piper\piper.exe"
VOICE_MODEL = r"C:\piper\models\voice-en-us-ryan-low\en-us-ryan-low.onnx"

# NATO phonetic map
phonetic_map = {
    'A': 'Alpha', 'B': 'Bravo', 'C': 'Charlie', 'D': 'Delta', 'E': 'Echo',
    'F': 'Foxtrot', 'G': 'Golf', 'H': 'Hotel', 'I': 'India', 'J': 'Juliett',
    'K': 'Kilo', 'L': 'Lima', 'M': 'Mike', 'N': 'November', 'O': 'Oscar',
    'P': 'Papa', 'Q': 'Quebec', 'R': 'Romeo', 'S': 'Sierra', 'T': 'Tango',
    'U': 'Uniform', 'V': 'Victor', 'W': 'Whiskey', 'X': 'X-ray', 'Y': 'Yankee', 'Z': 'Zulu',
    '0': 'Zero', '1': 'One', '2': 'Two', '3': 'Three', '4': 'Four',
    '5': 'Five', '6': 'Six', '7': 'Seven', '8': 'Eight', '9': 'Nine', '/': 'Portable'
}

# Cache variables
last_callsign = None
last_sntnr = None

def to_nato(call):
    return ' '.join(phonetic_map.get(ch.upper(), ch) for ch in call)

def format_sntnr(num_str):
    """Format number with leading zeros: 00# if <10, 0# if <100."""
    try:
        num = int(num_str)
    except (TypeError, ValueError):
        return None
    if num < 10:
        return f"00{num}"
    elif num < 100:
        return f"0{num}"
    else:
        return str(num)

def generate_tts(text, filename):
    try:
        cmd = [
            PIPER_PATH,
            "--model", VOICE_MODEL,
            "--output_file", filename
        ]
        subprocess.run(cmd, input=text.encode('utf-8'), check=True)
        print(f"[TTS] Saved to {filename}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Piper TTS failed: {e}")

# === SETUP SOCKET ===
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print(f"[INFO] Listening for N1MM LookupInfo packets on port {UDP_PORT}...")

while True:
    data, addr = sock.recvfrom(4096)
    xml_data = data.decode('utf-8', errors='ignore')

    if "<lookupinfo" in xml_data.lower():
        try:
            root = ET.fromstring(xml_data)

            # Callsign handling
            callsign = root.findtext(".//call") or root.findtext(".//callsign")
            if callsign:
                callsign = callsign.strip().upper()
                if callsign != last_callsign:
                    phonetics = to_nato(callsign)
                    print(f"[RX] Callsign: {callsign} → {phonetics}")
                    generate_tts(phonetics, N1MM_WAV_PATH_CALL)
                    last_callsign = callsign
                else:
                    print(f"[SKIP] Same callsign: {callsign}")

            # Sent number handling
            sntnr_val = root.findtext(".//sntnr")
            if sntnr_val:
                formatted_nr = format_sntnr(sntnr_val)
                if formatted_nr and formatted_nr != last_sntnr:
                    report_text = f"you are five nine {formatted_nr}"
                    print(f"[RX] Sent number: {sntnr_val} → formatted: {formatted_nr}")
                    generate_tts(report_text, N1MM_WAV_PATH_REPORT)
                    generate_tts(formatted_nr, N1MM_WAV_PATH_NR)
                    last_sntnr = formatted_nr
                elif formatted_nr == last_sntnr:
                    print(f"[SKIP] Same sent number: {formatted_nr}")

        except ET.ParseError:
            pass
