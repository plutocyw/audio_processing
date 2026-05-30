---
description: Download and transcribe podcast episodes. Browse your library, pick an episode, transcribe via Whisper, then choose to generate a digest, proofread, or get the raw transcript — with optional email delivery.
argument-hint: [rss_url or podcast name]
allowed-tools: Bash, Read
---

# Podcast Transcription Skill

Help the user download and transcribe a podcast episode, then process the result.

The user's input (if any) is: $ARGUMENTS

---

## Step 1 — Check prerequisites

Run these checks before doing anything else:

```bash
# Check ffmpeg
which ffmpeg
```

```bash
# Check API key
echo ${OPENAI_API_KEY:+set}
```

If ffmpeg is missing, tell the user:
> ffmpeg is required. Install it with: `brew install ffmpeg` (macOS) or `sudo apt install ffmpeg` (Linux)
> Then re-run `/podcast`.

If OPENAI_API_KEY is not set, tell the user:
> Your OpenAI API key is not set. Add this to ~/.zshrc and restart your terminal:
> `export OPENAI_API_KEY="sk-..."`
> Then re-run `/podcast`.

Do not continue if either check fails.

---

## Step 2 — Determine the starting point

Check if the user provided an RSS URL or podcast name in $ARGUMENTS.

**If $ARGUMENTS contains an RSS URL** (starts with `http`):
- Skip to Step 3 and use that URL directly without adding to the library

**If $ARGUMENTS is a podcast name or empty**:
- Show the library:
```bash
python3 manage.py list
```
- If the library is empty, ask:
  > No podcasts in your library yet. Paste an RSS feed URL to get started.
  Then wait for input and proceed with that URL.
- If the library has entries, ask the user to pick one by number, or offer to add a new feed.

---

## Step 3 — Browse episodes

If working with a saved podcast (from library):
```bash
python3 manage.py episodes <podcast-slug-or-index>
```

If working with a fresh RSS URL (not yet in library), first fetch and display episodes:
```bash
python3 parse_rss.py "<rss_url>" | python3 -c "
import json, sys
eps = json.load(sys.stdin)
print(f'  # | Date          | Dur    | Title')
print('  ' + '-'*70)
for ep in eps:
    print(f\"  {ep['index']:<3}| {ep['published_date']:<14}| {ep['duration']:<7}| {ep['title']}\")
"
```

Then ask:
> Which episode would you like to transcribe? (Enter the number)

Wait for the user's answer.

---

## Step 4 — Confirm and transcribe

Before transcribing, show a cost estimate. Assume ~$0.006 per minute. If you know the episode duration from the listing, calculate the estimate (e.g. "1h 47m ≈ $0.64"). If unknown, say "cost varies by episode length."

Ask:
> Transcribe episode [N]: "[title]"?
> Estimated cost: ~$X.XX  |  Estimated time: ~Y min
> Proceed? (yes / no)

If no → stop.

If yes:

**For saved podcasts**, run:
```bash
python3 manage.py transcribe <podcast> <episode-number>
```

**For a fresh URL** (not in library), run the full pipeline:
```bash
# Get the audio URL
AUDIO_URL=$(python3 parse_rss.py "<rss_url>" | python3 -c "import json,sys; eps=json.load(sys.stdin); print(eps[<episode-index>]['audio_url'])")
SLUG=$(python3 parse_rss.py "<rss_url>" | python3 -c "import json,sys; eps=json.load(sys.stdin); print(eps[<episode-index>]['slug'])")

# Download
python3 download.py "$AUDIO_URL" "/tmp/${SLUG}.mp3"

# Transcribe
python3 transcribe.py "/tmp/${SLUG}.mp3" "/tmp/${SLUG}.txt"
```

Show progress as each step runs. If any step fails, report the error clearly and stop.

After transcription completes, tell the user where the file was saved.

---

## Step 5 — Choose output format

Ask:
> Transcript is ready. What would you like to do with it?
>
> 1. Generate a digest (key topics, quotes, takeaways)
> 2. Proofread and clean up the transcript
> 3. Show the raw transcript
> 4. Nothing — I'll read the file directly

Wait for the user's choice, then:

**Option 1 — Digest:**
Read the transcript file and generate a digest with this structure:
- **Overview** (2–3 sentences summarising the episode)
- **Key topics** (bullet list)
- **Notable quotes** (2–4 direct quotes with context)
- **Main takeaways** (3–5 actionable or memorable points)

Format it cleanly in markdown.

**Option 2 — Proofread:**
Read the transcript and clean it up:
- Fix obvious Whisper transcription errors (homophones, proper nouns, technical terms)
- Add speaker labels where you can reasonably infer them (e.g. "Host:", "Guest:")
- Break into readable paragraphs
- Preserve all content — do not summarise

Output the cleaned transcript.

**Option 3 — Raw transcript:**
```bash
# For saved podcasts:
python3 manage.py show <podcast> <episode>

# For fresh URL:
cat "/tmp/${SLUG}.txt"
```

**Option 4 — Nothing:** Confirm the file path and stop.

---

## Step 6 (Optional) — Email delivery

After showing the output (digest, proofread, or raw), ask:
> Would you like to send this by email? (yes / no)

If no → done.

If yes:
1. Ask: > Send to which email address?
2. Ask: > Subject line? (suggest a default like "Transcript: [episode title]" or "Digest: [episode title]")
3. Confirm: > Send "[subject]" to [email]? (yes / no)

If confirmed, pipe the output to himalaya:
```bash
cat <<'EOF' | himalaya send --subject "<subject>" --to "<email>"
<content>
EOF
```

If himalaya is not installed, tell the user:
> himalaya is not installed. Install it with: `brew install himalaya`
> Then configure it with your email account: `himalaya account configure`

---

## Notes

- Always use `python3` (not `python`) to run scripts
- Scripts are in the project root — use paths relative to the repo root
- The library lives at `~/podcasts/` — manage.py handles all path logic
- If the user wants to add the fresh RSS URL to their library for future use, offer to run `python3 manage.py add <rss_url>` at the end
