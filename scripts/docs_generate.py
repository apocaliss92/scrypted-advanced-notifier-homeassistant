#!/usr/bin/env python3
"""Generate the DO-NOT-EDIT reference pages of the docs site.

    python3 scripts/docs_generate.py            # write the pages
    python3 scripts/docs_generate.py --check    # fail if what is on disk differs

The rule this enforces: anything derivable from the repository is generated, so a
change in the code is a change in the docs or a red build — never a page that
quietly rots. Prose lives in the hand-written pages; its citations are validated
separately by scripts/docs_check_refs.py.
"""
from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from docs_source import (  # noqa: E402  (needs the sys.path line above)
    EntityFacts,
    FlowFacts,
    FlowStep,
    IntegrationFacts,
    ProtocolFacts,
    REPO_ROOT,
    load_entity_facts,
    load_flow_facts,
    load_integration_facts,
    load_protocol_facts,
)

OUTPUT_DIR = REPO_ROOT / "docs" / "content" / "docs" / "reference"

def banner(sources: str) -> str:
    """MDX comment marking a page as machine-written.

    Built with concatenation rather than ``str.format`` because MDX comments are
    JSX expressions — the braces are content, not placeholders.
    """
    return (
        "{/* GENERATED FILE — DO NOT EDIT BY HAND.\n"
        f"    Source: {sources}\n"
        "    Regenerate: npm run docs:generate\n"
        "    Guard: npm run docs:check (scripts/docs_generate.py --check) */}"
    )


def _frontmatter(title: str, description: str, icon: str) -> str:
    return (
        "---\n"
        f"title: {title}\n"
        f"description: {description}\n"
        f"icon: {icon}\n"
        "---\n"
    )


def _table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_None._\n"
    out = ["| " + " | ".join(headers) + " |"]
    out.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out) + "\n"


def _code(value: object) -> str:
    return f"`{value}`"


def _cells(value: object) -> str:
    """Render a value for a Markdown table cell, escaping the column separator."""
    if isinstance(value, list):
        return ", ".join(_code(item) for item in value) if value else "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if value is None or value == "":
        return "—"
    return _code(str(value).replace("|", "\\|"))


# ── page: integration ────────────────────────────────────────────────────────

MANIFEST_NOTES = {
    "domain": "Home Assistant domain; the `custom_components/` directory name.",
    "name": "Display name in the integrations list.",
    "version": "Kept in sync with `VERSION` and `package.json` by `scripts/sync-version.js`.",
    "config_flow": "Whether the integration is set up from the UI.",
    "integration_type": "How Home Assistant classifies the entry.",
    "iot_class": "How data reaches Home Assistant.",
    "dependencies": "Home Assistant components that must be loaded first.",
    "codeowners": "GitHub handles responsible for the integration.",
    "documentation": "Link Home Assistant shows on the integration page.",
    "issue_tracker": "Where Home Assistant points users to report problems.",
    "loggers": "Logger names for the Home Assistant debug-logging toggle.",
}


def render_integration(facts: IntegrationFacts) -> str:
    manifest_rows = [
        [_code(key), _cells(value), MANIFEST_NOTES.get(key, "")]
        for key, value in facts.manifest.items()
    ]
    hacs_rows = [[_code(key), _cells(value)] for key, value in facts.hacs.items()]
    agree = (
        "All three agree."
        if facts.versions_agree
        else "**They disagree — run `npm run version:sync`.**"
    )
    return "\n".join(
        [
            _frontmatter(
                "Integration",
                "Manifest, HACS metadata and version of the Scrypted Advanced Notifier "
                "Home Assistant integration.",
                "Package",
            ),
            banner(
                "custom_components/scrypted_an/manifest.json, hacs.json, VERSION, package.json"
            ),
            "",
            "## Version",
            "",
            _table(
                ["Where", "Value"],
                [
                    [_code("VERSION"), _code(facts.version_file)],
                    [
                        _code("custom_components/scrypted_an/manifest.json"),
                        _cells(facts.manifest.get("version")),
                    ],
                    [_code("package.json"), _code(facts.package_version)],
                ],
            ),
            "",
            agree,
            "",
            "## Manifest",
            "",
            "From `custom_components/scrypted_an/manifest.json`.",
            "",
            _table(["Key", "Value", "Meaning"], manifest_rows),
            "",
            "## HACS",
            "",
            "From `hacs.json`. `homeassistant` is the minimum Home Assistant version "
            "HACS will install this integration on.",
            "",
            _table(["Key", "Value"], hacs_rows),
            "",
        ]
    )


# ── page: configuration ──────────────────────────────────────────────────────


