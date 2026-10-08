import logging
import pathlib
import re
import sys
from collections.abc import Sequence
from importlib import resources
from typing import Mapping, Optional, Union

import jsonschema_rs
import orjson
from cachetools import cached


def sanitize_str(val: Optional[str], separators: Optional[list[str]] = None) -> str:
    if not val:
        return ""
    sanitized = val if isinstance(val, str) else str(val)
    # Replace common whitespace control chars with space
    sanitized = sanitized.strip().strip('"').strip()
    sanitized = re.sub(r"[\t\n\r]", " ", sanitized)
    # Remove remaining control characters (U+0000–U+001F, U+007F)
    sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", sanitized)
    sanitized = re.sub(r" +", " ", sanitized)

    # sanitized = sanitized.replace('"', '\\"')
    separators_set = {",", "|", '"'}
    if separators:
        separators_set.update(separators)
    if any(c in sanitized for c in separators_set):
        return f'"{sanitized}"'
    return sanitized


def to_jsonpath(reference: list[Union[str, int]]):
    if not reference:
        return "$"
    json_path = "$"
    for item in reference:
        if isinstance(item, int):
            json_path += f"[{item}]"
        else:
            json_path += f".{item}"
    return json_path


def convert_full_path(full_path) -> str:
    if not full_path or full_path == "$":
        return "$"
    path = str(full_path)
    path = path.replace(".[", "[")
    path = path.replace("(", "")
    path = path.replace(")", "")

    return f"$.{path}" if path else "$"


def is_non_string_container(value) -> bool:
    return isinstance(value, (Sequence, Mapping)) and not isinstance(
        value, (str, bytes, bytearray)
    )


def setup_basic_logging_config(level: int = logging.INFO):
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] %(levelname)s "
        "[%(name)s.%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%d/%b/%Y %H:%M:%S",
        stream=sys.stdout,
    )
    logging.getLogger("httpx2").setLevel(logging.ERROR)


@cached
def get_jsonprofile_schema() -> dict:
    json_path = pathlib.Path(
        resources.files("jsonprofile").joinpath("jsonprofile.schema.json")
    )
    return orjson.loads(json_path.read_bytes())


def get_jsonprofile_schema_validator() -> jsonschema_rs.Draft202012Validator:
    schema = get_jsonprofile_schema()
    return jsonschema_rs.Draft202012Validator(schema=schema)


def validate_profile_schema(profile_content: str | pathlib.Path | dict) -> bool:
    validator = get_jsonprofile_schema_validator()
    content = None
    if isinstance(profile_content, str):
        content = orjson.loads(pathlib.Path(profile_content).read_bytes())
    elif isinstance(profile_content, pathlib.Path):
        content = orjson.loads(profile_content.read_bytes())
    elif isinstance(profile_content, dict):
        content = profile_content
    if not content:
        raise ValueError("Input is not valid")
    validator.validate(content)
