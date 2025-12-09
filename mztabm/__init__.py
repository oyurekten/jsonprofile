import json
import pathlib
from typing import Annotated, Any, Optional

import yaml
from pydantic import Field, ValidationError
from typing_extensions import Literal

from mztabm.model.mztabm import MzTabM
from mztabm.model.serialization import SerializationContext
from mztabm.model.validation import (
    Category,
    MessageType,
    ValidationMessage,
    ValidationSummary,
)


class MzTabMLoadResult(ValidationSummary):
    """Result object containing the loaded MzTabM data and validation information.

    This class extends ValidationSummary to include the loading status and
    the parsed MzTabM object. It's used as the return type for loading and
    parsing operations to provide both the result and any validation messages
    or errors that occurred during the process.
    """

    success: Annotated[
        bool,
        Field(
            default=False,
            description="Indicates whether the loading operation was successful",
        ),
    ] = None

    mztabm: Annotated[
        Optional[MzTabM],
        Field(
            default=None,
            description="The loaded and validated MzTabM object, if successful",
        ),
    ] = None


def read(
    file_path: str, format: Literal["tsv", "json", "yaml"] = "tsv"
) -> MzTabMLoadResult:
    """Read and parse an mzTab-M file in TSV, JSON, or YAML format.

    This function reads an mzTab-M formatted file and attempts to parse it into an MzTabM object.
    The parsing includes validation of the content against the mzTab-M specification.

    Args:
        file_path: Path to the mzTab-M file to read.
        format: The format of the input file. One of:
            - "tsv": Tab-separated values (default)
            - "json": JSON format
            - "yaml": YAML format

    Returns:
        MzTabMLoadResult containing:
            - success: Boolean indicating if parsing was successful
            - mztabm: The parsed MzTabM object if successful, None otherwise
            - messages: List of validation messages or errors encountered

    Raises:
        ValueError: If file_path is empty or format is invalid
        FileNotFoundError: If the specified file does not exist

    Example:
        >>> result = read("example.mztab", format="tsv")
        >>> if result.success:
        ...     mztabm = result.mztabm
        ...     print(f"Loaded mzTab-M file with {len(result.messages)} messages")
        ... else:
        ...     print("Failed to load file")
        ...     for msg in result.messages:
        ...         print(f"{msg.message_type}: {msg.message}")
    """
    if not file_path:
        raise ValueError("Invalid file path")
    if not format:
        raise ValueError("Invalid file format.")

    input_path = pathlib.Path(file_path)
    if not input_path.exists():
        raise ValueError("Input file does not exist.")

    if format == "tsv":
        content = input_path.read_text()
        result = MzTabMLoadResult(success=False, messages=[], source_format="tsv")
        try:
            mztabm = MzTabM.model_validate(content, by_alias=True, context=result)
            result.mztabm = mztabm
            result.success = True
        except ValidationError as ex:
            result.messages.extend(
                [
                    ValidationMessage(
                        category=Category.FORMAT,
                        message_type=MessageType.ERROR,
                        message=repr(x),
                    )
                    for x in ex.errors()
                ]
            )
        return result
    elif format == "json":
        with input_path.open() as f:
            content = json.load(f)
    elif format == "yaml":
        with input_path.open() as f:
            content = yaml.safe_load(f)
    else:
        raise ValueError(f"invalid format type: {format}")

    return load_from_dict(content)


def write(
    mztabm: MzTabM, file_path: str, format: Literal["tsv", "json", "yaml"] = "tsv"
) -> bool:
    """Write an MzTabM object to a file in TSV, JSON, or YAML format.

    This function serializes an MzTabM object to the specified format and writes it to a file.
    The target directory will be created if it doesn't exist.

    Args:
        mztabm: The MzTabM object to serialize
        file_path: Path where the file should be written
        format: The desired output format. One of:
            - "tsv": Tab-separated values (default)
            - "json": JSON format
            - "yaml": YAML format

    Returns:
        bool: True if the file was successfully written

    Raises:
        ValueError: If mztabm is None, file_path is empty, or format is invalid

    Example:
        >>> mztabm = read("example.mztab")
        >>> success = write(mztabm, "output.mztab")
        >>> if success:
        ...     print("File written successfully")
        ... else:
        ...     print("Failed to write file")
    """
    if not mztabm:
        raise ValueError("Invalid mzTab-M input")
    if not file_path:
        raise ValueError("Invalid file path")
    if not format:
        raise ValueError("Invalid file format.")

    if format == "tsv":
        result = mztabm.model_dump(
            context=SerializationContext(convert_to=format),
            by_alias=True,
            exclude_none=True,
        )
    elif format in {"json", "yaml"}:
        result = mztabm.model_dump_json(
            context=SerializationContext(convert_to="json"),
            by_alias=True,
            indent=2,
            exclude_none=True,
        )
        if format == "yaml":
            json_obj = json.loads(result)
            result = yaml.safe_dump(json_obj, sort_keys=False)

    target_path = pathlib.Path(file_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(file_path).write_text(result)
    return True


def load_from_dict(data: dict[str, Any]) -> MzTabMLoadResult:
    """Load and validate an MzTabM object from a dictionary.

    This function takes a dictionary representation of an mzTab-M file and attempts to
    validate and convert it into an MzTabM object. The dictionary should follow the
    mzTab-M structure with proper field names and data types.

    Args:
        data: A dictionary containing mzTab-M data. The structure should match
             the mzTab-M specification with proper field names and nested objects.

    Returns:
        MzTabMLoadResult containing:
            - success: Boolean indicating if loading was successful
            - mztabm: The loaded MzTabM object if successful, None otherwise
            - messages: List of validation messages or errors encountered

    Example:
        >>> result = load_from_dict(data)
        >>> if result.success:
        ...     mztabm = result.mztabm
        ...     print("Data loaded successfully")
        ... else:
        ...     print("Validation failed:")
        ...     for msg in result.messages:
        ...         print(f"{msg.message_type}: {msg.message}")
    """
    result = MzTabMLoadResult(success=False, messages=[], source_format="json")
    try:
        mztabm = MzTabM.model_validate(data, by_alias=True, context=result)
        result.mztabm = mztabm
        result.success = True
    except ValidationError as ex:
        result.messages.extend(
            [
                ValidationMessage(
                    category=Category.FORMAT,
                    message_type=MessageType.ERROR,
                    message=repr(x),
                )
                for x in ex.errors()
            ]
        )
    except Exception as ex:
        result.messages.append(
            ValidationMessage(
                category=Category.FORMAT,
                message_type=MessageType.ERROR,
                message=str(ex),
            )
        )
    return result


def convert_to_dict(mztabm: MzTabM) -> dict[str, Any]:
    """Convert an MzTabM object to a dictionary representation.

    This function converts an MzTabM object into a dictionary format suitable for
    serialization to JSON or other formats. The conversion uses field aliases and
    excludes None values to create a clean representation.

    Args:
        mztabm: The MzTabM object to convert

    Returns:
        dict[str, Any]: Dictionary representation of the MzTabM object

    Raises:
        ValueError: If mztabm is None

    Example:
        >>> mztabm = read("example.mztab")
        >>> dict_data = convert_to_dict(mztabm)
        >>> print(f"Converted object with {len(dict_data)} top-level keys")
    """
    if not mztabm:
        raise ValueError("Invalid mzTab-M input")

    return mztabm.model_dump(
        context=SerializationContext(convert_to="json"),
        by_alias=True,
        exclude_none=True,
    )
