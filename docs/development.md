# Development

Migrated from `CLAUDE.md`. Change it there first; this page mirrors it.

## Version management

```bash
npm run version:patch   # bump patch + sync to manifest.json
npm run version:minor
npm run version:major
npm run version:sync    # sync VERSION → manifest.json without bumping
```

`VERSION` is the source of truth. `scripts/sync-version.js` writes it into
`custom_components/scrypted_an/manifest.json` and `package.json`. Always keep
these three in sync.

## CI pipeline (`.github/workflows/release.yml`)

Triggers on every push to `main`:

1. **Hassfest** — validates manifest format and structure
2. **HACS validation** — validates HACS compatibility
3. **Release** — bumps patch version, commits, tags `vX.Y.Z`, creates GitHub Release

## Docs pipeline (`.github/workflows/docs-deploy.yml`)

A separate workflow, path-filtered to `docs/**`, `mkdocs.yml` and the container
files. It builds the site with `mkdocs build --strict` and, once the Railway
variables exist, deploys it. It never touches `VERSION`, tags or releases — see
[hosting.md](hosting.md).

## Language

All code comments, docstrings, commit messages, and PR descriptions must be in
**English**.
