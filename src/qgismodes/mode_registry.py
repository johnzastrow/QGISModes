# -*- coding: utf-8 -*-
"""ModeRegistry — discover installed modes from bundled + user directories.

See design-specification.md §3.1.

Realises FR-MS-1, FR-MS-2, FR-MS-3, FR-MS-4, FR-MS-5.
"""

import glob
import os
import shutil


class ModeRegistry:
    """Discover, cache, and serve metadata for every installed mode.

    User modes (`<profile>/qgismodes/modes/`) shadow bundled modes
    (`<plugin>/modes/`) with the same `meta.id`. On first run with an empty
    user dir, the bundled modes are copied in so they're editable.
    """

    def __init__(self, bundled_dir: str, user_dir: str, loader, logger=None):
        """
        Args:
            bundled_dir: path to the read-only bundled-modes folder.
            user_dir: path to the user-modes folder (may not yet exist).
            loader: a ModeLoader instance.
            logger: optional callable `(message, level)` for diagnostics.
        """
        self.bundled_dir = bundled_dir
        self.user_dir = user_dir
        self.loader = loader
        self.logger = logger
        # id -> (meta, source_path, is_user_mode); insertion-ordered
        self._modes: dict = {}

    def log(self, message: str, level: str = "info") -> None:
        if self.logger:
            self.logger(message, level)

    # ------------------------------------------------------------ public API

    def refresh(self) -> int:
        """Rescan both directories. Returns count of valid modes loaded."""
        self._modes.clear()

        first_run = self._ensure_user_dir()

        bundled_count = self._scan_dir(self.bundled_dir, is_user=False)

        if first_run and bundled_count > 0:
            self._seed_user_dir()

        self._scan_dir(self.user_dir, is_user=True)
        return len(self._modes)

    def available_modes(self) -> list:
        """Return `[(id, meta, is_user_mode), ...]` in load order."""
        return [
            (mid, meta, is_user)
            for mid, (meta, _path, is_user) in self._modes.items()
        ]

    def get_metadata(self, mode_id: str):
        entry = self._modes.get(mode_id)
        return entry[0] if entry else None

    def get_path(self, mode_id: str):
        entry = self._modes.get(mode_id)
        return entry[1] if entry else None

    def is_user_mode(self, mode_id: str) -> bool:
        entry = self._modes.get(mode_id)
        return bool(entry and entry[2])

    # ------------------------------------------------------------ internals

    def _ensure_user_dir(self) -> bool:
        """Create the user modes dir if absent. Returns True if empty (first run)."""
        try:
            if not os.path.isdir(self.user_dir):
                os.makedirs(self.user_dir, exist_ok=True)
                return True
            if not os.listdir(self.user_dir):
                return True
        except OSError as e:
            self.log(f"Cannot access user modes dir {self.user_dir}: {e}", "warning")
        return False

    def _seed_user_dir(self) -> None:
        """Copy bundled modes into the user dir (FR-MS-5)."""
        if not os.path.isdir(self.bundled_dir):
            return
        for src in glob.glob(os.path.join(self.bundled_dir, "*.json")):
            dst = os.path.join(self.user_dir, os.path.basename(src))
            try:
                shutil.copy2(src, dst)
                self.log(f"Seeded user mode: {os.path.basename(src)}")
            except OSError as e:
                self.log(f"Failed to seed {src}: {e}", "warning")

    def _scan_dir(self, directory: str, is_user: bool) -> int:
        """Load all `*.json` in `directory`. Returns count successfully loaded."""
        if not directory or not os.path.isdir(directory):
            return 0
        count = 0
        for path in sorted(glob.glob(os.path.join(directory, "*.json"))):
            config, errors = self.loader.load(path)
            if config is None:
                for err in errors:
                    self.log(
                        f"Skipping {os.path.basename(path)}: {err.kind}: {err.message}",
                        "warning",
                    )
                continue
            mode_id = config.get("meta", {}).get("id")
            if not mode_id:
                self.log(f"Skipping {os.path.basename(path)}: missing meta.id", "warning")
                continue
            if is_user and mode_id in self._modes:
                self.log(f"User mode '{mode_id}' shadows bundled mode of the same id.")
            self._modes[mode_id] = (config["meta"], path, is_user)
            count += 1
        return count
