import logging
import pathlib
from importlib import resources

import orjson

from jsonprofile.profile.model import JsonProfile
from jsonprofile.utils import setup_basic_logging_config

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    setup_basic_logging_config(level=logging.WARNING)
    json_path = pathlib.Path(
        resources.files("jsonprofile").joinpath("jsonprofile.schema.json")
    )
    schema = JsonProfile.model_json_schema(by_alias=True)
    json_path.write_bytes(orjson.dumps(schema, option=orjson.OPT_INDENT_2))
