# -*- coding: utf-8 -*-
"""ImportExportService — handle Import and Export commands end-to-end.

See design-specification.md §3.7.

The service owns the import / export algorithms. It does **not** own widgets;
dialog interaction is delegated to caller-provided callables so the service
can be tested headless if needed:

  * ``conflict_dialog(mode_id, remaining)`` →
        ``(action, apply_to_all)`` where ``action`` is one of
        ``CONFLICT_OVERWRITE`` / ``CONFLICT_KEEP_BOTH`` / ``CONFLICT_CANCEL``
        from ``dialogs``.
  * ``requires_dialog(requires, install_status)`` →
        ``True`` if the user wants to proceed, ``False`` to cancel.
  * ``on_batch_complete()`` — called once at the end of every import / export
        batch; the plugin wires this to
        ``registry.refresh() + shortcuts.refresh() + uiwidgets.refresh_mode_lists()``.

Realises FR-MS-7a, FR-MS-7b, FR-MS-9, FR-MS-10.
"""

import json
import os
import re
import shutil
from collections import namedtuple

import qgis.utils


ImportSummary = namedtuple("ImportSummary", ["imported", "skipped"])
ExportSummary = namedtuple("ExportSummary", ["written", "errors"])


# Mirror the strings in dialogs.py; importing them here would tighten the
# coupling unnecessarily — the caller passes the action string back to us.
_CONFLICT_OVERWRITE = "overwrite"
_CONFLICT_KEEP_BOTH = "keep_both"
_CONFLICT_CANCEL = "cancel"