def _step_section(step: FlowStep, strings: dict, section: str) -> list[str]:
    step_strings = strings.get(section, {}).get("step", {}).get(step.step_id, {})
    labels = step_strings.get("data", {})
    helps = step_strings.get("data_description", {})
    lines = [
        f"### `{step.step_id}`",
        "",
        f"Handler `{step.handler}`."
        + (f" {step_strings['description']}" if step_strings.get("description") else ""),
        "",
    ]
    if step.menu_options:
        lines += [
            _table(
                ["Menu option", "Label"],
                [
                    [
                        _code(option),
                        step_strings.get("menu_options", {}).get(option, "—"),
                    ]
                    for option in step.menu_options
                ],
            ),
            "",
        ]
    if step.fields:
        lines += [
            _table(
                ["Field", "Label", "Required", "Default", "Control", "Help"],
                [
                    [
                        _code(item.key),
                        labels.get(item.key, "—"),
                        "yes" if item.required else "no",
                        _cells(item.default),
                        _cells(item.control),
                        helps.get(item.key, "—"),
                    ]
                    for item in step.fields
                ],
            ),
            "",
        ]
    if not step.fields and not step.menu_options:
        lines += ["_No input fields._", ""]
    return lines


def _error_table(strings: dict, section: str) -> str:
    errors = strings.get(section, {}).get("error", {})
    return _table(
        ["Key", "Message"],
        [[_code(key), value] for key, value in errors.items()],
    )


def render_configuration(facts: FlowFacts) -> str:
    lines = [
        _frontmatter(
            "Configuration",
            "Every field, default and error message of the Home Assistant config "
            "flow and options flow.",
            "SlidersHorizontal",
        ),
        banner(
            "custom_components/scrypted_an/config_flow.py, custom_components/scrypted_an/strings.json"
        ),
        "",
        "Fields and defaults come from the voluptuous schemas in `config_flow.py`; "
        "labels, help text and error messages come from `strings.json`. A default "
        "shown as an expression is the expression the code evaluates at that point.",
        "",
        "## Config flow",
        "",
        "Run once, when the integration is added.",
        "",
    ]
    for step in facts.config_steps:
        lines += _step_section(step, facts.strings, "config")
    lines += ["### Errors", "", _error_table(facts.strings, "config"), ""]

    aborts = facts.strings.get("config", {}).get("abort", {})
    if aborts:
        lines += [
            "### Aborts",
            "",
            _table(
                ["Key", "Message"], [[_code(k), v] for k, v in aborts.items()]
            ),
            "",
        ]

    lines += [
        "## Options flow",
        "",
        "Reachable from **Configure** on the integration entry after setup.",
        "",
    ]
    for step in facts.options_steps:
        lines += _step_section(step, facts.strings, "options")
    lines += ["### Errors", "", _error_table(facts.strings, "options"), ""]
    return "\n".join(lines)


# ── page: entities ───────────────────────────────────────────────────────────


def render_entities(facts: EntityFacts) -> str:
    forwarded = set(facts.declared_platforms)
    built = {platform.platform for platform in facts.platforms}
    rows = [
        [
            _code(platform.platform),
            _code(platform.entity_class),
            _code(platform.module),
            "yes" if platform.platform in forwarded else "**no**",
        ]
        for platform in facts.platforms
    ]
    orphan_rows = [
        [_code(name), "—", "—", "yes"]
        for name in facts.declared_platforms
        if name not in built
    ]

    lines = [
        _frontmatter(
            "Entity platforms",
            "Which Home Assistant platforms the integration sets up, which entity "
            "class serves each, and the component-config keys they read.",
            "LayoutGrid",
        ),
        banner(
            "custom_components/scrypted_an/__init__.py, custom_components/scrypted_an/base_entity.py"
        ),
        "",
        "Two independent facts have to line up: `PLATFORMS` in `__init__.py` decides "
        "what Home Assistant forwards the config entry to, and the `build_entity()` "
        "factory decides which class a component payload becomes. A platform in one "
        "but not the other is a bug, so both columns are shown.",
        "",
        "## Platforms",
        "",
        _table(
            ["Platform", "Entity class", "Module", "In `PLATFORMS`"],
            rows + orphan_rows,
        ),
        "",
        f"`PLATFORMS` declares {len(facts.declared_platforms)}; the factory builds "
        f"{len(facts.platforms)}.",
        "",
        "## Component-config keys",
        "",
        "The plugin sends each entity an MQTT-autodiscovery-shaped `cmps` payload. "
        "These are the keys the integration actually reads out of it.",
        "",
        "### Read by every entity",
        "",
        _table(
            ["Key"], [[_code(key)] for key in facts.base_config_keys]
        ),
        "",
        "### Read per platform",
        "",
        _table(
            ["Platform", "Additional keys"],
            [
                [
                    _code(platform.platform),
                    _cells(
                        [
                            key
                            for key in platform.config_keys
                            if key not in facts.base_config_keys
                        ]
                    ),
                ]
                for platform in facts.platforms
            ],
        ),
        "",
        "## Entity categories",
        "",
        "Values accepted in the payload's `entity_category` key, from "
        "`_ENTITY_CATEGORY_MAP` in `base_entity.py`. Anything else leaves the entity "
        "uncategorised.",
        "",
        _table(["Value"], [[_code(value)] for value in facts.entity_categories]),
        "",
    ]
    return "\n".join(lines)


