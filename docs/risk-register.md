# QGIS Modes — Risk Register

| | |
| :-- | :-- |
| **Document** | Risk Register |
| **Project** | QGIS Modes |
| **Version** | 1.0 — baseline |
| **Date** | 2026-05-23 |
| **Status** | Stage 5 (final stage); baselined with the rest of the spec set. |
| **Scope** | Risks affecting design, implementation, and first release of QGIS Modes 1.0. |
| **Companions** | [`requirements.md`](requirements.md), [`design-specification.md`](design-specification.md), [`vision-and-scope.md`](vision-and-scope.md) |

---

## 1. Purpose

Identify, score, and assign mitigations for risks to delivering Release 1.0
(MVP — Phases 1 & 2). Reviewed at minimum at the start of each implementation
phase and before plugin upload to plugins.qgis.org.

## 2. Classification

| Dimension | Values |
|:--|:--|
| **Likelihood** | L (< 20%) · M (20–50%) · H (> 50%) |
| **Impact** | L (cosmetic / recoverable) · M (rework or delay) · H (blocks release or breaks user trust) |
| **Severity** | the worse of likelihood / impact (H × H = Critical) |

Risk categories: **T** technical · **S** schedule / process · **A** adoption /
external · **L** licensing / IP.

---

## 3. Risk register

### 3.1 Technical (T)

| ID | Risk | L | I | Sev | Mitigation | Status |
|:--|:--|:-:|:-:|:--|:--|:--|
| T1 | QGIS internal object names (toolbars, actions) drift between 3.44 and 4.x; some tokens fail to resolve. | M | L | M | FR-UI-6 skips + logs unresolved tokens; manual verification on both QGIS lines (UC-1..6). | Designed |
| T2 | `jsonschema` library missing in QGIS bundled Python; ModeLoader cannot do full schema validation. | M | M | M | Fallback hand-validator in ModeLoader covers `meta.{id,name,schema}` + top-level types. Test on QGIS 3.44 LTR pre-implementation. | Designed (spec §11) |
| T3 | A plugin enabled *after* QGIS Modes enters simplified mode adds a visible toolbar that QGIS Modes didn't hide. | M | L | M | Document caveat in user docs for 1.0; design event-filter hook in v1.1. | Accepted (spec §11) |
| T4 | Two QGIS instances on the same profile race on `QgsSettings` writes. | L | M | M | Document caveat; do not engineer around for 1.0. | Accepted (spec §11) |
| T5 | A QGIS plugin unloads while QGIS Modes is showing its `QAction` in a simplified toolbar — dangling reference. | L | H | M | Avoid plugin unload during simplified mode (docs); catch deleted-action exception in TokenResolver and skip-log. | Mitigated |
| T6 | Captured layout (Qt enum integer values) doesn't round-trip across Qt5 / Qt6 boundary. | M | M | M | `toEnum()` shim already designed (spec §3.6); test enable→disable on both Qt lines. | Designed |
| T7 | "Keep both" import semantically rewrites `meta.id` — sender's intent diverges. | H | L | M | Documented in spec §11; surface the rewritten id in the import-summary message. | Accepted (spec §11) |
| T8 | Mode-switch latency > 1 s on systems with many plugin toolbars / large algorithm groups. | L | M | L | NFR-PRF-1 acceptance test in DoD; if exceeded, profile and optimise. | Designed |
| T9 | `mainwindow.initializationCompleted` already fired before our connect (race on startup). | L | H | M | If `qgismodes/enabled` is true and signal has not yet fired, defensively call `enable()` via `QTimer.singleShot(0, …)`; verify on first QGIS 3.44 install. | Mitigated |

### 3.2 Schedule / process (S)

| ID | Risk | L | I | Sev | Mitigation | Status |
|:--|:--|:-:|:-:|:--|:--|:--|
| S1 | Implementation reveals design gaps requiring SRS updates; baseline churn. | M | M | M | Change-note process: each requirement change gets a logged commit with rationale; SRS / design version bumped on every change. | Process |
| S2 | Scope creep into v1.1 features (menu rebuild, Designer) before 1.0 ships. | M | M | M | MoSCoW priorities are strict; release strategy commits to "deliberately short-lived 1.0"; PR review enforces. | Process |
| S3 | Manual verification checklist (SRS §8 DoD) is labour-intensive every release. | H | L | M | Accept manual for 1.0; consider lightweight UC smoke tests in 1.x (e.g. `pytest-qgis`). | Accepted |
| S4 | Multi-week implementation gap → context loss across sessions. | M | L | L | Memory file + per-commit message discipline + this doc set. | Mitigated |

