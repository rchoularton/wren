## Summary

<!-- What does this PR change, and why? -->

## Checklist

- [ ] Ran `npm run setup:verify` against a scaffolded project and it passed
- [ ] Scaffolded clean into a temp path, including **one path containing a space**
      (e.g. `node bin/create-research-assistant.mjs --yes "/tmp/a b/proj"`),
      and `npm run setup:verify` passed in it
- [ ] If this touches `bin/create-research-assistant.mjs`, `setup.sh`, or
      `scripts/setup/*.py`: ran `node --check` / `python3 -m py_compile` on the
      changed files
- [ ] Updated docs (`README.md`, `docs/`, `QUICKSTART.md`) if user-facing behavior changed
- [ ] Added a `CHANGELOG.md` entry under `[Unreleased]` (or the next version) if this is a
      user-visible change

## Related issues

<!-- Closes #... -->
