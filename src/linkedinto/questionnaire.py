"""Interactive profile questionnaire over LinkedIn export data."""

from __future__ import annotations

from collections.abc import Callable

import typer
from rich.table import Table

from linkedinto.domain import LinkedInData, ProfileRow

# Field display order and labels for the questionnaire
_PROFILE_FIELDS = (
    "first_name",
    "last_name",
    "address",
    "zip_code",
    "geo_location",
    "occupation",
    "summary",
    "industry",
    "country",
    "country_code",
    "email_address",
    "phone_number",
    "twitter",
    "linkedin",
    "websites",
    "headline",
)


def _display_profile(profile: ProfileRow, table_cls: type[Table] | None = None) -> None:
    """Render profile as a rich.table.Table. Writes to stdout.

    Args:
        profile: ProfileRow to display.
        table_cls: Table class to use (defaults to rich.table.Table).
    """
    if table_cls is None:
        table_cls = Table

    table = table_cls()
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")

    if profile is None:
        table.add_row("(No profile data)", "")
    else:
        for field_name in _PROFILE_FIELDS:
            if field_name == "email_address":
                value = profile.email_address.address if profile.email_address else "(not set)"
            elif field_name == "phone_number":
                value = profile.phone_number.international if profile.phone_number else "(not set)"
            else:
                value = getattr(profile, field_name) or "(not set)"
            table.add_row(field_name.replace("_", " ").title(), str(value))

    table.print()


def _prompt_field_selection(prompt_fn: Callable[[str], str]) -> int:
    """Ask user which field to edit. Returns -1 to finish.

    Args:
        prompt_fn: Prompt function for testing (logically Typer.prompt).

    Returns:
        Index of selected field, or -1 if user chooses to finish.
    """
    typer.echo("\n=== Interactive Profile Editor ===")
    for i, field_name in enumerate(_PROFILE_FIELDS, start=1):
        field_display = field_name.replace("_", " ").title()
        typer.echo(f"{i}. {field_display}")
    typer.echo("\nSelect a field to edit, or press Enter to finish: ", nl=False)

    selection = prompt_fn("Select field number (1-16) or press Enter to finish: ", default="")

    if not selection.strip():
        return -1

    try:
        index = int(selection.strip()) - 1
        if 0 <= index < len(_PROFILE_FIELDS):
            return index
    except ValueError:
        pass

    typer.echo("Invalid selection. Please enter a number between 1 and 16, or press Enter to finish.")
    return -1


def _prompt_field_value(field: str, current: str | None | object, prompt_fn: Callable[[str], str]) -> str | None:
    """Prompt for a new value. Returns None to keep current, else new string.

    For special fields (email_address, phone_number), validates via Email.from_raw()
    and Phone.from_raw() respectively. Returns None on validation failure (re-prompt).

    Args:
        field: Field name to ask about.
        current: Current value as-is (email_address/phone_number are value objects).
        prompt_fn: Prompt function for testing (logically Typer.prompt).

    Returns:
        New string value to set, or None to keep the current value.
    """
    from linkedinto.email_utils import Email
    from linkedinto.phone_utils import Phone

    current_value = None
    if isinstance(current, (Email, Phone)):
        if isinstance(current, Email):
            current_value = str(current.address)
        else:  # Phone
            current_value = str(current.international)
    elif current is not None:
        current_value = str(current)

    if current_value and current_value != "(not set)":
        default_hint = f" [default: {current_value}]"
    else:
        default_hint = ""

    new_value_str = prompt_fn(f"{field.title()}: {default_hint}: ", default=current_value or "")

    if not new_value_str.strip():
        return current_value

    # Special field validation
    if field == "email_address":
        validated = Email.from_raw(new_value_str)
        if validated is None:
            typer.secho(
                "Invalid email. Please try again.", style="red"
            )
            return None
        return validated.address

    if field == "phone_number":
        validated = Phone.from_raw(new_value_str, default_region="US")
        if validated is None:
            typer.secho(
                "Invalid phone. Please try again.", style="red"
            )
            return None
        return validated.international

    # Regular string field
    return new_value_str


def _check_required_fields(profile: ProfileRow) -> None:
    """After all edits, check that name and email are set. Raises ValueError if any required field is missing.

    Args:
        profile: Updated profile to validate.

    Raises:
        ValueError: If required fields are missing.
    """
    if profile is None:
        return

    errors = []

    if not (profile.first_name or "").strip():
        errors.append("Missing required field: first_name")

    if not (profile.last_name or "").strip():
        errors.append("Missing required field: last_name")

    if profile.email_address is None and not (profile.email_address or "").strip():
        errors.append("Missing required field: email_address")

    if errors:
        typer.secho("\nValidation errors:", style="yellow")
        for error in errors:
            typer.secho(f"  - {error}", style="yellow")
        typer.echo(
            "Please run the questionnaire again to correct these errors, or remove the "
            "--no-interactive flag to interactively fix them.\n"
        )
        raise ValueError(", ".join(errors))


def run_questionnaire(
    profile: ProfileRow | LinkedInData,
    prompt_fn: Callable[[str], str] = typer.prompt,
) -> ProfileRow:
    """Orchestrates profile display and iterative editing.

    Args:
        profile: ProfileRow from parsed LinkedIn data (may be None).
        prompt_fn: Prompt function for testing, default is typer.prompt.

    Returns:
        Updated ProfileRow with user-upserted values. Original is not mutated.
    """
    if profile is None:
        typer.echo("No profile data to edit.")
        return None

    # Display current profile
    typer.echo("\nCurrent profile:")
    _display_profile(profile.profile if isinstance(profile, LinkedInData) else profile)

    editing = True
    while editing:
        field_index = _prompt_field_selection(prompt_fn)
        if field_index == -1:
            break

        field_name = _PROFILE_FIELDS[field_index]
        current_value = getattr(
            profile.profile if isinstance(profile, LinkedInData) else profile,
            field_name,
        )

        new_value = _prompt_field_value(field_name, current_value, prompt_fn)
        if new_value is None:
            continue

        # Mutate the existing ProfileRow in-place (pydantic dataclass behavior)
        if field_name == "email_address":
            new_value_obj = Email.from_raw(new_value)
            if new_value_obj:
                (profile.profile if isinstance(profile, LinkedInData) else profile).email_address = new_value_obj
        elif field_name == "phone_number":
            new_value_obj = Phone.from_raw(new_value, default_region="US")
            if new_value_obj:
                (profile.profile if isinstance(profile, LinkedInData) else profile).phone_number = new_value_obj
        else:
            setattr(
                profile.profile if isinstance(profile, LinkedInData) else profile,
                field_name,
                new_value,
            )

        # Re-display after update
        typer.echo("\nUpdated profile:")
        _display_profile(profile.profile if isinstance(profile, LinkedInData) else profile)

    # Validate required fields
    if isinstance(profile, LinkedInData):
        _check_required_fields(profile.profile)
    else:
        _check_required_fields(profile)

    return profile.profile if isinstance(profile, LinkedInData) else profile
