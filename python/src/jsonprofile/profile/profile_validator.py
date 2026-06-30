import json
from pathlib import Path

import jsonpath_ng

from jsonprofile.profile.base import Category, JsonProfileMessage, MessageType
from jsonprofile.profile.model import (
    FieldRequirement,
    FieldRequirementGroup,
    JsonProfile,
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
                message_type=MessageType.ERROR,
                message="Profile file path is not defined.",
            )
        ]
    if isinstance(file_path, str):
        file_path = Path(file_path)
    if not isinstance(file_path, Path):
        return False, [
            JsonProfileMessage(
                category=Category.CROSS_CHECK,
                message_type=MessageType.ERROR,
                message="Input is not file path.",
            )
        ]
    try:
        profile_json = json.loads(file_path.read_text())
    except Exception as ex:
        return False, [
            JsonProfileMessage(
                category=Category.CROSS_CHECK,
                message_type=MessageType.ERROR,
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
                    message_type=MessageType.ERROR,
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
                    message_type=MessageType.ERROR,
                    message=f"Requirement '{key}' is not unique.",
                )
            )

        requirements = []
        if isinstance(definition, FieldRequirement):
            requirements = [definition]
        elif isinstance(definition, FieldRequirementGroup):
            requirements = definition.requirements
        elif definition is not None:
            messages.append(
                JsonProfileMessage(
                    category=Category.CROSS_CHECK,
                    message_type=MessageType.ERROR,
                    message=f"Requirement '{key}' value is not valid. "
                    "Define field requirement or field requirement group",
                )
            )
            continue
        for requirement in requirements:
            if not requirement.code:
                if isinstance(requirement, FieldRequirement):
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
                        message_type=MessageType.ERROR,
                        message=message,
                    )
                )
            else:
                if requirement.code in unique_requirement_codes:
                    messages.append(
                        JsonProfileMessage(
                            code=requirement.code or "",
                            category=Category.CROSS_CHECK,
                            message_type=MessageType.ERROR,
                            message=message,
                        )
                    )
                    message = (
                        f"Requirement {requirement.code} of '{key}' is not unique."
                    )
                unique_requirement_codes.add(requirement.code)

            if requirement.value_constraint:
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
                                        message_type=MessageType.ERROR,
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
                                    message_type=MessageType.ERROR,
                                    message=f"Requirement {requirement.code} json path "
                                    f"'{json_path}' of '{key}' is not valid. ",
                                )
                            )
    errors = [x for x in messages if x.message_type == MessageType.ERROR]
    success = False if errors else True
    return success, messages
