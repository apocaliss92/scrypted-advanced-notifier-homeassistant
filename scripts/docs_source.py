"""Extract documentable facts from the integration source.

Everything here reads the real tree: JSON with ``json``, Python with the standard
library ``ast`` module. Nothing regexes prose and nothing hardcodes a value that
is not in the repository, so a fact that changes in the code changes here too.

Consumed by ``scripts/docs_generate.py`` (which renders MDX) and
``scripts/docs_check_refs.py`` (which validates what prose pages cite).
"""
from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = REPO_ROOT / "custom_components" / "scrypted_an"


# ── generic helpers ──────────────────────────────────────────────────────────


def read_json(path: Path) -> dict:
    """Parse a JSON file relative to the repository root."""
    return json.loads(path.read_text(encoding="utf-8"))


def parse_module(path: Path) -> ast.Module:
    """Parse a Python file into an AST."""
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def module_constants(tree: ast.Module) -> dict[str, object]:
    """Module-level assignments whose value is a literal or a resolvable f-string.

    f-strings are resolved against constants already seen in the same module, which
    is how ``ENDPOINT_HA_DEVICES = f"{ENDPOINT_BASE}/public/ha/devices"`` becomes a
    full path rather than a template.
    """
    resolved: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        if value is None:
            continue
        for target in targets:
            if not isinstance(target, ast.Name):
                continue
            literal = _literal(value, resolved)
            if literal is not _UNRESOLVED:
                resolved[target.id] = literal
    return resolved


_UNRESOLVED = object()


