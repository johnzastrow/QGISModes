# -*- coding: utf-8 -*-
"""ModeLoader — parse and validate a single mode file.

See design-specification.md §3.2.

Realises FR-MF-1, FR-MF-2, FR-MF-4, FR-MF-5, FR-MF-6, FR-MS-8.
"""

import json
import os


#: Highest mode-file schema version this plugin understands.
SUPPORTED_SCHEMA = 1


class ModeLoadError:
    """One diagnostic from a load() or validate() call.

    `kind` is one of the class constants below; `message` is human-readable;
    `path` is filled in by load() for caller convenience.
    """

    PARSE = "parse"        # JSON decode failure
    SCHEMA = "schema"      # schema-validation failure
    VERSION = "version"    # meta.schema > SUPPORTED_SCHEMA
    OTHER = "other"        # I/O or unexpected

    def __init__(self, kind: str, message: str, path: str = None):
        self.kind = kind
        self.message = message
        self.path = path

    def __repr__(self) -> str:
        return f"<ModeLoadError {self.kind}: {self.message} ({self.path})>"


class ModeLoader:
    """Parse a single mode file and validate it against the JSON Schema."""

    def __init__(self, schema_path: str = None):
        self.schema_path = schema_path
        self._schema = None
        self._validator = None
        self._load_schema()

    def _load_schema(self) -> None:
        """Load the schema and prepare a validator (if `jsonschema` is present).

        Falls back gracefully — the hand-rolled validator in `_fallback_validate`
        covers must-have checks if the library is absent.
        """
        if not self.schema_path or not os.path.isfile(self.schema_path):
            return
        try:
            with open(self.schema_path, "r", encoding="utf-8") as f:
                self._schema = json.load(f)
        except (OSError, json.JSONDecodeError):
            self._schema = None
            return
        try:
            import jsonschema
            self._validator = jsonschema.Draft7Validator(self._schema)
        except ImportError:
            self._validator = None
        except Exception:
            self._validator = None

    # ------------------------------------------------------------ public API

    def load(self, path: str):
        """Read, parse, and validate one mode file.

        Returns (config_dict or None, list[ModeLoadError]). On parse / schema /
        version failure, config is None. On success, errors is empty.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            return None, [ModeLoadError(ModeLoadError.PARSE, str(e), path)]
        except OSError as e:
            return None, [ModeLoadError(ModeLoadError.OTHER, str(e), path)]

        errors = self.validate(config)
        for err in errors:
            err.path = path

        if any(e.kind in (ModeLoadError.SCHEMA, ModeLoadError.VERSION) for e in errors):
            return None, errors
        return config, errors

    def validate(self, config) -> list:
        """Validate a config dict; return a list of ModeLoadError (possibly empty)."""
        errors = []
        if not isinstance(config, dict):
            return [ModeLoadError(ModeLoadError.SCHEMA, "top level is not an object")]

        if self._validator is not None:
            for v_err in self._validator.iter_errors(config):
                errors.append(ModeLoadError(ModeLoadError.SCHEMA, v_err.message))
        else:
            errors.extend(self._fallback_validate(config))

        meta = config.get("meta", {}) if isinstance(config.get("meta"), dict) else {}
        schema_v = meta.get("schema")
        if not isinstance(schema_v, int):
            errors.append(ModeLoadError(ModeLoadError.SCHEMA, "meta.schema must be an integer"))
        elif schema_v > SUPPORTED_SCHEMA:
            errors.append(ModeLoadError(
                ModeLoadError.VERSION,
                f"mode uses schema v{schema_v}; this plugin supports v{SUPPORTED_SCHEMA}",
            ))

        return errors

    # ------------------------------------------------------------ fallback

    def _fallback_validate(self, config: dict) -> list:
        """Minimal hand-rolled validation used when `jsonschema` is unavailable.

        Covers FR-MF-2 (meta block + required fields) and FR-MF-4 (top-level
        section shapes). Does NOT replicate the full schema.
        """
        errors = []
        meta = config.get("meta")
        if not isinstance(meta, dict):
            return [ModeLoadError(ModeLoadError.SCHEMA, "meta block missing or not an object")]
        for required in ("id", "name", "schema"):
            if required not in meta:
                errors.append(ModeLoadError(
                    ModeLoadError.SCHEMA, f"meta.{required} is required",
                ))
        for section in ("toolbars", "algorithms", "panels", "statusbar"):
            if section in config and not isinstance(config[section], dict):
                errors.append(ModeLoadError(
                    ModeLoadError.SCHEMA, f"{section} must be an object",
                ))
        return errors
