# Wren — terminal demo
# Rendered with VHS (https://github.com/charmbracelet/vhs)
#
# Live claude -p calls: /paper (portfolio orientation) and /draft example-paper
# (the Phase 7 gold-standard gate — the signature beat).
#
# Sync note: Wait+Screen proved unreliable on this machine for the multi-second
# real commands below (npm create's readline->subprocess handoff, and claude -p
# latency) — it repeatedly timed out even though the underlying command had
# genuinely completed (confirmed by inspecting rendered frames from Sleep-based
# runs). Fixed Sleep durations, sized from measured real timings, are used
# instead. A hidden claude -p warm-up call absorbs first-call cold-start
# latency before the two live on-screen beats, so their windows can be tight.
# `2>/dev/null` on every claude -p call suppresses the (harmless, cosmetic)
# workspace-trust stderr warning — verified it does not affect the real stdout
# response.

Output assets/demo.gif
Output assets/demo.mp4

Set Shell "bash"
Set FontSize 22
Set Width 1200
Set Height 800
Set Padding 20
Set Theme "Dracula"
Set TypingSpeed 50ms

# --- Prep (hidden): fresh scratch dir, short path for clean on-screen output ---
Hide
Type "cd ~/wren-demo && rm -rf my-research && clear"
Enter
Sleep 500ms
Show

# --- Beat 1: Install ---
Type "npm create wren@latest my-research -- --yes"
Enter
Sleep 20s

# --- Hidden: cd in + warm up claude (absorbs cold-start latency) ---
Hide
Type "cd my-research && clear"
Enter
Sleep 500ms
Type `claude -p "ok" >/dev/null 2>&1`
Enter
Sleep 35s
Type "clear"
Enter
Show

# --- Beat 2: Config ---
Type "head -20 research-config.yml"
Enter
Sleep 2s
Type `echo "Every field above is editable — change it and re-run ./setup.sh"`
Enter
Sleep 1.5s

# --- Beat 3: Orient ---
Type "clear"
Enter
Type `echo "Open the project in Claude Code..."`
Enter
Sleep 800ms
Type `claude -p "/paper" 2>/dev/null`
Enter
Sleep 30s

# --- Beat 4: SIGNATURE — the Phase 7 gold-standard gate ---
Type "clear"
Enter
Type `claude -p "/draft example-paper" 2>/dev/null`
Enter
Sleep 30s

# --- Beat 5: Build ---
Hide
Type 'printf "Climate Migration Study\n\n# Abstract\n\nPlaceholder draft text to demonstrate the build pipeline.\n" > papers/example-paper/drafts/example-paper_draft_v1.md'
Enter
Show
Type "clear"
Enter
Type "npm run paper:build -- example-paper 2>/dev/null"
Enter
Sleep 5s

# --- Beat 6: Self-improving loop (caption) ---
Type "clear"
Enter
Type `echo "Every /retro hooks findings back into the SessionStart context — the system tunes itself as you work."`
Enter
Sleep 2.5s

# --- Beat 7: Close ---
Type "clear"
Enter
Type `echo "Docs: https://rchoularton.github.io/wren/"`
Enter
Type `echo "Grow it: flip a backend, add Zotero, enable corpus memory."`
Enter
Sleep 3s
