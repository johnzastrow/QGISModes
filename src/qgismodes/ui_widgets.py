# -*- coding: utf-8 -*-
"""UIWidgets — user-facing widgets and dialogs.

See design-specification.md §3.9 + §7. Implements:

  * ``ToggleSplitButton`` (§7.1) — replaces the bare QAction on the file
    toolbar with a ``QToolButton`` in ``MenuButtonPopup`` mode. The body's
    default action is ``ShortcutManager.toggle_action`` so click + keystroke
    drive the same QAction. The dropdown lists installed modes (checkable,
    active mode marked) plus Import / Export entries.
  * ``ImportExportMenu`` (§7.2) — top-level *"QGIS Modes"* menu inserted into
    the QGIS main menu bar. Auto-hidden while simplified mode is active
    because ``LifecycleController.enable`` hides the whole menu bar.
  * ``ExitControl`` (§7.4) — a QAction whose object name is
    ``mActionDisableQGISModes``, **always** injected after a mode is applied
    (FR-GR-3). Replaces the synthetic-token mechanism inherited from QGIS
    Light.
  * ``InlineModeSwitcher`` (§7.3) — a ``QComboBox`` injected into the active
    mode's primary toolbar **only when ≥ 2 modes are installed** (FR-GR-2).

Phase 3b ships the visible UI. Import / Export menu entries are wired to
stubs that surface a "not yet implemented" message on the QGIS message bar;
Phase 3c repoints them at ``ImportExportService``.

Realises FR-SW-1, FR-SW-4, FR-SW-5, FR-SW-6, FR-GR-1, FR-GR-2, FR-GR-3.
"""

import os

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QAction,
    QActionGroup,
    QComboBox,
    QMenu,
    QToolBar,
    QToolButton,
)


_TOGGLE_BUTTON_NAME = "qgismodes_toggle_button"
_MODE_MENU_NAME = "qgismodes_modes_menu"
_MENUBAR_MENU_NAME = "qgismodes_main_menu"
_EXIT_ACTION_NAME = "mActionDisableQGISModes"
_SWITCHER_NAME = "qgismodes_inline_switcher"


