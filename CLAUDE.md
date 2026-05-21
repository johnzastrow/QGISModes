# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

## What this is

QGIS Modes is a **QGIS plugin** (Python / PyQt) that provides several
simplified QGIS interfaces — *modes* — that the user can select and switch
between at runtime. Each mode is a JSON file describing which toolbars, tools,
panels, and processing algorithms to show. It hides and regroups existing QGIS
UI elements; it does not add GIS functionality.

The deployable plugin is the folder `src/qgismodes/` (not the repo root).

### Status: skeleton

**This repository is an early skeleton, not a working plugin.** `src/qgismodes/
qgis_modes.py` is a scaffold: `initGui`/`unload` and the diagnostics helpers
work, but every mode-management and lifecycle method raises
`NotImplementedError`. The plugin loads in QGIS and shows its toolbar button;
clicking it currently only shows a "not implemented" message. Implement against
the phased roadmap in `docs/design-multi-mode-and-authoring.md`.

### Relationship to QGIS Light

QGIS Modes is **derived from [QGIS Light](https://github.com/ITC-CRIB/qgis-light)**
by Serkan Girgin (GPL-3.0). QGIS Light is config-driven: one `config.json`
declares one simplified interface. QGIS Modes extends that to **many named,
switchable configs**.

When implementing, the working logic to **port and adapt** lives in QGIS Light's
`qgis_light.py` (class `QGISLightPlugin`) — token resolution (`getItems`,
`addItems`, `findAction`), `enable`/`disable`, and `restoreLayout`. That
mechanism is documented in `docs/customizing-qgis-light.md`. QGIS Modes is also
GPL-3.0-or-later; preserve the attribution in file headers and `LICENSE`.

## Development workflow

There is **no build system, no test suite, and no linter** — it is a plain QGIS
plugin loaded by the QGIS Python runtime.

To run/test changes, the plugin must execute inside QGIS:

- Place (or symlink) `src/qgismodes/` into the active QGIS profile's plugin
  directory so it appears as `.../python/plugins/qgismodes/`. On Windows that is
  typically `%APPDATA%\QGIS\QGIS3\profiles\<profile>\python\plugins\` (QGIS 4
  uses a `QGIS4` folder).
- Enable "QGIS Modes" in Plugins → Manage and Install Plugins.
- After editing code, reload via the **Plugin Reloader** plugin or restart QGIS.
- Runtime diagnostics go to the QGIS Log Messages panel under the **"QGIS Modes"**
  tab (see `QGISModesPlugin.log`); user-facing notices use the message bar.

Releasing a new version means bumping `version=` in `src/qgismodes/metadata.txt`.
The plugin depends on two other QGIS plugins at runtime: **QuickMapServices** and
**DataPlotly** (declared in `metadata.txt` and referenced from mode files).

### Qt5 / Qt6 compatibility

The plugin must support **QGIS 3.22+ and QGIS 4.x from a single codebase** —
QGIS 3 runs Qt 5 / PyQt5, QGIS 4 runs Qt 6 / PyQt6. Code changes must work on
both:

- Always use fully-scoped Qt enum names (`Qt.ToolBarArea.TopToolBarArea`, not
  `Qt.TopToolBarArea`) — PyQt6 requires it and PyQt5 5.15 accepts it.
- Route the two known API differences through the existing `QGISModesPlugin`
  helpers: `associatedObjects()` (Qt6 renamed `QAction.associatedWidgets()`) and
  `toEnum()` (`QgsSettings` returns Qt enums natively under Qt6 but as plain
  integers under Qt5). These were carried over from QGIS Light.

## Architecture

The plugin is **declarative and config-driven**, inheriting QGIS Light's design.
`src/qgismodes/qgis_modes.py` (class `QGISModesPlugin`) is an interpreter; JSON
**mode files** are the specs describing each simplified UI.

**Mode files.** Each mode is one JSON file with a `meta` block (`id`, `name`,
`description`, `icon`, `schema` version) plus `toolbars`, `algorithms`,
`panels`, and `statusbar`. The format is defined by
`src/qgismodes/schema/mode.schema.json`. Modes live in two places:

- `src/qgismodes/modes/` — bundled, read-only templates shipped with the plugin.
- `<QGIS profile>/qgismodes/modes/` — user-authored modes; these survive plugin
  upgrades and shadow bundled modes with the same `id`.

`modes/default.json` is QGIS Light's original `config.json`, imported as a mode.

**`config.json` sections** (per mode) — same meaning as in QGIS Light; see
`docs/customizing-qgis-light.md` for `toolbars`, `algorithms`, `panels`, and
`statusbar`. Note: provider policy is **shared, not per-mode** (removing a data
provider needs a QGIS restart to undo — see design doc A.5), so mode files do
**not** carry a `providers` section.

**Lifecycle.** QGIS calls `classFactory(iface)` in `__init__.py`, which returns
a `QGISModesPlugin`. QGIS then calls `initGui()` and `unload()`.

**Planned mode mechanism** (see `docs/design-multi-mode-and-authoring.md`,
Part A): `enable()` is split so that capturing the user's original layout runs
once, while `apply_mode()` rebuilds the simplified UI and can therefore run
again on every mode switch. `_created_toolbars` tracks the toolbars the plugin
built so a switch tears down exactly those — never QActions borrowed from QGIS.
State is persisted in `QgsSettings` under `qgismodes/` (`qgismodes/enabled`,
`qgismodes/mode`, plus the captured layout).

**Token resolution** is the core mechanism inherited from QGIS Light: mode files
reference existing QGIS UI elements by string tokens, which `get_items()`
resolves to live Qt objects and `add_items()` places into toolbars/menus. See
`docs/customizing-qgis-light.md` for the full token vocabulary.

## Key documents

- `docs/design-multi-mode-and-authoring.md` — the design for multiple modes and
  the visual authoring tool; the phased roadmap; answered design questions.
- `docs/customizing-qgis-light.md` — how the QGIS Light base works (the
  inherited architecture and token mechanism).
- `docs/DesignQuestions.md` — original design questions (answers folded into the
  design doc).
