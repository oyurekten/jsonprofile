import abc
from collections.abc import Sequence
from decimal import Decimal
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import Field, field_validator

from jsonprofile.profile.base import (
    BaseCvTerm,
    ExtendedCvTerm,
    JsonPath,
    JsonProfileBaseModel,
)


class Precondition(JsonProfileBaseModel):
    """Condition that controls whether a constraint should be evaluated."""

    evaluations: Annotated[
        list["Evaluation"],
        Field(
            description="Evaluations that must be checked before the constraint runs.",
            min_length=1,
        ),
    ]
    join_operator: Annotated[
        Literal["and", "or"],
        Field(description="Boolean operator used to combine evaluations."),
    ] = "and"
    min_valid: Annotated[
        Optional[int],
        Field(
            description="Minimum number of evaluations that must be true.",
            ge=1,
        ),
    ] = None
    max_valid: Annotated[
        Optional[int],
        Field(description="Maximum number of evaluations that may be true."),
    ] = None


class Constraint(abc.ABC, JsonProfileBaseModel):
    """Base class for all validation constraints.

    Every concrete constraint has a ``type`` discriminator and may be
    assigned to a named validator implementation.
    """

    validator: Annotated[
        Optional[str],
        Field(
            description="Label of the validator that should evaluate this constraint. "
            "If omitted, the default validator is used."
        ),
    ] = None
    type: Annotated[
        str,
        Field(description="Unique discriminator identifying the constraint type."),
    ]
    name: Annotated[
        Optional[str],
        Field(description="Optional constraint name used to select a custom checker."),
    ] = None
    precondition: Annotated[
        None | Precondition,
        Field(
            description="Condition that must pass before this constraint is applied."
        ),
    ] = None
    json_path: Annotated[
        Optional[JsonPath],
        Field(
            description="Relative JSONPath used to select the value passed to this "
            "constraint. If omitted, the current value is used."
        ),
    ] = None

    default_precondition_evaluation: Annotated[
        Optional[bool],
        Field(
            description="Evaluation result to use "
            "when the precondition has not input to evaluate. "
            "If omitted, a no input precondition is treated as valid."
        ),
    ] = None
    negated: Annotated[
        Optional[bool],
        Field(
            description="Whether the constraint should be negated. If set to true, "
            "the constraint is inverted."
        ),
    ] = None
    null_values: Annotated[
        Optional[list[Optional[str]]],
        Field(description="Values that should be treated as null."),
    ] = None
    exceptional_values: Annotated[
        Optional[list[Union[None, str]]],
        Field(
            description="Values that bypass this constraint. If the input value is in "
            "this list, the constraint evaluates as valid."
        ),
    ] = None


class CollectionConstraint(Constraint):
    """Validates collection size and item matches against reference values."""

    type: Annotated[
        str,
        Field(description="Unique discriminator identifying the constraint type."),
    ] = "items-count"

    min_occurs: Annotated[
        Optional[int],
        Field(description="Minimum number of items allowed in the collection.", ge=0),
    ] = None
    max_occurs: Annotated[
        Optional[int],
        Field(description="Maximum number of items allowed in the collection.", ge=0),
    ] = None

    item_value_jsonpath_list: Annotated[
        Optional[list[str]],
        Field(
            description="Relative JSONPath expressions used to select values from each "
            "collection item before comparing against reference values. If omitted, "
            "the serialized collection item is compared."
        ),
    ] = None
    match_reference_values: Annotated[
        Optional[list[bool] | list[int] | list[str] | list[BaseCvTerm]],
        Field(description="Reference values to compare with collection item values."),
    ] = None
    min_match: Annotated[
        Optional[int],
        Field(description="Minimum number of matching items required.", ge=0),
    ] = None

    max_match: Annotated[
        Optional[int],
        Field(description="Maximum number of matching items allowed.", ge=0),
    ] = None

    min_referenced_value_match: Annotated[
        Optional[int],
        Field(
            description="Minimum number of reference values that must match at least "
            "one collection item.",
            ge=0,
        ),
    ] = None

    max_reference_value_match: Annotated[
        Optional[int],
        Field(
            description="Maximum number of reference values that may match collection "
            "items.",
            ge=0,
        ),
    ] = None


