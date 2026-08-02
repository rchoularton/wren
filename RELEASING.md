# Releasing Wren

The repeatable checklist for shipping a new version of `create-wren`. Plain-language
background is in [docs/maintaining.md](docs/maintaining.md); this file is the exact steps.

Each release is: **check → changelog → bump → tag → publish → announce.**

## Before you start

- Be on `main` with a clean tree: `git checkout main && git pull && git status`.
- CI is green on `main` (check the repo's **Actions** tab).
- Decide the new version with [semver](docs/maintaining.md#versioning-in-one-paragraph):
  PATCH for fixes, MINOR for new features (the norm pre-1.0), MAJOR for 1.0 / breaking.

## The steps

Replace `X.Y.Z` with the new version throughout.

1. **Scrub for secrets / private paths** (the pre-publish gate):
   ```bash
   npm run setup:scrub-check
   ```
   Fix anything it flags before continuing.

2. **Update the changelog.** In `CHANGELOG.md`, add a new `## [X.Y.Z] - YYYY-MM-DD` section
   at the top describing what changed (Added / Changed / Fixed). Keep the
   [Keep a Changelog](https://keepachangelog.com/) style.

3. **Bump the version** in `package.json` (no tag yet):
   ```bash
   npm version X.Y.Z --no-git-tag-version
   ```

4. **Commit** the bump + changelog:
   ```bash
   git add package.json CHANGELOG.md
   git commit -m "chore: release X.Y.Z"
   ```

5. **Tag and push** (the tag is a permanent bookmark for this version):
   ```bash
   git tag -a vX.Y.Z -m "vX.Y.Z"
   git push origin main --follow-tags
   ```

6. **Publish to npm** (needs your passkey — this is the one step only you can do):
   ```bash
   npm publish --auth-type=web
   ```
   A browser opens; approve with your passkey. Confirm it landed:
   ```bash
   npm view create-wren version      # should print X.Y.Z
   ```

7. **Create the GitHub Release** from the changelog notes:
   ```bash
   gh release create vX.Y.Z --title "vX.Y.Z" --notes "$(sed -n '/## \[X.Y.Z\]/,/## \[/p' CHANGELOG.md | sed '$d')"
   ```
   (Or just `gh release create vX.Y.Z --generate-notes` and paste the changelog in the web
   editor.) If the optional release workflow is enabled, pushing the tag in step 5 drafts
   this for you — just review and publish it.

8. **Verify + close out.** Confirm the docs site rebuilt (Actions → "Deploy docs"), then
   close the release's [milestone](https://github.com/rchoularton/wren/milestones) and any
   issues it resolved.

## Optional: fully automated npm publish

`npm publish` needs a passkey, which can't be scripted — **unless** you create an npm
**automation token** (they bypass 2FA) and add it to the repo:

1. On npmjs.com → Access Tokens → Generate → **Automation** token.
2. GitHub repo → Settings → Secrets and variables → Actions → New secret named `NPM_TOKEN`.

With that secret present, `.github/workflows/release.yml` publishes automatically when you
push a `vX.Y.Z` tag, and steps 6–7 above happen on their own. Without it, the workflow still
drafts the GitHub Release and you publish by hand — the default, and perfectly fine.

## If a release is broken

Don't edit a published version — it's permanent. Fix forward: make the change, then cut the
next PATCH (e.g. `X.Y.Z+1`) with this same checklist.
