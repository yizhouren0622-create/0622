#!/usr/bin/env python3
"""Compose and sing 《灯下》 in the Xiaoyi voice.

The poem is set as a short night song in C major, at 84 BPM:
intro, two verses, a wind section, a chorus, a walking bridge,
a quiet final refrain, and a music-box outro.

The vocal keeps Xiaoyi's timbre (zh-CN-XiaoyiNeural, pitch +14 Hz).
Each syllable is centered on a melody note, then held like a sung vowel.

Requires ffmpeg, fluidsynth, FluidR3_GM, edge-tts, librosa, and pyworld.
Output: audio/灯下-歌曲.mp3
"""

from __future__ import annotations

import asyncio
import struct
import subprocess
import tempfile
import wave
from pathlib import Path

import librosa
import numpy as np
import pyworld as pw
import soundfile as sf
from edge_tts import Communicate
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "audio" / "灯下-歌曲.mp3"
VOICE = "zh-CN-XiaoyiNeural"
TTS_RATE = "-6%"
TTS_PITCH = "+14Hz"
BPM = 84
SR = 44100
VOCAL_SR = 24000
BEAT = 60.0 / BPM
SF2 = Path("/usr/share/sounds/sf2/FluidR3_GM.sf2")

NOTE_HZ = {
    "C4": 261.63,
    "D4": 293.66,
    "E4": 329.63,
    "F4": 349.23,
    "G4": 392.00,
    "A4": 440.00,
    "B4": 493.88,
    "C5": 523.25,
    "D5": 587.33,
    "E5": 659.25,
}


def midi_of(name: str) -> int:
    table = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    return 12 * (int(name[-1]) + 1) + table[name[:-1]]


