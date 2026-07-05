import logging
from pathlib import Path
from typing import Annotated, Union

from jsonprofile.profile import JsonProfile
from jsonprofile.validator import CvTermSearch, JsonValidator
from pydantic import Field

from mztab_m_io.profile import DEFAULT_PROFILE_PATH, MZTABM_JSONSCHEMA_PATH
from mztab_m_io.profile.default_profile import DEFAULT_PROFILE

logger = logging.getLogger(__name__)


class MzTabMProfileValidator(JsonValidator):
    def __init__(
        self,
        profile: Annotated[
            None | str | Path | dict | JsonProfile,
            Field(
                description="Json profile file path or dictionary."
                " If it is not defined, default profile will be used."
            ),
        ],
        referenced_profiles: Annotated[
            dict[
                str,
                Union[str | Path, dict | JsonProfile],
            ],
            Field(
                description="Additional profile ids referenced (`extends`, etc.) "
                "in the profile and their sources. "
                "Default profile will be automatically injected."
            ),
        ] = None,
        default_cv_term_search: Annotated[
            CvTermSearch,
            Field(description="Default cv term search implementation "),
        ] = None,
    ):
        if not referenced_profiles:
            referenced_profiles = {DEFAULT_PROFILE.id: str(DEFAULT_PROFILE_PATH)}
        elif DEFAULT_PROFILE.id not in referenced_profiles:
            referenced_profiles[DEFAULT_PROFILE.id] = str(DEFAULT_PROFILE_PATH)
        if not profile:
            profile = DEFAULT_PROFILE
        super().__init__(
            json_schema=MZTABM_JSONSCHEMA_PATH,
            profile=profile,
            referenced_profiles=referenced_profiles,
            default_cv_term_search=default_cv_term_search,
        )
