"""Sheets2Anki per-deck options-group management (extracted from utils.py)."""

try:
    from .compat import mw
    from .templates_and_definitions import DEFAULT_PARENT_DECK_NAME
except ImportError:
    from compat import mw
    from templates_and_definitions import DEFAULT_PARENT_DECK_NAME

from .debug import add_debug_message


def _is_default_config(config, config_type="default"):
    """
    Checks if the configuration still has Sheets2Anki default values.

    Args:
        config (dict): Deck configuration
        config_type (str): Configuration type ("root" or "default")

    Returns:
        bool: True if it still has addon default values
    """
    try:
        if config_type == "root":
            # Default values for root deck
            expected_values = {
                "new_perDay": 20,
                "rev_perDay": 200,
                "new_delays": [1, 10],
                "lapse_delays": [10],
                "lapse_minInt": 1,
                "lapse_mult": 0.0,
            }
        else:
            # Default values for remote decks
            expected_values = {
                "new_perDay": 20,
                "rev_perDay": 200,
                "new_delays": [1, 10],
                "lapse_delays": [10],
                "lapse_minInt": 1,
                "lapse_mult": 0.0,
            }

        # Check each expected value
        checks = [
            config["new"]["perDay"] == expected_values["new_perDay"],
            config["rev"]["perDay"] == expected_values["rev_perDay"],
            config["new"]["delays"] == expected_values["new_delays"],
            config["lapse"]["delays"] == expected_values["lapse_delays"],
            config["lapse"]["minInt"] == expected_values["lapse_minInt"],
            config["lapse"]["mult"] == expected_values["lapse_mult"],
        ]

        return all(checks)
    except (KeyError, TypeError):
        # If there's an error accessing any field, consider it customized
        return False


def _should_update_config_version(config):
    """
    Checks if the configuration needs to be updated for a new version of the addon.
    This function can be used in the future to apply configuration updates
    without overwriting user customizations.

    Args:
        config (dict): Deck configuration

    Returns:
        bool: True if it needs to update to a new version
    """
    # For future versions, we can add logic here to detect
    # old configurations that need to be updated
    config_version = config.get("sheets2anki_version", "1.0.0")
    addon_version = "1.0.0"  # This would be obtained from manifest.json

    # For now, always returns False to not force updates
    return False


