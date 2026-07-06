# %% import packages
# Loading imports
import json
import logging
from pathlib import Path

from jsonprofile.profile import ValidationRuntimeConfiguration

import mztab_m_io as mztabm
from mztab_m_io.mztabm_loader import MzTabMLoader
from mztab_m_io.profile import (
    FULL_PROFILE_PATH,
    METABOLIGHTS_PROFILE_PATH,
    MTD_SMF_PROFILE_PATH,
    MTD_SML_PROFILE_PATH,
)
from scripts import utils

# creating a logger
logger = logging.getLogger(__name__)

utils.setup_basic_logging_config(logging.INFO)

# %% create loader with different profiles

default_loader = MzTabMLoader()
full_profile_loader = MzTabMLoader(profile=FULL_PROFILE_PATH)
mtd_sml_profile_loader = MzTabMLoader(profile=MTD_SML_PROFILE_PATH)
mtd_smf_profile_loader = MzTabMLoader(profile=MTD_SMF_PROFILE_PATH)
metabolights_profile_loader = MzTabMLoader(profile=METABOLIGHTS_PROFILE_PATH)


# %% Load mztab file
# You can load a MzTab-M file.
# Result contain list of errors and mztabm python object

file_path = "tests/data/example/example.mztab"
result: mztabm.MzTabMLoadResult = default_loader.read(file_path)
for message in result.messages:
    logger.info(
        "%s %s, %s, %s",
        message.code,
        message.message_type.name,
        message.source,
        message.message,
    )
mztabm_model = result.mztabm

# You can use model object to get data in mzTab-M file
logger.info("mzTab-M Id: %s", result.mztabm.metadata.mztab_id)


# %% Read MzTab-M json file and create Python MzTab-M model
# if you have a json version of mzTab-M, you can read it with format parameter.
file_path = "tests/data/example/example.json"
result: mztabm.MzTabMLoadResult = metabolights_profile_loader.read(
    file_path, format="json"
)
for message in result.messages:
    logger.info(
        "%s %s, %s, %s",
        message.code,
        message.message_type.name,
        message.source,
        message.message,
    )
mztabm_model = result.mztabm

# You can use model object to get data in mzTab-M file
logger.info("mzTab-M Id: %s", result.mztabm.metadata.mztab_id)


# %% Load mztab file with custom run configuration
# You can load a MzTab-M file and skip decimal validations.
# Result contain list of errors and mztabm python object

file_path = "tests/data/example/example.mztab"
runtime_config = ValidationRuntimeConfiguration(skip_decimal_validations=True)
result: mztabm.MzTabMLoadResult = default_loader.read(
    file_path, runtime_config=runtime_config
)
for message in result.messages:
    logger.info(
        "%s %s, %s, %s",
        message.code,
        message.message_type.name,
        message.source,
        message.message,
    )
mztabm_model = result.mztabm

# You can use model object to get data in mzTab-M file
logger.info("mzTab-M Id: %s", result.mztabm.metadata.mztab_id)


# %% Load mztab file in offline mode
# It skips jsonschema, online validations,
# (OLS CV Term validation and email address (DNS) validation),
# and specific requirements
# Result contain list of errors and mztabm python object

file_path = "tests/data/example/example.mztab"
runtime_config = ValidationRuntimeConfiguration(
    offline_mode=True,
    skip_jsonschema_validation=True,
    skipped_requirements=[
        "D-METADATA-SOFTWARE-0001",
        "D-METADATA-SOFTWARE-0010",
        "D-MTD-CONTACT-0001",
    ],
)
result: mztabm.MzTabMLoadResult = default_loader.read(
    file_path, runtime_config=runtime_config
)
for message in result.messages:
    logger.info(
        "%s %s, %s, %s",
        message.code,
        message.message_type.name,
        message.source,
        message.message,
    )
mztabm_model = result.mztabm

# You can use model object to get data in mzTab-M file
logger.info("mzTab-M Id: %s", result.mztabm.metadata.mztab_id)
