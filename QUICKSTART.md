# Quickstart — your first 15 minutes

This walks you from nothing to a working research assistant with persistent memory and a paper you can build.

## 1. Scaffold

```bash
npm create research-assistant@latest my-research
cd my-research
```

You'll answer a few prompts (name, project namespace, database backend, reference manager). Everything is editable later in `research-config.yml`.

> Prefer to clone? `cp research-config.example.yml research-config.yml`, edit it, then run `./setup.sh`.

The scaffolder then renders your templates, installs the hooks, and runs a verification pass. A green summary means you're ready.

## 2. (Optional) add secrets

Only if you enabled an integration:

```bash
cp .env.example .env    # then paste keys for whatever you turned on
```

The Core needs none of these.

## 3. Open in Claude Code

Open the folder in Claude Code. On start, the **SessionStart hook** surfaces any recent `/retro` learnings (none yet — that's expected).

## 4. Start a paper

Run:

```
/paper
```

Duplicate the example to begin a real one:

```bash
cp -r papers/example-paper papers/my-first-paper
echo "my-first-paper" > .current_paper
```

Edit `papers/my-first-paper/STATUS.md` frontmatter (title, journal, phase). From now on the **UserPromptSubmit hook** injects that paper's status into every turn so the assistant always knows what you're working on.

## 5. See memory capture

After doing some work, run:

```
/retro
```

It proposes a short learning and, on your approval, writes a `learning_<date>_*.md` into your Claude memory directory and indexes it. Next session, that learning resurfaces automatically. That's the self-improving loop.

## 6. Build a paper to Word

Put some Markdown in `papers/my-first-paper/drafts/`, then:

```bash
npm run paper:status
npm run paper:build my-first-paper      # Markdown → .docx
npm run paper:extract my-first-paper    # .docx → Markdown (round-trip)
```

## Where things live

| You want to… | Go to |
|---|---|
| Change your config | `research-config.yml` (re-run `./setup.sh`) |
| Read how memory is organised | `CLAUDE_REFERENCE.md` → Memory Architecture |
| Set up a real database | `docs/database.md` |
| Connect Zotero / other MCPs | `docs/integrations.md` |
| Enable an add-on suite | `research-config.yml` → `tiers:` |

## Troubleshooting

- **Hooks not firing?** `python3 scripts/setup/install_hooks.py` (makes them executable). Confirm `.claude/settings.json` exists.
- **`{{TOKENS}}` still in CLAUDE.md?** Re-run `./setup.sh` — the renderer didn't complete.
- **PyYAML error?** `python3 -m pip install pyyaml`.
- **Verify anytime:** `npm run setup:verify`.
