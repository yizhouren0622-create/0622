#!/usr/bin/env python3
"""Compose and sing 《灯下》 in the Xiaoyi voice.

The poem is set as a short night song in C major, at 84 BPM:
intro, two verses, a wind section, a chorus, a walking bridge,
a quiet final refrain, and a music-box outro.

The vocal is Xiaoyi singing, not reading. Each line stays one phrase.
Her vowel moves onto the melody note with a short glide, keeps the
shape of the Mandarin tone, and adds a light vibrato on the long notes.
The words are not sliced apart, and the band underneath is unchanged.

Requires ffmpeg, fluidsynth, FluidR3_GM, edge-tts, and praat-parselmouth.
Output: audio/灯下-歌曲.mp3
"""

from __future__ import annotations

import asyncio
import struct
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import parselmouth
import pyworld as pw
import soundfile as sf
from edge_tts import Communicate
from parselmouth.praat import call
from scipy.signal import butter, lfilter, resample_poly

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
        1.08,
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
        0.92,
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


def trim_phrase(samples: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(samples)) + 1e-9
    audible = np.where(np.abs(samples) > 0.02 * peak)[0]
    if len(audible) == 0:
        return samples
    start = max(0, int(audible[0]) - int(0.02 * VOCAL_SR))
    end = min(len(samples), int(audible[-1]) + int(0.05 * VOCAL_SR))
    trimmed = samples[start:end].copy()
    fade_in = min(len(trimmed) // 5, int(0.012 * VOCAL_SR))
    fade_out = min(len(trimmed) // 4, int(0.03 * VOCAL_SR))
    if fade_in > 1:
        trimmed[:fade_in] *= np.linspace(0.0, 1.0, fade_in)
    if fade_out > 1:
        trimmed[-fade_out:] *= np.linspace(1.0, 0.0, fade_out)
    return trimmed


# How each line is actually spoken. Commas are breaths she already has in the poem.
# A few words are lengthened only where the short form collapses into another word.
SPOKEN = {
    "一盏灯守着未完成的句子": "一盏灯，守着未完成的句子。",
    "只把灯芯拧得更亮一些": "只把灯芯，拧得更亮一些。",
    "它经过桥经过月色": "它经过桥，经过月色。",
    "人间秋天你的窗前": "人间，秋天，你的窗前。",
    "安静地陪你到天亮": "安静地，陪你到天亮。",
    "请替我寄出这一页": "请替我寄出，这一页。",
}


def spoken_text(text: str) -> str:
    if text in SPOKEN:
        return SPOKEN[text]
    return text if text.endswith("。") else f"{text}。"


def syllable_spans(bounds: list[tuple[float, float, str]], chars: list[str]) -> list[tuple[float, float]] | None:
    joined = "".join(ch for _s, _d, text in bounds for ch in text if "\u4e00" <= ch <= "\u9fff")
    if joined != "".join(chars):
        return None
    spans: list[tuple[float, float]] = []
    for start, dur, text in bounds:
        word = [ch for ch in text if "\u4e00" <= ch <= "\u9fff"]
        if not word:
            continue
        for i in range(len(word)):
            spans.append((start + dur * i / len(word), start + dur * (i + 1) / len(word)))
    return spans


def soften_hz(notes: list[str]) -> list[float]:
    """Stepwise tune inside her speaking range, so the line can actually be sung."""
    prev = NOTE_HZ["E4"]
    targets: list[float] = []
    for name in notes:
        hz = float(np.clip(NOTE_HZ[name], NOTE_HZ["D4"], NOTE_HZ["A4"]))
        leap = float(np.clip(12.0 * np.log2(hz / prev), -4.0, 4.0))
        hz = float(np.clip(prev * 2.0 ** (leap / 12.0), NOTE_HZ["D4"], NOTE_HZ["A4"]))
        targets.append(hz)
        prev = hz
    return targets


def envelope(samples: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    win = int(0.012 * VOCAL_SR)
    hop = int(0.004 * VOCAL_SR)
    if len(samples) <= win:
        return np.array([0.0]), np.array([0.0])
    times = []
    values = []
    for index in range(0, len(samples) - win, hop):
        segment = samples[index : index + win]
        values.append(float(np.sqrt(np.mean(segment * segment))))
        times.append((index + win / 2) / VOCAL_SR)
    smooth = np.convolve(np.array(values), np.array([0.25, 0.5, 0.25]), mode="same")
    return np.array(times), smooth


def aligned_spans(
    samples: np.ndarray,
    bounds: list[tuple[float, float, str]],
    chars: list[str],
) -> list[tuple[float, float]] | None:
    """Put each character on its own vowel, using the word timing as a fence."""
    rough = syllable_spans(bounds, chars)
    if rough is None:
        return None
    times, level = envelope(samples)
    if len(times) < 3:
        return rough
    spans: list[tuple[float, float]] = []
    nuclei: list[float] = []
    cursor = 0
    for start, dur, text in bounds:
        word = [ch for ch in text if "\u4e00" <= ch <= "\u9fff"]
        if not word:
            continue
        pieces = rough[cursor : cursor + len(word)]
        cursor += len(word)
        word_nuclei: list[float] = []
        for piece_start, piece_end in pieces:
            inside = (times >= piece_start) & (times <= piece_end)
            if not np.any(inside):
                word_nuclei.append(0.5 * (piece_start + piece_end))
                continue
            choice = int(np.argmax(np.where(inside, level, -1.0)))
            word_nuclei.append(float(times[choice]))
        for index, nucleus in enumerate(word_nuclei):
            left = start if index == 0 else 0.5 * (word_nuclei[index - 1] + nucleus)
            right = (start + dur) if index == len(word_nuclei) - 1 else 0.5 * (nucleus + word_nuclei[index + 1])
            if right - left < 0.04:
                right = left + 0.04
            spans.append((float(left), float(right)))
            nuclei.append(nucleus)
    if len(spans) != len(chars):
        return rough
    return spans


def resynthesize(samples: np.ndarray, times: np.ndarray, curve: np.ndarray, backend: str) -> np.ndarray:
    """Apply one continuous pitch curve. The phrase is never cut into pieces."""
    curve = np.clip(curve, 150.0, 520.0)
    if backend == "world":
        frames, frame_times = pw.harvest(samples, float(VOCAL_SR), f0_floor=75.0, f0_ceil=600.0)
        spectrum = pw.cheaptrick(samples, frames, frame_times, float(VOCAL_SR))
        aperiodicity = pw.d4c(samples, frames, frame_times, float(VOCAL_SR))
        sung_f0 = np.interp(frame_times, times, curve)
        sung_f0[frames <= 0] = 0.0
        sung = pw.synthesize(sung_f0, spectrum, aperiodicity, float(VOCAL_SR))
        return np.asarray(sung, dtype=np.float64)
    sound = parselmouth.Sound(samples, sampling_frequency=VOCAL_SR)
    manipulation = call(sound, "To Manipulation", 0.008, 75, 600)
    tier = call(manipulation, "Extract pitch tier")
    call(tier, "Remove points between", 0, sound.xmax)
    for time, hz in zip(times, curve):
        call(tier, "Add point", float(time), float(hz))
    call([manipulation, tier], "Replace pitch tier")
    sung = call(manipulation, "Get resynthesis (overlap-add)")
    return np.asarray(sung.values[0], dtype=np.float64)


def sing_phrase(
    samples: np.ndarray,
    spans: list[tuple[float, float]],
    notes: list[str],
    beats: list[float],
    tone_keep: float = 0.85,
    shift_limit: float = 4.0,
    backend: str = "world",
    protect_within: float = 1.15,
) -> np.ndarray:
    """Glide a whole phrase onto the melody without slicing the words apart."""
    samples = np.ascontiguousarray(samples, dtype=np.float64)
    sound = parselmouth.Sound(samples, sampling_frequency=VOCAL_SR)
    if sound.duration < 0.2 or len(spans) != len(notes) or len(beats) != len(notes):
        return samples
    original = sound.to_pitch(time_step=0.008, pitch_floor=75, pitch_ceiling=600)
    times_env, level = envelope(samples)
    nuclei: list[float] = []
    for start, end in spans:
        inside = (times_env >= start) & (times_env <= end)
        if not np.any(inside):
            nuclei.append(0.5 * (start + end))
            continue
        nuclei.append(float(times_env[int(np.argmax(np.where(inside, level, -1.0)))]))

    step = 0.008
    times = np.arange(0.012, float(sound.xmax) - 0.012, step)
    spoken = np.array(
        [call(original, "Get value at time", float(t), "Hertz", "Linear") for t in times],
        dtype=np.float64,
    )
    residual = np.zeros(len(times), dtype=np.float64)
    voiced = np.isfinite(spoken) & (spoken > 0)
    spoken_medians: list[float | None] = []
    for start, end in spans:
        region = (times >= start + 0.02) & (times <= end - 0.01) & voiced
        if int(np.sum(region)) < 3:
            spoken_medians.append(None)
            continue
        preliminary = float(np.median(spoken[region]))
        believable = region & (np.abs(12.0 * np.log2(np.where(voiced, spoken, preliminary) / preliminary)) < 4.5)
        if int(np.sum(believable)) >= 3:
            median = float(np.median(spoken[believable]))
            residual[believable] = 12.0 * np.log2(spoken[believable] / median)
        else:
            median = preliminary
        spoken_medians.append(median)
    shifts: list[float] = []

    targets = soften_hz(notes)
    limited: list[float] = []
    for hz, median in zip(targets, spoken_medians):
        if median is None or median <= 0:
            limited.append(hz)
            shifts.append(0.0)
            continue
        shift = float(np.clip(12.0 * np.log2(hz / median), -shift_limit, shift_limit))
        shifts.append(shift)
        limited.append(float(median * 2.0 ** (shift / 12.0)))
    targets = limited
    curve = np.empty(len(times), dtype=np.float64)
    for index, time in enumerate(times):
        syllable = 0
        for i, (start, _end) in enumerate(spans):
            if time >= start - 0.004:
                syllable = i
        start, _end = spans[syllable]
        hz = targets[syllable]
        previous = targets[syllable - 1] if syllable else hz
        glide_end = min(start + 0.07, nuclei[syllable])
        if syllable and time < glide_end and glide_end > start + 0.02:
            glide = float(np.clip((time - start) / (glide_end - start), 0.0, 1.0))
            blend = 0.5 - 0.5 * np.cos(np.pi * glide)
            base = previous * (hz / previous) ** blend
        else:
            base = hz
        ornament = float(np.clip(residual[index] * tone_keep, -3.0, 3.0))
        base *= 2.0 ** (ornament / 12.0)
        if beats[syllable] >= 1.5 and time > nuclei[syllable] + 0.12:
            age = time - (nuclei[syllable] + 0.12)
            depth = 0.30 * min(1.0, age / 0.14)
            base *= 2.0 ** ((depth * np.sin(2.0 * np.pi * 5.4 * age)) / 12.0)
        curve[index] = base
    sung = resynthesize(samples, times, curve, backend)
    return keep_near_syllables(samples, sung, spans, shifts, threshold=protect_within)


def keep_near_syllables(
    original: np.ndarray,
    sung: np.ndarray,
    spans: list[tuple[float, float]],
    shifts: list[float],
    threshold: float = 1.15,
) -> np.ndarray:
    """Leave a syllable spoken when the melody already sits on her pitch."""
    length = min(len(original), len(sung))
    mixed = sung[:length].copy()
    source = original[:length]
    fade = int(0.018 * VOCAL_SR)
    for (start, end), shift in zip(spans, shifts):
        if abs(shift) > threshold:
            continue
        left = int(start * VOCAL_SR)
        right = min(length, int(end * VOCAL_SR))
        if right - left < fade * 2:
            continue
        ramp = np.ones(right - left, dtype=np.float64)
        ramp[:fade] = np.linspace(0.0, 1.0, fade)
        ramp[-fade:] = np.linspace(1.0, 0.0, fade)
        mixed[left:right] = ramp * source[left:right] + (1.0 - ramp) * mixed[left:right]
    return mixed


async def render_vocals(build: Path) -> np.ndarray:
    total = int((TOTAL_BEATS * BEAT + 1.2) * VOCAL_SR)
    mix = np.zeros(total, dtype=np.float64)
    for index, (start, slot, text, melody, gain) in enumerate(VOCALS):
        chars = [ch for ch in text if "\u4e00" <= ch <= "\u9fff"]
        notes = [name for name, _beats in melody]
        note_beats = [beats for _name, beats in melody]
        mp3 = build / f"line{index:02d}.mp3"
        wav = build / f"line{index:02d}.wav"
        print(f"sing {text}", flush=True)
        bounds = await synthesize(spoken_text(text), mp3)
        phrase = decode_wav(mp3, wav)
        spans = aligned_spans(phrase, bounds, chars)
        if spans is None or len(spans) != len(notes):
            print(f"  even split for {text}", flush=True)
            audible = np.where(np.abs(phrase) > 0.02 * (np.max(np.abs(phrase)) + 1e-9))[0]
            a = float(audible[0] / VOCAL_SR) if len(audible) else 0.0
            b = float(audible[-1] / VOCAL_SR) if len(audible) else len(phrase) / VOCAL_SR
            spans = [(a + (b - a) * i / len(notes), a + (b - a) * (i + 1) / len(notes)) for i in range(len(notes))]
        if text == "如果星星会读信":
            # This hook sits higher than her speaking pitch. A smaller lift keeps 读信.
            sung = trim_phrase(sing_phrase(phrase, spans, notes, note_beats, tone_keep=1.0, shift_limit=1.45))
        else:
            sung = trim_phrase(sing_phrase(phrase, spans, notes, note_beats))
        room = slot * BEAT
        if len(sung) / VOCAL_SR > room - 0.05:
            keep = max(int(0.84 * len(sung)), int((room - 0.05) * VOCAL_SR))
            sung = sung[:keep].copy()
            fade_out = min(len(sung) // 4, int(0.04 * VOCAL_SR))
            if fade_out > 1:
                sung[-fade_out:] *= np.linspace(1.0, 0.0, fade_out)
        sung *= gain
        at = int(start * BEAT * VOCAL_SR)
        end = at + len(sung)
        if end > len(mix):
            mix = np.pad(mix, (0, end - len(mix) + VOCAL_SR))
        mix[at:end] += sung
    return mix


def presence(samples: np.ndarray, sr: int) -> np.ndarray:
    coefficients, denom = butter(2, 1700 / (sr / 2), btype="high")
    bright = lfilter(coefficients, denom, samples)
    return samples + 0.24 * bright


def reverb(samples: np.ndarray, sr: int) -> np.ndarray:
    wet = np.zeros_like(samples)
    for delay, gain in ((0.026, 0.18), (0.043, 0.12), (0.071, 0.07)):
        shift = int(delay * sr)
        wet[shift:] += gain * samples[:-shift]
    return samples + 0.08 * wet


def mix(vocal_24k: np.ndarray, instrumental: np.ndarray) -> np.ndarray:
    vocal = resample_poly(vocal_24k, 147, 80)
    n = max(len(vocal), len(instrumental))
    if len(vocal) < n:
        vocal = np.pad(vocal, (0, n - len(vocal)))
    if len(instrumental) < n:
        instrumental = np.pad(instrumental, ((0, n - len(instrumental)), (0, 0)))
    vocal = vocal[:n]
    instrumental = instrumental[:n]
    vocal = presence(vocal, SR)
    vocal = reverb(vocal, SR)
    vocal_st = np.stack([vocal, vocal], axis=1)
    env = np.convolve(np.abs(vocal), np.ones(int(0.03 * SR)) / int(0.03 * SR), mode="same")
    level = np.percentile(env[env > 0], 80) if np.any(env > 0) else 1.0
    duck = 1.0 - 0.62 * np.clip(env / (level + 1e-9), 0.0, 1.0)
    instrumental = instrumental * duck[:, None]
    v_peak = np.max(np.abs(vocal_st)) + 1e-9
    i_peak = np.max(np.abs(instrumental)) + 1e-9
    mixed = vocal_st / v_peak * 0.96 + instrumental / i_peak * 0.30
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
        vocal = await render_vocals(build)
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
