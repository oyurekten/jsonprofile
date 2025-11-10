from typing import Any, Literal

from pydantic import BaseModel


class MetadataDictInfo(BaseModel):
    object_level_value_field: str | None = None
    list_concatenation_str_dict: dict[str, str] = {}
    referenced_field_names: dict[str, str] = {}
    ignore_filed_names: set[str] = set()
    non_indexed_list_values: set[str] = set()
    field_type: type[BaseModel]


class MetadataSerialization(BaseModel):
    ignore: bool = False
    object_level_value: bool = False
    list_concatenation_str: None | str = None
    non_indexed_list_value: bool = False
    referenced_field_name: None | str = None


class TableSerialization(BaseModel):
    ignore: bool = False
    list_concatenation_str: None | str = None
    multiple_columns: bool = False
    column_name_field: None | str = None
    column_value_field: None | str = None
    referenced_section: None | str = None
    referenced_field_name: None | str = None


class TableInfo(BaseModel):
    list_concatenation_str_dict: dict[str, str] = {}
    multi_column_fields: dict[str, str] = {}
    column_name_fields: dict[str, str] = {}
    column_value_fields: dict[str, str] = {}
    data_types: dict[str, Any] = {}
    list_fields: dict[str, bool] = {}


class SerializationContext(BaseModel):
    convert_to: Literal["tsv", "json", "yaml"] = "tsv"
