"""Non-executing parser-stub fixture for future Verilator GPU options."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Sequence

try:
    from .hybrid_benchmark_specs import SIDECAR_ACCEL
except ImportError:  # pragma: no cover - exercised when imported via sys.path.
    from hybrid_benchmark_specs import SIDECAR_ACCEL


PARSER_STUB_REJECTION_LAYER = "parser_stub_validation_contract"
SOURCE_BOUNDARY_STATUS = "preserved_only_not_resolved"
CORRECTNESS_POLICY = "coverage_output_equivalence"
SURFACE = "native_verilator_parser_stub_fixture"

HANDOFF_FIELDS = tuple(
    "schema_version surface accelerator_mode state_count step_count shape "
    "ordinary_verilator_args mdir top_module source_files filelists defines "
    "include_dirs warning_flags source_boundary_status state_and_report_naming_rules "
    "correctness_policy non_claims".split()
)


class NativeOptionParserStubError(ValueError):
    """Structured parser-stub validation error."""

    def __init__(self, code: str, message: str, *, unsupported_value: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.rejection_layer = PARSER_STUB_REJECTION_LAYER
        self.unsupported_value = unsupported_value

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "code": self.code,
            "rejection_layer": self.rejection_layer,
            "message": str(self),
        }
        if self.unsupported_value is not None:
            payload["unsupported_value"] = self.unsupported_value
        return payload


@dataclass
class _ParsedArgs:
    sim_accel: str | None = None
    sim_accel_states: str | None = None
    sim_accel_steps: str | None = None
    sim_accel_shape: str | None = None
    ordinary_verilator_args: list[str] = field(default_factory=list)
    mdir: str | None = None
    top_module: str | None = None
    source_files: list[str] = field(default_factory=list)
    filelists: list[str] = field(default_factory=list)
    defines: list[str] = field(default_factory=list)
    include_dirs: list[str] = field(default_factory=list)
    warning_flags: list[str] = field(default_factory=list)


def _parser_error(code: str, message: str, *, unsupported_value: str | None = None) -> NativeOptionParserStubError:
    return NativeOptionParserStubError(code, message, unsupported_value=unsupported_value)


def _take_value(tokens: Sequence[str], index: int, option: str) -> tuple[str, int]:
    if index + 1 >= len(tokens):
        raise _parser_error(
            "missing_sim_accel_shape_half",
            f"{option} requires a value in the native parser-stub fixture",
        )
    return tokens[index + 1], index + 2


def _split_long_option(token: str, option: str) -> str | None:
    prefix = f"{option}="
    if token.startswith(prefix):
        return token[len(prefix) :]
    return None


def _record_ordinary_arg(parsed: _ParsedArgs, tokens: Sequence[str], index: int) -> int:
    token = tokens[index]
    parsed.ordinary_verilator_args.append(token)

    if token == "-Mdir" and index + 1 < len(tokens):
        value = tokens[index + 1]
        parsed.ordinary_verilator_args.append(value)
        parsed.mdir = value
        return index + 2
    if token.startswith("-Mdir="):
        parsed.mdir = token.split("=", 1)[1]
    elif token == "--top-module" and index + 1 < len(tokens):
        value = tokens[index + 1]
        parsed.ordinary_verilator_args.append(value)
        parsed.top_module = value
        return index + 2
    elif token.startswith("--top-module="):
        parsed.top_module = token.split("=", 1)[1]
    elif token == "-f" and index + 1 < len(tokens):
        value = tokens[index + 1]
        parsed.ordinary_verilator_args.append(value)
        parsed.filelists.append(value)
        return index + 2
    elif token.startswith("-f") and len(token) > 2:
        parsed.filelists.append(token[2:])
    elif token == "-I" and index + 1 < len(tokens):
        value = tokens[index + 1]
        parsed.ordinary_verilator_args.append(value)
        parsed.include_dirs.append(value)
        return index + 2
    elif token.startswith("-I") and len(token) > 2:
        parsed.include_dirs.append(token)
    elif token.startswith("+incdir+"):
        parsed.include_dirs.append(token)
    elif token.startswith("-D") or token.startswith("+define+"):
        parsed.defines.append(token)
    elif token.startswith("-W"):
        parsed.warning_flags.append(token)
    elif _looks_like_source_file(token):
        parsed.source_files.append(token)
    return index + 1


def _looks_like_source_file(token: str) -> bool:
    return token.endswith((".v", ".sv", ".vh", ".svh", ".vlt"))


def _parse_argv(argv: Sequence[str]) -> _ParsedArgs:
    tokens = list(argv)
    parsed = _ParsedArgs()
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "--sim-accel":
            parsed.sim_accel, index = _take_value(tokens, index, token)
            continue
        value = _split_long_option(token, "--sim-accel")
        if value is not None:
            parsed.sim_accel = value
            index += 1
            continue
        if token == "--sim-accel-states":
            parsed.sim_accel_states, index = _take_value(tokens, index, token)
            continue
        value = _split_long_option(token, "--sim-accel-states")
        if value is not None:
            parsed.sim_accel_states = value
            index += 1
            continue
        if token == "--sim-accel-steps":
            parsed.sim_accel_steps, index = _take_value(tokens, index, token)
            continue
        value = _split_long_option(token, "--sim-accel-steps")
        if value is not None:
            parsed.sim_accel_steps = value
            index += 1
            continue
        if token == "--sim-accel-shape":
            parsed.sim_accel_shape, index = _take_value(tokens, index, token)
            continue
        value = _split_long_option(token, "--sim-accel-shape")
        if value is not None:
            parsed.sim_accel_shape = value
            index += 1
            continue
        index = _record_ordinary_arg(parsed, tokens, index)
    return parsed


def _positive_count(raw: str, *, option_name: str) -> int:
    try:
        value = int(raw, 10)
    except ValueError as exc:
        raise _parser_error(
            "nonpositive_sim_accel_count",
            f"{option_name} must be a positive integer in the native parser-stub fixture",
        ) from exc
    if value <= 0:
        raise _parser_error(
            "nonpositive_sim_accel_count",
            f"{option_name} must be a positive integer in the native parser-stub fixture",
        )
    return value


def _validate_shape(parsed: _ParsedArgs) -> tuple[int, int]:
    if parsed.sim_accel is None:
        raise _parser_error(
            "missing_sim_accel",
            "--sim-accel must be provided explicitly in the native parser-stub fixture",
        )
    if parsed.sim_accel != SIDECAR_ACCEL:
        raise _parser_error(
            "invalid_sim_accel",
            f"unsupported --sim-accel {parsed.sim_accel!r}; only {SIDECAR_ACCEL!r} is supported",
            unsupported_value=parsed.sim_accel,
        )
    if parsed.sim_accel_shape is not None:
        raise _parser_error(
            "compact_shape_spelling_outside_native_minimum",
            "compact --sim-accel-shape is wrapper compatibility and outside the native parser-stub minimum; "
            "use --sim-accel-states and --sim-accel-steps",
        )
    if parsed.sim_accel_states is None or parsed.sim_accel_steps is None:
        raise _parser_error(
            "missing_sim_accel_shape_half",
            "--sim-accel-states and --sim-accel-steps must be provided together",
        )
    state_count = _positive_count(parsed.sim_accel_states, option_name="--sim-accel-states")
    step_count = _positive_count(parsed.sim_accel_steps, option_name="--sim-accel-steps")
    return state_count, step_count


def parse_verilator_native_option_stub(argv: Sequence[str]) -> dict[str, object]:
    """Parse a future Verilator option shape into a parser-only sidecar handoff."""

    parsed = _parse_argv(argv)
    state_count, step_count = _validate_shape(parsed)
    handoff = {
        "schema_version": 1,
        "surface": SURFACE,
        "accelerator_mode": SIDECAR_ACCEL,
        "state_count": state_count,
        "step_count": step_count,
        "shape": f"{state_count}x{step_count}",
        "ordinary_verilator_args": parsed.ordinary_verilator_args,
        "mdir": parsed.mdir,
        "top_module": parsed.top_module,
        "source_files": parsed.source_files,
        "filelists": parsed.filelists,
        "defines": parsed.defines,
        "include_dirs": parsed.include_dirs,
        "warning_flags": parsed.warning_flags,
        "source_boundary_status": SOURCE_BOUNDARY_STATUS,
        "state_and_report_naming_rules": "deterministic_rules_unresolved_by_parser_stub",
        "correctness_policy": CORRECTNESS_POLICY,
        "non_claims": [
            "parser stub fixture does not execute Verilator or hybrid runtime",
            "parser stub fixture does not infer source closure, coverage manifests, reports, or state paths",
            "parser stub fixture is not a native Verilator parser patch",
            "parser stub fixture does not perform automatic GPU allocation",
        ],
    }
    assert tuple(handoff.keys()) == HANDOFF_FIELDS
    return handoff
