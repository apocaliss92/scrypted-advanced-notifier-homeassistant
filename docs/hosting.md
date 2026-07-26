# Hosting these docs

`docs/` renders to a static site — MkDocs Material, client-side search, works on a
phone. `Dockerfile.docs` builds it and serves it with Caddy.

It is a **view** over the repository. There is no editing surface and there must
never be one: `README.md` and `CLAUDE.md` stay the files people edit.

## Locally

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install mkdocs-material==9.5.49

npm run docs:site          # mkdocs serve → http://127.0.0.1:8000
npm run docs:site:build    # mkdocs build --strict → site/
```

`--strict` fails on a broken internal link, so a deploy that would publish a
broken site does not deploy.

## As a container

```bash
docker build -f Dockerfile.docs -t scrypted-an-docs .

# Public, on purpose:
docker run -p 8080:8080 -e DOCS_PUBLIC=true scrypted-an-docs

# Or password-protected:
HASH=$(docker run --rm caddy:2.8-alpine caddy hash-password --plaintext 'secret')
docker run -p 8080:8080 -e DOCS_USER=me -e DOCS_PASSWORD_HASH="$HASH" scrypted-an-docs
```

**With neither set, the container exits 1.** These docs are meant to be public,
but a forgotten variable must never be the reason a site is open — the choice is
explicit in both directions.

## On Railway

A **service of its own**, built from this repository.

1. New service → this repo.
2. Service variables:

   | Variable | Value |
   | --- | --- |
   | `RAILWAY_DOCKERFILE_PATH` | `Dockerfile.docs` |
   | `DOCS_PUBLIC` | `true` (or `DOCS_USER` + `DOCS_PASSWORD_HASH` instead) |

   Instead of `RAILWAY_DOCKERFILE_PATH` you can point the service's *Config as
   code* path at `railway.docs.json`, which also sets the health check and restart
   policy. It is **not** named `railway.json` on purpose — that path would apply
   to every service built from this repo.
3. Custom domain on the service, e.g. `docs.<your-domain>`. Railway terminates TLS
   at its edge, which is why Caddy runs with `auto_https off`.

`PORT` is injected by Railway; the health check is `/_health`, deliberately left
unauthenticated so the platform can probe without credentials.

### Deploying on push

Pick **one** mechanism. Two things deploying one service is how you end up
debugging which of them shipped.

**Railway's own GitHub integration** — no workflow, no token. Connect the service
to the repo and set its *watch paths* so a code commit does not redeploy the docs:

```
docs/**, mkdocs.yml, Dockerfile.docs, Dockerfile.docs.dockerignore, docker/docs.*
```

**Or `.github/workflows/docs-deploy.yml`** — same path filter, plus it runs
`mkdocs build --strict` so a broken link fails against the commit that caused it.
Set on GitHub (Settings → Secrets and variables → Actions):

| | Name | Value |
| --- | --- | --- |
| Secret | `RAILWAY_TOKEN` | a Railway project or account token |
| Variable | `RAILWAY_DOCS_SERVICE` | the service name, e.g. `docs` |
| Variable | `RAILWAY_DOCS_ENVIRONMENT` | optional, defaults to `production` |

The workflow's `build` job runs regardless and uploads the site as an artifact, so
it is useful before any host exists. The `deploy` job skips with a notice when the
token is absent on a push, and fails on a manual dispatch — "not set up yet" and
"set up wrongly" should not look the same.

## What the container does

| Behaviour | Why |
| --- | --- |
| `/_health` → `200 ok`, no auth | platform probes must not need credentials |
| `/assets/*` → `immutable`, one year | filenames are content-fingerprinted |
| everything else → `must-revalidate` | `use_directory_urls` makes page URLs stable, so HTML must not be cached |
| 404 → MkDocs' own `404.html` | Caddy's bare 404 is not worth showing |
| gzip | text-heavy site |

The two `Cache-Control` matchers have to be mutually exclusive: a blanket
`header Cache-Control` next to a matched one does **not** act as a fallback — it
runs too and overwrites, so assets would silently get the must-revalidate value.
