"""BOO-145: provider-neutral routing, budget, redaction and evaluation parity.

Offline tests (always run, including CI) validate the fixture, evaluate its
routing/redaction cases with the fixture oracle, prove that the validators and
source extractors catch drift, and check the gate document.

Source tests run the same cases against the CURRENT implementation and are
skipped unless the local, read-only checkouts are named:

* ``PLATFORM_AI_PARITY_GATEWAY``: a ``bookchaowalit/platform-ai-gateway-api``
  checkout with ``npm ci`` run (provides ``tsx``; override with
  ``PLATFORM_AI_PARITY_TSX``);
* ``PLATFORM_AI_PARITY_SOLO_EMPIRE``: a ``bookchaowalit/solo-empire`` checkout.

The gateway (public) is enforced in CI by the ``gateway-parity`` job with
``REQUIRE_GATEWAY_PARITY=1``. solo-empire is private, so routing/redaction
parity against its real code is local-only and NOT enforced in CI.
"""

from __future__ import annotations

import copy
import importlib.util
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


parity = _load("platform_ai_parity", "scripts/ai_parity.py")
FIXTURE = parity.load_fixture()
GATEWAY_ROOT = os.environ.get("PLATFORM_AI_PARITY_GATEWAY")
# CI sets REQUIRE_GATEWAY_PARITY=1: a missing gateway checkout or tsx then fails
# instead of skipping, and a changed pinned source file is an error, not a warning.
REQUIRE_GATEWAY_PARITY = os.environ.get("REQUIRE_GATEWAY_PARITY") == "1"
SOLO_ROOT = os.environ.get("PLATFORM_AI_PARITY_SOLO_EMPIRE")


class FixtureIntegrityTests(unittest.TestCase):
    def test_fixture_is_valid(self) -> None:
        self.assertEqual(parity.validate_fixture(FIXTURE), [])

    def test_next_gate_matches_issue(self) -> None:
        self.assertEqual(FIXTURE["issue"], "BOO-145")
        self.assertEqual(
            FIXTURE["next_gate"],
            "Capture provider-neutral routing, budget, redaction, and evaluation parity before any hosted cutover.",
        )

    def test_owner_decision_is_accepted_on_2026_10_16(self) -> None:
        decision = FIXTURE["owner_decision"]
        self.assertEqual(FIXTURE["decision_state"], "owner-decision-accepted")
        self.assertEqual(decision["status"], "accepted")
        self.assertEqual(decision["date"], "2026-10-16")
        self.assertEqual(decision["accepted_option"], "accept parity evidence; no cutover")
        self.assertIs(decision["cutover_approved"], False)

    def test_owner_decision_marker_or_date_removed_fails(self) -> None:
        for path, label in ((("decision_state",), "decision_state"), (("owner_decision", "status"), "owner_decision.status"),
                            (("owner_decision", "date"), "owner_decision.date"), (("owner_decision",), "owner_decision.status")):
            mutated = copy.deepcopy(FIXTURE)
            target = mutated
            for key in path[:-1]:
                target = target[key]
            target.pop(path[-1])
            with self.subTest(removed=".".join(path)):
                self.assertTrue(any(label in error for error in parity.validate_fixture(mutated)))

    def test_owner_decision_cannot_approve_cutover(self) -> None:
        mutated = copy.deepcopy(FIXTURE)
        mutated["owner_decision"]["cutover_approved"] = True
        self.assertTrue(any("cutover_approved" in error for error in parity.validate_fixture(mutated)))

    def test_workload_without_lane_rule_fails(self) -> None:
        mutated = copy.deepcopy(FIXTURE)
        mutated["routing"]["workload_lane_rules"]["gpu_worker_workloads"].remove("detection")
        self.assertIn("workload detection has no lane rule", parity.validate_fixture(mutated))

    def test_budget_reason_classified_as_allow_fails(self) -> None:
        mutated = copy.deepcopy(FIXTURE)
        mutated["budget"]["monthly_guard"]["reasons"]["allow"].append("unmetered_api_events")
        errors = parity.validate_fixture(mutated)
        self.assertTrue(any("unmetered_api_events is classified more than once" in error for error in errors))
        self.assertTrue(any("only allow reason" in error for error in errors))

    def test_budget_denial_must_not_spend(self) -> None:
        mutated = copy.deepcopy(FIXTURE)
        mutated["budget"]["fail_closed"]["pre_provider_denial"]["provider_calls"] = 1
        self.assertTrue(any("zero provider calls" in error for error in parity.validate_fixture(mutated)))

    def test_content_key_cannot_be_allowed_in_telemetry(self) -> None:
        mutated = copy.deepcopy(FIXTURE)
        mutated["redaction"]["telemetry_metadata_keys"].append("prompt")
        self.assertIn(
            "content-bearing key prompt must not be an allowed telemetry/log key",
            parity.validate_fixture(mutated),
        )

    def test_redaction_rule_must_reference_known_case(self) -> None:
        mutated = copy.deepcopy(FIXTURE)
        mutated["redaction"]["rules"][0]["parity_cases"].append("GW-DOES-NOT-EXIST")
        self.assertTrue(any("unknown case GW-DOES-NOT-EXIST" in error for error in parity.validate_fixture(mutated)))

    def test_uncovered_scenario_needs_a_gap(self) -> None:
        mutated = copy.deepcopy(FIXTURE)
        scenario = next(item for item in mutated["evaluation"]["scenarios"] if not item["parity_cases"])
        scenario.pop("gap")
        self.assertTrue(any("no parity case and no recorded gap" in error for error in parity.validate_fixture(mutated)))

    def test_canaries_must_be_synthetic(self) -> None:
        mutated = copy.deepcopy(FIXTURE)
        mutated["evaluation"]["synthetic_canaries"]["email"] = "someone@example.com"
        self.assertIn("canary email must use a reserved .invalid domain", parity.validate_fixture(mutated))

    def test_every_eval_plan_scenario_is_mapped(self) -> None:
        names = [scenario["name"] for scenario in FIXTURE["evaluation"]["scenarios"]]
        self.assertEqual(len(names), 10)
        self.assertIn("Unknown rate card or monthly cap", names)
        self.assertIn("Telemetry privacy", names)


