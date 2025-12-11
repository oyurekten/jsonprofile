from typing import Dict
from typing_extensions import (
    Annotated,
    Any,
    List,
    Optional,
    OrderedDict,
    Union,
)

from pydantic import (
    Field,
    ModelWrapValidatorHandler,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    ValidationInfo,
    model_serializer,
    model_validator,
)

from mztab_m_io.model import CustomSerializer, IdentifiableModel, MzTabBaseModel
from mztab_m_io.model.field_utils import sanitize_str
from mztab_m_io.model.serialization import MetadataSerialization, ValidationPolicy
from mztab_m_io.model.validation import ValidationSummary

AdductIon = Annotated[str, Field(pattern=r"^\[\d*M([+-][\w\d]+)*\]\d*[+-]$")]


class Parameter(IdentifiableModel, CustomSerializer):
    cv_label: Annotated[
        Optional[str],
        Field(
            description="CV label",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = ""
    cv_accession: Annotated[
        Optional[str],
        Field(
            description="CV accession in CURIE format",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = ""
    name: Annotated[
        Optional[str],
        Field(
            description="name",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = ""
    value: Annotated[
        Optional[str],
        Field(
            description="value",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = ""

    @model_serializer(mode="wrap")
    def serialize_model(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> Union[str, Dict[str, Any]]:
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
        cls,
        data: Any,
        handler: ModelWrapValidatorHandler["Parameter"],
        info: ValidationInfo,
    ) -> "Parameter":
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
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    source: Annotated[
        Optional[Parameter],
        Field(
            description="The instrument's ion source.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    analyzer: Annotated[
        Optional[List[Parameter]],
        Field(
            description="The instrument's mass analyzer, as defined by the parameter.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    detector: Annotated[
        Optional[Parameter],
        Field(
            description="The instrument's mass analyzer, as defined by the parameter.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None


class SampleProcessing(IdentifiableModel):
    sample_processing: Annotated[
        Optional[List[Parameter]],
        Field(
            alias="sampleProcessing",
            description="Parameters specifying sample processing "
            "that was applied within one step.",
            json_schema_extra=MetadataSerialization(
                list_concatenation_str="|", object_level_value=True
            ).model_dump(),
        ),
    ] = None


class Software(IdentifiableModel):
    parameter: Annotated[
        Optional[Parameter],
        Field(
            json_schema_extra=MetadataSerialization(
                object_level_value=True,
            ).model_dump(),
        ),
    ] = None
    setting: Annotated[
        Optional[List[str]],
        Field(
            description="A software setting used. "
            "This field MAY occur multiple times for a single software. "
            "The value of this field is deliberately set as a String, "
            "since there currently do not exist cvParams for every possible setting.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None


class PublicationItem(MzTabBaseModel, CustomSerializer):
    type: Annotated[
        Optional[str],
        Field(
            description="The type qualifier of this publication item.",
            examples=["doi", "pubmed", "uri"],
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(pattern=r"doi|pubmed|uri")
            ).model_dump(),
        ),
    ] = None
    accession: Annotated[
        Optional[str],
        Field(
            description="The native accession id for this publication item.",
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(required=True)
            ).model_dump(),
        ),
    ] = None

    @model_serializer(mode="wrap")
    def serialize_model(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> Union[str, Dict[str, Any]]:
        default_success, result = self.serialize_to_json(handler, info)
        if default_success:
            return result
        return f"{sanitize_str(self.type)}:{sanitize_str(self.accession)}"

    @model_validator(mode="wrap")
    @classmethod
    def deserialize(
        cls,
        data: Any,
        handler: ModelWrapValidatorHandler["PublicationItem"],
        info: ValidationInfo,
    ) -> "PublicationItem":
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
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    affiliation: Annotated[
        Optional[str],
        Field(
            description="The contact's affiliation.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    email: Annotated[
        Optional[str],
        Field(
            description="The contact's e-mail address.",
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(
                    pattern=r"^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$",
                )
            ).model_dump(),
        ),
    ] = None
    orcid: Annotated[
        Optional[str],
        Field(
            description="The contact's orcid id, without https prefix.",
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(
                    pattern=r"^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]{1}$",
                )
            ).model_dump(),
        ),
    ] = None


class Uri(IdentifiableModel):
    value: Annotated[
        Optional[str],
        Field(
            description="The URI pointing to the external resource.",
            json_schema_extra=MetadataSerialization(
                object_level_value=True,
                validation_policy=ValidationPolicy(value_constraint="any-url"),
            ).model_dump(),
        ),
    ] = None


class Sample(IdentifiableModel):
    name: Annotated[
        Optional[str],
        Field(
            description="The sample's name.",
            json_schema_extra=MetadataSerialization(
                object_level_value=True
            ).model_dump(),
        ),
    ] = None
    custom: Annotated[
        Optional[List[Parameter]],
        Field(
            description="Additional user or cv parameters.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    species: Annotated[
        Optional[List[Parameter]],
        Field(
            description="Biological species information on the sample.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    tissue: Annotated[
        Optional[List[Parameter]],
        Field(
            description="Biological tissue information on the sample.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    cell_type: Annotated[
        Optional[List[Parameter]],
        Field(
            description="Biological cell type information on the sample.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    disease: Annotated[
        Optional[List[Parameter]],
        Field(
            description="Disease information on the sample.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    description: Annotated[
        Optional[str],
        Field(
            description="A free form description of the sample.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None


class MsRun(IdentifiableModel):
    name: Annotated[
        Optional[str],
        Field(
            description="The msRun's name.",
            json_schema_extra=MetadataSerialization(ignore=True).model_dump(),
        ),
    ] = None
    location: Annotated[
        Optional[str],
        Field(
            description="The msRun's location URI.",
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(required=True)
            ).model_dump(),
        ),
    ] = None
    instrument_ref: Annotated[
        Optional[int],
        Field(
            description="Sample reference.",
            json_schema_extra=MetadataSerialization(
                referenced_field_name="instrument",
            ).model_dump(),
        ),
    ] = None

    format: Annotated[
        Optional[Parameter],
        Field(
            description="",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    id_format: Annotated[
        Optional[Parameter],
        Field(
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    fragmentation_method: Annotated[
        Optional[List[Parameter]],
        Field(
            description="The fragmentation methods applied during this msRun.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    scan_polarity: Annotated[
        Optional[List[Parameter]],
        Field(
            description="The scan polarity/polarities used during this msRun.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    hash: Annotated[
        Optional[str],
        Field(
            description="The file hash value of this msRun's data file.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    hash_method: Annotated[
        Optional[Parameter],
        Field(
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None


class Assay(IdentifiableModel):
    name: Annotated[
        Optional[str],
        Field(
            description="The assay name.",
            json_schema_extra=MetadataSerialization(
                object_level_value=True,
                validation_policy=ValidationPolicy(required=True),
            ).model_dump(),
        ),
    ] = None
    custom: Annotated[
        Optional[List[Parameter]],
        Field(
            description="Additional user or cv parameters.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    external_uri: Annotated[
        Optional[str],
        Field(
            description="An external URI to further information about this assay.",
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(value_constraint="any-url"),
            ).model_dump(),
        ),
    ] = None
    sample_ref: Annotated[
        Optional[int],
        Field(
            description="Sample reference.",
            json_schema_extra=MetadataSerialization(
                referenced_field_name="sample",
            ).model_dump(),
        ),
    ] = None
    ms_run_ref: Annotated[
        Optional[List[int]],
        Field(
            description="The ms run(s) referenced by this assay.",
            min_length=1,
            json_schema_extra=MetadataSerialization(
                referenced_field_name="ms_run",
                list_concatenation_str="|",
                validation_policy=ValidationPolicy(
                    required=True, minimum=1, value_constraint="non-negative-integer"
                ),
            ).model_dump(),
        ),
    ] = None


class CV(IdentifiableModel):
    label: Annotated[
        Optional[str],
        Field(
            description="The abbreviated CV label.",
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(required=True),
            ).model_dump(),
        ),
    ] = None
    full_name: Annotated[
        Optional[str],
        Field(
            description="The full name of this CV, for humans.",
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(required=True),
            ).model_dump(),
        ),
    ] = None
    version: Annotated[
        Optional[str],
        Field(
            description="The CV version used when the file was generated.",
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(required=True),
            ).model_dump(),
        ),
    ] = None
    uri: Annotated[
        Optional[str],
        Field(
            description="A URI to the CV definition.",
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(
                    required=True, value_constraint="any-url"
                ),
            ).model_dump(),
        ),
    ] = None


class Database(IdentifiableModel):
    param: Annotated[
        Parameter,
        Field(
            description="The database name.",
            json_schema_extra=MetadataSerialization(
                object_level_value=True,
                validation_policy=ValidationPolicy(required=True),
            ).model_dump(),
        ),
    ] = None
    prefix: Annotated[
        Optional[str],
        Field(
            description="The prefix used in the “identifier” column of data tables. "
            "For the 'no database' case 'null' must be used.",
            json_schema_extra=MetadataSerialization(
                validation_policy=(
                    ValidationPolicy(required=True, enforcement_level="recommended")
                )
            ).model_dump(),
        ),
    ] = None
    version: Annotated[
        Optional[str],
        Field(
            description="The database version is mandatory where identification "
            "has been performed. This may be a formal version number "
            "e.g. “1.4.1”, a date of access “2016-10-27” (ISO-8601 format) "
            "or “Unknown” if there is no suitable version that can be annotated.",
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(required=True),
            ).model_dump(),
        ),
    ] = None
    uri: Annotated[
        Optional[str],
        Field(
            description="The URI to the database. "
            "For the “no database” case, 'null' must be reported.",
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(
                    required=True, enforcement_level="recommended"
                )
            ).model_dump(),
        ),
    ] = None

    def get_id(self):
        return self.param.id if self.param else None


class Publication(IdentifiableModel):
    publication_items: Annotated[
        Optional[List[PublicationItem]],
        Field(
            alias="publicationItems",
            description="The publication item ids referenced by this publication.",
            json_schema_extra=MetadataSerialization(
                object_level_value=True,
                list_concatenation_str="|",
                validation_policy=ValidationPolicy(required=True, minimum=1),
            ).model_dump(),
        ),
    ] = None


class StudyVariable(IdentifiableModel):
    name: Annotated[
        Optional[str],
        Field(
            description="The study variable name.",
            json_schema_extra=MetadataSerialization(
                object_level_value=True,
                validation_policy=ValidationPolicy(required=True),
            ).model_dump(),
        ),
    ] = None
    assay_refs: Annotated[
        Optional[List[int]],
        Field(
            description="The assays referenced by this study variable.",
            json_schema_extra=MetadataSerialization(
                referenced_field_name="assay",
                list_concatenation_str="|",
                validation_policy=ValidationPolicy(
                    value_constraint="non-negative-integer"
                ),
            ).model_dump(),
        ),
    ] = None
    average_function: Annotated[
        Optional[Parameter],
        Field(
            description="The function used to calculate "
            "the study variable quantification value "
            "and the operation used is not arithmetic mean (default). "
            "e.g. geometric mean, median.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    variation_function: Annotated[
        Optional[Parameter],
        Field(
            description="The function used to calculate "
            "the study variable quantification variation value "
            "if it is reported and the operation used is not coefficient of variation "
            "(default). e.g. standard error.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    description: Annotated[
        Optional[str],
        Field(
            description="A free-form description of this study variable.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    factors: Annotated[
        Optional[List[Parameter]],
        Field(
            description="Parameters indicating which factors were used "
            "for the assays referenced by this study variable, and at which levels.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None


class SpectraRef(MzTabBaseModel, CustomSerializer):
    ms_run: Annotated[
        Optional[int],
        Field(
            description="Reference to MsRun",
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(
                    required=True, value_constraint="positive-integer"
                )
            ).model_dump(),
        ),
    ] = None
    reference: Annotated[
        Optional[str],
        Field(
            description="The (vendor-dependent) reference string "
            "to the actual mass spectrum.",
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(required=True)
            ).model_dump(),
        ),
    ] = None

    @model_serializer(mode="wrap")
    def serialize_model(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> Union[str, Dict[str, Any]]:
        default_success, result = self.serialize_to_json(handler, info)
        if default_success:
            return result
        return f"ms_run[{self.ms_run}]:{self.reference}"

    @model_validator(mode="wrap")
    @classmethod
    def validate_model(
        cls,
        data: Any,
        handler: ModelWrapValidatorHandler["SpectraRef"],
        info: ValidationInfo,
    ) -> "SpectraRef":
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
        Optional[str],
        Field(
            description="The fully qualified target column name.",
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(required=True)
            ).model_dump(),
        ),
    ] = None
    param: Annotated[
        Optional[Parameter],
        Field(
            description="The database name.",
            json_schema_extra=MetadataSerialization(
                object_level_value=True,
                validation_policy=ValidationPolicy(required=True),
            ).model_dump(),
        ),
    ] = None

    @model_serializer(mode="wrap")
    def serialize_model(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> Union[str, Dict[str, Any]]:
        default_success, result = self.serialize_to_json(handler, info)
        if default_success:
            return result
        return (
            f"{sanitize_str(self.column_name)}={sanitize_str(self.param.serialize())}"
        )


class OptColumnMapping(MzTabBaseModel):
    identifier: Annotated[
        Optional[str],
        Field(
            description="The fully qualified column name.",
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(required=True)
            ).model_dump(),
        ),
    ] = None
    param: Annotated[
        Optional[Parameter],
        Field(
            description="The fully qualified column name.",
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(required=True)
            ).model_dump(),
        ),
    ] = None
    value: Annotated[
        Optional[str],
        Field(
            description="The value for this column in a particular row.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None


class Comment(MzTabBaseModel):
    prefix: Annotated[
        str,
        Field(
            description="Comment prefix",
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(required=True, pattern=r"COM")
            ).model_dump(),
        ),
    ] = "COM"
    msg: Annotated[
        Optional[str],
        Field(
            description="message",
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(required=True)
            ).model_dump(),
        ),
    ] = ""
    line_number: Annotated[
        Optional[int],
        Field(
            description="line number",
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(value_constraint="positive-integer")
            ).model_dump(),
        ),
    ] = None
