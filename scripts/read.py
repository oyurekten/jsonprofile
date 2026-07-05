import logging
import time
import traceback
from pathlib import Path

import orjson
from jsonprofile.validator.context import ValidationRuntimeConfiguration

from mztab_m_io import MzTabMLoadResult
from mztab_m_io.model.validation import MzTabMessage
from mztab_m_io.mztabm_loader import MzTabMLoader
from mztab_m_io.profile import (
    FULL_PROFILE_PATH,
    METABOLIGHTS_PROFILE_PATH,
    MTD_SMF_PROFILE_PATH,
    MTD_SML_PROFILE_PATH,
)

try:
    from scripts.utils import setup_basic_logging_config
except ModuleNotFoundError:
    from utils import setup_basic_logging_config

logger = logging.getLogger(__name__)


def print_start_message(
    file_path: Path, file_idx: int, profile_idx: int, profile_name: str
):
    logger.info("%s", 120 * "-")
    logger.info(
        "(%s) - Profile (%s) %s: %s validation results.",
        file_idx,
        profile_idx,
        file_path,
        profile_name,
    )
    logger.info("%s", 120 * "-")


def save_results_to_json(
    result: MzTabMLoadResult,
    source_file_path: Path,
    output_folder_path: Path,
    save_mztabm: bool,
):
    """Save the validation results to a JSON file."""

    result_file_path = output_folder_path / Path(f"{source_file_path.name}.result.json")
    json_file_path = output_folder_path / Path(f"{source_file_path.name}.json")
    results_json = result.model_dump(by_alias=True)
    result_file_path.write_bytes(
        orjson.dumps(
            {
                "status": result.success,
                "messages": results_json.get("messages", []),
            },
            option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS,
        )
    )

    logger.info("Validation results saved to %s", result_file_path)
    if save_mztabm:
        json_file_path.write_bytes(
            orjson.dumps(
                results_json.get("mztabm", {}),
                option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS,
            )
        )

        logger.info("MzTabM json file saved to %s", json_file_path)


def log_validation_messages(messages: list[MzTabMessage], elapsed_time: float):
    """Log the validation messages."""
    if not messages:
        logger.info(
            "Read and validation time: %.6f. No validation messages.", elapsed_time
        )
    else:
        logger.info(
            "Read and validation time: %.6f. Validation messages: %s",
            elapsed_time,
            len(messages),
        )
    logger.info("%s", 120 * "-")

    for message in messages or []:
        type_ = message.message_type.name
        logger.info(
            "%s\t%s\t%s\t%s\t%s",
            message.category.name,
            type_,
            message.code or "-",
            message.source,
            message.message,
        )


if __name__ == "__main__":
    setup_basic_logging_config(level=logging.INFO)

    default_loader = MzTabMLoader()
    full_loader = MzTabMLoader(profile=FULL_PROFILE_PATH)
    mtd_sml_loader = MzTabMLoader(profile=MTD_SML_PROFILE_PATH)
    mtd_smf_loader = MzTabMLoader(profile=MTD_SMF_PROFILE_PATH)
    mtbls_loader = MzTabMLoader(profile=METABOLIGHTS_PROFILE_PATH)

    runtime_config = ValidationRuntimeConfiguration(
        skip_jsonschema_validation=True,
        max_messages_for_each_requirement=5,
        skip_decimal_validations=True,
        offline_mode=False,
    )
    output_folder = Path("./output")
    # files = list(Path("tests/data/mztabm").glob("*.mz?ab"))
    files = list(Path("tests/data/mztabm").glob("masster_0.5.25_null.mztab"))

    loaders = [
        mtbls_loader,
        default_loader,
        mtd_sml_loader,
        mtd_smf_loader,
        full_loader,
    ]
    for idx, file_path in enumerate(files, start=1):
        try:
            for profile_idx, loader in enumerate(loaders, start=1):
                profile_name = loader.profile_validator.json_profile.name
                start = time.perf_counter()
                result = loader.read(
                    str(file_path),
                    runtime_config=runtime_config,
                    auto_complete_ids=True,
                )
                end = time.perf_counter()
                print_start_message(
                    file_path,
                    file_idx=f"{idx} / {len(files)}",
                    profile_idx=f"{profile_idx} / {len(loaders)}",
                    profile_name=profile_name,
                )

                log_validation_messages(result.messages, end - start)
                save_mztabm = True if profile_idx == 1 else False
                save_results_to_json(
                    result, file_path, output_folder, save_mztabm=save_mztabm
                )

                if profile_idx > 0:
                    break
        except Exception as e:
            logger.error(e)
            traceback.print_exc()
            break