class ImportExportService:
    """End-to-end mode-file import and export."""

    def __init__(self, loader, registry, user_dir, state_store,
                 conflict_dialog, requires_dialog, on_batch_complete,
                 logger=None, messenger=None):
        self.loader = loader
        self.registry = registry
        self.user_dir = user_dir
        self.state_store = state_store
        self.conflict_dialog = conflict_dialog
        self.requires_dialog = requires_dialog
        self.on_batch_complete = on_batch_complete
        self.logger = logger
        self.messenger = messenger

    # ------------------------------------------------------------------ helpers

    def log(self, message, level="info"):
        if self.logger:
            self.logger(message, level)

    def message(self, message, level="info"):
        if self.messenger:
            self.messenger(message, level)

    # ------------------------------------------------------------------ import

    def import_files(self, paths) -> ImportSummary:
        """Import the listed ``paths`` per §3.7 algorithm."""
        return self._import_batch(list(paths))

    def import_directory(self, path) -> ImportSummary:
        """Import every ``*.json`` inside ``path`` (non-recursive)."""
        try:
            entries = sorted(os.listdir(path))
        except OSError as e:
            self.message(f"Could not list {path!r}: {e}", "warning")
            return ImportSummary([], [])
        paths = [
            os.path.join(path, name)
            for name in entries
            if name.lower().endswith(".json")
        ]
        return self._import_batch(paths)

    def _import_batch(self, paths) -> ImportSummary:
        imported = []
        skipped = []

        # Apply-to-all sticky choice within a batch — set once the user ticks
        # the conflict dialog's "Apply to all remaining" box.
        pinned_action = None

        # Pre-load every file so we know how many conflicts the batch will
        # surface — drives the "N remaining" counter in the conflict dialog.
        loaded = []  # (path, config) for files that survived load + requires
        for src in paths:
            config, errors = self.loader.load(src)
            if config is None:
                summary = "; ".join(f"{e.kind}: {e.message}" for e in errors)
                skipped.append((src, f"failed to load: {summary}"))
                continue

            requires = config.get("meta", {}).get("requires") or []
            if requires:
                status = self._check_install_status(requires)
                proceed = self.requires_dialog(requires, status)
                if not proceed:
                    skipped.append((src, "user declined requires preview"))
                    continue

            loaded.append((src, config))

        # Count remaining conflicts as we go, so the dialog's "N remaining"
        # decreases naturally.
        existing_ids = {mid for mid, _, _ in self.registry.available_modes()}
        conflicts_remaining = sum(
            1 for _, cfg in loaded
            if cfg.get("meta", {}).get("id") in existing_ids
        )

        for src, config in loaded:
            mode_id = config["meta"]["id"]
            if mode_id in existing_ids:
                # Need a decision (or use the pinned one)
                if pinned_action is not None:
                    action = pinned_action
                else:
                    action, apply_to_all = self.conflict_dialog(
                        mode_id, conflicts_remaining,
                    )
                    if apply_to_all:
                        pinned_action = action
                conflicts_remaining -= 1

                if action == _CONFLICT_CANCEL:
                    skipped.append((src, "user cancelled conflict"))
                    continue
                if action == _CONFLICT_KEEP_BOTH:
                    new_id = self._unique_id(mode_id, existing_ids)
                    config["meta"]["id"] = new_id
                    dest_path = os.path.join(self.user_dir, f"{new_id}.json")
                    written = self._write_config(config, dest_path)
                    if written:
                        imported.append(new_id)
                        existing_ids.add(new_id)
                    else:
                        skipped.append((src, "write failed"))
                    continue
                # else: overwrite — fall through

            # Either no conflict or overwrite — write at canonical name.
            dest_path = os.path.join(self.user_dir, f"{mode_id}.json")
            written = self._write_config(config, dest_path)
            if written:
                imported.append(mode_id)
                existing_ids.add(mode_id)
            else:
                skipped.append((src, "write failed"))

        # Post-batch: refresh registry, shortcuts, UIWidgets lists.
        try:
            self.on_batch_complete()
        except Exception as e:  # noqa: BLE001
            self.log(f"on_batch_complete callback failed: {e}", "warning")

        self.message(
            f"{len(imported)} imported, {len(skipped)} skipped.",
            "info" if not skipped else "warning",
        )
        return ImportSummary(imported, skipped)

    # ------------------------------------------------------------------ export

    def export_modes(self, ids, dest_dir) -> ExportSummary:
        """Export the listed ``ids`` to ``dest_dir`` (one .json each).

        Preserves the source file's byte content exactly for round-trip
        fidelity (FR-MS-7b). Records ``last_export_dir`` after the first
        successful write.
        """
        written = []
        errors = []
        for mode_id in ids:
            src = self.registry.get_path(mode_id)
            if not src:
                errors.append((mode_id, "mode not found in registry"))
                continue
            dst = os.path.join(dest_dir, f"{mode_id}.json")
            try:
                shutil.copyfile(src, dst)
                written.append(dst)
                if len(written) == 1:
                    self.state_store.set_last_export_dir(dest_dir)
            except OSError as e:
                errors.append((mode_id, f"copy failed: {e}"))

        self.message(
            f"{len(written)} exported, {len(errors)} failed.",
            "info" if not errors else "warning",
        )
        return ExportSummary(written, errors)

    # ------------------------------------------------------------------ internals

    def _write_config(self, config, dest_path) -> bool:
        try:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
                f.write("\n")
            return True
        except OSError as e:
            self.log(f"Failed to write {dest_path!r}: {e}", "warning")
            return False

    def _unique_id(self, base_id, existing_ids):
        """Lowest free ``<base_id>-N``."""
        # Strip a trailing -N if the source id already ended in one — keeps
        # repeated 'Keep both' picks from compounding the suffix.
        stem = re.sub(r"-\d+$", "", base_id)
        n = 1
        while True:
            candidate = f"{stem}-{n}"
            if candidate not in existing_ids:
                return candidate
            n += 1

    def _check_install_status(self, requires):
        """Return ``{plugin_name: bool}`` for the requires list.

        Uses a case-insensitive substring match against the keys in
        ``qgis.utils.plugins`` because mode files in the wild may name
        plugins by display name (e.g. ``QuickMapServices``) while QGIS
        keys them by module directory (``quick_map_services``).
        """
        installed_names = {k.lower(): k for k in qgis.utils.plugins.keys()}
        status = {}
        for plugin in requires:
            needle = plugin.lower().replace("_", "")
            hit = any(
                needle in key.replace("_", "")
                for key in installed_names
            )
            status[plugin] = hit
        return status