def get_or_create_sheets2anki_options_group(deck_name=None, deck_url=None):
    """
    Gets or creates the options group based on the configured mode and deck-specific configuration.

    Args:
        deck_name (str, optional): Remote deck name for individual mode
        deck_url (str, optional): Deck URL to get specific configuration

    Returns:
        int: Options group ID or None if in manual mode
    """
    from .config_manager import get_deck_configurations_package_name
    from .config_manager import get_deck_options_mode

    if not mw or not mw.col:
        add_debug_message("❌ Anki not available", "DECK_OPTIONS")
        return None

    # Resolve the configured mode up front so it is always bound — the
    # stored-package-name branch below would otherwise skip assigning it.
    mode = get_deck_options_mode()

    # First, check if there's a specific configuration stored for this deck
    if deck_url:
        stored_package_name = get_deck_configurations_package_name(deck_url)
        if stored_package_name:
            options_group_name = stored_package_name
            add_debug_message(
                f"Using deck-specific configuration: '{options_group_name}'",
                "DECK_OPTIONS",
            )
        else:
            # Fallback to global mode if no specific configuration
            mode = get_deck_options_mode()
            if mode == "manual":
                add_debug_message(
                    "Manual mode active - not applying automatic options",
                    "DECK_OPTIONS",
                )
                return None
            elif mode == "individual" and deck_name:
                options_group_name = f"Sheets2Anki - {deck_name}"
                add_debug_message(
                    f"Individual mode: creating/getting group '{options_group_name}'",
                    "DECK_OPTIONS",
                )
            else:  # mode == "shared" or fallback
                options_group_name = "Sheets2Anki - Default Options"
                add_debug_message(
                    f"Shared mode: creating/getting group '{options_group_name}'",
                    "DECK_OPTIONS",
                )
    else:
        # Check configured mode (fallback when no URL)
        mode = get_deck_options_mode()

        if mode == "manual":
            add_debug_message(
                "Manual mode active - not applying automatic options", "DECK_OPTIONS"
            )
            return None
        elif mode == "individual" and deck_name:
            options_group_name = f"Sheets2Anki - {deck_name}"
            add_debug_message(
                f"Individual mode: creating/getting group '{options_group_name}'",
                "DECK_OPTIONS",
            )
        else:  # mode == "shared" or fallback
            options_group_name = "Sheets2Anki - Default Options"
            add_debug_message(
                f"Shared mode: creating/getting group '{options_group_name}'",
                "DECK_OPTIONS",
            )

    try:
        # Search for existing options group
        all_option_groups = mw.col.decks.all_config()

        add_debug_message(
            f"Searching for group '{options_group_name}' among {len(all_option_groups)} existing groups",
            "DECK_OPTIONS",
        )

        for group in all_option_groups:
            if group["name"] == options_group_name:
                add_debug_message(
                    f"✅ Group '{options_group_name}' already exists (ID: {group['id']})",
                    "DECK_OPTIONS",
                )

                # Check if configurations were customized by the user
                try:
                    existing_config = mw.col.decks.get_config(group["id"])
                    if existing_config and not _is_default_config(
                        existing_config, "default"
                    ):
                        add_debug_message(
                            f"🔒 Group '{options_group_name}' has customized settings - preserving",
                            "DECK_OPTIONS",
                        )
                    else:
                        add_debug_message(
                            f"📋 Group '{options_group_name}' still has default settings",
                            "DECK_OPTIONS",
                        )
                except Exception as check_error:
                    add_debug_message(
                        f"⚠️ Error checking existing group settings: {check_error}",
                        "DECK_OPTIONS",
                    )

                return group["id"]

        # If it doesn't exist, create a new group
        add_debug_message(
            f"Group does not exist, creating new one: '{options_group_name}'",
            "DECK_OPTIONS",
        )
        new_group = mw.col.decks.add_config_returning_id(options_group_name)
        add_debug_message(
            f"✅ New group '{options_group_name}' created (ID: {new_group})",
            "DECK_OPTIONS",
        )

        # IMPORTANT: We only apply default settings in NEW groups
        # Existing groups may have been customized by the user
        add_debug_message(
            f"🔧 Applying default settings to new group '{options_group_name}'",
            "DECK_OPTIONS",
        )

        # Configure optimized default options for spreadsheet flashcards
        try:
            config = mw.col.decks.get_config(new_group)
            if not config:
                add_debug_message(
                    f"❌ Could not get config for group {new_group}",
                    "DECK_OPTIONS",
                )
                return None

            # Optimized settings for spreadsheet study
            config["new"]["perDay"] = 20  # 20 new cards per day (good for spreadsheets)
            config["rev"]["perDay"] = 200  # 200 reviews per day
            config["new"]["delays"] = [1, 10]  # Short initial intervals
            config["lapse"]["delays"] = [10]  # Interval for forgotten cards
            config["lapse"]["minInt"] = 1  # Minimum interval after lapse
            config["lapse"]["mult"] = 0.0  # Interval reduction after lapse

            mw.col.decks.update_config(config)
            add_debug_message(
                f"✅ Default settings applied to new group '{options_group_name}'",
                "DECK_OPTIONS",
            )
            add_debug_message(
                f"📊 Applied values: new/day={config['new']['perDay']}, rev/day={config['rev']['perDay']}",
                "DECK_OPTIONS",
            )
        except Exception as config_error:
            add_debug_message(
                f"⚠️ Error configuring group {new_group}: {config_error}",
                "DECK_OPTIONS",
            )
            # We still return the group ID even if configuration failed
            add_debug_message(
                f"Returning group {new_group} even with configuration error",
                "DECK_OPTIONS",
            )

        return new_group

    except Exception as e:
        add_debug_message(
            f"❌ Error creating/getting options group: {e}", "DECK_OPTIONS"
        )
        import traceback

        traceback.print_exc()
        return None


