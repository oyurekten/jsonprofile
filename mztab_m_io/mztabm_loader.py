import logging
import pathlib
import time
from pathlib import Path
from typing import Annotated, Literal, Optional, Union

import orjson
from jsonprofile.profile import JsonProfile, ValidationRuntimeConfiguration
from jsonprofile.validator import CvTermSearch, JsonValidationResult
from pydantic import Field, ValidationError

from mztab_m_io.model.base import MzTabBaseModel
from mztab_m_io.model.mztabm import MzTabM
from mztab_m_io.model.validation import (
    Category,
    MessageType,
    MzTabMessage,
    ValidationContext,
)
from mztab_m_io.profile import DEFAULT_PROFILE_PATH
from mztab_m_io.profile_validator import MzTabMProfileValidator

logger = logging.getLogger(__name__)


class MzTabMLoadResult(MzTabBaseModel):
    """Result object containing the loaded MzTabM data and validation information.

    This class extends ValidationContext to include the loading status and
    the parsed MzTabM object. It's used as the return type for loading and
    parsing operations to provide both the result and any validation messages
    or errors that occurred during the process.
    """

    messages: Annotated[list[MzTabMessage], Field()] = []
    success: bool = False
    source_format: Literal["tsv", "json", "yaml"] = "tsv"
    auto_complete_ids: bool = False
    success: Annotated[
        bool,
        Field(
            default=False,
            description="Indicates whether the loading operation was successful",
        ),
    ] = None

    mztabm: Annotated[
        Optional[MzTabM],
        Field(
            default=None,
            description="The loaded and validated MzTabM object, if successful",
        ),
    ] = None


class MzTabMLoader:
    def __init__(
        self,
        profile: Annotated[
            None | str | Path | dict | JsonProfile,
            Field(
                description="Json profile file path or dictionary."
                " If it is not defined, default profile will be used."
            ),
        ] = None,
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
        if not profile:
            profile = DEFAULT_PROFILE_PATH
        self.profile_validator = MzTabMProfileValidator(
            profile=profile,
            referenced_profiles=referenced_profiles,
            default_cv_term_search=default_cv_term_search,
        )

    def read(
        self,
        file_path: str,
        format: Literal["tsv", "json", "yaml"] = "tsv",
        auto_complete_ids: bool = False,
        runtime_config: None | ValidationRuntimeConfiguration = None,
    ) -> MzTabMLoadResult:
        if not file_path:
            raise ValueError("Invalid file path")
        if not format:
            raise ValueError("Invalid file format.")

        input_path = pathlib.Path(file_path)
        if not input_path.exists():
            raise ValueError("Input file does not exist.")
        result = None
        runtime_config = runtime_config or ValidationRuntimeConfiguration()
        max_messages_for_each_code = runtime_config.max_messages_for_each_requirement
        logger.info("File '%s' will be parsed", file_path)
        start = time.perf_counter()
        if format == "tsv":
            result = MzTabMLoadResult(
                success=False,
                source_format="tsv",
                auto_complete_ids=auto_complete_ids,
            )
            try:
                mztabm, context = MzTabM.from_tsv_file(
                    input_path,
                    context=ValidationContext(
                        source_format="tsv",
                        auto_complete_ids=auto_complete_ids,
                        max_messages_for_each_code=max_messages_for_each_code,
                    ),
                )
                result.mztabm = mztabm
                if mztabm:
                    result.success = True
                messages = list(context.messages)
                result.messages.extend(messages)
            except ValidationError as ex:
                result.messages.extend(
                    [
                        MzTabMessage(
                            category=Category.FORMAT,
                            message_type=MessageType.ERROR,
                            message=repr(x),
                            source="",
                        )
                        for x in ex.errors()
                    ]
                )
        elif format == "json" or format == "yaml":
            context = ValidationContext(
                source_format=format,
                auto_complete_ids=auto_complete_ids,
                max_messages_for_each_code=max_messages_for_each_code,
            )
            if format == "json":
                mztabm, context = MzTabM.from_json_file(input_path, context=context)
            else:
                mztabm, context = MzTabM.from_yaml_file(input_path, context=context)
            success = False
            errors = [
                x for x in context.messages if x.message_type == MessageType.ERROR
            ]
            if not errors and mztabm:
                success = True

            result = MzTabMLoadResult(
                success=success, mztabm=mztabm, messages=list(context.messages)
            )
        else:
            raise ValueError(f"invalid format type: {format}")

        end = time.perf_counter()
        logger.info("File is loaded in %.6f seconds", end - start)
        if result and result.mztabm:
            validation_start = time.perf_counter()
            self._validate(
                source=result.mztabm,
                messages=result.messages,
                runtime_config=runtime_config,
            )
            validation_end = time.perf_counter()
            logger.info(
                "MzTabM validation execution time: %.6f seconds",
                (validation_end - validation_start),
            )
        else:
            result.messages.append(
                MzTabMessage(
                    code="D-1017",
                    category=Category.FORMAT,
                    message_type=MessageType.ERROR,
                    message="MzTabM file content is not valid",
                )
            )
        return result

    def _validate(
        self,
        source: dict | MzTabM | pathlib.Path | bytes | str,
        messages: None | list[MzTabMessage] = None,
        runtime_config: None | ValidationRuntimeConfiguration = None,
    ) -> list[MzTabMessage]:
        if messages is None:
            messages = []
        logger.info("File loading started")
        mztabm_input = None
        if isinstance(source, MzTabM):
            mztabm_input = source.model_dump(by_alias=True)
        elif isinstance(source, dict):
            mztabm_input = source
        elif isinstance(source, pathlib.Path):
            mztabm_input = orjson.loads(source.read_bytes())
        elif isinstance(source, str) or isinstance(source, bytes):
            mztabm_input = orjson.loads(source)
        else:
            raise ValueError("source is not valid")

        if not runtime_config:
            runtime_config = ValidationRuntimeConfiguration()

        validation_result: JsonValidationResult = self.profile_validator.validate_dict(
            input_json=mztabm_input, runtime_config=runtime_config
        )
        for message_type, message_dict in [
            (MessageType.ERROR, validation_result.errors),
            (MessageType.WARNING, validation_result.recommendations),
            (MessageType.INFO, validation_result.optionals),
        ]:
            for _, items in message_dict.items() or {}:
                for item in items:
                    messages.append(
                        MzTabMessage(
                            code=item.code or "",
                            category=Category.PROFILE,
                            message_type=message_type,
                            message=item.message,
                            source=item.source,
                        )
                    )
        return messages
