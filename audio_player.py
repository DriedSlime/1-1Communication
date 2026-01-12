# audio_player.py
import pyaudio

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

class AudioPlayer:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.stream = None

    def start(self):
        if self.stream:
            return
        self.stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            output=True,
            frames_per_buffer=CHUNK
        )

    def play(self, data: bytes):
        if not self.stream:
            self.start()
        try:
            self.stream.write(data)
        except:
            pass

    def stop(self):
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
            self.stream = None

    def __del__(self):
        try:
            self.audio.terminate()
        except:
            pass
