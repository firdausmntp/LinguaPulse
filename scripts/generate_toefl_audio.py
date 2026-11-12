"""Generate realistic TOEFL EPT listening audio files using Microsoft Edge Neural TTS."""
import argparse
import asyncio
import sys
from pathlib import Path

VOICE_PRESETS = {
    "narrator_guy": "en-US-GuyNeural",
    "narrator_andrew": "en-US-AndrewNeural",
    "lecture_jenny": "en-US-JennyNeural",
    "lecture_aria": "en-US-AriaNeural",
    "student_male": "en-US-ChristopherNeural",
    "student_female": "en-US-AnaNeural",
}

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "frontend" / "media" / "listening"


async def synthesize_text(text: str, voice: str, rate: str, output_path: Path) -> Path:
    import edge_tts

    output_path.parent.mkdir(parents=True, exist_ok=True)
    communicator = edge_tts.Communicate(text=text, voice=voice, rate=rate)
    await communicator.save(str(output_path))
    return output_path


async def generate_dialogue(segments: list, rate: str, output_path: Path) -> Path:
    """Generate audio with multiple speakers and pauses."""
    import edge_tts
    import tempfile

    temp_files = []
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        combined_bytes = bytearray()
        for idx, (speaker_voice, text) in enumerate(segments):
            voice = VOICE_PRESETS.get(speaker_voice, speaker_voice)
            comm = edge_tts.Communicate(text=text, voice=voice, rate=rate)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                temp_files.append(tmp_path)
            await comm.save(str(tmp_path))
            combined_bytes.extend(tmp_path.read_bytes())
        output_path.write_bytes(combined_bytes)
        return output_path
    finally:
        for tmp in temp_files:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass


def generate_toefl_sample():
    """Generates an authentic TOEFL instructional passage using en-US-GuyNeural."""
    text = (
        "Part A. Directions. In Part A, you will hear short conversations between two people. "
        "After each conversation, you will hear a question about the conversation. "
        "The conversations and questions will not be repeated. "
        "After you hear a question, read the four possible answers in your test book "
        "and choose the best answer. Then, on your answer sheet, find the number of the question "
        "and fill in the space that corresponds to the letter of the answer you have chosen."
    )
    output = DEFAULT_OUTPUT_DIR / "sample-instruction.mp3"
    print(f"Generating TOEFL sample audio to: {output}")
    asyncio.run(synthesize_text(text, VOICE_PRESETS["narrator_guy"], "-8%", output))
    print(f"Success! Audio saved ({output.stat().st_size} bytes).")


def main():
    parser = argparse.ArgumentParser(description="TOEFL EPT Neural Audio Generator")
    parser.add_argument("--text", type=str, help="Text transcript to synthesize")
    parser.add_argument("--voice", type=str, default="narrator_guy", choices=list(VOICE_PRESETS.keys()) + list(VOICE_PRESETS.values()), help="Voice preset or Edge Neural voice name")
    parser.add_argument("--rate", type=str, default="-8%", help="Speech pace adjustment (default: -8%% for clear TOEFL articulation)")
    parser.add_argument("--output", type=str, help="Destination audio file path (defaults to frontend/media/listening/<filename>)")
    parser.add_argument("--sample", action="store_true", help="Generate official TOEFL sample instruction audio")

    args = parser.parse_args()

    if args.sample:
        generate_toefl_sample()
        return

    if not args.text:
        parser.print_help()
        sys.exit(1)

    voice = VOICE_PRESETS.get(args.voice, args.voice)
    dest = Path(args.output) if args.output else DEFAULT_OUTPUT_DIR / "generated_listening.mp3"
    print(f"Synthesizing with {voice} at {args.rate}...")
    asyncio.run(synthesize_text(args.text, voice, args.rate, dest))
    print(f"Audio written to {dest} ({dest.stat().st_size} bytes).")


if __name__ == "__main__":
    main()

