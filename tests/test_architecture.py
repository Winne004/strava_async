"""Structural rules, enforced by parsing the source rather than trusting review.

Two families of rule live here:

* import boundaries — dependencies point downward only;
* the declarative service style — Pydantic in, Pydantic out, one delegating call.

If a change requires relaxing something here, the design is wrong. Raise it rather than
weakening the test.
"""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src" / "strava_async"
PACKAGE = "strava_async"

# Which internal modules each layer may import. A module may always import from its own
# entry; "*" means no restriction.
ALLOWED_IMPORTS: dict[str, set[str] | str] = {
    "settings": set(),
    "protocols": set(),
    "exceptions": set(),
    "auth": {"exceptions"},
    "schemas": {"schemas"},
    "services.base": {"protocols", "exceptions"},
    "services": {"services.base", "schemas", "protocols"},
    "registry": {"services", "settings"},
    "client": {"services", "registry", "protocols"},
    "initialise": "*",
}

SERVICE_MODULES = [
    "activities",
    "athletes",
    "clubs",
    "gear",
    "routes",
    "segment_efforts",
    "segments",
    "streams",
    "uploads",
]

# Annotations that would let untyped data back into a service signature.
FORBIDDEN_ANNOTATIONS = ("dict", "Any", "list[dict", "object")


def source_files() -> list[Path]:
    return sorted(path for path in SRC.rglob("*.py") if path.name != "__init__.py")


def module_name(path: Path) -> str:
    return ".".join(path.relative_to(SRC).with_suffix("").parts)


def internal_imports(tree: ast.AST) -> list[str]:
    """Every ``strava_async.*`` module this file imports, as dotted paths."""
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == PACKAGE or node.module.startswith(f"{PACKAGE}."):
                imports.append(node.module.removeprefix(f"{PACKAGE}.").removeprefix(PACKAGE))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(f"{PACKAGE}."):
                    imports.append(alias.name.removeprefix(f"{PACKAGE}."))
    return [name for name in imports if name]


def rule_for(module: str) -> set[str] | str:
    """The most specific rule that applies, so ``services.base`` beats ``services``."""
    candidates = [key for key in ALLOWED_IMPORTS if module == key or module.startswith(f"{key}.")]
    return ALLOWED_IMPORTS[max(candidates, key=len)]


def is_allowed(imported: str, allowed: set[str]) -> bool:
    return any(imported == entry or imported.startswith(f"{entry}.") for entry in allowed)


# --- Discovery guards --------------------------------------------------------------


def test_source_tree_is_where_the_rules_expect() -> None:
    """Fails loudly if the layout moves, rather than silently checking nothing."""
    assert SRC.is_dir(), f"Expected the package at {SRC}"
    assert len(source_files()) > 15


def test_every_service_module_exists() -> None:
    found = {path.stem for path in (SRC / "services").glob("*.py")} - {"__init__", "base"}

    assert found == set(SERVICE_MODULES)


def test_every_source_file_is_covered_by_a_rule() -> None:
    uncovered = [
        module_name(path)
        for path in source_files()
        if not any(
            module_name(path) == key or module_name(path).startswith(f"{key}.")
            for key in ALLOWED_IMPORTS
        )
    ]

    assert uncovered == [], f"Modules with no layering rule: {uncovered}"


# --- Import boundaries -------------------------------------------------------------


@pytest.mark.parametrize("path", source_files(), ids=module_name)
def test_module_respects_its_layer(path: Path) -> None:
    module = module_name(path)
    allowed = rule_for(module)
    if allowed == "*":
        return

    assert isinstance(allowed, set)
    own_package = module.rsplit(".", 1)[0] if "." in module else module
    violations = [
        imported
        for imported in internal_imports(ast.parse(path.read_text()))
        if not is_allowed(imported, allowed | {module, own_package})
    ]

    assert violations == [], f"{module} may not import {violations} (allowed: {sorted(allowed)})"


def test_foundation_modules_import_nothing_internal() -> None:
    for module in ("settings", "protocols", "exceptions"):
        tree = ast.parse((SRC / f"{module}.py").read_text())
        assert internal_imports(tree) == [], f"{module} must stay dependency-free"


