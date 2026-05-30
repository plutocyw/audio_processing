#!/usr/bin/env python3
"""
transcribe.py — compress, chunk, and transcribe an audio file via OpenAI Whisper API

Usage:
    OPENAI_API_KEY=sk-... python3 transcribe.py <input_audio> <output_transcript.txt>

Requirements:
    - ffmpeg on PATH
    - OPENAI_API_KEY environment variable

The script handles:
    - Compression to mono 16 kHz 32 kbps (to stay under Whisper's 25 MB limit)
    - Auto-chunking into 20-minute segments for long files
    - Retry with backoff on 429 rate limit errors
"""
import sys
import os
import glob
import time
import subprocess
import urllib.request
import urllib.error
import uuid

MAX_SIZE_BYTES = 24 * 1024 * 1024   # 24 MB (Whisper hard limit is 25 MB)
CHUNK_SIZE_BYTES = 20 * 1024 * 1024 # trigger chunking if > 20 MB after compression
SEGMENT_SECS = 1200                  # 20-minute chunks
MAX_RETRIES = 3
RETRY_DELAY = 30  # seconds to wait on 429


def human_mb(n_bytes):
    return f"{n_bytes / 1024 / 1024:.1f}"


def run_ffmpeg(args, description):
    result = subprocess.run(
        ["ffmpeg"] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        err = result.stderr.decode(errors="replace").strip()
        print(f"ffmpeg error ({description}):\n{err}", file=sys.stderr)
        sys.exit(1)


def compress(input_path):
    compressed = "/tmp/audio_compressed.mp3"
    in_size = os.path.getsize(input_path)
    print(f"Compressing: {human_mb(in_size)} MB → target ~32 kbps mono 16 kHz...")
    run_ffmpeg(
        ["-y", "-i", input_path, "-ar", "16000", "-ac", "1", "-b:a", "32k", compressed],
        "compress",
    )
    out_size = os.path.getsize(compressed)
    print(f"Compressed: {human_mb(in_size)} MB → {human_mb(out_size)} MB")
    return compressed


def split_chunks(audio_path):
    chunk_pattern = f"/tmp/audio_chunk_{uuid.uuid4().hex[:8]}_%03d.mp3"
    print(f"File > {human_mb(CHUNK_SIZE_BYTES)} MB — splitting into 20-min chunks...")
    run_ffmpeg(
        [
            "-y", "-i", audio_path,
            "-f", "segment",
            "-segment_time", str(SEGMENT_SECS),
            "-ar", "16000", "-ac", "1", "-b:a", "32k",
            chunk_pattern,
        ],
        "split chunks",
    )
    glob_pattern = chunk_pattern.replace("%03d", "*")
    chunks = sorted(glob.glob(glob_pattern))
    print(f"Created {len(chunks)} chunks.")
    return chunks, glob_pattern


def whisper_transcribe(audio_path, api_key, chunk_label):
    url = "https://api.openai.com/v1/audio/transcriptions"
    boundary = uuid.uuid4().hex
    filename = os.path.basename(audio_path)

    with open(audio_path, "rb") as f:
        audio_data = f.read()

    body_parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="model"\r\n\r\nwhisper-1\r\n'.encode(),
        f'--{boundary}\r\nContent-Disposition: form-data; name="response_format"\r\n\r\ntext\r\n'.encode(),
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: audio/mpeg\r\n\r\n'.encode()
        + audio_data + b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    body = b"".join(body_parts)

    for attempt in range(1, MAX_RETRIES + 1):
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            status = e.code
            body_text = e.read().decode("utf-8", errors="replace")
            if status == 429 and attempt < MAX_RETRIES:
                print(f"\n429 rate limit on {chunk_label} (attempt {attempt}/{MAX_RETRIES}) — waiting {RETRY_DELAY}s...", file=sys.stderr)
                time.sleep(RETRY_DELAY)
                continue
            print(f"\nWhisper API error on {chunk_label}: HTTP {status}\n{body_text}", file=sys.stderr)
            sys.exit(1)
        except urllib.error.URLError as e:
            print(f"\nNetwork error on {chunk_label}: {e.reason}", file=sys.stderr)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                continue
            sys.exit(1)

    print(f"Failed to transcribe {chunk_label} after {MAX_RETRIES} attempts.", file=sys.stderr)
    sys.exit(1)


def main():
    if len(sys.argv) != 3:
        print(f"Usage: python3 {sys.argv[0]} <input_audio> <output_transcript.txt>", file=sys.stderr)
        sys.exit(1)

    input_audio, output_path = sys.argv[1], sys.argv[2]

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(input_audio):
        print(f"Error: input file not found: {input_audio}", file=sys.stderr)
        sys.exit(1)

    compressed = compress(input_audio)
    compressed_size = os.path.getsize(compressed)
    glob_pattern = None

    if compressed_size > CHUNK_SIZE_BYTES:
        chunk_paths, glob_pattern = split_chunks(compressed)
    else:
        chunk_paths = [compressed]

    transcripts = []
    total = len(chunk_paths)
    for i, chunk in enumerate(chunk_paths, 1):
        label = f"chunk {i}/{total}" if total > 1 else "audio"
        print(f"Transcribing {label}...")
        text = whisper_transcribe(chunk, api_key, label)
        transcripts.append(text.strip())

    full_transcript = "\n\n".join(transcripts)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_transcript)

    if glob_pattern:
        for p in glob.glob(glob_pattern):
            try:
                os.remove(p)
            except OSError:
                pass

    print(f"Transcript saved: {output_path} ({len(full_transcript):,} chars)")


if __name__ == "__main__":
    main()
