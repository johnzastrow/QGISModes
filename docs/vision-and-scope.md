# QGIS Modes — Vision & Scope

| | |
| :-- | :-- |
| **Document** | Vision & Scope |
| **Project** | QGIS Modes |
| **Version** | 1.0 — baseline |
| **Date** | 2026-05-23 |
| **Status** | Baselined (tag `spec-v1.0`). All five stages complete. |
| **Related** | [`requirements.md`](requirements.md) (SRS), [`design-multi-mode-and-authoring.md`](design-multi-mode-and-authoring.md) (design), [`customizing-qgis-light.md`](customizing-qgis-light.md) (inherited architecture) |

> This document is **Stage 1** of a formal requirements & design process. It
> establishes *why* QGIS Modes exists and *what* its boundaries are. The
> numbered, testable requirements derive from it and live in
> [`requirements.md`](requirements.md). Open decisions needing the project
> owner's confirmation are collected in [§11](#11-open-decisions-for-review).


## 1. Purpose

This document defines the business rationale, stakeholders, users, goals, and
scope of QGIS Modes. It is the apex of the project's requirements baseline:
every requirement in the SRS must trace to a goal stated here, and every scope
boundary stated here constrains the SRS.


## 2. Background

QGIS is a capable, professional GIS application — and, as a direct consequence,
a complex one: many toolbars, panels, menus, and hundreds of processing
algorithms. For non-technical audiences (secondary education, citizen science)
that complexity is a barrier.

**QGIS Light** (by Serkan Girgin; the project QGIS Modes is derived from)
addressed this with a config-driven plugin: a single `config.json` declares one
simplified interface, and the plugin builds it by hiding and regrouping existing
QGIS UI elements.

That approach has one structural limitation: **it provides exactly one
simplified interface.** Different tasks need different tool sets. A data-capture
exercise, a spatial-analysis exercise, a raster-processing exercise, and a
map-output exercise each call for a different curated set of tools. With a
single config, serving all of them means either one bloated "compromise"
interface or hand-editing `config.json` between activities — impractical,
error-prone, and impossible to do quickly in front of a class.

**QGIS Modes** generalises QGIS Light's mechanism from one config to many. Each
task-specific interface becomes a named **mode**; the user selects and switches
between modes at runtime.


## 3. Problem statement

> A teacher runs a field-mapping activity in the morning and a data-analysis
> activity in the afternoon. The two activities need different, equally simple
> tool sets. Today they must choose between one cluttered interface that covers
> both, or manually rewriting a configuration file between sessions. There is no
> supported way to define several simple interfaces and switch between them in
> seconds — and no way for the non-developer who designs the lessons to create
> those interfaces without editing JSON by hand.

QGIS Modes exists to remove the first half of that problem now (multiple
selectable modes) and the second half later (visual authoring).


## 4. Product vision statement

> **For** educators, citizen-science coordinators, and the non-technical users
> they support,
> **who** need a QGIS interface focused on one specific task at a time,
> **QGIS Modes** is a QGIS plugin
> **that** provides multiple simplified interfaces ("modes") which can be
> selected and switched at runtime.
> **Unlike** QGIS Light, which provides a single fixed simplified interface,
> **QGIS Modes** lets one QGIS installation serve many task-specific workflows
> and move between them in seconds.


## 5. Goals and success metrics

| ID | Goal | Success metric (measurable) |
| :-- | :-- | :-- |
| **G1** | Ship a real, installable plugin. | Published and **approved** on plugins.qgis.org as a **non-experimental** release that passes the repository's automated QA/security scan. |
| **G2** | Deliver working multi-mode behaviour. | A user can switch among **≥ 3 modes** at runtime, with no QGIS restart, each rebuilding the interface correctly. |
| **G3** | Be safe for non-technical users. | In usability testing, a first-time user can enter a mode, switch modes, and return to standard QGIS **with no guidance and no dead-ends**. |
| **G4** | Be reliable and reversible. | Entering and exiting simplified mode restores the original QGIS interface **100%** of the time across supported platforms; the plugin never crashes QGIS. |
| **G5** | Keep modes authorable. | A mode can be created or changed by editing one JSON file, validated against a published schema — **no code changes**. |
| **G6** | Preserve provenance and licensing. | QGIS Light is credited in code, docs, and metadata; the project ships valid GPL-3.0-or-later licensing. |

