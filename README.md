# QGIS Modes

![QGIS Modes Logo](docs/logo/qgismodes.svg)

**Switchable, simplified QGIS interfaces — one per task.**

> ⚠️ **Status: early skeleton.** This repository currently contains the design,
> a runnable plugin scaffold, and a starter mode file — **not** a working
> plugin. The lifecycle and mode-management code is stubbed. See the
> [roadmap](#roadmap).

QGIS Modes lets you define several simplified QGIS interfaces — *modes* such as
**Data Creation & Editing**, **Analysis**, **Raster Processing**, or **Output
Creation** — and switch between them at runtime. Each mode is a small JSON file
describing which toolbars, tools, panels, and processing algorithms to show, and
how to arrange them.

It is aimed at the same audience as QGIS Light: non-technical users in secondary
education and citizen science, plus anyone who wants a focused, task-specific
QGIS workspace.


## Relationship to QGIS Light

**QGIS Modes starts from [QGIS Light](https://github.com/ITC-CRIB/qgis-light)
by Serkan Girgin, and uses it as its foundation.**

QGIS Light is a config-driven QGIS plugin: a `config.json` file declares one
simplified interface, and the plugin builds it. QGIS Modes extends that idea —
instead of one config it manages **many named configs** and lets the user pick
and switch between them, with a planned visual tool for authoring them.

The reused material in this repository:

- **Architecture & token mechanism** — inherited from QGIS Light and documented
  in [`docs/customizing-qgis-light.md`](docs/customizing-qgis-light.md).
- **Plugin scaffold** — `src/qgismodes/` is a renamed scaffold; the working
  logic to port lives in QGIS Light's `qgis_light.py`.
- **`modes/default.json`** — QGIS Light's `config.json`, imported as the first
  mode (with a `meta` block added).
- **Qt5/Qt6 compatibility shims** and **icons** — carried over directly.

QGIS Modes is a derivative work and, like QGIS Light, is licensed under
**GPL-3.0-or-later**. See [Attribution & license](#attribution--license).


## The idea: modes

A *mode* is one JSON file under `src/qgismodes/modes/` (bundled) or the user's
QGIS profile (user-authored). It carries a `meta` block — `id`, `name`,
`description`, `icon`, `schema` version — plus the interface definition
(`toolbars`, `algorithms`, `panels`, `statusbar`). The format is described by
[`src/qgismodes/schema/mode.schema.json`](src/qgismodes/schema/mode.schema.json).

Because a mode is a single file, modes are easy to share — email one, drop it on
a shared drive, or commit it to git. A classroom "mode pack" is just a folder of
JSON files.


## Repository layout

```
QGISModes/
├─ README.md                        This file
├─ CLAUDE.md                        Guidance for Claude Code
├─ LICENSE                          GNU GPL-3.0
├─ docs/
│  ├─ design-multi-mode-and-authoring.md   The core design (modes + authoring)
│  ├─ customizing-qgis-light.md            How the QGIS Light base works
│  ├─ DesignQuestions.md                   Open design questions (answered)
│  └─ qgis-processing-algorithms.xlsx      Algorithm analysis (from QGIS Light)
└─ src/
   └─ qgismodes/                    The deployable QGIS plugin
      ├─ __init__.py                classFactory entry point
      ├─ qgis_modes.py              QGISModesPlugin (SKELETON)
      ├─ metadata.txt               QGIS plugin metadata
      ├─ icons/                     Plugin icons (from QGIS Light)
      ├─ modes/
      │  └─ default.json            QGIS Light's config, imported as a mode
      └─ schema/
         └─ mode.schema.json        JSON Schema for mode files
```

The deployable plugin is the folder `src/qgismodes/`, not the repository root.


## Roadmap

The full design is in
[`docs/design-multi-mode-and-authoring.md`](docs/design-multi-mode-and-authoring.md).
Delivery is phased, each phase independently shippable:

| Phase | Scope |
| :-- | :-- |
| **1. Multi-file loading** | `meta` block, bundled + user `modes/` folders, the `qgismodes/mode` setting, migration of a legacy `config.json`. |
| **2. Mode picker + runtime** | Split toggle button, in-canvas mode switcher, the `enable` / `apply_mode` / `disable` refactor, the token resolver ported from QGIS Light. |
| **3. Visual Mode Designer** | Drag-and-drop authoring dialog so non-developers can build modes without editing JSON. |
| **4. Polish** | "Pick from QGIS" capture, live preview, guard rails, undo/redo. |

The current code is pre-Phase-1: a scaffold that loads in QGIS and shows its
button, with every mode/lifecycle method stubbed (`NotImplementedError`).


## Development

There is no build system, no test suite, and no linter — this is a plain QGIS
Python plugin. To run it:

- Place or symlink `src/qgismodes/` into the active QGIS profile's plugin
  directory so it appears as `.../python/plugins/qgismodes/`. On Windows that is
  typically `%APPDATA%\QGIS\QGIS3\profiles\<profile>\python\plugins\` (QGIS 4
  uses a `QGIS4` folder).
- Enable **QGIS Modes** in *Plugins → Manage and Install Plugins*.
- After editing code, reload with the **Plugin Reloader** plugin or restart QGIS.
- Diagnostics go to the *Log Messages* panel under the **"QGIS Modes"** tab.

A single codebase targets **QGIS 3.22+ and QGIS 4.x** (Qt 5 and Qt 6) — see the
compatibility notes in `CLAUDE.md`.


## Documentation

- [`docs/design-multi-mode-and-authoring.md`](docs/design-multi-mode-and-authoring.md)
  — the design for multiple modes and the visual authoring tool.
- [`docs/customizing-qgis-light.md`](docs/customizing-qgis-light.md) — how the
  QGIS Light base works and how its config is customized.
- [`docs/DesignQuestions.md`](docs/DesignQuestions.md) — open questions; answers
  are folded into the design doc.


## Attribution & license

QGIS Modes is **free software** under the **GNU General Public License v3.0 or
later** (see [`LICENSE`](LICENSE)).

- QGIS Modes — Copyright © 2026 John Zastrow.
- Derived from **QGIS Light** — Copyright © 2024 Serkan Girgin —
  https://github.com/ITC-CRIB/qgis-light

QGIS Light initiated the config-driven simplified-interface approach that QGIS
Modes builds on. Its design and the analysis behind it are documented in:

- Girgin, S., Gohil, J., and Mydur, I. (2025). *A streamlined GIS interface for
  Citizen Science activities: QGIS Light.* Int. Arch. Photogramm. Remote Sens.
  Spatial Inf. Sci., XLVIII-4/W13-2025, 127–134.
  https://doi.org/10.5194/isprs-archives-XLVIII-4-W13-2025-127-2025

At runtime the plugin depends on two other QGIS plugins, **QuickMapServices**
and **DataPlotly**.
