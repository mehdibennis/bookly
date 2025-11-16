from datetime import date as date_type


def parse_date(value: date_type | str | None | dict) -> date_type | None:
    """Parse input into a date object.

    Accepts:
    - datetime.date: returned as-is
    - ISO string (YYYY-MM-DD): parsed via fromisoformat
    - None/invalid: returns None
    """
    if value is None:
        return None
    # If already a date object, return it
    if isinstance(value, date_type):
        return value
    # If a string, try ISO format
    if isinstance(value, str) and value:
        try:
            return date_type.fromisoformat(value)
        except (ValueError, TypeError):
            return None
    # Any other type is unsupported
    return None
