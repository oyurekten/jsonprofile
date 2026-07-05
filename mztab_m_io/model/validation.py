import enum
import logging
from collections.abc import Iterator
from typing import Literal, Optional

from mztab_m_io.model.base import MzTabBaseModel

logger = logging.getLogger(__name__)


class Category(str, enum.Enum):
    SERIALIZE = "serialize"
    PARSE = "parse"
    FORMAT = "format"
    CROSS_CHECK = "cross_check"
    PROFILE = "profile"
    SCHEMA = "schema"


class MessageType(str, enum.Enum):
    ERROR = "error"
    WARNING = "warn"
    INFO = "info"


class MzTabMessage(MzTabBaseModel):
    code: str = ""
    category: Category
    message_type: Optional[MessageType] = MessageType.INFO
    message: str
    line_number: Optional[int] = None
    source: Optional[str] = None


class MessageCircuitBreaker:
    def __init__(self, max_messages_for_each_code: None | int = None):
        self.max_messages_for_each_code = max_messages_for_each_code
        self.code_messages: dict[str, list[MzTabMessage]] = {}

    def append(self, message: MzTabMessage) -> bool:
        if not self.is_open(message.code):
            if message.code not in self.code_messages:
                self.code_messages[message.code] = []
            self.code_messages[message.code].append(message)
            code_messages = len(self.code_messages[message.code])
            if (
                self.max_messages_for_each_code is not None
                and code_messages >= self.max_messages_for_each_code
            ):
                logger.warning(
                    "%s messages reached to %s. Circuit breaker activated for %s",
                    message.code,
                    self.max_messages_for_each_code,
                    message.code,
                )
            return True

        return False

    def extend(self, messages: list[MzTabMessage]) -> bool:
        for message in messages:
            if not self.append(message):
                return False

        return True

    def is_open(self, code: str):
        if (
            self.max_messages_for_each_code is not None
            and code in self.code_messages
            and len(self.code_messages[code]) >= self.max_messages_for_each_code
        ):
            return True
        return False

    def __iter__(self) -> Iterator[MzTabMessage]:
        for messages in self.code_messages.values():
            for message in messages:
                yield message


class ValidationContext:
    def __init__(
        self,
        source_format: Literal["tsv", "json", "yaml"] = "tsv",
        auto_complete_ids: bool = False,
        max_messages_for_each_code: None | int = None,
    ):
        self.messages: MessageCircuitBreaker = MessageCircuitBreaker(
            max_messages_for_each_code
        )
        self.source_format: Literal["tsv", "json", "yaml"] = source_format
        self.auto_complete_ids: bool = auto_complete_ids
