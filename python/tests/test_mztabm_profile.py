import json
import logging
from pathlib import Path

from jsonprofile.profile.base import EnforcementLevel
from jsonprofile.profile.model import ValidationRuntimeConfiguration
from jsonprofile.utils import setup_basic_logging_config
from jsonprofile.validator.json_validator import JsonValidator

logger = logging.getLogger(__name__)


def test_example_profile() -> None:
    setup_basic_logging_config()
    mtbls_profile_file = (
        "tests/resources/profiles/mztabm-metabolights-profile-2.1.0-M.json"
    )
    default_profile_id = "https://github.com/HUPO-PSI/mzTab-M/tree/main/schema/mztabm-default-profile-2.1.0-M.json"
    default_profile_path = (
        "tests/resources/profiles/mztabm-default-profile-2.1.0-M.json"
    )
    input_json = "tests/data/manual_null_MTBLS263.mztab.json"
    json_schema_path = "tests/resources/mztabm-schema-2.1.0-M.json"
    referenced_profiles = {default_profile_id: default_profile_path}
    validator = JsonValidator(
        json_schema=json_schema_path,
        profile=mtbls_profile_file,
        referenced_profiles=referenced_profiles,
    )

    runtime_config = ValidationRuntimeConfiguration()

    input_data = json.loads(Path(input_json).read_text())
    result = validator.validate_dict(input_data, runtime_config=runtime_config)

    if result.errors:
        logger.info("%s", 120 * "-")
        logger.info("PROFILE VALIDATION MESSAGES")
        logger.info("%s", 120 * "-")
        for _, messages in result.errors.items():
            for _, message in enumerate(messages):
                enforcement_level = message.enforcement_level
                if message.enforcement_level == EnforcementLevel.REQUIRED:
                    logger.error(
                        "%s\t%s\t%s\t%s",
                        enforcement_level.name,
                        message.code or "-",
                        message.source,
                        message.message,
                    )
                elif message.enforcement_level == EnforcementLevel.RECOMMENDED:
                    logger.warning(
                        "%s\t%s\t%s\t%s",
                        enforcement_level.name,
                        message.code or "-",
                        message.source,
                        message.message,
                    )
                else:
                    logger.info(
                        "%s\t%s\t%s\t%s",
                        enforcement_level.name,
                        message.code or "-",
                        message.source,
                        message.message,
                    )
        logger.info("%s", 120 * "-")
    else:
        logger.info("%s", 120 * "-")
        logger.info("SUCCESS - NO PROFILE VALIDATION MESSAGE")
        logger.info("%s", 120 * "-")