# ── page: protocol ───────────────────────────────────────────────────────────

CONST_NOTES = {
    "DOMAIN": "Home Assistant domain.",
    "HEARTBEAT_TIMEOUT_S": "Seconds without a heartbeat before every entity is marked unavailable.",
    "PUSH_API_PATH": "Path the plugin POSTs to on Home Assistant.",
    "ENDPOINT_BASE": "Prefix of every plugin endpoint.",
}


def render_protocol(facts: ProtocolFacts) -> str:
    consts = facts.const_values
    endpoints = [
        [_code(name), _cells(value)]
        for name, value in consts.items()
        if name.startswith("ENDPOINT_") and name != "ENDPOINT_BASE"
    ]
    events = [
        [_code(name), _cells(value)]
        for name, value in consts.items()
        if name.startswith("HA_EVENT_")
    ]
    conf = [
        [_code(name), _cells(value)]
        for name, value in consts.items()
        if name.startswith("CONF_")
    ]
    other = [
        [_code(name), _cells(value), CONST_NOTES.get(name, "")]
        for name, value in consts.items()
        if not name.startswith(("ENDPOINT_", "HA_EVENT_", "CONF_"))
    ]

    return "\n".join(
        [
            _frontmatter(
                "Protocol",
                "Bus events, HTTP endpoints, push message types and timings exchanged "
                "between Home Assistant and the Scrypted plugin.",
                "Radio",
            ),
            banner(
                "custom_components/scrypted_an/const.py, "
                "custom_components/scrypted_an/push_view.py, "
                "custom_components/scrypted_an/action_listener.py"
            ),
            "",
            "## Home Assistant bus events",
            "",
            "Fired inside Home Assistant, either by the push view or by the plugin.",
            "",
            _table(["Constant", "Event name"], events),
            "",
            "## Push endpoint (served by Home Assistant)",
            "",
            f"{_code(facts.push_view_class)} in `push_view.py`. Authentication is a "
            "bearer token compared against the configured HA Secret, not Home "
            "Assistant's own auth.",
            "",
            _table(
                ["Attribute", "Value"],
                [[_code(key), _cells(value)] for key, value in facts.push_view.items()],
            ),
            "",
            "Accepted `type` values in the POST body:",
            "",
            _table(
                ["Message type"], [[_code(value)] for value in facts.push_message_types]
            ),
            "",
            "## Plugin endpoints (called by Home Assistant)",
            "",
            f"All relative to the configured Scrypted URL, under "
            f"{_code(consts.get('ENDPOINT_BASE', ''))}.",
            "",
            _table(["Constant", "Path"], endpoints),
            "",
            "## Notification actions",
            "",
            "The action listener watches the Home Assistant Companion event below and "
            "forwards matching actions to the plugin.",
            "",
            _table(
                ["Constant", "Value"],
                [[_code(key), _cells(value)] for key, value in facts.action_listener.items()],
            ),
            "",
            "## Configuration keys",
            "",
            "Keys stored in the config entry.",
            "",
            _table(["Constant", "Key"], conf),
            "",
            "## Other constants",
            "",
            _table(["Constant", "Value", "Meaning"], other),
            "",
        ]
    )


# ── driver ───────────────────────────────────────────────────────────────────


def build_pages() -> dict[Path, str]:
    return {
        OUTPUT_DIR / "integration.mdx": render_integration(load_integration_facts()),
        OUTPUT_DIR / "configuration.mdx": render_configuration(load_flow_facts()),
        OUTPUT_DIR / "entities.mdx": render_entities(load_entity_facts()),
        OUTPUT_DIR / "protocol.mdx": render_protocol(load_protocol_facts()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit non-zero when a generated page is out of date",
    )
    args = parser.parse_args()

    pages = build_pages()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not args.check:
        for path, content in pages.items():
            path.write_text(content, encoding="utf-8")
            print(f"wrote {path.relative_to(REPO_ROOT)}")
        return 0

    stale: list[str] = []
    for path, content in pages.items():
        rel = path.relative_to(REPO_ROOT)
        on_disk = path.read_text(encoding="utf-8") if path.exists() else ""
        if on_disk == content:
            continue
        stale.append(str(rel))
        print(f"DRIFT {rel}")
        diff = difflib.unified_diff(
            on_disk.splitlines(),
            content.splitlines(),
            fromfile=f"{rel} (committed)",
            tofile=f"{rel} (regenerated)",
            lineterm="",
            n=1,
        )
        for line in list(diff)[:60]:
            print(f"  {line}")

    if stale:
        print(
            f"\n{len(stale)} generated page(s) out of date. "
            "Run `npm run docs:generate` and commit the result.",
            file=sys.stderr,
        )
        return 1
    print(f"docs:generate --check OK — {len(pages)} generated pages match the source")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
