from typing_extensions import Annotated, Any, List, Optional, OrderedDict, Union, Dict

from pydantic import (
    Field,
    ModelWrapValidatorHandler,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    ValidationInfo,
    model_serializer,
    model_validator,
)

from mztab_m_io.model import MzTabBaseModel
from mztab_m_io.model.common import Comment
from mztab_m_io.model.mztabm_parser_utils import parse_tsv_file, update_ids
from mztab_m_io.model.mztabm_validation import check_validation_policies, cross_check
from mztab_m_io.model.section.mtd import Metadata
from mztab_m_io.model.section.sme import SmallMoleculeEvidence
from mztab_m_io.model.section.smf import SmallMoleculeFeature
from mztab_m_io.model.section.sml import SmallMoleculeSummary
from mztab_m_io.model.serialization import (
    MetadataSerialization,
    ValidationPolicy,
)
from mztab_m_io.model.validation import (
    ValidationMessage,
    ValidationSummary,
)


class MzTabM(MzTabBaseModel):
    metadata: Annotated[
        Optional[Metadata],
        Field(
            description="The metadata section contains general information "
            "about the mztab file content.",
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(required=True)
            ).model_dump(),
        ),
    ] = None

    small_molecule_summary: Annotated[
        List[SmallMoleculeSummary],
        Field(
            alias="smallMoleculeSummary",
            description="The small molecule section is table-based. "
            "The small molecule section MUST always come after the metadata section. "
            "All table columns MUST be Tab separated. "
            "There MUST NOT be any empty cells; missing values MUST "
            "be reported using “null” for columns where Is Nullable = “True”.  "
            "Each row of the small molecule section is intended to report one final "
            "result to be communicated in terms of a molecule that has been quantified. "
            "In many cases, this may be the molecule of biological interest, "
            "although in some cases, the final result could be a derivatized form "
            "as appropriate - although it is desirable for the database identifier(s) "
            "to reference to the biological (non-derivatized) form. "
            "In general, different adduct forms would generally be reported "
            "in the Small Molecule Feature section.  "
            "The order of columns MUST follow the order specified below.  "
            "All columns are MANDATORY except for “opt_” columns. ",
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(
                    required=True, minimum=1, enforcement_level="recommended"
                )
            ).model_dump(),
        ),
    ] = None
    small_molecule_feature: Annotated[
        Optional[List[SmallMoleculeFeature]],
        Field(
            alias="smallMoleculeFeature",
            description="The small molecule feature section is table-based, "
            "representing individual MS regions (generally considered "
            "to be the elution profile for all isotopomers formed "
            "from a single charge state of a molecule), "
            "that have been measured/quantified. "
            "However, for approaches that quantify individual isotopomers "
            "e.g. stable isotope labelling/flux studies, "
            "then each SMF row SHOULD represent a single isotopomer. "
            "Different adducts or derivatives and different charge states "
            "of individual molecules should be reported as separate SMF rows. "
            "The small molecule feature section MUST always come after "
            "the Small Molecule Table. All table columns MUST be Tab separated. "
            "There MUST NOT be any empty cells. Missing values MUST be reported using “null”.  "
            "The order of columns MUST follow the order specified below.  "
            "All columns are MANDATORY except for “opt_” columns. ",
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(
                    required=True, minimum=1, enforcement_level="recommended"
                )
            ).model_dump(),
        ),
    ] = None
    small_molecule_evidence: Annotated[
        List[SmallMoleculeEvidence],
        Field(
            alias="smallMoleculeEvidence",
            description="The small molecule evidence section is table-based, "
            "representing evidence for identifications of small molecules/features, "
            "from database search or any other process used to give putative identifications "
            "to molecules. In a typical case, each row represents one result "
            "from a single search or interpretation of a piece of evidence "
            "e.g. a database search with a fragmentation spectrum. "
            "Multiple results from a given input data item (e.g. one fragment spectrum) "
            "SHOULD share the same value under evidence_input_id.  "
            "The small molecule evidence section MUST always come after "
            "the Small Molecule Feature Table. All table columns MUST be Tab separated. "
            "There MUST NOT be any empty cells. Missing values MUST be reported using “null”.  "
            "The order of columns MUST follow the order specified below.  "
            "All columns are MANDATORY except for “opt_” columns. ",
            json_schema_extra=MetadataSerialization(
                validation_policy=ValidationPolicy(
                    required=True, minimum=1, enforcement_level="recommended"
                )
            ).model_dump(),
        ),
    ] = None
    comment: Annotated[
        Optional[List[Comment]],
        Field(
            description="Comment lines can be placed anywhere in an mzTab file. "
            "These lines must start with the three-letter code COM and are "
            "ignored by most parsers. Empty lines can also occur "
            "anywhere in an mzTab file and are ignored. ",
            json_schema_extra=MetadataSerialization().model_dump(),
        ),
    ] = None

    @model_serializer(mode="wrap")
    def serialize_model(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> Union[str, Dict[str, Any]]:
        default_success, result = self.serialize_to_json(handler, info)
        if default_success:
            return result
        summary = [x.model_dump(by_alias=True) for x in self.small_molecule_summary]
        feature = [x.model_dump(by_alias=True) for x in self.small_molecule_feature]
        evidence = [x.model_dump(by_alias=True) for x in self.small_molecule_evidence]
        plain = [
            self.metadata.model_dump(),
            "\n",
            SmallMoleculeSummary.get_table_header(self.small_molecule_summary),
        ]
        plain.extend(summary)
        plain.append(SmallMoleculeFeature.get_table_header(self.small_molecule_feature))
        plain.extend(feature)
        plain.append(
            SmallMoleculeEvidence.get_table_header(self.small_molecule_evidence),
        )
        plain.extend(evidence)
        return "\n".join(plain)

    @model_validator(mode="wrap")
    @classmethod
    def validate_model(
        cls,
        data: Any,
        handler: ModelWrapValidatorHandler["MzTabM"],
        info: ValidationInfo,
    ) -> "MzTabM":
        if isinstance(data, MzTabM):
            return handler(data)
        if isinstance(info.context, ValidationSummary):
            if info.context.source_format == "json":
                return handler(data)

        if isinstance(data, (dict, OrderedDict)):
            mztabm = data
        else:
            mztabm = parse_tsv_file(cls, data)

        model = handler(mztabm)
        update_ids(model)
        messages: List[ValidationMessage] = []
        if isinstance(info.context, ValidationSummary):
            messages = info.context.messages

        cross_check(model, messages)
        check_validation_policies([], model, messages)
        return model
