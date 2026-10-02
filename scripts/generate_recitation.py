#!/usr/bin/env python3
"""Generate the recitation of the original poem 《灯下》.

The poem is spoken in one pass so the phrasing stays connected.
Voice is the brighter Xiaoyi neural voice, pitched up for a lighter tone.

Requires ffmpeg and edge-tts. Output: audio/灯下-诗朗诵.mp3
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
from edge_tts import Communicate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "audio" / "灯下-诗朗诵.mp3"
VOICE = "zh-CN-XiaoyiNeural"
RATE = "-8%"
PITCH = "+14Hz"
SR = 44100

# Same words as audio/灯下.txt. Commas keep neighboring lines in one breath;
# periods only mark the end of a stanza.
TEXT = (
    "诗朗诵，灯下。"
    "夜色把窗子涂成深蓝，一盏灯，守着未完成的句子，笔尖停在纸上，像一只犹豫的鸟。"
    "我想把今天交给你，那些来不及说的话，都变成轻轻的标点。"
    "风从远方走来，带着雨的气味，也带着一个名字，我没有回头，只把灯芯拧得更亮一些。"
    "如果星星会读信，请替我寄出这一页，地址很简单，人间，秋天，你的窗前。"
    "别担心路太长，诗会自己走路，它经过桥，经过月色，经过所有沉默的站台，最后停在你翻开书的手上。"
    "那时，请把灯留着，我就在字里，安静地，陪你到天亮。"
)


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
    env = np.clip(t / 1.6, 0, 1) * np.clip((dur - t) / 2.4, 0, 1)
    lfo = 0.88 + 0.12 * np.sin(2 * np.pi * 0.09 * t)

    def tone(freq: float, amp: float, detune: float = 0.0) -> np.ndarray:
        return amp * np.sin(2 * np.pi * (freq + detune) * t)

    left = tone(196.0, 0.16, -0.12) + tone(246.94, 0.08) + tone(392.0, 0.04, 0.06)
    right = tone(196.0, 0.16, 0.12) + tone(246.94, 0.07, -0.05) + tone(392.0, 0.035)
    stereo = np.stack([left * env * lfo, right * env * lfo], axis=1) * 0.028
    pcm = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(SR)
        handle.writeframes(pcm.tobytes())


async def render(build: Path) -> None:
    speech = build / "speech.mp3"
    speech_wav = build / "speech.wav"
    await Communicate(TEXT, VOICE, rate=RATE, pitch=PITCH).save(str(speech))
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(speech),
            "-ar",
            str(SR),
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(speech_wav),
        ]
    )

    lead, tail = build / "lead.wav", build / "tail.wav"
    silence(lead, 0.28)
    silence(tail, 0.9)
    listing = build / "list.txt"
    listing.write_text(
        f"file '{lead}'\nfile '{speech_wav}'\nfile '{tail}'\n",
        encoding="utf-8",
    )
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
    fade_out = max(0.0, dur - 1.1)
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
            "highpass=f=80[v];"
            "[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
            "lowpass=f=2200[p];"
            "[v][p]amix=inputs=2:duration=first:normalize=0:dropout_transition=0,"
            "alimiter=limit=0.95:level=false,loudnorm=I=-16:TP=-1.5:LRA=11,"
            f"afade=t=in:st=0:d=0.15,afade=t=out:st={fade_out:.3f}:d=1.1",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(OUT),
        ]
    )
    print(f"wrote {OUT} ({duration_of(OUT):.1f}s)")


async def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="recitation-") as tmp:
        await render(Path(tmp))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)
