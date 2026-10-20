import json
import re
import html
from pathlib import Path
from typing import Any

from .schema import create_statute, validate_statute


# =========================================================
# DIRECTORIES
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

MARKDOWN_DIR = BASE_DIR / "data" / "markdown"
JSON_DIR = BASE_DIR / "data" / "json"


# =========================================================
# CONSTANTS
# =========================================================

PDF_BASE_URL = (
    "https://punjablaws.punjab.gov.pk/uploads/articles/"
)


# =========================================================
# TEXT CLEANING
# =========================================================

def clean_text(text: str) -> str:
    """
    Clean Markdown/PDF-extracted text while preserving
    meaningful legal structure.
    """

    if not text:
        return ""

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    text = text.replace("\x00", "")

    # Common PDF encoding corrections
    replacements = {
        "â€“": "–",
        "â€”": "—",
        "â€˜": "‘",
        "â€™": "’",
        "â€œ": "“",
        "â€": "”",
        "â€¦": "…",
        "Â": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Normalize spaces but preserve line breaks
    text = re.sub(r"[ \t]+", " ", text)

    # Remove trailing whitespace
    text = "\n".join(
        line.rstrip()
        for line in text.split("\n")
    )

    # Prevent excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# =========================================================
# PDF URL
# =========================================================

def generate_pdf_url(title: str) -> str:
    """
    Generate the Punjab Laws PDF URL from the statute title.

    Example:
        ABDUL GHAFOOR NIAZI UNIVERSITY ACT 2025

    becomes:

        https://punjablaws.punjab.gov.pk/uploads/articles/
        abdul-ghafoor-niazi-university-act-2025-pdf1.pdf
    """

    slug = title.lower()

    # Remove unusual characters
    slug = re.sub(r"[^a-z0-9]+", "-", slug)

    # Remove duplicate hyphens
    slug = re.sub(r"-+", "-", slug)

    slug = slug.strip("-")

    return f"{PDF_BASE_URL}{slug}-pdf1.pdf"


# =========================================================
# TITLE
# =========================================================

def extract_title(
    text: str,
    markdown_path: Path,
) -> str:
    """
    Extract the first H1 Markdown heading.

    Falls back to filename if no H1 exists.
    """

    match = re.search(
        r"(?m)^\s*#\s+(.+?)\s*$",
        text,
    )

    if match:
        return clean_text(match.group(1))

    return clean_text(markdown_path.stem)


# =========================================================
# YEAR
# =========================================================

def extract_year(
    title: str,
    text: str,
) -> int | None:
    """
    Extract the most likely statute year.

    Preference:
        1. Title
        2. First 5,000 characters
    """

    match = re.search(
        r"\b(18|19|20)\d{2}\b",
        title,
    )

    if match:
        return int(match.group())

    match = re.search(
        r"\b(18|19|20)\d{2}\b",
        text[:5000],
    )

    if match:
        return int(match.group())

    return None


# =========================================================
# PROMULGATION DATE
# =========================================================

def extract_promulgation_date(
    text: str,
) -> str | None:
    """
    Extract common Pakistani statute dates.

    Example:
        [20th June, 1974]
    """

    patterns = [
        r"\[(\d{1,2}(?:st|nd|rd|th)?\s+"
        r"[A-Za-z]+\s*,\s*\d{4})\]",

        r"\[(\d{1,2}(?:st|nd|rd|th)?\s+"
        r"[A-Za-z]+\s+\d{4})\]",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return clean_text(match.group(1))

    return None


# =========================================================
# ACT / ORDINANCE / RULES / REGULATIONS
# =========================================================

def detect_act_or_ordinance(
    title: str,
    text: str,
) -> str | None:
    """
    Identify the legislative instrument type.
    """

    sample = (
        f"{title}\n{text[:3000]}"
    ).upper()

    if "ORDINANCE" in sample:
        return "Ordinance"

    if "ACT" in sample:
        return "Act"

    if "RULES" in sample:
        return "Rules"

    if "REGULATIONS" in sample:
        return "Regulations"

    return None


def detect_statute_type(
    title: str,
    text: str,
) -> str:
    """
    Return normalized statute type.
    """

    instrument = detect_act_or_ordinance(
        title,
        text,
    )

    if instrument:
        return instrument

    return "Law"


# =========================================================
# PAGE PARSING
# =========================================================

def extract_pages(
    text: str,
) -> list[dict[str, Any]]:
    """
    Extract page blocks generated by pdf_extractor.py.

    Expected:

        ## Page 1

        text...

        ## Page 2

        text...
    """

    pattern = re.compile(
        r"(?ms)"
        r"^##\s+Page\s+(\d+)\s*$"
        r"\n?"
        r"(.*?)"
        r"(?=^##\s+Page\s+\d+\s*$|\Z)"
    )

    pages = []

    for match in pattern.finditer(text):

        page_number = int(match.group(1))

        page_text = clean_text(
            match.group(2)
        )

        pages.append(
            {
                "page_number": page_number,
                "text": page_text,
            }
        )

    return pages


# =========================================================
# SECTION PARSING
# =========================================================

SECTION_PATTERN = re.compile(
    r"(?m)"
    r"^\s*"
    r"(\d+[A-Za-z]?(?:-[A-Za-z0-9]+)?)"
    r"\.\s+"
    r"([^\n]+?)"
    r"\s*$"
)


def extract_sections(
    text: str,
) -> list[dict[str, Any]]:
    """
    Detect top-level legal sections.

    Examples:

        1. Short title, commencement and application
        2. Definitions
        3. Tribunals
        3-A. Constitution of Benches
    """

    matches = list(
        SECTION_PATTERN.finditer(text)
    )

    sections = []

    for index, match in enumerate(matches):

        section_number = clean_text(
            match.group(1)
        )

        section_title = clean_text(
            match.group(2)
        )

        content_start = match.end()

        if index + 1 < len(matches):
            content_end = matches[
                index + 1
            ].start()
        else:
            content_end = len(text)

        section_text = clean_text(
            text[
                content_start:
                content_end
            ]
        )

        sections.append(
            {
                "section_number": section_number,
                "section_title": section_title,
                "text": section_text,
            }
        )

    return sections


# =========================================================
# DEFINITIONS
# =========================================================

def extract_definitions(
    sections: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """
    Extract definitions from sections whose title
    contains 'definition'.
    """

    definitions = []

    definition_pattern = re.compile(
        r"(?ms)"
        r"^\s*\(([a-z])\)\s*"
        r"[\"“]?(.+?)[\"”]?"
        r"\s+"
        r"(?:means|shall mean|includes)\s+"
        r"(.+?)"
        r"(?=\n\s*\([a-z]\)|\Z)",
        flags=re.IGNORECASE,
    )

    for section in sections:

        if "definition" not in (
            section["section_title"].lower()
        ):
            continue

        text = section["text"]

        for match in definition_pattern.finditer(
            text
        ):

            term = clean_text(
                match.group(2)
            )

            definition = clean_text(
                match.group(3)
            )

            if term and definition:

                definitions.append(
                    {
                        "term": term,
                        "definition": definition,
                    }
                )

    return definitions


# =========================================================
# CITATIONS
# =========================================================

def extract_citations(
    text: str,
) -> list[str]:
    """
    Detect common Pakistani legal citation formats.
    """

    patterns = [
        r"\bPLD\s+\d{4}\s+[A-Z]{2,}\s+\d+\b",
        r"\bSCMR\s+\d{4}\s+\d+\b",
        r"\bMLD\s+\d{4}\s+[A-Z]{2,}\s+\d+\b",
        r"\b\d{4}\s+[A-Z]{2,}\s+\d+\b",
    ]

    citations = set()

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        for citation in matches:

            citations.add(
                clean_text(citation)
            )

    return sorted(citations)


# =========================================================
# BOOKMARK ID
# =========================================================

def create_bookmark_id(
    title: str,
) -> str:
    """
    Generate stable URL/database-friendly identifier.
    """

    bookmark = title.lower()

    bookmark = re.sub(
        r"[^a-z0-9]+",
        "-",
        bookmark,
    )

    bookmark = bookmark.strip("-")

    return bookmark


# =========================================================
# BASIC HTML
# =========================================================

def markdown_to_basic_html(
    text: str,
) -> str:
    """
    Convert simple Markdown into basic HTML.
    """

    output = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        if line.startswith("# "):

            output.append(
                f"<h1>{html.escape(line[2:])}</h1>"
            )

        elif line.startswith("## "):

            output.append(
                f"<h2>{html.escape(line[3:])}</h2>"
            )

        else:

            output.append(
                f"<p>{html.escape(line)}</p>"
            )

    return "\n".join(output)


# =========================================================
# PARSE ONE MARKDOWN DOCUMENT
# =========================================================

def parse_markdown_file(
    markdown_path: Path,
) -> dict[str, Any]:
    """
    Parse one Markdown law into the statute schema.
    """

    raw_text = markdown_path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    text = clean_text(raw_text)

    if not text:
        raise ValueError(
            "Markdown file is empty."
        )

    # ---------------------------------------------
    # Basic metadata
    # ---------------------------------------------

    title = extract_title(
        text,
        markdown_path,
    )

    year = extract_year(
        title,
        text,
    )

    promulgation_date = (
        extract_promulgation_date(text)
    )

    act_or_ordinance = (
        detect_act_or_ordinance(
            title,
            text,
        )
    )

    statute_type = detect_statute_type(
        title,
        text,
    )

    bookmark_id = create_bookmark_id(
        title
    )

    # ---------------------------------------------
    # Structured content
    # ---------------------------------------------

    pages = extract_pages(text)

    sections = extract_sections(text)

    definitions = extract_definitions(
        sections
    )

    citations = extract_citations(
        text
    )

    # ---------------------------------------------
    # PDF URL
    # ---------------------------------------------

    pdf_url = generate_pdf_url(title)

    # ---------------------------------------------
    # Create statute
    # ---------------------------------------------

    statute = create_statute(

        Statute_Name=title,

        Category="Punjab Laws",

        Source=markdown_path.name,

        Statute_HTML=markdown_to_basic_html(
            text
        ),

        PDF_URL=pdf_url,

        Statute=text,

        Year=year,

        Promulgation_Date=promulgation_date,

        Act_Ordinance=act_or_ordinance,

        Section=sections,

        Definition=definitions,

        Citations=citations,

        Statute_RAG_Content=text,

        Textual_Metadata={
            "page_count": len(pages),
            "character_count": len(text),
            "word_count": len(text.split()),
            "pages": pages,
        },

        Statute_Type=statute_type,

        Bookmark_ID=bookmark_id,

        Province="Punjab",
    )

    # ---------------------------------------------
    # Validate
    # ---------------------------------------------

    validate_statute(statute)

    return statute


# =========================================================
# PARSE ALL MARKDOWN FILES
# =========================================================

def parse_all_markdown() -> None:
    """
    Parse every Markdown file in data/markdown/
    and create one JSON file in data/json/.
    """

    print("=" * 60)
    print("PUNJAB LAWS - MARKDOWN TO JSON")
    print("=" * 60)

    print(
        f"Markdown directory: {MARKDOWN_DIR}"
    )

    print(
        f"JSON directory:     {JSON_DIR}"
    )

    # ---------------------------------------------
    # Check directories
    # ---------------------------------------------

    if not MARKDOWN_DIR.exists():

        print(
            f"[ERROR] Markdown directory does not exist:"
        )

        print(MARKDOWN_DIR)

        return

    JSON_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ---------------------------------------------
    # Find Markdown files
    # ---------------------------------------------

    markdown_files = sorted(
        MARKDOWN_DIR.glob("*.md")
    )

    total = len(markdown_files)

    if total == 0:

        print(
            "[WARNING] No Markdown files found."
        )

        return

    print(
        f"Markdown files found: {total}"
    )

    print()

    # ---------------------------------------------
    # Counters
    # ---------------------------------------------

    parsed = 0
    failed = 0

    failed_files = []

    # ---------------------------------------------
    # Parse files
    # ---------------------------------------------

    for index, markdown_path in enumerate(
        markdown_files,
        start=1,
    ):

        try:

            statute = parse_markdown_file(
                markdown_path
            )

            json_path = (
                JSON_DIR
                / f"{markdown_path.stem}.json"
            )

            json_path.write_text(
                json.dumps(
                    statute,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            parsed += 1

            print(
                f"[{index}/{total}] OK: "
                f"{markdown_path.name}"
            )

        except Exception as error:

            failed += 1

            failed_files.append(
                {
                    "file": markdown_path.name,
                    "error": str(error),
                }
            )

            print(
                f"[{index}/{total}] FAILED: "
                f"{markdown_path.name}"
            )

            print(
                f"    ERROR: {error}"
            )

    # ---------------------------------------------
    # Summary
    # ---------------------------------------------

    print()
    print("=" * 60)
    print("PARSING COMPLETE")
    print("=" * 60)

    print(
        f"Total Markdown: {total}"
    )

    print(
        f"Parsed:         {parsed}"
    )

    print(
        f"Failed:         {failed}"
    )

    print(
        f"JSON directory: {JSON_DIR}"
    )

    if failed_files:

        print()
        print("FAILED FILES:")

        for item in failed_files:

            print(
                f"- {item['file']}"
            )

            print(
                f"  {item['error']}"
            )

    print("=" * 60)


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    parse_all_markdown()