def apply_sheets2anki_options_to_deck(deck_id, deck_name=None):
    """
    Applies the options group based on the configured mode to a specific deck.

    Args:
        deck_id (int): Anki deck ID
        deck_name (str, optional): Remote deck name for individual mode

    Returns:
        bool: True if successfully applied, False otherwise
    """
    from .config_manager import get_deck_options_mode

    if not mw or not mw.col or not deck_id:
        add_debug_message("❌ Anki or invalid deck_id", "DECK_OPTIONS")
        return False

    # Check if manual mode is active
    mode = get_deck_options_mode()
    if mode == "manual":
        add_debug_message(
            f"Manual mode active - not applying options to deck {deck_id}",
            "DECK_OPTIONS",
        )
        return False

    try:
        add_debug_message(
            f"Applying options to deck {deck_id} (name for options: {deck_name})",
            "DECK_OPTIONS",
        )

        # Get or create options group based on mode
        options_group_id = get_or_create_sheets2anki_options_group(deck_name)

        if not options_group_id:
            add_debug_message("❌ Failed to get options group", "DECK_OPTIONS")
            return False

        # Get deck information
        deck = mw.col.decks.get(deck_id)
        if not deck:
            add_debug_message(f"❌ Deck not found: {deck_id}", "DECK_OPTIONS")
            return False

        deck_full_name = deck["name"]

        add_debug_message(
            f"Options group obtained: {options_group_id} for deck '{deck_full_name}'",
            "DECK_OPTIONS",
        )

        # Apply options group to the deck
        deck["conf"] = options_group_id
        mw.col.decks.save(deck)

        add_debug_message(
            f"✅ Group applied to deck '{deck_full_name}' (ID: {deck_id})",
            "DECK_OPTIONS",
        )
        return True

    except Exception as e:
        add_debug_message(
            f"❌ Error applying options to deck {deck_id}: {e}", "DECK_OPTIONS"
        )
        import traceback

        traceback.print_exc()
        return False


def apply_sheets2anki_options_to_all_remote_decks():
    """
    Applies the options group based on the configured mode to all remote decks.

    Returns:
        dict: Operation statistics
    """
    from .config_manager import get_deck_options_mode
    from .config_manager import get_remote_decks

    if not mw or not mw.col:
        add_debug_message("❌ Anki not available", "DECK_OPTIONS")
        return {"success": False, "error": "Anki not available"}

    # Check if manual mode is active
    mode = get_deck_options_mode()
    if mode == "manual":
        add_debug_message(
            "Manual mode active - not applying options automatically", "DECK_OPTIONS"
        )
        return {
            "success": True,
            "total_decks": 0,
            "updated_decks": 0,
            "failed_decks": 0,
            "errors": ["Manual mode active - settings not applied automatically"],
        }

    stats = {
        "success": True,
        "total_decks": 0,
        "updated_decks": 0,
        "failed_decks": 0,
        "errors": [],
    }

    try:
        # Get all remote decks
        remote_decks = get_remote_decks()
        stats["total_decks"] = len(remote_decks)

        add_debug_message(f"Remote decks found: {len(remote_decks)}", "DECK_OPTIONS")

        if not remote_decks:
            add_debug_message("No remote decks found", "DECK_OPTIONS")
            return stats

        mode_desc = {
            "shared": "shared options (Default)",
            "individual": "individual options per deck",
        }

        add_debug_message(
            f"Applying {mode_desc.get(mode, 'options')} to {len(remote_decks)} remote decks...",
            "DECK_OPTIONS",
        )

        # Detailed log of found decks
        for spreadsheet_id, deck_info in remote_decks.items():
            add_debug_message(
                f"Deck ID: {spreadsheet_id}, Info: {deck_info}", "DECK_OPTIONS"
            )

        # Apply options to each remote deck
        for spreadsheet_id, deck_info in remote_decks.items():
            try:
                local_deck_id = deck_info.get("local_deck_id")
                local_deck_name = deck_info.get("local_deck_name", "Unknown")
                remote_deck_name = deck_info.get("remote_deck_name", "Unknown")

                add_debug_message(
                    f"Processing deck: {local_deck_name} (ID: {local_deck_id}, Remote: {remote_deck_name})",
                    "DECK_OPTIONS",
                )

                if not local_deck_id:
                    error_msg = f"Deck '{local_deck_name}' has no local_deck_id"
                    stats["errors"].append(error_msg)
                    stats["failed_decks"] += 1
                    add_debug_message(f"❌ {error_msg}", "DECK_OPTIONS")
                    continue

                # For individual mode, use remote deck name
                deck_name_for_options = (
                    remote_deck_name if mode == "individual" else None
                )

                add_debug_message(
                    f"Name for options: {deck_name_for_options} (mode: {mode})",
                    "DECK_OPTIONS",
                )

                # Apply options to the main deck
                if apply_sheets2anki_options_to_deck(
                    local_deck_id, deck_name_for_options
                ):
                    stats["updated_decks"] += 1
                    add_debug_message(
                        f"✅ Deck {local_deck_name} successfully configured",
                        "DECK_OPTIONS",
                    )

                    # Also apply to subdecks (if they exist)
                    apply_options_to_subdecks(
                        local_deck_name,
                        remote_deck_name if mode == "individual" else None,
                    )
                else:
                    stats["failed_decks"] += 1
                    add_debug_message(
                        f"❌ Failed to configure deck {local_deck_name}", "DECK_OPTIONS"
                    )

            except Exception as e:
                error_msg = f"Error in deck {spreadsheet_id}: {e}"
                stats["errors"].append(error_msg)
                stats["failed_decks"] += 1
                add_debug_message(f"❌ {error_msg}", "DECK_OPTIONS")

        add_debug_message(
            f"Operation completed: {stats['updated_decks']}/{stats['total_decks']} decks updated",
            "DECK_OPTIONS",
        )

        if stats["errors"]:
            add_debug_message(f"{len(stats['errors'])} errors found:", "DECK_OPTIONS")
            for error in stats["errors"]:
                add_debug_message(f"  - {error}", "DECK_OPTIONS")

        return stats

    except Exception as e:
        error_msg = f"General error in applying options: {e}"
        stats["success"] = False
        stats["errors"].append(error_msg)
        add_debug_message(error_msg, "DECK_OPTIONS")
        return stats