# (start_beat, slot_beats, lyric, melody, gain)
# melody entries are (note, beats). Slot is the musical room for the line.
VOCALS: list[tuple[float, float, str, list[tuple[str, float]], float]] = [
    (10, 6, "灯下", [("G4", 1.5), ("E4", 2.5)], 0.92),
    (
        16,
        8,
        "夜色把窗子涂成深蓝",
        [
            ("E4", 0.5),
            ("G4", 0.5),
            ("A4", 0.5),
            ("B4", 0.5),
            ("A4", 0.5),
            ("G4", 0.5),
            ("F4", 0.5),
            ("E4", 1.0),
            ("D4", 1.5),
        ],
        1.0,
    ),
    (
        24,
        8,
        "一盏灯守着未完成的句子",
        [
            ("G4", 0.5),
            ("A4", 0.5),
            ("C5", 1.0),
            ("A4", 0.5),
            ("G4", 0.5),
            ("A4", 0.5),
            ("G4", 0.5),
            ("F4", 0.5),
            ("E4", 0.5),
            ("F4", 0.5),
            ("E4", 1.5),
        ],
        1.0,
    ),
    (
        32,
        8,
        "笔尖停在纸上",
        [("E4", 0.5), ("F4", 0.5), ("G4", 1.0), ("E4", 0.5), ("D4", 1.0), ("C4", 2.0)],
        1.0,
    ),
    (
        40,
        8,
        "像一只犹豫的鸟",
        [
            ("G4", 0.5),
            ("A4", 0.5),
            ("B4", 0.5),
            ("A4", 0.5),
            ("G4", 0.5),
            ("F4", 0.5),
            ("E4", 2.5),
        ],
        1.0,
    ),
    (
        48,
        8,
        "我想把今天交给你",
        [
            ("E4", 0.5),
            ("G4", 0.5),
            ("A4", 0.5),
            ("B4", 0.5),
            ("A4", 1.0),
            ("G4", 0.5),
            ("F4", 0.5),
            ("E4", 2.0),
        ],
        1.0,
    ),
    (
        56,
        8,
        "那些来不及说的话",
        [
            ("F4", 0.5),
            ("G4", 0.5),
            ("A4", 0.5),
            ("B4", 0.5),
            ("A4", 1.0),
            ("G4", 0.5),
            ("F4", 0.5),
            ("E4", 2.0),
        ],
        1.0,
    ),
    (
        64,
        8,
        "都变成轻轻的标点",
        [
            ("E4", 0.5),
            ("G4", 0.5),
            ("A4", 0.5),
            ("B4", 0.5),
            ("C5", 1.0),
            ("A4", 0.5),
            ("G4", 0.5),
            ("E4", 2.0),
        ],
        1.0,
    ),
    (
        80,
        8,
        "风从远方走来",
        [("E4", 0.5), ("F4", 0.5), ("G4", 0.5), ("A4", 0.5), ("G4", 0.5), ("E4", 2.0)],
        1.0,
    ),
    (
        88,
        8,
        "带着雨的气味",
        [("A4", 0.5), ("G4", 0.5), ("A4", 0.5), ("F4", 0.5), ("G4", 0.5), ("E4", 2.0)],
        1.0,
    ),
    (
        96,
        8,
        "也带着一个名字",
        [
            ("G4", 0.5),
            ("A4", 0.5),
            ("B4", 0.5),
            ("A4", 0.5),
            ("G4", 0.5),
            ("A4", 0.5),
            ("E4", 2.0),
        ],
        1.0,
    ),
    (
        104,
        8,
        "我没有回头",
        [("E4", 0.5), ("D4", 0.5), ("C4", 1.0), ("D4", 0.5), ("E4", 2.0)],
        0.96,
    ),
    (
        112,
        16,
        "只把灯芯拧得更亮一些",
        [
            ("G4", 0.5),
            ("A4", 0.5),
            ("B4", 0.5),
            ("C5", 1.0),
            ("B4", 0.5),
            ("A4", 0.5),
            ("B4", 0.5),
            ("C5", 1.5),
            ("B4", 0.5),
            ("A4", 2.5),
        ],
        1.0,
    ),
    (
        128,
        8,
        "如果星星会读信",
        [
            ("G4", 0.5),
            ("A4", 0.5),
            ("C5", 1.0),
            ("B4", 1.0),
            ("A4", 0.5),
            ("G4", 0.5),
            ("E4", 2.0),
        ],
        1.0,
    ),
    (
        136,
        8,
        "请替我寄出这一页",
        [
            ("E4", 0.5),
            ("F4", 0.5),
            ("G4", 0.5),
            ("A4", 0.5),
            ("B4", 0.5),
            ("C5", 1.0),
            ("B4", 0.5),
            ("A4", 2.0),
        ],
        1.0,
    ),
    (
        144,
        8,
        "地址很简单",
        [("G4", 0.5), ("A4", 0.5), ("B4", 1.0), ("C5", 1.0), ("G4", 2.0)],
        1.0,
    ),
    (
        152,
        16,
        "人间秋天你的窗前",
        [
            ("C5", 1.0),
            ("B4", 1.0),
            ("A4", 0.5),
            ("G4", 1.0),
            ("E4", 0.5),
            ("G4", 0.5),
            ("A4", 0.5),
            ("C5", 4.0),
        ],
        1.0,
    ),
    (
        168,
        8,
        "别担心路太长",
        [("E4", 0.5), ("F4", 0.5), ("G4", 0.5), ("A4", 0.5), ("G4", 0.5), ("E4", 2.0)],
        0.95,
    ),
    (
        176,
        8,
        "诗会自己走路",
        [("F4", 0.5), ("G4", 0.5), ("A4", 0.5), ("B4", 0.5), ("A4", 0.5), ("G4", 2.0)],
        0.95,
    ),
    (
        184,
        8,
        "它经过桥经过月色",
        [
            ("E4", 0.5),
            ("G4", 0.5),
            ("A4", 0.5),
            ("C5", 1.0),
            ("A4", 0.5),
            ("G4", 0.5),
            ("A4", 1.0),
            ("G4", 2.0),
        ],
        0.98,
    ),
    (
        192,
        8,
        "经过所有沉默的站台",
        [
            ("E4", 0.5),
            ("F4", 0.5),
            ("G4", 0.5),
            ("A4", 0.5),
            ("G4", 0.5),
            ("F4", 0.5),
            ("E4", 0.5),
            ("F4", 0.5),
            ("G4", 2.0),
        ],
        0.96,
    ),
    (
        200,
        16,
        "最后停在你翻开书的手上",
        [
            ("C5", 0.5),
            ("B4", 0.5),
            ("A4", 0.5),
            ("G4", 0.5),
            ("F4", 0.5),
            ("E4", 0.5),
            ("F4", 0.5),
            ("G4", 0.5),
            ("A4", 0.5),
            ("B4", 1.0),
            ("C5", 3.5),
        ],
        1.0,
    ),
    (
        216,
        8,
        "那时请把灯留着",
        [
            ("E4", 0.5),
            ("G4", 0.5),
            ("A4", 0.5),
            ("B4", 0.5),
            ("C5", 1.5),
            ("A4", 0.5),
            ("G4", 2.0),
        ],
        0.92,
    ),
    (
        224,
        8,
        "我就在字里",
        [("E4", 0.5), ("F4", 0.5), ("G4", 0.5), ("E4", 1.0), ("C4", 2.5)],
        0.88,
    ),
    (
        232,
        16,
        "安静地陪你到天亮",
        [
            ("G4", 0.5),
            ("A4", 0.5),
            ("B4", 0.5),
            ("C5", 1.0),
            ("A4", 0.5),
            ("B4", 0.5),
            ("C5", 1.0),
            ("G4", 3.0),
        ],
        0.94,
    ),
    (
        248,
        16,
        "陪你到天亮",
        [("G4", 0.75), ("A4", 0.75), ("B4", 1.0), ("C5", 1.5), ("G4", 4.0)],
        0.7,
    ),
]

