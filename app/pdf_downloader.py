import os
import re
import sys
import time

import requests

# Allow importing scraper.py when this file is run as:
# python app\pdf_downloader.py
sys.path.append(
    os.path.dirname(os.path.abspath(__file__))
)

from scraper import get_all_laws, scrape_law_details


BASE_URL = "https://punjablaws.punjab.gov.pk"
PDF_DIRECTORY = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "pdfs",
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    )
}

session = requests.Session()
session.headers.update(HEADERS)


def clean_filename(name):
    """
    Convert a law title into a safe Windows filename.
    """

    name = re.sub(
        r'[<>:"/\\|?*]',
        "",
        name
    )

    name = re.sub(
        r"\s+",
        " ",
        name
    )

    name = name.strip()

    if not name:
        name = "unknown_law"

    return name


def download_pdf(pdf_url, output_path):
    """
    Download one PDF.
    """

    try:

        response = session.get(
            pdf_url,
            timeout=60,
            stream=True
        )

        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type",
            ""
        ).lower()

        # Some servers don't correctly return
        # application/pdf, so don't reject the file
        # solely because of Content-Type.
        if (
            "text/html" in content_type
            and "application/pdf" not in content_type
        ):
            print(
                "[WARNING] Server returned HTML "
                "instead of PDF."
            )
            return False

        with open(
            output_path,
            "wb"
        ) as file:

            for chunk in response.iter_content(
                chunk_size=8192
            ):

                if chunk:
                    file.write(chunk)

        # Make sure we didn't create an empty file.
        if os.path.getsize(output_path) == 0:

            os.remove(output_path)

            print(
                "[WARNING] Downloaded file is empty."
            )

            return False

        return True

    except requests.RequestException as exc:

        print(
            f"[ERROR] PDF download failed: {exc}"
        )

        if os.path.exists(output_path):
            os.remove(output_path)

        return False

    except OSError as exc:

        print(
            f"[ERROR] Could not save PDF: {exc}"
        )

        return False


def main():

    # Create data/pdfs if it doesn't exist.
    os.makedirs(
        PDF_DIRECTORY,
        exist_ok=True
    )

    print(
        "[INFO] Getting laws from Punjab Laws website..."
    )

    laws = get_all_laws()

    print(
        f"[INFO] Found {len(laws)} laws."
    )

    if not laws:
        print(
            "[ERROR] No laws found."
        )
        return

    downloaded = 0
    skipped = 0
    failed = 0
    no_pdf = 0

    total = len(laws)

    for index, law in enumerate(
        laws,
        start=1
    ):

        title = law.get(
            "title"
        )

        law_url = law.get(
            "url"
        )

        print(
            f"\n[{index}/{total}] {title}"
        )

        if not law_url:

            print(
                "[WARNING] Law has no URL."
            )

            failed += 1
            continue

        # Get the individual article page.
        try:

            details = scrape_law_details(
                law_url
            )

        except Exception as exc:

            print(
                f"[ERROR] Could not scrape law page: "
                f"{exc}"
            )

            failed += 1
            continue

        pdf_url = details.get(
            "PDF_URL"
        )

        if not pdf_url:

            print(
                "[WARNING] This law does not have "
                "a PDF URL."
            )

            no_pdf += 1
            continue

        safe_title = clean_filename(
            title
        )

        output_filename = (
            f"{safe_title}.pdf"
        )

        output_path = os.path.join(
            PDF_DIRECTORY,
            output_filename
        )

        # If the file already exists, don't download
        # it again.
        if os.path.exists(output_path):

            file_size = os.path.getsize(
                output_path
            )

            if file_size > 0:

                print(
                    "[SKIP] PDF already exists."
                )

                skipped += 1
                continue

        print(
            f"[INFO] PDF URL: {pdf_url}"
        )

        success = download_pdf(
            pdf_url,
            output_path
        )

        if success:

            file_size = os.path.getsize(
                output_path
            )

            print(
                f"[SUCCESS] Downloaded: "
                f"{output_filename} "
                f"({file_size:,} bytes)"
            )

            downloaded += 1

        else:

            failed += 1

        # Small delay so we don't hammer the website.
        time.sleep(0.2)

    print("\n" + "=" * 70)
    print("PDF DOWNLOAD COMPLETE")
    print("=" * 70)

    print(
        f"Total laws:       {total}"
    )

    print(
        f"Downloaded:       {downloaded}"
    )

    print(
        f"Already existed:  {skipped}"
    )

    print(
        f"No PDF:           {no_pdf}"
    )

    print(
        f"Failed:           {failed}"
    )

    print(
        f"PDF directory:    {PDF_DIRECTORY}"
    )


if __name__ == "__main__":
    main()