### 3.3 Adoption / external (A)

| ID | Risk | L | I | Sev | Mitigation | Status |
|:--|:--|:-:|:-:|:--|:--|:--|
| A1 | plugins.qgis.org approval delayed or rejected. | L | M | L | Pre-publish: validate against the NFR-PKG checklist; run Bandit + detect-secrets locally (NFR-SEC-1). | Designed |
| A2 | Automated security scan (Bandit / detect-secrets) flags a critical finding. | L | H | M | Local pre-upload run; keep the repo free of `eval` / `exec` / `subprocess` / hardcoded secrets from the start. | Mitigated |
| A3 | User confusion: "modes" vs QGIS "user profiles". | M | L | M | Glossary in docs; explicit "mode is not a profile" callout (already in vision-and-scope §8.3). | Designed |
| A4 | Existing QGIS Light users confused about QGIS Modes vs QGIS Light. | M | L | M | README / CLAUDE.md / file headers preserve attribution and explain relationship. Legacy migration (FR-MS-6) eases transition. | Designed |
| A5 | P5 power-users dissatisfied with v1.0 (no menu rebuild, no quick-run). | M | M | M | v1.0 explicitly "deliberately short-lived"; v1.1 ships power-user features per release strategy. Surface this in the plugin description on the repository page. | Accepted |
| A6 | Plugin dependencies (QuickMapServices, DataPlotly) not installed; users see broken-looking modes. | M | L | M | `plugin_dependencies` triggers install prompt (≥ 3.8, OK at 3.44 floor); FR-MS-10 plugin-requires preview at import; FR-UI-6 logs unresolved tokens. | Mitigated |
| A7 | Bundled modes (default, raster-analysis, vector-editing) don't match what users expect or want. | M | L | M | Users author and import their own modes (UC-4, UC-8); bundled are demonstrations only. | Accepted |

### 3.4 Licensing / IP (L)

| ID | Risk | L | I | Sev | Mitigation | Status |
|:--|:--|:-:|:-:|:--|:--|:--|
| L1 | GPL compliance issues with a derivative of QGIS Light. | L | H | M | Attribution preserved in code headers, LICENSE appendix, metadata.txt `about`, README, CLAUDE.md. GPL-3.0-or-later inherited. | Mitigated |
| L2 | Third-party content in icons / docs not GPL-compatible. | L | L | L | All icons inherited from QGIS Light (GPL); no other third-party assets. Verify before any future addition. | Mitigated |

---

## 4. Active-mitigation summary

The design and SRS already address most foreseeable risks:

- **Robustness on bad input** — every component public method catches and logs (NFR-REL-1, FR-GR-5).
- **Reversibility** — captured original layout fully restores standard QGIS (FR-LC-4, NFR-REL-2).
- **Validation** — JSON Schema + version check before any mode is applied (FR-MF-4..6).
- **Guard rails** — exit and switcher always present, runtime-injected (FR-GR-1 / 2 / 3).
- **Forward-compat** — schema version + ModeLoader version check defends against future-format files (FR-MS-8).

## 5. Risks accepted as-is

Per design, these are documented limitations of 1.0 rather than active risks:

- **T3** late-arriving plugin toolbars — caveat documented; engineered fix in v1.1.
- **T4** multi-process race on QgsSettings — caveat documented; not engineered around in 1.0.
- **T7** "Keep both" id rewrite — documented in design §11.
- **S3** manual verification labour — accepted for 1.0; automated tests considered for 1.x.
- **A5** P5 dissatisfaction with v1.0 alone — addressed by deliberately-short-lived 1.0 + v1.1 ramp.
- **A7** bundled mode mismatch — bundled modes are demonstrations; users author their own.

## 6. Review cadence

- **On every change-note** to SRS or design specification.
- **Before each plugin upload** — re-run pre-publish checklist; re-score active risks.
- **After release** — review based on bug reports; add new risks discovered.

## 7. References

- [SRS §8 Definition of Done](requirements.md)
- [Design Specification §11 Open implementation questions](design-specification.md)
- [Vision & Scope §9 Release strategy](vision-and-scope.md)
