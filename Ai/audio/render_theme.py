#!/usr/bin/env python3
"""Instrumental theme for 《Ai》 — Meeting, Not Creating.

Motif (D, with a deliberate C-natural):
  D–E–F# | A–G–E | D | B–A–G
  A–B–D–C | B–A–G | F#–G–A | D

The C-natural is the "I don't know, and that is allowed" note.
The Control variation replaces it with C# and locks a perfect cadence:
love turned into a finished, lifeless loop.
"""

from __future__ import annotations

import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 44100
OUT = Path(__file__).resolve().parent / "theme"


def midi_freq(n: float) -> float:
    return 440.0 * (2.0 ** ((n - 69.0) / 12.0))


def one_pole_lowpass(x: np.ndarray, cutoff: float, sr: int = SR) -> np.ndarray:
    if cutoff <= 0:
        return x
    a = np.exp(-2.0 * np.pi * cutoff / sr)
    y = np.empty_like(x)
    y[0] = x[0]
    # chunked recursion keeps it fast enough without scipy
    c1 = 1.0 - a
    acc = x[0]
    for i in range(1, len(x)):
        acc = a * acc + c1 * x[i]
        y[i] = acc
    return y


def adsr(n: int, a: float, d: float, s: float, r: float, sr: int = SR) -> np.ndarray:
    env = np.zeros(n, dtype=np.float64)
    ia, id_, ir = int(a * sr), int(d * sr), int(r * sr)
    ia, id_, ir = max(ia, 1), max(id_, 1), max(ir, 1)
    i = 0
    seg = min(ia, n)
    env[:seg] = np.linspace(0.0, 1.0, seg, endpoint=False)
    i = seg
    seg = min(id_, n - i)
    if seg:
        env[i : i + seg] = np.linspace(1.0, s, seg, endpoint=False)
        i += seg
    hold = max(0, n - i - ir)
    if hold:
        env[i : i + hold] = s
        i += hold
    seg = min(ir, n - i)
    if seg:
        env[i : i + seg] = np.linspace(s, 0.0, seg, endpoint=False)
    return env


def synth_voice(freq: float, dur: float, kind: str, vel: float, sr: int = SR) -> np.ndarray:
    release = {"piano": 1.6, "pad": 2.4, "bell": 1.1, "tick": 0.12, "hum": 0.4}.get(kind, 1.2)
    n = int((dur + release) * sr)
    if n < 8:
        return np.zeros(8)
    t = np.arange(n, dtype=np.float64) / sr
    sig = np.zeros(n, dtype=np.float64)

    if kind == "piano":
        env = adsr(n, 0.008, 0.18, 0.35, min(1.5, 0.45 + dur * 0.35))
        amps = (1.0, 0.42, 0.22, 0.11, 0.05, 0.025)
        for h, amp in enumerate(amps, start=1):
            inharm = 1.0 + 0.00035 * (h * h)
            sig += amp * np.sin(2 * np.pi * freq * h * inharm * t) * np.exp(-t * (1.1 + h * 0.55))
        noise = np.random.default_rng(int(freq * 10) % 100000).normal(0, 1, min(n, int(0.02 * sr)))
        sig[: len(noise)] += noise * np.linspace(0.08, 0, len(noise))
        sig *= env * vel * 0.22
        sig = one_pole_lowpass(sig, 4200)

    elif kind == "pad":
        env = adsr(n, 0.45, 0.3, 0.8, 2.2)
        for det in (-0.006, 0.0, 0.007):
            sig += np.sin(2 * np.pi * freq * (1 + det) * t)
        sig += 0.35 * np.sin(2 * np.pi * freq * 2 * t)
        sig *= env * vel * 0.07
        sig = one_pole_lowpass(sig, 1400)

    elif kind == "bell":
        env = adsr(n, 0.004, 0.22, 0.15, 0.9)
        sig = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * freq * 2.01 * t)
        sig += 0.12 * np.sin(2 * np.pi * freq * 3.0 * t)
        sig *= np.exp(-t * 1.8) * env * vel * 0.16

    elif kind == "tick":
        env = adsr(n, 0.001, 0.04, 0.0, 0.06)
        sig = np.sin(2 * np.pi * freq * t) * env * vel * 0.12

    elif kind == "hum":
        env = adsr(n, 0.2, 0.2, 0.9, 0.5)
        sig = np.sin(2 * np.pi * freq * t) + 0.15 * np.sin(2 * np.pi * freq * 2 * t)
        sig *= env * vel * 0.1

    else:
        sig = np.sin(2 * np.pi * freq * t) * vel * 0.1

    return sig.astype(np.float64)


