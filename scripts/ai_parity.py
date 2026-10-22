#!/usr/bin/env python3
"""BOO-145 provider-neutral parity check for the ``ai`` platform boundary.

``fixtures/gates/provider-neutral-parity.json`` records the routing, budget,
redaction and evaluation behaviour of the current implementation (the hosted
gateway in ``bookchaowalit/platform-ai-gateway-api`` plus the agent routing and
context redaction scripts in ``bookchaowalit/solo-empire``). This script:

* validates the fixture offline (always; runs in CI through the unit tests);
* evaluates the fixture's routing and redaction cases with a small oracle that
  interprets the fixture rules, so the cases stay self-consistent;
* with ``--gateway-root`` and/or ``--solo-empire`` (local, read-only), re-derives
  the facts from those checkouts, runs the same cases against the real current
  code, and reports drift. The gateway cases need ``tsx`` from the gateway
  checkout (``npm ci`` there first).

It never contacts an external network service, never reads ``.env`` files or
credentials, and only uses synthetic data.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_RELATIVE = "fixtures/gates/provider-neutral-parity.json"
GATE_DOC_RELATIVE = "docs/gates/BOO-145-provider-neutral-parity.md"
HARNESS_RELATIVE = "scripts/ai_parity_gateway_harness.mjs"
DECISION_STATE = "owner-decision-accepted"
DECISION_DATE = "2026-10-16"
DECISION_OPTION = "accept parity evidence; no cutover"
DECISION_HEADING = "Owner decision — ACCEPTED (owner decision 2026-10-16)"
SNAKE_LITERAL_RE = re.compile(r"'([a-z]+(?:_[a-z]+)*)'")


# --- fixture loading and offline validation ---------------------------------

def load_fixture(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or ROOT / FIXTURE_RELATIVE).read_text(encoding="utf-8"))


def _case_ids(fixture: dict[str, Any]) -> set[str]:
    evaluation = fixture.get("evaluation", {})
    ids: set[str] = set()
    for key in ("routing_cases", "redaction_cases", "gateway_cases"):
        ids.update(case["id"] for case in evaluation.get(key, []))
    return ids


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def validate_fixture(fixture: dict[str, Any]) -> list[str]:
    """Return integrity errors that do not need any source checkout."""

    errors: list[str] = []
    for key in ("issue", "next_gate", "contract", "sources", "routing", "budget", "redaction", "evaluation", "gaps"):
        if key not in fixture:
            errors.append(f"fixture is missing {key!r}")
    if errors:
        return errors
    if fixture.get("decision_state") != DECISION_STATE:
        errors.append(f"decision_state must be {DECISION_STATE!r} (owner decision {DECISION_DATE})")
    decision = fixture.get("owner_decision") or {}
    if decision.get("status") != "accepted":
        errors.append("owner_decision.status must be 'accepted'")
    if decision.get("date") != DECISION_DATE:
        errors.append(f"owner_decision.date must be {DECISION_DATE!r}")
    if decision.get("accepted_option") != DECISION_OPTION:
        errors.append(f"owner_decision.accepted_option must be {DECISION_OPTION!r}")
    if decision.get("cutover_approved") is not False:
        errors.append("owner_decision.cutover_approved must be false (the accepted option is 'no cutover')")
    if fixture.get("synthetic_only") is not True:
        errors.append("synthetic_only must be true")
    for name, source in fixture["sources"].items():
        if not re.fullmatch(r"[0-9a-f]{40}", source.get("commit", "")):
            errors.append(f"sources.{name}.commit must be a full git SHA")
        for path, digest in source.get("files", {}).items():
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                errors.append(f"sources.{name}.files[{path!r}] must be a sha256 digest")

    routing = fixture["routing"]
    profiles = routing["profiles"]
    lanes = set(routing["service_lanes"])
    for name, profile in profiles.items():
        if profile["service_lane"] not in lanes:
            errors.append(f"profile {name} uses unknown service lane {profile['service_lane']!r}")
    rules = routing["workload_lane_rules"]
    buckets = [["interactive"], rules["gpu_worker_workloads"], rules["text_workloads"]]
    flattened = [item for bucket in buckets for item in bucket]
    for duplicate in sorted(_duplicates(flattened)):
        errors.append(f"workload {duplicate} is assigned to more than one lane rule")
    for missing in sorted(set(routing["workloads"]) - set(flattened)):
        errors.append(f"workload {missing} has no lane rule")
    for extra in sorted(set(flattened) - set(routing["workloads"])):
        errors.append(f"lane rule names unknown workload {extra}")
    for alias in sorted(set(routing["specialized_workload_aliases"]) - set(rules["gpu_worker_workloads"])):
        errors.append(f"specialised alias {alias} is not a gpu_worker workload")
    for profile_name, gateway_profile in routing["gateway"]["profiles"].items():
        if gateway_profile["routing_profile"] not in profiles:
            errors.append(f"gateway profile {profile_name} maps to unknown routing profile")
    if set(routing["hosted_blocked_privacy_classes"]) - set(routing["privacy_classes"]):
        errors.append("hosted_blocked_privacy_classes must be privacy classes")

    reasons = fixture["budget"]["monthly_guard"]["reasons"]
    for duplicate in sorted(_duplicates(reason for bucket in reasons.values() for reason in bucket)):
        errors.append(f"budget reason {duplicate} is classified more than once")
    if reasons.get("allow") != ["within_budget"]:
        errors.append("the only allow reason must be within_budget (every other reason fails closed)")
    denial = fixture["budget"]["fail_closed"]["pre_provider_denial"]
    if denial.get("provider_calls") != 0 or denial.get("estimated_cost_usd") != 0:
        errors.append("pre-provider budget denial must record zero provider calls and zero cost")

    redaction = fixture["redaction"]
    case_ids = _case_ids(fixture)
    for duplicate in sorted(_duplicates(rule["id"] for rule in redaction["rules"])):
        errors.append(f"redaction rule id {duplicate} is duplicated")
    for rule in redaction["rules"]:
        if not rule.get("source"):
            errors.append(f"redaction rule {rule['id']} has no source citation")
        if not rule.get("parity_cases") and not rule.get("static_check"):
            errors.append(f"redaction rule {rule['id']} has neither parity cases nor a static check")
        for case in rule.get("parity_cases", []):
            if case not in case_ids:
                errors.append(f"redaction rule {rule['id']} references unknown case {case}")
    stored = set(redaction["telemetry_columns"]) | {"metadata"}
    for field in redaction["telemetry_event_fields"]:
        if field not in stored:
            errors.append(f"telemetry field {field} has no telemetry column")
    forbidden = {"prompt", "messages", "content", "response", "api_key", "authorization", "token"}
    for key in redaction["telemetry_event_fields"] + redaction["telemetry_metadata_keys"] + redaction["service_log_keys"]:
        if key in forbidden:
            errors.append(f"content-bearing key {key} must not be an allowed telemetry/log key")

    evaluation = fixture["evaluation"]
    gap_ids = {gap["id"] for gap in fixture["gaps"]}
    for duplicate in sorted(_duplicates(gap["id"] for gap in fixture["gaps"])):
        errors.append(f"gap id {duplicate} is duplicated")
    if len(evaluation["scenarios"]) != 10:
        errors.append("evaluation must map all 10 scenarios of ai-api-control-plane-eval-v1")
    for scenario in evaluation["scenarios"]:
        if not scenario["parity_cases"] and scenario.get("gap") not in gap_ids:
            errors.append(f"scenario {scenario['name']!r} has no parity case and no recorded gap")
        for case in scenario["parity_cases"]:
            if case not in case_ids:
                errors.append(f"scenario {scenario['name']!r} references unknown case {case}")
    for case in evaluation["redaction_cases"]:
        if case.get("gap") and case["gap"] not in gap_ids:
            errors.append(f"redaction case {case['id']} references unknown gap {case['gap']}")
    all_ids = [case["id"] for key in ("routing_cases", "redaction_cases", "gateway_cases") for case in evaluation[key]]
    for duplicate in sorted(_duplicates(all_ids)):
        errors.append(f"case id {duplicate} is duplicated")
    for case in evaluation["routing_cases"]:
        for key in ("requested", "selected"):
            if case["expect"][key] not in profiles:
                errors.append(f"routing case {case['id']} expects unknown profile {case['expect'][key]!r}")
    canaries = evaluation["synthetic_canaries"]
    if "SYNTHETIC" not in canaries["secret"] or "SYNTHETIC" not in canaries["provider_error_body"]:
        errors.append("secret canaries must be marked SYNTHETIC")
    if not canaries["email"].endswith(".invalid"):
        errors.append("canary email must use a reserved .invalid domain")
    return errors


# --- oracle: interprets the fixture's rules ----------------------------------

def oracle_route(fixture: dict[str, Any], case_input: dict[str, Any]) -> dict[str, Any]:
    """Apply the fixture's routing rules to one synthetic request."""

    routing = fixture["routing"]
    rules = routing["workload_lane_rules"]
    task = case_input["task"].strip()
    route = case_input["route"].strip()
    operation = case_input["operation"]
    workload = case_input.get("workload", "agent")
    privacy = case_input.get("privacy_class", "internal")
    adapters = set(case_input.get("available_adapters", ["local", "subscription"]))
    budgets = routing["default_token_budget"]
    token_budget = case_input.get("token_budget")
    if token_budget is None:
        token_budget = budgets["inspect"] if operation == "inspect" else budgets["other"]
    latency = case_input.get("latency_target_ms")

    if workload == "interactive":
        requested = rules["interactive"]
    elif workload in rules["gpu_worker_workloads"]:
        requested = "gpu_worker"
    elif case_input.get("quality"):
        requested = case_input["quality"]
    elif any(term in task.casefold() for term in routing["quality_terms"]) or token_budget > routing["quality_token_threshold"]:
        requested = "quality"
    elif latency is not None and latency <= routing["fast_latency_threshold_ms"] or operation in routing["fast_operations"] or route in routing["fast_routes"]:
        requested = "fast"
    else:
        requested = "balanced"

    order = routing["fallback_order"]
    chain = order["explicit_lane_chain"] if requested in order["explicit_lanes"] else order["text_chain"]
    names = list(dict.fromkeys(requested if item == "<requested>" else item for item in chain))
    candidates: list[list[str]] = []
    selected: str | None = None
    for name in names:
        profile = routing["profiles"][name]
        if privacy in routing["hosted_blocked_privacy_classes"] and profile["service_lane"] in {"api", "subscription", "runpod"}:
            status = "excluded"
        elif profile["adapter"] not in adapters:
            status = "unavailable"
        else:
            status = "available"
        candidates.append([name, status])
        if selected is None and status == "available":
            selected = name
    if selected is None:
        raise ValueError("no compatible model adapter is available")
    if selected == "local_reference":
        reason = ("requested_service_lane_unavailable_fallback_to_local" if requested in order["explicit_lanes"]
                  else "local_reference_is_only_configured_adapter")
    else:
        reason = "requested_profile_available" if selected == requested else "fallback_to_available_adapter"
    profile = routing["profiles"][selected]
    return {
        "requested": requested,
        "selected": selected,
        "service_lane": profile["service_lane"],
        "selection_reason": reason,
        "candidates": candidates,
        "credentials_required": profile["adapter"] in routing["credentials_required_adapters"],
        "max_output_tokens": min(profile["max_output_tokens"], token_budget),
        "token_budget": token_budget,
    }


