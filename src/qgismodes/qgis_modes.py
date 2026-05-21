# -*- coding: utf-8 -*-
"""QGIS Modes — switchable simplified QGIS interfaces.

Copyright (C) 2026  John Zastrow

Derived from QGIS Light (https://github.com/ITC-CRIB/qgis-light),
Copyright (C) 2024  Serkan Girgin.

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version. See the LICENSE file for details.

==============================================================================
STATUS: SKELETON — not yet a working plugin.

This file is a scaffold. The mode-management and lifecycle methods raise
NotImplementedError; they are placeholders for the design in
``docs/design-multi-mode-and-authoring.md``. The plugin loads in QGIS and shows
its toolbar button, but mode switching is not wired up yet.

Implementation order (see the "Phased roadmap" in the design doc):
  Phase 1 — mode discovery + loading (available_modes, load_mode, migration)
  Phase 2 — lifecycle refactor (enable / apply_mode / disable), mode picker,
            and the token resolver ported from QGIS Light
  Phase 3 — the visual Mode Designer
  Phase 4 — "Pick from QGIS" capture, live preview, guard rails

Starting point: the working logic to port lives in QGIS Light's
``qgis_light.py`` (QGISLightPlugin) — see ``docs/customizing-qgis-light.md``.
==============================================================================
"""

import os.path

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsSettings,
)
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QWidget