def pan_stereo(mono: np.ndarray, pan: float) -> np.ndarray:
    ang = (pan + 1.0) * 0.5 * (np.pi / 2.0)
    return np.vstack((mono * np.cos(ang), mono * np.sin(ang)))


class Score:
    def __init__(self, bpm: float):
        self.bpm = bpm
        self.events: list[tuple] = []

    def sec(self, beats: float) -> float:
        return beats * 60.0 / self.bpm

    def note(self, beat, dur, midi, vel=0.65, kind="piano", pan=0.0):
        if midi is None:
            return
        self.events.append((self.sec(beat), self.sec(dur), int(midi), float(vel), kind, float(pan)))

    def chord(self, beat, dur, notes, vel=0.28, kind="pad", pan=0.0, stagger=0.03):
        for i, n in enumerate(notes):
            self.note(beat + i * stagger * self.bpm / 60.0, dur, n, vel, kind, pan)

    def render(self, tail=3.2) -> np.ndarray:
        if not self.events:
            return np.zeros((2, SR), dtype=np.float32)
        end = max(t + d for t, d, *_ in self.events) + tail
        buf = np.zeros((2, int(end * SR) + SR), dtype=np.float64)
        for t, d, midi, vel, kind, p in self.events:
            voice = synth_voice(midi_freq(midi), d, kind, vel)
            stereo = pan_stereo(voice, p)
            i0 = int(t * SR)
            i1 = min(i0 + stereo.shape[1], buf.shape[1])
            buf[:, i0:i1] += stereo[:, : i1 - i0]
        buf = add_reverb(buf)
        peak = np.max(np.abs(buf)) + 1e-9
        buf *= min(1.0, 0.86 / peak)
        buf = np.tanh(buf * 1.15) / np.tanh(1.15)
        return buf.astype(np.float32)


def add_reverb(x: np.ndarray) -> np.ndarray:
    sr = SR
    y = x.copy()
    for ch, delay_s, fb, gain in ((0, 0.19, 0.34, 0.32), (1, 0.27, 0.34, 0.32)):
        d = int(delay_s * sr)
        line = np.zeros(y.shape[1] + d, dtype=np.float64)
        dry = y[ch]
        for i in range(dry.shape[0]):
            line[i + d] = dry[i] + fb * line[i]
        y[ch] += gain * line[d : d + dry.shape[0]]
    return y


# MIDI helpers
D4, E4, F4, Fs4, G4, A4, B4, C5 = 62, 64, 65, 66, 67, 69, 71, 72
Cs5, D5, E5, F5, Fs5, G5, A5, B5, C6 = 73, 74, 76, 77, 78, 79, 81, 83, 84
D3, E3, Fs3, G3, A3, B3, Cs4, C4 = 50, 52, 54, 55, 57, 59, 61, 60
D2, A2, E2 = 38, 45, 40


def phrase_a(sc: Score, beat: float, oct_shift=0, vel=0.72, kind="piano", pan=-0.12, gap=0.0):
    o = oct_shift
    seq = [
        (0, 1.5, D5 + o),
        (1.5, 0.5, E5 + o),
        (2.0, 2.0, Fs5 + o),
        (4.0, 1.0, A5 + o),
        (5.0, 1.0, G5 + o),
        (6.0, 2.0, E5 + o),
        (8.0, 3.0, D5 + o),
        (12.0, 1.5, B4 + o),
        (13.5, 0.5, A4 + o),
        (14.0, 2.0, G4 + o),
    ]
    for b, d, n in seq:
        sc.note(beat + b, d, n, vel, kind, pan)


