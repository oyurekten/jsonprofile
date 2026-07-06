# %% import packages
# Loading imports
import json
import logging
from pathlib import Path

import mztab_m_io as mztabm
from mztab_m_io.profile import (
    FULL_PROFILE_PATH,
    METABOLIGHTS_PROFILE_PATH,
)
from scripts import utils

# creating a logger
logger = logging.getLogger(__name__)

utils.setup_basic_logging_config(logging.INFO)

# %% Load mztab file
# You can load a MzTab-M file.
# Result contain list of errors and mztabm python object

file_path = "tests/data/example/example.mztab"
result: mztabm.MzTabMLoadResult = mztabm.read(file_path)
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


# %% Load mztab file with FULL profile (MTD + SML + SMF + SME)
# You can load a MzTab-M file.
# Result contain list of errors and mztabm python object

file_path = "tests/data/example/example.mztab"
result: mztabm.MzTabMLoadResult = mztabm.read(
    file_path, mztabm_profile_file_path=FULL_PROFILE_PATH
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


# %% Load mztab file with MetaboLights profile (MTD + SML + Additional requirements)
# You can load a MzTab-M file.
# Result contain list of errors and mztabm python object

file_path = "tests/data/example/example.mztab"
result: mztabm.MzTabMLoadResult = mztabm.read(
    file_path, mztabm_profile_file_path=METABOLIGHTS_PROFILE_PATH
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

# %% Convert python MzTab-M model to json
# You can convert model to json and fetch values from dictionary
mztabm_dict, context = mztabm.convert_to_dict(result.mztabm)
logger.info("mzTab-M Id: %s", mztabm_dict.get("metadata", {}).get("mzTab-ID"))

Path("example.json").write_text(json.dumps(mztabm_dict, indent=2))

# %% Read MzTab-M json file and create Python MzTab-M model
# if you have a json version of mzTab-M, you can read it with format parameter.
file_path = "tests/data/example/example.json"
result: mztabm.MzTabMLoadResult = mztabm.read(file_path, format="json")
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


# %% Read MzTab-M json and create Python MzTab-M model
# you can also load from dictionary
file_path = "tests/data/example/example.json"
with Path(file_path).open("rb") as f:
    mztabm_dict = json.loads(f.read())
result = mztabm.load_from_dict(mztabm_dict)
for message in result.messages:
    logger.info(
        "%s %s, %s, %s",
        message.code,
        message.message_type.name,
        message.source,
        message.message,
    )
logger.info("mzTab-M Id: %s", result.mztabm.metadata.mztab_id)
# %% Write MzTab-M model to tsv file
# You can write model object to mzTab-M file as tsv, json or yaml
temp_folder = Path(".temp/mztabm")
target_path = temp_folder / Path("example.mztab")
mztabm.write(result.mztabm, str(target_path), format="tsv")


# %% Write MzTab-M model to tsv file
target_path = temp_folder / Path("example.json")
mztabm.write(result.mztabm, str(target_path), format="json")
target_path = temp_folder / Path("example.yaml")
mztabm.write(result.mztabm, str(target_path), format="yaml")
