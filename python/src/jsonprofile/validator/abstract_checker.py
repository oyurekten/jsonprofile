from __future__ import annotations

import abc
import logging
from typing import TYPE_CHECKING, Any, Literal, Optional, Tuple

import jsonpath_ng

from jsonprofile.profile.base import JsonProfileBaseModel
from jsonprofile.profile.constraints.constraints import (
    Constraint,
    DecimalConstraint,
)

if TYPE_CHECKING:
    from jsonprofile.validator.context import JsonProfileRunContext

logger = logging.getLogger(__name__)


class ConstraintValidationResult(JsonProfileBaseModel):
    is_valid: bool
    message: Optional[str] = None


class ConstraintChecker(abc.ABC):
    validator_id: str | None = None
    name: str | None = None

    is_active: bool = True

    def __init__(self):
        # self.constraint_type = None
        # self.profile_validator_factory: ProfileValidatorFactory = None
        # self.constraint_name = None
        # context.json_path_expressions: dict[JsonPath, Any] = {}
        pass

    @abc.abstractmethod
    def validate(
        self,
        constraint: Constraint,
        value: Any,
        root: dict[str, Any],
        context: JsonProfileRunContext,
    ) -> Tuple[bool, Optional[str]]: ...

    def evaluate_precondition(
        self,
        constraint: Constraint,
        value: Any,
        root: dict[str, Any],
        context: JsonProfileRunContext,
    ) -> Tuple[bool, Optional[str]]:
        if not constraint.precondition or not constraint.precondition.evaluations:
            return True, "There in no precondition"

        runtime_config = context.runtime_config
        valid_conditions = []
        for evaluation in constraint.precondition.evaluations:
            json_path = evaluation.json_path or "$"

            if not json_path.startswith("$"):
                json_path = f"${json_path}"
            json_input = root if evaluation.root_value_evaluation else value
            checker = context.profile_validator_factory.get_checker(
                evaluation.constraint
            )

            json_expression = context.json_path_expressions.get(json_path)
            if not json_expression:
                json_expression = jsonpath_ng.parse(json_path)
                context.json_path_expressions[json_path] = json_expression

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
                    evaluation.constraint, matches, root=root, context=context
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
        root: dict[str, Any],
        context: JsonProfileRunContext,
    ) -> ConstraintValidationResult:
        """Dispatcher to route validation to the specific constraint validator."""
        checker = context.profile_validator_factory.get_checker(constraint)

        if checker:
            success, message = checker.evaluate_precondition(
                constraint, value, root=root, context=context
            )

            sub_value = self.get_json_path_value(constraint, value, context)
            if success:
                is_valid, message = checker.validate(
                    constraint, sub_value, root=root, context=context
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

    def get_json_path_value(
        self, constraint: Constraint, value: Any, context: JsonProfileRunContext
    ):
        sub_input_value = value

        if constraint.json_path:
            sub_jsonpath = constraint.json_path
            if not sub_jsonpath.startswith("$"):
                if sub_jsonpath.startswith("[") or sub_jsonpath.startswith("."):
                    sub_jsonpath = f"${sub_jsonpath}"
                elif not sub_jsonpath.startswith("."):
                    sub_jsonpath = f"$.{sub_jsonpath}"
            sub_jsonpath_expr = context.json_path_expressions.get(sub_jsonpath)
            if not sub_jsonpath_expr:
                sub_jsonpath_expr = jsonpath_ng.parse(sub_jsonpath)
                context.json_path_expressions[sub_jsonpath] = sub_jsonpath_expr

            sub_input_value = [a.value for a in sub_jsonpath_expr.find(value)]
            if len(sub_input_value) == 1:
                sub_input_value = sub_input_value[0]
            elif len(sub_input_value) == 0:
                sub_input_value = None
        return sub_input_value