def apply_options_to_subdecks(parent_deck_name, remote_deck_name=None):
    """
    Applies mode-based options to all subdecks of a parent deck.

    Args:
        parent_deck_name (str): Parent deck name
        remote_deck_name (str, optional): Remote deck name for individual mode
    """
    from .config_manager import get_deck_options_mode

    if not mw or not mw.col or not parent_deck_name:
        add_debug_message("❌ Invalid parameters for subdecks", "DECK_OPTIONS")
        return

    # Check if manual mode is active
    mode = get_deck_options_mode()
    if mode == "manual":
        add_debug_message(
            "Manual mode active - not applying options to subdecks", "DECK_OPTIONS"
        )
        return

    try:
        add_debug_message(
            f"Searching for subdecks of: {parent_deck_name}", "DECK_OPTIONS"
        )

        # Search for all decks that start with parent deck name
        all_decks = mw.col.decks.all()
        subdeck_count = 0

        for deck in all_decks:
            deck_name = deck["name"]

            # Check if it's a subdeck (contains :: after parent name)
            if deck_name.startswith(parent_deck_name + "::"):
                add_debug_message(f"Subdeck found: {deck_name}", "DECK_OPTIONS")
                deck_name_for_options = (
                    remote_deck_name if mode == "individual" else None
                )

                if apply_sheets2anki_options_to_deck(deck["id"], deck_name_for_options):
                    add_debug_message(
                        f"✅ Options applied to subdeck: {deck_name}", "DECK_OPTIONS"
                    )
                    subdeck_count += 1
                else:
                    add_debug_message(
                        f"❌ Failed to apply options to subdeck: {deck_name}",
                        "DECK_OPTIONS",
                    )

        add_debug_message(f"Total subdecks processed: {subdeck_count}", "DECK_OPTIONS")

    except Exception as e:
        add_debug_message(
            f"❌ Error applying options to subdecks of '{parent_deck_name}': {e}",
            "DECK_OPTIONS",
        )
        import traceback

        traceback.print_exc()


