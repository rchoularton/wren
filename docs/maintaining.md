# Maintaining Wren

A plain-language guide to running Wren as a public project. You don't need to be a
developer to follow it — this page explains what each piece is, why it exists, and the
routine you'll repeat. If you only read one thing, read [Cutting a release](#cutting-a-release).

## The moving parts, in plain terms

Everything about "managing the project" comes down to a few GitHub features and one npm step.

| Thing | What it is | When you use it |
|---|---|---|
| **Issue** | A single note on GitHub: a bug, an idea, or a task. Each has a number (#12). | Anything to do or track becomes an issue. |
| **Label** | A coloured tag on an issue (`bug`, `enhancement`, `skill-port`). | To sort and filter issues. |
| **Milestone** | A named bucket of issues, one per release (e.g. `0.6`). | To group "what's in the next version." |
| **Project board** | A drag-and-drop board (Todo → In progress → Done) of your issues. | To see everything at a glance. |
| **Release** | A snapshot on GitHub tied to a version (`v0.6.0`) with notes. | Published each time you ship a version. |
| **Tag** | A permanent bookmark in the code history for a version. | Created as part of each release. |
| **npm publish** | The command that makes `npm create wren@latest` serve the new version. | The final step of a release. |

You already have: a CI check that tests every change, an automatic docs website, issue
templates, and a pull-request template. This guide adds the release routine and the board.

## How work flows

1. **An idea or bug becomes an issue.** Use the templates
   ([new issue](https://github.com/rchoularton/wren/issues/new/choose)). Give it a label
   and, if it's slated for a version, a milestone.
2. **It shows on the board.** The [project board](https://github.com/rchoularton/wren/projects)
   tracks it through Todo → In progress → Done.
3. **A change is made in a branch and opened as a pull request (PR).** CI runs automatically
   (it scaffolds a fresh project and checks it works). The PR notes which issue it closes.
4. **The PR is merged to `main`.** If it touched docs, the website redeploys automatically.
5. **When a milestone's issues are all done, you cut a release** (below) and the version goes
   public on npm.

You are both the maintainer and (for now) the only contributor, so in practice you'll often
skip straight from "issue" to "make the change." That's fine — the machinery is there for
when others join.

## Versioning in one paragraph

Wren uses **semantic versioning**: versions look like `MAJOR.MINOR.PATCH` (e.g. `0.6.0`).
Bump **PATCH** (`0.6.0 → 0.6.1`) for small fixes, **MINOR** (`0.6.0 → 0.7.0`) for new
features that don't break anything, and **MAJOR** (`0.x → 1.0`) for the first stable release
or anything that changes how existing projects work. While Wren is pre-1.0, new tools ship
as MINOR bumps. Every version is written down in [`CHANGELOG.md`](changelog.md).

## Cutting a release

The full step-by-step checklist lives in
[`RELEASING.md`](https://github.com/rchoularton/wren/blob/main/RELEASING.md) at the repo
root. In short, each release is: **check → changelog → bump → tag → publish → announce.**
The one step only you can do is `npm publish --auth-type=web` (it needs your passkey). Follow
the checklist top to bottom; it maps every step to an exact command.

## Where the automation already lives

- **CI** (`.github/workflows/ci.yml`) — on every push and PR, scaffolds a fresh project on
  Node 18 and 20 and confirms it installs cleanly. This is your safety net.
- **Docs** (`.github/workflows/docs.yml`) — on every change under `docs/`, rebuilds and
  publishes this website automatically.
- **Release** (`.github/workflows/release.yml`, optional) — when you push a `v*` tag, drafts
  the GitHub Release for you; it can also publish to npm automatically if you add an npm
  automation token (see the release workflow's comments). Until then, publishing stays a
  manual passkey step, which is perfectly fine.

## If something goes wrong

- **A release had a bug** → don't edit the published version; cut the next PATCH (e.g.
  `0.6.1`) with the fix. Published versions are permanent.
- **The docs site didn't update** → check the "Deploy docs" run under the repo's Actions tab;
  confirm Settings → Pages source is the `gh-pages` branch.
- **You're unsure what's next** → the [roadmap](roadmap.md) and the
  [milestones](https://github.com/rchoularton/wren/milestones) are the source of truth.
