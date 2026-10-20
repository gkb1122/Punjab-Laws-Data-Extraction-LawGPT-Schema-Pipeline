import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


BASE_URL = "https://punjablaws.punjab.gov.pk"
LAWS_URL = f"{BASE_URL}/en/get_laws"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    )
}

session = requests.Session()
session.headers.update(HEADERS)


def fetch_page(url):
    """Fetch a webpage and return BeautifulSoup."""

    response = session.get(url, timeout=30)
    response.raise_for_status()

    return BeautifulSoup(response.text, "html.parser")


def clean_text(value):
    """Clean whitespace from extracted text."""

    if not value:
        return None

    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)

    return value.strip() or None


def extract_law_metadata(container):
    """Extract law metadata."""

    metadata = {
        "category": None,
        "act_or_ordinance": None,
        "promulgation_date": None,
        "views": None,
        "last_updated": None,
    }

    if not container:
        return metadata

    text = clean_text(container.get_text(" ", strip=True))

    if not text:
        return metadata

    parts = [clean_text(x) for x in text.split("|")]
    parts = [x for x in parts if x]

    if parts:
        metadata["category"] = parts[0]

    for part in parts[1:]:
        lower = part.lower()

        if lower.startswith("act ") or lower.startswith("ordinance "):
            metadata["act_or_ordinance"] = part

        elif "promulgation date:" in lower:
            metadata["promulgation_date"] = clean_text(
                part.split(":", 1)[1]
            )

        elif lower.startswith("views:"):
            metadata["views"] = clean_text(
                part.split(":", 1)[1]
            )

        elif "last updated on:" in lower:
            metadata["last_updated"] = clean_text(
                part.split(":", 1)[1]
            )

    return metadata


def extract_laws_from_page(soup):
    """Extract actual law/article links."""

    laws = []
    seen_urls = set()

    links = soup.select('a[href*="/show_article/"]')

    for link in links:

        href = link.get("href")

        if not href:
            continue

        url = urljoin(BASE_URL, href)

        if "/show_article/" not in url:
            continue

        if url in seen_urls:
            continue

        title = clean_text(link.get_text(" ", strip=True))

        if not title:
            continue

        metadata_container = link.find_next_sibling(
            class_="artdets"
        )

        if metadata_container is None:
            parent = link.parent

            if parent:
                metadata_container = parent.find_next(
                    class_="artdets"
                )

        metadata = extract_law_metadata(
            metadata_container
        )

        laws.append(
            {
                "title": title,
                "url": url,
                **metadata,
            }
        )

        seen_urls.add(url)

    return laws


def find_next_page(soup, current_url):
    """Find next pagination page."""

    next_selectors = [
        'a[rel="next"]',
        'a[aria-label="Next"]',
        'a[title="Next"]',
        "a.next",
        "li.next a",
    ]

    for selector in next_selectors:

        link = soup.select_one(selector)

        if link and link.get("href"):
            return urljoin(
                current_url,
                link["href"]
            )

    for link in soup.find_all("a", href=True):

        text = clean_text(
            link.get_text(" ", strip=True)
        )

        if not text:
            continue

        if text.lower() in {
            "next",
            "next page",
            "›",
            "»",
            ">>",
        }:
            return urljoin(
                current_url,
                link["href"]
            )

    return None


def get_all_laws():
    """Scrape all laws."""

    print(
        f"[INFO] Fetching laws page: {LAWS_URL}"
    )

    all_laws = []
    seen_urls = set()
    visited_pages = set()

    current_url = LAWS_URL

    while current_url:

        if current_url in visited_pages:
            break

        visited_pages.add(current_url)

        print(
            f"[INFO] Scraping listing page: "
            f"{current_url}"
        )

        try:
            soup = fetch_page(current_url)

        except requests.RequestException as exc:
            print(
                f"[ERROR] Could not fetch listing page: "
                f"{exc}"
            )
            break

        page_laws = extract_laws_from_page(soup)

        new_count = 0

        for law in page_laws:

            if law["url"] in seen_urls:
                continue

            seen_urls.add(law["url"])
            all_laws.append(law)
            new_count += 1

        print(
            f"[INFO] Found {new_count} new laws."
        )

        next_url = find_next_page(
            soup,
            current_url
        )

        if not next_url:
            break

        if next_url in visited_pages:
            break

        current_url = next_url

    print(
        f"[INFO] Total unique laws found: "
        f"{len(all_laws)}"
    )

    return all_laws


