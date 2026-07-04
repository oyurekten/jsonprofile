import logging
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any, Union

import jsonpath_ng
import jsonschema_rs
import orjson
from jsonschema_rs import ValidationError
from pydantic import Field

from jsonprofile.profile.base import (
    Category,
    EnforcementLevel,
    JsonPath,
    JsonProfileMessage,
)
from jsonprofile.profile.constraints.constraints import DecimalConstraint
from jsonprofile.profile.model import (
    FieldRequirement,
    FieldRequirementGroup,
    JsonProfile,
    JsonProfileConfiguration,
    OpaFieldRequirement,
    ValidationRuntimeConfiguration,
)
from jsonprofile.utils import convert_full_path, to_jsonpath
from jsonprofile.validator.base import CvTermSearch, ProfileValidatorFactory
from jsonprofile.validator.checkers.default_checker import (
    OpaPolicyInput,
    OpaPolicyMessagesOutput,
)
from jsonprofile.validator.context import (
    JsonProfileRunContext,
    JsonValidationResult,
    MessageCollector,
)
from jsonprofile.validator.default.ols_cv_term_search import OlsCvTermSearch
from jsonprofile.validator.default.profile_validator_factory import (
    DefaultProfileValidatorFactory,
)
from jsonprofile.validator.opa_engine import OpaEngineFactory

logger = logging.getLogger(__name__)


