import re
from typing import (
    Annotated,
    Any,
    List,
    Literal,
    Optional,
    OrderedDict,
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

from mztab_m_io.model import (
    CustomSerializer,
    IdentifiableModel,
    MzTabBaseModel,
    SerializableModel,
)
from mztab_m_io.model.common import (
    CV,
    Assay,
    ColumnParameterMapping,
    Contact,
    Database,
    Instrument,
    MsRun,
    Parameter,
    Publication,
    Sample,
    SampleProcessing,
    Software,
    StudyVariable,
    Uri,
)
from mztab_m_io.model.field_utils import get_field_type_info
from mztab_m_io.model.serialization import MetadataDictInfo, MetadataSerialization
from mztab_m_io.model.validation import ValidationSummary


class Metadata(MzTabBaseModel, CustomSerializer):
    prefix: Annotated[
        Literal["MTD"],
        Field(
            description="Metadata section prefix identifier.\n\n"
            "Value must be 'MTD'. Used to identify metadata lines in the mzTab-M file format.",
            examples=["MTD"],
            frozen=True,
            json_schema_extra=MetadataSerialization(ignore=True).model_dump(
                exclude_unset=True, exclude_defaults=True
            ),
        ),
    ] = "MTD"
    mztab_version: Annotated[
        str,
        Field(
            alias="mzTab-version",
            description="Version number of the mzTab format used.\n\n"
            "Format: `major.minor.patch-variant`\n"
            'Must end with "-M" suffix for metabolomics variant.\n\n'
            "Used to ensure compatibility and processing correctness.",
            pattern=r"^\d{1}\.\d{1}\.\d{1}-[A-Z]{1}$",
            examples=["2.0.0-M", "2.1.0-M"],
        ),
    ]
    mztab_id: Annotated[
        str,
        Field(
            alias="mzTab-ID",
            description="Unique identifier for the mzTab-M document.\n"
            "REQUIRED. Can be:\n"
            "- Repository accession number (e.g., MTBLS214)\n"
            "- Laboratory internal identifier\n"
            "- Study-specific identifier\n"
            "NOT intended as a globally unique identifier,\n"
            "but SHOULD have local meaning within its context.",
            examples=["MTBLS214", "LAB001_2023", "STUDY123_BATCH1"],
        ),
    ]
    title: Annotated[
        Optional[str],
        Field(
            description="Human-readable title of the experiment or study.\n"
            "OPTIONAL. SHOULD be:\n"
            "- Concise but informative\n"
            "- Reflect the main focus of the study\n"
            "- Unique within a collection of related studies",
            examples=[
                "Metabolomic Analysis of Human Plasma in Diabetes Type 2",
                "Lipidomics Study of Brain Tissue in Alzheimer's Disease",
            ],
        ),
    ] = None
    description: Annotated[
        Optional[str],
        Field(
            description="Detailed description of the experiment or study.\n"
            "OPTIONAL. SHOULD include:\n"
            "- Study objectives\n"
            "- Experimental design overview\n"
            "- Key methodological approaches\n"
            "- Any unique aspects of the study\n"
            "Provides context for understanding the data and its significance.",
            examples=[
                "Investigation of metabolic changes in human plasma samples "
                "from type 2 diabetes patients compared to healthy controls. "
                "Study includes both fasting and post-prandial measurements.",
                "Analysis of lipid profiles in brain tissue samples examining "
                "the relationship between specific lipid species and "
                "Alzheimer's disease progression.",
            ],
        ),
    ] = None
    contact: Annotated[
        Optional[List[Contact]],
        Field(
            description="Contact information for study personnel.\n\n"
            "Format\n"
            "- Name: `[first name] [initials] [last name]`\n"
            "- Multiple contacts numbered `[1-n]`\n\n"
            "Fields\n"
            "- Name of the contact person\n"
            "- Institutional affiliation\n"
            "- Email address",
            examples=[
                "MTD\tcontact[1]\t[MS,MS:1000586,contact name,John X Smith]",
                "MTD\tcontact[1]-affiliation\tUniversity of Somewhere",
                "MTD\tcontact[1]-email\tjohn.smith@university.edu",
            ],
        ),
    ] = None
    publication: Annotated[
        Optional[List[Publication]],
        Field(
            description="Associated research publications.\n\n"
            "Reference Format\n"
            "- PubMed IDs: prefix with `pubmed:`\n"
            "- DOIs: prefix with `doi:`\n"
            "- Multiple IDs: separate with `|`\n\n"
            "Multiple publications numbered `[1-n]`",
            examples=[
                "MTD\tpublication[1]\tdoi:10.1021/example.2023",
                "MTD\tpublication[2]\tpubmed:12345678|doi:10.1021/another.2023",
            ],
        ),
    ] = None
    uri: Annotated[
        Optional[List[Uri]],
        Field(
            description="A URI pointing to the file's source data "
            "(e.g., a MetaboLights records).",
        ),
    ] = None
    external_study_uri: Annotated[
        Optional[List[Uri]],
        Field(
            description="A URI pointing to an external file with more details "
            "about the study design (e.g., an ISA-TAB file).",
        ),
    ] = None
    instrument: Annotated[
        Optional[List[Instrument]],
        Field(
            description="Mass spectrometry instrument specifications.\n\n"
            "Each instrument includes:\n"
            "- `name`: Full instrument name and model\n"
            "- `source`: Ion source type (e.g., ESI, MALDI)\n"
            "- `analyzer`: Mass analyzer(s) used (e.g., quadrupole, TOF)\n"
            "- `detector`: Detector type\n\n"
            "Multiple instruments are numbered `[1-n]`. Referenced by `instrument_ref` in `ms_run` entries.",
            examples=[
                "MTD\tinstrument[1]-name\tThermo Fisher Q Exactive HF",
                "MTD\tinstrument[1]-source\t[MS,MS:1000073,ESI,]",
                "MTD\tinstrument[1]-analyzer[1]\t[MS,MS:1000084,TOF,]",
            ],
        ),
    ] = None
    quantification_method: Annotated[
        Parameter,
        Field(),
    ]
    sample: Annotated[
        Optional[List[Sample]],
        Field(
            description="Specification of sample. "
            "A name for each sample to serve as a list of the samples "
            "that MUST be reported in the following tables. "
            "Samples MUST be reported if a statistical design is being captured "
            "(i.e. bio or tech replicates). "
            "If the type of replicates are not known, samples SHOULD NOT be reported. "
            "species: The respective species of the samples analysed. "
            "For more complex cases, such as metagenomics, optional columns and userParams should be used."
            "tissue: The respective tissue(s) of the sample. "
            "cell_type: The respective cell type(s) of the sample. "
            "disease: The respective disease(s) of the sample. "
            "description: A human readable description of the sample. "
            "custom: Custom parameters describing the sample's additional properties. "
            "Dates MUST be provided in ISO-8601 format.",
        ),
    ] = None
    sample_processing: Annotated[
        Optional[List[SampleProcessing]],
        Field(
            description="Sample preparation and processing steps.\n\n"
            "Processing Documentation\n"
            "- Sequential steps numbered `[1-n]` in order of execution\n"
            "- Multiple parameters per step separated by `|`\n\n"
            "Special Cases\n"
            "- Derivatization:\n"
            "  - Report general step (e.g., 'silylation')\n"
            "  - Specify agents in derivatization_agent field\n\n"
            "Follows biological/analytical methods report format",
            examples=[
                "MTD\tsample_processing[1]\t[SEP,SEP:00142,extraction,]",
                "MTD\tsample_processing[2]\t[SEP,SEP:00210,centrifugation,]|[SEP,SEP:00211,13000g]",
                "MTD\tsample_processing[3]\t[MS,MS:1000085,silylation,]",
            ],
        ),
    ] = None
    software: Annotated[
        List[Software],
        Field(
            description="Analysis software specifications.\n\n"
            "For each software entry:\n"
            "- Include version information\n"
            "- Number entries (`[1-n]`) to reflect usage order\n"
            "- Settings can be specified multiple times per software\n"
            "- Use string values for settings without CV terms",
            examples=[
                "MTD\tsoftware[1]\t[MS,MS:1000532,Xcalibur,3.1]",
                "MTD\tsoftware[2]\t[MS,MS:1002342,MetaboScape,2022b]",
            ],
        ),
    ]
    derivatization_agent: Annotated[
        Optional[List[Parameter]],
        Field(
            description="A description of derivatization agents applied to small molecules, "
            "using userParams or CV terms where possible.",
        ),
    ] = None
    ms_run: Annotated[
        List[MsRun],
        Field(
            description="Specification of ms_run. "
            "location: Location of the external data file e.g. raw files on which analysis has been performed. "
            "If the actual location of the MS run is unknown, a “null” MUST be used as a place holder value, "
            "since the [1-n] cardinality is referenced elsewhere. If pre-fractionation has been performed, "
            "then [1-n] ms_runs SHOULD be created per assay."
            "instrument_ref: If different instruments are used in different runs, "
            "instrument_ref can be used to link a specific instrument to a specific run. "
            "format: Parameter specifying the data format of the external MS data file. "
            "If ms_run[1-n]-format is present, ms_run[1-n]-id_format SHOULD also be present, "
            "following the parameters specified in Table 1. "
            "id_format: Parameter specifying the id format used in the external data file. "
            "If ms_run[1-n]-id_format is present, ms_run[1-n]-format SHOULD also be present."
            "fragmentation_method: The type(s) of fragmentation used in a given ms run."
            "scan_polarity: The polarity mode of a given run. "
            "Usually only one value SHOULD be given here except for the case of mixed polarity runs."
            "hash: Hash value of the corresponding external MS data file defined in ms_run[1-n]-location. "
            "If ms_run[1-n]-hash is present, ms_run[1-n]-hash_method SHOULD also be present."
            "hash_method: A parameter specifying the hash methods used to generate the String in ms_run[1-n]-hash. "
            "Specifics of the hash method used MAY follow the definitions of the mzML format. "
            "If ms_run[1-n]-hash is present, ms_run[1-n]-hash_method SHOULD also be present.",
        ),
    ]
    assay: Annotated[
        List[Assay],
        Field(
            description="Specification of assay. "
            "(empty) name: A name for each assay, to serve as a list of the assays that MUST be "
            "reported in the following tables. "
            "custom: Additional custom parameters or values for a given assay. "
            "external_uri: An external reference uri to further information about the assay, "
            "for example via a reference to an object within an ISA-TAB file. "
            "sample_ref: An association from a given assay to the sample analysed. "
            "ms_run_ref: An association from a given assay to the source MS run. "
            "All assays MUST reference exactly one ms_run unless a workflow with pre-fractionation "
            "is being encoded, in which case each assay MUST reference n ms_runs where n fractions "
            "have been collected. "
            "Multiple assays SHOULD reference the same ms_run to capture multiplexed experimental designs.",
        ),
    ]
    study_variable: Annotated[
        List[StudyVariable],
        Field(
            description="Specification of study_variable. "
            "(empty) name: A name for each study variable (experimental condition or factor), "
            "to serve as a list of the study variables that MUST be reported in the following tables. "
            "For software that does not capture study variables, a single study variable MUST be reported, "
            "linking to all assays. This single study variable MUST have the identifier “undefined“. "
            "assay_refs: Bar-separated references to the IDs of assays grouped in the study variable. "
            "average_function: The function used to calculate the study variable quantification value "
            "and the operation used is not arithmetic mean (default) e.g. “geometric mean”, “median”. "
            "The 1-n refers to different study variables. "
            "variation_function: The function used to calculate the study variable quantification variation value "
            "if it is reported and the operation used is not coefficient of variation (default) e.g. "
            "“standard error”. description: A textual description of the study variable. "
            "factors: Additional parameters or factors, separated by bars, that are known "
            "about study variables allowing the capture of more complex, such as nested designs. ",
        ),
    ]
    custom: Annotated[
        Optional[List[Parameter]],
        Field(
            description="Any additional parameters describing the analysis reported.",
        ),
    ] = None
    cv: Annotated[
        List[CV],
        Field(
            description="Controlled vocabulary specifications.\n\n"
            "Fields\n"
            "- `label`: Short identifier (e.g., 'MS' for PSI-MS)\n"
            "- `full_name`: Complete ontology name\n"
            "- `version`: CV/ontology version\n"
            "- `uri`: Reference URI for the vocabulary",
            examples=[
                "MTD\tcv[1]-label\tMS",
                "MTD\tcv[1]-full_name\tPSI Mass Spectrometry Ontology",
                "MTD\tcv[1]-version\t4.1.0",
                "MTD\tcv[1]-uri\thttp://purl.obolibrary.org/obo/ms.obo",
            ],
        ),
    ]
    small_molecule_quantification_unit: Annotated[
        Parameter,
        Field(
            alias="small_molecule-quantification_unit",
        ),
    ]
    small_molecule_feature_quantification_unit: Annotated[
        Parameter,
        Field(
            alias="small_molecule_feature-quantification_unit",
        ),
    ]
    small_molecule_identification_reliability: Annotated[
        Optional[Parameter],
        Field(
            alias="small_molecule-identification_reliability",
        ),
    ] = None
    database: Annotated[
        List[Database],
        Field(
            description="Specification of databases. "
            "(empty): The description of databases used. "
            "For cases, where a known database has not been used for identification, "
            "a userParam SHOULD be inserted to describe any identification performed. "
            "e.g. de novo. "
            "If no identification has been performed at all then 'no database' "
            "should be inserted followed by null. prefix: The prefix used in the "
            "“identifier” column of data tables. For the 'no database' case 'null' must be used. "
            "version: The database version is mandatory where identification has been performed. "
            "This may be a formal version number e.g. “1.4.1”, "
            "a date of access “2016-10-27” (ISO-8601 format) or “Unknown” "
            "if there is no suitable version that can be annotated. "
            "uri: The URI to the database. "
            "For the 'no database' case, 'null' must be reported. ",
        ),
    ]
    id_confidence_measure: Annotated[
        List[Parameter],
        Field(
            description="Small molecule identification confidence metrics.\n\n"
            "Scoring System\n"
            "- Use CV parameters numbered `[1-n]`\n"
            "- Define score direction (high-to-low or low-to-high)\n"
            "- Order by importance for identification ranking\n\n"
            "Scores determine confidence in molecular identifications",
            examples=[
                "MTD\tid_confidence_measure[1]\t[MS,MS:1002890,fragmentation score,]",
                "MTD\tid_confidence_measure[2]\t[MS,MS:1002891,retention time score,]",
            ],
        ),
    ]
    colunit_small_molecule: Annotated[
        Optional[List[ColumnParameterMapping]],
        Field(
            alias="colunit-small_molecule",
            description="Unit definitions for small molecule data columns.\n\n"
            "Format\n"
            "- Pattern: `{column_name}={unit_parameter}`\n"
            "- Use CV parameters for units when possible\n\n"
            "Important Notes\n"
            "- Not for quantification columns\n"
            "- Use `small_molecule-quantification_unit` for quantification values",
            examples=[
                "MTD\tcolunit-small_molecule\tretention_time=[UO,UO:0000031,minute,]",
                "MTD\tcolunit-small_molecule\tmass=[UO,UO:0000221,dalton,]",
            ],
            json_schema_extra=MetadataSerialization(
                non_indexed_list_value=True,
            ).model_dump(exclude_unset=True, exclude_defaults=True),
        ),
    ] = None
    colunit_small_molecule_feature: Annotated[
        Optional[List[ColumnParameterMapping]],
        Field(
            alias="colunit-small_molecule_feature",
            description="Defines the used unit for a column in the small molecule feature section. "
            "The format of the value has to be {column name}={Parameter defining the unit}. "
            "This field MUST NOT be used to define a unit for quantification columns. "
            "The unit used for small molecule quantification values MUST be set "
            "in small_molecule_feature-quantification_unit.",
            json_schema_extra=MetadataSerialization(
                non_indexed_list_value=True,
            ).model_dump(exclude_unset=True, exclude_defaults=True),
        ),
    ] = None
    colunit_small_molecule_evidence: Annotated[
        Optional[List[ColumnParameterMapping]],
        Field(
            alias="colunit-small_molecule_evidence",
            description="Defines the used unit for a column in the small molecule evidence section. "
            "The format of the value has to be {column name}={Parameter defining the unit}.",
            json_schema_extra=MetadataSerialization(
                non_indexed_list_value=True,
            ).model_dump(exclude_unset=True, exclude_defaults=True),
        ),
    ] = None

    @classmethod
    def parse_metadata_line(cls, line: str) -> tuple[str, str]:
        """Parse a metadata line into key and value."""
        parts = line.split("\t", 2)
        if len(parts) < 3:
            return None, None
        key = parts[1]
        value = parts[2].strip()
        return key, value

    @classmethod
    def update_dict(cls, dict_info: MetadataDictInfo, item: dict[str, Any]):
        if not item:
            return
        if dict_info.object_level_value_field:
            item[dict_info.object_level_value_field] = item.get(None, None)
            if None in item:
                del item[None]
        for join_field, join_op in dict_info.list_concatenation_str_dict.items():
            if join_field in item:
                item[join_field] = item[join_field] or ""
                item[join_field] = [x.strip() for x in item[join_field].split(join_op)]
        for ref_field, ref in dict_info.referenced_field_names.items():
            if ref_field in item:
                val = item[ref_field]
                if isinstance(val, list):
                    new_val = []
                    for v in val:
                        ref_match = re.match(rf"\s*{ref}\[(\d+)\]\s*", v)
                        if ref_match:
                            new_val.append(int(ref_match.groups()[0]))
                    item[ref_field] = new_val
                else:
                    ref_match = re.match(rf"{ref}\[(\d+)\]", item[ref_field])
                    if ref_match:
                        item[ref_field] = int(ref_match.groups()[0])

    @classmethod
    def set_dict_value(
        cls,
        value,
        data_dict,
        field: str,
        field_index: Union[None, int],
        sub_field: str,
        sub_field_index: Union[None, int],
    ):
        if field not in data_dict:
            if field_index is not None:
                data_dict[field] = []
            else:
                data_dict[field] = OrderedDict()
        base_item = data_dict[field]
        if field_index is not None:
            i = len(data_dict[field])
            if i < field_index:
                while i < field_index:
                    data_dict[field].append(None)
                    i += 1
                data_dict[field][field_index - 1] = OrderedDict()
            base_item = data_dict[field][field_index - 1]

        if sub_field not in base_item:
            if sub_field_index is not None:
                base_item[sub_field] = []
            else:
                base_item[sub_field] = OrderedDict()
        if sub_field_index is not None:
            i = len(base_item[sub_field])
            while i < sub_field_index:
                base_item[sub_field].append(None)
                i += 1
            base_item[sub_field][sub_field_index - 1] = value
        else:
            base_item[sub_field] = value

    @classmethod
    def parse_metadata(cls, lines: List[str]) -> dict[str, Any]:
        """Parse metadata section of mzTab-M file."""
        pattern = re.compile(
            r"^(?P<field>[^\[\]]+)"
            r"(?:\[(?P<field_index>\d+)\])?"
            r"(?:-(?P<subfield>[^\[\]]+)"
            r"(?:\[(?P<subfield_index>\d+)\])?)?$"
        )

        metadata_dict = OrderedDict()
        for line in lines:
            if not line.startswith("MTD"):
                continue
            key, value = cls.parse_metadata_line(line)
            if not key:
                continue
            match = re.match(pattern, key)

            if match:
                parts = match.groups()
                field = parts[0]
                field_index = int(parts[1]) if parts[1] else None
                sub_field = parts[2]
                sub_field_index = int(parts[3]) if parts[3] else None
                cls.set_dict_value(
                    value=value,
                    data_dict=metadata_dict,
                    field=field,
                    field_index=field_index,
                    sub_field=sub_field,
                    sub_field_index=sub_field_index,
                )
            else:
                print(f"unexpected line '{key}'")

        return metadata_dict

    @model_validator(mode="wrap")
    @classmethod
    def validate_model(
        cls,
        input_data: Any,
        handler: ModelWrapValidatorHandler["Metadata"],
        info: ValidationInfo,
    ) -> "Metadata":
        if isinstance(input_data, Metadata):
            return handler(input_data)
        if isinstance(info.context, ValidationSummary):
            if info.context.source_format == "json":
                return handler(input_data)
        lines = []
        if isinstance(input_data, str):
            lines = input_data.split("\n")

        if isinstance(input_data, list) and isinstance(input_data[0], str):
            lines = input_data
            data = cls.parse_metadata(lines)
        elif isinstance(input_data, (dict, OrderedDict)):
            data = input_data

        for field, field_info in cls.model_fields.items():
            extra = field_info.json_schema_extra or {}
            json_extra = MetadataSerialization.model_validate(extra, by_alias=True)
            if json_extra.ignore:
                continue

            field_name = field_info.validation_alias or field
            val = data.get(field_name)
            is_list, field_type = get_field_type_info(cls, field)
            if not is_list:
                if issubclass(field_type, str):
                    str_val = val
                    if isinstance(val, (dict, OrderedDict)):
                        str_val = val.get(None)
                    data[field_name] = str_val
                elif issubclass(field_type, int):
                    int_val = val
                    if isinstance(val, (dict, OrderedDict)):
                        int_val = val.get(None)
                    ref_match = re.match(r"(.+)\[(\d+)\]")
                    if ref_match:
                        int_val = ref_match.groups(1)
                    data[field_name] = None if int_val is None else int(int_val)
                elif issubclass(field_type, MzTabBaseModel):
                    str_val = val
                    if isinstance(val, (dict, OrderedDict)):
                        str_val = val.get(None)
                    data[field_name] = field_type.model_validate(str_val, by_alias=True)
            else:
                if issubclass(field_type, int):
                    int_val = val
                    if isinstance(val, (dict, OrderedDict)):
                        int_val = val.get(None)
                    ref_match = re.match(r"(.+)\[(\d+)\]")
                    if ref_match:
                        int_val = ref_match.groups(1)
                    data[field_name] = None if int_val is None else int(int_val)
                if issubclass(field_type, SerializableModel):
                    new_list = []
                    dict_info = field_type.get_dict_info()
                    list_val = val or []
                    for item in list_val:
                        cls.update_dict(dict_info, item)

                        new_list.append(field_type.model_validate(item, by_alias=True))
                    if new_list:
                        data[field_name] = new_list

        return handler(data)

    @model_serializer(mode="wrap")
    def serialize_model(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> Union[str, dict[str, Any]]:
        default_success, result = self.serialize_to_json(handler, info)
        if default_success:
            return result
        lines = []
        self.serialize_object(self.prefix, "", self, lines)
        return "\n".join(lines)

    def serialize_object(
        self, section: str, prefix: str, model: MzTabBaseModel, lines: List[str]
    ):
        for field, field_info in model.__class__.model_fields.items():
            serializer_model = field_info.json_schema_extra
            if field_info.json_schema_extra is None:
                serializer_model = {}
            extra = MetadataSerialization.model_validate(serializer_model)
            if extra.ignore:
                continue
            value = getattr(model, field, None)
            alias = field_info.alias if field_info.alias else field
            key_name = alias
            if prefix:
                key_name = prefix if extra.object_level_value else f"{prefix}-{alias}"

            if value is None:
                continue
            elif isinstance(value, (str, AnyUrl)):
                line = f"{section}\t{key_name}\t{value or ''}"
                lines.append(line)
            elif isinstance(value, int):
                if value is None:
                    line = f"{section}\t{key_name}\t"
                elif extra.referenced_field_name:
                    ref = extra.referenced_field_name
                    line = f"{section}\t{key_name}\t{ref}[{value}]"
                else:
                    line = f"{section}\t{key_name}\t{value}"
                lines.append(line)
            elif isinstance(value, MzTabBaseModel):
                if isinstance(value, Parameter):
                    line_value = value.model_dump(by_alias=True)
                    line = f"{section}\t{key_name}\t{line_value or ''}"
                    lines.append(line)
                else:
                    self.serialize_object(section, key_name, value, lines)
            elif isinstance(value, list):
                if not value:
                    continue
                if isinstance(value[0], (str, AnyUrl)):
                    separator = extra.list_concatenation_str
                    if separator:
                        line_value = separator.join([str(x) for x in value])
                        line = f"{section}\t{key_name}\t{line_value}"
                    else:
                        for idx, item in enumerate(value, start=1):
                            indexed_key_name = f"{key_name}[{idx}]"
                            line = f"{section}\t{indexed_key_name}\t{item or ''}"
                            lines.append(line)
                elif isinstance(value[0], int):
                    separator = extra.list_concatenation_str or "|"
                    if extra.referenced_field_name:
                        values = [f"{extra.referenced_field_name}[{x}]" for x in value]
                        line_value = separator.join(values)
                        line = f"{section}\t{key_name}\t{line_value}"
                    else:
                        values = [str(x) for x in value if x is not None]
                        line = f"{section}\t{key_name}\t{separator.join(values)}"
                    lines.append(line)
                elif isinstance(value[0], MzTabBaseModel):
                    separator = extra.list_concatenation_str or None
                    if separator:
                        line_value = separator.join(
                            [x.model_dump(by_alias=True) for x in value]
                        )
                        line = f"{section}\t{key_name}\t{line_value or ''}"
                        lines.append(line)
                    else:
                        for idx, item in enumerate(value, start=1):
                            indexed_key_name = f"{key_name}[{idx}]"
                            if extra.non_indexed_list_value:
                                indexed_key_name = key_name
                            elif isinstance(item, IdentifiableModel):
                                id_val = item.get_id()
                                if id_val:
                                    indexed_key_name = f"{key_name}[{id_val}]"
                            if isinstance(item, Parameter):
                                line_value = item.model_dump(by_alias=True)
                                line = (
                                    f"{section}\t{indexed_key_name}\t{line_value or ''}"
                                )
                                lines.append(line)
                            else:
                                self.serialize_object(
                                    section, indexed_key_name, item, lines
                                )
                else:
                    print("not expected")

            else:
                print("Skipping unsupported value", key_name, extra)