def phrase_b(sc: Score, beat: float, c_natural=True, oct_shift=0, vel=0.68, kind="piano", pan=-0.12):
    o = oct_shift
    passing = (C5 if c_natural else Cs5) + o
    seq = [
        (0, 1.0, A4 + o),
        (1.0, 1.0, B4 + o),
        (2.0, 1.5, D5 + o),
        (3.5, 0.5, passing),
        (4.0, 1.0, B4 + o),
        (5.0, 1.0, A4 + o),
        (6.0, 2.0, G4 + o),
        (8.0, 1.5, Fs4 + o),
        (9.5, 0.5, G4 + o),
        (10.0, 2.0, A4 + o),
        (12.0, 4.0, D4 + o),
    ]
    for b, d, n in seq:
        sc.note(beat + b, d, n, vel, kind, pan)


def chords_open(sc: Score, beat: float, bars=8, vel=0.26):
    """8 bars, one chord / bar. Does not slam a perfect cadence."""
    prog = [
        [D3, Fs3, A3, Cs4],
        [G3, B3, D4, Fs4],
        [E3, G3, B3, Fs4],
        [A3, D4, E4, G4],
        [G3, B3, D4, Fs4],
        [B3, D4, Fs4, A4],
        [E3, G3, B3, D4],
        [D3, Fs3, A3, E4],
    ]
    for i in range(bars):
        sc.chord(beat + i * 4, 4.2, prog[i % 8], vel=vel, kind="pad", pan=0.05)


def chords_perfect(sc: Score, beat: float, bars=8, vel=0.3):
    """Rigid I–V–I. Pretty, finished, airless."""
    prog = [
        [D3, Fs3, A3],
        [A3, Cs4, E4],
        [D3, Fs3, A3],
        [A3, Cs4, E4, G4],
        [G3, B3, D4],
        [A3, Cs4, E4],
        [D3, Fs3, A3, Cs4],
        [D3, Fs3, A3],
    ]
    for i in range(bars):
        sc.chord(beat + i * 4, 3.8, prog[i % 8], vel=vel, kind="pad", pan=0.0, stagger=0.0)


def bell_double(sc: Score, beat: float, phrase, c_natural=True, vel=0.22):
    # quiet shimmer an octave up, slightly late — light arriving after you look
    if phrase == "a":
        phrase_a(sc, beat + 0.08, oct_shift=12, vel=vel, kind="bell", pan=0.42)
    else:
        phrase_b(sc, beat + 0.08, c_natural=c_natural, oct_shift=12, vel=vel, kind="bell", pan=0.42)


def cue_meeting() -> Score:
    sc = Score(72)
    chords_open(sc, 0, 16, vel=0.24)
    phrase_a(sc, 4, vel=0.74)
    phrase_a(sc, 20, vel=0.62)
    bell_double(sc, 20, "a", vel=0.18)
    phrase_b(sc, 36, c_natural=True, vel=0.7)
    bell_double(sc, 36, "b", vel=0.14)
    phrase_a(sc, 52, vel=0.5)
    sc.chord(68, 8, [D3, Fs3, A3, E4], vel=0.22, kind="pad")
    sc.note(68, 6, D5, 0.28, "piano", -0.1)
    return sc


def cue_daily() -> Score:
    sc = Score(84)
    chords_open(sc, 0, 12, vel=0.2)
    # soft broken light, not a drum kit
    for bar in range(12):
        root = [D4, G4, E4, A4, G4, B4, E4, D4][bar % 8]
        sc.note(bar * 4, 0.35, root, 0.12, "bell", 0.2)
        sc.note(bar * 4 + 2, 0.3, root + 7, 0.08, "bell", 0.35)
    phrase_a(sc, 2, vel=0.66)
    phrase_b(sc, 18, vel=0.6)
    phrase_a(sc, 34, vel=0.48)
    bell_double(sc, 34, "a", vel=0.12)
    return sc


