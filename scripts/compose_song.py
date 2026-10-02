#!/usr/bin/env python3
"""Compose and sing 《灯下》 in the Xiaoyi voice.

The poem is set as a short night song in C major, at 84 BPM:
intro, two verses, a wind section, a chorus, a walking bridge,
a quiet final refrain, and a music-box outro.

The vocal is Xiaoyi (pitch +14 Hz) speaking each line in one breath,
a little slower, with the rises and falls she already uses.
Forcing a separate pitch onto every syllable made the words unclear,
so the tune stays in her own intonation and the band carries the harmony.

Requires ffmpeg, fluidsynth, FluidR3_GM, and edge-tts.
Output: audio/灯下-歌曲.mp3
"""

from __future__ import annotations

import asyncio
import struct
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
from edge_tts import Communicate
from scipy.signal import butter, lfilter, resample_poly

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "audio" / "灯下-歌曲.mp3"
VOICE = "zh-CN-XiaoyiNeural"
TTS_RATE = "-12%"
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
    "请替我寄出这一页": "请替我寄出去，这一页。",
    "我就在字里": "我就在字里面。",
    "一盏灯守着未完成的句子": "一盏灯，守着未完成的句子。",
    "只把灯芯拧得更亮一些": "只把灯芯，拧得更亮一些。",
    "它经过桥经过月色": "它经过桥，经过月色。",
    "人间秋天你的窗前": "人间，秋天，你的窗前。",
    "安静地陪你到天亮": "安静地，陪你到天亮。",
    "那些来不及说的话": "那些来不及说的话。",
}


def spoken_text(text: str) -> str:
    if text in SPOKEN:
        return SPOKEN[text]
    return text if text.endswith("。") else f"{text}。"


async def render_vocals(build: Path) -> np.ndarray:
    total = int((TOTAL_BEATS * BEAT + 1.2) * VOCAL_SR)
    mix = np.zeros(total, dtype=np.float64)
    for index, (start, slot, text, _melody, gain) in enumerate(VOCALS):
        mp3 = build / f"line{index:02d}.mp3"
        wav = build / f"line{index:02d}.wav"
        print(f"sing {text}", flush=True)
        await synthesize(spoken_text(text), mp3)
        sung = trim_phrase(decode_wav(mp3, wav))
        room = slot * BEAT
        if len(sung) / VOCAL_SR > room - 0.05:
            keep = max(int(0.84 * len(sung)), int((room - 0.05) * VOCAL_SR))
            sung = sung[:keep].copy()
            fade_out = min(len(sung) // 4, int(0.04 * VOCAL_SR))
            if fade_out > 1:
                sung[-fade_out:] *= np.linspace(1.0, 0.0, fade_out)
            print(f"  shortened {text} to fit the phrase", flush=True)
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
    return samples + 0.18 * bright


def reverb(samples: np.ndarray, sr: int) -> np.ndarray:
    wet = np.zeros_like(samples)
    for delay, gain in ((0.023, 0.16), (0.037, 0.10)):
        shift = int(delay * sr)
        wet[shift:] += gain * samples[:-shift]
    return samples + 0.05 * wet


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
    duck = 1.0 - 0.48 * np.clip(env / (level + 1e-9), 0.0, 1.0)
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
