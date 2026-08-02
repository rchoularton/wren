# Getting Started

This page takes you from nothing to a working research assistant with persistent memory and a paper you can build, in about 15 minutes.

## 0. Install and open Claude Code

The kit is driven entirely from [Claude Code](https://claude.com/claude-code), Anthropic's terminal-based agentic coding tool. If you don't have it yet:

1. Install it following the instructions at [claude.com/claude-code](https://claude.com/claude-code).
2. Sign in with your Anthropic account.
3. Confirm it runs by opening a terminal and typing `claude` in any folder.

Everything below — the scaffolder, the paper workflow, every `/skill` — runs inside a Claude Code session in your project folder.

## 1. Scaffold

```bash
npm create wren@latest my-research
cd my-research
```

You'll answer a few prompts (name, project namespace, database backend, reference manager). Everything is editable later in `research-config.yml`.

!!! tip "Prefer to clone the repo directly?"
    ```bash
    cp research-config.example.yml research-config.yml   # edit a handful of fields
    ./setup.sh
    ```

The scaffolder then renders your templates, installs the hooks, and runs a verification pass. A green summary means you're ready.

## 2. (Optional) add secrets

Only if you enabled an integration:

```bash
cp .env.example .env    # then paste keys for whatever you turned on
```

The Core needs none of these.

## 3. Open in Claude Code

Open the folder in Claude Code. On start, the **SessionStart hook** surfaces any recent `/retro` learnings (none yet — that's expected) and, on a fresh project, nudges you to run the guided onboarding.

## 4. Run the guided onboarding

Run:

```
/setup wren
```

This is the recommended first step. It gives you a short tour of the system, asks a few questions about your research, sets up the right tools (database backend, references) to match, and starts your first paper — or plans a paper series. See [Welcome](welcome.md) for the same tour in writing.

Prefer to jump straight in? Run `/paper`, or duplicate the example by hand:

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

It proposes a short learning and, on your approval, writes a `learning_<date>_*.md` into your Claude memory directory and indexes it. Next session, that learning resurfaces automatically. That's the self-improving loop — see [Concepts](concepts.md) for the full memory model.

## 6. Build a paper to Word

Put some Markdown in `papers/my-first-paper/drafts/`, then:

```bash
npm run paper:setup                     # one-time: installs python-docx + markdown
npm run paper:status
npm run paper:build my-first-paper      # Markdown → .docx
npm run paper:extract my-first-paper    # .docx → Markdown (round-trip)
```

!!! note
    `paper:setup` is a one-time step — the Word build/extract engine needs `python-docx` and `markdown` (in `requirements.txt`). Scaffolding itself doesn't install them, so run this once before your first build. More detail in [Papers & the build engine](guides/papers.md).

## Where things live

| You want to… | Go to |
|---|---|
| Change your config | `research-config.yml` (re-run `./setup.sh`) — see [Configuration](configuration.md) |
| Read how memory is organised | [Concepts](concepts.md) |
| Set up a real database | [Databases](guides/databases.md) |
| Connect Zotero / other MCPs | [References & integrations](guides/references.md) |
| Toggle corpus memory | `research-config.yml` → `tiers.research_memory` — see [Corpus memory](guides/corpus-memory.md) |

## Troubleshooting

- **Hooks not firing?** `python3 scripts/setup/install_hooks.py` (makes them executable). Confirm `.claude/settings.json` exists.
- **`{{TOKENS}}` still in CLAUDE.md?** Re-run `./setup.sh` — the renderer didn't complete.
- **PyYAML error?** `python3 -m pip install pyyaml`.
- **`paper:build` says "Missing a dependency" / `No module named 'docx'`?** Run `npm run paper:setup` once.
- **Verify anytime:** `npm run setup:verify`.