class NotNullConstraint(Constraint):
    """Validates that a value is not null or one of the configured null values."""

    type: Annotated[
        str,
        Field(description="Unique discriminator identifying the constraint type."),
    ] = "not-null"

    case_sensitive: Annotated[
        Optional[bool],
        Field(description="Whether the comparison should be case-sensitive."),
    ] = None
    exceptional_values: Annotated[
        Optional[list[Union[None, str]]],
        Field(
            frozen=True,
            description="Values that are accepted even when they would otherwise fail "
            "the not-null check.",
        ),
    ] = None


class RegexConstraint(Constraint):
    """Validates a string value against a regular expression pattern.

    Use for structured identifiers or format patterns that can be
    expressed as a single regex (e.g. ORCID, adduct ion notation).
    """

    type: Annotated[str, Field(description="Constraint type discriminator.")] = "regex"
    pattern: Annotated[
        str,
        Field(
            min_length=2,
            description="Regular expression pattern the value must fully match.",
        ),
    ]
    case_sensitive: Annotated[
        Optional[bool],
        Field(
            description="Whether the pattern match is case-sensitive. Defaults to True."
        ),
    ] = True


class StringConstraint(Constraint):
    """Validates that a string value's length falls within a range.

    At least one of ``minimum`` or ``maximum`` should be set.
    """

    type: Annotated[str, Field(description="Constraint type discriminator.")] = (
        "string-length"
    )
    minimum: Annotated[
        Optional[int],
        Field(
            description="Minimum number of characters (inclusive). "
            "None means no lower bound.",
            ge=0,
        ),
    ] = None
    maximum: Annotated[
        Optional[int],
        Field(
            description="Maximum number of characters (inclusive). "
            "None means no upper bound.",
            ge=0,
        ),
    ] = None


class StringEnumConstraint(Constraint):
    """Validates that a string value is one of a fixed set of allowed options.

    Options may be a simple list of strings or a mapping from a string key
    to a display value, integer code, or ``ExtendedCvTerm`` metadata.
    """

    type: Annotated[str, Field(description="Constraint type discriminator.")] = (
        "string-enum"
    )
    options: Annotated[
        list[str] | dict[str, Union[int, str, ExtendedCvTerm]],
        Field(
            description="Allowed string values, or a mapping from allowed values to "
            "display labels, integer codes, or CV term definitions."
        ),
    ]


class IntegerEnumConstraint(Constraint):
    """Validates that an integer value is one of a fixed set of allowed options.

    Each option maps an integer value to a display value, integer code,
    or ``ExtendedCvTerm`` metadata.
    """

    type: Annotated[str, Field(description="Constraint type discriminator.")] = (
        "integer-enum"
    )
    options: Annotated[
        dict[int, Union[int, str, ExtendedCvTerm]],
        Field(
            description="Mapping from allowed integer values to display labels, "
            "integer codes, or CV term definitions."
        ),
    ]


class IntegerConstraint(Constraint):
    """Validates that a value is a valid integer within an optional range.

    Use ``PositiveIntegerConstraint`` or ``NonNegativeIntegerConstraint``
    for common presets.
    """

    type: Annotated[str, Field(description="Constraint type discriminator.")] = (
        "integer"
    )
    minimum: Annotated[
        Optional[int],
        Field(
            description="Minimum allowed value (inclusive). None means no lower bound."
        ),
    ] = None
    maximum: Annotated[
        Optional[int],
        Field(
            description="Maximum allowed value (inclusive). None means no upper bound."
        ),
    ] = None


class PositiveIntegerConstraint(IntegerConstraint):
    """Validates that a value is a positive integer (>= 1).

    Convenience subclass of ``IntegerConstraint`` with ``minimum=1``.
    """

    type: Annotated[str, Field(description="Constraint type discriminator.")] = (
        "positive-integer"
    )
    minimum: Annotated[
        Optional[int],
        Field(description="Minimum allowed value (inclusive). Defaults to 1."),
    ] = 1


class NonNegativeIntegerConstraint(IntegerConstraint):
    """Validates that a value is a non-negative integer (>= 0).

    Convenience subclass of ``IntegerConstraint`` with ``minimum=0``.
    """

    type: Annotated[str, Field(description="Constraint type discriminator.")] = (
        "non-negative-integer"
    )
    minimum: Annotated[
        Optional[int],
        Field(description="Minimum allowed value (inclusive). Defaults to 0."),
    ] = 0


