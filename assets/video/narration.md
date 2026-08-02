# Wren — narrated setup video: narration script

A ~2-minute voiceover for a screen recording of a real `/setup wren` session. Read it in
your own voice, plainly and unhurried. Timecodes are guides, not gospel — record the screen
first, then read to match. `[SCREEN]` notes say what should be visible.

Total target: ~110–120 seconds.

---

**[0:00–0:10] — Open**
`[SCREEN: an empty terminal]`

> This is Wren — a research assistant that runs entirely in your terminal, through Claude
> Code. Let me show you how you get started, from nothing, in about two minutes.

**[0:10–0:28] — Install**
`[SCREEN: type `npm create wren@latest my-research` — the little wren appears, the scaffold runs, ending in "Install verified"]`

> You start with one command. Wren scaffolds a fresh project, sets up its memory and its
> safety rules, and checks everything installed cleanly. No accounts, no database, nothing
> external required.

**[0:28–0:50] — The guided tour**
`[SCREEN: open the project in Claude Code, run `/setup wren`; the welcome + tour messages appear]`

> Then you run one thing: setup wren. Instead of dropping you at a blank page, it gives you a
> short guided tour — how your memory persists across sessions, the fourteen-phase path a
> paper takes, and the rule that you never write prose until your analysis is frozen and
> checked.

**[0:50–1:15] — The interview**
`[SCREEN: the interview — Wren asks about research interests, data, paper ideas; you answer]`

> After the tour, it interviews you. What do you work on. What data you use. What you want to
> write. It's a conversation, one question at a time — and it listens, so what you say shapes
> how the whole system is set up for you.

**[1:15–1:32] — Tools set up to match**
`[SCREEN: Wren recommends and configures a database backend + reference manager based on your answers]`

> From your answers, it sets up the right tools. A simple file store, or a real database if
> your data needs one. Your reference manager. Only what you'll actually use — matched to the
> work you described.

**[1:32–1:52] — Your first paper**
`[SCREEN: Wren scaffolds the first paper (or a paper series) and sets it as current]`

> And you don't finish empty-handed. It sets up your first paper — or plans out a whole series
> — so the moment onboarding ends, you're already working on something real.

**[1:52–2:05] — Close**
`[SCREEN: the docs site / the wren logo]`

> That's Wren. It's free, it's open source, and you can start right now with: npm create wren.
> Everything you've seen is at rchoularton dot github dot io slash wren.

---

## Notes for recording

- Keep the terminal font large (the demo tape uses size 22) and the window ~1200×800 so text
  is legible on small screens.
- Do the interview answers briefly on screen — the voiceover carries the meaning; the screen
  just needs to *show* the back-and-forth, not be readable word-for-word.
- If a step runs long (a model reply takes a few seconds), you can trim dead time in the edit;
  the narration is written to survive light cuts.
