import enum
from enum import Enum
from typing import Annotated, Any, Mapping, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ModelWrapValidatorHandler,
    ValidationInfo,
    model_validator,
)
from pydantic.alias_generators import to_pascal

from jsonprofile.utils import sanitize_str

JsonPath = Annotated[
    str,
    Field(description="JSONPath expression used to select values in a JSON document."),
]


class Category(str, enum.Enum):
    """High-level category for validation messages."""

    PARSE = "parse"
    FORMAT = "format"
    CROSS_CHECK = "cross_check"
    PROFILE = "profile"
    SCHEMA = "schema"


class JsonProfileBaseModel(BaseModel):
    """Base model configuration shared by JSON Profile schemas."""

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_default=True,
        validate_assignment=True,
        validation_error_cause=True,
        field_title_generator=lambda field_name, field_info: to_pascal(
            field_name.replace("_", " ").strip()
        ),
    )


class EnforcementLevel(str, Enum):
    """How strongly a profile requirement is enforced."""

    NOT_DEFINED = "not-defined"
    OPTIONAL = "optional"
    RECOMMENDED = "recommended"
    REQUIRED = "required"


class JsonProfileMessage(JsonProfileBaseModel):
    """Message emitted while validating a profile or JSON document."""

    code: Annotated[
        str,
        Field(
            description="Requirement or validation code associated with the message."
        ),
    ] = ""
    source: Annotated[
        Optional[str],
        Field(description="Source file, JSONPath, or resource related to the message."),
    ] = None
    category: Annotated[
        Category | str,
        Field(description="Validation category that produced the message."),
    ]
    name: Annotated[
        Optional[str],
        Field(description="Source file, JSONPath, or resource related to the message."),
    ] = None
    message: Annotated[
        str,
        Field(description="Human-readable validation message."),
    ]
    enforcement_level: Annotated[
        Optional[EnforcementLevel],
        Field(description="Severity applied when the requirement is not satisfied."),
    ] = EnforcementLevel.REQUIRED


class BaseCvTerm(JsonProfileBaseModel):
    """A lightweight reference to a controlled vocabulary (CV) term.

    Used within constraint definitions to identify specific CV terms
    by their label, accession, or human-readable name.
    """

    cv_label: Annotated[
        Optional[str],
        Field(
            description="Short identifier of the controlled vocabulary "
            "(e.g. 'MS' for PSI-MS, 'UO' for Unit Ontology)."
        ),
    ] = ""
    cv_accession: Annotated[
        Optional[str],
        Field(description="Accession of the term in CURIE format (e.g. 'MS:1000073')."),
    ] = ""
    name: Annotated[
        Optional[str],
        Field(
            description="Human-readable name of the parameter term "
            "(e.g. 'electrospray ionization')."
        ),
    ] = ""

    def __str__(self):
        return (
            f"[{sanitize_str(self.cv_label)}, "
            f"{sanitize_str(self.cv_accession)}, "
            f"{sanitize_str(self.name)}, "
        )


class CvTerm(JsonProfileBaseModel):
    """Controlled vocabulary term with an optional user-provided value."""

    cv_label: Annotated[
        Optional[str],
        Field(
            description="Short identifier of the controlled vocabulary "
            "(e.g. 'MS' for PSI-MS, 'UO' for Unit Ontology)."
        ),
    ] = ""
    cv_accession: Annotated[
        Optional[str],
        Field(description="Accession of the term in CURIE format (e.g. 'MS:1000073')."),
    ] = ""
    name: Annotated[
        Optional[str],
        Field(description="Human-readable name of the controlled vocabulary term."),
    ] = ""
    value: Annotated[
        Optional[str],
        Field(description="User-provided value associated with the term."),
    ] = ""

    def __str__(self):
        return (
            f"[{sanitize_str(self.cv_label)}, "
            f"{sanitize_str(self.cv_accession)}, "
            f"{sanitize_str(self.name)}, "
            f"{sanitize_str(self.value)}]"
        )

    @model_validator(mode="wrap")
    @classmethod
    def validate_model(
        cls,
        data: Any,
        handler: ModelWrapValidatorHandler["CvTerm"],
        info: ValidationInfo,
    ) -> "CvTerm":
        if not data:
            return None
        if isinstance(data, CvTerm):
            return handler(data)
        val = data
        if isinstance(val, Mapping):
            if len(val) == 1 and None in val:
                val = data[None]
        if isinstance(val, str):
            cleaned = val.strip("[]")
            parts = cleaned.split(",", maxsplit=3)

            cv_label = parts[0].strip() if len(parts) > 0 else ""
            cv_accession = parts[1].strip() if len(parts) > 1 else ""
            name = parts[2].strip() if len(parts) > 2 else ""
            value = parts[3].strip() if len(parts) > 3 else ""

            val = {
                "cv_label": cv_label,
                "cv_accession": cv_accession,
                "name": name,
                "value": value,
            }
        return handler(val)


class ExtendedCvTerm(CvTerm):
    """Controlled vocabulary term whose value may be another CV term."""

    value: Annotated[
        Optional[str | CvTerm],
        Field(
            description="User-provided value associated with the term. The value may "
            "itself be represented as a controlled vocabulary term."
        ),
    ] = None

    @model_validator(mode="wrap")
    @classmethod
    def validate_model(
        cls,
        data: Any,
        handler: ModelWrapValidatorHandler["ExtendedCvTerm"],
        info: ValidationInfo,
    ) -> "ExtendedCvTerm":
        if not data:
            return None
        if isinstance(data, ExtendedCvTerm):
            return handler(data)

        val = data
        if isinstance(val, Mapping):
            if len(val) == 1 and None in val:
                val = data[None]
        if isinstance(val, dict):
            value_str: str = val.get("value", "")
            value_str = value_str.strip('"')
            if value_str.startswith("["):
                value = CvTerm.model_validate(value_str.strip("[]"))
                val["value"] = value.model_dump(by_alias=True)
        elif isinstance(val, str):
            cleaned = val.strip("[]")
            parts = cleaned.split(",", maxsplit=3)

            cv_label = parts[0].strip() if len(parts) > 0 else ""
            cv_accession = parts[1].strip() if len(parts) > 1 else ""
            name = parts[2].strip() if len(parts) > 2 else ""
            value = ""
            if len(parts) > 3:
                value_str = parts[3].strip('"').strip()
                value = value_str
                if value_str.startswith("["):
                    value = CvTerm.model_validate(value_str.strip("[]"))

            val = {
                "cv_label": cv_label,
                "cv_accession": cv_accession,
                "name": name,
                "value": value.strip('"'),
            }
        return handler(val)