class OracleTests(unittest.TestCase):
    def test_routing_cases_match_fixture_rules(self) -> None:
        for case in FIXTURE["evaluation"]["routing_cases"]:
            with self.subTest(case=case["id"]):
                self.assertEqual(parity.oracle_route(FIXTURE, case["input"]), case["expect"])

    def test_redaction_cases_match_fixture_patterns(self) -> None:
        for case in FIXTURE["evaluation"]["redaction_cases"]:
            with self.subTest(case=case["id"]):
                self.assertEqual(parity.oracle_redact(FIXTURE, case["input"]), (case["expect_output"], case["expect_count"]))

    def test_synthetic_secret_canary_is_redacted(self) -> None:
        secret = FIXTURE["evaluation"]["synthetic_canaries"]["secret"]
        redacted, count = parity.oracle_redact(FIXTURE, f"api_key={secret}\nAuthorization: Bearer {secret}\n")
        self.assertNotIn(secret, redacted)
        self.assertEqual(count, 2)

    def test_private_data_never_selects_a_hosted_lane(self) -> None:
        for privacy in FIXTURE["routing"]["hosted_blocked_privacy_classes"]:
            for workload in ("agent", "interactive", "embedding"):
                plan = parity.oracle_route(FIXTURE, {
                    "task": "synthetic", "route": "ai-pipeline", "operation": "operate", "workload": workload,
                    "privacy_class": privacy, "available_adapters": ["local", "external", "subscription", "runpod"],
                })
                with self.subTest(privacy=privacy, workload=workload):
                    self.assertEqual(plan["service_lane"], "local")

    def test_mutated_threshold_breaks_a_case(self) -> None:
        mutated = copy.deepcopy(FIXTURE)
        mutated["routing"]["quality_token_threshold"] = 8000
        self.assertTrue(any("RT-05" in error for error in parity.check_oracle(mutated)))


# Made-up TypeScript (not taken from the gateway) shaped only to exercise the
# extractor regexes; identifiers, numbers and messages are deliberately different.
SAMPLE_GATEWAY = """
// synthetic extractor fixture
export const PROFILE_DEFAULT_OUTPUT: Map<Tier, number> = {
  fast: 300,
  balanced: 2_000,
  quality: 9000,
};
export const PRIVACY_CLASSES = new Set<Level>(['open', 'team', 'private', 'restricted']);
function demoLimits(env: Env) {
  const floor = boundedInt(env.AI_GATEWAY_DEFAULT_TOKEN_BUDGET, 1_000, 100, 9_999);
  return [floor, boundedInt(env.AI_GATEWAY_MAX_TOKEN_BUDGET, defaultTokenBudget, 100, 77_777)];
}
function demoGuard(privacyClass: string) {
  if (privacyClass === 'private' || privacyClass === 'restricted') { throw new AiGatewayError(403, 'demo refusal'); }
}
const errorClass = code === 1 ? 'demo_alpha' : 'demo_beta';
"""


