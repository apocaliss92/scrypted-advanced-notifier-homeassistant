#!/bin/sh
# Decides the docs site's access control, then hands off to Caddy.
#
# The container REFUSES TO START without an explicit decision. This project's docs
# are meant to be public, but "I forgot to set the variables" must never be the
# reason a site is open — the choice is explicit in both directions.
#
#   Public, deliberately (what this project normally wants):
#     DOCS_PUBLIC=true
#
#   Protected:
#     DOCS_USER=someone
#     DOCS_PASSWORD_HASH='<output of: caddy hash-password --plaintext "…">'
#
# Anything else exits 1 with the instructions.
set -eu

ACCESS_CONF=/etc/caddy/access.conf

if [ "${DOCS_PUBLIC:-}" = "true" ]; then
  echo "docs: PUBLIC (DOCS_PUBLIC=true)" >&2
  printf '# public: DOCS_PUBLIC=true\n' >"$ACCESS_CONF"

elif [ -n "${DOCS_USER:-}" ] && [ -n "${DOCS_PASSWORD_HASH:-}" ]; then
  echo "docs: password-protected (user: ${DOCS_USER})" >&2
  # The health endpoint stays open so the platform can probe without credentials.
  cat >"$ACCESS_CONF" <<EOF
@needs_auth not path /_health
basic_auth @needs_auth {
	${DOCS_USER} ${DOCS_PASSWORD_HASH}
}
EOF

else
  cat >&2 <<'EOF'
docs: refusing to start.

The site will not serve without an explicit access decision. Set EITHER:

  DOCS_PUBLIC=true              # publish openly, on purpose

or, to put it behind a password:

  DOCS_USER=<username>
  DOCS_PASSWORD_HASH=<hash>     # docker run --rm caddy:2.8-alpine \
                                #   caddy hash-password --plaintext 'your-password'
EOF
  exit 1
fi

exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
