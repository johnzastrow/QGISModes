# -*- coding: utf-8 -*-
"""LifecycleController — orchestrate enter / apply_mode / switch_mode / disable.

See design-specification.md §3.5.

The crucial split: ``enable()`` captures the original layout **once** per
session; ``apply_mode()`` rebuilds the simplified UI and can run on every
switch without re-capturing.

Two distinct concepts:
  * **intent** — whether the user wants simplified mode (persisted in
    ``StateStore.enabled()``).
  * **currently applied** — whether the plugin has actually built the
    simplified UI in *this* process (in-memory flag
    ``self._currently_applied``).

These diverge across QGIS restarts: intent persists, applied state doesn't.

Realises FR-LC-1..9, FR-SW-2, FR-SW-3, FR-GR-3, FR-GR-4.
"""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDockWidget, QToolBar

from ._qt_compat import to_enum


_DEFAULT_MODE_ID = "default"


class LifecycleController:
    """Orchestrate enter / exit / switch with capture-once-apply-many semantics."""

    def __init__(self, mainwindow, registry, loader, state_store, applier,
                 logger=None, messenger=None):
        self.mainwindow = mainwindow
        self.registry = registry
        self.loader = loader
        self.state_store = state_store
        self.applier = applier
        self.logger = logger
        self.messenger = messenger

        # In-memory state — distinct from persisted intent (state_store.enabled())
        self._currently_applied: bool = False
        # Saved before being changed; restored on disable.
        self._prev_ctx_menu_policy = None
        # Last mode that successfully applied — used as fallback target.
        self._last_known_good_mode_id = None

    # ------------------------------------------------------------------ helpers

    def log(self, message: str, level: str = "info") -> None:
        if self.logger:
            self.logger(message, level)

    def message(self, msg: str, level: str = "info") -> None:
        if self.messenger:
            self.messenger(msg, level)

    def is_currently_applied(self) -> bool:
        """True iff the simplified UI is built right now in this process."""
        return self._currently_applied

    def active_mode_id(self):
        return self.state_store.active_mode_id()

    # ------------------------------------------------------------------ enable

    def enable(self, mode_id: str = None) -> None:
        """Enter simplified mode (or switch, if already applied).

        Three cases handled:
          * Already applied — degrade to a mode switch (no UI thrash).
          * Not applied, no prior intent — full enter: capture + hide + apply.
          * Not applied, prior intent (restart resume) — hide + apply, skip
            capture (the captured layout from the previous session is still in
            ``QgsSettings``).
        """
        target_id = (
            mode_id
            or self.active_mode_id()
            or self._default_mode_id()
        )
        if not target_id:
            self.message("No modes installed.", "warning")
            return

        if self._currently_applied:
            if target_id != self.active_mode_id():
                self.apply_mode(target_id)
            return

        intent_was_enabled = self.state_store.enabled()
        if not intent_was_enabled:
            self._capture_original_layout()

        # Hide standard UI
        self._prev_ctx_menu_policy = self.mainwindow.contextMenuPolicy()
        self.mainwindow.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.mainwindow.menuBar().hide()
        for toolbar in self.mainwindow.findChildren(QToolBar):
            if toolbar.parent() == self.mainwindow and not toolbar.isHidden():
                toolbar.hide()

        # Apply the target mode (panel hiding for unlisted docks happens inside)
        self.apply_mode(target_id)

        self._currently_applied = True
        self.state_store.set_enabled(True)
        self.log(f"Simplified mode active (mode={target_id!r}).")

    # ------------------------------------------------------------------ apply_mode

    def apply_mode(self, mode_id: str) -> None:
        """Load ``mode_id`` and (re)build the simplified UI.

        Safe to call whether transitioning Disabled→Enabled (from ``enable()``)
        or Enabled(A)→Enabled(B) (a mode switch). Does **not** re-capture the
        original layout (FR-LC-7).
        """
        path = self.registry.get_path(mode_id)
        if not path:
            self.log(f"Unknown mode_id: {mode_id!r}", "error")
            self.message(f"Mode {mode_id!r} not found.", "warning")
            return self._fallback(exclude=mode_id)

        config, errors = self.loader.load(path)
        if config is None:
            summary = "; ".join(f"{e.kind}: {e.message}" for e in errors)
            self.log(f"Mode {mode_id!r} failed to load: {summary}", "warning")
            self.message(
                f"Mode {mode_id!r} failed: {summary}", "warning",
            )
            return self._fallback(exclude=mode_id)

        # Tear down the previous mode's toolbars, then build the new one.
        self.applier.teardown_owned_toolbars()
        self.applier.apply(config)
        self.state_store.set_active_mode_id(mode_id)
        self._last_known_good_mode_id = mode_id
        self.log(f"Applied mode: {mode_id!r}")

    # ------------------------------------------------------------------ switch_mode

    def switch_mode(self, mode_id: str) -> None:
        """Swap to ``mode_id``. If not yet applied, enters at that mode."""
        if not self._currently_applied:
            self.enable(mode_id)
            return
        self.apply_mode(mode_id)

    # ------------------------------------------------------------------ disable / teardown

    def disable(self) -> None:
        """User-initiated exit: tear down and clear the intent flag."""
        self._teardown(clear_intent=True)

    def teardown_for_unload(self) -> None:
        """Restore standard UI for plugin unload; **preserve** intent flag.

        Called from ``QGISModesPlugin.unload()``. If we're currently in
        simplified mode we restore the captured original UI so the user isn't
        left in an inconsistent state. We do NOT clear the intent flag — next
        time the plugin loads, it should resume simplified mode.
        """
        self._teardown(clear_intent=False)

    def _teardown(self, clear_intent: bool) -> None:
        if not self._currently_applied:
            if clear_intent:
                self.state_store.set_enabled(False)
            return

        self.log("Exiting simplified mode.")
        self.applier.teardown_owned_toolbars()
        self._restore_original_layout()
        self.mainwindow.menuBar().show()
        if self._prev_ctx_menu_policy is not None:
            self.mainwindow.setContextMenuPolicy(self._prev_ctx_menu_policy)
        else:
            self.mainwindow.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        self._prev_ctx_menu_policy = None
        self._currently_applied = False

        if clear_intent:
            self.state_store.set_enabled(False)

    # ------------------------------------------------------------------ fallback

    def _default_mode_id(self):
        """Return the id of the 'default' mode, or the first available, or None."""
        modes = self.registry.available_modes()
        for mid, _, _ in modes:
            if mid == _DEFAULT_MODE_ID:
                return _DEFAULT_MODE_ID
        if modes:
            return modes[0][0]
        return None

    def _fallback(self, exclude=None) -> None:
        """When a mode fails, fall back to last-known-good or default (FR-GR-4)."""
        candidates = [
            self._last_known_good_mode_id,
            _DEFAULT_MODE_ID,
        ]
        for cand in candidates:
            if cand and cand != exclude and self.registry.get_path(cand):
                self.log(f"Falling back to mode: {cand!r}")
                self.apply_mode(cand)
                return
        self.log("No fallback mode available; exiting simplified mode.")
        if self._currently_applied:
            self.disable()

    # ------------------------------------------------------------------ capture / restore

    def _capture_original_layout(self) -> None:
        """Snapshot toolbars + panels into StateStore (FR-LC-2)."""
        toolbars = []
        for tb in self.mainwindow.findChildren(QToolBar):
            if tb.parent() != self.mainwindow:
                continue
            name = tb.objectName()
            if not name:
                continue
            toolbars.append({
                "name": name,
                "area": int(self.mainwindow.toolBarArea(tb)),
                "hidden": tb.isHidden(),
            })

        panels = []
        for d in self.mainwindow.findChildren(QDockWidget):
            name = d.objectName()
            if not name:
                continue
            panels.append({
                "name": name,
                "area": int(self.mainwindow.dockWidgetArea(d)),
                "features": int(d.features()),
                "hidden": d.isHidden(),
                "floating": d.isFloating(),
            })

        self.state_store.save_original_layout(toolbars, panels)
        self.log(
            f"Captured original layout: {len(toolbars)} toolbars, "
            f"{len(panels)} panels."
        )

    def _restore_original_layout(self) -> None:
        """Restore toolbars + panels from snapshot (FR-LC-4)."""
        toolbars, panels = self.state_store.original_layout()

        for item in toolbars:
            tb = self.mainwindow.findChild(QToolBar, item["name"])
            if not tb:
                continue
            try:
                area = to_enum(Qt.ToolBarArea, item["area"])
                if self.mainwindow.toolBarArea(tb) != area:
                    self.mainwindow.addToolBar(area, tb)
            except (TypeError, ValueError):
                pass
            if item.get("hidden"):
                tb.hide()
            else:
                tb.show()

        for item in panels:
            d = self.mainwindow.findChild(QDockWidget, item["name"])
            if not d:
                continue
            try:
                area = to_enum(Qt.DockWidgetArea, item["area"])
                if self.mainwindow.dockWidgetArea(d) != area:
                    self.mainwindow.addDockWidget(area, d)
            except (TypeError, ValueError):
                pass
            try:
                features = to_enum(QDockWidget.DockWidgetFeature, item["features"])
                d.setFeatures(features)
            except (TypeError, ValueError):
                pass
            if item.get("floating"):
                d.setFloating(True)
            if item.get("hidden"):
                d.hide()
            else:
                d.show()

        self.log(
            f"Restored original layout: {len(toolbars)} toolbars, "
            f"{len(panels)} panels."
        )
