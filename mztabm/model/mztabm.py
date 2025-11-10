import re
from typing import (
    Annotated,
    Any,
    List,
    Optional,
    OrderedDict,
    Self,
)

from pydantic import (
    BaseModel,
    Field,
    ModelWrapValidatorHandler,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    ValidationError,
    ValidationInfo,
    model_serializer,
    model_validator,
)

from mztabm.model import IdentifiableModel, MzTabBaseModel
from mztabm.model.common import Comment
from mztabm.model.section.base_table_section import BaseTableSection
from mztabm.model.section.mtd import Metadata
from mztabm.model.section.sme import SmallMoleculeEvidence
from mztabm.model.section.smf import SmallMoleculeFeature
from mztabm.model.section.sml import SmallMoleculeSummary
from mztabm.model.validation import (
    Category,
    MessageType,
    ValidationMessage,
    ValidationSummary,
)


class MzTabM(MzTabBaseModel):
    metadata: Annotated[
        Metadata,
        Field(
            description="The metadata section contains general information about the mztab file content.",
        ),
    ]

    small_molecule_summary: Annotated[
        List[SmallMoleculeSummary],
        Field(
            alias="smallMoleculeSummary",
            description="The small molecule section is table-based. The small molecule section MUST always come after the metadata section. All table columns MUST be Tab separated. There MUST NOT be any empty cells; missing values MUST be reported using “null” for columns where Is Nullable = “True”.  Each row of the small molecule section is intended to report one final result to be communicated in terms of a molecule that has been quantified. In many cases, this may be the molecule of biological interest, although in some cases, the final result could be a derivatized form as appropriate – although it is desirable for the database identifier(s) to reference to the biological (non-derivatized) form. In general, different adduct forms would generally be reported in the Small Molecule Feature section.  The order of columns MUST follow the order specified below.  All columns are MANDATORY except for “opt_” columns. ",
            min_length=1,
        ),
    ] = []
    small_molecule_feature: Annotated[
        List[SmallMoleculeFeature],
        Field(
            alias="smallMoleculeFeature",
            description="The small molecule feature section is table-based, representing individual MS regions (generally considered to be the elution profile for all isotopomers formed from a single charge state of a molecule), that have been measured/quantified. However, for approaches that quantify individual isotopomers e.g. stable isotope labelling/flux studies, then each SMF row SHOULD represent a single isotopomer.  Different adducts or derivatives and different charge states of individual molecules should be reported as separate SMF rows.  The small molecule feature section MUST always come after the Small Molecule Table. All table columns MUST be Tab separated. There MUST NOT be any empty cells. Missing values MUST be reported using “null”.  The order of columns MUST follow the order specified below.  All columns are MANDATORY except for “opt_” columns. ",
        ),
    ] = []
    small_molecule_evidence: Annotated[
        List[SmallMoleculeEvidence],
        Field(
            alias="smallMoleculeEvidence",
            description="The small molecule evidence section is table-based, representing evidence for identifications of small molecules/features, from database search or any other process used to give putative identifications to molecules. In a typical case, each row represents one result from a single search or intepretation of a piece of evidence e.g. a database search with a fragmentation spectrum. Multiple results from a given input data item (e.g. one fragment spectrum) SHOULD share the same value under evidence_input_id.  The small molecule evidence section MUST always come after the Small Molecule Feature Table. All table columns MUST be Tab separated. There MUST NOT be any empty cells. Missing values MUST be reported using “null”.  The order of columns MUST follow the order specified below.  All columns are MANDATORY except for “opt_” columns. ",
        ),
    ] = []
    comment: Annotated[
        Optional[List[Comment]],
        Field(
            description="Comment lines can be placed anywhere in an mzTab file. These lines must start with the three-letter code COM and are ignored by most parsers. Empty lines can also occur anywhere in an mzTab file and are ignored. "
        ),
    ] = None

    @classmethod
    def parse_table_section(
        cls, lines: List[str], header_prefix: str, data_prefix: str
    ) -> List[dict[str, str]]:
        """Parse a table section (SML, SMF, or SME) of mzTab-M file."""
        headers = None
        data = []

        for line in lines:
            if line.startswith(header_prefix):
                headers = [x for x in line.split("\t")[1:] if x and x.strip()]
            elif line.startswith(data_prefix) and headers:
                values = [x for x in line.split("\t")[1:] if x and x.strip()]
                if len(values) == len(headers):
                    row = dict(zip(headers, values))
                    data.append(row)

        return data

    @classmethod
    def parse_table_header(cls, header: str) -> dict[str, Any]:
        if not header:
            return {}
        header = header or ""
        columns = header.strip().split("\t")
        column_map = {}
        for column in columns:
            if column.startswith("opt_"):
                optional_column_name = column.replace("opt_", "", 1)
                column_map[column] = (
                    "opt",
                    optional_column_name,
                )
            else:
                match = re.match(r"^\s*(.+)\s*\[\s*(\d+)\s*\]\s*$", column)
                if match:
                    column_name, index = match.groups()
                    column_map[column] = (column_name, int(index))
                else:
                    column_map[column] = (column, None)
        return column_map

    @classmethod
    def split_file_sections(cls, lines: list[str]) -> dict[str, list[str]]:
        all_section_headers = {"SEH", "SME", "SFH", "SMF", "SMH", "SML", "MTD", "COM"}
        section_order: dict[str, list[str]] = [
            ("MTD", [None, ("MTD", "COM"), ("SMH")]),
            ("SML", ["SMH", ("SMH", "SML", "COM"), ("SFH")]),
            ("SMF", ["SFH", ("SFH", "SMF", "COM"), ("SEH")]),
            ("SME", ["SEH", ("SEH", "SME", "COM"), None]),
        ]
        sections: dict[str, list[str]] = {"MTD": [], "SML": [], "SMF": [], "SME": []}
        current_section = 0
        for idx, line in enumerate(lines, start=1):
            sanitized = line.strip()
            if not sanitized:
                continue
            if len(sanitized) < 4:
                print(f"line error at {idx}: '{line}'")
                continue
            line_header = sanitized[:3]
            if line_header not in all_section_headers:
                print(f"line error at {idx}: '{line}'")
                continue
            section, config = section_order[current_section]
            start, includes, terminators = config

            if terminators and line_header in terminators:
                current_section += 1
                section, config = section_order[current_section]
                start, includes, terminators = config

            if line_header in includes:
                sections[section].append(line)
        return sections

    @model_serializer(mode="wrap")
    def serialize_model(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> str | dict[str, Any]:
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
        handler: ModelWrapValidatorHandler[Self],
        info: ValidationInfo,
    ) -> Self:
        if isinstance(data, MzTabM):
            return handler(data)
        if isinstance(info.context, ValidationSummary):
            if info.context.source_format == "json":
                return handler(data)

        if isinstance(data, (dict, OrderedDict)):
            mztabm = data
        else:
            mztabm = cls.parse_tsv_file(data)

        model = handler(mztabm)
        cls.update_ids(model)
        messages: list[ValidationMessage] = []
        if isinstance(info.context, ValidationSummary):
            messages = info.context.messages

        model.cross_check(messages)
        return model

    @classmethod
    def parse_tsv_file(cls, data: str | list[str]) -> OrderedDict[str, Any]:
        lines = data
        if isinstance(data, str):
            lines = data.split("\n")
        if not lines:
            raise ValidationError("input content is empty")
        if not isinstance(lines, list):
            raise ValidationError("input format is not valid")
        if not isinstance(lines[0], str):
            raise ValidationError(f"input data is not valid: {data[0].__class__}")
        sections = cls.split_file_sections(lines)
        mztabm = OrderedDict()
        mztabm["metadata"] = Metadata.parse_metadata(sections["MTD"])
        section_inputs = [
            (SmallMoleculeSummary, "small_molecule_summary", "SMH", "SML"),
            (SmallMoleculeFeature, "small_molecule_feature", "SFH", "SMF"),
            (SmallMoleculeEvidence, "small_molecule_evidence", "SEH", "SME"),
        ]
        for section_class, section, header_prefix, data_prefix in section_inputs:
            if sections[data_prefix]:
                summary_map = cls.parse_table_header(sections[data_prefix][0])
                summary_dict = cls.parse_table_section(
                    sections[data_prefix], header_prefix, data_prefix
                )

                field_info = cls.model_fields.get(section)
                field_name = field_info.validation_alias or section

                mztabm[field_name] = cls.update_table_dict(
                    section_class, summary_map, summary_dict
                )

        return mztabm

    def cross_check(self, messages: list[ValidationMessage]) -> list[ValidationMessage]:
        if messages is None:
            messages = []
        references = self._get_reference_dict(messages)

        reference_hits = self._check_referenced_items(references, messages)

        self._check_unreferenced_items(reference_hits, messages)
        return messages

    def _check_referenced_items(
        self, references: dict[str, dict[int, Any]], messages: list[ValidationMessage]
    ) -> dict[str, dict[int, int]]:
        reference_hits: dict[str, dict[int, int]] = {}
        for k, v in references.items():
            reference_hits[k] = {key: 0 for key in v.keys()}

        for section, field, subfield, referenced_field in [
            ("metadata", "ms_run", "instrument_ref", "instrument"),
            ("metadata", "assay", "sample_ref", "sample"),
            ("metadata", "assay", "ms_run_ref", "ms_run"),
            ("metadata", "study_variable", "assay_refs", "assay"),
            ("small_molecule_summary", None, "smf_id_refs", "small_molecule_feature"),
            ("small_molecule_feature", None, "sme_id_refs", "small_molecule_evidence"),
            ("small_molecule_evidence", "spectra_ref", "ms_run", "ms_run"),
        ]:
            section_data = getattr(self, section, {})
            if not section_data:
                continue
            target = section_data
            field_ref = section
            targets = []
            if not isinstance(section_data, list):
                field_ref = field
                target = getattr(section_data, field, None)
                if not target:
                    continue
                targets = [(None, target)]
            else:
                if field:
                    targets = [
                        (idx, getattr(x, field)) for idx, x in enumerate(section_data)
                    ]
                else:
                    targets = [(idx, x) for idx, x in enumerate(section_data)]

            for target_idx, target in targets:
                if isinstance(target, list):
                    for idx, list_item in enumerate(target):
                        field_ref_name = (
                            f"{field_ref}[{idx}]"
                            if target_idx is None
                            else f"{field}[{target_idx}] {field_ref}[{idx}]"
                        )
                        self._check_references(
                            references,
                            field_ref_name,
                            subfield,
                            referenced_field,
                            list_item,
                            reference_hits,
                            messages,
                        )
                elif target:
                    field_ref_name = (
                        f"{field_ref}"
                        if target_idx is None
                        else f"{field}[{target_idx}] {field_ref}"
                    )
                    if isinstance(target, tuple):
                        pass
                    self._check_references(
                        references,
                        field_ref_name,
                        subfield,
                        referenced_field,
                        target,
                        reference_hits,
                        messages,
                    )
        return reference_hits

    def _check_unreferenced_items(
        self,
        reference_hits: dict[str, dict[int, int]],
        messages: list[ValidationMessage],
    ):
        for k, v in reference_hits.items():
            for idx, hit in v.items():
                if hit < 1:
                    messages.append(
                        ValidationMessage(
                            category=Category.CROSS_CHECK,
                            message_type=MessageType.WARNING,
                            message=f"{k}[{idx}] is not referenced in the file",
                        )
                    )

    def _get_reference_dict(
        self, messages: list[ValidationMessage]
    ) -> dict[str, dict[int, Any]]:
        references: dict[str, dict[int, Any]] = {}

        for indexed_field in ["assay", "instrument", "sample", "ms_run"]:
            vals = getattr(self.metadata, indexed_field)
            if not vals:
                continue
            references[indexed_field] = {}
            for idx, item in enumerate(vals):
                if isinstance(item, IdentifiableModel):
                    references[indexed_field][item.id] = item
                    if item.id != idx + 1:
                        messages.append(
                            ValidationMessage(
                                category=Category.CROSS_CHECK,
                                message_type=MessageType.WARNING,
                                message=f"metadata {indexed_field} item at index {idx} "
                                f"has different id {item.id}",
                            )
                        )
                else:
                    messages.append(
                        ValidationMessage(
                            category=Category.CROSS_CHECK,
                            message_type=MessageType.WARNING,
                            message=f"metadata {indexed_field} item at index {idx} "
                            f"is not valid {str(item)}",
                        )
                    )

        for section, indexed_field in [
            ("small_molecule_evidence", "sme_id"),
            ("small_molecule_feature", "smf_id"),
        ]:
            references[section] = {}
            items = getattr(self, section)
            if not items:
                continue

            for item in items:
                val = getattr(item, indexed_field)
                references[section][val] = item
        return references

    @classmethod
    def _check_references(
        cls,
        references: dict[str, dict[int, Any]],
        field_ref: str,
        subfield: str,
        referenced_field: str,
        target: BaseModel,
        reference_hits: dict[str, dict[int, Any]],
        messages: list[ValidationMessage],
    ):
        subfield_vals = getattr(target, subfield)
        indexed_items = references.get(referenced_field, {})
        if isinstance(subfield_vals, list):
            for i, idx in enumerate(subfield_vals):
                if idx in indexed_items:
                    reference_hits[referenced_field][idx] += 1
                else:
                    messages.append(
                        ValidationMessage(
                            category=Category.CROSS_CHECK,
                            message_type=MessageType.WARNING,
                            message=f"{field_ref} -> {subfield}[{i}] value "
                            f"{referenced_field}[{idx}] is not defined.",
                        )
                    )
        elif isinstance(subfield_vals, int):
            idx = subfield_vals
            if idx in indexed_items:
                reference_hits[referenced_field][idx] += 1
            else:
                messages.append(
                    ValidationMessage(
                        category=Category.CROSS_CHECK,
                        message_type=MessageType.WARNING,
                        message=f"{field_ref} -> {subfield} value "
                        f"{referenced_field}[{idx}] is not defined ",
                    )
                )

    @classmethod
    def update_ids(cls, model: BaseModel, idx: None | int = None):
        if isinstance(model, IdentifiableModel):
            if idx is not None:
                model.id = idx
        for field in model.__class__.model_fields.keys():
            val = getattr(model, field)
            if isinstance(val, list):
                for id, item in enumerate(val, start=1):
                    if isinstance(item, BaseModel):
                        cls.update_ids(item, id)
            if isinstance(val, (dict, OrderedDict)):
                for _, v in val.items():
                    if isinstance(v, list):
                        for id, item in enumerate(v, start=1):
                            if isinstance(item, BaseModel):
                                cls.update_ids(item, id)
            elif isinstance(val, BaseModel):
                cls.update_ids(val, None)

    @classmethod
    def update_table_dict(
        cls,
        field_type: type[BaseTableSection],
        summary_headers,
        rows: list[OrderedDict[str, Any]],
    ):
        new_table = []
        table_info = field_type.get_table_info()

        for row in rows:
            new_row = OrderedDict()
            for item, val in row.items():
                header, idx = summary_headers.get(item)
                item_type = table_info.data_types.get(header, None)
                is_list = table_info.list_fields.get(header, None)
                join_op = table_info.list_concatenation_str_dict.get(header, None)
                new_cell_data = None
                if is_list:
                    if join_op:
                        new_cell_data = val if val and val != "null" else None
                        if new_cell_data:
                            new_cell_data = [
                                x if x and x != "null" else None
                                for x in val.split(join_op)
                            ]

                            if issubclass(item_type, int):
                                new_cell_data = [
                                    int(x) if x else None for x in new_cell_data
                                ]
                            elif issubclass(item_type, float):
                                new_cell_data = [
                                    float(x) if x else None for x in new_cell_data
                                ]
                    else:
                        if issubclass(item_type, MzTabBaseModel):
                            new_cell_data = None
                            if val and val != "null":
                                new_cell_data = val

                        elif issubclass(item_type, int):
                            new_cell_data = [
                                int(val) if val and val != "null" else None
                            ]
                        elif issubclass(item_type, float):
                            new_cell_data = [
                                float(val) if val and val != "null" else None
                            ]
                        else:
                            new_cell_data = [val]
                else:
                    if issubclass(item_type, MzTabBaseModel):
                        new_cell_data = None
                        if val and val != "null":
                            new_cell_data = val
                    elif issubclass(item_type, int):
                        new_cell_data = int(val) if val and val != "null" else None
                    elif issubclass(item_type, float):
                        new_cell_data = None
                        if val and val.lower() != "null":
                            new_cell_data = (
                                float(val) if val.lower() != "nan" else float("nan")
                            )
                    else:
                        if val and val.lower() != "null":
                            new_cell_data = val
                        else:
                            new_cell_data = None

                if new_cell_data:
                    new_header, index = summary_headers[item]

                    if index is None:
                        new_row[new_header] = new_cell_data
                    elif isinstance(index, int):
                        if new_header not in new_row:
                            new_row[new_header] = []
                        i = len(new_row[new_header])
                        if i < index:
                            while i < index:
                                i += 1
                                new_row[new_header].append(None)
                        if not new_cell_data:
                            new_row[new_header][index - 1] = None
                        if isinstance(new_cell_data, list):
                            new_row[new_header][index - 1] = new_cell_data[0]
                        else:
                            new_row[new_header][index - 1] = new_cell_data
                    else:
                        if new_header not in new_row:
                            new_row[new_header] = []
                        new_row[new_header].append(
                            {
                                table_info.column_name_fields.get(header): index,
                                table_info.column_value_fields.get(
                                    header
                                ): new_cell_data,
                            }
                        )

            new_table.append(new_row)
        return new_table
