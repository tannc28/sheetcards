"""
Qt/Anki Compatibility Module

This module provides clean imports and constants for Anki 25.x+ with Qt6.
All backward compatibility code has been removed.
"""

from typing import Any
from typing import Optional

# =============================================================================
# ANKI IMPORTS
# =============================================================================
from aqt import mw
from aqt.qt import QAbstractItemView
from aqt.qt import QAction
from aqt.qt import QApplication
from aqt.qt import QButtonGroup
from aqt.qt import QCheckBox
from aqt.qt import QComboBox
from aqt.qt import QDialog
from aqt.qt import QDialogButtonBox
from aqt.qt import QFileDialog
from aqt.qt import QFont
from aqt.qt import QFormLayout
from aqt.qt import QFrame
from aqt.qt import QGridLayout
from aqt.qt import QGroupBox
from aqt.qt import QHBoxLayout
from aqt.qt import QInputDialog
from aqt.qt import QKeySequence
from aqt.qt import QLabel
from aqt.qt import QLineEdit
from aqt.qt import QListWidget
from aqt.qt import QListWidgetItem
from aqt.qt import QMenu
from aqt.qt import QMessageBox
from aqt.qt import QPalette
from aqt.qt import QProgressBar
from aqt.qt import QProgressDialog
from aqt.qt import QPushButton
from aqt.qt import QRadioButton
from aqt.qt import QScrollArea
from aqt.qt import QSize
from aqt.qt import QSizePolicy
from aqt.qt import QSpinBox
from aqt.qt import QSplitter
from aqt.qt import Qt
from aqt.qt import QTabWidget
from aqt.qt import QTextBrowser
from aqt.qt import QTextCursor
from aqt.qt import QTextEdit
from aqt.qt import QTimer
from aqt.qt import QVBoxLayout
from aqt.qt import QWidget
from aqt.qt import qconnect
from aqt.utils import showCritical
from aqt.utils import showInfo
from aqt.utils import showWarning
from aqt.utils import tooltip

# Export qconnect for direct use
safe_qconnect = qconnect

# =============================================================================
# QT6 CONSTANTS
# =============================================================================

# Alignment constants
AlignTop = Qt.AlignmentFlag.AlignTop
AlignLeft = Qt.AlignmentFlag.AlignLeft
AlignCenter = Qt.AlignmentFlag.AlignCenter
AlignRight = Qt.AlignmentFlag.AlignRight
AlignBottom = Qt.AlignmentFlag.AlignBottom
AlignVCenter = Qt.AlignmentFlag.AlignVCenter
AlignHCenter = Qt.AlignmentFlag.AlignHCenter

# Key constants
Key_Return = Qt.Key.Key_Return
Key_Enter = Qt.Key.Key_Enter
Key_Escape = Qt.Key.Key_Escape

# Text format constants
TextFormat_RichText = Qt.TextFormat.RichText
TextFormat_PlainText = Qt.TextFormat.PlainText

# Orientation constants
Horizontal = Qt.Orientation.Horizontal
Vertical = Qt.Orientation.Vertical

# Context Menu Policy constants
CustomContextMenu = Qt.ContextMenuPolicy.CustomContextMenu
NoContextMenu = Qt.ContextMenuPolicy.NoContextMenu
DefaultContextMenu = Qt.ContextMenuPolicy.DefaultContextMenu

# Dialog constants
DialogAccepted = QDialog.DialogCode.Accepted
DialogRejected = QDialog.DialogCode.Rejected

# Window modality constants
WINDOW_MODAL = Qt.WindowModality.WindowModal
APPLICATION_MODAL = Qt.WindowModality.ApplicationModal
NON_MODAL = Qt.WindowModality.NonModal

# QDialogButtonBox constants
ButtonBox_Ok = QDialogButtonBox.StandardButton.Ok
ButtonBox_Cancel = QDialogButtonBox.StandardButton.Cancel
ButtonBox_Yes = QDialogButtonBox.StandardButton.Yes
ButtonBox_No = QDialogButtonBox.StandardButton.No
ButtonBox_Apply = QDialogButtonBox.StandardButton.Apply
ButtonBox_Close = QDialogButtonBox.StandardButton.Close

# QMessageBox constants
MessageBox_Yes = QMessageBox.StandardButton.Yes
MessageBox_Ok = QMessageBox.StandardButton.Ok
MessageBox_Cancel = QMessageBox.StandardButton.Cancel
MessageBox_Information = QMessageBox.Icon.Information
MessageBox_Warning = QMessageBox.Icon.Warning
MessageBox_Critical = QMessageBox.Icon.Critical
MessageBox_Question = QMessageBox.Icon.Question

# Echo mode constants for QLineEdit
EchoModeNormal = QLineEdit.EchoMode.Normal
EchoModePassword = QLineEdit.EchoMode.Password

# QPalette constants
Palette_Window = QPalette.ColorRole.Window
Palette_WindowText = QPalette.ColorRole.WindowText
Palette_Base = QPalette.ColorRole.Base
Palette_Text = QPalette.ColorRole.Text

# QAbstractItemView constants
MultiSelection = QAbstractItemView.SelectionMode.MultiSelection
SingleSelection = QAbstractItemView.SelectionMode.SingleSelection
NoSelection = QAbstractItemView.SelectionMode.NoSelection
ExtendedSelection = QAbstractItemView.SelectionMode.ExtendedSelection
ContiguousSelection = QAbstractItemView.SelectionMode.ContiguousSelection

# Alternative names for consistency
MULTI_SELECTION = MultiSelection
SINGLE_SELECTION = SingleSelection
NO_SELECTION = NoSelection
EXTENDED_SELECTION = ExtendedSelection
CONTIGUOUS_SELECTION = ContiguousSelection

# QFrame constants
Frame_HLine = QFrame.Shape.HLine
Frame_VLine = QFrame.Shape.VLine
Frame_NoFrame = QFrame.Shape.NoFrame
Frame_Sunken = QFrame.Shadow.Sunken
Frame_Raised = QFrame.Shadow.Raised
Frame_Plain = QFrame.Shadow.Plain

# QFont constants
Font_Bold = QFont.Weight.Bold
Font_Normal = QFont.Weight.Normal
Font_Light = QFont.Weight.Light

# ScrollBar Policy constants
ScrollBarAlwaysOff = Qt.ScrollBarPolicy.ScrollBarAlwaysOff
ScrollBarAlwaysOn = Qt.ScrollBarPolicy.ScrollBarAlwaysOn
ScrollBarAsNeeded = Qt.ScrollBarPolicy.ScrollBarAsNeeded

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def safe_exec_dialog(dialog) -> int:
    """
    Executes a dialog.

    Args:
        dialog: Qt dialog to execute

    Returns:
        int: Dialog result code (Accepted/Rejected)
    """
    return dialog.exec()


def safe_exec_menu(menu, position) -> Any:
    """
    Executes a context menu.

    Args:
        menu: QMenu to execute
        position: Position where to show the menu

    Returns:
        Selected QAction or None
    """
    return menu.exec(position)


# Alias for consistency
safe_exec = safe_exec_dialog
