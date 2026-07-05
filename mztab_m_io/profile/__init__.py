from importlib import resources
from pathlib import Path

import mztab_m_io
from mztab_m_io.profile.default_profile import (
    DEFAULT_MZTABM_OPA_POLICY_WASM_FILE,
    DEFAULT_MZTABM_OPA_POLICY_WASM_FILE_URL,
    DEFAULT_NULL_VALUES,
    DEFAULT_PROFILE,
)
from mztab_m_io.profile.full_profile import FULL_PROFILE
from mztab_m_io.profile.metabolights_profile import METABOLIGHTS_PROFILE
from mztab_m_io.profile.mtd_smf_profile import MTD_SMF_PROFILE
from mztab_m_io.profile.mtd_sml_profile import MTD_SML_PROFILE

_root_path = Path(resources.files(mztab_m_io.__name__))
MZTABM_JSONSCHEMA_PATH = _root_path / Path("resources/mztabm-2.1.0-M.schema.json")

_profiles_path = _root_path / Path("resources/profiles")
DEFAULT_PROFILE_PATH = _profiles_path / Path(DEFAULT_PROFILE.id).name
FULL_PROFILE_PATH = _profiles_path / Path(FULL_PROFILE.id).name
MTD_SML_PROFILE_PATH = _profiles_path / Path(MTD_SML_PROFILE.id).name
MTD_SMF_PROFILE_PATH = _profiles_path / Path(MTD_SMF_PROFILE.id).name
METABOLIGHTS_PROFILE_PATH = _profiles_path / Path(METABOLIGHTS_PROFILE.id).name

__all__ = [
    "DEFAULT_PROFILE",
    "DEFAULT_MZTABM_OPA_POLICY_WASM_FILE",
    "DEFAULT_MZTABM_OPA_POLICY_WASM_FILE_URL",
    "DEFAULT_NULL_VALUES",
    "MTD_SML_PROFILE",
    "MTD_SMF_PROFILE",
    "FULL_PROFILE",
    "METABOLIGHTS_PROFILE",
    "DEFAULT_PROFILE_PATH",
    "FULL_PROFILE_PATH",
    "MTD_SML_PROFILE_PATH",
    "MTD_SMF_PROFILE_PATH",
    "METABOLIGHTS_PROFILE_PATH",
    "MZTABM_JSONSCHEMA_PATH",
]