CHORDS = {
    "Cmaj7": [48, 52, 55, 59],
    "Am7": [45, 48, 52, 55],
    "Dm7": [50, 53, 57, 60],
    "G": [43, 47, 50, 55],
    "F": [41, 45, 48, 53],
    "Em": [40, 43, 47, 52],
    "Am": [45, 48, 52, 57],
    "C": [48, 52, 55],
}

PROGRESSION = (
    ["Cmaj7", "Cmaj7", "Am7", "G"]
    + ["Cmaj7", "Am7", "Dm7", "G", "Cmaj7", "Am7", "F", "G"] * 2
    + ["F", "G", "Em", "Am", "F", "G", "C", "C", "F", "G", "C", "G"]
    + ["F", "G", "C", "Am", "F", "G", "Em", "Am", "F", "G"]
    + ["C", "G", "Am", "F", "C", "G", "Am", "F", "F", "G", "C", "G"]
    + ["Cmaj7", "Am7", "F", "G", "Cmaj7", "Am7", "F", "C"]
    + ["C", "G", "Am", "F", "C", "Am", "F", "C"]
)
TOTAL_BARS = len(PROGRESSION)
TOTAL_BEATS = TOTAL_BARS * 4


def validate_score() -> None:
    if TOTAL_BARS != 70:
        raise SystemExit(f"expected 70 bars, got {TOTAL_BARS}")
    for start, slot, text, melody, _gain in VOCALS:
        chars = [c for c in text if "\u4e00" <= c <= "\u9fff"]
        if len(chars) != len(melody):
            raise SystemExit(f"{text}: {len(chars)} chars, {len(melody)} notes")
        used = sum(beats for _note, beats in melody)
        if used > slot + 1e-6:
            raise SystemExit(f"{text}: {used} beats do not fit in {slot}")
        if start + slot > TOTAL_BEATS + 1e-6:
            raise SystemExit(f"{text}: runs past the end of the song")


def section_at(beat: float) -> str:
    if beat < 16:
        return "intro"
    if beat < 80:
        return "verse"
    if beat < 128:
        return "wind"
    if beat < 168:
        return "chorus"
    if beat < 216:
        return "walk"
    if beat < 264:
        return "final"
    return "outro"