def extract_pdf_url(soup, law_url):
    """
    Find the PDF URL using multiple methods.

    Checks:
    - direct PDF links
    - download links
    - object data
    - embed src
    - iframe src
    - data attributes
    - JavaScript/raw HTML
    """

    # --------------------------------------------------
    # 1. Look through ALL links
    # --------------------------------------------------

    for link in soup.find_all("a", href=True):

        href = link.get("href", "").strip()

        if not href:
            continue

        text = clean_text(
            link.get_text(" ", strip=True)
        ) or ""

        href_lower = href.lower()
        text_lower = text.lower()

        if (
            ".pdf" in href_lower
            or "pdf" in text_lower
            or "download" in text_lower
        ):
            pdf_url = urljoin(
                law_url,
                href
            )

            print(
                f"[PDF] Found from link: {pdf_url}"
            )

            return pdf_url

    # --------------------------------------------------
    # 2. Object tag
    # --------------------------------------------------

    for obj in soup.find_all("object"):

        for attribute in [
            "data",
            "src",
            "url",
        ]:

            value = obj.get(attribute)

            if value and (
                ".pdf" in value.lower()
                or "pdf" in value.lower()
            ):

                pdf_url = urljoin(
                    law_url,
                    value
                )

                print(
                    f"[PDF] Found from object: "
                    f"{pdf_url}"
                )

                return pdf_url

    # --------------------------------------------------
    # 3. Embed tag
    # --------------------------------------------------

    for embed in soup.find_all("embed"):

        for attribute in [
            "src",
            "data",
        ]:

            value = embed.get(attribute)

            if value and (
                ".pdf" in value.lower()
                or "pdf" in value.lower()
            ):

                pdf_url = urljoin(
                    law_url,
                    value
                )

                print(
                    f"[PDF] Found from embed: "
                    f"{pdf_url}"
                )

                return pdf_url

    # --------------------------------------------------
    # 4. iframe
    # --------------------------------------------------

    for iframe in soup.find_all("iframe"):

        src = iframe.get("src")

        if src and (
            ".pdf" in src.lower()
            or "pdf" in src.lower()
            or "download" in src.lower()
        ):

            pdf_url = urljoin(
                law_url,
                src
            )

            print(
                f"[PDF] Found from iframe: "
                f"{pdf_url}"
            )

            return pdf_url

    # --------------------------------------------------
    # 5. Search data-* attributes
    # --------------------------------------------------

    for tag in soup.find_all(True):

        for attribute, value in tag.attrs.items():

            if not isinstance(value, str):
                continue

            value_lower = value.lower()

            if (
                ".pdf" in value_lower
                or (
                    "pdf" in value_lower
                    and (
                        "download" in value_lower
                        or "file" in value_lower
                        or "document" in value_lower
                    )
                )
            ):

                pdf_url = urljoin(
                    law_url,
                    value
                )

                print(
                    f"[PDF] Found from attribute: "
                    f"{pdf_url}"
                )

                return pdf_url

    # --------------------------------------------------
    # 6. Search raw HTML for PDF URLs
    # --------------------------------------------------

    html = str(soup)

    patterns = [
        r'https?://[^"\'>\s]+\.pdf(?:\?[^"\'>\s]*)?',
        r'["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']',
        r'["\']([^"\']*pdf[^"\']*)["\']',
    ]

    for pattern in patterns:

        matches = re.findall(
            pattern,
            html,
            re.IGNORECASE
        )

        for match in matches:

            if isinstance(match, tuple):
                match = match[0]

            if not match:
                continue

            pdf_url = urljoin(
                law_url,
                match
            )

            print(
                f"[PDF] Found in HTML: "
                f"{pdf_url}"
            )

            return pdf_url

    print("[PDF] No PDF URL found.")

    return None


def extract_bookmark_id(soup):
    """Extract article/bookmark ID."""

    bookmark_id = None

    # Search scripts
    for script in soup.find_all("script"):

        script_text = script.string or script.get_text()

        if not script_text:
            continue

        patterns = [
            r'article_id\s*=\s*["\'](\d+)["\']',
            r'article_id["\']?\s*[:=]\s*["\']?(\d+)',
            r'bookmark_id\s*=\s*["\'](\d+)["\']',
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                script_text,
                re.IGNORECASE
            )

            if match:
                return int(match.group(1))

    # Fallback: numeric HTML id
    for tag in soup.find_all(id=True):

        tag_id = tag.get("id")

        if tag_id and re.fullmatch(
            r"\d+",
            str(tag_id)
        ):

            try:
                return int(tag_id)

            except ValueError:
                pass

    return bookmark_id


