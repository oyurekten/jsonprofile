import importlib
import logging
from typing import Annotated, Any, Optional

from pydantic import Field

from jsonprofile.profile.constraints.constraints import Constraint
from jsonprofile.profile.model import ProfileValidatorDefinition
from jsonprofile.validator.base import (
    ConstraintChecker,
    ProfileValidator,
    ProfileValidatorFactory,
    ProfileValidatorLoader,
)
from jsonprofile.validator.default.profile_validator import DefaultProfileValidator
from jsonprofile.validator.opa_engine import OpaEngineFactory

logger = logging.getLogger(__name__)


class DefaultProfileValidatorLoader(ProfileValidatorLoader):
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


class DefaultProfileValidatorFactory(ProfileValidatorFactory):
    """Factory that manages default and custom profile validators."""

    def __init__(
        self,
        custom_validator_definitions: Annotated[
            Optional[list[ProfileValidatorDefinition]],
            Field(
                description="Custom profile validator definitions "
                "available to the factory."
            ),
        ] = None,
        default_profile_validator_id: Annotated[
            None | str,
            Field(
                description="Default Profile validator identifier. "
                "None selects the default."
            ),
        ] = None,
        profile_validator_loader: Annotated[
            None | DefaultProfileValidatorLoader,
            Field(description="Loader used to instantiate custom profile validators."),
        ] = None,
        opa_engine_factory: Annotated[
            Optional[OpaEngineFactory],
            Field(description="Factory used by validators that evaluate OPA policies."),
        ] = None,
        **kwargs: Annotated[Any, Field(description="Additional factory arguments.")],
    ):
        """Create a validator factory and register the built-in default validator."""

        super().__init__(
            custom_validator_definitions=custom_validator_definitions,
            default_profile_validator_id=default_profile_validator_id,
            opa_engine_factory=opa_engine_factory,
            **kwargs,
        )
        if not profile_validator_loader:
            profile_validator_loader = DefaultProfileValidatorLoader(
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

        self.profile_validator_loader = profile_validator_loader
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

    def get_validator_by_label(
        self,
        label: Annotated[
            None | str,
            Field(
                description="Human-readable validator label. None selects the default."
            ),
        ],
    ) -> None | ProfileValidator:
        """Return the validator registered for a label, loading it if needed."""

        if not label:
            validator_id = self.default_profile_validator_id
        else:
            validator_id = self._validator_ids_by_label.get(label)
        profile_validator = self._profile_validators.get(validator_id)
        if not profile_validator:
            definition = self._validator_definitions.get(validator_id)
            if definition:
                validator = self.profile_validator_loader.load_validator(definition)
                self._profile_validators[definition.validator_id] = validator
                self._validator_labels[definition.validator_id] = definition.label
                self._validator_ids_by_label[definition.label] = definition.validator_id

                profile_validator = validator
        return profile_validator

    def get_validator_by_id(
        self,
        validator_id: Annotated[
            None | str,
            Field(
                description="Profile validator identifier. None selects the default."
            ),
        ],
    ) -> None | ProfileValidator:
        """Return the validator registered for an id, loading it if needed."""

        if not validator_id:
            validator_id = self.default_profile_validator_id

        profile_validator = self._profile_validators.get(validator_id)
        if not profile_validator:
            definition = self._validator_definitions.get(validator_id)
            if definition:
                validator = self.profile_validator_loader.load_validator(definition)
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
        constraint_type: Annotated[
            str,
            Field(description="Constraint type discriminator handled by a checker."),
        ],
        constraint_name: Annotated[
            Annotated[
                Optional[str],
                Field(description="Optional named checker for a constraint type."),
            ],
            Field(description="Name of the constraint to resolve."),
        ] = None,
        validator_id: Annotated[
            None | str,
            Field(
                description="Profile validator identifier. None selects the default."
            ),
        ] = None,
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

        profile_validator = self.profile_validator_loader.load_validator(definition)
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

    def unregister_profile_validator(
        self,
        validator_id: Annotated[
            None | str,
            Field(
                description="Profile validator identifier. None selects the default."
            ),
        ],
    ) -> None:
        """Remove a profile validator from the factory registries."""

        definition = self._validator_definitions.get(validator_id)
        if validator_id in self._profile_validators:
            del self._profile_validators[validator_id]
        if validator_id in self._validator_labels:
            del self._validator_labels[validator_id]
        if definition and definition.label in self._validator_ids_by_label:
            del self._validator_ids_by_label[definition.label]
