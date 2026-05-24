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
STATUS: Phase 2 done — lifecycle (enter / exit / switch) is live.

Implementation phases (per docs/design-specification.md §3):
  Phase 1 (done) — StateStore, ModeLoader, ModeRegistry, TokenResolver.
  Phase 2 (done) — ModeApplier + LifecycleController. Toggle button now
                   actually enters / exits simplified mode; the synthetic
                   mActionDisableQGISModes token is wired to disable().
  Phase 3        — UIWidgets, ShortcutManager, ImportExportService (MVP).
  Post-MVP       — Designer (FR-DS-*), capture (FR-CP-*), menus (FR-UI-9),
                   quick-run (FR-UI-10), provider trimming (FR-PP-*).

Public API on the plugin instance:

    qm = qgis.utils.plugins['qgismodes']
    qm.state_store, qm.loader, qm.registry, qm.token_resolver,
    qm.applier, qm.lifecycle                                # components
    qm.enable(id) / qm.disable() / qm.apply_mode(id) /
    qm.switch_mode(id) / qm.available_modes() / qm.load_mode(id)
                                                            # convenience wrappers

See docs/design-specification.md for the full design (baseline tag spec-v1.0).
==============================================================================
"""

import os.path

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsSettings,
)
from qgis.gui import QgisInterface
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QWidget

from .state_store import StateStore
from .mode_loader import ModeLoader
from .mode_registry import ModeRegistry
from .token_resolver import TokenResolver
from .mode_applier import ModeApplier
from .lifecycle_controller import LifecycleController


class QGISModesPlugin:
    """QGIS Modes plugin — manages multiple switchable simplified interfaces.

    The plugin class is the orchestrator / entry point. The real work is done
    by the component objects assembled in ``__init__`` (see
    ``docs/design-specification.md`` §3).
    """

    SETTINGS_PREFIX = "qgismodes"
    LOG_TAB = "QGIS Modes"

    _message_levels = {
        "info": Qgis.MessageLevel.Info,
        "warning": Qgis.MessageLevel.Warning,
        "error": Qgis.MessageLevel.Critical,
    }

    # ------------------------------------------------------------------ setup

    def __init__(self, iface: QgisInterface):
        self.iface = iface
        self.mainwindow = iface.mainWindow()
        self.settings = QgsSettings()

        self.plugin_dir = os.path.dirname(os.path.realpath(__file__))
        self.schema_path = os.path.join(self.plugin_dir, "schema", "mode.schema.json")

        self.log(f"Plugin directory is {self.plugin_dir}.")

        # --- Phase 1 components (design-specification.md §3.1–§3.4, §3.6) ---
        self.state_store = StateStore(self.settings)
        self.loader = ModeLoader(self.schema_path)
        self.registry = ModeRegistry(
            bundled_dir=self.bundled_modes_dir(),
            user_dir=self.user_modes_dir(),
            loader=self.loader,
            logger=self.log,
        )
        self.token_resolver = TokenResolver(
            mainwindow=self.mainwindow,
            plugin_dir=self.plugin_dir,
            logger=self.log,
            disable_callback=None,  # wired below after lifecycle exists
        )

        count = self.registry.refresh()
        self.log(f"Discovered {count} mode(s).")

        # --- Phase 2 components (design-specification.md §3.3, §3.5) ---
        self.applier = ModeApplier(
            mainwindow=self.mainwindow,
            token_resolver=self.token_resolver,
            logger=self.log,
        )
        self.lifecycle = LifecycleController(
            mainwindow=self.mainwindow,
            registry=self.registry,
            loader=self.loader,
            state_store=self.state_store,
            applier=self.applier,
            logger=self.log,
            messenger=self.message,
        )
        # Wire TokenResolver's synthetic exit action to lifecycle.disable.
        self.token_resolver.disable_callback = self.lifecycle.disable

    # ------------------------------------------------------------ diagnostics

    def log(self, message: str, level: str = "info"):
        QgsApplication.messageLog().logMessage(
            message,
            self.LOG_TAB,
            self._message_levels.get(level, Qgis.MessageLevel.Info),
        )

    def message(self, message: str, level: str = "info"):
        self.iface.messageBar().pushMessage(
            self.LOG_TAB,
            message,
            self._message_levels.get(level, Qgis.MessageLevel.Info),
        )

    # ---------------------------------------------------------- Qt5/Qt6 shims
    # Kept on the plugin for back-compat with any code calling
    # plugin.associatedObjects() / plugin.toEnum(). New code should import
    # ._qt_compat directly.

    @staticmethod
    def associatedObjects(action: QAction) -> list:
        if hasattr(action, "associatedObjects"):
            return action.associatedObjects()
        return action.associatedWidgets()

    @staticmethod
    def toEnum(enum_type, value):
        if isinstance(value, enum_type):
            return value
        return enum_type(value)

    # ---------------------------------------------------------- mode locations

    def bundled_modes_dir(self) -> str:
        """Path to the read-only modes shipped with the plugin."""
        return os.path.join(self.plugin_dir, "modes")

    def user_modes_dir(self) -> str:
        """Path to the user's editable modes in the active QGIS profile."""
        return os.path.join(
            QgsApplication.qgisSettingsDirPath(), "qgismodes", "modes"
        )

    # ----------------------------------------------------- convenience wrappers
    # Thin delegations so Python-console users can call plugin.enable() etc.
    # The actual implementations live on the components.

    def available_modes(self) -> list:
        return self.registry.available_modes()

    def load_mode(self, mode_id: str):
        path = self.registry.get_path(mode_id)
        if not path:
            return None, []
        return self.loader.load(path)

    def enable(self, mode_id: str = None) -> None:
        self.lifecycle.enable(mode_id)

    def apply_mode(self, mode_id: str) -> None:
        self.lifecycle.apply_mode(mode_id)

    def switch_mode(self, mode_id: str) -> None:
        self.lifecycle.switch_mode(mode_id)

    def disable(self) -> None:
        self.lifecycle.disable()

    def active_mode_id(self):
        return self.state_store.active_mode_id()

    def get_items(self, token: str) -> list:
        return self.token_resolver.get_items(token)

    def add_items(self, parent: QWidget, items: list) -> None:
        self.token_resolver.add_items(parent, items)

    def migrate_legacy_config(self):
        """Import an existing QGIS Light config.json as a 'default' mode.

        FR-MS-6 is *Could* per decision D3; deferred to v1.1 / on demand.
        """
        raise NotImplementedError("FR-MS-6 is *Could* / post-MVP")

    # -------------------------------------------------------- QGIS plugin API

    def initGui(self):
        """Build the plugin's entry points in the QGIS UI.

        Adds the QGIS Modes toggle button to the file toolbar and View menu.
        If simplified mode was previously enabled, schedules re-entry for
        after QGIS finishes loading other plugins (FR-LC-6).
        """
        self.log("Initializing QGIS Modes.")

        action = QAction(self.mainwindow)
        action.setObjectName("mActionToggleQGISModes")
        action.setIcon(QIcon(os.path.join(self.plugin_dir, "icons/qgismodes.svg")))
        action.setText("QGIS Modes")
        action.triggered.connect(self._on_toggle)
        self.iface.fileToolBar().addAction(action)
        self.iface.viewMenu().addAction(action)

        # FR-LC-6: defer re-entry so tokens referencing other plugins' toolbars
        # resolve correctly after those plugins have loaded.
        if self.state_store.enabled():
            self.log("Persisted as enabled; deferring re-entry to initializationCompleted.")
            try:
                self.mainwindow.initializationCompleted.connect(self._enter_on_init)
            except Exception as e:  # noqa: BLE001
                self.log(f"Could not connect initializationCompleted: {e}", "warning")
                # Fallback — re-enter now and accept the timing risk.
                self._enter_on_init()

    def _on_toggle(self):
        """Toggle button: enter if standard, exit if simplified."""
        if self.lifecycle.is_currently_applied():
            self.lifecycle.disable()
        else:
            self.lifecycle.enable()

    def _enter_on_init(self):
        """Re-enter simplified mode after QGIS startup completes (FR-LC-6)."""
        try:
            self.mainwindow.initializationCompleted.disconnect(self._enter_on_init)
        except (TypeError, RuntimeError):
            pass  # not connected, or already disconnected
        self.lifecycle.enable(self.state_store.active_mode_id())

    def unload(self):
        """Remove the plugin's UI when QGIS unloads it.

        If simplified mode is currently applied, restore the standard UI but
        preserve the enabled-intent flag so the next plugin load resumes the
        same mode (FR-LC-8).
        """
        self.log("Unloading QGIS Modes.")
        try:
            self.lifecycle.teardown_for_unload()
        except Exception as e:  # noqa: BLE001
            self.log(f"Error during lifecycle teardown: {e}", "warning")

        action = self.mainwindow.findChild(QAction, "mActionToggleQGISModes")
        if action:
            for widget in self.associatedObjects(action):
                widget.removeAction(action)
            action.deleteLater()
