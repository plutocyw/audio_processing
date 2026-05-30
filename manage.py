#!/usr/bin/env python3
"""
manage.py — podcast library manager

Commands:
    add <rss_url>               Add a podcast feed to your library
    list                        List subscribed podcasts
    episodes <podcast>          Show latest episodes with download/transcript status
    download <podcast> <ep>     Download an episode's audio
    transcribe <podcast> <ep>   Transcribe an episode (downloads first if needed)
    show <podcast> <ep>         Print the transcript to stdout

<podcast>  podcast index from `list`, or its slug
<ep>       episode index from `episodes` (1 = most recent)

Storage layout:
    ~/podcasts/
      library.json
      <podcast-slug>/
        <iso_date>-<episode-slug>/
          audio.mp3
          transcript.txt
          meta.json
"""
import sys
import os
import json
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import date

LIBRARY_DIR = Path.home() / "podcasts"
LIBRARY_FILE = LIBRARY_DIR / "library.json"
SCRIPT_DIR = Path(__file__).parent


# ── Helpers ───────────────────────────────────────────────────────────────────

def die(msg):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def load_library():
    if not LIBRARY_FILE.exists():
        return {"podcasts": []}
    with open(LIBRARY_FILE) as f:
        return json.load(f)


def save_library(lib):
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    with open(LIBRARY_FILE, "w") as f:
        json.dump(lib, f, indent=2, ensure_ascii=False)


def slugify(text, max_len=60):
    import re
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return text[:max_len]


def resolve_podcast(lib, ref):
    podcasts = lib["podcasts"]
    if not podcasts:
        die("No podcasts in library. Run:\n  python3 manage.py add <rss_url>")
    try:
        idx = int(ref) - 1
        if 0 <= idx < len(podcasts):
            return podcasts[idx]
        die(f"Podcast index out of range (1–{len(podcasts)})")
    except ValueError:
        for p in podcasts:
            if p["slug"] == ref:
                return p
        die(f"Podcast not found: {ref!r}\nRun `python3 manage.py list` to see available podcasts.")


def resolve_ep_index(ref, count):
    try:
        idx = int(ref) - 1
        if 0 <= idx < count:
            return idx
        die(f"Episode index out of range (1–{count})")
    except ValueError:
        die(f"Episode must be a number, got: {ref!r}")


def fetch_episodes(rss_url):
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "parse_rss.py"), rss_url],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        die(f"Failed to fetch feed:\n{result.stderr.strip()}")
    return json.loads(result.stdout)


def episode_dir(podcast, ep):
    prefix = ep["iso_date"] + "-" if ep.get("iso_date") else ""
    return LIBRARY_DIR / podcast["slug"] / f"{prefix}{ep['slug']}"


def episode_status(podcast, ep):
    d = episode_dir(podcast, ep)
    return (d / "audio.mp3").exists(), (d / "transcript.txt").exists()


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_add(args):
    if not args:
        die("Usage: manage.py add <rss_url>")
    rss_url = args[0]

    print(f"Fetching: {rss_url}")
    req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            xml_data = resp.read()
    except Exception as e:
        die(f"Could not fetch feed: {e}")

    root = ET.fromstring(xml_data)
    channel = root.find("channel")
    if channel is None:
        die("Invalid RSS feed — no <channel> element found")

    title = (channel.findtext("title") or "").strip()
    if not title:
        die("Could not read podcast title from feed")

    slug = slugify(title)
    lib = load_library()

    for p in lib["podcasts"]:
        if p["rss_url"] == rss_url or p["slug"] == slug:
            print(f"Already in library: {p['title']}  [{p['slug']}]")
            return

    lib["podcasts"].append({
        "slug": slug,
        "title": title,
        "rss_url": rss_url,
        "added": date.today().isoformat(),
    })
    save_library(lib)

    # Count episodes without printing them
    items = root.findall("channel/item")
    print(f"Added: {title}")
    print(f"  slug:     {slug}")
    print(f"  episodes: {len(items)} in feed")
    print(f"\nNext steps:")
    print(f"  python3 manage.py episodes {slug}")


def cmd_list(args):
    lib = load_library()
    podcasts = lib["podcasts"]
    if not podcasts:
        print("No podcasts yet.\n\nAdd one:\n  python3 manage.py add <rss_url>")
        return
    print(f"{'#':<4} {'Title':<42} Slug")
    print("─" * 72)
    for i, p in enumerate(podcasts, 1):
        print(f"{i:<4} {p['title']:<42} {p['slug']}")