def varlen(value: int) -> bytes:
    out = [value & 0x7F]
    value >>= 7
    while value:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(out))


def write_midi(path: Path, events: list[tuple[int, bytes]]) -> None:
    events = sorted(events, key=lambda item: (item[0], item[1][0]))
    track = bytearray()
    last = 0
    for tick, data in events:
        track += varlen(max(0, tick - last))
        track += data
        last = tick
    track += varlen(0) + bytes([0xFF, 0x2F, 0x00])
    header = b"MThd" + struct.pack(">IHHH", 6, 1, 1, 480)
    body = b"MTrk" + struct.pack(">I", len(track)) + track
    path.write_bytes(header + body)


def build_arrangement(path: Path) -> None:
    tpq = 480
    events: list[tuple[int, bytes]] = []
    tempo = int(60_000_000 / BPM)
    events.append((0, bytes([0xFF, 0x51, 0x03]) + struct.pack(">I", tempo)[1:]))

    programs = {0: 24, 1: 0, 2: 8, 3: 48, 4: 32}  # guitar, piano, celesta, strings, bass
    for channel, program in programs.items():
        events.append((0, bytes([0xC0 | channel, program])))

    def note(channel: int, pitch: int, start: float, beats: float, vel: int) -> None:
        on = int(start * tpq)
        off = int((start + max(0.05, beats)) * tpq)
        if off <= on:
            off = on + 20
        events.append((on, bytes([0x90 | channel, pitch & 0x7F, max(1, min(127, vel))])))
        events.append((off, bytes([0x80 | channel, pitch & 0x7F, 0])))

    def motif(start: float, vel: int) -> None:
        figure = [("E5", 0.5), ("D5", 0.5), ("C5", 0.75), ("A4", 0.5), ("G4", 0.5), ("E4", 1.0)]
        cursor = start
        for name, beats in figure:
            if name == "A4":
                cursor += 0.25
            note(2, midi_of(name), cursor, beats * 0.92, vel)
            cursor += beats

    for bar, name in enumerate(PROGRESSION):
        start = bar * 4
        kind = section_at(start + 0.1)
        tones = CHORDS[name]
        bass_root = tones[0] - 12

        guitar_vel = {"intro": 52, "verse": 64, "wind": 66, "chorus": 74, "walk": 58, "final": 50, "outro": 42}[kind]
        if kind != "outro":
            pattern = [0, 2, 1, 3 if len(tones) > 3 else 2, 2, 1, 0, 2]
            for step, degree in enumerate(pattern):
                pitch = tones[degree]
                if step in (0, 6):
                    pitch -= 12
                note(0, pitch, start + step * 0.5, 0.42, guitar_vel - (8 if step % 2 else 0))

        piano_vel = {"intro": 36, "verse": 46, "wind": 50, "chorus": 62, "walk": 28, "final": 40, "outro": 34}[kind]
        if kind != "walk" or bar % 2 == 0:
            for pitch in tones:
                note(1, pitch + 12, start, 3.4 if kind != "chorus" else 1.6, piano_vel)
            if kind == "chorus":
                for pitch in tones:
                    note(1, pitch + 12, start + 2, 1.5, piano_vel - 6)

        if kind in {"wind", "chorus", "final"} or (kind == "outro" and bar < TOTAL_BARS - 1):
            string_vel = 34 if kind == "wind" else 44 if kind == "chorus" else 30
            for pitch in tones[:3]:
                note(3, pitch + 12, start, 3.8, string_vel)

        if kind != "intro" or bar >= 2:
            fade = 70 if kind not in {"outro", "final"} else 52
            if kind == "walk":
                note(4, bass_root, start, 0.9, fade)
                note(4, bass_root + 7, start + 2, 0.7, fade - 8)
            elif kind == "chorus":
                note(4, bass_root, start, 1.2, fade + 6)
                note(4, bass_root + 7, start + 2.0, 0.8, fade)
                note(4, bass_root + 12, start + 3.0, 0.6, fade - 6)
            else:
                note(4, bass_root, start, 1.6, fade)
                note(4, bass_root + 7, start + 2.5, 1.0, fade - 8)

        if kind in {"verse", "wind", "chorus", "walk"} and not (kind == "verse" and start < 24):
            for step in range(8):
                vel = 34 if step % 2 == 0 else 24
                if kind == "chorus":
                    vel += 8
                note(9, 70, start + step * 0.5, 0.2, vel)  # maracas
        if kind == "chorus" or (kind == "wind" and start >= 112):
            note(9, 36, start, 0.3, 58)  # kick
            note(9, 36, start + 2, 0.25, 48)
            note(9, 37, start + 1, 0.15, 42)  # sidestick
            note(9, 37, start + 3, 0.15, 38)
        if kind == "walk" and start >= 200:
            note(9, 36, start, 0.25, 44)

    motif(8, 62)
    motif(72, 54)
    motif(264, 58)
    motif(268, 48)
    # final lamp, one octave down from the twinkle, very quiet, on the resolving bar
    note(2, midi_of("C5"), 276, 3.2, 40)

    write_midi(path, events)


