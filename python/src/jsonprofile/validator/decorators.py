import logging
from typing import Optional

from jsonprofile.profile.constraints.constraints import Constraint
from jsonprofile.validator.abstract_checker import ConstraintChecker

logger = logging.getLogger(__name__)

DEFAULT_VALIDATOR_ID = "default"
REGISTERED_PROFILE_CHECKER_CLASSES: dict[
    str, dict[tuple[str, str], type[ConstraintChecker]]
] = {}


def constraint_checker(
    constraint_class: type[Constraint],
    constraint_name: Optional[str] = None,
    validator_id: Optional[str] = None,
    is_active: bool = True,
):
    global REGISTERED_PROFILE_CHECKER_CLASSES
    if not validator_id:
        validator_id = DEFAULT_VALIDATOR_ID
    if validator_id not in REGISTERED_PROFILE_CHECKER_CLASSES:
        REGISTERED_PROFILE_CHECKER_CLASSES[validator_id] = {}

    def decorator(checker_class: type[ConstraintChecker]):
        if not issubclass(checker_class, ConstraintChecker):
            raise ValueError("Must be a subclass of ConstraintChecker")
        if not issubclass(constraint_class, Constraint):
            raise ValueError("Must be a subclass of Constraint")

        if not is_active:
            logger.debug(
                "Constraint checker '%s' is not active. Skipping...",
                constraint_class.__name__,
            )
            return
        checkers = REGISTERED_PROFILE_CHECKER_CLASSES[validator_id]
        constraint_type = constraint_class.model_fields.get("type").default
        if constraint_type == "custom" and not constraint_name:
            ValueError("constraint_name is required for a custom constraint")
        key = (constraint_type, constraint_name or None)
        if key in checkers:
            raise ValueError(
                f"{constraint_type} {constraint_name} checker is already in registry"
            )
        checkers[key] = checker_class
        logger.info(
            "Registering constraint checker '%s' %s %s",
            constraint_class.__name__,
            constraint_name,
            constraint_class.__name__,
        )
        return checker_class

    return decorator