class JsonValidator:
    def __init__(
        self,
        json_schema: Annotated[
            str | Path | dict,
            Field(description="Json schema file path for the profile."),
        ],
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
        default_cv_term_search: Annotated[
            CvTermSearch,
            Field(description="Default cv term search implementation "),
        ] = None,
    ):

        logger.info("Json schema will be loaded.")
        self.json_schema = self.load_jsonschema(json_schema)
        self.validate_jsonschema(self.json_schema)
        logger.debug("Json schema validated.")
        self.schema_validator = jsonschema_rs.validator_for(self.json_schema)
        self.referenced_profiles = (
            referenced_profiles if referenced_profiles is not None else {}
        )
        self.json_profile = self.create_profile(profile)
        if not default_cv_term_search:
            self.default_cv_term_search = OlsCvTermSearch()

        if not isinstance(self.json_profile, JsonProfile):
            raise ValueError("Profile is not valid")

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
        self.json_path_expressions: dict[JsonPath, Any] = {}

    def load_jsonschema(self, json_schema: str | Path | dict) -> dict:
        if isinstance(json_schema, str):
            json_schema = Path(json_schema)
        target_schema = None
        if isinstance(json_schema, Path):
            if not json_schema.exists():
                raise ValueError(f"Json schema ({json_schema}) file does not exist.")
            target_schema = orjson.loads(json_schema.read_bytes())
        elif isinstance(json_schema, dict):
            target_schema = json_schema
        if not target_schema or not isinstance(target_schema, dict):
            raise ValueError(
                "Json schema load failure. Please provide schema file path or dict"
            )
        return target_schema

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
            profile_json = orjson.loads(profile.read_bytes())
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

        input_json = orjson.loads(json_file_path.read_bytes())

        return self.validate_dict(input_json, runtime_config=runtime_config)

    @staticmethod
    def extend_profile(parent_profile: None | JsonProfile, input_profile: JsonProfile):
        if not parent_profile:
            if not input_profile.configuration:
                input_profile.configuration = JsonProfileConfiguration(
                    wasm_file_definitions={}
                )
            logger.info(
                "Profile %s does not extend any parent profile.",
                input_profile.name,
            )
            return input_profile
        logger.info(
            "Profile %s extends %s profile. Updating configuration and requirements.",
            input_profile.name,
            parent_profile.name,
        )
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
        merge_actions: list[str] = []

        for key, value in new_requirements.items():
            new_codes = JsonValidator.get_requirement_codes(value)
            if key in input_profile.requirements:
                old_codes = JsonValidator.get_requirement_codes(
                    input_profile.requirements[key]
                )
                if value is None:
                    merge_actions.append(f"Deleted: {key}[{old_codes}] -> {key}[]")
                    del input_profile.requirements[key]
                    logger.debug(
                        "Deleted: Dropped profile requirement(s) for '%s': %s",
                        key,
                        old_codes,
                    )
                else:
                    merge_actions.append(
                        f"Overridden: {key}[{old_codes}] -> {key}[{new_codes}]"
                    )
                    logger.debug(
                        "Overridden: "
                        "Requirement updates for '%s'. old codes: %s, new: %s",
                        key,
                        old_codes,
                        new_codes,
                    )

            else:
                merge_actions.append(f"Added: {key}[] -> {key}[{new_codes}]")
                logger.debug(
                    "Added: New profile requirement(s) for '%s': %s ",
                    key,
                    new_codes,
                )
            input_profile.requirements[key] = value
        if merge_actions:
            logger.info("Profile merge results:")
            for action in merge_actions:
                logger.info(action)
        return input_profile

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

    @staticmethod
    def _iter_error_context(error):
        yield error
        context = getattr(getattr(error, "kind", None), "context", None)
        if context is None:
            return
        if isinstance(context, list):
            for item in context:
                if isinstance(item, list):
                    for nested_item in item:
                        yield from JsonValidator._iter_error_context(nested_item)
                else:
                    yield from JsonValidator._iter_error_context(item)

    @staticmethod
    def best_match(errors):
        def has_context(error) -> bool:
            return getattr(getattr(error, "kind", None), "context", None) is not None

        errors = [
            nested_error
            for error in errors
            for nested_error in JsonValidator._iter_error_context(error)
        ]
        if not errors:
            return None

        return max(
            errors,
            key=lambda e: (
                len(getattr(e, "instance_path", []) or []),
                not has_context(e),
                str(e.schema_path),
            ),
        )

    def validate_json_with_schema(
        self, json_data: dict, context: JsonProfileRunContext
    ) -> None:
        logging.info("Json schema validation started.")
        start = time.perf_counter()

        for error in sorted(self.schema_validator.iter_errors(json_data), key=str):
            error = self.best_match([error]) or error
            json_path = to_jsonpath(error.instance_path)
            context.message_collector.add_message(
                json_path=json_path,
                message=JsonProfileMessage(
                    code="SCHEMA-0001",
                    source=json_path,
                    category=Category.SCHEMA,
                    name="jsonschema",
                    enforcement_level=EnforcementLevel.REQUIRED,
                    message=f"Json schema validation error: {error.message}",
                ),
            )
        end = time.perf_counter()
        logger.info(
            "Json data is validated with its source jsonschema in %.6f seconds",
            end - start,
        )

    def create_context(
        self, runtime_config: None | ValidationRuntimeConfiguration = None
    ) -> JsonProfileRunContext:
        runtime_config = runtime_config or ValidationRuntimeConfiguration()
        return JsonProfileRunContext(
            runtime_config=runtime_config or ValidationRuntimeConfiguration(),
            profile_config=self.json_profile.configuration
            or JsonProfileConfiguration(),
            opa_engine_factory=self.opa_engine_factory,
            profile_validator_factory=self.profile_validator_factory,
            cv_term_search=self.default_cv_term_search,
            message_collector=MessageCollector(
                runtime_config.max_messages_for_each_requirement
            ),
            json_path_expressions=self.json_path_expressions or {},
        )

    def validate_jsonschema(
        self, json_schema: dict
    ) -> tuple[bool, None | JsonProfileMessage]:
        try:
            jsonschema_rs.meta.validate(json_schema)
        except ValidationError as ex:
            raise ValueError(f"Json schema is not valid. {ex.message}") from ex

    def find_all_constraints(
        self,
        requirement: FieldRequirement | FieldRequirementGroup,
        constraints: set[tuple[str, None | str]],
    ):
        if requirement is None:
            return
        if isinstance(requirement, FieldRequirement):
            if requirement.value_constraint:
                constraints.add(
                    (
                        requirement.value_constraint.type,
                        requirement.value_constraint.name or None,
                    )
                )
        elif isinstance(requirement, FieldRequirementGroup):
            for req in requirement.requirements:
                self.find_all_constraints(req, constraints)

    def validate_dict(
        self,
        input_json: dict,
        runtime_config: None | ValidationRuntimeConfiguration = None,
    ) -> JsonValidationResult:
        if not runtime_config:
            runtime_config = ValidationRuntimeConfiguration()
        runtime_config.skipped_requirements = runtime_config.skipped_requirements or []
        context = self.create_context(runtime_config=runtime_config)
        if not runtime_config.skip_jsonschema_validation:
            self.validate_json_with_schema(json_data=input_json, context=context)
        else:
            logger.info("Jsonschema validation is skipped")
        if runtime_config.skip_profile_validation:
            logger.info("Profile validation is skipped")
            return context.message_collector.process_messages()
        requirements_start = time.perf_counter()
        requirement_evaluation_times: dict[str, str] = {}
        for (
            json_path,
            requirement_definition,
        ) in self.json_profile.requirements.items():
            source_json_path = json_path
            requirement_evaluation_times[source_json_path] = 0
            json_path_eval_start = time.perf_counter()
            json_path = json_path or "$"
            if not requirement_definition:
                logger.info(
                    "Skipping key. Field requirement is not defined for '%s'", json_path
                )
                continue

            if runtime_config.skip_decimal_validations:
                all_field_constraints: set[tuple[str, None | str]] = set()
                self.find_all_constraints(
                    requirement=requirement_definition,
                    constraints=all_field_constraints,
                )
                is_decimal = [x for x, _ in all_field_constraints if x == "decimal"]
                if len(all_field_constraints) == 1 and is_decimal:
                    logger.warning(
                        "Decimal validations are skipped for '%s'", json_path
                    )
            requirement_group = None
            if isinstance(
                requirement_definition, (FieldRequirement, OpaFieldRequirement)
            ):
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
                if field_requirement.code in runtime_config.skipped_requirements:
                    logger.warning(
                        "%s for %s is in skipped list.",
                        field_requirement.code,
                        json_path,
                    )
                    constraint_name = (
                        field_requirement.value_constraint.type
                        if field_requirement.value_constraint
                        else "field-requirement"
                    )
                    context.message_collector.add_message(
                        json_path=json_path,
                        message=JsonProfileMessage(
                            code=field_requirement.code,
                            source=json_path,
                            category=Category.PROFILE,
                            name=constraint_name,
                            enforcement_level=EnforcementLevel.RECOMMENDED,
                            message=f"{field_requirement.code} of '{json_path}' "
                            "is in skipped list.",
                        ),
                    )
                    continue

                start = time.perf_counter()
                if isinstance(field_requirement, OpaFieldRequirement):
                    self.validate_opa_field_requirement(
                        field_requirement=field_requirement,
                        json_path=json_path,
                        input_json=input_json,
                        context=context,
                    )

                else:
                    self.validate_requirement(
                        field_requirement=field_requirement,
                        json_path=json_path,
                        input_json=input_json,
                        context=context,
                    )

                end = time.perf_counter()
                duration = end - start
                if duration > 0.5:
                    logger.warning(
                        "%s execution time: %.6f seconds",
                        field_requirement.code,
                        (end - start),
                    )
            json_path_eval_end = time.perf_counter()
            requirement_evaluation_times[source_json_path] = (
                json_path_eval_end - json_path_eval_start
            )

        requirements_end = time.perf_counter()
        logger.info(
            "Profile requirements are evaluated in %.6f seconds",
            requirements_end - requirements_start,
        )
        if logger.getEffectiveLevel() == logging.DEBUG:
            for json_path, elapsed_time in requirement_evaluation_times.items():
                logger.debug("%s\t%0.6f", json_path, elapsed_time)

        return context.message_collector.process_messages()

    def validate_opa_field_requirement(
        self,
        field_requirement: OpaFieldRequirement,
        json_path: JsonPath,
        input_json: dict,
        context: JsonProfileRunContext,
    ):
        config = context.profile_config
        label = field_requirement.wasm_file_key or "default"
        wasm_file_path = None
        wasm_file_download_url = None
        if config and config.wasm_file_definitions:
            opa_config = config.wasm_file_definitions.get(label)
            if not opa_config:
                raise ValueError("OPA policy file not found")
            wasm_file_path = opa_config.wasm_file_path
            wasm_file_download_url = opa_config.wasm_file_download_url
            entrypoint = opa_config.entrypoint

        engine = context.profile_validator_factory.opa_engine_factory.get_opa_engine(
            wasm_file_path=wasm_file_path,
            wasm_file_download_url=wasm_file_download_url,
        )
        sub_jsonpath_expr = context.json_path_expressions.get(json_path)
        if not sub_jsonpath_expr:
            sub_jsonpath_expr = jsonpath_ng.parse(json_path)
            context.json_path_expressions[json_path] = sub_jsonpath_expr

        sub_input_value = [a.value for a in sub_jsonpath_expr.find(input_json)]
        if len(sub_input_value) == 1:
            sub_input_value = sub_input_value[0]
        elif len(sub_input_value) == 0:
            sub_input_value = None
        opa_input = OpaPolicyInput(
            policy_id=field_requirement.policy_id,
            value=sub_input_value,
            root=input_json,
            config=config,
            constraint=None,
        )
        input_data = opa_input.model_dump(by_alias=True)

        start = time.perf_counter()
        result = engine.evaluate(input_data=input_data, entrypoint=entrypoint)
        end = time.perf_counter()
        logger.debug("Policy Engine Execution time: %.6f seconds", (end - start))
        if result is None:
            raise ValueError("OPA policy decision is not valid")
        if isinstance(result, dict):
            result = [result]
        if not isinstance(result, list):
            raise ValueError("OPA policy decision is not valid")
        if not result:
            raise ValueError(
                "OPA policy decision is empty. "
                f"Check input policy id {field_requirement.policy_id} "
                f"and entrypoint: {entrypoint or '<default>'}"
            )
        messages_output = OpaPolicyMessagesOutput.model_validate(result[0])

        for item in messages_output.messages or []:
            added = context.message_collector.add_message(
                json_path=json_path,
                message=JsonProfileMessage(
                    code=field_requirement.code,
                    category=Category.PROFILE,
                    name="opa-field-requirement",
                    source=item.source,
                    message=item.message,
                    enforcement_level=field_requirement.enforcement_level,
                ),
            )
            if not added:
                break

    def validate_requirement(
        self,
        field_requirement: FieldRequirement | OpaFieldRequirement,
        json_path: JsonPath,
        input_json: dict,
        context: JsonProfileRunContext,
    ):
        runtime_config = context.runtime_config

        constraint_name = (
            field_requirement.value_constraint.type
            if field_requirement.value_constraint
            else "field-requirement"
        )
        if field_requirement.value_constraint:
            if runtime_config and runtime_config.skip_decimal_validations:
                if isinstance(field_requirement.value_constraint, DecimalConstraint):
                    logger.warning("Decimal validations are skipped for %s", json_path)
                    context.message_collector.add_message(
                        json_path=json_path,
                        message=JsonProfileMessage(
                            code=field_requirement.code,
                            source=json_path,
                            category=Category.PROFILE,
                            name=field_requirement.value_constraint.type,
                            enforcement_level=EnforcementLevel.RECOMMENDED,
                            message=f"{field_requirement.code} decimal validations "
                            f"are skipped for '{json_path}'",
                        ),
                    )
                    return
        jsonpath_expr = context.json_path_expressions.get(json_path)
        if not jsonpath_expr:
            jsonpath_expr = jsonpath_ng.parse(json_path)
            context.json_path_expressions[json_path] = jsonpath_expr

        matches = jsonpath_expr.find(input_json)
        if not matches:
            if field_requirement.match_is_required:
                context.message_collector.add_message(
                    json_path=json_path,
                    message=JsonProfileMessage(
                        code=field_requirement.code,
                        source=json_path,
                        category=Category.PROFILE,
                        name=constraint_name,
                        enforcement_level=field_requirement.enforcement_level,
                        message=f"There is no value with json path '{json_path}'",
                    ),
                )
        else:
            for x in matches or []:
                if context.message_collector.is_open(field_requirement.code):
                    break
                source = convert_full_path(x.full_path)
                if (
                    field_requirement.required_properties
                    or field_requirement.recommended_properties
                ) and not isinstance(x.value, Mapping):
                    context.message_collector.add_message(
                        json_path=source,
                        message=JsonProfileMessage(
                            code=field_requirement.code,
                            source=source,
                            category=Category.PROFILE,
                            name="property-check",
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
                        context.message_collector.add_message(
                            json_path=source,
                            message=JsonProfileMessage(
                                code=field_requirement.code,
                                source=source,
                                category=Category.PROFILE,
                                name="property-check",
                                enforcement_level=EnforcementLevel.REQUIRED,
                                message="Required property does not exist "
                                f"{fields} is not in object '{source}'",
                            ),
                        )
                    not_defined_fields = [
                        a
                        for a in field_requirement.recommended_properties or []
                        if a not in x.value
                    ]

                    if not_defined_fields:
                        fields = ", ".join(not_defined_fields)
                        context.message_collector.add_message(
                            json_path=source,
                            message=JsonProfileMessage(
                                code=field_requirement.code,
                                source=source,
                                category=Category.PROFILE,
                                name="property-check",
                                enforcement_level=EnforcementLevel.RECOMMENDED,
                                message="Recommended property does not exist. "
                                f"{fields} field(s) not in object '{source}'",
                            ),
                        )

                if field_requirement.value_constraint:
                    constraint = field_requirement.value_constraint
                    checker = self.profile_validator_factory.get_checker(constraint)
                    skip = False
                    if runtime_config and runtime_config.skip_decimal_validations:
                        if isinstance(constraint, DecimalConstraint):
                            skip = True

                    if not skip:
                        res = checker.validate_constraint(
                            constraint=field_requirement.value_constraint,
                            value=x.value,
                            root=input_json,
                            context=context,
                        )
                        if not res.is_valid:
                            context.message_collector.add_message(
                                json_path=source,
                                message=JsonProfileMessage(
                                    code=field_requirement.code,
                                    source=source,
                                    category=Category.PROFILE,
                                    name=field_requirement.value_constraint.type
                                    or "field-requirement",
                                    enforcement_level=field_requirement.enforcement_level,
                                    message=res.message,
                                ),
                            )
