#!/usr/bin/env python3
"""Generate the one-minute recitation of the original poem 《灯下》.

Requires ffmpeg and edge-tts. Output: audio/灯下-诗朗诵.mp3
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from edge_tts import Communicate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "audio" / "灯下-诗朗诵.mp3"
VOICE = "zh-CN-XiaoxiaoNeural"
RATE = "-16%"
PITCH = "-2Hz"
SR = 44100

SEGMENTS = [
    "诗朗诵。《灯下》。",
    "夜色把窗子涂成深蓝，一盏灯，守着未完成的句子。笔尖停在纸上，像一只犹豫的鸟。",
    "我想把今天交给你。那些来不及说的话，都变成轻轻的标点。",
    "风从远方走来，带着雨的气味，也带着一个名字。我没有回头，只把灯芯拧得更亮一些。",
    "如果星星会读信，请替我寄出这一页。地址很简单：人间，秋天，你的窗前。",
    "别担心路太长，诗会自己走路。它经过桥，经过月色，经过所有沉默的站台，最后停在你翻开书的手上。",
    "那时，请把灯留着。我就在字里，安静地，陪你到天亮。",
]


def run(cmd: list[str]) -> None:
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def duration_of(path: Path) -> float:
    raw = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        text=True,
    )
    return float(raw.strip())


async def synthesize(build: Path) -> list[Path]:
    wavs: list[Path] = []
    for i, text in enumerate(SEGMENTS):
        mp3 = build / f"seg{i:02d}.mp3"
        wav = build / f"seg{i:02d}.wav"
        await Communicate(text, VOICE, rate=RATE, pitch=PITCH).save(str(mp3))
        run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(mp3),
                "-ar",
                str(SR),
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(wav),
            ]
        )
        wavs.append(wav)
    return wavs


def silence(path: Path, seconds: float) -> None:
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=r={SR}:cl=mono",
            "-t",
            f"{seconds:.3f}",
            "-c:a",
            "pcm_s16le",
            str(path),
        ]
    )


def write_pad(path: Path, dur: float) -> None:
    n = int(SR * dur)
    t = np.arange(n) / SR
    env = np.clip(t / 2.2, 0, 1) * np.clip((dur - t) / 3.0, 0, 1)
    lfo = 0.82 + 0.18 * np.sin(2 * np.pi * 0.07 * t)

    def tone(freq: float, amp: float, detune: float = 0.0) -> np.ndarray:
        return amp * np.sin(2 * np.pi * (freq + detune) * t)

    left = (
        tone(110.0, 0.22, -0.15)
        + tone(164.81, 0.11, 0.05)
        + tone(220.0, 0.07)
        + tone(329.63, 0.035, 0.08)
    )
    right = (
        tone(110.0, 0.22, 0.15)
        + tone(164.81, 0.11, -0.04)
        + tone(220.0, 0.07, 0.12)
        + tone(329.63, 0.03, -0.05)
    )
    stereo = np.stack([left * env * lfo, right * env * lfo], axis=1) * 0.045
    pcm = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)
    import wave

    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(SR)
        handle.writeframes(pcm.tobytes())


async def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="recitation-") as tmp:
        await render(Path(tmp))


async def render(build: Path) -> None:
    wavs = await synthesize(build)

    lead, gap, tail = build / "lead.wav", build / "gap.wav", build / "tail.wav"
    silence(lead, 0.65)
    silence(gap, 0.38)
    silence(tail, 1.35)

    parts: list[Path] = [lead]
    for i, wav in enumerate(wavs):
        parts.append(wav)
        parts.append(tail if i == len(wavs) - 1 else gap)

    listing = build / "list.txt"
    listing.write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
    voice = build / "voice.wav"
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(listing),
            "-c:a",
            "pcm_s16le",
            str(voice),
        ]
    )
    dur = duration_of(voice)
    pad = build / "pad.wav"
    write_pad(pad, dur)

    fade_out = max(0.0, dur - 1.6)
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(voice),
            "-i",
            str(pad),
            "-filter_complex",
            "[0:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
            "highpass=f=70,aecho=0.8:0.88:22|40:0.08|0.04,volume=2.2dB[v];"
            "[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
            "lowpass=f=1800,volume=-4dB[p];"
            "[v][p]amix=inputs=2:duration=first:normalize=0:dropout_transition=0,"
            "alimiter=limit=0.95:level=false,loudnorm=I=-16:TP=-1.5:LRA=11,"
            f"afade=t=in:st=0:d=0.4,afade=t=out:st={fade_out:.3f}:d=1.6",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(OUT),
        ]
    )
    print(f"wrote {OUT} ({duration_of(OUT):.1f}s)")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)
