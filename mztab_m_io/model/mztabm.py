import json
import pathlib
from functools import partial

import yaml
from pydantic import Field
from typing_extensions import Annotated, Any, Callable, List, Literal, Optional, Tuple

from mztab_m_io.model.common import Comment
from mztab_m_io.model.mztabm_parser_utils import parse_tsv_file, update_ids
from mztab_m_io.model.mztabm_validation import check_validation_policies, cross_check
from mztab_m_io.model.section.mtd import Metadata
from mztab_m_io.model.section.sme import SmallMoleculeEvidence
from mztab_m_io.model.section.smf import SmallMoleculeFeature
from mztab_m_io.model.section.sml import SmallMoleculeSummary
from mztab_m_io.model.serialization import (
    CustomSerializer,
    MetadataSerialization,
    MzTabSerializableModel,
    SerializationContext,
    ValidationPolicy,
)
from mztab_m_io.model.validation import (
    Category,
    MessageType,
    MzTabMessage,
    ValidationContext,
)


class MzTabM(MzTabSerializableModel, CustomSerializer):
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
        Optional[List[SmallMoleculeSummary]],
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
        Optional[List[SmallMoleculeEvidence]],
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

    def to_tsv(self, context: SerializationContext) -> str:
        plain = [self.metadata.to_tsv(context)]
        plain.extend([x.to_tsv(context) for x in self.comment or []])
        plain.append("\n")
        plain.append(SmallMoleculeSummary.get_table_header(self.small_molecule_summary))
        plain.extend([x.to_tsv(context) for x in self.small_molecule_summary or []])
        plain.append("\n")
        plain.append(SmallMoleculeFeature.get_table_header(self.small_molecule_feature))
        plain.extend([x.to_tsv(context) for x in self.small_molecule_feature or []])
        plain.append("\n")
        plain.append(
            SmallMoleculeEvidence.get_table_header(self.small_molecule_evidence)
        )
        plain.extend([x.to_tsv(context) for x in self.small_molecule_evidence or []])
        errors = [x for x in context.messages if x.message_type == MessageType.ERROR]
        if not errors:
            context.success = True
        return "\n".join(plain) + "\n"

    @classmethod
    def post_process_model(cls, model: "MzTabM", context: ValidationContext):
        update_ids(model)
        cross_check(model, context.messages)
        check_validation_policies([], model, context.messages)

    @classmethod
    def from_dict(
        cls,
        data: dict,
        context: Optional[ValidationContext] = None,
        source_format: Literal["tsv", "json", "yaml"] = "json",
    ) -> Tuple["MzTabM", ValidationContext]:
        if not context:
            context = ValidationContext(source_format=source_format, messages=[])
        model = cls.model_validate(data, context=context, by_alias=True)
        cls.post_process_model(model, context)
        return model, context

    @classmethod
    def from_tsv_file(
        cls, io: Any, context: Optional[ValidationContext] = None
    ) -> Tuple["MzTabM", ValidationContext]:
        return cls._from_file(
            io,
            loader=partial(MzTabM._tsv_file_loader, context=context),
            source_format="tsv",
            context=context,
        )

    @classmethod
    def from_json_file(
        cls, io: Any, context: Optional[ValidationContext] = None
    ) -> Tuple["MzTabM", ValidationContext]:
        return cls._from_file(
            io,
            loader=json.load,
            source_format="json",
            context=context,
        )

    @classmethod
    def from_yaml_file(
        cls, io: Any, context: Optional[ValidationContext] = None
    ) -> Tuple["MzTabM", ValidationContext]:
        return cls._from_file(
            io,
            loader=yaml.safe_load,
            source_format="yaml",
            context=context,
        )

    def save(
        self, file_path: str, format: Literal["tsv", "json", "yaml"] = "tsv"
    ) -> SerializationContext:
        if not format:
            format = "tsv"
        serializers = {
            "tsv": self.to_tsv,
            "json": self.to_json,
            "yaml": self.to_yaml,
        }
        return self._to_file(file_path, serializers[format], format)

    def to_yaml_file(
        self, io: Any, context: Optional[SerializationContext] = None
    ) -> SerializationContext:
        return self._to_file(io, self.to_yaml, "yaml", context)

    def to_json_file(
        self, io: Any, context: Optional[SerializationContext] = None
    ) -> SerializationContext:
        return self._to_file(io, self.to_json, "json", context)

    def to_tsv_file(
        self, io: Any, context: Optional[SerializationContext] = None
    ) -> SerializationContext:
        return self._to_file(io, self.to_tsv, "tsv", context)

    @staticmethod
    def _to_file(
        file_path: str,
        serializer: Callable[[Any], Any],
        source_format: Literal["tsv", "json", "yaml"] = "json",
        context: Optional[SerializationContext] = None,
    ) -> SerializationContext:
        if not context:
            context = SerializationContext(source_format=source_format, messages=[])
        try:
            with open(file_path, "w") as f:
                f.write(serializer(context))
            context.success = True
        except Exception as e:
            context.success = False
            context.messages.append(
                MzTabMessage(
                    message_type=MessageType.ERROR,
                    category=Category.FORMAT,
                    source="output file",
                    message=str(e),
                )
            )
        return context

    @staticmethod
    def _tsv_file_loader(io: Any, context: Optional[ValidationContext] = None) -> str:
        if isinstance(io, pathlib.Path):
            content = io.read_text()
        elif hasattr(io, "read"):
            content = io.read()
        elif isinstance(io, str) and len(io) < 1024 and "\n" not in io:
            p = pathlib.Path(io)
            if p.exists() and p.is_file():
                content = p.read_text()

        return parse_tsv_file(MzTabM, content, context=context)

    @classmethod
    def _from_file(
        cls,
        io: Any,
        loader: Callable[[Any], Any],
        source_format: Literal["tsv", "json", "yaml"] = "json",
        context: Optional[ValidationContext] = None,
    ) -> Tuple["MzTabM", ValidationContext]:
        if not context:
            context = ValidationContext(source_format=source_format, messages=[])

        try:
            if hasattr(io, "read"):
                data = loader(io)
            else:
                with open(io) as f:
                    data = loader(f)
            model, context = cls.from_dict(
                data,
                context=context,
                source_format=source_format,
            )
            return model, context
        except Exception as e:
            context.messages.append(
                MzTabMessage(
                    message_type=MessageType.ERROR,
                    category=Category.FORMAT,
                    source="input file",
                    message=str(e),
                )
            )
            return None, context