class QGISModesPlugin:
    """QGIS Modes plugin — manages multiple switchable simplified interfaces.

    QGIS Modes builds on QGIS Light. QGIS Light loads exactly one ``config.json``
    describing one simplified interface; QGIS Modes loads one of several named
    "mode" files (Data Editing, Analysis, Raster Processing, Output Creation,
    ...) and lets the user switch between them at runtime.

    See ``docs/design-multi-mode-and-authoring.md`` for the full design and
    ``docs/customizing-qgis-light.md`` for the inherited QGIS Light architecture.
    """

    #: Prefix for every key this plugin writes to QgsSettings.
    SETTINGS_PREFIX = "qgismodes"

    #: Label of the Log Messages panel tab used by this plugin.
    LOG_TAB = "QGIS Modes"

    # Message levels (config string -> Qgis.MessageLevel).
    _message_levels = {
        "info": Qgis.MessageLevel.Info,
        "warning": Qgis.MessageLevel.Warning,
        "error": Qgis.MessageLevel.Critical,
    }

    # Toolbar areas (config string -> Qt enum).
    _toolbar_areas = {
        "top": Qt.ToolBarArea.TopToolBarArea,
        "bottom": Qt.ToolBarArea.BottomToolBarArea,
        "left": Qt.ToolBarArea.LeftToolBarArea,
        "right": Qt.ToolBarArea.RightToolBarArea,
    }

    # Panel areas (config string -> Qt enum).
    _panel_areas = {
        "top": Qt.DockWidgetArea.TopDockWidgetArea,
        "bottom": Qt.DockWidgetArea.BottomDockWidgetArea,
        "left": Qt.DockWidgetArea.LeftDockWidgetArea,
        "right": Qt.DockWidgetArea.RightDockWidgetArea,
    }

    # ----------------------------------------------------------------- setup

    def __init__(self, iface: QgisInterface):
        """Store handles and locate the mode directories.

        Args:
            iface: QGIS interface object.
        """
        self.iface = iface
        self.mainwindow = iface.mainWindow()
        self.settings = QgsSettings()

        self.plugin_dir = os.path.dirname(os.path.realpath(__file__))

        # Toolbars created by this plugin, tracked so a mode switch can tear
        # down exactly what it built — and nothing it borrowed from QGIS.
        # See design doc, "Open questions / risks".
        self._created_toolbars = []

        # Active mode config dict, populated by load_mode().
        self.config = None

        self.log(f"Plugin directory is {self.plugin_dir}.")

    # ------------------------------------------------------------ diagnostics

    def log(self, message: str, level: str = "info"):
        """Log a message to the QGIS Log Messages panel ("QGIS Modes" tab)."""
        QgsApplication.messageLog().logMessage(
            message,
            self.LOG_TAB,
            self._message_levels.get(level, Qgis.MessageLevel.Info),
        )

    def message(self, message: str, level: str = "info"):
        """Show a message in the QGIS message bar."""
        self.iface.messageBar().pushMessage(
            self.LOG_TAB,
            message,
            self._message_levels.get(level, Qgis.MessageLevel.Info),
        )

    # ---------------------------------------------------------- Qt5/Qt6 shims
    # Carried over verbatim from QGIS Light: the two known Qt 5 / Qt 6 API
    # differences. A single codebase must support QGIS 3 (Qt5) and QGIS 4 (Qt6).

    @staticmethod
    def associatedObjects(action: QAction) -> list:
        """Return objects associated with an action (Qt5/Qt6 compatible).

        QAction.associatedWidgets() was renamed associatedObjects() in Qt6.
        """
        if hasattr(action, "associatedObjects"):
            return action.associatedObjects()
        return action.associatedWidgets()

    @staticmethod
    def toEnum(enum_type, value):
        """Coerce a value read from QgsSettings to a Qt enum (Qt5/Qt6).

        QgsSettings preserves Qt enum types under Qt6 but returns plain integers
        under Qt5.
        """
        if isinstance(value, enum_type):
            return value
        return enum_type(value)

    # --------------------------------------------------------- mode locations

    def bundled_modes_dir(self) -> str:
        """Return the path to the read-only modes shipped with the plugin."""
        return os.path.join(self.plugin_dir, "modes")

    def user_modes_dir(self) -> str:
        """Return the path to the user's editable modes in the active profile.

        See design doc A.2. User modes shadow bundled modes with the same id and
        survive plugin upgrades.
        """
        return os.path.join(
            QgsApplication.qgisSettingsDirPath(), "qgismodes", "modes"
        )

    def active_mode_id(self):
        """Return the id of the currently selected mode, or None."""
        return self.settings.value(f"{self.SETTINGS_PREFIX}/mode")

    # -------------------------------------------------------- mode management
    # TODO Phase 1 — see design doc, Part A.

    def available_modes(self) -> list:
        """Return metadata for every installed mode (bundled + user).

        TODO Phase 1: scan bundled_modes_dir() and user_modes_dir() for *.json,
        parse each file's ``meta`` block, and let user files shadow bundled ones
        by id. See design doc A.2.
        """
        raise NotImplementedError("available_modes() — design doc A.2 (Phase 1)")

    def load_mode(self, mode_id: str) -> dict:
        """Load and validate a mode config by id.

        TODO Phase 1: resolve mode_id to a file, parse JSON, validate against
        schema/mode.schema.json, and return the config dict. See design doc A.6.
        """
        raise NotImplementedError("load_mode() — design doc A.6 (Phase 1)")

    def migrate_legacy_config(self):
        """Import an existing single config.json as a 'default' mode.

        TODO Phase 1: see design doc A.7.
        """
        raise NotImplementedError("migrate_legacy_config() — design doc A.7")

    # -------------------------------------------------------------- lifecycle
    # TODO Phase 2 — the enable / apply_mode / disable refactor; see design
    # doc A.4. The logic to adapt lives in QGIS Light's QGISLightPlugin.

    def enable(self, mode_id: str = None):
        """Enter simplified mode (first time) and apply a mode.

        TODO Phase 2: on first entry, capture the original layout, hide the
        standard UI, and apply the shared provider policy once; then call
        apply_mode(). See design doc A.4.
        """
        raise NotImplementedError("enable() — design doc A.4 (Phase 2)")

    def apply_mode(self, mode_id: str):
        """Swap the simplified UI to a different mode (safe while enabled).

        TODO Phase 2: tear down self._created_toolbars, load the mode, rebuild
        toolbars, and re-apply panels and the status bar. Must NOT delete
        QActions borrowed from QGIS. See design doc A.4 and "Open questions".
        """
        raise NotImplementedError("apply_mode() — design doc A.4 (Phase 2)")

    def switch_mode(self, mode_id: str):
        """Switch to another mode while staying in simplified mode.

        TODO Phase 2: thin wrapper over apply_mode() for the in-canvas mode
        switcher. See design doc A.3.
        """
        raise NotImplementedError("switch_mode() — design doc A.3 (Phase 2)")

    def disable(self):
        """Return to the standard QGIS interface.

        TODO Phase 2: tear down created toolbars and restore the captured
        original layout. See design doc A.4.
        """
        raise NotImplementedError("disable() — design doc A.4 (Phase 2)")

    def _capture_original_layout(self):
        """Store the current toolbar/panel layout so it can be restored.

        TODO Phase 2: runs once, on first enable(). See design doc A.4.
        """
        raise NotImplementedError("_capture_original_layout() — Phase 2")

    def restore_layout(self):
        """Restore the toolbar/panel layout captured before simplification.

        TODO Phase 2.
        """
        raise NotImplementedError("restore_layout() — Phase 2")

    # ------------------------------------------------------- token resolution
    # The core mechanism inherited from QGIS Light. See
    # docs/customizing-qgis-light.md, "Token resolution — the core mechanism".

    def get_items(self, token: str) -> list:
        """Resolve a config token to live Qt objects.

        TODO Phase 2: port QGIS Light's getItems(). See the customization guide,
        section 2.5.
        """
        raise NotImplementedError("get_items() — port from QGIS Light getItems()")

    def add_items(self, parent: QWidget, items: list):
        """Recursively place resolved objects into a toolbar or menu.

        TODO Phase 2: port QGIS Light's addItems(). See the customization guide,
        section 2.6.
        """
        raise NotImplementedError("add_items() — port from QGIS Light addItems()")

    # -------------------------------------------------------- QGIS plugin API

    def initGui(self):
        """Build the plugin's entry points in the QGIS UI.

        Adds the QGIS Modes toggle button to the file toolbar and the View menu.
        TODO Phase 2: turn the button into a split button whose dropdown lists
        the available modes (design doc A.3).
        """
        self.log("Initializing QGIS Modes (skeleton).")

        action = QAction(self.mainwindow)
        action.setObjectName("mActionToggleQGISModes")
        action.setIcon(QIcon(os.path.join(self.plugin_dir, "icons/qgis-green.svg")))
        action.setText("QGIS Modes")
        action.triggered.connect(self._on_toggle)

        self.iface.fileToolBar().addAction(action)
        self.iface.viewMenu().addAction(action)

    def _on_toggle(self):
        """Placeholder handler for the toggle button.

        TODO Phase 2: replace with the real enable()/disable() logic and the
        mode picker.
        """
        self.message(
            "QGIS Modes is a skeleton — mode switching is not implemented yet. "
            "See docs/design-multi-mode-and-authoring.md.",
            "warning",
        )
        self.log("Toggle clicked; lifecycle not yet implemented.")

    def unload(self):
        """Remove the plugin's UI when QGIS unloads it."""
        self.log("Unloading QGIS Modes.")
        action = self.mainwindow.findChild(QAction, "mActionToggleQGISModes")
        if action:
            for widget in self.associatedObjects(action):
                widget.removeAction(action)
            action.deleteLater()
