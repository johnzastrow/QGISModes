# QGIS Modes — Software Requirements Specification (SRS)

| | |
| :-- | :-- |
| **Document** | Software Requirements Specification |
| **Project** | QGIS Modes |
| **Version** | 0.1 — DRAFT for review |
| **Date** | 2026-05-21 |
| **Status** | Stage 2 of the requirements & design process; awaiting review. |
| **Baseline target** | Release 1.0 (MVP — Phases 1 & 2) |
| **Related** | [`vision-and-scope.md`](vision-and-scope.md), [`design-multi-mode-and-authoring.md`](design-multi-mode-and-authoring.md), [`customizing-qgis-light.md`](customizing-qgis-light.md) |


## 1. Introduction

### 1.1 Purpose

This SRS specifies the requirements for **Release 1.0 (MVP)** of QGIS Modes — a
working multi-mode QGIS plugin, without the visual authoring tool. It also
records post-MVP requirements at lower priority so the design can accommodate
them. It is the contract against which the design ([Stage 4](design-multi-mode-and-authoring.md))
and verification are traced.

### 1.2 Scope of the product

QGIS Modes is a QGIS plugin that provides multiple simplified QGIS interfaces
("modes"), selectable and switchable at runtime. It hides and regroups existing
QGIS UI elements; it adds no GIS functionality. See
[`vision-and-scope.md`](vision-and-scope.md) for the full scope rationale.

### 1.3 Definitions

| Term | Meaning |
| :-- | :-- |
| **Mode** | One simplified interface, defined by one **mode file**. |
| **Mode file** | A JSON file describing a mode: a `meta` block plus interface sections. |
| **Simplified mode** | The state in which a mode is applied and the standard QGIS UI is hidden. |
| **Standard interface** | QGIS's normal, full interface. |
| **Token** | A string in a mode file naming an existing QGIS/plugin UI element. |
| **Token resolution** | Turning tokens into live Qt objects — the core mechanism inherited from QGIS Light. |
| **Original layout** | The toolbar/panel arrangement captured before simplified mode is first entered. |
| **Provider policy** | The allow-list of QGIS data-source / data-item providers. |
| **The Designer** | The future visual mode-authoring tool (post-MVP). |

### 1.4 Requirement conventions

- **Identifiers.** `FR-<area>-<n>` for functional, `NFR-<area>-<n>` for
  non-functional, `UC-<n>` for use cases, `IF-<n>` for interfaces. IDs are
  stable and never reused.
- **Priority (MoSCoW).** **M** = Must (MVP-blocking) · **S** = Should (MVP if
  feasible) · **C** = Could (post-MVP) · **W** = Won't (this release).
- **"shall"** denotes a binding requirement.
- **DECISION** callouts mark open choices from
  [`vision-and-scope.md`](vision-and-scope.md) §11; each states a recommended
  default used by this draft.

### 1.5 References