def cleanup_orphaned_deck_option_groups():
    """
    Removes orphaned deck options groups that start with "Sheets2Anki" and are not
    attached to any deck (total of zero attached decks).

    Returns:
        int: Number of removed orphaned options groups
    """
    if not mw or not mw.col:
        add_debug_message("Anki is not available", "DECK_OPTIONS_CLEANUP")
        return 0

    try:
        add_debug_message(
            "Starting orphaned options group cleanup...", "DECK_OPTIONS_CLEANUP"
        )

        # Get all options groups
        all_option_groups = mw.col.decks.all_config()
        sheets2anki_groups = []

        # Filter only groups that start with "Sheets2Anki"
        for group in all_option_groups:
            if group["name"].startswith("Sheets2Anki"):
                sheets2anki_groups.append(group)

        if not sheets2anki_groups:
            add_debug_message("No Sheets2Anki groups found", "DECK_OPTIONS_CLEANUP")
            return 0

        # Get all decks to check which groups are in use
        all_decks = mw.col.decks.all()
        groups_in_use = set()

        for deck in all_decks:
            conf_id = deck.get("conf", None)
            if conf_id:
                groups_in_use.add(conf_id)

        # Identify orphaned groups (not used by any deck)
        orphaned_groups = []
        for group in sheets2anki_groups:
            group_id = group["id"]
            if group_id not in groups_in_use:
                orphaned_groups.append(group)
                add_debug_message(
                    f"Orphaned group found: '{group['name']}' (ID: {group_id})",
                    "DECK_OPTIONS_CLEANUP",
                )

        # Remove orphaned groups
        removed_count = 0
        for group in orphaned_groups:
            try:
                mw.col.decks.remove_config(group["id"])
                add_debug_message(
                    f"Removed: '{group['name']}' (ID: {group['id']})",
                    "DECK_OPTIONS_CLEANUP",
                )
                removed_count += 1
            except Exception as e:
                add_debug_message(
                    f"Error removing group '{group['name']}': {e}",
                    "DECK_OPTIONS_CLEANUP",
                )

        if removed_count > 0:
            add_debug_message(
                f"Cleanup completed: {removed_count} orphaned groups removed",
                "DECK_OPTIONS_CLEANUP",
            )
        else:
            add_debug_message("No orphaned groups found", "DECK_OPTIONS_CLEANUP")

        return removed_count

    except Exception as e:
        add_debug_message(
            f"Error in orphaned group cleanup: {e}", "DECK_OPTIONS_CLEANUP"
        )
        return 0