G1–G5 are MVP goals. G6 is continuous.


## 6. Stakeholders

| Stakeholder | Interest / stake | Influence on requirements |
| :-- | :-- | :-- |
| **Project owner / maintainer** (John Zastrow) | Delivers and releases the plugin; owns scope decisions. | Decision authority; sign-off. |
| **End users** (students, field volunteers) | Use a mode to do GIS work; must not be confused or trapped. | Drive usability & safety requirements. |
| **Educators / activity leaders** | Choose and switch modes for a class; may tweak modes. | Drive mode-selection & switching requirements. |
| **Mode authors** (curriculum designers, GIS-literate volunteers) | Create and curate modes. | Drive the mode-file format & (future) authoring tool. |
| **QGIS plugin repository reviewers** | Gate-keep plugins.qgis.org; enforce metadata, licensing, QA. | Drive packaging, licensing, and quality NFRs. |
| **QGIS Light project** (ITC-CRIB / Serkan Girgin) | Origin of the codebase and design. | Attribution & licensing obligations. |
| **QuickMapServices & DataPlotly maintainers** | Their plugins are runtime dependencies. | Dependency-handling requirements. |


## 7. User personas

**P1 — Sam, the end user** (student / field volunteer).
Non-technical. Opens QGIS to do one task with a mode someone prepared. Must not
be able to break the setup or get lost. *Needs:* a small, predictable interface;
an always-obvious way back to normal.

**P2 — Dana, the educator / activity leader.**
Semi-technical. Picks the mode appropriate to today's activity and may switch
modes mid-session. Occasionally adjusts a mode. *Needs:* fast, obvious mode
selection; switching without restarting QGIS; confidence nothing is destroyed.

**P3 — Alex, the mode author** (curriculum designer / GIS-literate volunteer).
Comfortable editing structured text. Curates the tool set for each activity.
*Needs (MVP):* a documented, validated mode-file format and a clear edit→reload
cycle. *Needs (future):* a visual authoring tool (no JSON).

**P4 — Jordan, the project maintainer.**
Develops, packages, and releases the plugin. *Needs:* a config-driven design,
clean code, and a package that passes repository QA.

**P5 — Timmy, GIS Analyst.**
Uses many tools in QGIS, but needs to focus on one type of work at time. Finds the cluttered UI with tons of toolbars and buttons distracting. *Needs:* configure modes to slim the interface down to focus controls on the task at hand, allow quickly switching between them as the work changes. For example, Raster analysis, Vector analysis, Vector editing, Attribute work, Data Management


## 8. Scope

### 8.1 In scope — MVP (Phases 1 & 2)

The first release is a **working multi-mode plugin without the visual editor**:

- Define simplified interfaces as **mode files** (JSON), each self-describing
  via a `meta` block, validated against a published JSON Schema.
- Load modes from a **bundled** location and a **user** location (user modes
  survive plugin upgrades and override bundled ones).
- **Enter / exit** simplified mode, capturing and faithfully restoring the
  user's original toolbar/panel layout.
- **Select** a mode and **switch** between modes at runtime, without restarting
  QGIS; persist the choice across sessions.
- Build the interface by **token resolution** (toolbars, dropdown groups,
  processing algorithms, panels, status bar) — the mechanism inherited from
  QGIS Light.
- **Guard rails:** the user can always exit and always switch modes; a broken
  mode file is skipped, not fatal.
