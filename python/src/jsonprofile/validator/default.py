import logging
from typing import Annotated, Any, Optional

from pydantic import Field

from jsonprofile.profile.constraints import Constraint
from jsonprofile.profile.model import ProfileValidatorDefinition
from jsonprofile.validator.base import (
    ConstraintChecker,
    ProfileValidator,
    ProfileValidatorFactory,
    ProfileValidatorLoader,
)
from jsonprofile.validator.decorators import get_registered_constraint_checkers
from jsonprofile.validator.opa_engine import OpaEngineFactory

logger = logging.getLogger(__name__)

ValidatorId = Annotated[
    None | str,
    Field(description="Profile validator identifier. None selects the default."),
]
ValidatorLabel = Annotated[
    None | str,
    Field(description="Human-readable validator label. None selects the default."),
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
CustomValidatorDefinitions = Annotated[
    Optional[list[ProfileValidatorDefinition]],
    Field(description="Custom profile validator definitions available to the factory."),
]
ValidatorLoader = Annotated[
    None | ProfileValidatorLoader,
    Field(description="Loader used to instantiate custom profile validators."),
]
OpaFactory = Annotated[
    Optional[OpaEngineFactory],
    Field(description="Factory used by validators that evaluate OPA policies."),
]


class DefaultProfileValidator(ProfileValidator):
    """Default profile validator backed by registered constraint checkers.

    The validator resolves checker classes by constraint type and optional
    constraint name, lazily instantiates them, and reuses checker instances
    for subsequent validations.
    """

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
        checkers = get_registered_constraint_checkers(self.get_id())
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
                checker.profile_validator_factory = self.profile_validator_factory
                checker.constraint_type = constraint_type
                checker.constraint_name = constraint_type
                checker.validator_id = self.get_id()
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


class DefaultProfileValidatorFactory(ProfileValidatorFactory):
    """Factory that manages default and custom profile validators."""

    def __init__(
        self,
        custom_validator_definitions: CustomValidatorDefinitions = None,
        default_profile_validator_id: ValidatorId = None,
        validator_loader: ValidatorLoader = None,
        opa_engine_factory: OpaFactory = None,
        **kwargs: Annotated[Any, Field(description="Additional factory arguments.")],
    ):
        """Create a validator factory and register the built-in default validator."""

        super().__init__(
            custom_validator_definitions=custom_validator_definitions,
            default_profile_validator_id=default_profile_validator_id,
            opa_engine_factory=opa_engine_factory,
            **kwargs,
        )
        if not validator_loader:
            validator_loader = ProfileValidatorLoader(
                validator_definitions=custom_validator_definitions
            )
        self._validator_definitions: Annotated[
            dict[str, ProfileValidatorDefinition],
            Field(description="Validator definitions keyed by validator id."),
        ] = {x.validator_id: x for x in custom_validator_definitions or []}
        self._profile_validators: Annotated[
            dict[str, ProfileValidator],
            Field(description="Loaded profile validators keyed by validator id."),
        ] = {}
        self._validator_labels: Annotated[
            dict[str, str],
            Field(description="Validator labels keyed by validator id."),
        ] = {}
        self._validator_ids_by_label: Annotated[
            dict[str, str],
            Field(description="Validator ids keyed by label."),
        ] = {}

        self.validator_loader: ValidatorLoader = validator_loader
        base = DefaultProfileValidator(profile_validator_factory=self)
        self._profile_validators[base.get_id()] = base
        base_label = ""
        base_class_path = (
            DefaultProfileValidator.__module__ + "." + DefaultProfileValidator.__name__
        )
        self._validator_definitions[self.default_profile_validator_id] = (
            ProfileValidatorDefinition(
                label=base_label,
                validator_id=base.get_id(),
                profile_validator_class={"python": base_class_path},
            )
        )
        self._validator_labels[self.default_profile_validator_id] = base_label
        self._validator_ids_by_label[base_label] = self.default_profile_validator_id
        if not default_profile_validator_id:
            self.default_profile_validator_id = base.get_id()

        for definition in self.custom_validator_definitions:
            default = self.default_profile_validator_id == definition.validator_id
            self.register_profile_validator(definition=definition, default=default)

        # for validator_id, checkers in self.initial_checker_classes.items():

    def get_validator_by_label(self, label: ValidatorLabel) -> None | ProfileValidator:
        """Return the validator registered for a label, loading it if needed."""

        if not label:
            validator_id = self.default_profile_validator_id
        else:
            validator_id = self._validator_ids_by_label.get(label)
        profile_validator = self._profile_validators.get(validator_id)
        if not profile_validator:
            definition = self._validator_definitions.get(validator_id)
            if definition:
                validator = self.validator_loader.load_validator(definition)
                self._profile_validators[definition.validator_id] = validator
                self._validator_labels[definition.validator_id] = definition.label
                self._validator_ids_by_label[definition.label] = definition.validator_id

                profile_validator = validator
        return profile_validator

    def get_validator_by_id(self, validator_id: ValidatorId) -> None | ProfileValidator:
        """Return the validator registered for an id, loading it if needed."""

        if not validator_id:
            validator_id = self.default_profile_validator_id

        profile_validator = self._profile_validators.get(validator_id)
        if not profile_validator:
            definition = self._validator_definitions.get(validator_id)
            if definition:
                validator = self.validator_loader.load_validator(definition)
                self._profile_validators[definition.validator_id] = validator
                self._validator_labels[definition.validator_id] = definition.label
                self._validator_ids_by_label[definition.label] = definition.validator_id

                profile_validator = validator
        return profile_validator

    def get_checker(
        self,
        constraint: Annotated[
            Constraint,
            Field(description="Constraint whose checker should be resolved."),
        ],
    ) -> Optional[ConstraintChecker]:
        """Resolve a checker using the validator referenced by the constraint."""

        validator = self.get_validator_by_id(validator_id=constraint.validator)
        if not validator:
            raise ValueError(f"Validator is not found for {constraint.validator}")
        return validator.get_checker(constraint=constraint)

    def get_checker_by_name(
        self,
        constraint_type: ConstraintType,
        constraint_name: ConstraintName = None,
        validator_id: ValidatorId = None,
    ) -> Optional[ConstraintChecker]:
        """Resolve a checker by validator id, constraint type, and optional name."""

        validator = self.get_validator_by_id(validator_id=validator_id)
        if not validator:
            raise ValueError(f"Validator is not found for {validator_id}")
        return validator.get_checker_by_name(
            constraint_type=constraint_type, constraint_name=constraint_name
        )

    def register_profile_validator(
        self,
        definition: Annotated[
            ProfileValidatorDefinition,
            Field(description="Profile validator definition to register."),
        ],
        default: Annotated[
            bool,
            Field(description="Whether this validator should become the default."),
        ] = False,
    ) -> ProfileValidator:
        """Load and register a profile validator definition."""

        profile_validator = self.validator_loader.load_validator(definition)
        self._profile_validators[definition.validator_id] = profile_validator
        self._validator_labels[definition.validator_id] = definition.label
        self._validator_ids_by_label[definition.label] = definition.validator_id
        logger.info(
            "%s name: %s class: %s is registered",
            definition.label,
            definition.validator_id,
            definition.profile_validator_class,
        )
        if default:
            self.default_profile_validator_id = definition.validator_id

        return profile_validator

    def unregister_profile_validator(self, validator_id: ValidatorId) -> None:
        """Remove a profile validator from the factory registries."""

        definition = self._validator_definitions.get(validator_id)
        if validator_id in self._profile_validators:
            del self._profile_validators[validator_id]
        if validator_id in self._validator_labels:
            del self._validator_labels[validator_id]
        if definition and definition.label in self._validator_ids_by_label:
            del self._validator_ids_by_label[definition.label]
