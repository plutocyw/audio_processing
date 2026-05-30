# audio-processing

Podcast download, management, and transcription toolkit using OpenAI Whisper. Zero pip dependencies.

## Scripts

| Script | Purpose |
|--------|---------|
| `manage.py` | Podcast library manager — add feeds, browse episodes, download, transcribe |
| `transcribe.py` | Transcribe any audio file via Whisper API |
| `download.py` | Download an audio file from a URL with retry |
| `parse_rss.py` | Fetch a podcast RSS feed and return episodes as JSON |

## Prerequisites

- **ffmpeg** — required for audio compression (`brew install ffmpeg`)
- **OPENAI_API_KEY** — required for Whisper transcription
- **himalaya** — optional, only for email delivery (`brew install himalaya`)

## manage.py commands

```bash
python3 manage.py search <name>           # search iTunes by podcast name → returns feed URL
python3 manage.py add <rss_url>           # subscribe to a podcast
python3 manage.py list                    # list subscribed podcasts
python3 manage.py episodes <podcast>      # show latest 10 episodes with status
python3 manage.py download <podcast> <ep> # download audio only
python3 manage.py transcribe <podcast> <ep>  # transcribe (downloads first if needed)
python3 manage.py show <podcast> <ep>     # print transcript to stdout
```

`<podcast>` = index from `list` or slug. `<ep>` = episode number (1 = most recent).

## Storage layout

```
~/podcasts/
  library.json
  <podcast-slug>/
    <iso_date>-<episode-slug>/
      audio.mp3
      transcript.txt
      meta.json
```

## Direct transcription (no library)

```bash
python3 transcribe.py <input_audio> <output.txt>
python3 download.py <url> <output.mp3>
python3 parse_rss.py <rss_url>            # returns JSON
```

## Skill

The `/podcast` command in `.claude/commands/podcast.md` provides an interactive workflow that drives these scripts conversationally.