class UIWidgets:
    """Builds and owns the plugin's user-facing widgets."""

    def __init__(self, mainwindow, iface, registry, lifecycle, shortcuts,
                 plugin_dir, logger=None, messenger=None):
        self.mainwindow = mainwindow
        self.iface = iface
        self.registry = registry
        self.lifecycle = lifecycle
        self.shortcuts = shortcuts
        self.plugin_dir = plugin_dir
        self.logger = logger
        self.messenger = messenger

        self._icon = QIcon(
            os.path.join(self.plugin_dir, "icons", "qgismodes.svg")
        )

        # Persistent widgets (live across mode switches)
        self._toggle_button = None      # QToolButton on file toolbar
        self._toggle_menu = None        # QMenu used as the SplitButton dropdown
        self._mode_group = None         # QActionGroup for exclusive mode items
        self._menubar_menu = None       # QMenu added to the main menu bar
        self._menubar_action = None     # QAction returned by addMenu()

        # Transient widgets (re-created on every apply_mode)
        self._exit_action = None        # QAction injected into mode toolbar
        self._switcher_widget = None    # QComboBox injected into mode toolbar

    # ------------------------------------------------------------------ helpers

    def log(self, message: str, level: str = "info") -> None:
        if self.logger:
            self.logger(message, level)

    def message(self, message: str, level: str = "info") -> None:
        if self.messenger:
            self.messenger(message, level)

    # ============================================================ persistent UI

    def install_toggle_button(self) -> None:
        """Add the ToggleSplitButton to the QGIS file toolbar (§7.1).

        Expects ``ShortcutManager.refresh()`` to have run, so
        ``shortcuts.toggle_action`` is already created.
        """
        action = self.shortcuts.toggle_action
        if action is None:
            self.log("install_toggle_button: no toggle action yet", "warning")
            return

        # Decorate the shared action so it carries the icon onto the button.
        # text() stays "QGIS Modes: toggle" for Settings → Keyboard Shortcuts.
        action.setIcon(self._icon)
        action.setIconText("QGIS Modes")
        action.setToolTip("Toggle simplified QGIS interface")

        button = QToolButton(self.mainwindow)
        button.setObjectName(_TOGGLE_BUTTON_NAME)
        button.setDefaultAction(action)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        button.setMenu(self._build_toggle_menu())
        self.iface.fileToolBar().addWidget(button)

        self._toggle_button = button

    def uninstall_toggle_button(self) -> None:
        """Remove the SplitButton from the file toolbar."""
        if self._toggle_button is not None:
            try:
                self._toggle_button.deleteLater()
            except RuntimeError:
                pass
            self._toggle_button = None
        self._toggle_menu = None
        self._mode_group = None

    def install_menubar_menu(self) -> None:
        """Add the QGIS Modes top-level menu to the main menu bar (§7.2)."""
        menu = QMenu("QGIS Modes", self.mainwindow)
        menu.setObjectName(_MENUBAR_MENU_NAME)

        enter = QAction("Enter simplified mode", menu)
        enter.triggered.connect(lambda checked=False: self.lifecycle.enable())
        menu.addAction(enter)
        menu.addSeparator()

        menu.addAction(self._make_action(
            "Import mode…", lambda: self._stub("Import mode")))
        menu.addAction(self._make_action(
            "Import folder…", lambda: self._stub("Import folder")))
        menu.addAction(self._make_action(
            "Export modes…", lambda: self._stub("Export modes")))
        menu.addSeparator()

        manage = QAction("Manage modes…", menu)
        manage.setEnabled(False)  # placeholder for v1.1
        menu.addAction(manage)

        self._menubar_menu = menu
        self._menubar_action = self.mainwindow.menuBar().addMenu(menu)

    def uninstall_menubar_menu(self) -> None:
        """Remove the QGIS Modes menu from the main menu bar."""
        if self._menubar_action is not None:
            try:
                self.mainwindow.menuBar().removeAction(self._menubar_action)
            except RuntimeError:
                pass
            self._menubar_action = None
        if self._menubar_menu is not None:
            try:
                self._menubar_menu.deleteLater()
            except RuntimeError:
                pass
            self._menubar_menu = None

    # ============================================================ mode toolbar

    def inject_into_primary_toolbar(self, toolbar: QToolBar) -> None:
        """Inject the always-on ExitControl + optional InlineModeSwitcher.

        Called by ``LifecycleController.apply_mode`` after the applier has
        (re)built the toolbars. The injected widgets are children of the
        toolbar, so ``applier.teardown_owned_toolbars`` destroys them
        automatically on the next switch / disable — we just have to forget
        the dangling references.
        """
        # Forget anything that may have been carried over from a prior toolbar.
        self._exit_action = None
        self._switcher_widget = None

        # InlineModeSwitcher first (left of the exit), only when ≥ 2 modes.
        modes = self.registry.available_modes()
        if len(modes) >= 2:
            combo = QComboBox(toolbar)
            combo.setObjectName(_SWITCHER_NAME)
            active_id = self.lifecycle.active_mode_id()
            active_index = 0
            for i, (mid, meta, _) in enumerate(modes):
                combo.addItem(meta.get("name", mid), mid)
                if mid == active_id:
                    active_index = i
            combo.setCurrentIndex(active_index)
            combo.currentIndexChanged.connect(self._on_switcher_changed)
            toolbar.addSeparator()
            toolbar.addWidget(combo)
            self._switcher_widget = combo

        # ExitControl — always injected, regardless of mode-file content.
        toolbar.addSeparator()
        exit_action = QAction(toolbar)
        exit_action.setObjectName(_EXIT_ACTION_NAME)
        exit_action.setIcon(self._icon)
        exit_action.setText("Exit simplified mode")
        exit_action.setToolTip("Exit simplified mode (return to standard QGIS)")
        exit_action.triggered.connect(
            lambda checked=False: self.lifecycle.disable()
        )
        toolbar.addAction(exit_action)
        self._exit_action = exit_action

    def clear_injected_refs(self) -> None:
        """Drop refs to widgets that ``applier.teardown_owned_toolbars``
        already destroyed. Called from ``LifecycleController._teardown``."""
        self._exit_action = None
        self._switcher_widget = None

    # ============================================================ refresh

    def refresh_mode_lists(self) -> None:
        """Rebuild mode lists in the SplitButton dropdown after the registry
        changes (post-import / post-export). The InlineModeSwitcher is
        rebuilt on the next ``apply_mode`` injection cycle, so we don't
        touch it here.
        """
        if self._toggle_menu is None:
            return
        new_menu = self._build_toggle_menu()
        if self._toggle_button is not None:
            self._toggle_button.setMenu(new_menu)
        # Replace the old menu (Qt deletes it on next event-loop turn).
        try:
            self._toggle_menu.deleteLater()
        except RuntimeError:
            pass
        self._toggle_menu = new_menu

    # ============================================================ internals

    def _build_toggle_menu(self) -> QMenu:
        menu = QMenu(self.mainwindow)
        menu.setObjectName(_MODE_MENU_NAME)
        menu.aboutToShow.connect(self._sync_mode_check_state)

        group = QActionGroup(menu)
        group.setExclusive(True)

        modes = self.registry.available_modes()
        for mid, meta, _ in modes:
            display = meta.get("name", mid)
            action = QAction(display, menu)
            action.setCheckable(True)
            action.setData(mid)
            action.setActionGroup(group)
            action.triggered.connect(
                lambda checked=False, _mid=mid: self.lifecycle.switch_mode(_mid)
            )
            menu.addAction(action)

        if modes:
            menu.addSeparator()
        menu.addAction(self._make_action(
            "Import mode…", lambda: self._stub("Import mode")))
        menu.addAction(self._make_action(
            "Import folder…", lambda: self._stub("Import folder")))
        menu.addAction(self._make_action(
            "Export modes…", lambda: self._stub("Export modes")))

        self._toggle_menu = menu
        self._mode_group = group
        return menu

    def _sync_mode_check_state(self) -> None:
        """Tick the active mode's row when the dropdown is about to open."""
        if self._mode_group is None:
            return
        active_id = self.lifecycle.active_mode_id()
        for action in self._mode_group.actions():
            action.setChecked(action.data() == active_id)

    def _on_switcher_changed(self, index: int) -> None:
        combo = self._switcher_widget
        if combo is None or index < 0:
            return
        mode_id = combo.itemData(index)
        if mode_id and mode_id != self.lifecycle.active_mode_id():
            self.lifecycle.switch_mode(mode_id)

    def _make_action(self, text: str, slot) -> QAction:
        action = QAction(text, self.mainwindow)
        action.triggered.connect(lambda checked=False: slot())
        return action

    def _stub(self, label: str) -> None:
        """Phase 3b placeholder; Phase 3c replaces with real handlers."""
        self.message(f"{label} — not yet implemented (Phase 3c).", "info")
