import socket
import xml.etree.ElementTree as ET
import subprocess
import re

UDP_IP = "127.0.0.1"
UDP_PORT = 12061  # Custom port to avoid conflicts with N1MMClubLogGateway

# NATO phonetic alphabet mapping
PHONETICS = {
    'A': 'Alpha', 'B': 'Bravo', 'C': 'Charlie', 'D': 'Delta', 'E': 'Echo',
    'F': 'Foxtrot', 'G': 'Golf', 'H': 'Hotel', 'I': 'India', 'J': 'Juliett',
    'K': 'Kilo', 'L': 'Lima', 'M': 'Mike', 'N': 'November', 'O': 'Oscar',
    'P': 'Papa', 'Q': 'Quebec', 'R': 'Romeo', 'S': 'Sierra', 'T': 'Tango',
    'U': 'Uniform', 'V': 'Victor', 'W': 'Whiskey', 'X': 'X-ray', 'Y': 'Yankee', 'Z': 'Zulu',
    '0': 'Zero', '1': 'One', '2': 'Two', '3': 'Three', '4': 'Four',
    '5': 'Five', '6': 'Six', '7': 'Seven', '8': 'Eight', '9': 'Nine', '/': 'Portable'
}

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print(f"Listening for N1MM UDP packets on {UDP_IP}:{UDP_PORT}...")

def callsign_to_phonetics(callsign):
    return ' '.join(PHONETICS.get(ch.upper(), ch) for ch in callsign)

while True:
    data, addr = sock.recvfrom(4096)
    try:
        xml_data = ET.fromstring(data.decode('utf-8'))
    except ET.ParseError:
        continue

    callsign_elem = xml_data.find('call')
    if callsign_elem is None or not callsign_elem.text:
        continue

    callsign = callsign_elem.text.strip()
    if not re.match(r'^[A-Za-z0-9/]+$', callsign):
        continue

    phonetic_str = callsign_to_phonetics(callsign)
    print(f"Received call: {callsign} -> {phonetic_str}")

    wav_file = "callsign.wav"
    subprocess.run([
        "piper",
        "--model", "en_US-amy-medium.onnx",
        "--output_file", wav_file
    ], input=phonetic_str.encode('utf-8'))

    print(f"Generated {wav_file} with Piper.")
