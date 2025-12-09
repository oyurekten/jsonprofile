from typing import (
    Annotated,
    List,
    Literal,
    Optional,
)

from pydantic import Field

from mztab_m_io.model.common import Comment, OptColumnMapping, Parameter
from mztab_m_io.model.section.base_table_section import BaseTableSection
from mztab_m_io.model.serialization import TableSerialization


class SmallMoleculeFeature(BaseTableSection):
    prefix: Annotated[
        Optional[Literal["SMF"]],
        Field(
            description="The small molecule feature table row prefix. SMF MUST be used for rows of the small molecule feature table.",
            json_schema_extra=TableSerialization(ignore=True).model_dump(
                exclude_unset=True, exclude_defaults=True
            ),
        ),
    ] = "SMF"
    header_prefix: Annotated[
        Literal["SFH"],
        Field(
            description="The small molecule feature table header prefix. SFH MUST be used for the small molecule feature table header line (the column labels).",
            json_schema_extra=TableSerialization(ignore=True).model_dump(
                exclude_unset=True, exclude_defaults=True
            ),
        ),
    ] = "SFH"
    smf_id: Annotated[
        int,
        Field(
            alias="SMF_ID",
            description="A within file unique identifier for the small molecule feature.",
        ),
    ]
    sme_id_refs: Annotated[
        Optional[List[int]],
        Field(
            alias="SME_ID_REFS",
            description="References to the identification evidence (SME elements) via referencing SME_ID values. Multiple values MAY be provided as a “|” separated list to indicate ambiguity in the identification or to indicate that different types of data supported the identifiction (see SME_ID_REF_ambiguity_code). For the case of a consensus approach where multiple adduct forms are used to infer the SML ID, different features should just reference the same SME_ID value(s).",
            json_schema_extra=TableSerialization(list_concatenation_str="|").model_dump(
                exclude_unset=True, exclude_defaults=True
            ),
        ),
    ] = None
    sme_id_ref_ambiguity_code: Annotated[
        Optional[int],
        Field(
            alias="SME_ID_REF_ambiguity_code",
            description="If multiple values are given under SME_ID_REFS, one of the following codes MUST be provided. 1=Ambiguous identification; 2=Only different evidence streams for the same molecule with no ambiguity; 3=Both ambiguous identification and multiple evidence streams. If there are no or one value under SME_ID_REFs, this MUST be reported as null.",
        ),
    ] = None
    adduct_ion: Annotated[
        Optional[str],
        Field(
            description="The assumed classification of this molecule's adduct ion after detection, following the general style in the 2013 IUPAC recommendations on terms relating to MS e.g. [M+H]1+, [M+Na]1+, [M+NH4]1+, [M-H]1-, [M+Cl]1-, [M+H]1+.",
            pattern=r"^\[\d*M([+-][\w\d]+)*\]\d*[+-]$",
        ),
    ] = None
    isotopomer: Optional[Parameter] = None
    exp_mass_to_charge: Annotated[
        float,
        Field(
            description="The experimental mass/charge value for the feature, by default assumed to be the mean across assays or a representative value. For approaches that report isotopomers as SMF rows, then the m/z of the isotopomer MUST be reported here."
        ),
    ]
    charge: Annotated[
        int,
        Field(
            description="The feature's charge value using positive integers both for positive and negative polarity modes."
        ),
    ]
    retention_time_in_seconds: Annotated[
        Optional[float],
        Field(
            description="The apex of the feature on the retention time axis, in a Master or aggregate MS run. Retention time MUST be reported in seconds. Retention time values for individual MS runs (i.e. before alignment) MAY be reported as optional columns. Retention time SHOULD only be null in the case of direct infusion MS or other techniques where a retention time value is absent or unknown. Relative retention time or retention time index values MAY be reported as optional columns, and could be considered for inclusion in future versions of mzTab as appropriate."
        ),
    ] = None
    retention_time_in_seconds_start: Annotated[
        Optional[float],
        Field(
            description="The start time of the feature on the retention time axis, in a Master or aggregate MS run. Retention time MUST be reported in seconds. Retention time start and end SHOULD only be null in the case of direct infusion MS or other techniques where a retention time value is absent or unknown and MAY be reported in optional columns."
        ),
    ] = None
    retention_time_in_seconds_end: Annotated[
        Optional[float],
        Field(
            description="The end time of the feature on the retention time axis, in a Master or aggregate MS run. Retention time MUST be reported in seconds. Retention time start and end SHOULD only be null in the case of direct infusion MS or other techniques where a retention time value is absent or unknown and MAY be reported in optional columns.."
        ),
    ] = None
    abundance_assay: Annotated[
        Optional[List[Optional[float]]],
        Field(
            description="The feature's abundance in every assay described in the metadata section MUST be reported. Null or zero values may be reported as appropriate.",
            json_schema_extra=TableSerialization(multiple_columns=True).model_dump(
                exclude_unset=True, exclude_defaults=True
            ),
        ),
    ] = None
    opt: Annotated[
        Optional[List[OptColumnMapping]],
        Field(
            description="Additional columns can be added to the end of the small molecule feature table. These column headers MUST start with the prefix “opt_” followed by the {identifier} of the object they reference: assay, study variable, MS run or “global” (if the value relates to all replicates). Column names MUST only contain the following characters: ‘A'-‘Z', ‘a'-‘z', ‘0'-‘9', ‘', ‘-', ‘[', ‘]', and ‘:'. CV parameter accessions MAY be used for optional columns following the format: opt{identifier}_cv_{accession}_parameter name}. Spaces within the parameter's name MUST be replaced by ‘_'. ",
            json_schema_extra=TableSerialization(
                multiple_columns=True,
                column_name_field="identifier",
                column_value_field="value",
            ).model_dump(exclude_unset=True, exclude_defaults=True),
        ),
    ] = None
    comment: Annotated[
        Optional[List[Comment]],
        Field(
            description="",
            json_schema_extra=TableSerialization(ignore=True).model_dump(
                exclude_unset=True, exclude_defaults=True
            ),
        ),
    ] = None
