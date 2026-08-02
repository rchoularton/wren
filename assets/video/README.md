# Wren — making the narrated setup video

Everything you need to produce a ~2-minute narrated walkthrough of `/setup wren`. You don't
need video-editing experience; the "easy path" below uses a free drag-and-drop editor.

**Files here:**
- `narration.md` — the voiceover script, with timecodes and on-screen cues.
- `narration.srt` — the captions (subtitles), timed to the script.

The plan: **record the screen → record your voice reading the script → lay them together →
add the captions → upload.**

---

## 1. Record the screen (~2 min)

The onboarding is a real conversation, so record a real session — it looks far better than a
scripted fake.

- **macOS:** press `Cmd-Shift-5` → "Record Selected Portion" (or record the whole screen).
- Make the terminal **big and legible**: font size ~22, window ~1200×800, a clean theme.
- Then actually do it, unhurried:
  1. `npm create wren@latest my-research` — let the wren + scaffold show, ending in "Install verified".
  2. `cd my-research`, open it in Claude Code.
  3. Run `/setup wren` and go through the tour + interview, answering **briefly** (the
     voiceover carries the detail — the screen just needs to *show* the back-and-forth).
  4. Stop when your first paper is set up.
- Save it as `screen.mov`. Don't worry about dead time or small mistakes — you'll trim in the edit.

## 2. Record the voice

Read `narration.md` in your own voice, plainly. Two ways:

- **Your voice (recommended):** `Cmd-Shift-5` can't record audio-only cleanly, so use
  QuickTime → File → New Audio Recording, or the Voice Memos app / your phone. Read the whole
  script in one take; re-read any line you fumble and keep going. Save as `voice.m4a`.
- **A synthesized voice (if you'd rather not record):** macOS can speak the script —
  `say -v Samantha -f narration.txt -o voice.aiff` (strip the timecodes/cues into a plain
  `narration.txt` first). Or paste the script into any text-to-speech tool and export the audio.

## 3. Put them together

**Easy path — a drag-and-drop editor (iMovie on Mac, or CapCut, both free):**
1. Drag `screen.mov` onto the timeline; **mute its audio** (right-click → detach/mute).
2. Drag `voice.m4a` under it as the audio track.
3. Nudge the video clips so what's on screen roughly matches what you're saying (trim dead
   time so it stays ~2 min).
4. Add captions: import `narration.srt` (CapCut: "Captions → import"; iMovie: add as titles),
   or turn them on when you upload (step 4).
5. Export as `wren-setup.mp4` (1080p is plenty).

**Command-line path (optional, if you like `ffmpeg`):**
```bash
# 1. Lay the voice over the (muted) screen recording, end when the shorter one ends:
ffmpeg -i screen.mov -i voice.m4a -map 0:v -map 1:a -c:v libx264 -shortest wren-setup.mp4
# 2. Burn the captions in (optional — or attach them as a soft track / add on YouTube):
ffmpeg -i wren-setup.mp4 -vf "subtitles=narration.srt" wren-setup-captioned.mp4
```

## 4. Host it and show it off

- **Upload to YouTube as *Unlisted*** (shareable by link, not listed publicly), and add
  `narration.srt` as the subtitle track (YouTube → Subtitles → upload file). An unlisted video
  is the simplest thing to embed and costs nothing.
- **Link it from the README:** GitHub READMEs can't embed a YouTube player, so add a clickable
  thumbnail that links to the video (reuse `assets/demo.gif` or a poster frame):
  ```markdown
  [![Watch the 2-minute setup walkthrough](assets/demo.gif)](https://youtu.be/YOUR_VIDEO_ID)
  ```
- **Embed it in the docs site:** mkdocs pages allow HTML, so on `docs/index.md` or
  `docs/getting-started.md`:
  ```html
  <iframe width="720" height="405" src="https://www.youtube.com/embed/YOUR_VIDEO_ID"
    title="Wren setup" frameborder="0" allowfullscreen></iframe>
  ```

## Tips

- Keep it **under ~2 minutes** — attention drops fast; the script is timed for it.
- Legible text beats fancy editing. Big font, calm pace, trim the waiting.
- The existing silent `assets/demo.gif` stays as the quick auto-playing teaser in the README;
  this narrated video is the richer "show me how it works" companion.
