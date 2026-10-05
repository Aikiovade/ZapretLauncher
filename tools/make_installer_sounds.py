"""A9/I3: генерация звуков установщика (stdlib, без зависимостей).

Запуск: python tools/make_installer_sounds.py
Результат:
  installer/sound_intro.wav  (~3.2 c: whoosh + аккорд + искры) — играется в начале мастера
  installer/sound_done.wav   (~1.8 c: арпеджио) — играется на финальной странице
"""
import math
import os
import random
import struct
import sys
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "installer")
RATE = 44100


def _write_wav(path, samples):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        frames = bytearray()
        for s in samples:
            v = max(-1.0, min(1.0, s))
            frames += struct.pack("<h", int(v * 32000))
        w.writeframes(bytes(frames))


def _envelope(t, start, attack, hold, release):
    if t < start:
        return 0.0
    dt = t - start
    if dt < attack:
        return dt / attack
    if dt < attack + hold:
        return 1.0
    dt -= attack + hold
    if dt < release:
        return max(0.0, 1.0 - dt / release)
    return 0.0


def make_intro(path):
    duration = 3.2
    n = int(RATE * duration)
    samples = []
    rnd = random.Random(17)
    noise_state = 0.0
    for i in range(n):
        t = i / RATE
        value = 0.0

        # whoosh: шум через простой low-pass + восходящий свип
        noise = rnd.uniform(-1.0, 1.0)
        noise_state = noise_state * 0.86 + noise * 0.14
        sweep_freq = 180 + 900 * (t / 1.4) if t < 1.4 else 1080
        sweep = math.sin(2 * math.pi * sweep_freq * t) * 0.22
        value += (noise_state * 0.5 + sweep) * _envelope(t, 0.0, 0.25, 0.7, 0.9)

        # аккорд C5-E5-G5
        for k, freq in enumerate((523.25, 659.25, 783.99)):
            value += 0.16 * math.sin(2 * math.pi * freq * t) * _envelope(t, 0.85 + k * 0.05, 0.05, 0.7, 1.3)

        # искры (высокие ноты)
        for k, freq in enumerate((1046.5, 1318.5, 1568.0)):
            value += 0.08 * math.sin(2 * math.pi * freq * t) * _envelope(t, 1.9 + k * 0.12, 0.02, 0.15, 0.7)

        value *= 0.9 * _envelope(t, 0.0, 0.05, duration - 0.6, 0.55)
        samples.append(value)
    _write_wav(path, samples)
    return path


def make_done(path):
    duration = 1.8
    n = int(RATE * duration)
    notes = (523.25, 659.25, 783.99, 1046.5)
    samples = []
    for i in range(n):
        t = i / RATE
        value = 0.0
        for k, freq in enumerate(notes):
            value += 0.2 * math.sin(2 * math.pi * freq * t) * _envelope(t, k * 0.12, 0.02, 0.12, 0.9)
        value += 0.08 * math.sin(2 * math.pi * 2093.0 * t) * _envelope(t, 0.55, 0.02, 0.05, 0.8)
        value *= _envelope(t, 0.0, 0.03, duration - 0.5, 0.45)
        samples.append(value)
    _write_wav(path, samples)
    return path


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("OK:", make_intro(os.path.join(OUT_DIR, "sound_intro.wav")))
    print("OK:", make_done(os.path.join(OUT_DIR, "sound_done.wav")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
