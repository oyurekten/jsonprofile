from typing_extensions import Any, Dict, List, Literal, Optional, Set, Union, Type

from pydantic import BaseModel


class MetadataDictInfo(BaseModel):
    object_level_value_field: Optional[str] = None
    list_concatenation_str_dict: Dict[str, str] = {}
    referenced_field_names: Dict[str, str] = {}
    ignore_filed_names: Set[str] = set()
    non_indexed_list_values: Set[str] = set()
    field_type: Type[BaseModel]


ValueConstraint = Literal[
    "positive-integer", "non-negative-integer", "curie", "any-url", "datetime", "date"
]

EnforcementLevel = Literal["optional", "recommended", "required"]


class ValidationPolicy(BaseModel):
    required: Optional[bool] = None
    minimum: Optional[int] = None
    maximum: Optional[int] = None
    pattern: Optional[str] = None
    value_constraint: Optional[ValueConstraint] = None
    enforcement_level: Optional[EnforcementLevel] = "required"


class ValidationProfile(BaseModel):
    validation_policy: Optional[Union[ValidationPolicy, List[ValidationPolicy]]] = (
        ValidationPolicy()
    )


class MetadataSerialization(ValidationProfile):
    ignore: bool = False
    object_level_value: bool = False
    list_concatenation_str: Optional[str] = None
    non_indexed_list_value: bool = False
    referenced_field_name: Optional[str] = None


class TableSerialization(ValidationProfile):
    ignore: bool = False
    list_concatenation_str: Optional[str] = None
    multiple_columns: bool = False
    column_name_field: Optional[str] = None
    column_value_field: Optional[str] = None
    referenced_section: Optional[str] = None
    referenced_field_name: Optional[str] = None


class TableInfo(BaseModel):
    list_concatenation_str_dict: Dict[str, str] = {}
    multi_column_fields: Dict[str, str] = {}
    column_name_fields: Dict[str, str] = {}
    column_value_fields: Dict[str, str] = {}
    data_types: Dict[str, Any] = {}
    list_fields: Dict[str, bool] = {}


class SerializationContext(BaseModel):
    convert_to: Literal["tsv", "json", "yaml"] = "tsv"