def apply_automatic_deck_options_system():
    """
    Applies the complete automatic deck options system.
    This function should be called at the end of synchronization and when the user
    clicks the "Apply" button in the deck settings.

    Performs the following actions (when automatic mode is active):
    1. Applies options to root deck "Sheets2Anki"
    2. Applies options to all remote decks and subdecks
    3. Removes orphaned options groups (cleanup)

    Returns:
        dict: Operation statistics
    """
    add_debug_message(
        "🚀 STARTING automatic deck options system...", "DECK_OPTIONS_SYSTEM"
    )

    from .config_manager import get_deck_options_mode

    if not mw or not mw.col:
        add_debug_message("❌ Anki not available", "DECK_OPTIONS_SYSTEM")
        return {"success": False, "error": "Anki not available"}

    try:
        mode = get_deck_options_mode()
        add_debug_message(f"📋 Current mode: '{mode}'", "DECK_OPTIONS_SYSTEM")
    except Exception as e:
        add_debug_message(f"❌ Error getting mode: {e}", "DECK_OPTIONS_SYSTEM")
        return {"success": False, "error": f"Error getting mode: {e}"}

    if mode == "manual":
        add_debug_message(
            "⏹️ Manual mode active - automatic system disabled", "DECK_OPTIONS_SYSTEM"
        )
        return {
            "success": True,
            "mode": "manual",
            "root_deck_updated": False,
            "remote_decks_updated": 0,
            "cleaned_groups": 0,
            "message": "Manual mode active - automatic system disabled",
        }

    add_debug_message(
        f"⚙️ Applying automatic system in mode: {mode}", "DECK_OPTIONS_SYSTEM"
    )

    try:
        stats = {
            "success": True,
            "mode": mode,
            "root_deck_updated": False,
            "remote_decks_updated": 0,
            "cleaned_groups": 0,
            "errors": [],
        }

        add_debug_message("🎯 STEP 1: Configuring root deck...", "DECK_OPTIONS_SYSTEM")
        # 1. Apply options to root deck
        try:
            root_result = ensure_root_deck_has_root_options()
            stats["root_deck_updated"] = root_result
            if root_result:
                add_debug_message(
                    "✅ Root deck successfully configured", "DECK_OPTIONS_SYSTEM"
                )
            else:
                add_debug_message(
                    "⚠️ Root deck was not configured", "DECK_OPTIONS_SYSTEM"
                )
        except Exception as e:
            error_msg = f"Error configuring root deck: {e}"
            stats["errors"].append(error_msg)
            add_debug_message(f"❌ {error_msg}", "DECK_OPTIONS_SYSTEM")
            import traceback

            traceback.print_exc()

        add_debug_message(
            "🎯 STEP 2: Configuring remote decks...", "DECK_OPTIONS_SYSTEM"
        )
        # 2. Apply options to all remote decks
        try:
            remote_result = apply_sheets2anki_options_to_all_remote_decks()
            if remote_result and remote_result.get("success", False):
                stats["remote_decks_updated"] = remote_result.get("updated_decks", 0)
                add_debug_message(
                    f"✅ {remote_result.get('updated_decks', 0)} remote decks configured",
                    "DECK_OPTIONS_SYSTEM",
                )
                if remote_result.get("errors"):
                    stats["errors"].extend(remote_result["errors"])
            else:
                error_detail = (
                    remote_result.get("error", "Unknown error in remote decks")
                    if remote_result
                    else "Empty result"
                )
                stats["errors"].append(error_detail)
                add_debug_message(
                    f"❌ Remote decks failure: {error_detail}", "DECK_OPTIONS_SYSTEM"
                )
        except Exception as e:
            error_msg = f"Error configuring remote decks: {e}"
            stats["errors"].append(error_msg)
            add_debug_message(f"❌ {error_msg}", "DECK_OPTIONS_SYSTEM")
            import traceback

            traceback.print_exc()

        add_debug_message(
            "🎯 STEP 3: Cleaning up orphaned groups...", "DECK_OPTIONS_SYSTEM"
        )
        # 3. Cleanup of orphaned groups (only when automatic system is active)
        try:
            cleaned_count = cleanup_orphaned_deck_option_groups()
            stats["cleaned_groups"] = cleaned_count
            if cleaned_count > 0:
                add_debug_message(
                    f"✅ {cleaned_count} orphaned groups removed", "DECK_OPTIONS_SYSTEM"
                )
            else:
                add_debug_message("ℹ️ No orphaned groups found", "DECK_OPTIONS_SYSTEM")
        except Exception as e:
            error_msg = f"Error cleaning up orphaned groups: {e}"
            stats["errors"].append(error_msg)
            add_debug_message(f"❌ {error_msg}", "DECK_OPTIONS_SYSTEM")
            import traceback

            traceback.print_exc()

        add_debug_message("📊 Generating final summary...", "DECK_OPTIONS_SYSTEM")
        # Generate summary message
        messages = []
        if stats["root_deck_updated"]:
            messages.append("Root deck configured")
        if stats["remote_decks_updated"] > 0:
            messages.append(f"{stats['remote_decks_updated']} remote decks configured")
        if stats["cleaned_groups"] > 0:
            messages.append(f"{stats['cleaned_groups']} orphaned groups removed")

        if messages:
            stats["message"] = f"Automatic system applied: {', '.join(messages)}"
        else:
            stats["message"] = "Automatic system executed without changes"

        if stats["errors"]:
            stats["message"] += f" ({len(stats['errors'])} errors)"
            add_debug_message(
                f"⚠️ Errors found: {stats['errors']}", "DECK_OPTIONS_SYSTEM"
            )

        add_debug_message(f"🎉 COMPLETED: {stats['message']}", "DECK_OPTIONS_SYSTEM")
        return stats

    except Exception as e:
        error_msg = f"General error in automatic system: {e}"
        add_debug_message(f"❌ GENERAL FAILURE: {error_msg}", "DECK_OPTIONS_SYSTEM")
        import traceback

        traceback.print_exc()
        return {
            "success": False,
            "mode": mode if "mode" in locals() else "unknown",
            "root_deck_updated": False,
            "remote_decks_updated": 0,
            "cleaned_groups": 0,
            "error": error_msg,
        }


