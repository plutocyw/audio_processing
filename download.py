#!/usr/bin/env python3
"""
download.py — download a podcast audio file with retry logic

Usage:
    python3 download.py <url> <output_path>
"""
import sys
import os
import time
import urllib.request
import urllib.error

MAX_RETRIES = 3
RETRY_DELAY = 5
CONNECT_TIMEOUT = 60
CHUNK_SIZE = 1024 * 1024  # 1 MB


def human_mb(n_bytes):
    return f"{n_bytes / 1024 / 1024:.1f}"


def download(url, output_path):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=CONNECT_TIMEOUT) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                with open(output_path, "wb") as f:
                    while True:
                        chunk = resp.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            print(f"\rDownloading... {human_mb(downloaded)} MB / {human_mb(total)} MB", end="", flush=True)
                        else:
                            print(f"\rDownloading... {human_mb(downloaded)} MB", end="", flush=True)
                print()
            size = os.path.getsize(output_path)
            print(f"Downloaded: {output_path} ({human_mb(size)} MB)")
            return True

        except urllib.error.HTTPError as e:
            print(f"\nHTTP error {e.code}: {e.reason}", file=sys.stderr)
            if e.code in (401, 403, 404):
                return False
        except urllib.error.URLError as e:
            print(f"\nURL error (attempt {attempt}/{MAX_RETRIES}): {e.reason}", file=sys.stderr)
        except Exception as e:
            print(f"\nUnexpected error (attempt {attempt}/{MAX_RETRIES}): {e}", file=sys.stderr)

        if attempt < MAX_RETRIES:
            print(f"Retrying in {RETRY_DELAY}s...", file=sys.stderr)
            time.sleep(RETRY_DELAY)

    print(f"Failed to download after {MAX_RETRIES} attempts: {url}", file=sys.stderr)
    return False


def main():
    if len(sys.argv) != 3:
        print(f"Usage: python3 {sys.argv[0]} <url> <output_path>", file=sys.stderr)
        sys.exit(1)

    url, output_path = sys.argv[1], sys.argv[2]
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    if not download(url, output_path):
        sys.exit(1)


if __name__ == "__main__":
    main()
