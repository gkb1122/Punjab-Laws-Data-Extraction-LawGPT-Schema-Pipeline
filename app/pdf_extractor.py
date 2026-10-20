import os
import re
from pathlib import Path

from pypdf import PdfReader


# ---------------------------------------------------------
# DIRECTORIES
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

PDF_DIR = BASE_DIR / "data" / "pdfs"
MARKDOWN_DIR = BASE_DIR / "data" / "markdown"


# ---------------------------------------------------------
# TEXT CLEANING
# ---------------------------------------------------------

def clean_text(text: str) -> str:
    """
    Clean extracted PDF text while preserving useful
    paragraph and section structure.
    """

    if not text:
        return ""

    # Normalize different newline formats
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove null characters
    text = text.replace("\x00", "")

    # Remove excessive spaces/tabs
    text = re.sub(r"[ \t]+", " ", text)

    # Remove spaces at the beginning/end of lines
    text = "\n".join(line.strip() for line in text.split("\n"))

    # Collapse more than 2 consecutive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ---------------------------------------------------------
# PDF EXTRACTION
# ---------------------------------------------------------

def extract_pdf_to_markdown(pdf_path: Path, markdown_path: Path) -> bool:
    """
    Extract text from one PDF and save it as Markdown.

    Returns:
        True  -> extraction successful
        False -> extraction failed or PDF has no text
    """

    try:
        print(f"[INFO] Extracting: {pdf_path.name}")

        reader = PdfReader(str(pdf_path))

        if not reader.pages:
            print(f"[WARNING] No pages found: {pdf_path.name}")
            return False

        pages = []

        for page_number, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
                text = clean_text(text)

                if text:
                    pages.append(
                        f"## Page {page_number}\n\n{text}"
                    )

            except Exception as error:
                print(
                    f"[WARNING] Could not extract page "
                    f"{page_number} from {pdf_path.name}: {error}"
                )

        if not pages:
            print(
                f"[WARNING] No extractable text: {pdf_path.name}"
            )
            return False

        # -------------------------------------------------
        # Create Markdown document
        # -------------------------------------------------

        document_title = pdf_path.stem.replace("-", " ").strip()

        markdown_content = (
            f"# {document_title}\n\n"
            + "\n\n".join(pages)
            + "\n"
        )

        markdown_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        markdown_path.write_text(
            markdown_content,
            encoding="utf-8"
        )

        return True

    except Exception as error:
        print(
            f"[ERROR] Failed to extract "
            f"{pdf_path.name}: {error}"
        )
        return False


# ---------------------------------------------------------
# MAIN EXTRACTION PROCESS
# ---------------------------------------------------------

def extract_all_pdfs():
    """
    Extract all PDFs from data/pdfs/ into data/markdown/.
    """

    print("=" * 60)
    print("PDF TO MARKDOWN EXTRACTION")
    print("=" * 60)

    print(f"[INFO] PDF directory: {PDF_DIR}")
    print(f"[INFO] Markdown directory: {MARKDOWN_DIR}")

    # Check PDF directory
    if not PDF_DIR.exists():
        print(
            f"[ERROR] PDF directory does not exist: {PDF_DIR}"
        )
        return

    # Create Markdown directory
    MARKDOWN_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Find PDFs
    pdf_files = sorted(
        PDF_DIR.glob("*.pdf")
    )

    total = len(pdf_files)

    if total == 0:
        print("[WARNING] No PDF files found.")
        return

    print(f"[INFO] Found {total} PDF files.")
    print()

    extracted = 0
    already_existed = 0
    failed = 0

    for index, pdf_path in enumerate(pdf_files, start=1):

        markdown_path = MARKDOWN_DIR / (
            pdf_path.stem + ".md"
        )

        print(
            f"[{index}/{total}] {pdf_path.name}"
        )

        # -------------------------------------------------
        # Skip existing Markdown
        # -------------------------------------------------

        if markdown_path.exists():
            print(
                f"[INFO] Already exists: "
                f"{markdown_path.name}"
            )

            already_existed += 1
            continue

        # -------------------------------------------------
        # Extract PDF
        # -------------------------------------------------

        success = extract_pdf_to_markdown(
            pdf_path,
            markdown_path
        )

        if success:
            extracted += 1
            print(
                f"[SUCCESS] Created: "
                f"{markdown_path.name}"
            )
        else:
            failed += 1

        print()

    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    print("=" * 60)
    print("PDF EXTRACTION COMPLETE")
    print("=" * 60)

    print(f"Total PDFs:       {total}")
    print(f"Extracted:        {extracted}")
    print(f"Already existed:  {already_existed}")
    print(f"Failed:           {failed}")
    print(f"Markdown directory: {MARKDOWN_DIR}")
    print("=" * 60)


# ---------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------

if __name__ == "__main__":
    extract_all_pdfs()