QGIS plugin development and publishing
([docs.qgis.org PyQGIS cookbook](https://docs.qgis.org/latest/en/docs/pyqgis_developer_cookbook/plugins/plugins.html),
[plugins.qgis.org/docs/publish](https://plugins.qgis.org/docs/publish),
[plugin security scanning](https://plugins.qgis.org/docs/security-scanning),
[QGIS Human Interface Guidelines](https://docs.qgis.org/latest/en/docs/developers_guide/hig.html))
inform the packaging, quality, and usability requirements in §5.


## 2. Overall description

### 2.1 Product perspective

QGIS Modes is a Python plugin loaded into the QGIS process. It is **derived from
QGIS Light** and reuses its config-driven, token-resolution architecture
(documented in [`customizing-qgis-light.md`](customizing-qgis-light.md)),
generalising one config into many switchable modes. It is a self-contained
plugin with no server component.

### 2.2 Product functions (summary)

1. Load and validate mode files 

   1.1 import and export mode files from QGIS Light, User Profiles, and other users Mode files

2. enter and exit simplified mode

3. capture and restore the original layout

4. select and switch modes at runtime · 

5. build the interface from a mode via token resolution · 

6. keep the user safe (always exit, always switch, fail soft) · 

7. persist state across sessions.

### 2.3 User classes

Per [`vision-and-scope.md`](vision-and-scope.md) §7: **P1** end user, **P2**
educator, **P3** mode author, **P4** maintainer. P1 and P2 are the primary
runtime users for the MVP; P3 authors modes by editing JSON in the MVP.



### 2.4 Operating environment

- QGIS **3.22+ and 4.x**; Qt 5 (QGIS 3) and Qt 6 (QGIS 4); PyQt5 / PyQt6.
- Windows, Linux, macOS.
- Runtime plugin dependencies: **QuickMapServices**, **DataPlotly**.

> **DECISION D1.** This draft assumes minimum QGIS **3.22** (dual Qt support).
> Choosing 4.0+ only would drop NFR-CMP-2's Qt 5 obligation. 
>
> **Decision: minimum QGIS can be 3.4**

### 2.5 Design and implementation constraints

| ID | Constraint |
| :-- | :-- |
| CON-1 | Plain QGIS Python plugin — no build/compile step. |
| CON-2 | Single codebase for Qt 5 and Qt 6 (fully-scoped enum names; the `associatedObjects()` / `toEnum()` shims). |
| CON-3 | Licensed GPL-3.0-or-later; a `LICENSE` file ships in the package. |
| CON-4 | The deployable unit is the `src/qgismodes/` folder; its name is ASCII and does not start with a digit. |
| CON-5 | The package contains no binaries, no generated files, no `__pycache__`/`.git`. |
| CON-6 | Mode files are data — parsed as JSON only; never `eval`/`exec`-ed. |
| CON-7 | Built only on the public QGIS/PyQt API; no private QGIS internals beyond documented widget discovery. |

### 2.6 Assumptions and dependencies

| ID | Assumption / dependency |
| :-- | :-- |
| ASM-1 | QGIS calls `classFactory` → `initGui` / `unload` and emits `initializationCompleted` as documented. |
| ASM-2 | The QGIS Light token-resolution logic ports without redesign. |
| ASM-3 | `QgsSettings` and `QgsApplication.qgisSettingsDirPath()` behave as documented under Qt 5 and Qt 6. |
| ASM-4 | QuickMapServices and DataPlotly are installed when a mode references them; absence degrades gracefully (FR-UI-6). |
| ASM-5 | Users have write access to their QGIS profile directory. |


## 3. Functional requirements

Priorities: **M**ust · **S**hould · **C**ould · **W**on't (this release).

### 3.1 Mode files and schema (FR-MF)

| ID | Pri | Requirement | Acceptance criteria |
| :-- | :-- | :-- | :-- |
| FR-MF-1 | M | Each mode shall be defined by a single JSON mode file. | A well-formed mode file produces exactly one selectable mode. |
| FR-MF-2 | M | A mode file shall contain a `meta` block with at least `id`, `name`, and integer `schema`. | A file missing any of the three is rejected (FR-MF-5). |
| FR-MF-3 | M | A mode file shall support the sections `menus`,`toolbars`, `algorithms`, `panels`, `statusbar, docks, browser`.UPDATE: all the customizable UI elements | Each section, when present, is applied per §3.4–§3.5. |
| FR-MF-4 | M | The system shall validate every mode file against the published JSON Schema on load. | A file violating the schema is detected before it is applied. |
| FR-MF-5 | M | An invalid or unparseable mode file shall be skipped with a logged diagnostic; it shall not abort plugin load or startup. | With one corrupt file present, all valid modes still load; a warning names the bad file. |
| FR-MF-6 | M | The mode-file format shall carry an integer `schema` version. | A file whose `schema` exceeds the supported version is skipped with an explanatory diagnostic. |
| FR-MF-7 | M | Provider policy shall be defined once and shared by all modes — never stored per mode file. | The schema has no per-mode `providers` section; switching modes does not change provider policy. |
| FR-MF-8 | C | A mode file may declare `meta.requires` (names of QGIS plugins it depends on). | When present, the value is readable by the mode manager for dependency warnings. |

### 3.2 Mode storage and discovery (FR-MS)

| ID | Pri | Requirement | Acceptance criteria |
| :-- | :-- | :-- | :-- |
| FR-MS-1 | M | The system shall load **bundled** modes from the plugin's `modes/` directory. | Bundled modes appear in the mode list. |
| FR-MS-2 | M | The system shall load **user** modes from `<QGIS profile>/qgismodes/modes/`. | A user-placed mode file appears in the mode list after reload. |
| FR-MS-3 | M | A user mode shall override (shadow) a bundled mode having the same `meta.id`. | With both present, the user version is the one offered. |
| FR-MS-4 | M | User modes shall be unaffected by plugin upgrade/reinstall. | After reinstalling the plugin, user modes still exist and load. |
| FR-MS-5 | S | On first run with an empty user modes directory, the system shall seed it by copying the bundled modes. | First launch creates editable copies; **DECISION D5**. |
| FR-MS-6 | C | The system shall import an existing QGIS Light `config.json` as a `default` mode. | Legacy migration; **DECISION D3**. |

*Add: FR-MS-7. Provide function to share and backup/restore mode files (export/import capability). FR-MS-8. Gracefully adapt early schema versions of mode files to current standard*

### 3.3 Lifecycle — enter / exit simplified mode (FR-LC)

| ID | Pri | Requirement | Acceptance criteria |
| :-- | :-- | :-- | :-- |
| FR-LC-1 | M | The system shall provide a user command to **enter** simplified mode. | Invoking it applies the active mode and hides the standard UI. |
| FR-LC-2 | M | On the **first** entry, the system shall capture the original toolbar and panel layout. | The captured layout is persisted and is sufficient to fully reconstruct the pre-simplification UI. |
| FR-LC-3 | M | The system shall provide a user command to **exit** to the standard interface. | Invoking it removes mode UI and restores the standard UI. |
| FR-LC-4 | M | On exit, the system shall restore the captured original layout exactly. | Toolbars/panels return to their prior visibility, position, and dock state. |
| FR-LC-5 | M | Simplified state (on/off and active mode) shall persist across QGIS restarts. | Restarting QGIS while simplified resumes the same mode. |
| FR-LC-6 | M | When simplified mode is active at startup, building the interface shall be deferred until QGIS initialisation completes. | Tokens referencing other plugins' toolbars resolve correctly at startup. |
| FR-LC-7 | M | A mode switch shall **not** re-capture or overwrite the stored original layout. | After A→B→exit, the UI matches the state captured before A. |
| FR-LC-8 | M | On plugin `unload()`, the system shall remove all UI it added and, if simplified mode is active, restore the standard interface. | After disabling the plugin, no QGIS Modes UI remains and the standard UI is intact. |

### 3.4 Mode selection and switching (FR-SW)

| ID | Pri | Requirement | Acceptance criteria |
| :-- | :-- | :-- | :-- |
| FR-SW-1 | M | The system shall let the user select which mode to apply, listing modes by `meta.name`. | The picker shows every installed mode's human name. |
| FR-SW-2 | M | The system shall let the user switch to a different mode **while remaining in simplified mode**, without restarting QGIS. | Switching A→B replaces the interface in place; QGIS is not restarted. |
| FR-SW-3 | M | The system shall persist the active mode `id` and reapply it on next startup. | Selected mode survives a restart. |
| FR-SW-4 | M | The active mode shall be indicated in the mode picker. | The current mode is visibly marked. |
| FR-SW-5 | M | When ≥ 2 modes are installed, a mode switcher shall be reachable from within the simplified interface. | A user in simplified mode can switch modes without exiting first. |
| FR-SW-6 | S | A mode switch shall complete without flicker of the standard (un-simplified) interface. | The menu bar / standard toolbars do not momentarily reappear during a switch. |

### 3.5 Interface construction — token resolution (FR-UI)

| ID | Pri | Requirement | Acceptance criteria |
| :-- | :-- | :-- | :-- |
| FR-UI-1 | M | The system shall create the toolbars defined in the active mode's `toolbars` section, in the specified areas. | Each declared toolbar appears in its `area` with its items. |
| FR-UI-2 | M | The system shall resolve `parent:identifier` tokens to existing QGIS or plugin UI elements (matched by object name, text, or tooltip). | A valid token yields the corresponding live action/widget. |
| FR-UI-3 | M | The system shall render a nested array of tokens as a single dropdown button, the first item shown by default. | A grouped array produces one drop-down tool button. |
| FR-UI-4 | M | The system shall support `separator`, `section:Label`, wildcard (`*`) expansion, processing-algorithm id tokens, and `algorithms:<group>` tokens. | Each token form behaves as documented in [`customizing-qgis-light.md`](customizing-qgis-light.md) §2.5. |
| FR-UI-5 | M | The system shall apply the `panels` section (visibility, dock area, fixed/hidden state) and the `statusbar` section. | Listed panels/status-bar widgets reach their declared state; unlisted panels are hidden. |
| FR-UI-6 | M | A token that fails to resolve shall be skipped with a logged diagnostic; interface construction shall continue. | A mode with one bad token still builds; the bad token is named in the log. |
| FR-UI-7 | M | On entering simplified mode, the system shall hide the menu bar and all standard toolbars and panels not required by the active mode. | Only the active mode's toolbars/panels are visible. |
| FR-UI-8 | M | `apply_mode()` shall tear down only the toolbars QGIS Modes created, never `QAction`s borrowed from QGIS. | After repeated switching, borrowed QGIS actions remain valid and functional. |

### 3.6 Safety and guard rails (FR-GR)

| ID | Pri | Requirement | Acceptance criteria |
| :-- | :-- | :-- | :-- |
| FR-GR-1 | M | The simplified interface shall **always** present a visible control to exit to the standard interface. | Every mode, including a minimal or malformed-but-loadable one, shows an exit control. |
| FR-GR-2 | M | When ≥ 2 modes are installed, the simplified interface shall always present a mode switcher (see FR-SW-5). | The switcher is present regardless of mode-file content. |
| FR-GR-3 | M | The exit control and mode switcher shall be **injected by the runtime**, independent of mode-file content. | Removing all items from a mode file does not remove the exit/switcher. |
| FR-GR-4 | M | If the active mode fails to load or apply, the system shall fall back to a known-good mode, or to the standard interface, and inform the user. | A corrupt active mode never leaves the user with a broken or empty interface. |
| FR-GR-5 | M | All foreseeable errors (file I/O, parse, token, Qt) shall be caught, logged to the "QGIS Modes" log tab, and — when user-relevant — surfaced via the message bar. | No QGIS Modes operation produces an unhandled exception dialog or crash. |

### 3.7 Persistence and configuration (FR-PS)

| ID | Pri | Requirement | Acceptance criteria |
| :-- | :-- | :-- | :-- |
| FR-PS-1 | M | All persisted state shall be stored in `QgsSettings` under the `qgismodes/` namespace. | Keys observed: `qgismodes/enabled`, `qgismodes/mode`, and the captured layout. |
| FR-PS-2 | M | The system shall not write outside its `qgismodes/` settings namespace and its own modes directories. | No settings/files are created elsewhere. |

### 3.8 Provider policy (FR-PP)

| ID | Pri | Requirement | Acceptance criteria |
| :-- | :-- | :-- | :-- |
| FR-PP-1 | S | The system shall apply a single shared provider policy when simplified mode is first entered. | Providers outside the policy are removed once; **DECISION D2**. |
| FR-PP-2 | M* | A mode switch shall not change provider policy. | Switching modes leaves data providers unchanged. *(M if FR-PP-1 is built.)* |
| FR-PP-3 | S | The system shall warn the user that restoring removed providers requires a QGIS restart. | A message is shown on exit when providers were removed. |

### 3.9 Visual Mode Designer (FR-DS) — post-MVP

| ID | Pri | Requirement |
| :-- | :-- | :-- |
| FR-DS-1 | C | The system shall provide a visual dialog to create and edit mode files without editing JSON. |
| FR-DS-2 | C | The Designer shall present available tools/panels/algorithms by real icon and label, never raw tokens. |
| FR-DS-3 | C | The Designer shall build interfaces by drag-and-drop and round-trip existing mode files. |
| FR-DS-4 | W | "Pick from QGIS" capture, live preview, and undo/redo. |

> FR-DS-* are recorded so the MVP design does not foreclose them; they are **not**
> in Release 1.0. Their full design is in
> [`design-multi-mode-and-authoring.md`](design-multi-mode-and-authoring.md)
> Part B.

## 4. Use cases

Each use case lists its exercised requirements.

**UC-1 — First-time use.**
*Actor:* P1/P2. *Pre:* plugin installed, never enabled.
*Flow:* user invokes "enter simplified mode" → original layout captured → the
default mode is applied → standard UI hidden.
*Post:* a simplified interface with an exit control is shown.
*Covers:* FR-LC-1, FR-LC-2, FR-UI-1, FR-UI-7, FR-GR-1, FR-MS-1.

**UC-2 — Switch modes mid-session.**
*Actor:* P2. *Pre:* in simplified mode "Analysis"; ≥ 2 modes installed.
*Flow:* user opens the mode switcher → picks "Raster Processing" → interface is
torn down and rebuilt in place.
*Post:* "Raster Processing" is active; original layout untouched; QGIS not
restarted.
*Covers:* FR-SW-1, FR-SW-2, FR-SW-5, FR-UI-8, FR-LC-7, FR-PP-2.

**UC-3 — Exit to standard QGIS.**
*Actor:* P1/P2. *Pre:* in simplified mode.
*Flow:* user invokes the exit control → mode UI removed → original layout
restored.
*Post:* the standard QGIS interface is exactly as before simplification.
*Covers:* FR-LC-3, FR-LC-4, FR-GR-1.

**UC-4 — Author a mode by editing JSON** (MVP authoring path).
*Actor:* P3. *Pre:* plugin installed.
*Flow:* author copies an existing mode file in the user modes directory →
edits it → reloads the plugin → the new mode appears in the picker.
*Post:* the new mode is selectable.
*Covers:* FR-MS-2, FR-MF-1..6, FR-SW-1.

**UC-5 — Recover from a broken mode.**
*Actor:* P2. *Pre:* the active mode file is malformed.
*Flow:* startup → active mode fails validation → system logs it, falls back to a
good mode (or standard QGIS), and informs the user.
*Post:* the user has a usable interface and is not trapped.
*Covers:* FR-MF-5, FR-GR-4, FR-GR-5.

**UC-6 — Restart while simplified.**
*Actor:* P1/P2. *Pre:* simplified mode active, QGIS closed and reopened.
*Flow:* QGIS starts → plugin sees `qgismodes/enabled` → defers build to
`initializationCompleted` → reapplies the persisted mode.
*Post:* the same mode is active after restart.
*Covers:* FR-LC-5, FR-LC-6, FR-SW-3.


## 5. Non-functional requirements

### 5.1 Compatibility (NFR-CMP)

| ID | Pri | Requirement | Acceptance |
| :-- | :-- | :-- | :-- |
| NFR-CMP-1 | M | One codebase shall run on QGIS 3.22+ and QGIS 4.x. | Verified on a QGIS 3.x and a QGIS 4.x install. |
| NFR-CMP-2 | M | The code shall run under both Qt 5 / PyQt5 and Qt 6 / PyQt6 (fully-scoped enums; the documented shims). | No Qt-version errors on either. |
| NFR-CMP-3 | M | The plugin shall function on Windows, Linux, and macOS. | Core flows verified per platform (at least Windows; others by review/spot-check). |
| NFR-CMP-4 | M | `metadata.txt` shall set `qgisMaximumVersion=4.99` to remain on the "QGIS 4 Ready" list. | Field present and correct. |

### 5.2 Performance (NFR-PRF)

| ID | Pri | Requirement | Acceptance |
| :-- | :-- | :-- | :-- |
| NFR-PRF-1 | M | A mode switch shall complete in **< 1 s** on a typical project and machine. | Measured switch time < 1 s. |
| NFR-PRF-2 | S | The plugin shall add **< 200 ms** to QGIS startup when simplified mode is off. | Measured startup delta within budget. |

### 5.3 Usability (NFR-USA)

| ID | Pri | Requirement | Acceptance |
| :-- | :-- | :-- | :-- |
| NFR-USA-1 | M | A first-time non-technical user shall be able to enter a mode, switch modes, and exit, **with no training and no dead-ends**. | Confirmed in informal usability testing (Goal G3). |
| NFR-USA-2 | M | The user shall **never** be left unable to return to the standard interface through the UI. | No reachable state lacks an exit (see FR-GR-1/3). |
| NFR-USA-3 | S | The interface shall follow the QGIS Human Interface Guidelines where applicable (minimalism, grouping, novice-first). | Reviewed against the HIG. |
| NFR-USA-4 | S | Diagnostics shall be discoverable in the Log Messages panel under a "QGIS Modes" tab; user-facing notices use the message bar. | Both channels present and used. |

### 5.4 Reliability (NFR-REL)

| ID | Pri | Requirement | Acceptance |
| :-- | :-- | :-- | :-- |
| NFR-REL-1 | M | The plugin shall not crash QGIS under any specified operation or input. | Survives the §4 use cases plus malformed inputs without crashing. |
| NFR-REL-2 | M | Exiting simplified mode or unloading the plugin shall restore the standard interface to its pre-simplification state 100% of the time. | No residual/missing toolbars or panels after exit/unload. |
| NFR-REL-3 | M | `unload()` shall remove every menu item, toolbar item, and widget the plugin added, and disconnect every signal it connected. | Verified by inspection and by enable→disable cycling. |
| NFR-REL-4 | S | Repeated enter/exit and mode-switch cycles shall not leak widgets or degrade behaviour. | 20 cycles leave behaviour and the standard UI intact. |

### 5.5 Maintainability (NFR-MNT)

| ID | Pri | Requirement | Acceptance |
| :-- | :-- | :-- | :-- |
| NFR-MNT-1 | M | Customising an interface shall require **only** editing a mode file — no code change. | A new mode is created without touching Python. |
| NFR-MNT-2 | M | Code shall follow PEP 8 and pass Flake8 with no errors. | Flake8 reports zero errors. |
| NFR-MNT-3 | S | Public modules, classes, and methods shall carry docstrings. | Spot-check: all public APIs documented. |
| NFR-MNT-4 | S | The mode-file format shall be defined by a versioned, published JSON Schema. | `schema/mode.schema.json` exists and matches FR-MF. |

### 5.6 Security (NFR-SEC)

| ID | Pri | Requirement | Acceptance |
| :-- | :-- | :-- | :-- |
| NFR-SEC-1 | M | The package shall pass the plugins.qgis.org security scan (Bandit, detect-secrets) with **no CRITICAL findings**. | Local Bandit + detect-secrets run is clean. |
| NFR-SEC-2 | M | Mode files shall be treated as data: parsed as JSON only, never `eval`/`exec`-ed (CON-6). | No dynamic-execution calls on file content. |
| NFR-SEC-3 | M | The plugin shall contain no hardcoded secrets/credentials and make no undisclosed network calls. | detect-secrets clean; no network code in 1.0. |

### 5.7 Licensing and packaging (NFR-PKG)

| ID | Pri | Requirement | Acceptance |
| :-- | :-- | :-- | :-- |
| NFR-PKG-1 | M | The plugin shall be licensed GPL-3.0-or-later, with a `LICENSE` file in the package and SPDX/GPL notices in source headers; QGIS Light attribution preserved. | License file and headers present and correct. |
| NFR-PKG-2 | M | `metadata.txt` shall contain all repository-required fields (`name`, `qgisMinimumVersion`, `description`, `about`, `version`, `author`, `email`, `repository`) and the recommended `tags`, `changelog`, `category`, `tracker`, `homepage`; `about` shall disclose the QuickMapServices/DataPlotly dependencies. | Metadata validated against the publish checklist. |
| NFR-PKG-3 | M | The published package shall contain no binaries, no generated files, and no `__pycache__`/`.git` (CON-5). | Package inspected before upload. |
| NFR-PKG-4 | M | The 1.0 release shall set `experimental=False`. | Field is `False` for the public release. |
| NFR-PKG-5 | M | `metadata.txt` `homepage`, `repository`, and `tracker` URLs shall be live and point to the QGIS Modes repository. | All three URLs resolve. |
| NFR-PKG-6 | M | `plugin_dependencies` shall list QuickMapServices and DataPlotly so QGIS prompts the user to install them. | Field present; install prompt observed. |


## 6. External interface requirements

| ID | Interface | Requirement |
| :-- | :-- | :-- |
| IF-1 | **QGIS plugin API** | `__init__.py` exposes `classFactory(iface)`; the plugin class implements `initGui()` and `unload()` (FR-LC-8, NFR-REL-3). |
| IF-2 | **QgsSettings** | State under `qgismodes/`: `enabled`, `mode`, captured layout (FR-PS-1). |
| IF-3 | **File system** | Reads bundled modes from `<plugin>/modes/`; reads/writes user modes under `<QGIS profile>/qgismodes/modes/` (FR-MS-1/2). |
| IF-4 | **Mode file format** | JSON conforming to `schema/mode.schema.json` (FR-MF-4). |
| IF-5 | **QGIS UI surface** | Discovers and reuses existing QGIS/plugin `QAction`/`QToolBar`/`QDockWidget`/`QWidget` objects via token resolution (FR-UI-2). |
| IF-6 | **User commands** | A toolbar/menu entry point to enter simplified mode; an in-canvas exit control and mode switcher (FR-LC-1/3, FR-SW-5). |


## 7. Out of scope for Release 1.0

The visual Mode Designer and all of Phase 4 (FR-DS-*); mode import/export UI;
internationalisation; rebuilding a trimmed menu bar; managing PIP dependencies;
an automated test suite (a manual verification checklist is used instead — see
§8). Permanent exclusions are in [`vision-and-scope.md`](vision-and-scope.md) §8.3.


## 8. Verification approach and Definition of Done

There is no automated test framework in 1.0; verification is by a **manual
verification checklist** executed before release, structured around the §4 use
cases and the acceptance criteria in §3 and §5.

**Release 1.0 is Done when:**

1. Every **M** requirement passes its acceptance criteria.
2. All six use cases (UC-1…UC-6) pass on QGIS 3.22+ and QGIS 4.x.
3. Flake8, Bandit, and detect-secrets are clean (NFR-MNT-2, NFR-SEC-1).
4. The package meets all NFR-PKG requirements.
5. Goals G1–G5 ([`vision-and-scope.md`](vision-and-scope.md) §5) are met.
6. The traceability matrix (Stage 4) shows every **M** requirement covered by a
   design element.


## 9. Traceability

| Direction | Status |
| :-- | :-- |
| Vision goals → requirements | G1→§5.7; G2→FR-SW; G3→NFR-USA; G4→NFR-REL/FR-GR/FR-LC; G5→FR-MF/NFR-MNT. |
| Requirements → design | **Pending Stage 4** — a requirement-to-design matrix will be added to `design-specification.md`. |
| Requirements → verification | §8 manual checklist, keyed by requirement ID. |


## 10. Open decisions (consolidated)

| # | Decision | This draft assumes | Confirm? |
| :-- | :-- | :-- | :-- |
| D1 | Minimum QGIS version | 3.4 (dual Qt 5/6) — §2.4 | [X] |
| D2 | Provider trimming in MVP | Yes, *Should* — FR-PP-1. Explain in more detail | ☐ |
| D3 | Legacy `config.json` migration | *Could* — FR-MS-6 - see additional requirements | [X] |
| D4 | Number of bundled example modes | Three (default + two) — Goal G2. Need | ☐ |
| D5 | Seed user modes dir on first run | Yes, *Should* — FR-MS-5 | [X] |

> **Reviewer:** confirm or amend D1–D5 and flag any requirement to add, remove,
> or re-prioritise. On sign-off this SRS becomes **baseline v1.0** and Stage 4
> (design specification) begins.
