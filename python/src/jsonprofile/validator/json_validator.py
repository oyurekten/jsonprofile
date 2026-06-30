import json
import logging
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any, Union

import jsonpath_ng
from pydantic import BaseModel, Field

from jsonprofile.profile.base import EnforcementLevel, JsonPath
from jsonprofile.profile.constraints import Constraint, DecimalConstraint
from jsonprofile.profile.model import (
    FieldRequirement,
    FieldRequirementGroup,
    JsonProfile,
    JsonProfileConfiguration,
    ValidationRuntimeConfiguration,
)
from jsonprofile.utils import convert_full_path
from jsonprofile.validator.base import ProfileValidatorFactory
from jsonprofile.validator.default import DefaultProfileValidatorFactory
from jsonprofile.validator.opa_engine import OpaEngineFactory

logger = logging.getLogger(__name__)


class JsonValidationMessage(BaseModel):
    code: None | str = None
    source: JsonPath
    name: str
    enforcement_level: EnforcementLevel
    message: str = ""


class JsonValidationResult(BaseModel):
    errors: dict[JsonPath, list[JsonValidationMessage]]
    recommendations: dict[JsonPath, list[JsonValidationMessage]]
    optionals: dict[JsonPath, list[JsonValidationMessage]]


class MessageCircuitBreaker:
    def __init__(self, max_messages_for_each_requirement: None | int = None):
        self.max_messages_for_each_requirement = max_messages_for_each_requirement
        self.messages: dict[JsonPath, dict[str, list[JsonValidationMessage]]] = {}
        self.code_messages: dict[str, list[JsonValidationMessage]] = {}

    def append_message(
        self,
        json_path: JsonPath,
        message: JsonValidationMessage,
    ):
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