def cmd_episodes(args):
    if not args:
        die("Usage: manage.py episodes <podcast>")
    lib = load_library()
    podcast = resolve_podcast(lib, args[0])

    print(f"Fetching feed: {podcast['title']}")
    episodes = fetch_episodes(podcast["rss_url"])

    print(f"\n{'#':<4} {'Date':<13} {'Dur':<8} DL TX  Title")
    print("─" * 80)
    for ep in episodes:
        has_audio, has_tx = episode_status(podcast, ep)
        dl = "✓" if has_audio else "·"
        tx = "✓" if has_tx else "·"
        title = ep["title"]
        if len(title) > 53:
            title = title[:52] + "…"
        print(f"{ep['index']:<4} {ep['published_date']:<13} {ep['duration']:<8} {dl}  {tx}   {title}")

    print("\n  DL = audio downloaded   TX = transcript ready")
    slug = podcast["slug"]
    print(f"\n  Download ep 1:    python3 manage.py download {slug} 1")
    print(f"  Transcribe ep 1:  python3 manage.py transcribe {slug} 1")


def cmd_download(args):
    if len(args) < 2:
        die("Usage: manage.py download <podcast> <episode>")
    lib = load_library()
    podcast = resolve_podcast(lib, args[0])

    print(f"Fetching feed: {podcast['title']}")
    episodes = fetch_episodes(podcast["rss_url"])
    ep = episodes[resolve_ep_index(args[1], len(episodes))]

    dest_dir = episode_dir(podcast, ep)
    audio_path = dest_dir / "audio.mp3"

    if audio_path.exists():
        print(f"Already downloaded: {audio_path}")
        return

    dest_dir.mkdir(parents=True, exist_ok=True)
    with open(dest_dir / "meta.json", "w") as f:
        json.dump(ep, f, indent=2, ensure_ascii=False)

    print(f"Episode: {ep['title']}")
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "download.py"), ep["audio_url"], str(audio_path)]
    )
    if result.returncode != 0:
        sys.exit(1)

    print(f"\nSaved: {audio_path}")
    print(f"Next:  python3 manage.py transcribe {podcast['slug']} {args[1]}")


def cmd_transcribe(args):
    if len(args) < 2:
        die("Usage: manage.py transcribe <podcast> <episode>")
    lib = load_library()
    podcast = resolve_podcast(lib, args[0])

    print(f"Fetching feed: {podcast['title']}")
    episodes = fetch_episodes(podcast["rss_url"])
    ep = episodes[resolve_ep_index(args[1], len(episodes))]

    dest_dir = episode_dir(podcast, ep)
    audio_path = dest_dir / "audio.mp3"
    transcript_path = dest_dir / "transcript.txt"

    if transcript_path.exists():
        print(f"Already transcribed: {transcript_path}")
        return

    if not audio_path.exists():
        print("Audio not yet downloaded — fetching first...")
        cmd_download([args[0], args[1]])

    if not audio_path.exists():
        die("Download failed — cannot transcribe")

    if not os.environ.get("OPENAI_API_KEY"):
        die("OPENAI_API_KEY is not set.\nExport it first:\n  export OPENAI_API_KEY=sk-...")

    print(f"Transcribing: {ep['title']}")
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "transcribe.py"), str(audio_path), str(transcript_path)]
    )
    if result.returncode != 0:
        sys.exit(1)

    print(f"\nTranscript: {transcript_path}")
    print(f"View:       python3 manage.py show {podcast['slug']} {args[1]}")


def cmd_show(args):
    if len(args) < 2:
        die("Usage: manage.py show <podcast> <episode>")
    lib = load_library()
    podcast = resolve_podcast(lib, args[0])

    episodes = fetch_episodes(podcast["rss_url"])
    ep = episodes[resolve_ep_index(args[1], len(episodes))]

    transcript_path = episode_dir(podcast, ep) / "transcript.txt"
    if not transcript_path.exists():
        die(
            f"No transcript yet for this episode.\n"
            f"Run: python3 manage.py transcribe {podcast['slug']} {args[1]}"
        )

    with open(transcript_path) as f:
        print(f.read())


# ── Entry point ───────────────────────────────────────────────────────────────

COMMANDS = {
    "add": cmd_add,
    "list": cmd_list,
    "episodes": cmd_episodes,
    "download": cmd_download,
    "transcribe": cmd_transcribe,
    "show": cmd_show,
}

USAGE = """\
Usage: python3 manage.py <command> [args]

Commands:
  add <rss_url>               Add a podcast to your library
  list                        List subscribed podcasts
  episodes <podcast>          Show latest episodes with download/transcript status
  download <podcast> <ep>     Download episode audio
  transcribe <podcast> <ep>   Transcribe episode (downloads first if needed)
  show <podcast> <ep>         Print transcript to stdout

<podcast>  — index from `list`, or slug (e.g. lex-fridman-podcast)
<ep>       — episode index from `episodes`  (1 = most recent)

Files are stored under ~/podcasts/
"""


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(USAGE)
        sys.exit(0 if len(sys.argv) < 2 else 1)
    COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
