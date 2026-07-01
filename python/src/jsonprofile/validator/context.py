import logging
from typing import Annotated, Any

from pydantic import ConfigDict, Field

from jsonprofile.profile.base import (
    EnforcementLevel,
    JsonPath,
    JsonProfileBaseModel,
    JsonProfileMessage,
)
from jsonprofile.profile.model import (
    JsonProfileConfiguration,
    ValidationRuntimeConfiguration,
)
from jsonprofile.validator.base import CvTermSearch, ProfileValidatorFactory
from jsonprofile.validator.opa_engine import OpaEngineFactory

logger = logging.getLogger(__name__)


class JsonValidationResult(JsonProfileBaseModel):
    errors: dict[JsonPath, list[JsonProfileMessage]]
    recommendations: dict[JsonPath, list[JsonProfileMessage]]
    optionals: dict[JsonPath, list[JsonProfileMessage]]


class MessageCollector:
    def __init__(self, max_messages_for_each_requirement: None | int = None):
        self.max_messages_for_each_requirement = max_messages_for_each_requirement
        self.messages: dict[JsonPath, dict[str, list[JsonProfileMessage]]] = {}
        self.code_messages: dict[str, list[JsonProfileMessage]] = {}

    def append_message(self, json_path: JsonPath, message: JsonProfileMessage) -> bool:
        if not self.is_open(message.code):
            if json_path not in self.messages:
                self.messages[json_path] = {}
            if message.code not in self.messages[json_path]:
                self.messages[json_path][message.code] = []
            self.messages.get(json_path).get(message.code).append(message)

            if message.code not in self.code_messages:
                self.code_messages[message.code] = []
            self.code_messages[message.code].append(message)
            code_messages = len(self.code_messages[message.code])
            if (
                self.max_messages_for_each_requirement is not None
                and code_messages >= self.max_messages_for_each_requirement
            ):
                logger.warning(
                    "%s messages reached to %s. Circuit breaker activated for %s",
                    message.code,
                    self.max_messages_for_each_requirement,
                    message.code,
                )
            return True

        return False

    def is_open(self, code: str):
        if self.max_messages_for_each_requirement is None:
            return False
        current_messages = len(self.code_messages.get(code, []))
        return current_messages >= self.max_messages_for_each_requirement

    def process_messages(self) -> JsonValidationResult:
        errors = {}
        recommendations = {}
        optionals = {}
        for k, v in self.messages.items():
            for _, data in v.items():
                for x in data:
                    for level, items in [
                        (EnforcementLevel.REQUIRED, errors),
                        (EnforcementLevel.RECOMMENDED, recommendations),
                        (EnforcementLevel.OPTIONAL, optionals),
                    ]:
                        if level == x.enforcement_level:
                            if k not in items:
                                items[k] = []
                            items[k].append(x)

        return JsonValidationResult(
            errors=errors, recommendations=recommendations, optionals=optionals
        )


class JsonProfileRunContext(JsonProfileBaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    runtime_config: Annotated[
        ValidationRuntimeConfiguration,
        Field(description="Runtime configuration"),
    ]
    profile_config: Annotated[
        JsonProfileConfiguration,
        Field(description="Profile configuration"),
    ]
    cv_term_search: Annotated[
        CvTermSearch,
        Field(description="Current CV term search implementation"),
    ]
    profile_validator_factory: Annotated[
        ProfileValidatorFactory,
        Field(description="Current profile validator factory implementation"),
    ]
    opa_engine_factory: Annotated[
        OpaEngineFactory,
        Field(description="Current OpaEngine factory implementation"),
    ]
    message_collector: Annotated[
        MessageCollector,
        Field(description="Message"),
    ]
    json_path_expressions: Annotated[
        dict[JsonPath, Any],
        Field(description="Message"),
    ] = {}
