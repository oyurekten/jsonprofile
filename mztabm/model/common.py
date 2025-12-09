from typing import (
    Annotated,
    Any,
    List,
    Literal,
    Optional,
    OrderedDict,
    Self,
    Union,
)

from pydantic import (
    AnyUrl,
    Field,
    ModelWrapValidatorHandler,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    ValidationInfo,
    model_serializer,
    model_validator,
)

from mztabm.model import CustomSerializer, IdentifiableModel, MzTabBaseModel
from mztabm.model.field_utils import sanitize_str
from mztabm.model.serialization import MetadataSerialization
from mztabm.model.validation import ValidationSummary

AdductIon = Annotated[str, Field(pattern=r"^\[\d*M([+-][\w\d]+)*\]\d*[+-]$")]


class Parameter(IdentifiableModel, CustomSerializer):
    cv_label: Optional[str] = ""
    cv_accession: Optional[str] = ""
    name: Optional[str] = None
    value: Optional[str] = None

    @model_serializer(mode="wrap")
    def serialize_model(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> str | dict[str, Any]:
        default_success, result = self.serialize_to_json(handler, info)
        if default_success:
            return result

        return (
            f"[{sanitize_str(self.cv_label)}, "
            f"{sanitize_str(self.cv_accession)}, "
            f"{sanitize_str(self.name)}, "
            f"{sanitize_str(self.value)}]"
        )

    @model_validator(mode="wrap")
    @classmethod
    def validate_model(
        cls, data: Any, handler: ModelWrapValidatorHandler[Self], info: ValidationInfo
    ) -> Self:
        if not data:
            return None
        if isinstance(data, Parameter):
            return handler(data)
        if isinstance(info.context, ValidationSummary):
            if info.context.source_format == "json":
                return handler(data)
        val = data
        if isinstance(val, (dict, OrderedDict)):
            if len(val) == 1 and None in val:
                val = data[None]
        if isinstance(val, str):
            cleaned = val.strip("[]")
            parts = cleaned.split(",", maxsplit=3)

            if len(parts) < 4:
                return None

            val = {
                "cv_label": parts[0].strip() or None,
                "cv_accession": parts[1].strip() or None,
                "name": parts[2].strip() or None,
                "value": parts[3].strip() or None,
            }
        return handler(val)


class Instrument(IdentifiableModel):
    name: Annotated[
        Optional[Parameter],
        Field(
            description="The instrument's name.",
        ),
    ] = None
    source: Annotated[
        Optional[Parameter],
        Field(
            description="The instrument's ion source.",
        ),
    ] = None
    analyzer: Annotated[
        Optional[List[Parameter]],
        Field(
            description="The instrument's mass analyzer, as defined by the parameter.",
        ),
    ] = None
    detector: Annotated[
        Optional[Parameter],
        Field(
            description="The instrument's mass analyzer, as defined by the parameter.",
        ),
    ] = None


class SampleProcessing(IdentifiableModel):
    sample_processing: Annotated[
        Optional[List[Parameter]],
        Field(
            alias="sampleProcessing",
            description="Parameters specifiying sample processing "
            "that was applied within one step.",
            json_schema_extra=MetadataSerialization(
                list_concatenation_str="|", object_level_value=True
            ).model_dump(exclude_unset=True, exclude_defaults=True),
        ),
    ] = None


class Software(IdentifiableModel):
    parameter: Annotated[
        Optional[Parameter],
        Field(
            json_schema_extra=MetadataSerialization(
                object_level_value=True,
            ).model_dump(exclude_unset=True, exclude_defaults=True),
        ),
    ] = None
    setting: Annotated[
        Optional[List[str]],
        Field(
            description="A software setting used. "
            "This field MAY occur multiple times for a single software. "
            "The value of this field is deliberately set as a String, "
            "since there currently do not exist cvParams for every possible setting.",
        ),
    ] = None


class PublicationItem(MzTabBaseModel, CustomSerializer):
    type: Annotated[
        Literal["doi", "pubmed", "uri"],
        Field(description="The type qualifier of this publication item."),
    ]
    accession: Annotated[
        str, Field(description="The native accession id for this publication item.")
    ]

    @model_serializer(mode="wrap")
    def serialize_model(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> str | dict[str, Any]:
        default_success, result = self.serialize_to_json(handler, info)
        if default_success:
            return result
        return f"{sanitize_str(self.type)}:{sanitize_str(self.accession)}"

    @model_validator(mode="wrap")
    @classmethod
    def deserialize(
        cls, data: Any, handler: ModelWrapValidatorHandler[Self], info: ValidationInfo
    ) -> Self:
        if isinstance(data, PublicationItem):
            return handler(data)
        if isinstance(info.context, ValidationSummary):
            if info.context.source_format == "json":
                return handler(data)
        val = data
        if isinstance(data, (OrderedDict, dict)):
            if len(data) == 1 and None in data:
                val = data[None]
        if isinstance(val, str) and ":" in val:
            parts = val.split(":", maxsplit=1)
            val = {"type": parts[0], "accession": parts[1]}
        return handler(val)


class Contact(IdentifiableModel):
    name: Annotated[
        Optional[str],
        Field(
            description="The contact's name.",
        ),
    ] = None
    affiliation: Annotated[
        Optional[str],
        Field(
            description="The contact's affiliation.",
        ),
    ] = None
    email: Annotated[
        Optional[str],
        Field(
            description="The contact's e-mail address.",
            pattern=r"^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$",
        ),
    ] = None
    orcid: Annotated[
        Optional[str],
        Field(
            description="The contact's orcid id, without https prefix.",
            pattern=r"^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]{1}$",
        ),
    ] = None


class Uri(IdentifiableModel):
    value: Annotated[
        Optional[AnyUrl],
        Field(
            description="The URI pointing to the external resource.",
            json_schema_extra=MetadataSerialization(object_level_value=True).model_dump(
                exclude_unset=True, exclude_defaults=True
            ),
        ),
    ] = None


class Sample(IdentifiableModel):
    name: Annotated[
        Optional[str],
        Field(
            description="The sample's name.",
            json_schema_extra=MetadataSerialization(object_level_value=True).model_dump(
                exclude_unset=True, exclude_defaults=True
            ),
        ),
    ] = None
    custom: Annotated[
        Optional[List[Parameter]],
        Field(
            description="Additional user or cv parameters.",
        ),
    ] = None
    species: Annotated[
        Optional[List[Parameter]],
        Field(
            description="Biological species information on the sample.",
        ),
    ] = None
    tissue: Annotated[
        Optional[List[Parameter]],
        Field(
            description="Biological tissue information on the sample.",
        ),
    ] = None
    cell_type: Annotated[
        Optional[List[Parameter]],
        Field(
            description="Biological cell type information on the sample.",
        ),
    ] = None
    disease: Annotated[
        Optional[List[Parameter]],
        Field(
            description="Disease information on the sample.",
        ),
    ] = None
    description: Annotated[
        Optional[str],
        Field(
            description="A free form description of the sample.",
        ),
    ] = None


class MsRun(IdentifiableModel):
    name: Annotated[
        Optional[str],
        Field(
            description="The msRun's name.",
            json_schema_extra=MetadataSerialization(ignore=True).model_dump(
                exclude_unset=True, exclude_defaults=True
            ),
        ),
    ] = None
    location: Annotated[
        str,
        Field(
            description="The msRun's location URI.",
        ),
    ]
    instrument_ref: Annotated[
        Optional[int],
        Field(
            description="Sample reference.",
            json_schema_extra=MetadataSerialization(
                referenced_field_name="instrument",
            ).model_dump(exclude_unset=True, exclude_defaults=True),
        ),
    ] = None

    format: Annotated[
        Optional[Parameter],
        Field(),
    ] = None
    id_format: Annotated[
        Optional[Parameter],
        Field(),
    ] = None
    fragmentation_method: Annotated[
        Optional[List[Parameter]],
        Field(
            description="The fragmentation methods applied during this msRun.",
        ),
    ] = None
    scan_polarity: Annotated[
        Optional[List[Parameter]],
        Field(
            description="The scan polarity/polarities used during this msRun.",
        ),
    ] = None
    hash: Annotated[
        Optional[str],
        Field(
            description="The file hash value of this msRun's data file.",
        ),
    ] = None
    hash_method: Annotated[
        Optional[Parameter],
        Field(),
    ] = None


class Assay(IdentifiableModel):
    name: Annotated[
        str,
        Field(
            description="The assay name.",
            json_schema_extra=MetadataSerialization(object_level_value=True).model_dump(
                exclude_unset=True, exclude_defaults=True
            ),
        ),
    ]
    custom: Annotated[
        Optional[List[Parameter]],
        Field(
            description="Additional user or cv parameters.",
        ),
    ] = None
    external_uri: Annotated[
        Optional[AnyUrl],
        Field(
            description="An external URI to further information about this assay.",
        ),
    ] = None
    sample_ref: Annotated[
        Optional[int],
        Field(
            description="Sample reference.",
            json_schema_extra=MetadataSerialization(
                referenced_field_name="sample",
            ).model_dump(exclude_unset=True, exclude_defaults=True),
        ),
    ] = None
    ms_run_ref: Annotated[
        List[int],
        Field(
            description="The ms run(s) referenced by this assay.",
            min_length=1,
            json_schema_extra=MetadataSerialization(
                referenced_field_name="ms_run", list_concatenation_str="|"
            ).model_dump(exclude_unset=True, exclude_defaults=True),
        ),
    ]


class CV(IdentifiableModel):
    label: Annotated[
        str,
        Field(
            description="The abbreviated CV label.",
        ),
    ]
    full_name: Annotated[
        str,
        Field(
            description="The full name of this CV, for humans.",
        ),
    ]
    version: Annotated[
        str,
        Field(
            description="The CV version used when the file was generated.",
        ),
    ]
    uri: Annotated[
        AnyUrl,
        Field(description="A URI to the CV definition."),
    ]


class Database(IdentifiableModel):
    param: Annotated[
        Parameter,
        Field(
            description="The database name.",
            json_schema_extra=MetadataSerialization(
                object_level_value=True,
            ).model_dump(exclude_unset=True, exclude_defaults=True),
        ),
    ]
    prefix: Annotated[
        Union[None, str],
        Field(
            description="The database prefix.",
        ),
    ]
    version: Annotated[
        Union[None, str],
        Field(
            description="The database version.",
        ),
    ]
    uri: Annotated[
        Union[None, str],
        Field(
            description="The URI to the online database.",
        ),
    ]

    def get_id(self):
        return self.param.id if self.param else None


class Publication(IdentifiableModel):
    publication_items: Annotated[
        List[PublicationItem],
        Field(
            alias="publicationItems",
            description="The publication item ids referenced by this publication.",
            json_schema_extra=MetadataSerialization(
                object_level_value=True,
                list_concatenation_str="|",
            ).model_dump(exclude_unset=True, exclude_defaults=True),
        ),
    ]


class StudyVariable(IdentifiableModel):
    name: Annotated[
        str,
        Field(
            description="The study variable name.",
            json_schema_extra=MetadataSerialization(
                object_level_value=True,
            ).model_dump(exclude_unset=True, exclude_defaults=True),
        ),
    ]
    assay_refs: Annotated[
        Optional[List[int]],
        Field(
            description="The assays referenced by this study variable.",
            json_schema_extra=MetadataSerialization(
                referenced_field_name="assay", list_concatenation_str="|"
            ).model_dump(exclude_unset=True, exclude_defaults=True),
        ),
    ] = None
    average_function: Annotated[
        Optional[Parameter],
        Field(
            description="The function used to calculate "
            "the study variable quantification value "
            "and the operation used is not arithmetic mean (default). "
            "e.g. geometric mean, median."
        ),
    ] = None
    variation_function: Annotated[
        Optional[Parameter],
        Field(
            description="The function used to calculate "
            "the study variable quantification variation value "
            "if it is reported and the operation used is not coefficient of variation "
            "(default). e.g. standard error.",
        ),
    ] = None
    description: Annotated[
        Optional[str],
        Field(description="A free-form description of this study variable."),
    ] = None
    factors: Annotated[
        Optional[List[Parameter]],
        Field(
            description="Parameters indicating which factors were used "
            "for the assays referenced by this study variable, and at which levels."
        ),
    ] = None


class SpectraRef(MzTabBaseModel, CustomSerializer):
    ms_run: int
    reference: Annotated[
        str,
        Field(
            description="The (vendor-dependent) reference string "
            "to the actual mass spectrum."
        ),
    ]

    @model_serializer(mode="wrap")
    def serialize_model(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> str | dict[str, Any]:
        default_success, result = self.serialize_to_json(handler, info)
        if default_success:
            return result
        return f"ms_run[{self.ms_run}]:{self.reference}"

    @model_validator(mode="wrap")
    @classmethod
    def validate_model(
        cls, data: Any, handler: ModelWrapValidatorHandler[Self], info: ValidationInfo
    ) -> Self:
        if isinstance(data, SpectraRef):
            return handler(data)
        if isinstance(info.context, ValidationSummary):
            if info.context.source_format == "json":
                return handler(data)
        val = data
        if isinstance(val, (dict, OrderedDict)):
            if len(val) == 1 and None in val:
                val = data[None]

        if isinstance(val, str):
            parts = val.strip().split(":", maxsplit=1)
            if len(parts) < 2:
                return None
            ms_run_val = parts[0].removeprefix("ms_run").strip("[]")
            ms_run = int(ms_run_val)
            val = {
                "ms_run": ms_run,
                "reference": parts[1].strip(),
            }
        return handler(val)


class ColumnParameterMapping(MzTabBaseModel, CustomSerializer):
    column_name: Annotated[
        str, Field(description="The fully qualified target column name.")
    ]
    param: Annotated[
        Parameter,
        Field(
            description="The database name.",
            json_schema_extra=MetadataSerialization(
                object_level_value=True,
            ).model_dump(exclude_unset=True, exclude_defaults=True),
        ),
    ]

    @model_serializer(mode="wrap")
    def serialize_model(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> str | dict[str, Any]:
        default_success, result = self.serialize_to_json(handler, info)
        if default_success:
            return result
        return (
            f"{sanitize_str(self.column_name)}={sanitize_str(self.param.serialize())}"
        )


class OptColumnMapping(MzTabBaseModel):
    identifier: Annotated[str, Field(description="The fully qualified column name.")]
    param: Optional[Parameter] = None
    value: Annotated[
        Optional[str],
        Field(description="The value for this column in a particular row."),
    ] = None


class Comment(MzTabBaseModel):
    prefix: Annotated[Literal["COM"], Field(description="Comment prefix")] = "COM"
    msg: Annotated[str, Field(description="message")]
    line_number: Optional[int] = None
