# -*- coding: utf-8 -*-
"""ShortcutManager — register per-mode + toggle QActions with QGIS shortcuts.

See design-specification.md §3.8.

The manager owns its own QActions (it does not borrow the toolbar button's
action). They're parented to the QGIS main window so they survive as long as
the window does, and they're registered with ``QgsGui.shortcutsManager()`` so
users can bind keys in *Settings → Keyboard Shortcuts*.

Default shortcut for every action is the empty string — users bind keys
themselves (FR-SW-7).

Public API:

  * ``refresh()``         — sync registered actions with the current registry.
                            Called from ``initGui()`` and after every batch
                            ``ImportExportService`` operation.
  * ``unregister_all()``  — strip everything; called from ``unload()``.
  * ``toggle_action``     — the ``qgismodes_toggle`` QAction (used by
                            UIWidgets as the ToggleSplitButton's default
                            action so both the keystroke and the toolbar
                            button drive the same QAction).
  * ``switch_action(id)`` — the per-mode QAction, or ``None`` if unknown.

Realises FR-SW-7.
"""

from qgis.gui import QgsGui
from qgis.PyQt.QtWidgets import QAction


_TOGGLE_NAME = "qgismodes_toggle"
_TOGGLE_TEXT = "QGIS Modes: toggle"
_SWITCH_PREFIX = "qgismodes_switch_"


class ShortcutManager:
    """Per-mode + toggle QActions registered with QGIS's shortcut manager."""

    def __init__(self, mainwindow, registry, toggle_callback, switch_callback,
                 logger=None):
        self.mainwindow = mainwindow
        self.registry = registry
        self.toggle_callback = toggle_callback
        self.switch_callback = switch_callback
        self.logger = logger

        # Owned actions, by mode id.
        self._switch_actions = {}   # mode_id -> QAction
        self._toggle_action = None  # QAction or None

    # ------------------------------------------------------------------ helpers

    def log(self, message: str, level: str = "info") -> None:
        if self.logger:
            self.logger(message, level)

    def _register(self, action: QAction) -> None:
        try:
            QgsGui.shortcutsManager().registerAction(action, "")
        except Exception as e:  # noqa: BLE001
            self.log(
                f"Could not register shortcut {action.objectName()!r}: {e}",
                "warning",
            )

    def _unregister_and_delete(self, action: QAction) -> None:
        try:
            QgsGui.shortcutsManager().unregisterAction(action)
        except Exception as e:  # noqa: BLE001
            self.log(
                f"Could not unregister shortcut {action.objectName()!r}: {e}",
                "warning",
            )
        action.deleteLater()

    # ------------------------------------------------------------------ public

    def refresh(self) -> None:
        """Synchronise registered actions with ``registry.available_modes()``.

        Diffs current state against the registry:
          * adds actions for newly-present modes
          * updates text on already-known modes (in case ``meta.name`` changed)
          * unregisters + deletes actions for modes that have disappeared
          * ensures the toggle action exists exactly once
        """
        target = {mid: meta for mid, meta, _ in self.registry.available_modes()}

        # Remove gone modes
        for gone_id in list(self._switch_actions.keys() - target.keys()):
            self._unregister_and_delete(self._switch_actions.pop(gone_id))

        # Add or update per-mode actions
        for mode_id, meta in target.items():
            display = meta.get("name", mode_id)
            text = f"QGIS Modes: switch to {display}"
            action = self._switch_actions.get(mode_id)
            if action is not None:
                action.setText(text)
                continue
            action = QAction(self.mainwindow)
            action.setObjectName(f"{_SWITCH_PREFIX}{mode_id}")
            action.setText(text)
            # Default-arg trick to bind mode_id at action-creation time.
            action.triggered.connect(
                lambda checked=False, mid=mode_id: self.switch_callback(mid)
            )
            self._register(action)
            self._switch_actions[mode_id] = action

        # Ensure the toggle action exists
        if self._toggle_action is None:
            action = QAction(self.mainwindow)
            action.setObjectName(_TOGGLE_NAME)
            action.setText(_TOGGLE_TEXT)
            action.triggered.connect(
                lambda checked=False: self.toggle_callback()
            )
            self._register(action)
            self._toggle_action = action

        self.log(
            f"Shortcuts registered: 1 toggle + {len(self._switch_actions)} "
            f"per-mode."
        )

    def unregister_all(self) -> None:
        """Unregister and delete every action this manager owns."""
        for action in self._switch_actions.values():
            self._unregister_and_delete(action)
        self._switch_actions.clear()
        if self._toggle_action is not None:
            self._unregister_and_delete(self._toggle_action)
            self._toggle_action = None

    # ------------------------------------------------------------------ accessors

    @property
    def toggle_action(self):
        """The ``qgismodes_toggle`` QAction (after ``refresh()`` has run)."""
        return self._toggle_action

    def switch_action(self, mode_id: str):
        """The ``qgismodes_switch_<mode_id>`` QAction, or ``None``."""
        return self._switch_actions.get(mode_id)
