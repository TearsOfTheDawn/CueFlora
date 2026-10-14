#!/usr/bin/env python3
"""Test script to upload a local audio file to the Whisper API.

Bypasses native messaging and yt-dlp download — useful for isolating
transcription / SSL issues.

Usage:
    # Uses OPENAI_API_KEY env var by default
    python -m cueflora_host.test_whisper path/to/audio.m4a

    # Explicit key and model
    python -m cueflora_host.test_whisper audio.webm --api-key sk-... --model whisper-1

    # Use Groq
    python -m cueflora_host.test_whisper audio.mp3 \
        --base-url https://api.groq.com/openai/v1 \
        --api-key gsk_... \
        --model whisper-large-v3-turbo

    # Match extension settings more closely
    python -m cueflora_host.test_whisper audio.m4a \
        --language en \
        --prompt "Product names include cueflora and yt-dlp"
"""

import argparse
import json
import os
import sys

from .whisper import (
    DEFAULT_MAX_API_ATTEMPTS,
    WHISPER_FORMATS,
    build_transcription_params,
    parse_cues,
    transcribe,
)


def main():
    parser = argparse.ArgumentParser(
        description="Test Whisper API transcription with a local file"
    )
    parser.add_argument("audio_file", help="Path to an audio file to transcribe")
    parser.add_argument(
        "--api-key",
        default=os.environ.get("OPENAI_API_KEY"),
        help="API key (default: $OPENAI_API_KEY)",
    )
    parser.add_argument(
        "--base-url", required=True, help="Your service's API base URL"
    )
    parser.add_argument(
        "--model", required=True, help="Your transcription model name"
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=DEFAULT_MAX_API_ATTEMPTS,
        help=f"Max retry attempts (default: {DEFAULT_MAX_API_ATTEMPTS})",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print raw API response instead of parsed cues",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Optional input language (ISO-639-1), e.g. en, es, ja",
    )
    parser.add_argument(
        "--prompt",
        default=None,
        help="Optional transcription prompt (style/spelling guidance)",
    )
    args = parser.parse_args()

    if not args.api_key:
        print(
            "Error: No API key. Set OPENAI_API_KEY or pass --api-key", file=sys.stderr
        )
        sys.exit(1)

    audio_path = os.path.abspath(args.audio_file)
    if not os.path.exists(audio_path):
        print(f"Error: File not found: {audio_path}", file=sys.stderr)
        sys.exit(1)

    ext = os.path.splitext(audio_path)[1].lstrip(".").lower()
    if ext not in WHISPER_FORMATS:
        print(
            f"Warning: .{ext} may not be accepted by Whisper API (supported: {', '.join(sorted(WHISPER_FORMATS))})",
            file=sys.stderr,
        )

    file_size = os.path.getsize(audio_path)
    print(f"File: {audio_path}")
    print(f"Size: {file_size / 1024 / 1024:.2f} MB")
    print(f"Model: {args.model}")
    print(f"URL: {args.base_url}/audio/transcriptions")
    print(
        f"Params: {build_transcription_params(args.model, args.language, args.prompt)}"
    )
    print()

    try:
        print("Uploading...")
        result = transcribe(
            audio_path,
            args.api_key,
            args.base_url,
            args.model,
            max_attempts=args.max_attempts,
            language=args.language,
            prompt=args.prompt,
        )
        print("Success!\n")

        if args.raw:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Raw response keys: {list(result.keys())}")
            if "duration" in result:
                print(f"Duration: {result['duration']:.1f}s")
            print()

            cues = parse_cues(result)
            print(f"Parsed {len(cues)} cue(s):\n")
            for i, cue in enumerate(cues):
                start = cue["startMs"] / 1000
                end = cue["endMs"] / 1000
                print(f"  [{start:7.2f} - {end:7.2f}] {cue['text']}")

    except RuntimeError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
