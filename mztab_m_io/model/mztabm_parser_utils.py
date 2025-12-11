import re
from typing_extensions import Any, List, OrderedDict, Union, Type, Dict

from pydantic import BaseModel, ValidationError

from mztab_m_io.model import IdentifiableModel, MzTabBaseModel
from mztab_m_io.model.section.base_table_section import BaseTableSection
from mztab_m_io.model.section.mtd import Metadata
from mztab_m_io.model.section.sme import SmallMoleculeEvidence
from mztab_m_io.model.section.smf import SmallMoleculeFeature
from mztab_m_io.model.section.sml import SmallMoleculeSummary


def parse_table_section(
    lines: List[str], header_prefix: str, data_prefix: str
) -> List[Dict[str, str]]:
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


def parse_table_header(header: str) -> Dict[str, Any]:
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


def split_file_sections(lines: List[str]) -> Dict[str, List[str]]:
    all_section_headers = {"SEH", "SME", "SFH", "SMF", "SMH", "SML", "MTD", "COM"}
    section_order: Dict[str, List[str]] = [
        ("MTD", [None, ("MTD", "COM"), ("SMH")]),
        ("SML", ["SMH", ("SMH", "SML", "COM"), ("SFH")]),
        ("SMF", ["SFH", ("SFH", "SMF", "COM"), ("SEH")]),
        ("SME", ["SEH", ("SEH", "SME", "COM"), None]),
    ]
    sections: Dict[str, List[str]] = {"MTD": [], "SML": [], "SMF": [], "SME": []}
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
        _, includes, terminators = config

        if terminators and line_header in terminators:
            current_section += 1
            section, config = section_order[current_section]
            _, includes, terminators = config

        if line_header in includes:
            sections[section].append(line)
    return sections


def update_table_dict(
    field_type: Type[BaseTableSection],
    summary_headers,
    rows: List[OrderedDict[str, Any]],
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
                            x if x and x != "null" else None for x in val.split(join_op)
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
                        new_cell_data = [int(val) if val and val != "null" else None]
                    elif issubclass(item_type, float):
                        new_cell_data = [float(val) if val and val != "null" else None]
                    else:
                        new_cell_data = [val]
            else:
                if issubclass(item_type, MzTabBaseModel):
                    new_cell_data = None
                    if val and val != "null":
                        new_cell_data = val
                elif issubclass(item_type, int):
                    new_cell_data = (
                        int(val) if val is not None and val != "null" else None
                    )
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

            if new_cell_data is not None:
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
                            table_info.column_value_fields.get(header): new_cell_data,
                        }
                    )

        new_table.append(new_row)
    return new_table


def update_ids(model: BaseModel, idx: Union[None, int] = None):
    if isinstance(model, IdentifiableModel):
        if idx is not None:
            model.id = idx
    for field in model.__class__.model_fields.keys():
        val = getattr(model, field)
        if isinstance(val, list):
            for id, item in enumerate(val, start=1):
                if isinstance(item, BaseModel):
                    update_ids(item, id)
        if isinstance(val, (dict, OrderedDict)):
            for _, v in val.items():
                if isinstance(v, list):
                    for id, item in enumerate(v, start=1):
                        if isinstance(item, BaseModel):
                            update_ids(item, id)
        elif isinstance(val, BaseModel):
            update_ids(val, None)


def parse_tsv_file(
    model_class: Type[BaseModel], data: Union[str, List[str]]
) -> OrderedDict[str, Any]:
    lines = data
    if isinstance(data, str):
        lines = data.split("\n")
    if not lines:
        raise ValidationError("input content is empty")
    if not isinstance(lines, list):
        raise ValidationError("input format is not valid")
    if not isinstance(lines[0], str):
        raise ValidationError(f"input data is not valid: {data[0].__class__}")
    sections = split_file_sections(lines)
    mztabm = OrderedDict()
    mztabm["metadata"] = Metadata.parse_metadata(sections["MTD"])
    section_inputs = [
        (SmallMoleculeSummary, "small_molecule_summary", "SMH", "SML"),
        (SmallMoleculeFeature, "small_molecule_feature", "SFH", "SMF"),
        (SmallMoleculeEvidence, "small_molecule_evidence", "SEH", "SME"),
    ]
    for section_class, section, header_prefix, data_prefix in section_inputs:
        if sections[data_prefix]:
            summary_map = parse_table_header(sections[data_prefix][0])
            summary_dict = parse_table_section(
                sections[data_prefix], header_prefix, data_prefix
            )

            field_info = model_class.model_fields.get(section)
            field_name = field_info.validation_alias or section

            mztabm[field_name] = update_table_dict(
                section_class, summary_map, summary_dict
            )

    return mztabm