def _literal(node: ast.AST, known: dict[str, object]) -> object:
    """Best-effort literal evaluation with substitution of known constants."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return known.get(node.id, _UNRESOLVED)
    if isinstance(node, (ast.List, ast.Tuple)):
        items = [_literal(item, known) for item in node.elts]
        return _UNRESOLVED if _UNRESOLVED in items else items
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for piece in node.values:
            if isinstance(piece, ast.Constant):
                parts.append(str(piece.value))
            elif isinstance(piece, ast.FormattedValue):
                inner = _literal(piece.value, known)
                if inner is _UNRESOLVED:
                    return _UNRESOLVED
                parts.append(str(inner))
            else:
                return _UNRESOLVED
        return "".join(parts)
    return _UNRESOLVED


def string_literals(tree: ast.AST) -> set[str]:
    """Every string constant anywhere in a module."""
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def defined_classes(tree: ast.Module) -> set[str]:
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}


def _kwarg(call: ast.Call, name: str) -> ast.AST | None:
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _const_str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _equality_literals(tree: ast.AST, variables: set[str]) -> list[str]:
    """String literals compared with ``==`` against any of ``variables``.

    Used to recover the dispatch tables written as ``if platform == "switch":``
    without hardcoding the table itself.
    """
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare) or not node.ops:
            continue
        if not isinstance(node.ops[0], ast.Eq):
            continue
        if not (isinstance(node.left, ast.Name) and node.left.id in variables):
            continue
        literal = _const_str(node.comparators[0])
        if literal is not None and literal not in found:
            found.append(literal)
    return found


# ── integration metadata ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class IntegrationFacts:
    version_file: str
    manifest: dict
    hacs: dict
    package_version: str

    @property
    def versions_agree(self) -> bool:
        return (
            self.version_file == self.manifest.get("version") == self.package_version
        )


def load_integration_facts() -> IntegrationFacts:
    return IntegrationFacts(
        version_file=(REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        manifest=read_json(PACKAGE_DIR / "manifest.json"),
        hacs=read_json(REPO_ROOT / "hacs.json"),
        package_version=str(read_json(REPO_ROOT / "package.json").get("version", "")),
    )


# ── config flow ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FlowField:
    key: str
    required: bool
    default: str | None
    control: str


@dataclass(frozen=True)
class FlowStep:
    step_id: str
    handler: str
    fields: tuple[FlowField, ...] = ()
    menu_options: tuple[str, ...] = ()


@dataclass(frozen=True)
class FlowFacts:
    config_steps: tuple[FlowStep, ...]
    options_steps: tuple[FlowStep, ...]
    strings: dict


def _describe_control(node: ast.AST | None) -> str:
    """Human name for the widget a voluptuous schema value asks for."""
    if isinstance(node, ast.Name):
        return {"str": "text", "int": "number", "bool": "toggle"}.get(node.id, node.id)
    if isinstance(node, ast.Call):
        name = node.func.id if isinstance(node.func, ast.Name) else ast.unparse(node.func)
        if name == "SelectSelector":
            multiple = False
            mode = ""
            for inner in ast.walk(node):
                if isinstance(inner, ast.keyword) and inner.arg == "multiple":
                    multiple = bool(getattr(inner.value, "value", False))
                if isinstance(inner, ast.keyword) and inner.arg == "mode":
                    mode = ast.unparse(inner.value).split(".")[-1].lower()
            return f"select ({'multiple' if multiple else 'single'}{', ' + mode if mode else ''})"
        return name
    return ast.unparse(node) if node is not None else "unknown"


def _fields_from_schema_dict(
    node: ast.Dict, constants: dict[str, object]
) -> tuple[FlowField, ...]:
    fields: list[FlowField] = []
    for key_node, value_node in zip(node.keys, node.values):
        if not isinstance(key_node, ast.Call):
            continue
        marker = (
            key_node.func.attr
            if isinstance(key_node.func, ast.Attribute)
            else ast.unparse(key_node.func)
        )
        if not key_node.args:
            continue
        raw_key = key_node.args[0]
        key = (
            str(constants.get(raw_key.id, raw_key.id))
            if isinstance(raw_key, ast.Name)
            else str(_const_str(raw_key) or ast.unparse(raw_key))
        )
        default_node = _kwarg(key_node, "default")
        fields.append(
            FlowField(
                key=key,
                required=marker == "Required",
                default=ast.unparse(default_node) if default_node is not None else None,
                control=_describe_control(value_node),
            )
        )
    return tuple(fields)


def _schema_dict_for(
    node: ast.AST, helpers: dict[str, ast.FunctionDef]
) -> ast.Dict | None:
    """Resolve a ``data_schema=`` expression down to its literal dict.

    Handles both an inline ``vol.Schema({...})`` and a call to a module-level
    helper such as ``_build_select_schema(...)`` that returns one.
    """
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr == "Schema":
        if node.args and isinstance(node.args[0], ast.Dict):
            return node.args[0]
        return None
    if isinstance(func, ast.Name) and func.id in helpers:
        for inner in ast.walk(helpers[func.id]):
            if isinstance(inner, ast.Return) and inner.value is not None:
                return _schema_dict_for(inner.value, helpers)
    return None


def _steps_of(
    cls: ast.ClassDef, helpers: dict[str, ast.FunctionDef], constants: dict[str, object]
) -> tuple[FlowStep, ...]:
    steps: list[FlowStep] = []
    for member in cls.body:
        if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not member.name.startswith("async_step_"):
            continue
        for call in ast.walk(member):
            if not isinstance(call, ast.Call):
                continue
            func = call.func
            if not isinstance(func, ast.Attribute):
                continue
            if func.attr == "async_show_form":
                step_id = _const_str(_kwarg(call, "step_id")) or member.name[len("async_step_"):]
                schema = _schema_dict_for(_kwarg(call, "data_schema"), helpers)
                steps.append(
                    FlowStep(
                        step_id=step_id,
                        handler=member.name,
                        fields=_fields_from_schema_dict(schema, constants) if schema else (),
                    )
                )
            elif func.attr == "async_show_menu":
                step_id = _const_str(_kwarg(call, "step_id")) or member.name[len("async_step_"):]
                options_node = _kwarg(call, "menu_options")
                options = (
                    tuple(
                        str(_const_str(item))
                        for item in options_node.elts
                        if _const_str(item) is not None
                    )
                    if isinstance(options_node, (ast.List, ast.Tuple))
                    else ()
                )
                steps.append(
                    FlowStep(step_id=step_id, handler=member.name, menu_options=options)
                )
    return tuple(steps)


def load_flow_facts() -> FlowFacts:
    tree = parse_module(PACKAGE_DIR / "config_flow.py")
    constants = module_constants(parse_module(PACKAGE_DIR / "const.py"))
    helpers = {
        node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    config_steps: tuple[FlowStep, ...] = ()
    options_steps: tuple[FlowStep, ...] = ()
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        bases = {ast.unparse(base) for base in node.bases}
        if any(base.endswith("ConfigFlow") for base in bases):
            config_steps = _steps_of(node, helpers, constants)
        elif any(base.endswith("OptionsFlow") for base in bases):
            options_steps = _steps_of(node, helpers, constants)
    return FlowFacts(
        config_steps=config_steps,
        options_steps=options_steps,
        strings=read_json(PACKAGE_DIR / "strings.json"),
    )


# ── entities ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PlatformFacts:
    platform: str
    entity_class: str
    module: str
    config_keys: tuple[str, ...]


@dataclass(frozen=True)
class EntityFacts:
    declared_platforms: tuple[str, ...]
    platforms: tuple[PlatformFacts, ...]
    base_config_keys: tuple[str, ...]
    entity_categories: tuple[str, ...]


def _config_keys(tree: ast.AST) -> tuple[str, ...]:
    """Keys the module reads out of a component config dict.

    Recovered from ``<something ending in cmp_config>.get("key")`` calls, which is
    how every entity module reads its MQTT-autodiscovery-shaped payload.
    """
    keys: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "get" or not node.args:
            continue
        receiver = ast.unparse(node.func.value)
        if not receiver.endswith("cmp_config"):
            continue
        key = _const_str(node.args[0])
        if key is not None and key not in keys:
            keys.append(key)
    return tuple(sorted(keys))


def load_entity_facts() -> EntityFacts:
    init_tree = parse_module(PACKAGE_DIR / "__init__.py")
    constants = module_constants(init_tree)
    declared = tuple(str(item) for item in constants.get("PLATFORMS", []))

    factory = next(
        (
            node
            for node in init_tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "build_entity"
        ),
        None,
    )
    platforms: list[PlatformFacts] = []
    if factory is not None:
        for branch in factory.body:
            if not isinstance(branch, ast.If):
                continue
            names = _equality_literals(branch.test, {"platform"})
            if not names:
                continue
            module_name = ""
            class_name = ""
            for inner in ast.walk(branch):
                if isinstance(inner, ast.ImportFrom) and inner.names:
                    module_name = inner.module or ""
                    class_name = inner.names[0].name
            module_path = PACKAGE_DIR / f"{module_name}.py"
            platforms.append(
                PlatformFacts(
                    platform=names[0],
                    entity_class=class_name,
                    module=f"custom_components/scrypted_an/{module_name}.py",
                    config_keys=_config_keys(parse_module(module_path))
                    if module_path.exists()
                    else (),
                )
            )

    base_tree = parse_module(PACKAGE_DIR / "base_entity.py")
    category_map = next(
        (
            node.value
            for node in base_tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(t, ast.Name) and t.id == "_ENTITY_CATEGORY_MAP"
                for t in node.targets
            )
        ),
        None,
    )
    categories = (
        tuple(
            str(_const_str(key))
            for key in category_map.keys
            if _const_str(key) is not None
        )
        if isinstance(category_map, ast.Dict)
        else ()
    )

    return EntityFacts(
        declared_platforms=declared,
        platforms=tuple(platforms),
        base_config_keys=_config_keys(base_tree),
        entity_categories=categories,
    )


# ── protocol ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ProtocolFacts:
    const_values: dict[str, object]
    push_view_class: str
    push_view: dict[str, object]
    push_message_types: tuple[str, ...]
    bus_event_types: tuple[str, ...]
    action_listener: dict[str, object]


def load_protocol_facts() -> ProtocolFacts:
    const_values = module_constants(parse_module(PACKAGE_DIR / "const.py"))

    push_tree = parse_module(PACKAGE_DIR / "push_view.py")
    # Located by its base class, not by name, so renaming it renames it here too.
    push_class = next(
        (
            node
            for node in push_tree.body
            if isinstance(node, ast.ClassDef)
            and any(ast.unparse(base).endswith("HomeAssistantView") for base in node.bases)
        ),
        None,
    )
    push_attrs: dict[str, object] = {}
    if push_class is not None:
        attrs = module_constants(ast.Module(body=push_class.body, type_ignores=[]))
        for name, value in attrs.items():
            push_attrs[name] = value
        if "url" not in push_attrs and "PUSH_API_PATH" in const_values:
            push_attrs["url"] = const_values["PUSH_API_PATH"]
        for member in push_class.body:
            if isinstance(member, ast.Assign) and isinstance(member.value, ast.Constant):
                for target in member.targets:
                    if isinstance(target, ast.Name):
                        push_attrs[target.id] = member.value.value

    action_tree = parse_module(PACKAGE_DIR / "action_listener.py")
    action_consts = module_constants(action_tree)

    return ProtocolFacts(
        const_values=const_values,
        push_view_class=push_class.name if push_class is not None else "",
        push_view=push_attrs,
        push_message_types=tuple(_equality_literals(push_tree, {"msg_type", "t"})),
        bus_event_types=tuple(
            str(value)
            for name, value in const_values.items()
            if name.startswith("HA_EVENT_")
        ),
        action_listener={
            key: action_consts[key]
            for key in ("EVENT_TYPE", "ACTION_PREFIX", "SNOOZE_PREFIX")
            if key in action_consts
        },
    )


# ── whole-package symbol index (used by the reference checker) ───────────────


@dataclass(frozen=True)
class SymbolIndex:
    constants: frozenset[str]
    classes: frozenset[str]
    strings: frozenset[str]


def load_symbol_index() -> SymbolIndex:
    constants: set[str] = set()
    classes: set[str] = set()
    strings: set[str] = set()
    for path in sorted(PACKAGE_DIR.rglob("*.py")):
        tree = parse_module(path)
        constants.update(module_constants(tree))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.add(node.name)
                constants.update(
                    module_constants(ast.Module(body=node.body, type_ignores=[]))
                )
        strings.update(string_literals(tree))
    return SymbolIndex(
        constants=frozenset(constants),
        classes=frozenset(classes),
        strings=frozenset(strings),
    )
