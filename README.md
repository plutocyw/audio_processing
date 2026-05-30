# audio-processing

Python scripts for downloading and transcribing podcast audio via the [OpenAI Whisper API](https://platform.openai.com/docs/guides/speech-to-text). Zero pip dependencies — standard library only.

Designed to work standalone or as the backend for a [Claude Code](https://claude.ai/code) skill.

---

## What This Does

Feed it any audio URL or local file. It transcribes via Whisper, then you choose what to do next.

| Step | Required? | Description |
|------|-----------|-------------|
| Transcribe audio | **Required** | Converts any audio to text via Whisper |
| Post-process | Optional | Generate digest, proofread, or use as-is |
| Send by email | Optional | Deliver transcript or digest to your inbox |

For podcasts, `manage.py` adds a full library workflow: subscribe to feeds, browse episodes, download and transcribe with automatic file organization.

---

## Prerequisites

| Requirement | Install | Notes |
|-------------|---------|-------|
| Python 3.8+ | pre-installed on macOS/Linux | — |
| ffmpeg | `brew install ffmpeg` or `sudo apt install ffmpeg` | **Required** — used to compress audio before Whisper |
| OpenAI API key | [platform.openai.com](https://platform.openai.com/api-keys) | **Required** — Whisper transcription |
| himalaya | `brew install himalaya` | Optional — only needed for email delivery |

### Set your API key

Add to `~/.zshrc` (or `~/.bashrc`), then restart your terminal:

```bash
export OPENAI_API_KEY="sk-..."
```

---

## Podcast Workflow (manage.py)

`manage.py` organizes everything under `~/podcasts/` so you never have to remember where files are.

### Storage layout

```
~/podcasts/
  library.json                          ← your subscribed feeds
  lex-fridman-podcast/
    2026-05-28-432-the-future-of-ai/
      audio.mp3                         ← downloaded episode
      transcript.txt                    ← Whisper transcript
      meta.json                         ← episode metadata
    2026-05-21-431-climate-technology/
      ...
```

---

### Step 1 — Find a podcast

Search by name — no need to hunt for the RSS URL yourself:

```bash
python3 manage.py search "lex fridman"
```

```
#    Podcast                                       Episodes  Feed URL
──────────────────────────────────────────────────────────────────────────────────────────
1    Lex Fridman Podcast                                432  https://lexfridman.com/feed/podcast/
2    Lex Fridman Podcast (Video)                        432  https://lexfridman.com/feed/video/
...
```

Uses the iTunes Search API — no account or API key required.

If you already know the RSS URL, you can skip search and go straight to `add`.

---

### Step 2 — Add a podcast

```bash
python3 manage.py add "https://lexfridman.com/feed/podcast/"
```

```
Fetching: https://lexfridman.com/feed/podcast/
Added: Lex Fridman Podcast
  slug:     lex-fridman-podcast
  episodes: 432 in feed
```

The podcast is saved to `~/podcasts/library.json`. You only do this once per feed.

---

### Step 3 — Browse episodes

```bash
python3 manage.py episodes lex-fridman-podcast
# or by index:
python3 manage.py episodes 1
```

```
#    Date          Dur      DL TX  Title
────────────────────────────────────────────────────────────────────────────────
1    May 28, 2026  2h 14m   ·  ·   #432 — The Future of AI
2    May 21, 2026  1h 47m   ✓  ✓   #431 — Climate and Technology
3    May 14, 2026  2h 3m    ✓  ·   #430 — Writing and Creativity
...

  DL = audio downloaded   TX = transcript ready
```

`·` means not yet done, `✓` means already on disk.

---

### Step 4 — Transcribe an episode

```bash
python3 manage.py transcribe lex-fridman-podcast 1
```

This handles everything:
1. Downloads the audio (skips if already on disk)
2. Compresses audio to mono 16 kHz 32 kbps for Whisper
3. Splits into 20-minute chunks if the file is large
4. Transcribes via Whisper API with automatic retry on rate limits
5. Saves `transcript.txt` alongside the audio

**Cost estimate:** Whisper charges ~$0.006/min. A 2-hour episode costs ~**$0.72**.

If you only want to download without transcribing:

```bash
python3 manage.py download lex-fridman-podcast 1
```

---

### Step 5 — View the transcript

```bash
python3 manage.py show lex-fridman-podcast 1
```

---

### Step 6 (Optional) — Post-process

Choose what to do with the transcript. Pipe `show` into Claude:

**Generate a digest:**

```bash
python3 manage.py show lex-fridman-podcast 1 \
  | claude "Write a concise digest: key topics, notable quotes, main takeaways. Format as an article."
```

**Proofread and clean up:**

```bash
python3 manage.py show lex-fridman-podcast 1 \
  | claude "Proofread this transcript. Fix transcription errors, add speaker labels where possible, format for readability."
```

---

### Step 7 (Optional) — Send by email

Requires [himalaya](https://github.com/soywod/himalaya) configured with your email account.

**Send the raw transcript:**

```bash
python3 manage.py show lex-fridman-podcast 1 \
  | himalaya send --subject "Transcript: #432 The Future of AI" --to "you@example.com"
```

**Send a digest:**

```bash
python3 manage.py show lex-fridman-podcast 1 \
  | claude "Write a concise digest: key topics, notable quotes, main takeaways." \
  | himalaya send --subject "Digest: #432 The Future of AI" --to "you@example.com"
```

---

### All manage.py commands

```
python3 manage.py search <name>           Search for a podcast by name (iTunes)
python3 manage.py add <rss_url>           Add a podcast to your library
python3 manage.py list                    List all subscribed podcasts
python3 manage.py episodes <podcast>      Show latest 10 episodes with status
python3 manage.py download <podcast> <ep> Download episode audio only
python3 manage.py transcribe <podcast> <ep>  Transcribe (downloads first if needed)
python3 manage.py show <podcast> <ep>     Print transcript to stdout
```

`<podcast>` can be the index from `list` or the slug (e.g. `lex-fridman-podcast`).  
`<ep>` is the episode number from `episodes` — `1` is always the most recent.

---

## Transcribing Any Audio File (Without manage.py)

The individual scripts work with any audio independently. Supported formats: mp3, mp4, m4a, wav, ogg, flac, webm, and anything else ffmpeg can read.

```bash
# Local file → transcript
python3 transcribe.py /path/to/recording.m4a /path/to/transcript.txt

# URL → download → transcript
python3 download.py "https://example.com/audio.mp3" /tmp/audio.mp3
python3 transcribe.py /tmp/audio.mp3 /tmp/transcript.txt
```

---

## Script Reference

### `manage.py`

Podcast library manager. Stores everything under `~/podcasts/`. See workflow above.

---

### `parse_rss.py`

Fetches a podcast RSS feed and returns the 10 most recent episodes as JSON.

```bash
python3 parse_rss.py <rss_url>
```

Output fields per episode: `index`, `title`, `iso_date`, `published_date`, `duration`, `audio_url`, `slug`

---

### `download.py`

Downloads an audio file from a URL. Retries up to 3 times with a 5-second backoff.

```bash
python3 download.py <url> <output_path>
```

---

### `transcribe.py`

Transcribes an audio file to text using the Whisper API.

```bash
python3 transcribe.py <input_audio> <output_transcript.txt>
```

Handles automatically:
- Compresses to mono 16 kHz 32 kbps (to stay under Whisper's 25 MB limit)
- Splits into 20-minute chunks if the file is large
- Retries with 30-second backoff on 429 rate limit errors

---

## Claude Code Skill

This repo ships with a `/podcast` slash command for [Claude Code](https://claude.ai/code). Clone the repo, open it in Claude Code, and type `/podcast` to get a fully guided interactive workflow.

### Setup

```bash
git clone https://github.com/plutocyw/audio_processing.git
cd audio_processing
```

Open the folder in Claude Code (CLI or IDE extension), then:

```
/podcast
```

### What the skill does

The `/podcast` command walks you through every step conversationally:

1. **Prerequisites check** — verifies ffmpeg and `OPENAI_API_KEY` are ready, tells you exactly what to fix if not
2. **Episode browsing** — paste any RSS URL, or pick from your saved podcast library
3. **Transcription** — shows cost estimate before starting, then runs download + compress + transcribe automatically
4. **Output choice** — choose one:
   - **Digest** — key topics, notable quotes, main takeaways as a formatted article
   - **Proofread** — cleaned-up transcript with speaker labels and paragraph breaks
   - **Raw** — the Whisper transcript as-is
5. **Email delivery** (optional) — sends the result via [himalaya](https://github.com/soywod/himalaya)

### Example session

```
> /podcast

Checking prerequisites... ffmpeg ✓  OPENAI_API_KEY ✓

Your library:
  1  Lex Fridman Podcast   lex-fridman-podcast
  2  99% Invisible         99-invisible

Pick a podcast (or paste a new RSS URL):
> 1

Fetching feed: Lex Fridman Podcast
  1 | May 28, 2026 | 2h 14m | #432 — The Future of AI
  2 | May 21, 2026 | 1h 47m | #431 — Climate and Technology
  ...

Which episode?
> 1

Transcribe "#432 — The Future of AI"?
Estimated cost: ~$0.80  |  Estimated time: ~5 min
Proceed? (yes / no)
> yes

[Downloading... Compressing... Transcribing chunks 1/3, 2/3, 3/3... Done]
Transcript saved: ~/podcasts/lex-fridman-podcast/2026-05-28-432.../transcript.txt

What would you like to do with it?
  1. Generate a digest
  2. Proofread and clean up
  3. Show raw transcript
  4. Nothing — I'll read the file directly
> 1

[Digest output...]

Would you like to send this by email?
> yes

Send to: you@example.com
Subject: Digest: #432 — The Future of AI
Confirm? > yes

Sent.
```
