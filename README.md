# Punjab Laws Data Extraction & LawGPT Schema Pipeline

A Python-based legal data extraction and processing pipeline that collects legislation from the [Punjab Laws website](https://punjablaws.punjab.gov.pk/en/get_laws), downloads associated PDF documents, extracts text into Markdown, and transforms legal content into structured JSON records compatible with the LawGPT statute schema.

The project demonstrates an end-to-end workflow for **web scraping, document processing, legal text structuring, and schema validation**.

## Overview

Legal documents are often published as web pages and PDFs, making their content difficult to process consistently. This project automates the collection and transformation of Punjab legislation into structured, machine-readable data.

The pipeline:

- Scrapes law listings and metadata across paginated website results.
- Identifies individual law pages and associated PDF URLs.
- Downloads PDF documents with basic error handling and duplicate avoidance.
- Extracts page-level text and saves it as Markdown.
- Parses Markdown documents to identify legal sections, definitions, citations, and statute metadata.
- Generates individual JSON records following the LawGPT-compatible statute schema.
- Validates mandatory fields and reports files that fail processing.

## Architecture

```text
Punjab Laws Website
        |
        v
   scraper.py
   Web scraping
   Metadata extraction
        |
        v
   downloader.py
   PDF discovery and download
        |
        v
   data/pdfs/
   Downloaded documents
        |
        v
   pdf_extractor.py
   PDF text extraction
        |
        v
   data/markdown/
   Page-organized Markdown
        |
        v
   parser.py
   Text cleaning and legal parsing
        |
        v
   schema.py
   Schema creation and validation
        |
        v
   data/json/
   Structured statute records
```

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core implementation and data processing |
| Requests | HTTP requests and file downloads |
| BeautifulSoup4 | HTML parsing and web scraping |
| Regular expressions (`re`) | Metadata extraction, text cleaning, and legal pattern matching |
| pypdf | PDF text extraction |
| JSON | Structured data output |
| pathlib and os | File and directory management |

## Project Structure

```text
Punjab-Laws-Pipeline/
├── app/
│   ├── scraper.py
│   ├── downloader.py
│   ├── pdf_extractor.py
│   ├── parser.py
│   └── schema.py
│
├── data/
│   ├── pdfs/
│   ├── markdown/
│   └── json/
│
├── requirements.txt
└── README.md
```

The directory structure above reflects the paths used by the scripts. Create the directories as needed; the downloader, extractor, and parser create their respective output directories automatically when appropriate.

## Pipeline Workflow

### 1. Web Scraping — `scraper.py`

Collects law listings from the Punjab Laws website.

Key functionality:

- Traverses listing pages using pagination links.
- Extracts law titles, URLs, categories, legislative instrument details, promulgation dates, view counts, and last-updated dates.
- Removes duplicate law URLs.
- Discovers PDF URLs from individual law pages using multiple HTML elements and raw HTML pattern matching.
- Extracts available article text and metadata.
- Generates structured statute data with fields intended for the LawGPT schema.

### 2. PDF Downloading — `downloader.py`

Downloads the PDF documents associated with the discovered laws.

Features:

- Retrieves law listings and processes individual law pages.
- Sanitizes law titles for filenames.
- Streams downloads in chunks to reduce memory usage.
- Skips existing non-empty PDF files.
- Rejects HTML responses and empty downloads.
- Tracks successful downloads, skipped files, missing PDFs, and failures.
- Adds a short delay between download attempts.

Output directory: `data/pdfs/`

### 3. PDF-to-Markdown Extraction — `pdf_extractor.py`

Uses `pypdf` to extract text from downloaded PDF files.

Processing includes:

- Iterating through PDF pages and extracting available text.
- Normalizing whitespace and newline characters.
- Removing null characters and excessive blank lines.
- Preserving page boundaries through Markdown headings.
- Saving extracted content as UTF-8 Markdown files.
- Skipping Markdown files that already exist.
- Reporting extraction failures and documents without extractable text.

Example output:

```markdown
# Punjab Example Act 2025

## Page 1

An Act to provide for ...

## Page 2

1. Short title and commencement ...
```

Output directory: `data/markdown/`

**Note:** Text extraction is based on machine-readable PDF content. Scanned documents may require OCR, which is not implemented in the supplied extractor.

### 4. Legal Text Parsing — `parser.py`

Transforms Markdown documents into structured statute records.

The parser performs the following operations:

- Cleans text and corrects several common character-encoding issues.
- Extracts statute titles and likely enactment years.
- Detects promulgation dates and legislative instrument types.
- Parses page-level content and attempts to identify numbered legal sections.
- Extracts definitions from sections whose titles contain “definition”.
- Identifies common Pakistani legal citation formats.
- Generates bookmark identifiers and PDF URLs.
- Produces basic HTML from Markdown text.
- Calculates page, character, and word counts.
- Creates a JSON record for each successfully parsed Markdown document.
- Records processing failures for individual files without stopping the entire batch.

Output directory: `data/json/`

### 5. Schema Definition and Validation — `schema.py`

Defines the target statute record structure through `STATUTE_FIELDS`.

The schema includes fields such as:

- `Statute_Name`
- `Category`
- `Source`
- `Statute_HTML`
- `PDF_URL`
- `Statute`
- `Year`
- `Promulgation_Date`
- `Act_Ordinance`
- `Section`
- `Definition`
- `Citations`
- `Statute_RAG_Content`
- `Textual_Metadata`
- `Statute_Type`
- `Bookmark_ID`
- `Province`

The `create_statute()` function initializes records with the expected fields and rejects unknown field names. The `validate_statute()` function checks that designated mandatory fields are populated.

## Installation

### Prerequisites

- Python 3.10 or later recommended.
- Internet access to the source website.
- Sufficient local storage for PDF, Markdown, and JSON files.

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
cd YOUR_REPOSITORY
```

Replace the repository URL with your actual GitHub repository URL.

### 2. Create a virtual environment

Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

Create a `requirements.txt` file containing:

```text
requests
beautifulsoup4
pypdf
```

Then install the packages:

```bash
python -m pip install -r requirements.txt
```

## Running the Pipeline

Run the scripts from the project root directory.

### Step 1: Inspect scraped law listings

```bash
python app/scraper.py
```

This runs the scraper's current test workflow, displaying the first five laws and testing the details of the first law.

### Step 2: Download PDFs

```bash
python app/downloader.py
```

Downloads available PDFs into `data/pdfs/`.

### Step 3: Extract PDF text

```bash
python app/pdf_extractor.py
```

Converts downloaded PDFs into Markdown files under `data/markdown/`.

### Step 4: Parse Markdown into JSON

```bash
python -m app.parser
```

Parses Markdown documents and writes individual statute records into `data/json/`.

The module command assumes `app` is a Python package; add an empty `app/__init__.py` if needed.

**Execution order:** Run the downloader first, then the extractor, and finally the parser. The listing scraper is also used by the downloader to discover laws.

## Output Schema Example

A generated statute record has the following general structure:

```json
{
  "Statute_Name": "Example Punjab Act 2025",
  "Category": "Punjab Laws",
  "Source": "Example-Punjab-Act-2025.md",
  "Statute_HTML": "<h1>Example Punjab Act 2025</h1>",
  "PDF_URL": "https://punjablaws.punjab.gov.pk/uploads/articles/example-punjab-act-2025-pdf1.pdf",
  "Statute": "Extracted legal text...",
  "Year": 2025,
  "Promulgation_Date": null,
  "Act_Ordinance": "Act",
  "Section": [],
  "Definition": [],
  "Citations": [],
  "Statute_RAG_Content": "Extracted legal text...",
  "Textual_Metadata": {
    "page_count": 2,
    "character_count": 1200,
    "word_count": 200,
    "pages": []
  },
  "Statute_Type": "Act",
  "Bookmark_ID": "example-punjab-act-2025",
  "Province": "Punjab"
}
```

This is an illustrative example, not a record extracted from a particular law. Actual field values depend on the source document, and the example's metadata counts are placeholders.

## Error Handling and Limitations

The pipeline includes HTTP error handling, duplicate URL detection, existing-file checks, empty-download checks, per-page extraction warnings, and per-document parsing error reports.

Some limitations to be aware of:

- The scraper depends on the website's current HTML structure and pagination controls.
- PDF URL discovery may fail when documents are embedded through unsupported mechanisms.
- The downloader skips existing non-empty files without checking whether they are complete or up to date.
- `pypdf` does not perform OCR on scanned documents.
- Section and definition extraction uses regular expressions and may not correctly interpret every legal document format.
- Generated PDF URLs are based on normalized statute titles and may not match every actual PDF URL.
- The generated HTML is a basic representation of Markdown, not a full Markdown renderer.
- Schema validation checks field presence rather than legal correctness or completeness. Records without a detectable year can fail validation.
- The scripts do not currently demonstrate a unified orchestrator that automatically executes every stage in sequence.

## Future Improvements

Potential next steps include:

- Add retries with exponential backoff and more detailed logging.
- Improve PDF validation and recovery of failed downloads.
- Add OCR support for scanned legal documents.
- Improve legal section, definition, and citation extraction.
- Verify generated PDF URLs against the actual source URLs.
- Add automated tests for scraping, parsing, and schema validation.
- Introduce a pipeline-level runner to coordinate all stages.
- Add record-level quality checks and processing statistics.

## Data Source

Punjab Laws — Government of Punjab

https://punjablaws.punjab.gov.pk/en/get_laws

This project is intended for data engineering, document processing, and structured legal-data preparation. Extracted legal information should be checked against official source documents before being relied upon for legal interpretation.

## License

Add an appropriate license before distributing or reusing this project. Confirm the source website's terms and the applicable conditions for reproducing its content.