def ensure_root_deck_has_root_options():
    """
    Ensures that the root deck 'Sheets2Anki' uses the specific options group
    "Sheets2Anki - Root Options".

    Returns:
        bool: True if successfully applied, False otherwise
    """
    from .config_manager import get_deck_options_mode

    if not mw or not mw.col:
        add_debug_message("Anki is not available", "DECK_OPTIONS")
        return False

    # Check if manual mode is active
    mode = get_deck_options_mode()
    if mode == "manual":
        add_debug_message(
            "Manual mode active - not applying options to root deck", "DECK_OPTIONS"
        )
        return False

    try:
        add_debug_message(
            f"Checking root deck: '{DEFAULT_PARENT_DECK_NAME}'", "DECK_OPTIONS"
        )

        # Get or create the root deck
        parent_deck = mw.col.decks.by_name(DEFAULT_PARENT_DECK_NAME)

        if not parent_deck:
            add_debug_message(
                f"Root deck '{DEFAULT_PARENT_DECK_NAME}' does not exist, creating...",
                "DECK_OPTIONS",
            )
            # Create root deck if it doesn't exist
            parent_deck_id = mw.col.decks.id(DEFAULT_PARENT_DECK_NAME)
            if parent_deck_id is not None:
                parent_deck = mw.col.decks.get(parent_deck_id)
                add_debug_message(
                    f"Root deck created with ID: {parent_deck_id}", "DECK_OPTIONS"
                )
            else:
                add_debug_message("❌ Failed to create root deck", "DECK_OPTIONS")
                return False
        else:
            add_debug_message(
                f"Root deck found: ID {parent_deck['id']}", "DECK_OPTIONS"
            )

        if parent_deck:
            # Get current root options group of the deck
            current_conf_id = parent_deck.get("conf", 1)  # 1 is Anki default
            add_debug_message(
                f"Current root deck configuration: {current_conf_id}", "DECK_OPTIONS"
            )

            # Apply specific root deck group
            add_debug_message(
                "Calling get_or_create_root_options_group()...", "DECK_OPTIONS"
            )
            root_options_group_id = get_or_create_root_options_group()
            add_debug_message(
                f"get_or_create_root_options_group() returned: {root_options_group_id}",
                "DECK_OPTIONS",
            )

            if root_options_group_id:
                if current_conf_id != root_options_group_id:
                    parent_deck["conf"] = root_options_group_id
                    mw.col.decks.save(parent_deck)
                    add_debug_message(
                        f"✅ Root options applied to deck '{DEFAULT_PARENT_DECK_NAME}' (ID: {root_options_group_id})",
                        "DECK_OPTIONS",
                    )
                else:
                    add_debug_message(
                        f"✅ Root deck already uses the correct options (ID: {root_options_group_id})",
                        "DECK_OPTIONS",
                    )
                return True
            else:
                add_debug_message(
                    "❌ Failed to get/create root options group", "DECK_OPTIONS"
                )
                return False
        else:
            add_debug_message("❌ Failed to get/create root deck", "DECK_OPTIONS")
            return False

    except Exception as e:
        add_debug_message(
            f"❌ Error applying root options to parent deck: {e}", "DECK_OPTIONS"
        )
        import traceback

        traceback.print_exc()
        return False