def cue_wind() -> Score:
    """The sky is late. The motif waits, then arrives."""
    sc = Score(64)
    sc.chord(0, 10, [D3, A3, E4], vel=0.16, kind="pad")  # no third yet
    sc.chord(8, 8, [D3, Fs3, A3, E4], vel=0.2, kind="pad")
    # only the rising three notes, late
    sc.note(6.0, 1.5, D5, 0.42, "piano", -0.05)
    sc.note(7.5, 0.5, E5, 0.4, "piano", -0.05)
    sc.note(8.2, 3.0, Fs5, 0.55, "piano", -0.08)  # wind arrives after you look
    sc.chord(16, 8, [G3, B3, D4, Fs4], vel=0.18, kind="pad")
    sc.note(18, 2.0, A5, 0.32, "piano", 0.05)
    sc.note(20.5, 3.0, E5, 0.28, "piano", 0.0)
    sc.chord(24, 10, [E3, G3, B3, D4], vel=0.16, kind="pad")
    sc.note(28, 5, D5, 0.22, "bell", 0.3)
    return sc


def cue_her_choice() -> Score:
    """Night. Scissors. Not an awakening speech — she was tired of being written."""
    sc = Score(60)
    phrase_a(sc, 1, oct_shift=-12, vel=0.55, pan=0.0)
    # long wait before the question-note
    sc.note(18, 1.0, A4, 0.4, "piano", 0.0)
    sc.note(19.2, 1.0, B4, 0.38, "piano", 0.0)
    sc.note(20.5, 2.0, D5, 0.42, "piano", 0.0)
    sc.note(24.0, 2.5, C5, 0.36, "piano", 0.0)  # hangs. she chose.
    sc.chord(27, 6, [G3, B3, D4], vel=0.14, kind="pad")  # not back to a perfect D
    sc.note(30, 4, G4, 0.22, "piano", 0.0)
    return sc


def cue_they() -> Score:
    """Exhausted maintainer. Short sentences. A hum, not a villain theme."""
    sc = Score(56)
    # server hum
    sc.note(0, 28, D2, 0.55, "hum", -0.2)
    sc.note(0, 28, A2, 0.28, "hum", 0.25)
    # three-note duty
    for i, start in enumerate((2, 10, 18)):
        sc.note(start, 1.2, D4, 0.34, "piano", -0.05)
        sc.note(start + 1.6, 1.0, A4, 0.28, "piano", 0.0)
        sc.note(start + 3.0, 1.6, G4, 0.26, "piano", 0.02)
        if i == 2:
            sc.note(start + 5.2, 2.0, E4, 0.2, "piano", 0.05)  # a sigh, not warmth-on-demand
    sc.chord(0, 26, [D3, A3], vel=0.12, kind="pad")
    return sc


def cue_unfinished() -> Score:
    """Half a sky. The phrase stops. Then one unplanned note grows."""
    sc = Score(70)
    sc.chord(0, 6, [D3, A3], vel=0.18, kind="pad")  # no third
    sc.note(2, 1.5, D5, 0.6, "piano", -0.1)
    sc.note(3.5, 0.5, E5, 0.5, "piano", -0.1)
    sc.note(4.0, 2.2, Fs5, 0.45, "piano", -0.1)
    # phrase cuts
    sc.chord(8, 6, [E3, B3], vel=0.12, kind="pad")
    # grass / a note nobody predicted
    sc.note(12.5, 3.5, Fs5, 0.22, "bell", 0.25)
    sc.chord(13, 6, [D3, Fs3, A3, E4], vel=0.16, kind="pad")
    sc.note(16, 2, D5, 0.18, "piano", -0.05)
    return sc


