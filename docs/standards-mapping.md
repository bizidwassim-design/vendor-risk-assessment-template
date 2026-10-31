# Standards mapping

How the workbook supports each standard, by identifier only. This is a working aid, not an official
interpretation: always check the current text of each standard before relying on it in an audit.

## 1. Template element → standard

| Template element | ISO/IEC 27001:2022 Annex A | NIST CSF 2.0 | SOC 2 (2017 TSC) | ISO/IEC 42001:2023 |
|------------------|----------------------------|--------------|------------------|--------------------|
| `01_Methodology` — tiering criteria, cadence, rating matrix | A.5.19 | GV.SC-01, GV.SC-03, GV.RM-01 | CC9.2 | A.10.2 |
| `02_Vendor_Inventory` — vendor list, criticality, access, AI flag | A.5.19, A.5.21, A.5.23 | GV.SC-04, ID.AM-04 | CC9.2 | A.10.2, A.10.3 |
| `03_Questionnaire` — due diligence before and during the relationship | A.5.19, A.5.21, A.5.22 | GV.SC-06, GV.SC-07 | CC9.2 | A.10.3 |
| `04_Assessment_Summary` — residual rating, review cadence, overdue flag | A.5.22 | GV.SC-07, GV.SC-09 | CC9.2 | A.10.3 |
| `05_Contract_Clauses_Checklist` — security in agreements | A.5.20, A.5.23 | GV.SC-05, GV.SC-10 | CC9.2 | A.10.3, A.10.4 |
| `06_Dashboard` — oversight, coverage, overdue reviews | A.5.22 (monitoring) ; clause 9.3 inputs | GV.OV-01, GV.SC-09 | CC9.2 | clause 9.3 |

## 2. Questionnaire domain → standard

| Domain | ISO/IEC 27001:2022 Annex A | NIST CSF 2.0 | SOC 2 | ISO/IEC 42001:2023 |
|--------|----------------------------|--------------|-------|--------------------|
| Governance & Risk | A.5.1, A.5.2, A.5.4, A.6.1, A.6.3, A.6.6 | GV.OC, GV.RR, GV.PO, GV.RM | CC1, CC2, CC3 | A.2, A.3 |
| Access Control | A.5.15, A.5.16, A.5.17, A.5.18, A.8.2, A.8.5 | PR.AA-01 to PR.AA-05 | CC6.1, CC6.2, CC6.3 | — |
| Data Protection & Privacy | A.5.12, A.5.13, A.5.14, A.5.34, A.8.10, A.8.12 | PR.DS-01, PR.DS-10, GV.OC-03 | CC6.5, CC6.7, C1, P series | A.7 |
| Encryption | A.8.24, A.8.20 | PR.DS-01, PR.DS-02 | CC6.1, CC6.6, CC6.7 | — |
| Vulnerability & Patch Management | A.8.8, A.8.9, A.8.29 | ID.RA-01, ID.RA-08, PR.PS-02 | CC7.1 | — |
| Logging & Monitoring | A.8.15, A.8.16, A.8.17 | DE.CM-01, DE.CM-09, DE.AE-02 | CC7.2 | — |
| Incident Response & Notification | A.5.24, A.5.25, A.5.26, A.5.27, A.5.28, A.6.8 | RS.MA, RS.CO-02, RS.CO-03, GV.SC-08 | CC7.3, CC7.4, CC7.5 | A.8.4 |
| Business Continuity & Resilience | A.5.29, A.5.30, A.8.13, A.8.14 | PR.IR-03, PR.IR-04, RC.RP | A1.1, A1.2, A1.3 | — |
| Sub-processors & Supply Chain | A.5.19, A.5.20, A.5.21, A.5.22 | GV.SC-02, GV.SC-04, GV.SC-05, GV.SC-06, GV.SC-10 | CC9.2 | A.10.2, A.10.3 |
| Secure Development | A.8.25, A.8.26, A.8.27, A.8.28, A.8.29, A.8.31, A.8.32 | PR.PS-06, ID.RA-09 | CC8.1 | A.6.2 |
| AI Usage | A.5.19, A.5.34, A.8.10 | GV.SC-04, GV.RM-01, ID.RA-01 | CC9.2 | A.4.2, A.5.2, A.5.4, A.6.2, A.7.2, A.7.4, A.8.2, A.9.2, A.9.3, A.10.2, A.10.3, A.10.4 |

## 3. Contract clause → standard

| Clause | ISO/IEC 27001:2022 | NIST CSF 2.0 | SOC 2 | ISO/IEC 42001:2023 |
|--------|--------------------|--------------|-------|--------------------|
| CL-01 Confidentiality | A.6.6 | GV.SC-05 | CC9.2 | — |
| CL-02 Security obligations | A.5.20 | GV.SC-05 | CC9.2 | A.10.3 |
| CL-03 Data processing terms | A.5.34, A.5.20 | GV.SC-05, GV.OC-03 | P6 series | A.10.3 |
| CL-04 Data location and transfers | A.5.20, A.5.23 | GV.SC-05 | CC6.7 | — |
| CL-05 Incident notification | A.5.20, A.5.24 | GV.SC-08, RS.CO-02 | CC7.3 | A.8.4 |
| CL-06 Right to audit / assurance | A.5.20, A.5.22 | GV.SC-07 | CC9.2 | A.10.3 |
| CL-07 Sub-processor transparency | A.5.21 | GV.SC-04, GV.SC-05 | CC9.2 | A.10.3 |
| CL-08 Return and deletion | A.5.20, A.8.10 | GV.SC-10, PR.DS-01 | CC6.5 | A.7.2 |
| CL-09 Service levels | A.5.20, A.5.30 | GV.SC-05, PR.IR-04 | A1.1 | — |
| CL-10 BC/DR commitments | A.5.29, A.5.30 | PR.IR-03, RC.RP-01 | A1.2, A1.3 | — |
| CL-11 Vendor staff access and MFA | A.5.15, A.5.20, A.8.5 | PR.AA-03 | CC6.1 | — |
| CL-12 Patching commitments | A.5.20, A.8.8 | PR.PS-02 | CC7.1 | — |
| CL-13 Cooperation in incidents | A.5.20, A.5.26 | RS.CO-03, GV.SC-08 | CC7.4 | — |
| CL-14 Liability and indemnity | A.5.20 | GV.RM-05 | CC9.2 | — |
| CL-15 Cyber insurance | A.5.20 | GV.RM-05 | CC9.1 | — |
| CL-16 Exit assistance | A.5.20, A.5.30 | GV.SC-10 | CC9.2 | — |
| CL-17 Change notification | A.5.22 | GV.SC-07 | CC9.2 | A.10.3 |
| CL-18 AI usage terms | A.5.20 | GV.SC-05 | CC9.2 | A.10.2, A.10.3, A.10.4, A.8.2 |

## 4. Where the evidence lives for an audit

| Auditor question | Where to point |
|------------------|----------------|
| How do you decide how deeply to assess a supplier? | `01_Methodology` sections 1 and 2 |
| Which suppliers are in scope and why? | `02_Vendor_Inventory` (score, tier, data, access) |
| What did you check and what did you find? | `03_Questionnaire` copy for the vendor, plus the evidence folder referenced in the summary notes |
| Who accepted the residual risk and when is the next review? | `04_Assessment_Summary` (final rating, owner, next review) |
| Are the security requirements in the contract? | `05_Contract_Clauses_Checklist` for the vendor |
| How does management oversee supplier risk? | `06_Dashboard` in the management-review pack |
