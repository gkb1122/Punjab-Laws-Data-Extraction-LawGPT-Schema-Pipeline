"""
PUNJAB LAWS - MongoDB

MongoDB database layer for the Punjab Laws project.

Features:
- Connects to MongoDB using MONGODB_URI from .env
- Imports JSON law files from data/json
- Uses upsert to prevent duplicate documents
- Creates indexes for searching
- Provides basic database operations
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, TEXT
from pymongo.errors import PyMongoError


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
JSON_DIR = BASE_DIR / "data" / "json"

load_dotenv(BASE_DIR / ".env")

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
DATABASE_NAME = os.getenv("MONGODB_DATABASE", "punjab_laws")
COLLECTION_NAME = os.getenv("MONGODB_COLLECTION", "laws")


# ---------------------------------------------------------
# MongoDB Connection
# ---------------------------------------------------------

def get_client():
    """Create and return a MongoDB client."""
    return MongoClient(
        MONGODB_URI,
        serverSelectionTimeoutMS=5000
    )


def get_database():
    """Connect to MongoDB and return the Punjab Laws database."""
    client = get_client()

    # Verify connection
    client.admin.command("ping")

    return client[DATABASE_NAME]


def get_collection():
    """Return the laws collection."""
    db = get_database()
    return db[COLLECTION_NAME]


# ---------------------------------------------------------
# Indexes
# ---------------------------------------------------------

def create_indexes(collection):
    """Create indexes useful for law searching."""

    collection.create_index(
        [("Statute_Name", ASCENDING)],
        unique=False,
        name="statute_name_index"
    )

    collection.create_index(
        [("Category", ASCENDING)],
        name="category_index"
    )

    collection.create_index(
        [("Source", ASCENDING)],
        unique=True,
        name="source_unique_index"
    )

    collection.create_index(
        [
            ("Statute_Name", TEXT),
            ("Statute_HTML", TEXT)
        ],
        name="law_text_search_index"
    )


# ---------------------------------------------------------
# Import JSON Files
# ---------------------------------------------------------

def import_json_files():
    """
    Import all JSON files from data/json into MongoDB.

    Existing documents are updated using Source as the
    unique identifier.
    """

    if not JSON_DIR.exists():
        print(f"ERROR: JSON directory not found: {JSON_DIR}")
        return

    files = sorted(JSON_DIR.glob("*.json"))

    if not files:
        print("ERROR: No JSON files found.")
        return

    client = None

    try:
        client = get_client()

        # Test MongoDB connection
        client.admin.command("ping")

        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]

        print("MongoDB connection successful.")
        print(f"Database:   {DATABASE_NAME}")
        print(f"Collection: {COLLECTION_NAME}")
        print(f"JSON files: {len(files)}")
        print()

        # Create indexes before importing
        create_indexes(collection)

        inserted = 0
        updated = 0
        failed = 0

        for file_path in files:

            try:
                # Read JSON as UTF-8
                with open(
                    file_path,
                    "r",
                    encoding="utf-8"
                ) as file:
                    document = json.load(file)

                if not isinstance(document, dict):
                    print(f"SKIPPED: {file_path.name} - not a JSON object")
                    failed += 1
                    continue

                # Make sure Source exists
                document.setdefault(
                    "Source",
                    file_path.name
                )

                # Keep the original filename
                document["File_Name"] = file_path.name

                source = document["Source"]

                # Upsert based on Source
                result = collection.update_one(
                    {"Source": source},
                    {"$set": document},
                    upsert=True
                )

                if result.upserted_id is not None:
                    inserted += 1
                else:
                    updated += 1

            except json.JSONDecodeError as error:
                print(
                    f"INVALID JSON: {file_path.name} - {error}"
                )
                failed += 1

            except Exception as error:
                print(
                    f"ERROR: {file_path.name} - {error}"
                )
                failed += 1

        print()
        print("=" * 55)
        print("IMPORT COMPLETED")
        print("=" * 55)
        print(f"Files processed : {len(files)}")
        print(f"Inserted        : {inserted}")
        print(f"Updated         : {updated}")
        print(f"Failed          : {failed}")
        print(
            f"MongoDB documents: {collection.count_documents({})}"
        )
        print("=" * 55)

    except PyMongoError as error:
        print("MongoDB ERROR:")
        print(error)

    except Exception as error:
        print("ERROR:")
        print(error)

    finally:
        if client:
            client.close()


# ---------------------------------------------------------
# Database Information
# ---------------------------------------------------------

def show_database_info():
    """Display basic information about the MongoDB collection."""

    client = None

    try:
        client = get_client()
        client.admin.command("ping")

        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]

        print()
        print("=" * 55)
        print("PUNJAB LAWS - MONGODB")
        print("=" * 55)
        print(f"Database:   {DATABASE_NAME}")
        print(f"Collection: {COLLECTION_NAME}")
        print(f"Documents:  {collection.count_documents({})}")
        print("=" * 55)

    except PyMongoError as error:
        print("MongoDB ERROR:")
        print(error)

    finally:
        if client:
            client.close()


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

if __name__ == "__main__":
    print()
    print("=" * 55)
    print("PUNJAB LAWS - MONGODB IMPORTER")
    print("=" * 55)
    print()

    import_json_files()

    show_database_info()