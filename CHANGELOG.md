# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed
- The first visit opens on the fictional sample, with a banner and a *Start with a blank assessment* button that is remembered, so visitors see real-looking results straight away.

### Added
- Web app (`index.html`, `assets/`, `data/tprm.js`): inventory and tiering, the 60-question questionnaire with domain scores, band and residual rating, contract-clause checklist per tier, dashboard with coverage and overdue reviews, JSON export/import, CSV summary, print, local draft, light and dark themes, strict CSP. Hosted on GitHub Pages.
- `scripts/build_web_data.py` generates `data/tprm.js` from the build script; CI checks it is current, syntax-checks the app and validates the HTML.

## [1.0.0] — 2026-10-31

### Added
- Initial public release.
- `Vendor-Risk-Assessment-Template.xlsx` with six sheets: methodology and tiering model, vendor inventory (20 rows,
  6 fictional vendors), 60-question weighted questionnaire with automatic domain scores, assessment summary with
  residual rating, next review and overdue flag, contract clauses checklist per tier, dashboard with charts.
- `questionnaire/vendor-questionnaire.md` and `.csv` generated from the same question list.
- `docs/standards-mapping.md` for ISO/IEC 27001:2022 A.5.19–A.5.23, NIST CSF 2.0 GV.SC, SOC 2 CC9.2 and ISO/IEC 42001 A.10.
- CI that rebuilds the workbook and the questionnaire exports and fails on drift; Dependabot; security policy.