- Ship **bundled example modes** and full documentation.
- Be **publishable** on plugins.qgis.org (packaging, licensing, QA compliance).

### 8.2 Future scope — post-MVP (Phases 3 & 4)

Designed for, but **not built in the MVP**:

- **Visual Mode Designer** — a drag-and-drop dialog to author modes without JSON.
- **"Pick from QGIS"** capture, **live preview**, **undo/redo** in the Designer.
- Mode **import/export** UI and "mode pack" distribution helpers.
- Internationalisation of mode labels.

### 8.3 Out of scope (permanently)

- Adding new GIS/analysis functionality — QGIS Modes only hides and regroups
  what QGIS and other plugins already provide.
- Changing QGIS core or replacing QGIS's own customization systems.
- Simplifying separate windows (Layout Designer, attribute tables).
- Managing non-plugin (PIP) Python dependencies.
- Acting as a profile manager — QGIS user profiles remain QGIS's concern.


## 9. Release strategy

| Release | Content | Gate |
| :-- | :-- | :-- |
| **0.x (current)** | Design + skeleton. | — |
| **1.0 (MVP)** | Phases 1 & 2 — working multi-mode plugin (toolbars, panels, algorithms, status bar, import/export). | Goals G1–G5 met; published, non-experimental, on plugins.qgis.org. |
| **1.1** | Power-user features — per-mode **menu-bar rebuild** (FR-UI-9), per-mode context-menu opt-in. | Power users (P5) can replace the standard menu bar with a mode-defined one; no need to keep the entire QGIS menu bar hidden. |
| **1.x** | Phase 3 — visual Mode Designer (FR-DS-*). | Authoring without JSON. |
| **1.x+** | Phase 4 — capture (FR-CP-*), live preview, polish. | — |

**1.0 is deliberately short-lived.** It establishes the engine and a publishable
baseline; 1.1 follows quickly with the menu-bar rebuild and related power-user
controls — the features P5 (GIS analyst) needs. Each release is independently
shippable. The phased roadmap is detailed in
[`design-multi-mode-and-authoring.md`](design-multi-mode-and-authoring.md).


## 10. Constraints and assumptions (summary)

Detailed constraints and assumptions are itemised in the SRS
([`requirements.md`](requirements.md) §2.4–§2.5). At a glance:

- **Platform:** a single codebase must run on QGIS **3.44+** and QGIS 4.x (Qt 5
  and Qt 6), on Windows, Linux, and macOS.
- **No build system:** a plain QGIS Python plugin — no compile step, and (today)
  no automated test suite.
- **Licensing:** GPL-3.0-or-later, inherited from QGIS Light.
- **Runtime dependencies:** QuickMapServices and DataPlotly (other QGIS plugins).
- **Assumption:** QGIS's plugin lifecycle and `QgsSettings` behave as documented;
  the token-resolution mechanism ports cleanly from QGIS Light.


## 11. Open decisions for review

All five are **resolved** (mirrored in [`requirements.md`](requirements.md) §10).

| # | Decision | Resolution |
| :-- | :-- | :-- |
| **D1** | Minimum QGIS version | **3.44+** (and QGIS 4.x). Latest 3.x LTR; supports every API the plugin needs. |
| **D2** | Data-provider trimming in MVP | **Deferred** — FR-PP-* moved to *Could* for v1.0. P5 (power user) needs an unrestricted Browser; revisit alongside v1.1 power-user work. |
| **D3** | Legacy QGIS Light `config.json` migration | **Could** — FR-MS-6. Broader import/export need formalised as FR-MS-7a / 7b / 8 / 9 / 10. |
| **D4** | Bundled example modes in 1.0 | **Three** — `default`, `raster-analysis`, `vector-editing`. |
| **D5** | First-run seeding of user modes dir | **Yes** (*Should*) — FR-MS-5. |

> All decisions baselined; further changes require a new change-note round.