class BooleanConstraint(Constraint):
    """Validates that a value is boolean."""

    type: Annotated[str, Field(description="Constraint type discriminator.")] = (
        "boolean"
    )

    exceptional_false_values: Annotated[
        Optional[list[Optional[str]]],
        Field(
            description="String values that should be interpreted as false, such as "
            "'0' or 'no'. Values should be lowercase."
        ),
    ] = None
    exceptional_true_values: Annotated[
        Optional[list[Optional[str]]],
        Field(
            description="String values that should be interpreted as true, such as "
            "'1' or 'yes'. Values should be lowercase."
        ),
    ] = None


class DecimalConstraint(Constraint):
    """Validates that a value is a valid floating-point number.

    Supports optional range bounds, scientific notation control,
    and decimal precision limits.
    """

    type: Annotated[str, Field(description="Constraint type discriminator.")] = (
        "decimal"
    )
    minimum: Annotated[
        Optional[Decimal],
        Field(
            description="Minimum allowed value (inclusive). None means no lower bound."
        ),
    ] = None
    maximum: Annotated[
        Optional[Decimal],
        Field(
            description="Maximum allowed value (inclusive). None means no upper bound."
        ),
    ] = None
    allow_scientific_notation: Annotated[
        Optional[bool],
        Field(
            description="Whether scientific notation (e.g. '1.23e4') is "
            "accepted. None means no restriction."
        ),
    ] = None
    min_scale: Annotated[
        Optional[int],
        Field(
            description="Minimum number of digits after the decimal point. "
            "None means no minimum scale requirement.",
            ge=0,
        ),
    ] = None
    max_scale: Annotated[
        Optional[int],
        Field(
            description="Maximum number of digits after the decimal point. "
            "None means no maximum scale limit.",
            ge=0,
        ),
    ] = None
    allow_non_finite_values: Annotated[
        Optional[bool],
        Field(description="Whether NaN and positive or negative infinity are allowed."),
    ] = None


class DateTimeConstraint(Constraint):
    """Validates that a string value represents a valid date, time,
    or datetime.

    When ``format`` is provided, the value must match that specific
    pattern (e.g. ISO-8601). When omitted, ISO-8601 is accepted.
    """

    type: Annotated[str, Field(description="Constraint type discriminator.")] = "time"
    format: Annotated[
        Optional[str],
        Field(
            description="Expected time/date format string "
            "(e.g. '%Y-%m-%d', '%Y-%m-%dT%H:%M:%SZ', '%H:%M:%S'). "
            "If omitted, ISO-8601 date, time, or datetime values are accepted."
        ),
    ] = None


class EmailConstraint(Constraint):
    """Validates that a string value is a well-formed email address."""

    type: Annotated[str, Field(description="Constraint type discriminator.")] = "email"


class UriConstraint(Constraint):
    """Validates that a string value is a well-formed URI.

    Optionally restricts accepted URI schemes (e.g. only ``https``,
    ``ftp``).
    """

    type: Annotated[str, Field(description="Constraint type discriminator.")] = "uri"
    allowed_schemes: Annotated[
        Optional[list[str]],
        Field(
            description="List of accepted URI schemes "
            "(e.g. ['http', 'https', 'ftp']). "
            "None means any scheme is accepted."
        ),
    ] = None


class BaseCvTermConstraint(Constraint):
    """Base class for constraints that validate controlled vocabulary terms."""

    type: Annotated[
        str,
        Field(description="Unique discriminator identifying the constraint type."),
    ]
    exceptional_values: Annotated[
        Optional[list[Union[None, BaseCvTerm]]],
        Field(description="CV terms that bypass this constraint."),
    ] = None

    null_values: Annotated[
        Optional[list[Optional[str]]],
        Field(description="String values that should be treated as null CV terms."),
    ] = None


class CVTermConstraint(BaseCvTermConstraint):
    """Base constraint for values that must be controlled vocabulary terms.

    Subclasses refine which CV terms are acceptable (by list, by parent
    term, or by CV namespace). This class captures the common options
    shared across all CV term constraints.
    """

    type: Annotated[str, Field(description="Constraint type discriminator.")] = (
        "cv-term"
    )
    allow_user_defined_terms: Annotated[
        Optional[bool],
        Field(
            description="Whether user-defined terms (empty cv_label and cv_accession) "
            "are accepted alongside CV terms."
        ),
    ] = None
    is_cv_term_value_required: Annotated[
        Optional[bool],
        Field(
            description="Whether the CV term's value slot must be populated. "
            "When True, value MUST not be empty or null."
        ),
    ] = None


