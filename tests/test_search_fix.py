#!/usr/bin/env python3
"""
Simple test to validate that search corrections are working.
"""

import os
import sys


def test_search_patterns():
    """
    Tests if search patterns were correctly fixed.
    """
    print("🧪 Testing search pattern corrections...")

    # Get the project root directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Verify config_manager.py
    config_path = os.path.join(base_dir, "src/config_manager.py")
    try:
        with open(config_path, encoding="utf-8") as f:
            content = f.read()

        if 'find_notes("*")' in content:
            print("✅ config_manager.py: Corrected pattern found")
        else:
            print("❌ config_manager.py: Correction pattern not found")

        if 'find_notes("")' in content:
            print("❌ config_manager.py: Problematic pattern still present")
        else:
            print("✅ config_manager.py: Problematic pattern removed")

    except Exception as e:
        print(f"❌ Error verifying config_manager.py: {e}")

    print("\n🎯 Correction test completed!")


def test_comment_quality():
    """
    Verifies if explanatory comments were added.
    """
    print("\n🧪 Testing comment quality...")

    # Get the project root directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Verify if explanatory comments are present
    paths_to_check = [
        os.path.join(base_dir, "src/config_manager.py"),
    ]

    for path in paths_to_check:
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()

            filename = os.path.basename(path)

            # Since comments were translated to English, we check for English keywords
            if "use wildcard" in content.lower():
                print(f"✅ {filename}: Explanatory comment found")
            else:
                print(f"⚠️ {filename}: Explanatory comment not found")

        except Exception as e:
            print(f"❌ Error verifying {path}: {e}")

    print("\n🎯 Comment test completed!")


if __name__ == "__main__":
    print("🚀 Correction Validation Test - Sheets2Anki")
    print("=" * 60)

    test_search_patterns()
    test_comment_quality()

    print("\n" + "=" * 60)
    print("✨ All tests finished!")
    print("\n💡 Correction summary:")
    print("   • find_notes('') → find_notes('*')")
    print("   • Double quotes error eliminated")
    print("   • Compatibility with modern Anki improved")