async def synthesize(text: str, path: Path) -> list[tuple[float, float, str]]:
    last_error: Exception | None = None
    for _ in range(3):
        try:
            comm = Communicate(
                text,
                VOICE,
                rate=TTS_RATE,
                pitch=TTS_PITCH,
                boundary="WordBoundary",
            )
            audio = bytearray()
            bounds: list[tuple[float, float, str]] = []
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    audio += chunk["data"]
                elif chunk["type"] == "WordBoundary":
                    bounds.append((chunk["offset"] / 1e7, chunk["duration"] / 1e7, chunk["text"]))
            path.write_bytes(audio)
            return bounds
        except Exception as exc:  # network hiccup; the line is retried
            last_error = exc
    raise RuntimeError(f"TTS failed for {text}") from last_error


def decode_wav(mp3: Path, wav: Path) -> np.ndarray:
    subprocess.check_call(
        ["ffmpeg", "-y", "-i", str(mp3), "-ar", str(VOCAL_SR), "-ac", "1", str(wav)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    audio, sr = sf.read(wav)
    if sr != VOCAL_SR:
        raise RuntimeError(f"unexpected sample rate {sr}")
    return np.asarray(audio, dtype=np.float64)


def f0_median(samples: np.ndarray) -> float:
    if len(samples) < int(0.05 * VOCAL_SR):
        return 0.0
    f0, _times = pw.harvest(
        samples.astype(np.float64),
        VOCAL_SR,
        f0_floor=80.0,
        f0_ceil=750.0,
        frame_period=5.0,
    )
    voiced = f0[f0 > 0]
    if len(voiced) < 3:
        return 0.0
    return float(np.median(voiced))


def align_chars(samples: np.ndarray, bounds: list[tuple[float, float, str]], chars: list[str]) -> list[tuple[int, int]]:
    joined = "".join(ch for _s, _d, text in bounds for ch in text if "\u4e00" <= ch <= "\u9fff")
    if joined == "".join(chars):
        spans: list[tuple[int, int]] = []
        for start, dur, text in bounds:
            word = [ch for ch in text if "\u4e00" <= ch <= "\u9fff"]
            a = int(start * VOCAL_SR)
            b = min(len(samples), int((start + dur) * VOCAL_SR))
            if len(word) <= 1:
                spans.append((a, max(a + 1, b)))
                continue
            seg = samples[a:b]
            hop = max(1, int(0.008 * VOCAL_SR))
            env = np.array(
                [np.sqrt(np.mean(seg[i : i + hop] ** 2) + 1e-12) for i in range(0, max(1, len(seg) - hop), hop)]
            )
            if len(env) > 5:
                env = np.convolve(env, np.ones(5) / 5, mode="same")
            cuts = [0]
            for k in range(1, len(word)):
                lo = int(len(env) * (k - 0.28) / len(word))
                hi = int(len(env) * (k + 0.28) / len(word))
                lo = max(cuts[-1] + 1, lo)
                hi = max(lo + 1, min(len(env) - 1, hi))
                cuts.append(lo + int(np.argmin(env[lo:hi])))
            cuts.append(len(env))
            for i in range(len(word)):
                s = a + cuts[i] * hop
                e = a + min(len(seg), cuts[i + 1] * hop)
                spans.append((max(0, s), max(s + 1, e)))
        return spans

    # Fall back to valleys across the whole phrase.
    trimmed = np.where(np.abs(samples) > 0.02 * np.max(np.abs(samples) + 1e-9))[0]
    a = int(trimmed[0]) if len(trimmed) else 0
    b = int(trimmed[-1]) if len(trimmed) else len(samples)
    seg = samples[a:b]
    hop = max(1, int(0.008 * VOCAL_SR))
    env = np.array(
        [np.sqrt(np.mean(seg[i : i + hop] ** 2) + 1e-12) for i in range(0, max(1, len(seg) - hop), hop)]
    )
    cuts = [0]
    for k in range(1, len(chars)):
        lo = int(len(env) * (k - 0.3) / len(chars))
        hi = int(len(env) * (k + 0.3) / len(chars))
        lo = max(cuts[-1] + 1, lo)
        hi = max(lo + 1, min(len(env) - 1, hi))
        cuts.append(lo + int(np.argmin(env[lo:hi])))
    cuts.append(len(env))
    spans = []
    for i in range(len(chars)):
        s = a + cuts[i] * hop
        e = a + min(len(seg), cuts[i + 1] * hop)
        spans.append((max(0, s), max(s + 1, e)))
    return spans


def fade(samples: np.ndarray, fade_in: float = 0.01, fade_out: float = 0.04) -> np.ndarray:
    out = samples.copy()
    fi = min(len(out) // 4, int(fade_in * VOCAL_SR))
    fo = min(len(out) // 3, int(fade_out * VOCAL_SR))
    if fi > 1:
        out[:fi] *= np.linspace(0.0, 1.0, fi)
    if fo > 1:
        out[-fo:] *= np.linspace(1.0, 0.0, fo)
    return out


def sing_slice(slice_y: np.ndarray, target_hz: float, target_n: int, fallback_f0: float) -> tuple[np.ndarray, float]:
    context = slice_y.astype(np.float64)
    med = f0_median(context) or fallback_f0 or target_hz
    steps = float(np.clip(12.0 * np.log2(target_hz / med), -9.0, 10.0))
    shifted = librosa.effects.pitch_shift(context.astype(np.float32), sr=VOCAL_SR, n_steps=steps)
    shifted = np.asarray(shifted, dtype=np.float64)
    thr = 0.025 * (np.max(np.abs(shifted)) + 1e-9)
    nz = np.where(np.abs(shifted) > thr)[0]
    if len(nz):
        shifted = shifted[max(0, nz[0] - int(0.008 * VOCAL_SR)) : min(len(shifted), nz[-1] + int(0.025 * VOCAL_SR))]
    natural = min(len(shifted), target_n)
    out = np.zeros(target_n, dtype=np.float64)
    out[:natural] = shifted[:natural]
    if natural < target_n - int(0.03 * VOCAL_SR) and len(shifted) > int(0.07 * VOCAL_SR):
        f0, _t = pw.harvest(shifted, VOCAL_SR, f0_floor=80.0, f0_ceil=750.0, frame_period=5.0)
        sp = pw.cheaptrick(shifted, f0, _t, VOCAL_SR)
        ap = pw.d4c(shifted, f0, _t, VOCAL_SR)
        rms = sp.mean(axis=1)
        voiced = np.where(f0 > 0)[0]
        if len(voiced):
            late = voiced[voiced > len(f0) * 0.3]
            if len(late) == 0:
                late = voiced
            best = int(late[np.argmax(rms[late])])
            need = target_n - natural + int(0.045 * VOCAL_SR)
            frames = max(4, int(need / VOCAL_SR * 1000.0 / 5.0))
            times = np.arange(frames) * 0.005
            vibrato = 1.0 + 0.014 * np.sin(2 * np.pi * 5.2 * times) * np.clip(times / 0.22, 0.0, 1.0)
            f0s = target_hz * vibrato
            tail = pw.synthesize(
                f0s.astype(np.float64),
                np.repeat(sp[best : best + 1], frames, axis=0),
                np.clip(np.repeat(ap[best : best + 1], frames, axis=0) * 0.55, 0.0, 1.0),
                VOCAL_SR,
                5.0,
            )
            cf = min(int(0.04 * VOCAL_SR), natural, len(tail))
            start = natural - cf
            seg = tail[: target_n - start]
            if cf > 1:
                ramp = np.linspace(0.0, 1.0, cf)
                out[start : start + cf] = out[start : start + cf] * (1.0 - ramp) + seg[:cf] * ramp
                if len(seg) > cf:
                    out[start + cf : start + len(seg)] = seg[cf:]
            else:
                out[start : start + len(seg)] = seg
    out = fade(out)
    got = f0_median(out[int(0.03 * VOCAL_SR) : max(int(0.03 * VOCAL_SR) + 8, int(len(out) * 0.75))])
    cents = 1200.0 * np.log2(got / target_hz) if got else 999.0
    if got and abs(cents) > 35:
        corr = float(np.clip(-cents / 100.0, -3.0, 3.0))
        fixed = librosa.effects.pitch_shift(out.astype(np.float32), sr=VOCAL_SR, n_steps=corr)
        fixed = np.asarray(fixed, dtype=np.float64)
        if len(fixed) < target_n:
            fixed = np.pad(fixed, (0, target_n - len(fixed)))
        out = fade(fixed[:target_n])
        got = f0_median(out[int(0.03 * VOCAL_SR) : max(int(0.03 * VOCAL_SR) + 8, int(len(out) * 0.75))])
        cents = 1200.0 * np.log2(got / target_hz) if got else 999.0
    peak = np.max(np.abs(out)) + 1e-9
    if peak > 0.95:
        out *= 0.95 / peak
    return out, cents


async def render_vocals(build: Path) -> tuple[np.ndarray, list[float]]:
    total = int((TOTAL_BEATS * BEAT + 1.2) * VOCAL_SR)
    mix = np.zeros(total, dtype=np.float64)
    cents: list[float] = []
    for index, (start, _slot, text, melody, gain) in enumerate(VOCALS):
        chars = [c for c in text if "\u4e00" <= c <= "\u9fff"]
        mp3 = build / f"line{index:02d}.mp3"
        wav = build / f"line{index:02d}.wav"
        print(f"sing {text}", flush=True)
        bounds = await synthesize(text, mp3)
        phrase = decode_wav(mp3, wav)
        fallback = f0_median(phrase) or 325.0
        spans = align_chars(phrase, bounds, chars)
        if len(spans) != len(chars):
            raise RuntimeError(f"{text}: aligned {len(spans)} slices for {len(chars)} characters")
        cursor = start
        for (a, b), ch, (name, beats) in zip(spans, chars, melody):
            target_n = max(int(0.12 * VOCAL_SR), int(beats * BEAT * VOCAL_SR))
            ctx = int(0.03 * VOCAL_SR)
            sl = phrase[max(0, a - ctx) : min(len(phrase), b + ctx)]
            note, err = sing_slice(sl, NOTE_HZ[name], target_n, fallback)
            note *= gain
            at = int(cursor * BEAT * VOCAL_SR)
            end = at + len(note)
            if end > len(mix):
                mix = np.pad(mix, (0, end - len(mix) + VOCAL_SR))
            mix[at:end] += note
            cents.append(err)
            cursor += beats
            del ch
    return mix, cents


def reverb(samples: np.ndarray, sr: int) -> np.ndarray:
    wet = np.zeros_like(samples)
    for delay, gain in ((0.029, 0.20), (0.047, 0.15), (0.071, 0.10), (0.097, 0.07)):
        shift = int(delay * sr)
        wet[shift:] += gain * samples[:-shift]
    echo = int(0.083 * sr)
    tail = np.zeros_like(samples)
    tail[echo:] += 0.28 * wet[:-echo]
    return samples + 0.18 * (wet + tail)


def mix(vocal_24k: np.ndarray, instrumental: np.ndarray) -> np.ndarray:
    vocal = resample_poly(vocal_24k, 147, 80)
    n = max(len(vocal), len(instrumental))
    if len(vocal) < n:
        vocal = np.pad(vocal, (0, n - len(vocal)))
    if len(instrumental) < n:
        instrumental = np.pad(instrumental, ((0, n - len(instrumental)), (0, 0)))
    vocal = vocal[:n]
    instrumental = instrumental[:n]
    vocal = reverb(vocal, SR)
    # Keep the voice close and a little wider than a dry mono track.
    delay = int(0.007 * SR)
    right = np.pad(vocal, (delay, 0))[:n] * 0.88
    vocal_st = np.stack([vocal, right], axis=1)
    env = np.abs(vocal)
    win = np.ones(int(0.04 * SR)) / int(0.04 * SR)
    smooth = np.convolve(env, win, mode="same")
    level = np.percentile(smooth[smooth > 0], 85) if np.any(smooth > 0) else 1.0
    duck = 1.0 - 0.28 * np.clip(smooth / (level + 1e-9), 0.0, 1.0)
    instrumental = instrumental * duck[:, None]
    # Vocal sits forward; the bed stays under the lyric.
    v_peak = np.max(np.abs(vocal_st)) + 1e-9
    i_peak = np.max(np.abs(instrumental)) + 1e-9
    mixed = vocal_st / v_peak * 0.82 + instrumental / i_peak * 0.46
    peak = np.max(np.abs(mixed)) + 1e-9
    mixed *= 0.89 / peak
    fade_n = int(0.4 * SR)
    mixed[:fade_n] *= np.linspace(0.0, 1.0, fade_n)[:, None]
    mixed[-fade_n:] *= np.linspace(1.0, 0.0, fade_n)[:, None]
    return mixed.astype(np.float32)


def render_midi(mid: Path, wav: Path) -> None:
    subprocess.check_call(
        [
            "fluidsynth",
            "-ni",
            "-q",
            "-g",
            "1.0",
            "-R",
            "1",
            "-C",
            "0",
            "-r",
            str(SR),
            "-F",
            str(wav),
            "-T",
            "wav",
            str(SF2),
            str(mid),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


async def main() -> None:
    validate_score()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dengxia-") as tmp:
        build = Path(tmp)
        mid = build / "song.mid"
        inst = build / "inst.wav"
        build_arrangement(mid)
        print("render arrangement", flush=True)
        render_midi(mid, inst)
        instrumental, isr = sf.read(inst)
        if isr != SR:
            raise RuntimeError(f"instrumental sample rate {isr}")
        if instrumental.ndim == 1:
            instrumental = np.stack([instrumental, instrumental], axis=1)
        vocal, cents = await render_vocals(build)
        good = [c for c in cents if c < 900]
        off = sum(abs(c) > 80 for c in good)
        print(
            f"pitch: {len(good)} notes, median error {np.median(np.abs(good)):.1f} cents, {off} off by >80",
            flush=True,
        )
        mixed = mix(vocal, instrumental.astype(np.float64))
        wav_out = build / "song.wav"
        sf.write(wav_out, mixed, SR)
        subprocess.check_call(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(wav_out),
                "-af",
                "loudnorm=I=-14:TP=-1.2:LRA=11",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "256k",
                str(OUT),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    print(f"wrote {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