class CVListConstraint(CVTermConstraint):
    """Restricts CV terms to those from specific controlled vocabularies.

    The ``allowed_cv_list`` field specifies which CV namespace labels are
    allowed (e.g. ``['MS', 'UO']``).
    """

    type: Annotated[
        str,
        Field(description="Constraint type discriminator."),
    ] = "allowed-cv-list"
    allowed_cv_list: Annotated[
        Optional[list[str]],
        Field(
            min_length=1,
            description="List of allowed CV namespace labels "
            "(e.g. ['MS', 'UO', 'PRIDE']). Use only uppercase letters. "
            "None means any CV namespace is accepted.",
        ),
    ] = None
    allow_user_defined_terms: Annotated[
        Optional[bool],
        Field(
            description="Whether user-defined terms (empty cv_label and cv_accession) "
            "are accepted alongside CV terms."
        ),
    ] = False

    @field_validator("allowed_cv_list", check_fields=False)
    @classmethod
    def cv_list_validation(cls, value):
        if not value:
            return None
        if isinstance(value, str):
            return [value.upper()]
        if isinstance(value, Sequence):
            return [str(x).upper() for x in value]
        return value


class CVTermEnumConstraint(CVTermConstraint):
    """Restricts the value to a specific set of CV terms.

    Unlike ``CVListConstraint`` which filters by CV namespace, this
    constraint enumerates the exact terms that are acceptable.
    """

    type: Annotated[str, Field(description="Constraint type discriminator.")] = (
        "cv-term-enum"
    )
    allowed_cv_terms: Annotated[
        list[BaseCvTerm],
        Field(
            min_length=1,
            description="Explicit list of allowed CV terms. "
            "Each entry identifies a term by label, accession, or name.",
        ),
    ]

    exceptional_cv_list: Annotated[
        Optional[list[str]],
        Field(description="CV namespace labels that bypass this enum constraint."),
    ] = None


class ParentCVTermConstraint(CVTermConstraint):
    """Restricts the value to CV terms that are descendants of
    specified parent terms in the ontology hierarchy.

    Supports exclusion of specific terms or name patterns to
    filter out unwanted branches of the ontology tree.
    """

    type: Annotated[str, Field(description="Constraint type discriminator.")] = (
        "parent-cv-term"
    )
    parent_cv_terms: Annotated[
        Optional[list[BaseCvTerm]],
        Field(
            min_length=1,
            description="List of parent CV terms. Valid values must be "
            "descendants of at least one of these terms.",
        ),
    ] = None
    excluded_cv_terms: Annotated[
        Optional[list[BaseCvTerm]],
        Field(
            description="CV terms to exclude even if they are descendants "
            "of a parent term."
        ),
    ] = None


class CVTermValueConstraint(Constraint):
    """Validates the value slot of a specific CV term.

    When a field contains a CV term matching ``key_cv_term``, its
    value is validated against the nested ``value_constraint``.
    This enables context-dependent validation (e.g. a numeric range
    that only applies when a specific CV term is used).
    """

    type: Annotated[str, Field(description="Constraint type discriminator.")] = (
        "cv-term-value"
    )
    key_cv_term: Annotated[
        Optional[BaseCvTerm],
        Field(
            description="The CV term whose value slot should be validated. "
            "When the field contains this term, the value_constraint is applied."
        ),
    ]
    value_constraint: Annotated[
        Optional["DefaultConstraintType"],
        Field(
            description="Constraint applied to the value slot of the "
            "matched CV term. Determines the expected type and format."
        ),
    ]


class OpaPolicyConstraint(Constraint):
    """Evaluates an Open Policy Agent policy against the input value."""

    type: Annotated[str, Field(description="Constraint type discriminator.")] = (
        "opa-policy"
    )
    wasm_file_key: Annotated[
        Optional[str],
        Field(
            description="OPA policy WASM file key defined in profile configuration. "
            "If omitted, the default policy file is used."
        ),
    ] = None
    policy_id: Annotated[
        str,
        Field(description="OPA policy id. policy_0001, policy_d_01010, etc."),
    ]


