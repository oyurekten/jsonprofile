import abc
import importlib
import logging
from typing import Any, Literal, Optional, Tuple

import jsonpath_ng

from jsonprofile.profile.base import JsonPath, JsonProfileBaseModel
from jsonprofile.profile.constraints import (
    Constraint,
    DecimalConstraint,
)
from jsonprofile.profile.model import (
    JsonProfileConfiguration,
    ProfileValidatorDefinition,
    ValidationRuntimeConfiguration,
)
from jsonprofile.validator.opa_engine import OpaEngineFactory

logger = logging.getLogger(__name__)


class ConstraintValidationResult(JsonProfileBaseModel):
    is_valid: bool
    message: Optional[str] = None


class ConstraintChecker(abc.ABC):
    validator_id: str | None = None
    name: str | None = None

    is_active: bool = True

    def __init__(self):
        self.constraint_type = None
        self.profile_validator_factory: ProfileValidatorFactory = None
        self.constraint_name = None
        self._json_path_expressions: dict[JsonPath, Any] = {}

    @abc.abstractmethod
    def validate(
        self,
        constraint: Constraint,
        value: Any,
        root: None | dict[str, Any] = None,
        config: None | JsonProfileConfiguration = None,
        runtime_config: None | ValidationRuntimeConfiguration = None,
    ) -> Tuple[bool, Optional[str]]:
        raise NotImplementedError

    def evaluate_precondition(
        self,
        constraint: Constraint,
        value: Any,
        root: None | dict[str, Any] = None,
        config: None | JsonProfileConfiguration = None,
        runtime_config: None | ValidationRuntimeConfiguration = None,
    ) -> Tuple[bool, Optional[str]]:
        if not constraint.precondition or not constraint.precondition.evaluations:
            return True, "There in no precondition"
        valid_conditions = []
        for evaluation in constraint.precondition.evaluations:
            json_path = evaluation.json_path or "$"

            if not json_path.startswith("$"):
                json_path = f"${json_path}"
            json_input = root if evaluation.root_value_evaluation else value
            checker = self.profile_validator_factory.get_checker(evaluation.constraint)

            json_expression = self._json_path_expressions.get(json_path)
            if not json_expression:
                json_expression = jsonpath_ng.parse(json_path)
                self._json_path_expressions[json_path] = json_expression

            matches = [x.value for x in json_expression.find(json_input)]
            if len(matches) == 1:
                matches = matches[0]
            elif len(matches) == 0:
                matches = None
            skip = False
            if runtime_config and runtime_config.skip_decimal_validations:
                if isinstance(constraint, DecimalConstraint):
                    skip = True

            if not skip:
                res = checker.validate_constraint(
                    evaluation.constraint, matches, root=root
                )
                if res.is_valid:
                    valid_conditions.append(evaluation)
            # elif res.message:
            #     logger.info("%s", res.message)

        return self.evaluate_results(
            valid_items_count=len(valid_conditions),
            all_items_count=len(constraint.precondition.evaluations),
            default_evaluation=evaluation.default_evaluation,
            join_operator=evaluation.join_operator,
            min_valid=evaluation.min_valid,
            max_valid=evaluation.max_valid,
        )

    def evaluate_results(
        self,
        # condition: Constraint | Evaluation,
        valid_items_count: int,
        all_items_count: int,
        join_operator: Literal["and", "or"] = "and",
        min_valid: None | int = None,
        max_valid: None | int = None,
        default_evaluation: None | bool = None,
    ):
        if all_items_count == 0:
            success = default_evaluation if default_evaluation is not None else True
            return success, "No item found for evaluation"

        if join_operator == "and":
            message = "some conditions are not satisfied"
            if valid_items_count == all_items_count:
                return True, "all conditions are satisfied"
        else:
            message = "some conditions are satisfied"
            min_valid = min_valid if min_valid is not None else 1
            max_valid_constraints = (
                max_valid if max_valid is not None else all_items_count
            )
            min_valid_req = False
            max_valid_req = False
            messages = []
            if valid_items_count >= min_valid:
                min_valid_req = True
            else:
                messages.append("min valid conditions is not satisfied")
            if valid_items_count <= max_valid_constraints:
                max_valid_req = True
            else:
                messages.append("min valid conditions is not satisfied")
            if min_valid_req and max_valid_req:
                message = "all conditions are satisfied"
                return True, message
            message = ". ".join(messages)
        return False, message

    def validate_constraint(
        self,
        constraint: Constraint,
        value: Any,
        root: None | dict[str, Any] = None,
        config: None | JsonProfileConfiguration = None,
        runtime_config: None | ValidationRuntimeConfiguration = None,
    ) -> ConstraintValidationResult:
        """Dispatcher to route validation to the specific constraint validator."""
        checker = self.profile_validator_factory.get_checker(constraint)

        if checker:
            success, message = checker.evaluate_precondition(
                constraint, value, root=root
            )

            sub_value = self.get_json_path_value(constraint, value)
            if success:
                is_valid, message = checker.validate(
                    constraint,
                    sub_value,
                    root=root,
                    config=config,
                    runtime_config=runtime_config,
                )
            else:
                is_valid = True
                message = f"Precondition does not meet: {message}"
            return ConstraintValidationResult(
                is_valid=is_valid,
                message=message,
                constraint_name=getattr(constraint, "name", "unknown"),
            )

        return ConstraintValidationResult(
            is_valid=False,
            message=f"Unknown constraint type: {type(constraint)}",
            constraint_name=getattr(constraint, "name", "unknown"),
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
            sub_jsonpath_expr = self._json_path_expressions.get(sub_jsonpath)
            if not sub_jsonpath_expr:
                sub_jsonpath_expr = jsonpath_ng.parse(sub_jsonpath)
                self._json_path_expressions[sub_jsonpath] = sub_jsonpath_expr

            sub_input_value = [a.value for a in sub_jsonpath_expr.find(value)]
            if len(sub_input_value) == 1:
                sub_input_value = sub_input_value[0]
            elif len(sub_input_value) == 0:
                sub_input_value = None
        return sub_input_value


class ProfileValidator(abc.ABC):
    def __init__(self, profile_validator_factory: "ProfileValidatorFactory", id: str):
        self.id = id
        self.profile_validator_factory = profile_validator_factory

    def get_id(self) -> str:
        return self.id

    @abc.abstractmethod
    def get_checker(self, constraint: Constraint) -> Optional[ConstraintChecker]: ...

    @abc.abstractmethod
    def get_checker_by_name(
        self, constraint_type: str, constraint_name: Optional[str] = None
    ) -> Optional[ConstraintChecker]: ...

    @abc.abstractmethod
    def register_checker(
        self,
        constraint_type: str,
        checker: ConstraintChecker,
        constraint_name: Optional[str] = None,
    ) -> None: ...


class ProfileValidatorLoader:
    def __init__(
        self, validator_definitions: None | list[ProfileValidatorDefinition] = None
    ):
        self.loaded_validators: dict[str, ProfileValidator] = {}
        self.validator_definitions = validator_definitions
        for definition in self.validator_definitions or []:
            self.load_validator(definition)

    def load_validator(
        self, definition: ProfileValidatorDefinition
    ) -> ProfileValidator:
        profile_validator_class = definition.profile_validator_class
        if isinstance(profile_validator_class, dict):
            profile_validator_class = profile_validator_class.get("python")
        if not profile_validator_class:
            message = (
                f"Profile validator class is not defined for {definition.validator_id}"
            )
            logger.error(message)
            raise ValueError(message)
        parts = profile_validator_class.split(".")
        class_name = parts[-1]
        module_name = ".".join(parts[:-1])
        try:
            module_object = importlib.import_module(module_name)
            target_class = getattr(module_object, class_name)

        except Exception as ex:
            message = f"Error while loading {module_name}.{class_name}: {ex}"
            logger.error(message)
            raise ValueError(message)
        if not issubclass(target_class, ProfileValidator):
            message = f"Class {module_name}.{class_name} is not ProfileValidator class"
            logger.error(message)
            raise ValueError(message)
        instance = target_class()
        self.loaded_validators[definition.validator_id] = instance
        return instance


class ProfileValidatorFactory(abc.ABC):
    def __init__(
        self,
        custom_validator_definitions: Optional[list[ProfileValidatorDefinition]] = None,
        default_profile_validator_id: Optional[str] = None,
        opa_engine_factory: Optional[OpaEngineFactory] = None,
        **kwargs,
    ):
        self.custom_validator_definitions = custom_validator_definitions or []
        self.default_profile_validator_id = default_profile_validator_id
        self.opa_engine_factory = opa_engine_factory
        self.kwargs = kwargs

    @abc.abstractmethod
    def get_validator_by_label(self, label: str) -> Optional[ProfileValidator]: ...

    @abc.abstractmethod
    def get_validator_by_id(self, validator_id: str) -> Optional[ProfileValidator]: ...

    @abc.abstractmethod
    def get_checker(self, constraint: Constraint) -> Optional[ConstraintChecker]: ...

    def get_checker_by_name(
        self,
        constraint_type: str,
        constraint_name: Optional[str] = None,
        validator_id: Optional[str] = None,
    ) -> Optional[ConstraintChecker]: ...

    @abc.abstractmethod
    def register_profile_validator(
        self,
        definition: ProfileValidatorDefinition,
        default: bool = False,
    ) -> ProfileValidator: ...

    @abc.abstractmethod
    def unregister_profile_validator(self, validator_id: str) -> ProfileValidator: ...

    @staticmethod
    def get_profile_validator_factory(
        factory_class: str,
        custom_validator_definitions: Optional[list[ProfileValidatorDefinition]] = None,
        default_profile_validator_id: Optional[str] = None,
        **kwargs,
    ) -> "ProfileValidatorFactory":
        parts = factory_class.split(".")
        class_name = parts[-1]
        module_name = ".".join(parts[:-1])
        try:
            module_object = importlib.import_module(module_name)
            target_class = getattr(module_object, class_name)

        except Exception as ex:
            message = f"Error while loading {module_name}.{class_name}: {ex}"
            logger.error(message)
            raise ValueError(message)
        if not issubclass(target_class, ProfileValidatorFactory):
            message = (
                f"Class {module_name}.{class_name} is not ProfileValidatorFactory class"
            )
            logger.error(message)
            raise ValueError(message)
        instance = target_class(
            custom_validator_definitions=custom_validator_definitions,
            default_profile_validator_id=default_profile_validator_id,
            **kwargs,
        )
        return instance
