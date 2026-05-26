# -*- coding: utf-8 -*-
"""Modal dialogs used by ImportExportService.

See design-specification.md §7.5, §7.6 and the (unmocked) export-selection
dialog. Each class is a thin wrapper over ``QDialog`` exposing a
``prompt(...)`` classmethod that builds, runs, and tears down the dialog,
returning a small native Python value to the caller.

Keeping the dialogs in their own module (rather than nested under
``UIWidgets``) avoids bloating ``ui_widgets.py`` and lets the
``ImportExportService`` import them directly if it ever needs to be tested
without a full UIWidgets instance.
"""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)


# ConflictDialog return values
CONFLICT_OVERWRITE = "overwrite"
CONFLICT_KEEP_BOTH = "keep_both"
CONFLICT_CANCEL = "cancel"


class ConflictDialog(QDialog):
    """Overwrite / Keep both / Cancel + Apply-to-all (§7.5)."""

    def __init__(self, parent, mode_id, remaining_conflicts):
        super().__init__(parent)
        self.setWindowTitle("Mode already exists")
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"A mode with id <b>{mode_id!r}</b> is already installed in "
            f"your user modes folder."
        ))

        self._apply_to_all_box = None
        if remaining_conflicts >= 2:
            self._apply_to_all_box = QCheckBox(
                f"Apply to all remaining conflicts ({remaining_conflicts} left)"
            )
            layout.addWidget(self._apply_to_all_box)

        # OS-appropriate button order via QDialogButtonBox (NFR-USA-3).
        buttons = QDialogButtonBox(self)
        overwrite_btn = QPushButton("Overwrite")
        keep_btn = QPushButton("Keep both")
        cancel_btn = QPushButton("Cancel")
        buttons.addButton(overwrite_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(keep_btn, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.addButton(cancel_btn, QDialogButtonBox.ButtonRole.RejectRole)
        layout.addWidget(buttons)

        self._action = CONFLICT_CANCEL
        overwrite_btn.clicked.connect(lambda: self._finish(CONFLICT_OVERWRITE))
        keep_btn.clicked.connect(lambda: self._finish(CONFLICT_KEEP_BOTH))
        cancel_btn.clicked.connect(lambda: self._finish(CONFLICT_CANCEL))

    def _finish(self, action):
        self._action = action
        self.accept()

    @classmethod
    def prompt(cls, parent, mode_id, remaining_conflicts):
        """Returns ``(action, apply_to_all)``.

        ``action`` is one of ``CONFLICT_OVERWRITE`` / ``CONFLICT_KEEP_BOTH`` /
        ``CONFLICT_CANCEL``. ``apply_to_all`` is ``False`` unless the user
        ticked the checkbox (only shown when ≥ 2 conflicts remain).
        """
        dlg = cls(parent, mode_id, remaining_conflicts)
        result = dlg.exec()
        if result == QDialog.DialogCode.Rejected:
            action = CONFLICT_CANCEL
        else:
            action = dlg._action
        apply_to_all = (
            dlg._apply_to_all_box is not None
            and dlg._apply_to_all_box.isChecked()
        )
        dlg.deleteLater()
        return action, apply_to_all


class RequiresPreviewDialog(QDialog):
    """List ``meta.requires`` with install status; informational (§7.6)."""

    def __init__(self, parent, requires, install_status):
        super().__init__(parent)
        self.setWindowTitle("This mode requires")
        self.setModal(True)

        layout = QVBoxLayout(self)

        listbox = QListWidget(self)
        listbox.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        for plugin in requires:
            installed = install_status.get(plugin, False)
            mark = "✓" if installed else "✗"
            suffix = "installed" if installed else "not installed"
            item = QListWidgetItem(f"  {mark}  {plugin}   ({suffix})")
            listbox.addItem(item)
        layout.addWidget(listbox)

        layout.addWidget(QLabel(
            "Tools referenced by this mode that depend on missing plugins\n"
            "will not appear until those plugins are installed."
        ))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        import_btn = QPushButton("Import")
        buttons.addButton(import_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @classmethod
    def prompt(cls, parent, requires, install_status):
        """Returns ``True`` if the user clicked Import, ``False`` otherwise."""
        dlg = cls(parent, requires, install_status)
        result = dlg.exec()
        dlg.deleteLater()
        return result == QDialog.DialogCode.Accepted


class ExportSelectionDialog(QDialog):
    """Multi-select list of modes to export. Not in the design spec mockups
    — kept minimal."""

    def __init__(self, parent, modes):
        super().__init__(parent)
        self.setWindowTitle("Export modes")
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select modes to export:"))

        self._listbox = QListWidget(self)
        for mode_id, display_name in modes:
            item = QListWidgetItem(f"{display_name}    [{mode_id}]")
            item.setData(Qt.ItemDataRole.UserRole, mode_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self._listbox.addItem(item)
        layout.addWidget(self._listbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _selected_ids(self):
        ids = []
        for i in range(self._listbox.count()):
            item = self._listbox.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                ids.append(item.data(Qt.ItemDataRole.UserRole))
        return ids

    @classmethod
    def prompt(cls, parent, modes):
        """Returns the list of selected mode ids (empty if cancelled)."""
        dlg = cls(parent, modes)
        result = dlg.exec()
        ids = dlg._selected_ids() if result == QDialog.DialogCode.Accepted else []
        dlg.deleteLater()
        return ids
