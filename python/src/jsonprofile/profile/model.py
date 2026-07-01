import json
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any, Optional, Union

from pydantic import Field, field_validator

from jsonprofile.profile.base import (
    EnforcementLevel,
    JsonPath,
    JsonProfileBaseModel,
)
from jsonprofile.profile.constraints.constraints import (
    DEFAULT_CONSTRAINTS_MAP,
    Constraint,
    ConstraintGroup,
    CVTermValueConstraint,
    DefaultConstraintType,
)


class EnforcedRequirement(JsonProfileBaseModel):
    """Common metadata for a profile requirement."""

    code: Annotated[
        Optional[str],
        Field(
            description="Stable requirement identifier. "
            "Use a unique code for each requirement so validation messages can "
            "be referenced and skipped reliably."
        ),
    ] = None
    description: Annotated[
        Optional[str],
        Field(description="Human-readable explanation of the requirement."),
    ] = None
    enforcement_level: Annotated[
        Optional[EnforcementLevel],
        Field(description="Severity applied when the requirement is not satisfied."),
    ] = EnforcementLevel.REQUIRED


class FieldRequirement(EnforcedRequirement):
    """Validation rules that apply to one profiled JSON field."""

    value_constraint: Annotated[
        Optional[DefaultConstraintType],
        Field(description="Constraint that validates the field value."),
    ] = None
    match_is_required: Annotated[
        Optional[bool],
        Field(
            description="Whether the target JSONPath must match at least one value. "
            "Field must be defined and value can be null, string, object, etc."
        ),
    ] = None
    required_properties: Annotated[
        Optional[list[str]],
        Field(
            description="Object properties that must be present when the field value "
            "is an object."
        ),
    ] = None
    recommended_properties: Annotated[
        Optional[list[str]],
        Field(
            description="Object properties that should be present when the field value "
            "is an object."
        ),
    ] = None

    @field_validator("value_constraint", mode="before")
    @classmethod
    def populate_value_constraint(cls, value):
        return _populate_constraint_from_name(value)


class FieldRequirementGroup(EnforcedRequirement):
    """Group of requirements combined by valid-count bounds."""

    requirements: Annotated[
        list[Union[FieldRequirement, "FieldRequirementGroup"]],
        Field(
            min_length=1,
            description="Requirements that belong to this group.",
        ),
    ]
    min_valid: Annotated[
        Optional[int],
        Field(
            description="Minimum number of requirements that must be valid "
            "for the group to be true.",
            ge=1,
        ),
    ] = None
    max_valid: Annotated[
        Optional[int],
        Field(
            description="Maximum number of requirements that can be valid "
            "for the group to be true."
        ),
    ] = None


class ProfileValidatorDefinition(JsonProfileBaseModel):
    """Definition of a profile validator implementation."""

    label: Annotated[
        str,
        Field(
            description="Profile validator label used to reference this validator "
            "from profiles and constraints."
        ),
    ]
    validator_id: Annotated[
        str,
        Field(description="Unique identifier of the profile validator."),
    ]
    profile_validator_class: Annotated[
        dict[str, str],
        Field(
            description="Mapping from runtime or language name to the fully qualified "
            "validator class name."
        ),
    ]
    description: Annotated[
        Optional[str],
        Field(
            description="Human-readable description of the custom validator.",
        ),
    ] = None


class WasmFileDefinition(JsonProfileBaseModel):
    """Configuration for an Open Policy Agent policy module."""

    wasm_file_download_url: Annotated[
        str,
        Field(
            description="URL used to download the policy WASM file when it is not "
            "available locally."
        ),
    ]
    wasm_file_path: Annotated[
        str,
        Field(
            description="Local path to the WASM file that implements the OPA policy."
        ),
    ]


class JsonProfileConfiguration(JsonProfileBaseModel):
    """Optional configuration shared by validators for a profile."""

    supported_cv_lists: Annotated[
        Optional[list[str]],
        Field(description="Controlled vocabulary lists supported by this profile."),
    ] = None
    supported_cv_list_enforcement_level: Annotated[
        Optional[EnforcementLevel],
        Field(
            description="Enforcement level used when a value references an unsupported "
            "controlled vocabulary list."
        ),
    ] = None

    custom_validator_definitions: Annotated[
        Optional[list[ProfileValidatorDefinition]],
        Field(description="Custom profile validators available to this profile."),
    ] = None
    default_validator_key: Annotated[
        Optional[str],
        Field(
            description="Key of the validator used by default. If omitted, only the "
            "built-in JSON Schema validator is used."
        ),
    ] = None

    profile_validator_factory_class: Annotated[
        Optional[dict[str, str]],
        Field(
            description="Fully qualified profile validator factory classes "
            "for each scheme or programming language. e.g., python, java, etc. "
            "If omitted, the default factory is used."
        ),
    ] = None
    profile_validator_factory_class_arguments: Annotated[
        Optional[dict[str, Any]],
        Field(description="Keyword arguments passed to the profile validator factory."),
    ] = None
    default_wasm_file_key: Annotated[
        Optional[str],
        Field(
            description="Label of the wasm file used by default."
            " WASM file with 'default' label will be used."
        ),
    ] = None
    wasm_file_definitions: Annotated[
        Optional[dict[str, WasmFileDefinition]],
        Field(
            description="Named OPA policy WASM file label and definitions "
            "available to constraints."
        ),
    ] = None