class CustomConstraint(Constraint):
    """Runs a named custom constraint checker."""

    type: Annotated[str, Field(description="Constraint type discriminator.")] = "custom"

    name: Annotated[
        str,
        Field(description="Name used to resolve the custom constraint checker."),
    ]

    default_arguments: Annotated[
        Optional[dict[str, Any]],
        Field(description="Default arguments passed to the custom constraint checker."),
    ] = None
    value_jsonpath_arguments: Annotated[
        Optional[dict[str, str]],
        Field(
            description="Mapping from argument names to relative JSONPath expressions "
            "resolved against the current value."
        ),
    ] = None
    root_jsonpath_arguments: Annotated[
        Optional[dict[str, str]],
        Field(
            description="Mapping from argument names to JSONPath expressions resolved "
            "against the root JSON document."
        ),
    ] = None


class ConstraintGroup(Constraint):
    """Combines multiple constraints using boolean or valid-count logic."""

    type: Annotated[str, Field(description="Constraint type discriminator.")] = "group"
    constraints: Annotated[
        list["DefaultConstraintType"],
        Field(
            min_length=1,
            description="Constraints that belong to this group.",
        ),
    ]
    join_operator: Annotated[
        Literal["and", "or"],
        Field(description="Boolean operator used to combine constraints."),
    ] = "and"
    min_valid: Annotated[
        Optional[int],
        Field(
            description="Minimum number of constraints that must be valid for the "
            "group to be valid.",
            ge=1,
        ),
    ] = None
    max_valid: Annotated[
        Optional[int],
        Field(
            description="Maximum number of constraints that may be valid for the "
            "group to be valid."
        ),
    ] = None


DefaultConstraintType = Annotated[
    Union[
        BooleanConstraint,
        CollectionConstraint,
        ConstraintGroup,
        CVListConstraint,
        CVTermConstraint,
        CVTermEnumConstraint,
        CustomConstraint,
        DateTimeConstraint,
        DecimalConstraint,
        EmailConstraint,
        IntegerConstraint,
        IntegerEnumConstraint,
        NonNegativeIntegerConstraint,
        NotNullConstraint,
        OpaPolicyConstraint,
        ParentCVTermConstraint,
        PositiveIntegerConstraint,
        RegexConstraint,
        StringEnumConstraint,
        StringConstraint,
        UriConstraint,
    ],
    Field(description="Supported constraint definition for a profiled field."),
]


class Evaluation(JsonProfileBaseModel):
    """Evaluates a constraint against either the current value or another JSONPath."""

    root_value_evaluation: Annotated[
        Optional[bool],
        Field(
            description="Whether the evaluation JSONPath should be resolved from the "
            "root JSON document instead of the current value."
        ),
    ] = None
    json_path: Annotated[
        Optional[JsonPath],
        Field(
            description="JSONPath used to select the value for this evaluation. If "
            "omitted, either the root document or current value is used depending on "
            "root_value_evaluation."
        ),
    ] = None
    constraint: Annotated[
        DefaultConstraintType,
        Field(description="Constraint applied during this evaluation."),
    ]
    default_evaluation: Annotated[
        Optional[bool],
        Field(
            description="Evaluation result to use when the JSONPath query returns no "
            "value. If omitted, missing values are treated as valid."
        ),
    ] = None
    join_operator: Annotated[
        Literal["and", "or"],
        Field(
            description="Boolean operator used when this evaluation has sub-results."
        ),
    ] = "and"
    min_valid: Annotated[
        Optional[int],
        Field(
            description="Minimum number of sub-results that must be valid.",
            ge=1,
        ),
    ] = None
    max_valid: Annotated[
        Optional[int],
        Field(description="Maximum number of sub-results that may be valid."),
    ] = None


DEFAULT_CONSTRAINTS: list[type[Constraint]] = [
    BooleanConstraint,
    CollectionConstraint,
    ConstraintGroup,
    CVListConstraint,
    CVTermConstraint,
    CVTermEnumConstraint,
    CustomConstraint,
    DateTimeConstraint,
    DecimalConstraint,
    EmailConstraint,
    IntegerConstraint,
    IntegerEnumConstraint,
    NonNegativeIntegerConstraint,
    NotNullConstraint,
    OpaPolicyConstraint,
    ParentCVTermConstraint,
    PositiveIntegerConstraint,
    RegexConstraint,
    StringEnumConstraint,
    StringConstraint,
    UriConstraint,
]
DEFAULT_CONSTRAINTS_MAP: dict[str, Constraint] = {
    x.model_fields.get("type").default: x for x in DEFAULT_CONSTRAINTS
}
