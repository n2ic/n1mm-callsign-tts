import sounddevice as sd
import soundfile as sf

SAMPLE_RATE = 22050  # matches Piper's preferred rate
DURATION = 3         # seconds to record
TEST_FILE = "mic_test.wav"

print("🎙  Microphone test: Recording will start in 2 seconds...")
sd.sleep(2000)

print("Recording...")
audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="float32")
sd.wait()
print("Recording finished.")

# Save file
sf.write(TEST_FILE, audio, SAMPLE_RATE, subtype="PCM_16")
print(f"Saved recording to {TEST_FILE}")

# Play it back
print("Playing back...")
sd.play(audio, SAMPLE_RATE)
sd.wait()
print("Done.")