def oracle_redact(fixture: dict[str, Any], text: str) -> tuple[str, int]:
    """Apply the fixture's agent-context secret patterns to synthetic text."""

    patterns = fixture["redaction"]["secret_patterns"]
    secret_re = re.compile(patterns["secret_value"])
    bearer_re = re.compile(patterns["bearer"])
    pem_re = re.compile(patterns["pem"])
    total = 0
    output: list[str] = []
    for line in text.splitlines(keepends=True):
        count = 0

        def replace(match: re.Match[str]) -> str:
            nonlocal count
            count += 1
            return match.group(1) + patterns["value_replacement"]

        line = secret_re.sub(replace, line)
        line = bearer_re.sub(replace, line)
        if pem_re.search(line):
            line, count = patterns["pem_line_replacement"], count + 1
        output.append(line)
        total += count
    return "".join(output), total


def check_oracle(fixture: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for case in fixture["evaluation"]["routing_cases"]:
        observed = oracle_route(fixture, case["input"])
        if observed != case["expect"]:
            errors.append(f"oracle routing {case['id']}: expected {case['expect']}, got {observed}")
    for case in fixture["evaluation"]["redaction_cases"]:
        observed = oracle_redact(fixture, case["input"])
        if observed != (case["expect_output"], case["expect_count"]):
            errors.append(f"oracle redaction {case['id']}: expected {(case['expect_output'], case['expect_count'])!r}, got {observed!r}")
    return errors


# --- static extraction from the current gateway (TypeScript) ------------------

def _block(text: str, start_pattern: str) -> str:
    match = re.search(start_pattern, text)
    if not match:
        raise ValueError(f"pattern not found: {start_pattern}")
    return text[match.end():]


def extract_profile_default_output(text: str) -> dict[str, int]:
    block = _block(text, r"PROFILE_DEFAULT_OUTPUT[^=]*=\s*\{")
    block = block[: block.index("}")]
    return {key: int(value.replace("_", "")) for key, value in re.findall(r"(\w+):\s*([\d_]+)", block)}


def extract_string_set(text: str, name: str) -> list[str]:
    match = re.search(rf"const {name}\s*=\s*new Set(?:<[^>]+>)?\(\[([^\]]*)\]\)", text)
    if not match:
        raise ValueError(f"set {name} not found")
    return re.findall(r"'([^']*)'", match.group(1))


def extract_bounded_ints(text: str) -> dict[str, dict[str, Any]]:
    """Map each ``boundedInt(env.X, default, min, max)`` call to its literal bounds."""

    found: dict[str, dict[str, Any]] = {}
    pattern = re.compile(r"boundedInt\(\s*env\.(\w+),\s*([^,]+?),\s*([\d_]+),\s*([\d_]+)\s*,?\s*\)", re.DOTALL)
    for name, default, low, high in pattern.findall(text):
        default = default.strip()
        if re.fullmatch(r"[\d_]+", default):
            default_value: Any = int(default.replace("_", ""))
        else:
            nested = re.search(r"env\.(\w+)", default)
            default_value = nested.group(1) if nested else default
        found.setdefault(name, {"default": default_value, "min": int(low.replace("_", "")), "max": int(high.replace("_", ""))})
    # AI_GATEWAY_MAX_TOKEN_BUDGET defaults to the default budget (variable, not a literal).
    match = re.search(r"boundedInt\(env\.AI_GATEWAY_MAX_TOKEN_BUDGET,\s*defaultTokenBudget,\s*([\d_]+),\s*([\d_]+)\)", text)
    if match:
        found["AI_GATEWAY_MAX_TOKEN_BUDGET"] = {"default": "AI_GATEWAY_DEFAULT_TOKEN_BUDGET", "min": int(match.group(1).replace("_", "")), "max": int(match.group(2).replace("_", ""))}
    reasoning = re.search(r"boundedInt\(\s*env\.AI_GATEWAY_REASONING_TIMEOUT_MS,\s*boundedInt\(env\.(\w+)[^)]*\),\s*([\d_]+),\s*([\d_]+)", text)
    if reasoning:
        found["AI_GATEWAY_REASONING_TIMEOUT_MS"] = {"default": reasoning.group(1), "min": int(reasoning.group(2).replace("_", "")), "max": int(reasoning.group(3).replace("_", ""))}
    return found


def extract_error_classes(text: str) -> list[str]:
    ignore = {"failure", "success", "error", "budget_exceeded", "unknown"}
    classes: set[str] = set()
    for line in text.splitlines():
        if "errorClass" in line or "telemetryForError(" in line:
            classes.update(literal for literal in SNAKE_LITERAL_RE.findall(line) if literal not in ignore)
    return sorted(classes)


def extract_interface_fields(text: str, name: str) -> list[str]:
    block = _block(text, rf"export interface {name}\s*\{{")
    block = block[: block.index("\n}")]
    return re.findall(r"^\s{2}(\w+)\??:", block, re.MULTILINE)


def extract_model_envs(text: str) -> list[str]:
    return sorted(set(re.findall(r"env\.(AI_GATEWAY_(?:FALLBACK_)?MODEL(?:_[A-Z]+)?)\b", text)))


def extract_hosted_blocked(text: str) -> list[str]:
    match = re.search(r"if \((privacyClass === '\w+'(?:\s*\|\|\s*privacyClass === '\w+')*)\)\s*\{\s*throw new AiGatewayError\(403", text)
    if not match:
        raise ValueError("hosted privacy block not found")
    return re.findall(r"'(\w+)'", match.group(1))


def extract_budget_reasons(text: str) -> list[str]:
    # Reasons are multi-word snake_case identifiers; ledger event names are not reasons.
    ignore = {"session_started", "session_stopped"}
    return sorted({literal for literal in SNAKE_LITERAL_RE.findall(text) if "_" in literal and literal not in ignore})


def extract_sql_columns(text: str) -> list[str]:
    body = _block(text, r"CREATE TABLE IF NOT EXISTS ai_run_telemetry \(")
    body = body[: body.index(");")]
    return re.findall(r"^\s{4}(\w+)\s", body, re.MULTILINE)


def extract_log_keys(text: str) -> list[str]:
    block = _block(text, r"event: 'ai_gateway\.run',")
    block = block[: block.index("...fields")]
    return ["ts", "event"] + re.findall(r"^\s+(\w+):", block, re.MULTILINE)


def extract_log_extra_keys(text: str) -> list[str]:
    keys: set[str] = set()
    for args in re.findall(r"logRun\(\{([^}]*)\}", text):
        keys.update(re.findall(r"(\w+):", args))
        keys.update(re.findall(r"(?:^|,)\s*(\w+)\s*(?=,|$)", args))
    return sorted(keys)


def gateway_facts(gateway_root: Path) -> dict[str, Any]:
    gateway = (gateway_root / "api/ai_gateway.ts").read_text(encoding="utf-8")
    budget = (gateway_root / "api/ai_budget.ts").read_text(encoding="utf-8")
    service = (gateway_root / "api/ai-gateway-service/service.ts").read_text(encoding="utf-8")
    sql = (gateway_root / "database/migrations/025_ai_run_telemetry.sql").read_text(encoding="utf-8")
    limits = extract_bounded_ints(gateway)
    return {
        "profile_default_output": extract_profile_default_output(gateway),
        "privacy_classes": extract_string_set(gateway, "PRIVACY_CLASSES"),
        "profiles": extract_string_set(gateway, "PROFILES"),
        "response_formats": extract_string_set(gateway, "RESPONSE_FORMATS"),
        "request_reasoning_efforts": extract_string_set(gateway, "REQUEST_REASONING_EFFORTS"),
        "hosted_blocked_privacy_classes": extract_hosted_blocked(gateway),
        "request_limits": {name: limits[name] for name in sorted(limits) if re.search(r"TOKEN|CONTEXT|TIMEOUT", name)},
        "model_envs": extract_model_envs(gateway),
        "error_classes": extract_error_classes(gateway),
        "telemetry_event_fields": extract_interface_fields(gateway, "AiTelemetryEvent"),
        "budget_reasons": extract_budget_reasons(budget),
        "telemetry_columns": extract_sql_columns(sql),
        "service_log_keys": extract_log_keys(service),
        "service_log_extra_keys": extract_log_extra_keys(service),
    }


def compare_gateway(fixture: dict[str, Any], gateway_root: Path) -> tuple[list[str], list[str]]:
    facts = gateway_facts(gateway_root)
    routing = fixture["routing"]
    gateway = routing["gateway"]
    redaction = fixture["redaction"]
    budget_reasons = sorted(reason for bucket in fixture["budget"]["monthly_guard"]["reasons"].values() for reason in bucket)
    expected = {
        "profile_default_output": {name: value["default_max_output_tokens"] for name, value in gateway["profiles"].items()},
        "privacy_classes": routing["privacy_classes"],
        "profiles": list(gateway["profiles"]),
        "response_formats": gateway["response_formats"],
        "request_reasoning_efforts": gateway["request_reasoning_efforts"],
        "hosted_blocked_privacy_classes": routing["hosted_blocked_privacy_classes"],
        "request_limits": fixture["budget"]["request_limits"],
        "model_envs": sorted({gateway["shared_model_env"], gateway["shared_fallback_env"]}
                             | {value["model_env"] for value in gateway["profiles"].values()}
                             | {value["fallback_env"] for value in gateway["profiles"].values()}),
        "error_classes": redaction["error_classes"],
        "telemetry_event_fields": redaction["telemetry_event_fields"],
        "budget_reasons": budget_reasons,
        "telemetry_columns": redaction["telemetry_columns"],
        "service_log_keys": redaction["service_log_keys"],
        "service_log_extra_keys": sorted(redaction["service_log_extra_keys"]),
    }
    errors: list[str] = []
    for key, value in expected.items():
        observed = facts[key]
        if isinstance(value, dict):
            same = observed == value
        else:
            same = sorted(observed) == sorted(value)
        if not same:
            errors.append(f"gateway drift in {key}: fixture {value} != source {observed}")
    return errors, pin_warnings(fixture["sources"]["gateway"], gateway_root)


def pin_warnings(source: dict[str, Any], root: Path) -> list[str]:
    warnings: list[str] = []
    for relative, digest in source["files"].items():
        path = root / relative
        if not path.is_file():
            warnings.append(f"{source['repository']}:{relative} is missing from {root}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            warnings.append(f"{source['repository']}:{relative} changed since {source['commit'][:7]} (sha256 {actual[:12]}); re-review the fixture")
    return warnings


# --- current agent routing / redaction (Python, solo-empire hub) -------------

def _load_module(name: str, path: Path):
    agent_dir = path.parent
    for extra in (str(agent_dir), str(agent_dir.parent / "utils")):
        if extra not in sys.path:
            sys.path.insert(0, extra)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_current_routing(solo_root: Path):
    return _load_module("boo145_current_model_routing", solo_root / "infra/scripts/agent/model_routing.py")


def load_current_context_pack(solo_root: Path):
    return _load_module("boo145_current_context_pack", solo_root / "infra/scripts/agent/context_pack.py")


def _requested_profile_literals(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    facts: dict[str, Any] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_requested_profile":
            for inner in ast.walk(node):
                if isinstance(inner, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "quality_terms" for t in inner.targets):
                    facts["quality_terms"] = list(ast.literal_eval(inner.value))
                if isinstance(inner, ast.Compare) and isinstance(inner.left, ast.Name):
                    op, right = inner.ops[0], inner.comparators[0]
                    if inner.left.id == "workload" and isinstance(op, ast.In) and isinstance(right, ast.Set):
                        facts["gpu_worker_workloads"] = sorted(ast.literal_eval(right))
                    if inner.left.id == "token_budget" and isinstance(op, ast.Gt):
                        facts["quality_token_threshold"] = ast.literal_eval(right)
                    if inner.left.id == "latency_target_ms" and isinstance(op, ast.LtE):
                        facts["fast_latency_threshold_ms"] = ast.literal_eval(right)
                    if inner.left.id == "route" and isinstance(op, ast.In):
                        facts["fast_routes"] = sorted(ast.literal_eval(right))
                    if inner.left.id == "operation" and isinstance(op, ast.Eq):
                        facts["fast_operations"] = [ast.literal_eval(right)]
    match = re.search(r"token_budget = (\d+) if operation == \"inspect\" else (\d+)", source)
    if match:
        facts["default_token_budget"] = {"inspect": int(match.group(1)), "other": int(match.group(2))}
    return facts


def compare_routing(fixture: dict[str, Any], solo_root: Path) -> tuple[list[str], list[str]]:
    module = load_current_routing(solo_root)
    routing = fixture["routing"]
    errors: list[str] = []
    catalog = {name: {key: value for key, value in profile.to_dict().items() if key != "name"} for name, profile in module.PROFILE_CATALOG.items()}
    checks: dict[str, tuple[Any, Any]] = {
        "policy_version": (routing["policy_version"], module.ROUTING_POLICY_VERSION),
        "profiles": (routing["profiles"], catalog),
        "workloads": (sorted(routing["workloads"]), sorted(module.WORKLOADS)),
        "privacy_classes": (routing["privacy_classes"], list(module.PRIVACY_CLASSES)),
        "specialized_workload_aliases": (routing["specialized_workload_aliases"], dict(module.SPECIALIZED_WORKLOAD_ALIASES)),
    }
    literals = _requested_profile_literals((solo_root / "infra/scripts/agent/model_routing.py").read_text(encoding="utf-8"))
    for key in ("quality_terms", "quality_token_threshold", "fast_latency_threshold_ms", "fast_routes", "fast_operations", "default_token_budget"):
        checks[key] = (routing[key], literals.get(key))
    checks["gpu_worker_workloads"] = (sorted(routing["workload_lane_rules"]["gpu_worker_workloads"]), literals.get("gpu_worker_workloads"))
    for key, (expected, observed) in checks.items():
        if expected != observed:
            errors.append(f"agent routing drift in {key}: fixture {expected} != source {observed}")
    for case in fixture["evaluation"]["routing_cases"]:
        plan = module.build_routing_plan(**case["input"])
        observed = {
            "requested": plan["requested_profile"]["name"],
            "selected": plan["selected_profile"]["name"],
            "service_lane": plan["service_lane"],
            "selection_reason": plan["selection_reason"],
            "candidates": [[item["profile"]["name"], item["status"]] for item in plan["candidates"]],
            "credentials_required": plan["credentials_required"],
            "max_output_tokens": plan["token_policy"]["max_output_tokens"],
            "token_budget": plan["token_budget"],
        }
        if observed != case["expect"]:
            errors.append(f"current routing {case['id']}: expected {case['expect']}, got {observed}")
        if case["input"]["task"] in json.dumps(plan, ensure_ascii=False):
            errors.append(f"current routing {case['id']}: plan echoes the raw task (RD-7)")
    context_pack = load_current_context_pack(solo_root)
    patterns = fixture["redaction"]["secret_patterns"]
    for attr, key in (("_SECRET_VALUE_RE", "secret_value"), ("_BEARER_RE", "bearer"), ("_PEM_RE", "pem")):
        current = getattr(context_pack, attr)
        pattern = current.pattern
        if pattern != patterns[key]:
            errors.append(f"agent redaction drift in {key}: fixture {patterns[key]!r} != source {pattern!r}")
    for case in fixture["evaluation"]["redaction_cases"]:
        observed = context_pack.redact_text(case["input"])
        if tuple(observed) != (case["expect_output"], case["expect_count"]):
            errors.append(f"current redaction {case['id']}: expected {(case['expect_output'], case['expect_count'])!r}, got {tuple(observed)!r}")
    return errors, pin_warnings(fixture["sources"]["agent_routing"], solo_root)


# --- current gateway behaviour (TypeScript via tsx harness) ------------------

def find_tsx(gateway_root: Path) -> Path | None:
    override = os.environ.get("PLATFORM_AI_PARITY_TSX")
    candidate = Path(override) if override else gateway_root / "node_modules/.bin/tsx"
    return candidate if candidate.is_file() else None


def run_gateway_cases(fixture_path: Path, gateway_root: Path, tsx: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [str(tsx), str(ROOT / HARNESS_RELATIVE), str(gateway_root), str(fixture_path)],
        capture_output=True, text=True, timeout=120, check=False,
        env={"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "/tmp")},
    )
    if completed.returncode != 0:
        raise RuntimeError(f"gateway harness failed ({completed.returncode}): {completed.stderr.strip()[-2000:]}")
    return json.loads(completed.stdout.strip().splitlines()[-1])


def compare_gateway_cases(fixture: dict[str, Any], observed: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    redaction = fixture["redaction"]
    allowed_metadata = set(redaction["telemetry_metadata_keys"])
    allowed_fields = set(redaction["telemetry_event_fields"])
    for case in fixture["evaluation"]["gateway_cases"]:
        result = observed.get(case["id"])
        if result is None:
            errors.append(f"gateway case {case['id']} was not executed")
            continue
        for key, expected in case["expect"].items():
            if key == "telemetry_fields_subset":
                actual = set(result.get("telemetry_fields", [])) <= allowed_fields
            elif key == "metadata_keys_subset":
                actual = set(result.get("metadata_keys", [])) <= allowed_metadata
            else:
                actual = result.get(key)
            if actual != expected:
                errors.append(f"gateway case {case['id']}.{key}: expected {expected!r}, got {actual!r}")
        extra_fields = set(result.get("telemetry_fields", [])) - allowed_fields
        extra_metadata = set(result.get("metadata_keys", [])) - allowed_metadata
        if extra_fields or extra_metadata:
            errors.append(f"gateway case {case['id']} emitted unlisted telemetry keys {sorted(extra_fields | extra_metadata)}")
        if result.get("telemetry_contains_canary"):
            errors.append(f"gateway case {case['id']} leaked a synthetic canary into telemetry")
    return errors


# --- CLI ---------------------------------------------------------------------

def run(fixture_path: Path, gateway_root: Path | None, solo_root: Path | None) -> tuple[list[str], list[str]]:
    fixture = load_fixture(fixture_path)
    errors = validate_fixture(fixture)
    if errors:
        return errors, []
    errors += check_oracle(fixture)
    warnings: list[str] = []
    if gateway_root is not None:
        gateway_errors, gateway_warnings = compare_gateway(fixture, gateway_root)
        errors += gateway_errors
        warnings += gateway_warnings
        tsx = find_tsx(gateway_root)
        if tsx is None:
            warnings.append("tsx not found in the gateway checkout; run `npm ci` there to execute gateway cases")
        else:
            errors += compare_gateway_cases(fixture, run_gateway_cases(fixture_path, gateway_root, tsx))
    if solo_root is not None:
        routing_errors, routing_warnings = compare_routing(fixture, solo_root)
        errors += routing_errors
        warnings += routing_warnings
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fixture", type=Path, default=ROOT / FIXTURE_RELATIVE)
    parser.add_argument("--gateway-root", type=Path, help="local platform-ai-gateway-api checkout (read-only)")
    parser.add_argument("--solo-empire", type=Path, help="local solo-empire checkout (read-only)")
    args = parser.parse_args(argv)
    errors, warnings = run(args.fixture, args.gateway_root, args.solo_empire)
    for warning in warnings:
        print(f"warning: {warning}")
    for error in errors:
        print(f"error: {error}")
    scope = ["fixture", "oracle"] + (["gateway-source", "gateway-cases"] if args.gateway_root else []) + (["agent-routing"] if args.solo_empire else [])
    print(f"ai parity: {'FAIL' if errors else 'OK'} ({', '.join(scope)}; {len(errors)} error(s), {len(warnings)} warning(s))")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