def scrape_law_details(law_url):
    """Scrape an individual law page."""

    print(
        f"[INFO] Scraping law: {law_url}"
    )

    soup = fetch_page(law_url)

    # --------------------------------------------------
    # Title
    # --------------------------------------------------

    title_tag = soup.find("h2")

    if title_tag:
        statute_name = clean_text(
            title_tag.get_text(
                " ",
                strip=True
            )
        )
    else:
        statute_name = None

    # --------------------------------------------------
    # PDF
    # --------------------------------------------------

    pdf_url = extract_pdf_url(
        soup,
        law_url
    )

    # --------------------------------------------------
    # Bookmark ID
    # --------------------------------------------------

    bookmark_id = extract_bookmark_id(
        soup
    )

    # --------------------------------------------------
    # Metadata
    # --------------------------------------------------

    category = None
    act_or_ordinance = None
    promulgation_date = None

    metadata_blocks = soup.select(
        ".artdets"
    )

    if metadata_blocks:

        metadata = extract_law_metadata(
            metadata_blocks[0]
        )

        category = metadata[
            "category"
        ]

        act_or_ordinance = metadata[
            "act_or_ordinance"
        ]

        promulgation_date = metadata[
            "promulgation_date"
        ]

    # --------------------------------------------------
    # Year
    # --------------------------------------------------

    year = None

    year_match = re.search(
        r"\b(18|19|20)\d{2}\b",
        statute_name or ""
    )

    if year_match:
        year = int(
            year_match.group(0)
        )

    if year is None and act_or_ordinance:

        year_match = re.search(
            r"\b(18|19|20)\d{2}\b",
            act_or_ordinance
        )

        if year_match:
            year = int(
                year_match.group(0)
            )

    # --------------------------------------------------
    # HTML
    # --------------------------------------------------

    body = soup.find("body")

    statute_html = (
        str(body)
        if body
        else str(soup)
    )

    # --------------------------------------------------
    # Article text
    # --------------------------------------------------

    article_body = soup.select_one(
        ".article_body"
    )

    if article_body:

        statute_text = clean_text(
            article_body.get_text(
                "\n",
                strip=True
            )
        )

    else:

        statute_text = None

    # --------------------------------------------------
    # Type
    # --------------------------------------------------

    statute_type = "Act"

    if (
        statute_name
        and "ORDINANCE"
        in statute_name.upper()
    ):
        statute_type = "Ordinance"

    elif (
        statute_name
        and "BILL"
        in statute_name.upper()
    ):
        statute_type = "Bill"

    # --------------------------------------------------
    # Result
    # --------------------------------------------------

    return {
        "Statute_Name": statute_name,
        "Category": category,
        "Source": BASE_URL,
        "Statute_HTML": statute_html,
        "PDF_URL": pdf_url,
        "Statute": statute_text,
        "Year": year,
        "Promulgation_Date": promulgation_date,
        "Act_Ordinance": act_or_ordinance,
        "Section": None,
        "Definition": None,
        "Citations": [],
        "Statute_RAG_Content": None,
        "Textual_Metadata": None,
        "Statute_Type": statute_type,
        "Bookmark_ID": bookmark_id,
        "Province": "Punjab",
        "Source_URL": law_url,
    }


def main():

    laws = get_all_laws()

    if not laws:

        print(
            "[ERROR] No laws found."
        )

        return

    print(
        "\n[INFO] First 5 laws:\n"
    )

    for law in laws[:5]:

        print(
            f"Title: {law['title']}"
        )

        print(
            f"URL: {law['url']}"
        )

        print(
            f"Category: {law['category']}"
        )

        print(
            f"Act/Ordinance: "
            f"{law['act_or_ordinance']}"
        )

        print(
            f"Promulgation Date: "
            f"{law['promulgation_date']}"
        )

        print(
            f"Views: {law['views']}"
        )

        print(
            f"Last Updated: "
            f"{law['last_updated']}"
        )

        print("-" * 80)

    print(
        "\n[INFO] Testing first law details..."
    )

    details = scrape_law_details(
        laws[0]["url"]
    )

    print(
        f"Title: "
        f"{details['Statute_Name']}"
    )

    print(
        f"PDF URL: "
        f"{details['PDF_URL']}"
    )

    print(
        f"Article ID: "
        f"{details['Bookmark_ID']}"
    )


if __name__ == "__main__":
    main()