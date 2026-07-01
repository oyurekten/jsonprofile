import logging
from typing import Annotated, Optional

from pydantic import Field

from jsonprofile.profile.constraints.constraints import Constraint
from jsonprofile.validator.base import (
    ConstraintChecker,
    ProfileValidator,
    ProfileValidatorFactory,
)
from jsonprofile.validator.decorators import (
    DEFAULT_VALIDATOR_ID,
    REGISTERED_PROFILE_CHECKER_CLASSES,
)

logger = logging.getLogger(__name__)


ValidatorId = Annotated[
    None | str,
    Field(description="Profile validator identifier. None selects the default."),
]
ConstraintType = Annotated[
    str,
    Field(description="Constraint type discriminator handled by a checker."),
]
ConstraintName = Annotated[
    Optional[str],
    Field(description="Optional named checker for a constraint type."),
]
CheckerClass = Annotated[
    type[ConstraintChecker],
    Field(description="Constraint checker class to register."),
]
CheckerInstance = Annotated[
    ConstraintChecker,
    Field(description="Constraint checker instance to unregister."),
]


class DefaultProfileValidator(ProfileValidator):
    """Default profile validator backed by registered constraint checkers.

    The validator resolves checker classes by constraint type and optional
    constraint name, lazily instantiates them, and reuses checker instances
    for subsequent validations.
    """

    @staticmethod
    def get_registered_constraint_checkers(
        validator_id: None | str = None,
    ) -> dict[tuple[str, str], type["ConstraintChecker"]]:
        if not validator_id:
            validator_id = DEFAULT_VALIDATOR_ID
        return REGISTERED_PROFILE_CHECKER_CLASSES.get(validator_id) or {}

    def __init__(
        self,
        profile_validator_factory: Annotated[
            "ProfileValidatorFactory",
            Field(description="Factory that owns this profile validator."),
        ],
        id: ValidatorId = "default",
    ):
        """Create the default validator and load registered checker classes."""

        super().__init__(profile_validator_factory=profile_validator_factory, id=id)
        self.id: ValidatorId = id
        self._registry: Annotated[
            dict[tuple[str, str], type[ConstraintChecker]],
            Field(description="Registered checker classes keyed by type and name."),
        ] = {}
        self._checkers: Annotated[
            dict[tuple[str, str], ConstraintChecker],
            Field(description="Instantiated checker cache keyed by type and name."),
        ] = {}
        checkers = self.get_registered_constraint_checkers(self.get_id())
        for (constraint_type, name), checker in checkers.items():
            self.register_checker(
                constraint_type=constraint_type, constraint_name=name, checker=checker
            )

    def get_id(self) -> str:
        """Return this validator's identifier."""

        return self.id

    def get_checker(
        self,
        constraint: Annotated[
            Constraint,
            Field(description="Constraint whose checker should be resolved."),
        ],
    ) -> Optional[ConstraintChecker]:
        """Resolve the checker for a concrete constraint definition."""

        return self.get_checker_by_name(
            constraint_type=constraint.type, constraint_name=constraint.name
        )

    def get_checker_by_name(
        self, constraint_type: ConstraintType, constraint_name: ConstraintName
    ) -> Optional[ConstraintChecker]:
        """Resolve or instantiate a checker by constraint type and optional name."""

        key = (constraint_type, constraint_name or None)
        checker_class = self._registry.get(key)
        if checker_class:
            checker = self._checkers.get(key)
            if not checker:
                checker = checker_class()
                # checker.constraint_type = constraint_type
                # checker.constraint_name = constraint_name
                # checker.validator_id = self.get_id()
                self._checkers[key] = checker
            return checker
        else:
            raise ValueError(
                f"There is no checker class for '{constraint_type}, {constraint_name}'"
            )

    def register_checker(
        self,
        constraint_type: ConstraintType,
        constraint_name: ConstraintName,
        checker: CheckerClass,
    ) -> None:
        """Register a checker class for a constraint type/name pair."""

        self._registry[(constraint_type, constraint_name)] = checker

    def unregister_checker(self, checker: CheckerInstance) -> None:
        """Remove a checker instance and its registered class from this validator."""

        matches = [k for k, v in self._registry.items() if v == checker.__class__]
        for key in matches or []:
            del self._registry[key]
        matches = [k for k, v in self._checkers.items() if v == checker]
        for key in matches or []:
            del self._checkers[key]
