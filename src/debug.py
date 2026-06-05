"""Debug logging for the Sheets2Anki addon (extracted from utils.py).

Holds the DebugManager and the module-level add_debug_message / log helpers."""

from datetime import datetime


class DebugManager:
    """Centralized debug manager for Sheets2Anki."""

    def __init__(self):
        self.messages: list[str] = []
        self.is_debug_enabled = False
        self._update_debug_status()

    def _update_debug_status(self):
        """Updates debug status based on configuration."""
        try:
            from .config_manager import get_meta

            meta = get_meta()
            # Debug is in the config section of meta.json
            self.is_debug_enabled = meta.get("config", {}).get("debug", False)
        except Exception:
            self.is_debug_enabled = False

    def add_message(self, message: str, category: str = "DEBUG") -> None:
        """
        Adds a debug message.

        Args:
            message: Debug message
            category: Message category (SYNC, DECK, ERROR, etc.)
        """
        # Ensure we have the latest debug status
        self._update_debug_status()

        if not self.is_debug_enabled:
            return

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # With milliseconds
        formatted_msg = f"[{timestamp}] [{category}] {message}"
        self.messages.append(formatted_msg)

        # Print to Anki console
        print(formatted_msg)

        # Save to file for easy access
        self._save_to_file(formatted_msg)

    def _save_to_file(self, message: str) -> None:
        """
        Saves debug message to file.

        Args:
            message: Formatted message to save
        """
        try:
            import os

            # Determine log file path
            addon_path = os.path.dirname(os.path.dirname(__file__))
            log_path = os.path.join(addon_path, "debug_sheets2anki.log")

            # Save to file
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(message + "\n")
                f.flush()  # Force immediate write

        except Exception as e:
            # We don't use add_debug_message here to avoid potential infinite recursion
            print(f"[DEBUG_FILE] Error saving log: {e}")

    def get_messages(self) -> list[str]:
        """Returns all debug messages."""
        return self.messages.copy()

    def clear_messages(self) -> None:
        """Clears all debug messages."""
        self.messages.clear()

    def initialize_log_file(self) -> None:
        """
        Initializes the log file with a header.
        """
        self._update_debug_status()
        if not self.is_debug_enabled:
            return

        try:
            import os

            addon_path = os.path.dirname(os.path.dirname(__file__))
            log_path = os.path.join(addon_path, "debug_sheets2anki.log")

            # Create file if it doesn't exist or add session separator
            separator = f"\n{'='*60}\n=== NEW DEBUG SESSION - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n{'='*60}\n"

            # Check if logs should be accumulated
            try:
                from .config_manager import should_accumulate_logs

                accumulate = should_accumulate_logs()
            except ImportError:
                accumulate = True

            mode = "w" if not os.path.exists(log_path) or not accumulate else "a"
            with open(log_path, mode, encoding="utf-8") as f:
                if mode == "w":
                    f.write(
                        f"=== SHEETS2ANKI DEBUG LOG - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n"
                    )
                    if not accumulate and os.path.exists(log_path):
                        add_debug_message(
                            "🧹 Log cleared at session start (accumulation disabled)",
                            "DEBUG",
                        )
                else:
                    f.write(separator)
                f.flush()

            # print(f"[DEBUG_FILE] Log initialized: {log_path}")
            pass

        except Exception as e:
            # We don't use add_debug_message here to avoid potential infinite recursion
            print(f"[DEBUG_FILE] Error initializing log: {e}")

    def get_log_path(self) -> str:
        """
        Returns the log file path.

        Returns:
            str: Full path to the log file
        """
        import os

        addon_path = os.path.dirname(os.path.dirname(__file__))
        return os.path.join(addon_path, "debug_sheets2anki.log")


# Global instance of the debug manager
debug_manager = DebugManager()


def add_debug_message(message: str, category: str = "DEBUG") -> None:
    """
    Convenience function to add debug messages.

    Args:
        message: Debug message
        category: Message category
    """
    debug_manager.add_message(message, category)


def is_debug_enabled() -> bool:
    """Checks if debug is enabled."""
    debug_manager._update_debug_status()
    return debug_manager.is_debug_enabled


def get_debug_messages() -> list[str]:
    """Returns all debug messages."""
    return debug_manager.get_messages()


def clear_debug_messages() -> None:
    """Clears all debug messages."""
    debug_manager.clear_messages()


def initialize_debug_log() -> None:
    """Initializes the debug log file."""
    debug_manager.initialize_log_file()


def get_debug_log_path() -> str:
    """Returns the debug log file path."""
    return debug_manager.get_log_path()


def clear_debug_log():
    """
    Clears the debug log file and starts a new one.
    """
    try:
        from datetime import datetime

        log_path = debug_manager.get_log_path()

        with open(log_path, "w", encoding="utf-8") as f:
            f.write(
                f"=== SHEETS2ANKI DEBUG LOG - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n"
            )

        # add_debug_message(f"Log cleared: {log_path}", "DEBUG")
        pass

    except Exception as e:
        # We don't use add_debug_message here to avoid potential infinite recursion
        print(f"[DEBUG] Error clearing log: {e}")
