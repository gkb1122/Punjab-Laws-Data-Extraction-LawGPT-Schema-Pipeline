from typing import Any


STATUTE_FIELDS = {
    "Statute_Name": None,
    "Category": None,
    "Source": None,
    "Statute_HTML": None,
    "PDF_URL": None,
    "Statute": None,
    "Year": None,
    "Promulgation_Date": None,
    "Act_Ordinance": None,
    "Section": None,
    "Definition": None,
    "Citations": [],
    "Statute_RAG_Content": None,
    "Textual_Metadata": None,
    "Statute_Type": None,
    "Bookmark_ID": None,
    "Province": None,
}


def create_statute(**kwargs: Any) -> dict:
    """
    Create a statute record using the project's required schema.
    """

    statute = {
        key: value.copy() if isinstance(value, list) else value
        for key, value in STATUTE_FIELDS.items()
    }

    for key, value in kwargs.items():
        if key not in STATUTE_FIELDS:
            raise ValueError(f"Unknown statute field: {key}")

        statute[key] = value

    return statute


def validate_statute(statute: dict) -> None:
    """
    Validate mandatory statute fields.
    """

    mandatory_fields = [
        "Statute_Name",
        "Source",
        "Statute_HTML",
        "Statute",
        "Year",
        "Section",
        "Definition",
        "Statute_Type",
        "Bookmark_ID",
    ]

    missing_fields = [
        field
        for field in mandatory_fields
        if statute.get(field) in (None, "")
    ]

    if missing_fields:
        raise ValueError(
            f"Missing mandatory statute fields: {', '.join(missing_fields)}"
        )