from typing import (
    Annotated,
    List,
    Literal,
    Optional,
)

from pydantic import AnyUrl, Field

from mztabm.model.common import Comment, OptColumnMapping, Parameter, SpectraRef
from mztabm.model.section.base_table_section import BaseTableSection
from mztabm.model.serialization import TableSerialization


class SmallMoleculeEvidence(BaseTableSection):
    prefix: Annotated[
        Literal["SME"],
        Field(
            description="The small molecule evidence table row prefix. SME MUST be used for rows of the small molecule evidence table.",
            json_schema_extra=TableSerialization(ignore=True).model_dump(
                exclude_unset=True, exclude_defaults=True
            ),
        ),
    ] = "SME"
    header_prefix: Annotated[
        Literal["SEH"],
        Field(
            description="The small molecule evidence table header prefix. SEH MUST be used for the small molecule evidence table header line (the column labels).",
            json_schema_extra=TableSerialization(ignore=True).model_dump(
                exclude_unset=True, exclude_defaults=True
            ),
        ),
    ] = "SEH"
    sme_id: Annotated[
        int,
        Field(
            alias="SME_ID",
            description="A within file unique identifier for the small molecule evidence result.",
        ),
    ]
    evidence_input_id: Annotated[
        str,
        Field(
            description="A within file unique identifier for the input data used to support this identification e.g. fragment spectrum, RT and m/z pair, isotope profile that was used for the identification process, to serve as a grouping mechanism, whereby multiple rows of results from the same input data share the same ID. The identifiers may be human readable but should not be assumed to be interpretable. For example, if fragmentation spectra have been searched then the ID may be the spectrum reference, or for accurate mass search, the ms_run[2]:458.75."
        ),
    ]
    database_identifier: Annotated[
        str,
        Field(
            description="The putative identification for the small molecule sourced from an external database, using the same prefix specified in database[1-n]-prefix.  This could include additionally a chemical class or an identifier to a spectral library entity, even if its actual identity is unknown.  For the “no database” case, 'null' must be used. The unprefixed use of 'null' is prohibited for any other case. If no putative identification can be reported for a particular database, it MUST be reported as the database prefix followed by null."
        ),
    ]
    chemical_formula: Annotated[
        Optional[str],
        Field(
            description="The chemical formula of the identified compound e.g. in a database, assumed to match the theoretical mass to charge (in some cases this will be the derivatized form, including adducts and protons).  This should be specified in Hill notation (EA Hill 1900), i.e. elements in the order C, H and then alphabetically all other elements. Counts of one may be omitted. Elements should be capitalized properly to avoid confusion (e.g., “CO” vs. “Co”). The chemical formula reported should refer to the neutral form. Charge state is reported by the charge field.  Example N-acetylglucosamine would be encoded by the string “C8H15NO6” "
        ),
    ] = None
    smiles: Annotated[
        Optional[str],
        Field(
            description="The potential molecule's structure in the simplified molecular-input line-entry system (SMILES) for the small molecule."
        ),
    ] = None
    inchi: Annotated[
        Optional[str],
        Field(
            description="A standard IUPAC International Chemical Identifier (InChI) for the given substance."
        ),
    ] = None
    chemical_name: Annotated[
        Optional[str],
        Field(
            description="The small molecule's chemical/common name, or general description if a chemical name is unavailable."
        ),
    ] = None
    uri: Annotated[
        Optional[AnyUrl],
        Field(
            description="A URI pointing to the small molecule's entry in a database (e.g., the small molecule's HMDB, Chebi or KEGG entry)."
        ),
    ] = None
    derivatized_form: Optional[Parameter] = None
    adduct_ion: Annotated[
        Optional[str],
        Field(
            description="The assumed classification of this molecule's adduct ion after detection, following the general style in the 2013 IUPAC recommendations on terms relating to MS e.g. [M+H]+, [M+Na]1+, [M+NH4]1+, [M-H]1-, [M+Cl]1-. If the adduct classification is ambiguous with regards to identification evidence it MAY be null.",
            pattern=r"^\[\d*M([+-][\w\d]+)*\]\d*[+-]$",
        ),
    ] = None
    exp_mass_to_charge: Annotated[
        float,
        Field(
            description="The experimental mass/charge value for the precursor ion. If multiple adduct forms have been combined into a single identification event/search, then a single value e.g. for the protonated form SHOULD be reported here."
        ),
    ]
    charge: Annotated[
        int,
        Field(
            description="The small molecule evidence's charge value using positive integers both for positive and negative polarity modes."
        ),
    ]
    theoretical_mass_to_charge: Annotated[
        float,
        Field(
            description="The theoretical mass/charge value for the small molecule or the database mass/charge value (for a spectral library match)."
        ),
    ]
    spectra_ref: Annotated[
        List[SpectraRef],
        Field(
            description="Reference to a spectrum in a spectrum file, for example a fragmentation spectrum has been used to support the identification. If a separate spectrum file has been used for fragmentation spectrum, this MUST be reported in the metadata section as additional ms_runs. The reference must be in the format ms_run[1-n]:{SPECTRA_REF} where SPECTRA_REF MUST follow the format defined in 5.2 (including references to chromatograms where these are used to inform identification). Multiple spectra MUST be referenced using a “|” delimited list for the (rare) cases in which search engines have combined or aggregated multiple spectra in advance of the search to make identifications.  If a fragmentation spectrum has not been used, the value should indicate the ms_run to which is identification is mapped e.g. “ms_run[1]”. ",
            json_schema_extra=TableSerialization(list_concatenation_str="|").model_dump(
                exclude_unset=True, exclude_defaults=True
            ),
        ),
    ]
    identification_method: Parameter
    ms_level: Parameter
    id_confidence_measure: Annotated[
        Optional[List[Optional[float]]],
        Field(
            description="Any statistical value or score for the identification. "
            "The metadata section reports the type of score used, as id_confidence_measure[1-n] of type Param.",
            json_schema_extra=TableSerialization(multiple_columns=True).model_dump(
                exclude_unset=True, exclude_defaults=True
            ),
        ),
    ] = None
    rank: Annotated[
        int,
        Field(
            description="The rank of this identification from this approach as increasing integers from 1 (best ranked identification). Ties (equal score) are represented by using the same rank – defaults to 1 if there is no ranking system used.",
            ge=1,
        ),
    ]
    opt: Annotated[
        Optional[List[OptColumnMapping]],
        Field(
            description="Additional columns can be added to the end of the small molecule evidence table. These column headers MUST start with the prefix “opt_” followed by the {identifier} of the object they reference: assay, study variable, MS run or “global” (if the value relates to all replicates). Column names MUST only contain the following characters: ‘A'-‘Z', ‘a'-‘z', ‘0'-‘9', ‘', ‘-', ‘[', ‘]', and ‘:'. CV parameter accessions MAY be used for optional columns following the format: opt{identifier}_cv_{accession}_{parameter name}. Spaces within the parameter's name MUST be replaced by ‘_'. ",
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
