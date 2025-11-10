import abc
import enum
from typing import Annotated, Any, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializationInfo,
    SerializerFunctionWrapHandler,
)

from mztabm.model.serialization import (
    MetadataDictInfo,
    MetadataSerialization,
    SerializationContext,
)


class SerializationCategory(str, enum.Enum):
    STRING = "string"
    INTEGER = "integer"
    OBJECT = "object"
    STRING_LIST = "string_list"
    INTEGER_LIST = "integer_list"
    OBJECT_LIST = "object_list"


class CustomSerializer(abc.ABC):
    def serialize(self) -> str:
        pass


class MzTabBaseModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_default=True,
        validate_assignment=True,
        validation_error_cause=True,
    )

    def serialize_to_json(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> tuple[bool, dict[str, Any]]:
        if info and isinstance(info.context, SerializationContext):
            if info.context.convert_to and info.context.convert_to.lower() == "json":
                return True, handler(self)
        return False, {}


class SerializableModel(MzTabBaseModel):
    __field_info__: None | MetadataDictInfo = None

    @classmethod
    def get_dict_info(cls):
        if cls.__field_info__:
            return cls.__field_info__

        dict_info = MetadataDictInfo(field_type=cls)

        for field, field_info in cls.model_fields.items():
            extra = field_info.json_schema_extra or {}
            json_extra = MetadataSerialization.model_validate(extra, by_alias=True)
            if json_extra.ignore:
                continue
            field_name = field_info.validation_alias or field
            if json_extra.object_level_value:
                dict_info.object_level_value_field = field_name
            if json_extra.list_concatenation_str:
                dict_info.list_concatenation_str_dict[field_name] = (
                    json_extra.list_concatenation_str
                )
            if json_extra.referenced_field_name:
                dict_info.referenced_field_names[field_name] = (
                    json_extra.referenced_field_name
                )
            if json_extra.ignore:
                dict_info.ignore_filed_names.add(field_name)
            if json_extra.non_indexed_list_value:
                dict_info.non_indexed_list_values.add(field_name)
        cls.__field_info__ = dict_info
        return dict_info


class IdentifiableModel(SerializableModel):
    id: Annotated[
        Optional[int],
        Field(
            ge=1,
            json_schema_extra=MetadataSerialization(ignore=True).model_dump(
                exclude_unset=True, exclude_defaults=True
            ),
        ),
    ] = None

    def get_id(self):
        return self.id
