from typing import Any, Literal, Set, Union

from pydantic import BaseModel


class MetadataDictInfo(BaseModel):
    object_level_value_field: Union[None, str] = None
    list_concatenation_str_dict: dict[str, str] = {}
    referenced_field_names: dict[str, str] = {}
    ignore_filed_names: Set[str] = set()
    non_indexed_list_values: Set[str] = set()
    field_type: type[BaseModel]


class MetadataSerialization(BaseModel):
    ignore: bool = False
    object_level_value: bool = False
    list_concatenation_str: Union[None, str] = None
    non_indexed_list_value: bool = False
    referenced_field_name: Union[None, str] = None


class TableSerialization(BaseModel):
    ignore: bool = False
    list_concatenation_str: Union[None, str] = None
    multiple_columns: bool = False
    column_name_field: Union[None, str] = None
    column_value_field: Union[None, str] = None
    referenced_section: Union[None, str] = None
    referenced_field_name: Union[None, str] = None


class TableInfo(BaseModel):
    list_concatenation_str_dict: dict[str, str] = {}
    multi_column_fields: dict[str, str] = {}
    column_name_fields: dict[str, str] = {}
    column_value_fields: dict[str, str] = {}
    data_types: dict[str, Any] = {}
    list_fields: dict[str, bool] = {}


class SerializationContext(BaseModel):
    convert_to: Literal["tsv", "json", "yaml"] = "tsv"