class JsonValidator:
    def __init__(
        self,
        profile: Annotated[
            None | str | Path | dict | JsonProfile,
            Field(
                description="Json profile file path or dictionary."
                " If it is not defined, default profile will be used."
            ),
        ],
        referenced_profiles: Annotated[
            dict[
                str,
                Union[str | Path, dict | JsonProfile],
            ],
            Field(
                description="Profile ids referenced (`extends`, etc.) in the profile "
                "and their sources."
            ),
        ] = None,
    ):
        self.referenced_profiles = (
            referenced_profiles if referenced_profiles is not None else {}
        )
        self.json_profile = self.create_profile(profile)

        if not isinstance(self.json_profile, JsonProfile):
            raise ValueError("Profile is not valid")

        self.json_path_expressions: dict[JsonPath, Any] = {}
        if not self.json_profile.configuration:
            self.json_profile.configuration = JsonProfileConfiguration()
        config = self.json_profile.configuration

        custom_validator_definitions = None
        self.default_profile_validator_id = None

        custom_validator_definitions = config.custom_validator_definitions or []
        labels = {x.label: x for x in custom_validator_definitions}
        default_label = config.default_validator_key
        default_validator_definition = labels.get(default_label)
        self.default_profile_validator_id = (
            default_validator_definition.validator_id
            if default_validator_definition
            else None
        )
        self.opa_engine_factory = OpaEngineFactory()
        profile_validator_factory_class = ".".join(
            [
                DefaultProfileValidatorFactory.__module__,
                DefaultProfileValidatorFactory.__name__,
            ]
        )
        kwargs = {}
        if config.profile_validator_factory_class:
            kwargs = config.profile_validator_factory_class_arguments or {}
            config.profile_validator_factory_class = (
                config.profile_validator_factory_class or {}
            )
            if config.profile_validator_factory_class.get("python"):
                profile_validator_factory_class = (
                    config.profile_validator_factory_class.get("python")
                )

        self.profile_validator_factory = (
            ProfileValidatorFactory.get_profile_validator_factory(
                profile_validator_factory_class,
                custom_validator_definitions=custom_validator_definitions,
                default_profile_validator_id=self.default_profile_validator_id,
                opa_engine_factory=self.opa_engine_factory,
                **kwargs,
            )
        )

    def create_profile(
        self,
        profile: Annotated[
            str | Path | dict | JsonProfile,
            Field(
                description="Json profile file path or dictionary."
                " If it is not defined, default profile will be used."
            ),
        ],
    ) -> JsonProfile:
        if isinstance(profile, str):
            profile = Path(profile)
        target_profile = None
        if isinstance(profile, Path):
            if not profile.exists():
                raise ValueError(f"Json profile ({profile}) file does not exist.")
            profile_json = json.loads(profile.read_text())
            target_profile = JsonProfile.model_validate(profile_json)
        elif isinstance(profile, dict):
            target_profile = JsonProfile.model_validate(profile, by_alias=True)
        if isinstance(profile, JsonProfile):
            target_profile = profile
        if not target_profile or not isinstance(target_profile, JsonProfile):
            raise ValueError(
                "Json profile load failure. "
                "Please provide profile file path, dict or JsonProfile object"
            )
        if target_profile.extends:
            if target_profile.extends not in self.referenced_profiles:
                raise ValueError(
                    f"Referenced Json profile {target_profile.extends} not found. "
                )
            referenced_profile_source = self.referenced_profiles[target_profile.extends]
            referenced_profile = self.create_profile(referenced_profile_source)
            self.referenced_profiles[referenced_profile.id] = referenced_profile

            merged_profile = self.extend_profile(referenced_profile, target_profile)
            return merged_profile

        self.referenced_profiles[target_profile.id] = target_profile
        return target_profile

    def validate_json_file(
        self,
        json_file_path: str | Path,
        runtime_config: None | ValidationRuntimeConfiguration = None,
    ) -> JsonValidationResult:
        if isinstance(json_file_path, str):
            json_file_path = Path(json_file_path)

        if not json_file_path.exists():
            raise ValueError("Json file does not exist.")

        if not runtime_config:
            runtime_config = ValidationRuntimeConfiguration()

        input_json = json.loads(json_file_path.read_text())

        return self.validate_dict(input_json, runtime_config=runtime_config)

    @staticmethod
    def extend_profile(parent_profile: None | JsonProfile, input_profile: JsonProfile):
        if not parent_profile:
            if not input_profile.configuration:
                input_profile.configuration = JsonProfileConfiguration(
                    wasm_file_definitions={}
                )
            return input_profile
        new_requirements = input_profile.requirements
        input_profile.requirements = parent_profile.requirements

        if not input_profile.configuration:
            input_profile.configuration = parent_profile.configuration

        # set configuration fields from parent if they are not defined.
        config = input_profile.configuration
        parent_config = parent_profile.configuration or JsonProfileConfiguration()
        for field, _ in config.__class__.model_fields.items():
            val = getattr(config, field)
            if val is None:
                parent_val = getattr(parent_config, field)
                setattr(config, field, parent_val)

        for key, value in new_requirements.items():
            new_codes = JsonValidator.get_requirement_codes(value)
            if key in input_profile.requirements:
                old_codes = JsonValidator.get_requirement_codes(
                    input_profile.requirements[key]
                )
                if value is None:
                    del input_profile.requirements[key]
                    logger.info(
                        "Deleted: Dropped profile requirement(s) for '%s': %s",
                        key,
                        old_codes,
                    )
                else:
                    logger.info(
                        "Overridden: "
                        "Requirement updates for '%s'. old codes: %s, new: %s",
                        key,
                        old_codes,
                        new_codes,
                    )

            else:
                logger.info(
                    "Added: New profile requirement(s) for '%s': %s ",
                    key,
                    new_codes,
                )
            input_profile.requirements[key] = value

        return input_profile

    def validate_dict(
        self,
        input_json: dict,
        runtime_config: None | ValidationRuntimeConfiguration = None,
    ):
        result = self.validate_dict_with_profile(
            input_json=input_json, runtime_config=runtime_config
        )

        return self.process_messages(result)

    @staticmethod
    def get_requirement_codes(value: FieldRequirement | FieldRequirementGroup):
        requirement_codes = []
        if value:
            if isinstance(value, FieldRequirement):
                requirement_codes = [value.code] if value.code else ""
            else:
                requirement_codes = [x.code for x in value.requirements if x.code]
        requirement_codes_str = ", ".join(requirement_codes)
        return requirement_codes_str

    def validate_dict_with_profile(
        self,
        input_json: dict,
        runtime_config: None | ValidationRuntimeConfiguration = None,
    ) -> dict[JsonPath, list[JsonValidationMessage]]:
        max_message = (
            runtime_config.max_messages_for_each_requirement if runtime_config else None
        )
        message_breaker = MessageCircuitBreaker(max_message)
        for (
            json_path,
            requirement_definition,
        ) in self.json_profile.requirements.items():
            json_path = json_path or "$"
            if not requirement_definition:
                logger.info(
                    "Skipping key. Field requirement is not defined for '%s'", json_path
                )
                continue
            requirement_group = None
            if isinstance(requirement_definition, FieldRequirement):
                requirement_group = FieldRequirementGroup(
                    requirements=[requirement_definition]
                )
            elif isinstance(requirement_definition, FieldRequirementGroup):
                requirement_group = requirement_definition
            else:
                raise ValueError(
                    f"Invalid requirement type: {type(requirement_definition)}"
                )
            if not json_path:
                logger.info("Field key is not defined. $ will be used.")
                json_path = "$"
            for field_requirement in requirement_group.requirements:
                start = time.perf_counter()
                self.validate_requirement(
                    field_requirement=field_requirement,
                    json_path=json_path,
                    input_json=input_json,
                    message_breaker=message_breaker,
                    runtime_config=runtime_config,
                )

                end = time.perf_counter()
                duration = end - start
                if duration > 0.5:
                    logger.warning(
                        "%s execution time: %.6f seconds",
                        field_requirement.code,
                        (end - start),
                    )

        return message_breaker.messages

    def validate_requirement(
        self,
        field_requirement: FieldRequirement,
        json_path: JsonPath,
        input_json: dict,
        message_breaker: MessageCircuitBreaker,
        runtime_config: None | ValidationRuntimeConfiguration = None,
    ):
        constraint_name = (
            field_requirement.value_constraint.type
            if field_requirement.value_constraint
            else "field-requirement"
        )
        if runtime_config and runtime_config.skipped_requirements:
            if field_requirement.code in runtime_config.skipped_requirements:
                logger.warning(
                    "%s for %s is in skipped list.", field_requirement.code, json_path
                )
                message_breaker.append_message(
                    json_path=json_path,
                    message=JsonValidationMessage(
                        code=field_requirement.code,
                        source=json_path,
                        name=constraint_name,
                        enforcement_level=EnforcementLevel.RECOMMENDED,
                        message=f"{field_requirement.code} of '{json_path}' "
                        "is in skipped list.",
                    ),
                )
                return
        if field_requirement and field_requirement.value_constraint:
            if runtime_config and runtime_config.skip_decimal_validations:
                if isinstance(field_requirement.value_constraint, DecimalConstraint):
                    logger.warning("Decimal validations are skipped for %s", json_path)
                    message_breaker.append_message(
                        json_path=json_path,
                        message=JsonValidationMessage(
                            code=field_requirement.code,
                            source=json_path,
                            name=field_requirement.value_constraint.type,
                            enforcement_level=EnforcementLevel.RECOMMENDED,
                            message=f"{field_requirement.code} decimal validations "
                            f"are skipped for '{json_path}'",
                        ),
                    )
                    return
        jsonpath_expr = self.json_path_expressions.get(json_path)
        if not jsonpath_expr:
            jsonpath_expr = jsonpath_ng.parse(json_path)
            self.json_path_expressions[json_path] = jsonpath_expr

        matches = jsonpath_expr.find(input_json)
        if not matches:
            if field_requirement.match_is_required:
                message_breaker.append_message(
                    json_path=json_path,
                    message=JsonValidationMessage(
                        code=field_requirement.code,
                        source=json_path,
                        name=constraint_name,
                        enforcement_level=field_requirement.enforcement_level,
                        message=f"There is no value with json path '{json_path}'",
                    ),
                )
        else:
            for x in matches or []:
                if message_breaker.is_open(field_requirement.code):
                    break
                source = convert_full_path(x.full_path)
                if (
                    field_requirement.required_properties
                    or field_requirement.recommended_properties
                ) and not isinstance(x.value, Mapping):
                    message_breaker.append_message(
                        json_path=source,
                        message=JsonValidationMessage(
                            code=field_requirement.code,
                            source=source,
                            name="Property check failed",
                            enforcement_level=EnforcementLevel.REQUIRED,
                            message=f"Property check failed. '{source}' is not object.",
                        ),
                    )

                else:
                    not_defined_fields = [
                        a
                        for a in field_requirement.required_properties or []
                        if a not in x.value
                    ]
                    if not_defined_fields:
                        fields = ", ".join(not_defined_fields)
                        message_breaker.append_message(
                            json_path=source,
                            message=JsonValidationMessage(
                                code=field_requirement.code,
                                source=source,
                                name="Required property does not exist",
                                enforcement_level=EnforcementLevel.REQUIRED,
                                message=f"{fields} is not in object '{source}'",
                            ),
                        )
                    not_defined_fields = [
                        a
                        for a in field_requirement.recommended_properties or []
                        if a not in x.value
                    ]

                    if not_defined_fields:
                        fields = ", ".join(not_defined_fields)
                        message_breaker.append_message(
                            json_path=source,
                            message=JsonValidationMessage(
                                code=field_requirement.code,
                                source=source,
                                name="Recommended property does not exist",
                                enforcement_level=EnforcementLevel.RECOMMENDED,
                                message=f"{fields} field(s) not in object '{source}'",
                            ),
                        )

                if field_requirement.value_constraint:
                    constraint = field_requirement.value_constraint
                    checker = self.profile_validator_factory.get_checker(constraint)
                    # sub_input_value = self.get_json_path_value(
                    #     field_requirement.value_constraint, x.value
                    # )
                    skip = False
                    if runtime_config and runtime_config.skip_decimal_validations:
                        if isinstance(constraint, DecimalConstraint):
                            skip = True

                    if not skip:
                        res = checker.validate_constraint(
                            constraint=field_requirement.value_constraint,
                            value=x.value,
                            root=input_json,
                            config=self.json_profile.configuration,
                            runtime_config=runtime_config,
                        )
                        if not res.is_valid:
                            message_breaker.append_message(
                                json_path=source,
                                message=JsonValidationMessage(
                                    code=field_requirement.code,
                                    source=source,
                                    name=field_requirement.value_constraint.type,
                                    enforcement_level=field_requirement.enforcement_level,
                                    message=res.message,
                                ),
                            )

    def get_json_path_value(self, constraint: Constraint, value: Any):
        sub_input_value = value

        if constraint.json_path:
            sub_jsonpath = constraint.json_path
            if not sub_jsonpath.startswith("$"):
                if sub_jsonpath.startswith("[") or sub_jsonpath.startswith("."):
                    sub_jsonpath = f"${sub_jsonpath}"
                elif not sub_jsonpath.startswith("."):
                    sub_jsonpath = f"$.{sub_jsonpath}"

            sub_jsonpath_expr = self.json_path_expressions.get(sub_jsonpath)
            if not sub_jsonpath_expr:
                sub_jsonpath_expr = jsonpath_ng.parse(sub_jsonpath)
                self.json_path_expressions[sub_jsonpath] = sub_jsonpath_expr

            sub_input_value = [a.value for a in sub_jsonpath_expr.find(value)]
            if len(sub_input_value) == 1:
                sub_input_value = sub_input_value[0]
            elif len(sub_input_value) == 0:
                sub_input_value = None
        return sub_input_value

    def process_messages(self, messages: dict[JsonPath, list[JsonValidationMessage]]):
        errors = {}
        recommendations = {}
        optionals = {}
        for k, v in messages.items():
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

        # for k, v in errors.items():
        #     for x in v:
        #         logger.error(
        #             "%s\t%s\t%s\t%s", x.enforcement_level.value, k, x.name, x.message
        #         )
        return JsonValidationResult(
            errors=errors, recommendations=recommendations, optionals=optionals
        )
