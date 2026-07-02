import math

from jsonprofile.profile.constraints.constraints import OpaPolicyConstraint
from jsonprofile.profile.model import ValidationRuntimeConfiguration
from jsonprofile.validator.opa_engine import OpaEngine


class FakePolicy:
    def __init__(self, entrypoints=None):
        self.data_calls = []
        self.evaluate_calls = []
        self.entrypoints = entrypoints or {}

    def set_data(self, data):
        self.data_calls.append(data)

    def evaluate(self, input_data, entrypoint=None):
        self.evaluate_calls.append((input_data, entrypoint))
        return [{"result": [{"evaluation": True, "message": "ok"}]}]


def make_engine(bundle_data=None):
    engine = object.__new__(OpaEngine)
    engine.policy = FakePolicy()
    engine.__dict__["_bundle_data"] = bundle_data
    return engine


def make_engine_with_entrypoints(entrypoints, bundle_data=None):
    engine = object.__new__(OpaEngine)
    engine.policy = FakePolicy(entrypoints=entrypoints)
    engine.__dict__["_bundle_data"] = bundle_data
    return engine


def test_evaluate_accepts_dynamic_entrypoint_and_data():
    engine = make_engine(bundle_data={"source": "bundle"})

    result = engine.evaluate(
        input_data={"value": math.inf},
        entrypoint="dynamic/package/rule",
        data={"source": "dynamic", "bad": math.nan},
    )

    assert result == [{"evaluation": True, "message": "ok"}]
    assert engine.policy.data_calls == [{"source": "dynamic", "bad": None}]
    assert engine.policy.evaluate_calls == [({"value": None}, "dynamic/package/rule")]


def test_evaluate_restores_bundle_data_when_dynamic_data_is_omitted():
    engine = make_engine(bundle_data={"source": "bundle"})

    engine.evaluate(input_data={}, data={"source": "dynamic"})
    engine.evaluate(input_data={}, entrypoint="pkg/rule")

    assert engine.policy.data_calls == [
        {"source": "dynamic"},
        {"source": "bundle"},
    ]
    assert engine.policy.evaluate_calls[-1] == ({}, "pkg/rule")


def test_evaluate_omits_entrypoint_when_not_provided():
    engine = make_engine_with_entrypoints({"pkg/rule": 0})

    engine.evaluate(input_data={})

    assert engine.policy.evaluate_calls == [({}, None)]


def test_evaluate_normalizes_dynamic_entrypoint():
    entrypoints = {"mztabm/policies/policy_D_0010": 0}
    engine = make_engine_with_entrypoints(entrypoints)

    engine.evaluate(input_data={}, entrypoint="data.mztabm.policies.policy_D_0010")
    engine.evaluate(input_data={}, entrypoint="/mztabm/policies/policy_D_0010")
    engine.evaluate(input_data={}, entrypoint="policy_D_0010")
    engine.evaluate(input_data={}, entrypoint="mztabm/policies/policy_d_0010")

    assert engine.policy.evaluate_calls == [
        ({}, "mztabm/policies/policy_D_0010"),
        ({}, "mztabm/policies/policy_D_0010"),
        ({}, "mztabm/policies/policy_D_0010"),
        ({}, "mztabm/policies/policy_D_0010"),
    ]


def test_engine_exposes_compiled_entrypoints():
    engine = make_engine_with_entrypoints(
        {
            "mztabm/policies/policy_D_0010": 0,
            "mztabm/policies/policy_D_0020": 1,
        }
    )

    assert engine.list_entrypoints() == [
        "mztabm/policies/policy_D_0010",
        "mztabm/policies/policy_D_0020",
    ]
    assert engine.resolve_entrypoint("policy_d_0020") == "mztabm/policies/policy_D_0020"


def test_engine_exposes_bundle_data_values():
    engine = make_engine_with_entrypoints(
        {},
        bundle_data={
            "mztabm": {
                "policies": {
                    "policy_D_0010": {"enabled": True},
                    "constraint": {"entrypoint": "mztabm/policies/policy_D_0010"},
                }
            }
        },
    )

    assert engine.get_data("mztabm/policies/policy_D_0010") == {"enabled": True}
    assert engine.get_data("data.mztabm.policies.constraint.entrypoint") == (
        "mztabm/policies/policy_D_0010"
    )
    assert "mztabm/policies/policy_D_0010" in engine.list_data_paths()
    assert "mztabm/policies/constraint/entrypoint" in engine.list_data_paths()


def test_opa_entrypoint_can_be_supplied_at_runtime():
    constraint = OpaPolicyConstraint.model_validate({"type": "opa-policy"})
    runtime_config = ValidationRuntimeConfiguration(
        opa_policy_entrypoint="runtime/package/rule",
        opa_policy_entrypoints={"custom": "runtime/package/custom_rule"},
    )

    assert constraint.entrypoint is None
    assert runtime_config.opa_policy_entrypoint == "runtime/package/rule"
    assert runtime_config.opa_policy_entrypoints == {
        "custom": "runtime/package/custom_rule"
    }
