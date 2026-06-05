#!/usr/bin/env python3
"""
Anki Add-on Package Validator

This script validates whether an .ankiaddon package is correct according to
AnkiWeb specifications and best practices for Anki add-ons.
"""

import json
import sys
import zipfile
from pathlib import Path


def validate_ankiaddon(ankiaddon_path):
    """
    Validates an .ankiaddon file

    Args:
        ankiaddon_path: Path to the .ankiaddon file

    Returns:
        bool: True if valid, False otherwise
    """
    print(f"🔍 VALIDATING: {ankiaddon_path}")
    print("=" * 50)

    if not Path(ankiaddon_path).exists():
        print("❌ ERROR: File not found")
        return False

    try:
        with zipfile.ZipFile(ankiaddon_path, "r") as zipf:
            return validate_zip_contents(zipf)
    except zipfile.BadZipFile:
        print("❌ ERROR: Corrupted ZIP file")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def validate_zip_contents(zipf):
    """Validates ZIP file contents"""

    # Get file list
    files = zipf.namelist()

    print("1. Checking ZIP structure...")

    # Check if there's a root folder (should not have one)
    root_folders = [f for f in files if f.endswith("/") and "/" not in f.rstrip("/")]
    if root_folders:
        print("❌ ERROR: ZIP contains root folders - AnkiWeb does not accept!")
        print(f"   Folders found: {root_folders}")
        return False

    print("   ✅ Structure without root folder: OK")

    # Check mandatory files
    print("\n2. Checking mandatory files...")

    root_files = [f for f in files if "/" not in f and f != ""]

    if "__init__.py" not in root_files:
        print("❌ ERROR: __init__.py not found at root")
        return False
    print("   ✅ __init__.py: OK")

    if "manifest.json" not in root_files:
        print("❌ ERROR: manifest.json not found at root")
        return False
    print("   ✅ manifest.json: OK")

    # Check Python cache
    print("\n3. Checking Python cache...")

    cache_files = [
        f for f in files if "__pycache__" in f or f.endswith((".pyc", ".pyo"))
    ]
    if cache_files:
        print("❌ CRITICAL ERROR: Python cache found - AnkiWeb does not accept!")
        print("   Problematic files:")
        for f in cache_files[:5]:  # Show only the first 5
            print(f"   - {f}")
        if len(cache_files) > 5:
            print(f"   ... and {len(cache_files) - 5} more files")
        return False

    print("   ✅ No Python cache: OK")

    # Validate manifest.json
    print("\n4. Validating manifest.json...")

    try:
        manifest_data = zipf.read("manifest.json")
        manifest = json.loads(manifest_data.decode("utf-8"))
    except Exception as e:
        print(f"❌ ERROR: Could not read manifest.json: {e}")
        return False

    # Check mandatory fields
    required_fields = ["package", "name"]
    for field in required_fields:
        if field not in manifest:
            print(f"❌ ERROR: Mandatory field missing: {field}")
            return False
        if not manifest[field] or not isinstance(manifest[field], str):
            print(f"❌ ERROR: Field '{field}' must be a non-empty string")
            return False
        print(f"   ✅ {field}: {manifest[field]}")

    # Check optional fields
    optional_fields = ["version", "author", "description", "conflicts", "mod"]
    for field in optional_fields:
        if field in manifest:
            if field == "conflicts" and not isinstance(manifest[field], list):
                print(f"❌ ERROR: Field '{field}' must be a list")
                return False
            print(f"   ✅ {field}: {manifest[field]}")

    # Check suspicious files
    print("\n5. Checking suspicious files...")

    suspicious_files = [f for f in files if f.startswith(".") or f.endswith(".tmp")]
    if suspicious_files:
        print("⚠️  Suspicious files found:")
        for f in suspicious_files:
            print(f"   - {f}")
    else:
        print("   ✅ No suspicious files found")

    # Statistics
    print("\n6. Package statistics...")

    total_files = len(files)
    total_size = sum(zipf.getinfo(f).file_size for f in files)

    print(f"   📁 Total files: {total_files}")
    print(f"   📦 Unpacked size: {total_size / 1024:.1f} KB")

    # List files by type
    python_files = [f for f in files if f.endswith(".py")]
    json_files = [f for f in files if f.endswith(".json")]
    other_files = [f for f in files if not f.endswith((".py", ".json"))]

    print(f"   🐍 Python files: {len(python_files)}")
    print(f"   📄 JSON files: {len(json_files)}")
    print(f"   📎 Other files: {len(other_files)}")

    return True


def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python validate_packages.py <file.ankiaddon>")
        sys.exit(1)

    ankiaddon_path = sys.argv[1]

    if validate_ankiaddon(ankiaddon_path):
        print("\n🎉 VALIDATION COMPLETE!")
        print("✅ File is ready for distribution")
        print("🚀 Can be uploaded to AnkiWeb")
    else:
        print("\n❌ VALIDATION FAILED!")
        print("🔧 Fix issues before distributing")
        sys.exit(1)


if __name__ == "__main__":
    main()