class ValidationRuntimeConfiguration(JsonProfileBaseModel):
    """Options that alter validation behavior for one validation run."""

    offline_mode: Annotated[
        None | bool,
        Field(description="Skip validations and checks that require network access."),
    ] = None

    skipped_requirements: Annotated[
        None | list[str],
        Field(
            description="Requirement codes that should be skipped during validation."
        ),
    ] = None

    max_messages_for_each_requirement: Annotated[
        None | int,
        Field(
            description="Maximum number of validation messages emitted for each "
            "requirement."
        ),
    ] = 10

    skip_decimal_validations: Annotated[
        None | bool,
        Field(description="Skip decimal value constraints."),
    ] = None

    cv_term_search_class: Annotated[
        None | str,
        Field(
            description="Selected CV term search implementation class. "
            "If it is not defined, default implementation will be used. "
            "If you want to skip online searches, use `offline_mode`"
        ),
    ] = None


class JsonProfile(JsonProfileBaseModel):
    """A JSON profile containing metadata, configuration, and field requirements."""

    id: Annotated[
        str,
        Field(
            description="Unique profile identifier. Define different for each version"
        ),
    ]
    extends: Annotated[
        Optional[str],
        Field(
            description="Profile id that will be extended."
            "If it is not defined, only this profile will be used."
        ),
    ] = None
    version: Annotated[str, Field(description="Human readable profile version.")]
    name: Annotated[str, Field(description="Human-readable profile name.")]
    description: Annotated[
        Optional[str],
        Field(description="Human-readable profile description."),
    ] = None
    configuration: Annotated[
        Optional[JsonProfileConfiguration],
        Field(description="Validator configuration for the profile."),
    ] = None
    requirements: Annotated[
        Optional[dict[JsonPath, None | FieldRequirementGroup | FieldRequirement]],
        Field(
            description="Mapping from JSONPath expressions to the requirements that "
            "apply to matching values."
        ),
    ] = None

    @field_validator("requirements", mode="before")
    @classmethod
    def validate_requirements(cls, value):
        if value is None or not isinstance(value, dict):
            return value

        return {k: cls.create_requirement(v) for k, v in value.items()}

    def create_requirement(value: Any) -> FieldRequirementGroup | FieldRequirement:
        if (
            value is None
            or isinstance(value, FieldRequirement)
            or isinstance(value, FieldRequirementGroup)
            or not isinstance(value, dict)
        ):
            return value

        if "requirements" in value:
            return FieldRequirementGroup.model_validate(value, by_alias=True)
        else:
            return FieldRequirement.model_validate(value, by_alias=True)


def _populate_constraint_from_name(value):
    if value is None or isinstance(value, Constraint):
        return value
    if not isinstance(value, dict):
        return value

    constraint_type = value.get("type")
    if not constraint_type:
        return value

    constraint_class = DEFAULT_CONSTRAINTS_MAP.get(constraint_type)
    if not constraint_class:
        raise ValueError(f"Unknown value constraint type: {constraint_type}")

    constraint_data = dict(value)
    precondition = constraint_data.get("precondition")
    if precondition and isinstance(precondition, Mapping):
        evaluations = precondition.get("evaluations")
        if evaluations and isinstance(evaluations, list):
            for evaluation in precondition.get("evaluations", []):
                if isinstance(evaluation, Mapping) and evaluation.get("constraint"):
                    constraint = evaluation["constraint"]
                    evaluation["constraint"] = _populate_constraint_from_name(
                        constraint
                    )

    if constraint_class == ConstraintGroup:
        constraint_data["constraints"] = [
            _populate_constraint_from_name(constraint)
            for constraint in constraint_data.get("constraints", [])
        ]
    elif constraint_class == CVTermValueConstraint:
        value_constraint = constraint_data.get("value_constraint")
        if value_constraint and isinstance(value_constraint, Mapping):
            constraint_data["value_constraint"] = _populate_constraint_from_name(
                value_constraint
            )

    return constraint_class.model_validate(constraint_data)


if __name__ == "__main__":
    with Path("../shared/schema/jsonprofile.schema.json").open(
        "w", encoding="utf-8"
    ) as f:
        json.dump(JsonProfile.model_json_schema(), f, indent=2)