def test_base_service_imports_no_schema_and_no_sibling() -> None:
    """The pipeline is generic: it must not know a single Strava model."""
    imports = internal_imports(ast.parse((SRC / "services" / "base.py").read_text()))

    assert not [name for name in imports if name.startswith("schemas")]
    assert not [name for name in imports if name.startswith("services.")]


def test_client_does_not_import_settings_or_concrete_auth() -> None:
    imports = internal_imports(ast.parse((SRC / "client.py").read_text()))

    assert "settings" not in imports
    assert not [name for name in imports if name.startswith("auth")]


# --- The declarative service style -------------------------------------------------


def service_methods() -> list[tuple[str, ast.AsyncFunctionDef]]:
    methods: list[tuple[str, ast.AsyncFunctionDef]] = []
    for name in SERVICE_MODULES:
        tree = ast.parse((SRC / "services" / f"{name}.py").read_text())
        for klass in (node for node in tree.body if isinstance(node, ast.ClassDef)):
            for node in klass.body:
                if isinstance(node, ast.AsyncFunctionDef) and not node.name.startswith("_"):
                    methods.append((f"{name}.{node.name}", node))
    return methods


ALL_METHODS = service_methods()


def test_every_endpoint_has_a_method() -> None:
    """34 operations in the swagger, 34 public service methods."""
    assert len(ALL_METHODS) == 34


@pytest.mark.parametrize(("name", "node"), ALL_METHODS, ids=[name for name, _ in ALL_METHODS])
def test_method_body_is_a_single_delegating_return(name: str, node: ast.AsyncFunctionDef) -> None:
    """No branching, no post-processing, no orchestration — one call to a Base helper."""
    body = [stmt for stmt in node.body if not _is_docstring(stmt)]

    assert len(body) == 1, f"{name} should be one statement, found {len(body)}"
    statement = body[0]
    assert isinstance(statement, ast.Return), f"{name} must return directly"
    assert isinstance(statement.value, ast.Await), f"{name} must await a Base helper"


@pytest.mark.parametrize(("name", "node"), ALL_METHODS, ids=[name for name, _ in ALL_METHODS])
def test_method_has_a_docstring_naming_its_scope(name: str, node: ast.AsyncFunctionDef) -> None:
    docstring = ast.get_docstring(node)

    assert docstring, f"{name} needs a docstring"
    assert "Returns:" in docstring, f"{name} needs a Returns: section"


@pytest.mark.parametrize(("name", "node"), ALL_METHODS, ids=[name for name, _ in ALL_METHODS])
def test_method_signature_is_typed_and_modelled(name: str, node: ast.AsyncFunctionDef) -> None:
    """Path params are scalars; everything else structured is a Pydantic model."""
    assert node.returns is not None, f"{name} needs a return annotation"
    rendered_return = ast.unparse(node.returns)
    assert not any(bad in rendered_return for bad in FORBIDDEN_ANNOTATIONS), (
        f"{name} returns {rendered_return}; return a model"
    )

    for argument in node.args.args[1:]:
        assert argument.annotation is not None, f"{name}: {argument.arg} needs an annotation"
        rendered = ast.unparse(argument.annotation)
        assert not any(bad in rendered for bad in FORBIDDEN_ANNOTATIONS), (
            f"{name}: {argument.arg} is annotated {rendered}; pass a model instead"
        )
        assert _is_acceptable_parameter(rendered), (
            f"{name}: {argument.arg} is annotated {rendered}; structured input must be a "
            "Params or RequestBody model"
        )


def _is_docstring(statement: ast.stmt) -> bool:
    return isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)


def _is_acceptable_parameter(rendered: str) -> bool:
    base = rendered.removesuffix(" | None").strip()
    if base in {"int", "str", "float", "bool"}:
        return True
    if base in {"BinaryIO | bytes"}:  # an upload stream is not a serialisable field
        return True
    return base.endswith(("Params", "RequestBody"))
