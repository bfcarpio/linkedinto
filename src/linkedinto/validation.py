"""Validation error formatting with examples."""

from typing import Any

from pydantic import BaseModel, ValidationError


def _follow_ref(schema: dict[str, Any], ref_path: str) -> dict[str, Any]:
    """Follow a $ref to resolve the referenced definition."""
    parts = ref_path.split("/")  # ['#/$defs/AiConfig'] → ['#', '$defs', 'AiConfig']
    current = schema
    for part in parts[1:]:  # Skip '#'
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return {}
    return current


def format_validation_error(
    exc: ValidationError,
    model_cls: type[BaseModel] | None = None,
) -> list[str]:
    """Convert a Pydantic ValidationError into human-readable messages.

    Each message includes the field path, what went wrong, and an example of
    valid input when available.

    Args:
        exc: The validation error to format.
        model_cls: Optional model class to fetch examples from JSON schema.

    Returns:
        List of formatted error messages.
    """
    errors = exc.errors()
    messages = []

    # Fetch schema if model_cls is provided
    schema: dict[str, Any] | None = None
    if model_cls is not None:
        schema = model_cls.model_json_schema()

    for error in errors:
        loc = error["loc"]
        msg = error["msg"]

        # Build field path
        field_path_parts = []
        for part in loc:
            if isinstance(part, int):
                # Handle list indexing
                field_path_parts.append(f"[{part}]")
            else:
                field_path_parts.append(str(part))
        field_path = ".".join(field_path_parts)

        # Find example for this field
        example = None
        if schema is not None and isinstance(loc, tuple) and len(loc) > 0:
            # Start with top-level properties
            current = schema.get("properties", {})

            # Navigate through the location path
            for i, part in enumerate(loc):
                if isinstance(current, dict) and part in current:
                    field_def = current[part]

                    if "examples" in field_def:
                        # Found the field with examples
                        example = field_def["examples"]
                        break

                    # Handle nested models and $refs
                    if isinstance(field_def, dict):
                        # Check if this is nested within another model (not the final target)
                        if i < len(loc) - 1:
                            # Follow nested properties
                            if "properties" in field_def:
                                current = field_def["properties"]
                            elif "$ref" in field_def:
                                # Follow $ref to get definitions
                                defn = _follow_ref(schema, field_def["$ref"])
                                if isinstance(defn, dict) and "properties" in defn:
                                    current = defn["properties"]
                                else:
                                    current = {}
                                # After resolving $ref, we're now in the nested model's properties
                            else:
                                current = {}
                        else:
                            # This is the target field - check for examples
                            if "examples" in field_def:
                                example = field_def["examples"]
                                break
                else:
                    current = {}

        # Format message
        message = f"{field_path}: {msg}"
        if example is not None:
            # Convert example to string
            if isinstance(example, (list, dict)):
                example_str = str(example)
            else:
                example_str = str(example)
            message += f". Example: {example_str}"

        messages.append(message)

    return messages
