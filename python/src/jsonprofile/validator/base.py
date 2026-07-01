import abc
import importlib
import logging
from typing import Optional

from jsonprofile.profile.base import CvTerm
from jsonprofile.profile.constraints.constraints import Constraint
from jsonprofile.profile.model import ProfileValidatorDefinition
from jsonprofile.validator.abstract_checker import ConstraintChecker
from jsonprofile.validator.opa_engine import OpaEngineFactory

logger = logging.getLogger(__name__)


class CvTermSearch(abc.ABC):
    @abc.abstractmethod
    def get_iri(self, cv_term: CvTerm) -> str | None: ...

    @abc.abstractmethod
    def get_curie(self, cv_term: CvTerm) -> str | None: ...

    @abc.abstractmethod
    def find_cv_term(
        self,
        source: str,
        accession_or_label: str,
        matched_accession: None | str = None,
        allow_synonym_search: bool = False,
    ) -> None | CvTerm: ...

    @abc.abstractmethod
    def check_cv_term(
        self,
        cv_term: CvTerm,
        parent_cv_term: None | CvTerm = None,
        allow_synonym_search: bool = False,
    ) -> tuple[bool, str]: ...

    @abc.abstractmethod
    def find_cv_term_with_accession(
        self, source: str, accession: str
    ) -> tuple[CvTerm, list[str]]: ...

    @abc.abstractmethod
    def get_children(
        self,
        cv_term: CvTerm,
        allow_only_leaf: bool = True,
        excluded_cv_accessions: None | list[str] = None,
        recursive: bool = False,
    ) -> list[CvTerm]: ...


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


class ProfileValidatorLoader(abc.ABC):
    @abc.abstractmethod
    def load_validator(
        self, definition: ProfileValidatorDefinition
    ) -> ProfileValidator: ...


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