def get_or_create_root_options_group():
    """
    Gets or creates the specific options group for the root deck "Sheets2Anki - Root Options".

    Returns:
        int: Options group ID or None if error
    """
    if not mw or not mw.col:
        add_debug_message(
            "Anki not available to create root options group", "DECK_OPTIONS"
        )
        return None

    options_group_name = "Sheets2Anki - Root Options"
    add_debug_message(
        f"Searching/creating options group: '{options_group_name}'", "DECK_OPTIONS"
    )

    try:
        # Search for existing options group
        all_option_groups = mw.col.decks.all_config()
        add_debug_message(
            f"Total options groups found: {len(all_option_groups)}",
            "DECK_OPTIONS",
        )

        for group in all_option_groups:
            if group["name"] == options_group_name:
                add_debug_message(
                    f"✅ Root group '{options_group_name}' already exists (ID: {group['id']})",
                    "DECK_OPTIONS",
                )

                # Check if configurations were customized by the user
                try:
                    existing_config = mw.col.decks.get_config(group["id"])
                    if existing_config and not _is_default_config(
                        existing_config, "root"
                    ):
                        add_debug_message(
                            f"🔒 Root group '{options_group_name}' has customized settings - preserving",
                            "DECK_OPTIONS",
                        )
                    else:
                        add_debug_message(
                            f"📋 Root group '{options_group_name}' still has default settings",
                            "DECK_OPTIONS",
                        )
                except Exception as check_error:
                    add_debug_message(
                        f"⚠️ Error checking existing root group settings: {check_error}",
                        "DECK_OPTIONS",
                    )

                return group["id"]

        add_debug_message(
            f"Group '{options_group_name}' does not exist, creating new one...",
            "DECK_OPTIONS",
        )
        # If it doesn't exist, create new group
        new_group = mw.col.decks.add_config_returning_id(options_group_name)
        add_debug_message(
            f"✅ New root group '{options_group_name}' created (ID: {new_group})",
            "DECK_OPTIONS",
        )

        # IMPORTANT: We only apply default settings in NEW groups
        # Existing groups may have been customized by the user
        add_debug_message(
            f"🔧 Applying default settings to new root group '{options_group_name}'",
            "DECK_OPTIONS",
        )

        # Configure optimized default options for the root deck
        add_debug_message(
            f"📋 Configuring options for root group '{options_group_name}' (ID: {new_group})...",
            "DECK_OPTIONS",
        )

        # Use the correct API to configure the options group
        # In recent Anki versions, we use mw.col.decks.get_config() and mw.col.decks.update_config()
        try:
            # Get current group configuration
            config = mw.col.decks.get_config(new_group)
            if config is None:
                add_debug_message(
                    f"❌ Could not get configuration for group ID {new_group}",
                    "DECK_OPTIONS",
                )
                return new_group  # Returns group even without configuring

            add_debug_message(
                f"📋 Configuration obtained for group ID {new_group}", "DECK_OPTIONS"
            )

            # Specific settings for root deck - more conservative
            config["new"][
                "perDay"
            ] = 30  # 30 new cards per day (conservative for root deck)
            config["rev"]["perDay"] = 150  # 150 reviews per day
            config["new"]["delays"] = [1, 10]  # Short initial intervals
            config["lapse"]["delays"] = [10]  # Interval for forgotten cards
            config["lapse"]["minInt"] = 1  # Minimum interval after lapse
            config["lapse"]["mult"] = 0.0  # Interval reduction after lapse

            # Save configurations
            mw.col.decks.update_config(config)
            add_debug_message(
                f"💾 Configurations saved for group ID {new_group}", "DECK_OPTIONS"
            )
            add_debug_message(
                f"📊 Values applied to root group: new/day={config['new']['perDay']}, rev/day={config['rev']['perDay']}",
                "DECK_OPTIONS",
            )

        except (AttributeError, TypeError) as api_error:
            add_debug_message(
                f"⚠️ API get_config/update_config not available: {api_error}",
                "DECK_OPTIONS",
            )
            # Fallback to older method if available
            try:
                # Alternative method for older versions
                config = mw.col.decks.confForDid(new_group)
                if config is None:
                    add_debug_message(
                        f"❌ confForDid returned None for group ID {new_group}",
                        "DECK_OPTIONS",
                    )
                    return new_group

                add_debug_message(
                    f"📋 Using confForDid as fallback for group ID {new_group}",
                    "DECK_OPTIONS",
                )

                config["new"]["perDay"] = 30
                config["rev"]["perDay"] = 150
                config["new"]["delays"] = [1, 10]
                config["lapse"]["delays"] = [10]
                config["lapse"]["minInt"] = 1
                config["lapse"]["mult"] = 0.0

                mw.col.decks.save(config)
                add_debug_message(
                    f"💾 Configurations saved via fallback for group ID {new_group}",
                    "DECK_OPTIONS",
                )

            except Exception as fallback_error:
                add_debug_message(
                    f"❌ Fallback failed: {fallback_error}", "DECK_OPTIONS"
                )
                # If no method works, at least the group was created
                add_debug_message(
                    "⚠️ Group created but configurations not applied due to API incompatibility",
                    "DECK_OPTIONS",
                )
        add_debug_message(
            f"✅ Default settings applied to root group '{options_group_name}'",
            "DECK_OPTIONS",
        )

        return new_group

    except Exception as e:
        add_debug_message(
            f"❌ Error creating/getting root options group: {str(e)}", "DECK_OPTIONS"
        )
        return None


# =============================================================================
# DEBUG AND LOGGING SYSTEM (consolidated from debug_manager.py)
# =============================================================================
