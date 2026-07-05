import abc
from typing import Annotated, Any, List, Literal, Mapping, Optional, OrderedDict, Union

from pydantic import (
    Field,
    ModelWrapValidatorHandler,
    ValidationInfo,
    model_validator,
)

from mztab_m_io.model.field_utils import sanitize_str
from mztab_m_io.model.serialization import (
    CompactObjectModel,
    CustomSerializer,
    IdentifiableModel,
    MetadataSerialization,
    MzTabSerializableModel,
    SerializationContext,
)
from mztab_m_io.model.validation import ValidationContext


class Parameter(CompactObjectModel, IdentifiableModel, CustomSerializer):
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
            description="The name of the parameter term.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = ""
    value: Annotated[
        Optional[str],
        Field(
            description="The user value for the parameter.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = ""

    def to_tsv(self, context: SerializationContext) -> str:
        return self.__str__()

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
        handler: ModelWrapValidatorHandler["Parameter"],
        info: ValidationInfo,
    ) -> "Parameter":
        if not data:
            return None
        if isinstance(data, Parameter):
            return handler(data)
        if info and isinstance(info.context, ValidationContext):
            if info.context.source_format in {"json", "yaml"}:
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


class ExtendedParameter(Parameter):
    value: Annotated[
        Optional[str | Parameter],
        Field(
            description="The user value for the parameter.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None

    def to_tsv(self, context: SerializationContext) -> str:
        if isinstance(self.value, Parameter):
            return (
                f"[{sanitize_str(self.cv_label)}, "
                f"{sanitize_str(self.cv_accession)}, "
                f"{sanitize_str(self.name)}, "
                f"{sanitize_str(self.value.to_tsv(context))}]"
            )
        return super().to_tsv(context)

    @model_validator(mode="wrap")
    @classmethod
    def validate_model(
        cls,
        data: Any,
        handler: ModelWrapValidatorHandler["ExtendedParameter"],
        info: ValidationInfo,
    ) -> "ExtendedParameter":
        if not data:
            return None
        if isinstance(data, ExtendedParameter):
            return handler(data)
        if info and isinstance(info.context, ValidationContext):
            if info.context.source_format in {"json", "yaml"}:
                return handler(data)

        val = data
        if isinstance(val, Mapping):
            if len(val) == 1 and None in val:
                val = data[None]
        if isinstance(val, dict):
            value_str = val.get("value", "")
            value_str = value_str.strip('"')
            if value_str.startswith("["):
                value = Parameter.model_validate(value_str.strip("[]"))
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
                    value = Parameter.model_validate(value_str.strip("[]"))

            val = {
                "cv_label": cv_label,
                "cv_accession": cv_accession,
                "name": name,
                "value": value.strip('"'),
            }
        return handler(val)


class CustomParameterContainerModel(MzTabSerializableModel):
    custom: Annotated[
        Optional[List[ExtendedParameter]],
        Field(
            description="Additional user or cv parameters.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None


class Instrument(IdentifiableModel, CustomParameterContainerModel):
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

    @model_validator(mode="wrap")
    @classmethod
    def validate_model(
        cls,
        data: Any,
        handler: ModelWrapValidatorHandler["Instrument"],
        info: ValidationInfo,
    ) -> "Instrument":
        if info and isinstance(info.context, ValidationContext):
            if info.context.source_format in {"json", "yaml"}:
                return handler(data)
        if isinstance(data, Mapping):
            if "analyzer" in data:
                val = data["analyzer"]
                if isinstance(val, (str, Parameter)):
                    data["analyzer"] = [val]
        return handler(data)


class Protocol(IdentifiableModel):
    name: Annotated[
        Optional[str],
        Field(
            description="The protocol name.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    type: Annotated[
        Optional[Parameter],
        Field(
            description="The protocol type, as defined by the parameter.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    description: Annotated[
        Optional[str],
        Field(
            description="Description of the protocol.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    parameter: Annotated[
        Optional[List[ExtendedParameter]],
        Field(
            description="The protocol parameters.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None


class SampleProcessing(IdentifiableModel):
    """A list of parameters describing a sample processing,
    preparation or handling step similar to a biological or analytical methods report.
    The order of the sample_processing items should reflect the order
    these processing steps were performed in. If multiple parameters are given
    for a step these MUST be separated by a “|”. If derivatization was performed,
    it MUST be reported here as a general step, e.g. 'silylation' and
    the actual derivatization agens MUST be specified in the Section 6.2.54 part.
    """

    sample_processing: Annotated[
        Optional[List[Parameter]],
        Field(
            description="Parameters specifying sample processing "
            "that was applied within one step.",
            json_schema_extra=MetadataSerialization(
                list_concatenation_str="|", object_level_value=True
            ).model_dump(),
        ),
    ] = None


class Software(IdentifiableModel, CustomParameterContainerModel):
    """Software used to analyze the data and obtain the reported results.
    The parameter's value SHOULD contain the software's version.
    The order (numbering) should reflect the order in which the tools were used.
    A software setting used. This field MAY occur multiple times for a single software.
    The value of this field is deliberately set as a String,
    since there currently do not exist CV terms for every possible setting.
    """

    parameter: Annotated[
        Optional[Parameter],
        Field(
            description="The software utilized.",
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


class PublicationItem(CustomParameterContainerModel, CustomSerializer):
    """A publication item, defined by a qualifier
    and a native accession, e.g. pubmed id.
    """

    type: Annotated[
        Optional[str],
        Field(
            description="The type qualifier of this publication item.",
            examples=["doi", "pubmed", "uri"],
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    accession: Annotated[
        Optional[str],
        Field(
            description="The native accession id for this publication item.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None

    def to_tsv(self, context: SerializationContext) -> str:
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
        if info and isinstance(info.context, ValidationContext):
            if info.context.source_format in {"json", "yaml"}:
                return handler(data)
        val = data
        if isinstance(data, (OrderedDict, dict)):
            if len(data) == 1 and None in data:
                val = data[None]
        if isinstance(val, str) and ":" in val:
            parts = val.split(":", maxsplit=1)
            val = {"type": parts[0], "accession": parts[1]}
        return handler(val)


class Uri(IdentifiableModel):
    """A URI pointing to the file's source data (e.g., a MetaboLights records)
    or an external file with more details about the study design.."""

    value: Annotated[
        Optional[str],
        Field(
            description="The URI pointing to the external resource.",
            json_schema_extra=MetadataSerialization(
                object_level_value=True,
            ).model_dump(),
        ),
    ] = None


class Contact(IdentifiableModel, CustomParameterContainerModel):
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
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    orcid: Annotated[
        Optional[str],
        Field(
            description="The contact's orcid id, without https prefix.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None


class Sample(IdentifiableModel, CustomParameterContainerModel):
    """Specification of sample.
    (empty) name: A name for each sample to serve as a list of the samples that MUST be
    reported in the following tables.
    Samples MUST be reported if a statistical design is being captured
    (i.e. bio or tech replicates).
    If the type of replicates are not known, samples SHOULD NOT be reported.
    species: The respective species of the samples analysed.
    For more complex cases, such as metagenomics, optional columns
    and userParams should be used.\ntissue: The respective tissue(s) of the sample.
    cell_type: The respective cell type(s) of the sample.
    disease: The respective disease(s) of the sample.
    description: A human readable description of the sample.
    custom: Custom parameters describing the sample's additional properties.
    Dates MUST be provided in ISO-8601 format.
    """

    name: Annotated[
        Optional[str],
        Field(
            description="The sample's name.",
            json_schema_extra=MetadataSerialization(
                object_level_value=True
            ).model_dump(),
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


class MsRun(IdentifiableModel, CustomParameterContainerModel):
    """Specification of ms_run.
    location: Location of the external data file
    e.g. raw files on which analysis has been performed.
    If the actual location of the MS run is unknown, a `null` MUST be used
    as a place holder value, since the [1-n] cardinality is referenced elsewhere.
    If pre-fractionation has been performed,
    then [1-n] ms_runs SHOULD be created per assay.
    instrument_ref: If different instruments are used in different runs,
    instrument_ref can be used to link a specific instrument to a specific run.
    format: Parameter specifying the data format of the external MS data file.
    If ms_run[1-n]-format is present, ms_run[1-n]-id_format SHOULD also be present,
    following the parameters specified in Table 1.
    id_format: Parameter specifying the id format used in the external data file.
    If ms_run[1-n]-id_format is present, ms_run[1-n]-format SHOULD also be present.
    fragmentation_method: The type(s) of fragmentation used in a given ms run.
    scan_polarity: The polarity mode of a given run.
    Usually only one value SHOULD be given here except for the case of
    mixed polarity runs.
    hash: Hash value of the corresponding external MS data file defined
    in ms_run[1-n]-location. If ms_run[1-n]-hash is present, ms_run[1-n]-hash_method
    SHOULD also be present.\nhash_method: A parameter specifying the hash methods
    used to generate the String in ms_run[1-n]-hash.
    Specifics of the hash method used MAY follow the definitions of the mzML format.
    If ms_run[1-n]-hash is present, ms_run[1-n]-hash_method SHOULD also be present.
    """

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
            json_schema_extra=MetadataSerialization().model_dump(),
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
            description="The format of the MS run file.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    id_format: Annotated[
        Optional[Parameter],
        Field(
            description="The format of the IDs in the MS run file.",
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
            description="The method used to calculate the hash.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    parameter: Annotated[
        Optional[List[ExtendedParameter]],
        Field(
            description="Additional user or cv parameters.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None


class Assay(IdentifiableModel, CustomParameterContainerModel):
    """Specification of assay.
    (empty) name: A name for each assay, to serve as a list of the assays
    that MUST be reported in the following tables.
    custom: Additional custom parameters or values for a given assay.
    external_uri: An external reference uri to further information about the assay,
    for example via a reference to an object within an ISA-TAB file.
    sample_ref: An association from a given assay to the sample analysed.
    ms_run_ref: An association from a given assay to the source MS run. All assays
    MUST reference exactly one ms_run unless a workflow with pre-fractionation
    is being encoded, in which case each assay MUST reference n ms_runs
    where n fractions have been collected.
    Multiple assays SHOULD reference the same ms_run
    to capture multiplexed experimental designs.
    """

    name: Annotated[
        Optional[str],
        Field(
            description="The assay name.",
            json_schema_extra=MetadataSerialization(
                object_level_value=True,
            ).model_dump(),
        ),
    ] = None
    external_uri: Annotated[
        Optional[str],
        Field(
            description="An external URI to further information about this assay.",
            json_schema_extra=MetadataSerialization().model_dump(),
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
    ms_run_refs: Annotated[
        Optional[List[int]],
        Field(
            alias="ms_run_ref",
            description="The ms run(s) referenced by this assay.",
            json_schema_extra=MetadataSerialization(
                referenced_field_name="ms_run",
                list_concatenation_str="|",
            ).model_dump(),
        ),
    ] = None
    protocol_refs: Annotated[
        Optional[List[int]],
        Field(
            description="The protocol(s) referenced by this assay.",
            examples=["MTD\tassay[1]-protocol_ref\tprotocol[1]| protocol[2]"],
            json_schema_extra=MetadataSerialization(
                referenced_field_name="protocol",
                list_concatenation_str="|",
            ).model_dump(),
        ),
    ] = []
    parameter: Annotated[
        Optional[List[ExtendedParameter]],
        Field(
            description="Additional parameters of the assay, separated by bars.",
            examples=[
                "MTD\tassay[1]-parameter[1]\t[MS, MS:1000031, instrument model, "
                "[MS, MS:1000449, LTQ Orbitrap,]]"
            ],
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None


class CV(IdentifiableModel, CustomParameterContainerModel):
    """Specification of controlled vocabularies.
    label: A string describing the labels of the controlled vocabularies/ontologies
    used in the mzTab file as a short-hand e.g. 'MS' for PSI-MS.
    full_name: A string describing the full names of the controlled
    vocabularies/ontologies used in the mzTab file.
    version: A string describing the version of the controlled vocabularies/ontologies
    used in the mzTab file.
    uri: A string containing the URIs of the controlled vocabularies/ontologies used in
    the mzTab file.
    """

    label: Annotated[
        Optional[str],
        Field(
            description="The abbreviated CV label.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    full_name: Annotated[
        Optional[str],
        Field(
            description="The full name of this CV, for humans.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    version: Annotated[
        Optional[str],
        Field(
            description="The CV version used when the file was generated.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    uri: Annotated[
        Optional[str],
        Field(
            description="A URI to the CV definition.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None


class Database(IdentifiableModel, CustomParameterContainerModel):
    param: Annotated[
        Parameter,
        Field(
            description="The database name.",
            json_schema_extra=MetadataSerialization(
                object_level_value=True,
            ).model_dump(),
        ),
    ] = None
    prefix: Annotated[
        Optional[str],
        Field(
            description="The prefix used in the “identifier” column of data tables. "
            "For the 'no database' case 'null' must be used.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    version: Annotated[
        Optional[str],
        Field(
            description="The database version is mandatory where identification "
            "has been performed. This may be a formal version number "
            "e.g. “1.4.1”, a date of access “2016-10-27” (ISO-8601 format) "
            "or “Unknown” if there is no suitable version that can be annotated.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    uri: Annotated[
        Optional[str],
        Field(
            description="The URI to the database. "
            "For the “no database” case, 'null' must be reported.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None

    def get_id(self):
        return self.param.id if self.param else None


class Publication(IdentifiableModel):
    publication_items: Annotated[
        Optional[List[PublicationItem]],
        Field(
            description="The publication item ids referenced by this publication.",
            json_schema_extra=MetadataSerialization(
                object_level_value=True,
                list_concatenation_str="|",
            ).model_dump(),
        ),
    ] = None


class StudyVariableGroup(IdentifiableModel, CustomParameterContainerModel):
    """Specification of study_variable_group.
    (empty) name/parameter: A parameter defining the group to which study
    variables belong. This allows grouping of related study variables that belong to
    the same experimental design factor in multi-factorial designs.
    The parameter can be either a CV Parameter
    (e.g., [OBI, OBI:0001667, organism development stage, ])
    or a user-defined parameter (e.g., [,,sex,]).
    For software that does not capture study variables,
    a single study_variable_group MUST be reported,
    linking to the single study variable, and MUST have the identifier `undefined`.
    Added in mzTab-M 2.1.
    description: A textual description of the study variable group.
    type: The statistical type of the group variable, which determines how the values
    should be interpreted in a statistical analysis context.
    The type MUST be a term from the STATO ontology, and SHOULD be one of
    [STATO, STATO:0000252, categorical variable],
    [STATO, STATO:0000228, ordinal variable],
    or [STATO, STATO:0000251, continuous variable].
    datatype: The datatype of the group variable, used to disambiguate how the
    associated values are encoded and parsed. Optional, but producers SHOULD provide it
    to simplify interpretation by downstream consumers.
    Supported values are xsd:string, xsd:integer, xsd:decimal, xsd:boolean,
    xsd:date, xsd:time, xsd:dateTime, xsd:anyURI, and Parameter
    (for values reported as user-defined or CV Parameters).
    Date, time and dateTime values MUST be encoded in ISO 8601 format.
    Writers MUST ensure that all study_variable values linked to the same
    study_variable_group share the declared datatype and reporting convention.
    unit: An optional parameter specifying the unit of
    the study variable group (e.g., day, hour, concentration, etc.).
    """

    name: Annotated[
        Optional[Parameter],
        Field(
            description="The study variable group name.",
            json_schema_extra=MetadataSerialization(
                object_level_value=True
            ).model_dump(),
        ),
    ] = None

    description: Annotated[
        Optional[str],
        Field(
            description="Description of the study variable group.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None

    type: Annotated[
        Optional[Parameter],
        Field(
            description="The study variable group type, as defined by the parameter.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    datatype: Annotated[
        Optional[
            Union[
                Literal[
                    "xsd:string",
                    "xsd:integer",
                    "xsd:decimal",
                    "xsd:boolean",
                    "xsd:date",
                    "xsd:time",
                    "xsd:dateTime",
                    "xsd:anyURI",
                ],
                Parameter,
            ]
        ],
        Field(
            description="The study variable group datatype",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None

    unit: Annotated[
        Optional[Parameter],
        Field(
            description="The study variable group unit, as defined by the parameter.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None


class StudyVariable(IdentifiableModel, CustomParameterContainerModel):
    """Specification of study_variable.
    (empty) name: A name for each study variable (experimental condition or factor),
    to serve as a list of the study variables that MUST be reported in the following
    tables. For software that does not capture study variables,
    a single study variable MUST be reported, linking to all assays.
    This single study variable MUST have the identifier “undefined“.
    assay_refs: Bar-separated references to the IDs of assays grouped
    in the study variable.
    average_function: The function used to calculate the study variable quantification
    value and the operation used is not arithmetic mean (default)
    e.g. “geometric mean”, “median”. The 1-n refers to different study variables.
    variation_function: The function used to calculate
    the study variable quantification variation value if it is reported
    and the operation used is not coefficient of variation (default)
    e.g. “standard error”.
    description: A textual description of the study variable.
    """

    name: Annotated[
        Optional[Union[str, Parameter]],
        Field(
            description="The study variable value. Encoded according to the datatype "
            "declared on the referenced study_variable_group: either a literal value "
            "(for xsd:* datatypes) "
            "or a Parameter (for the Parameter datatype, "
            "e.g. `[NO, NO:12345, Male,]` or `[,,Male,]`).",
            json_schema_extra=MetadataSerialization(
                object_level_value=True,
            ).model_dump(),
        ),
    ] = None
    group_refs: Annotated[
        Optional[List[int]],
        Field(
            description="The study variable group this study variable belongs to.",
            json_schema_extra=MetadataSerialization(
                referenced_field_name="study_variable_group",
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
            ).model_dump(),
        ),
    ] = None
    ms_run_refs: Annotated[
        Optional[List[int]],
        Field(
            description="The ms run(s) referenced by this study variable.",
            json_schema_extra=MetadataSerialization(
                referenced_field_name="ms_run",
                list_concatenation_str="|",
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


class SpectraReference(MzTabSerializableModel, CustomSerializer):
    """Reference to a spectrum in a spectrum file, for example a fragmentation spectrum
    has been used to support the identification. If a separate spectrum file has been
    used for fragmentation spectrum, this MUST be reported in the metadata section
    as additional ms_runs. The reference must be in the format
    ms_run[1-n]:{SPECTRA_REF} where SPECTRA_REF MUST follow the format defined in 5.2
    (including references to chromatograms where these are used to
    inform identification). Multiple spectra MUST be referenced
    using a | delimited list for the (rare) cases in which search engines have combined
    or aggregated multiple spectra in advance of the search to make identifications.

    If a fragmentation spectrum has not been used, the value should indicate the ms_run
    to which is identification is mapped e.g. “ms_run[1]”.
    """

    ms_run_ref: Annotated[
        Optional[int],
        Field(
            validation_alias="ms_run",
            serialization_alias="ms_run",
            description="Reference to MsRun",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    reference: Annotated[
        Optional[str],
        Field(
            description="The (vendor-dependent) reference string "
            "to the actual mass spectrum.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None

    def to_tsv(self, context: SerializationContext) -> str:
        return f"ms_run[{self.ms_run_ref}]:{sanitize_str(self.reference)}"

    @model_validator(mode="wrap")
    @classmethod
    def validate_model(
        cls,
        data: Any,
        handler: ModelWrapValidatorHandler["SpectraReference"],
        info: ValidationInfo,
    ) -> "SpectraReference":
        if isinstance(data, SpectraReference):
            return handler(data)
        if info and isinstance(info.context, ValidationContext):
            if info.context.source_format in {"json", "yaml"}:
                return handler(data)
        val = data
        if isinstance(val, Mapping):
            if len(val) == 1 and None in val:
                val = data[None]

        if isinstance(val, str):
            parts = val.strip().split(":", maxsplit=1)
            if len(parts) < 2:
                return None
            ms_run_val = parts[0].removeprefix("ms_run").strip("[]")
            ms_run = int(ms_run_val)
            val = {
                "ms_run_ref": ms_run,
                "reference": parts[1].strip(),
            }
        return handler(val)


class ColumnParameterMapping(
    MzTabSerializableModel, CompactObjectModel, CustomSerializer
):
    column_name: Annotated[
        Optional[str],
        Field(
            description="The fully qualified target column name.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    param: Annotated[
        Optional[Parameter],
        Field(
            description="The parameter defining the unit.",
            json_schema_extra=MetadataSerialization(
                object_level_value=True,
            ).model_dump(),
        ),
    ] = None

    def to_tsv(self, context: SerializationContext) -> str:
        if self.param:
            return f"{sanitize_str(self.column_name)}={self.param.to_tsv(context)}"
        return f"{sanitize_str(self.column_name)}=null"

    @model_validator(mode="wrap")
    @classmethod
    def validate_model(
        cls,
        data: Any,
        handler: ModelWrapValidatorHandler["OptColumnMapping"],
        info: ValidationInfo,
    ) -> "ColumnParameterMapping":
        if not data:
            return None
        if isinstance(data, ColumnParameterMapping):
            return handler(data)
        if info and isinstance(info.context, ValidationContext):
            if info.context.source_format in {"json", "yaml"}:
                return handler(data)
        val = data
        if isinstance(val, Mapping):
            if len(val) == 1 and None in val:
                val = data[None]
        if isinstance(val, str):
            parts = val.split("=", maxsplit=1)

            if len(parts) < 2:
                return None
            if parts[0]:
                val = {
                    "column_name": parts[0].strip() if parts[0] else None,
                    "param": Parameter.model_validate(parts[1].strip())
                    if parts[1]
                    else None,
                }

        return handler(val)


class OptionalTableColumn(abc.ABC):
    """
    An abstract base class to show that a model is a optional table column.
    """

    @abc.abstractmethod
    def get_header(self) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def get_value(self) -> Union[int, float, bool, str, MzTabSerializableModel, None]:
        raise NotImplementedError


class OptColumnMapping(MzTabSerializableModel, OptionalTableColumn):
    identifier: Annotated[
        Union[None, str],
        Field(
            description="The fully qualified column name.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    param: Annotated[
        Optional[Parameter],
        Field(
            description="The fully qualified column parameter.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None
    value: Annotated[
        Optional[str],
        Field(
            description="The value for this column in a particular row.",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None

    def get_header(self) -> str:
        if self.param and self.param.cv_accession and self.param.cv_label:
            return (
                f"opt_{self.identifier}_cv_{self.param.cv_accession}_{self.param.name}"
            )
        elif self.param and self.param.name:
            return f"opt_{self.identifier}_{self.param.name}"
        return f"opt_{self.identifier}"

    def get_value(self) -> str:
        return self.value


class Comment(MzTabSerializableModel, CustomSerializer):
    """
    Comment lines can be placed anywhere in an mzTab file.
    These lines must start with the three-letter code COM
    and are ignored by most parsers.
    Empty lines can also occur anywhere in an mzTab file and are ignored.
    """

    __mztab_example__ = "COM\tThis is a comment"

    prefix: Annotated[
        str,
        Field(
            description="Comment prefix",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = "COM"

    msg: Annotated[
        Optional[str],
        Field(
            description="message",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = ""

    line_number: Annotated[
        Optional[int],
        Field(
            description="line number",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None

    def to_tsv(self, context: SerializationContext) -> str:
        return f"{self.prefix}\t{self.msg}"
