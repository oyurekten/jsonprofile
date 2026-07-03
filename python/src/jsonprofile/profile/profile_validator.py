from pathlib import Path

import jsonpath_ng
import orjson

from jsonprofile.profile.base import Category, EnforcementLevel, JsonProfileMessage
from jsonprofile.profile.model import (
    FieldRequirement,
    FieldRequirementGroup,
    JsonProfile,
    OpaFieldRequirement,
)


def validate_profile_file(
    file_path: str | Path,
) -> tuple[bool, list[JsonProfileMessage]]:
    """Validate a json profile file

    Args:
        file_path (str | Path): Profile file path

    Returns:
        tuple[bool, list[JsonProfileMessage]]: valid or not and related messages
    """
    if not file_path:
        return False, [
            JsonProfileMessage(
                category=Category.CROSS_CHECK,
                message="Profile file path is not defined.",
            )
        ]
    if isinstance(file_path, str):
        file_path = Path(file_path)
    if not isinstance(file_path, Path):
        return False, [
            JsonProfileMessage(
                category=Category.CROSS_CHECK,
                message="Input is not file path.",
            )
        ]
    try:
        profile_json = orjson.loads(file_path.read_bytes())
    except Exception as ex:
        return False, [
            JsonProfileMessage(
                category=Category.CROSS_CHECK,
                message=f"Profile file is not valid json file: {ex}",
            )
        ]
    return validate_profile(profile=profile_json)


def validate_profile(profile: dict | JsonProfile):
    validated_json_paths = set()
    if isinstance(profile, dict):
        try:
            profile: JsonProfile = JsonProfile.model_validate(profile, by_alias=True)
        except Exception as ex:
            return False, [
                JsonProfileMessage(
                    category=Category.CROSS_CHECK,
                    message=f"Profile json file format is not valid: {ex}",
                )
            ]
    messages: list[JsonProfileMessage] = []
    unique_keys = set()
    unique_requirement_codes = set()
    for key, definition in profile.requirements.items():
        if key in unique_keys:
            messages.append(
                JsonProfileMessage(
                    category=Category.CROSS_CHECK,
                    message=f"Requirement '{key}' is not unique.",
                )
            )

        requirements = []
        if isinstance(definition, (FieldRequirement, OpaFieldRequirement)):
            requirements = [definition]
        elif isinstance(definition, FieldRequirementGroup):
            requirements = definition.requirements
        elif definition is not None:
            messages.append(
                JsonProfileMessage(
                    category=Category.CROSS_CHECK,
                    message=f"Requirement '{key}' value is not valid. "
                    "Define field requirement or field requirement group",
                )
            )
            continue
        for requirement in requirements:
            is_opa_field_requirement = isinstance(requirement, OpaFieldRequirement)
            if not requirement.code:
                if isinstance(requirement, (FieldRequirement, OpaFieldRequirement)):
                    message = f"Requirement '{key}' code is not defined."
                else:
                    index = requirements.index(requirement)
                    message = (
                        f"Requirement '{key}' code (at index {index}) is not defined."
                    )

                messages.append(
                    JsonProfileMessage(
                        code=requirement.code or "",
                        category=Category.CROSS_CHECK,
                        message=message,
                    )
                )
            else:
                if requirement.code in unique_requirement_codes:
                    messages.append(
                        JsonProfileMessage(
                            code=requirement.code or "",
                            category=Category.CROSS_CHECK,
                            message=message,
                        )
                    )
                    message = (
                        f"Requirement {requirement.code} of '{key}' is not unique."
                    )
                unique_requirement_codes.add(requirement.code)

            if not is_opa_field_requirement and requirement.value_constraint:
                if requirement.value_constraint.precondition:
                    evaluations = requirement.value_constraint.precondition.evaluations

                    for evaluation in evaluations or []:
                        json_path = evaluation.json_path
                        if json_path not in validated_json_paths:
                            try:
                                jsonpath_ng.parse(json_path)
                                validated_json_paths.add(json_path)
                            except Exception:
                                index = evaluations.index(evaluation)
                                messages.append(
                                    JsonProfileMessage(
                                        code=requirement.code or "",
                                        category=Category.CROSS_CHECK,
                                        message=f"'{key}' requirement "
                                        f"{requirement.code} "
                                        "precondition evaluation (at index {index})"
                                        f" json path '{json_path}' of is not valid.",
                                    )
                                )

                if requirement.value_constraint.json_path:
                    json_path = requirement.value_constraint.json_path
                    if json_path not in validated_json_paths:
                        try:
                            jsonpath_ng.parse(json_path)
                            validated_json_paths.add(json_path)
                        except Exception:
                            messages.append(
                                JsonProfileMessage(
                                    code=requirement.code or "",
                                    category=Category.CROSS_CHECK,
                                    message=f"Requirement {requirement.code} json path "
                                    f"'{json_path}' of '{key}' is not valid. ",
                                )
                            )
    errors = [x for x in messages if x.enforcement_level == EnforcementLevel.REQUIRED]
    success = False if errors else True
    return success, messages
