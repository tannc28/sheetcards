#!/usr/bin/env python3
"""
Standalone Package Creation Script

This script creates an .ankiaddon package for distribution OUTSIDE of AnkiWeb.
For distribution outside of AnkiWeb, the manifest.json must include full information.
"""

import json
import os
import shutil
import zipfile
from pathlib import Path


def create_standalone_package():
    """
    Creates .ankiaddon package for distribution outside AnkiWeb.

    For distribution outside AnkiWeb, the manifest.json must contain:
    - package: folder name where it will be stored
    - name: name shown to the user
    - conflicts (optional): list of conflicting packages
    - mod (optional): update timestamp
    """

    print("📦 CREATING STANDALONE PACKAGE (.ankiaddon)")
    print("=" * 50)
    print("ℹ️  For distribution OUTSIDE AnkiWeb")

    # Directories
    script_dir = Path(__file__).parent
    source_dir = script_dir.parent  # Project root directory
    build_dir = source_dir / "build"
    package_dir = build_dir / "sheetcards-standalone"

    # Clean previous build
    if package_dir.exists():
        shutil.rmtree(package_dir)

    # Create directories
    build_dir.mkdir(exist_ok=True)
    package_dir.mkdir()

    print("1. Copying essential files...")

    # Mandatory files
    essential_files = [
        "__init__.py",
        "manifest.json",
        "config.json",
        "README.md",
        "LICENSE",
    ]

    for file in essential_files:
        source = source_dir / file
        dest = package_dir / file
        if source.exists():
            shutil.copy2(source, dest)
            print(f"   ✓ {file}")
        else:
            print(f"   ❌ {file} not found")

    print("\n2. Copying source code...")

    # src directory
    src_source = source_dir / "src"
    src_dest = package_dir / "src"
    if src_source.exists():
        shutil.copytree(src_source, src_dest, ignore=ignore_patterns)
        print("   ✓ src/")

    print("\n3. Configuring production mode...")

    # Change IS_DEVELOPMENT_MODE constant to False
    templates_path = package_dir / "src" / "templates_and_definitions.py"
    if templates_path.exists():
        with open(templates_path, encoding="utf-8") as f:
            content = f.read()

        # Replace IS_DEVELOPMENT_MODE = True with IS_DEVELOPMENT_MODE = False
        if "IS_DEVELOPMENT_MODE = True" in content:
            content = content.replace(
                "IS_DEVELOPMENT_MODE = True", "IS_DEVELOPMENT_MODE = False"
            )

            with open(templates_path, "w", encoding="utf-8") as f:
                f.write(content)

            print("   ✅ Development mode disabled")
        else:
            print(
                "   ⚠️  IS_DEVELOPMENT_MODE = True not found in templates_and_definitions.py"
            )
    else:
        print(f"   ❌ ERROR: File not found: {templates_path}")

    print("\n4. Validating manifest.json for standalone distribution...")

    # Read and validate manifest
    manifest_path = package_dir / "manifest.json"
    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        print(f"   ❌ Error reading manifest.json: {e}")
        return False

    # Check mandatory fields for external distribution
    required_fields = ["package", "name"]
    for field in required_fields:
        if field not in manifest or not manifest[field]:
            print(f"   ❌ Mandatory field missing: {field}")
            return False
        print(f"   ✓ {field}: {manifest[field]}")

    # Add timestamp if missing
    if "mod" not in manifest:
        import time

        manifest["mod"] = int(time.time())
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=4, ensure_ascii=False)
        print(f"   ✓ 'mod' field added: {manifest['mod']}")

    # Check other useful fields
    if "conflicts" not in manifest:
        manifest["conflicts"] = []
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=4, ensure_ascii=False)
        print("   ✓ 'conflicts' field added (empty list)")

    print("\n5. Cleaning unnecessary files...")

    # Remove cache files
    for root, dirs, files in os.walk(package_dir):
        # Remove __pycache__
        dirs_to_remove = [d for d in dirs if d == "__pycache__"]
        for d in dirs_to_remove:
            shutil.rmtree(os.path.join(root, d))
            print(
                f"   🗑️  Removed: {os.path.relpath(os.path.join(root, d), package_dir)}"
            )
            dirs.remove(d)

        # Remove .pyc, .pyo files
        for file in files[:]:
            if file.endswith((".pyc", ".pyo", ".DS_Store")) or file.startswith("."):
                file_path = os.path.join(root, file)
                os.remove(file_path)
                print(f"   🗑️  Removed: {os.path.relpath(file_path, package_dir)}")

    print("\n6. Creating standalone .ankiaddon file...")

    # Create .ankiaddon file
    ankiaddon_path = build_dir / "sheetcards-standalone.ankiaddon"

    with zipfile.ZipFile(ankiaddon_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Relative path without the root folder
                arc_path = os.path.relpath(file_path, package_dir)
                zipf.write(file_path, arc_path)
                print(f"   📝 Added: {arc_path}")

    # Statistics
    file_count = sum(len(files) for _, _, files in os.walk(package_dir))
    ankiaddon_size = ankiaddon_path.stat().st_size / 1024  # KB

    print("\n📊 STANDALONE PACKAGE STATISTICS:")
    print(f"   📁 Files included: {file_count}")
    print(f"   📦 .ankiaddon size: {ankiaddon_size:.1f} KB")
    print(f"   📋 Package ID: {manifest['package']}")
    print(f"   🏷️  Name: {manifest['name']}")
    print(f"   🕒 Timestamp: {manifest.get('mod', 'N/A')}")

    print("\n✅ STANDALONE PACKAGE CREATED SUCCESSFULLY!")
    print(f"📍 File: {ankiaddon_path}")
    print("\n📤 DISTRIBUTION OUTSIDE ANKIWEB:")
    print("   - This file can be distributed independently")
    print("   - Users can install via 'Install from file...'")
    print("   - manifest.json contains all necessary information")
    print("   - Compatible with manual installation in Anki")

    return True


def ignore_patterns(dir, files):
    """File patterns to ignore"""
    ignore = []
    for file in files:
        if file.startswith("."):
            ignore.append(file)
        elif file.endswith((".pyc", ".pyo")):
            ignore.append(file)
        elif file == "__pycache__":
            ignore.append(file)
    return ignore


if __name__ == "__main__":
    create_standalone_package()