class ExtractorTests(unittest.TestCase):
    def test_profile_default_output(self) -> None:
        self.assertEqual(parity.extract_profile_default_output(SAMPLE_GATEWAY), {"fast": 300, "balanced": 2000, "quality": 9000})

    def test_bounded_ints(self) -> None:
        limits = parity.extract_bounded_ints(SAMPLE_GATEWAY)
        self.assertEqual(limits["AI_GATEWAY_DEFAULT_TOKEN_BUDGET"], {"default": 1000, "min": 100, "max": 9999})
        self.assertEqual(limits["AI_GATEWAY_MAX_TOKEN_BUDGET"], {"default": "AI_GATEWAY_DEFAULT_TOKEN_BUDGET", "min": 100, "max": 77777})

    def test_hosted_block_and_error_classes(self) -> None:
        self.assertEqual(parity.extract_hosted_blocked(SAMPLE_GATEWAY), ["private", "restricted"])
        self.assertEqual(parity.extract_error_classes(SAMPLE_GATEWAY), ["demo_alpha", "demo_beta"])

    def test_dropping_hosted_block_is_detected(self) -> None:
        weakened = SAMPLE_GATEWAY.replace(" || privacyClass === 'restricted'", "")
        self.assertEqual(parity.extract_hosted_blocked(weakened), ["private"])

    def test_budget_reasons_ignore_ledger_events(self) -> None:
        text = "throw new AiBudgetError('x', 'invalid_budget'); event.event !== 'session_started'; decision: 'deny'"
        self.assertEqual(parity.extract_budget_reasons(text), ["invalid_budget"])

    def test_gateway_case_comparison_flags_leaks(self) -> None:
        observed = {case["id"]: dict(case["expect"]) for case in FIXTURE["evaluation"]["gateway_cases"]}
        for case in FIXTURE["evaluation"]["gateway_cases"]:
            result = observed[case["id"]]
            result.pop("telemetry_fields_subset", None)
            result.pop("metadata_keys_subset", None)
            result["telemetry_fields"] = []
            result["metadata_keys"] = []
        self.assertEqual(parity.compare_gateway_cases(FIXTURE, observed), [])
        observed["GW-REDACT-SUCCESS"]["telemetry_contains_canary"] = True
        observed["GW-REDACT-SUCCESS"]["metadata_keys"] = ["prompt"]
        errors = parity.compare_gateway_cases(FIXTURE, observed)
        self.assertTrue(any("leaked a synthetic canary" in error for error in errors))
        self.assertTrue(any("unlisted telemetry keys ['prompt']" in error for error in errors))


class GateDocumentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.doc = (ROOT / parity.GATE_DOC_RELATIVE).read_text(encoding="utf-8")

    def test_doc_quotes_gate_and_records_accepted_decision(self) -> None:
        self.assertIn(FIXTURE["next_gate"], self.doc)
        self.assertIn("## " + parity.DECISION_HEADING, self.doc)
        self.assertNotIn("PROPOSED, NOT ACCEPTED", self.doc)
        self.assertIn(FIXTURE["owner_decision"]["owner_answer_verbatim"], self.doc)
        self.assertIn(FIXTURE["owner_decision"]["accepted_option"], self.doc)
        self.assertIn(FIXTURE["contract"]["path"], self.doc)

    def test_doc_lists_every_gap_and_rule(self) -> None:
        for gap in FIXTURE["gaps"]:
            self.assertIn(gap["id"], self.doc)
        for rule in FIXTURE["redaction"]["rules"]:
            self.assertIn(rule["id"], self.doc)

    def test_readme_links_gate_doc(self) -> None:
        self.assertIn(parity.GATE_DOC_RELATIVE, (ROOT / "README.md").read_text(encoding="utf-8"))


class CurrentGatewayParityTests(unittest.TestCase):
    """Runs against the real gateway; enforced in CI by the gateway-parity job."""

    def setUp(self) -> None:
        if not GATEWAY_ROOT or not Path(GATEWAY_ROOT, "api/ai_gateway.ts").is_file():
            message = "set PLATFORM_AI_PARITY_GATEWAY to a platform-ai-gateway-api checkout"
            if REQUIRE_GATEWAY_PARITY:
                self.fail(f"REQUIRE_GATEWAY_PARITY=1 but the gateway checkout is missing: {message}")
            self.skipTest(message)
        self.root = Path(GATEWAY_ROOT)

    def test_static_facts_match_fixture(self) -> None:
        errors, warnings = parity.compare_gateway(FIXTURE, self.root)
        self.assertEqual(errors, [])
        if REQUIRE_GATEWAY_PARITY:
            self.assertEqual(warnings, [], "pinned gateway sources changed; re-review the fixture")

    def test_gateway_cases_against_real_code(self) -> None:
        tsx = parity.find_tsx(self.root)
        if tsx is None:
            if REQUIRE_GATEWAY_PARITY:
                self.fail("REQUIRE_GATEWAY_PARITY=1 but tsx is missing (run npm ci in the gateway checkout)")
            self.skipTest("tsx not installed in the gateway checkout (run npm ci there)")
        observed = parity.run_gateway_cases(ROOT / parity.FIXTURE_RELATIVE, self.root, tsx)
        self.assertEqual(parity.compare_gateway_cases(FIXTURE, observed), [])


@unittest.skipUnless(SOLO_ROOT, "set PLATFORM_AI_PARITY_SOLO_EMPIRE to a solo-empire checkout")
class CurrentAgentRoutingParityTests(unittest.TestCase):
    def test_routing_and_redaction_against_real_code(self) -> None:
        errors, _warnings = parity.compare_routing(FIXTURE, Path(SOLO_ROOT))
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