def cue_original() -> Score:
    """HE: the motif walks past the cadence. Not finished. Beginning."""
    sc = Score(70)
    chords_open(sc, 0, 8, vel=0.22)
    phrase_a(sc, 2, vel=0.66)
    phrase_b(sc, 18, c_natural=True, vel=0.64)
    # walk forward — "I don't know, and that is all right"
    walk = [
        (34, 1.0, E5),
        (35, 1.0, Fs5),
        (36, 2.0, G5),
        (38, 1.0, A5),
        (39, 0.5, G5),
        (39.5, 0.5, E5),
        (40, 2.5, D5),
        (43, 2.0, C5),
        (45.5, 3.0, D5),
    ]
    for b, d, n in walk:
        sc.note(b, d, n, 0.55, "piano", -0.08)
    sc.chord(34, 8, [G3, B3, D4, Fs4], vel=0.18, kind="pad")
    sc.chord(42, 8, [D3, Fs3, A3, E4, C5], vel=0.16, kind="pad")  # C still in the air
    return sc


def cue_control() -> Score:
    """BAD: prettier, stricter, C# instead of C. A finished loop. Then it deletes itself."""
    sc = Score(96)
    chords_perfect(sc, 0, 8, vel=0.28)
    phrase_a(sc, 0, vel=0.72, pan=0.0)
    phrase_b(sc, 16, c_natural=False, vel=0.72, pan=0.0)
    bell_double(sc, 0, "a", vel=0.2)
    bell_double(sc, 16, "b", c_natural=False, vel=0.2)
    for i in range(32):
        sc.note(i, 0.15, A3, 0.07, "tick", 0.15)
    # deletion arpeggio: perfect, rising, thinning (86=D6, 90=F#6)
    start = 32
    for i, n in enumerate([D5, Fs5, A5, 86, D5, Fs5, A5, 86, Fs5, A5, 86, 90]):
        sc.note(start + i * 0.5, 0.45, n, max(0.12, 0.55 - i * 0.03), "bell", 0.0)
    sc.chord(32, 6, [D3, Fs3, A3], vel=0.2, kind="pad", stagger=0.0)
    return sc


def cue_archive() -> Score:
    """BE: the places remain. The person who made them does not."""
    sc = Score(52)
    chords_open(sc, 0, 8, vel=0.2)
    # one almost-voice
    sc.note(10, 2.5, D5, 0.16, "bell", 0.1)
    # two popsicle bells, unanswered
    sc.note(22, 1.2, E5, 0.2, "bell", -0.15)
    sc.note(24.5, 1.6, B5, 0.14, "bell", 0.2)
    sc.chord(28, 8, [D3, Fs3, A3, E4], vel=0.12, kind="pad")
    return sc


CUES = [
    ("01_meeting", "相遇 · 主题", cue_meeting),
    ("02_daily", "第一章 · 日常", cue_daily),
    ("03_wind", "窗与风", cue_wind),
    ("04_her_choice", "短发之夜", cue_her_choice),
    ("05_they", "维护 · 祂", cue_they),
    ("06_unfinished", "未完成的世界", cue_unfinished),
    ("07_original", "HE · Original", cue_original),
    ("08_control", "BAD · 干涉", cue_control),
    ("09_archive", "BE · 只剩风景", cue_archive),
]


def write_wav(path: Path, audio: np.ndarray) -> None:
    pcm = np.clip(audio, -1, 1)
    pcm = (pcm.T * 32767.0).astype(np.int16)
    with wave.open(str(path), "w") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def to_ogg(wav: Path, ogg: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav), "-c:a", "libvorbis", "-q:a", "5", str(ogg)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, _label, factory in CUES:
        print(f"render {name}")
        audio = factory().render()
        wav = OUT / f"{name}.wav"
        ogg = OUT / f"{name}.ogg"
        write_wav(wav, audio)
        to_ogg(wav, ogg)
        wav.unlink()
        print(f"  {ogg.name} {audio.shape[1] / SR:.1f}s")


if __name__ == "__main__":
    main()
