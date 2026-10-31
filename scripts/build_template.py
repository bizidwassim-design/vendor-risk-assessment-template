#!/usr/bin/env python3
"""
Build Vendor-Risk-Assessment-Template.xlsx and the questionnaire exports.

An open-source third-party risk management (TPRM) workbook: vendor tiering
(inherent risk), a weighted security questionnaire, residual-risk rating,
contract-clause checklist and a dashboard. Aligned with ISO/IEC 27001:2022
(A.5.19-A.5.23), NIST CSF 2.0 (GV.SC), SOC 2 (CC9.2) and ISO/IEC 42001 (A.10).

Usage:
    pip install openpyxl
    python scripts/build_template.py          # writes the workbook + questionnaire/*.csv|.md

The workbook contains no macros and no personal data. All sample vendors are
fictional. Licensed under the MIT License (see LICENSE).
"""
from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.comments import Comment
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

# --------------------------------------------------------------------------- #
# Design tokens
# --------------------------------------------------------------------------- #
FONT = "Arial"
NAVY = "1F3864"
MID_BLUE = "2F5597"
LIGHT_BLUE = "D9E2F3"
PALE = "F2F2F2"
INPUT_BLUE = "0000FF"
GRID = "BFBFBF"
HIGHLIGHT = "FFF2CC"

thin = Side(style="thin", color=GRID)
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

# Sheet names
S_METH = "01_Methodology"
S_INV = "02_Vendor_Inventory"
S_Q = "03_Questionnaire"
S_SUM = "04_Assessment_Summary"
S_CLAUSE = "05_Contract_Clauses_Checklist"
S_DASH = "06_Dashboard"

INV_FIRST, INV_LAST = 5, 24      # 20 vendor rows
SUM_FIRST, SUM_LAST = 6, 25      # 20 assessment rows

# (label, fill, text colour)
TIERS = [
    ("Tier 1", "C00000", "FFFFFF"),
    ("Tier 2", "F4B183", "7F3200"),
    ("Tier 3", "C6E0B4", "1E4620"),
]
RATINGS = [
    ("Low", "C6E0B4", "1E4620"),
    ("Medium", "FFE699", "7F6000"),
    ("High", "F4B183", "7F3200"),
    ("Critical", "C00000", "FFFFFF"),
]
RATING_ORDER = ["Critical", "High", "Medium", "Low"]

# --------------------------------------------------------------------------- #
# Tiering model (single source of truth: tables on 01_Methodology, formulas
# in the inventory look them up)
# --------------------------------------------------------------------------- #
DATA_CLASS = [("Public", 1), ("Internal", 2), ("Confidential", 3), ("Restricted", 4)]
CRITICALITY = [("Low", 1), ("Medium", 2), ("High", 3), ("Critical", 4)]
ACCESS = [("None", 1), ("Read-only", 2), ("Read / write", 3), ("Privileged / integrated", 4)]
AI_USE = [("No", 1), ("Yes", 2)]
TIER1_MIN = 36   # inherent score >= 36 -> Tier 1
TIER2_MIN = 12   # 12-35 -> Tier 2 ; below -> Tier 3

CADENCE_MONTHS = {"Tier 1": 12, "Tier 2": 24, "Tier 3": 36}

# Questionnaire score bands (percentage of weighted points obtained)
SCORE_BANDS = [("Strong", 85), ("Adequate", 70), ("Weak", 50), ("Poor", 0)]

# Residual rating = f(tier, score band)
RESIDUAL = {
    "Tier 1": {"Strong": "Medium", "Adequate": "High", "Weak": "Critical", "Poor": "Critical"},
    "Tier 2": {"Strong": "Low", "Adequate": "Medium", "Weak": "High", "Poor": "High"},
    "Tier 3": {"Strong": "Low", "Adequate": "Low", "Weak": "Medium", "Poor": "Medium"},
}

CATEGORIES = ["SaaS", "Cloud infrastructure (IaaS/PaaS)", "Managed service provider", "Software / licence",
              "Professional services", "Logistics / operations", "Hardware", "Data processor / analytics"]
STATUS_INV = ["Onboarding", "Active", "Under review", "Offboarding", "Offboarded"]
STATUS_ASSESS = ["Not started", "Questionnaire sent", "In review", "Complete", "Remediation agreed"]
ANSWERS = ["Yes", "Partial", "No", "N/A"]
YN = ["Y", "N"]

# --------------------------------------------------------------------------- #
# Fictional vendors (id, name, service, category, owner role, data class,
# criticality, access, ai, data location, contract end, status, notes)
# --------------------------------------------------------------------------- #
VENDORS = [
    ("VND-001", "Contoso Cloud Platform", "Hosting of the ERP and customer portal (IaaS/PaaS)",
     "Cloud infrastructure (IaaS/PaaS)", "Head of Infrastructure", "Restricted", "Critical",
     "Privileged / integrated", "No", "EU (two regions)", date(2027, 6, 30), "Active",
     "Single cloud provider for production workloads. Exit plan to be documented."),
    ("VND-002", "Fabrikam People Cloud", "HR and payroll SaaS for all employees",
     "SaaS", "Head of HR", "Restricted", "High", "Read / write", "Yes", "EU", date(2027, 3, 31), "Active",
     "Processes employee personal and banking data. Embedded AI assistant for HR queries."),
    ("VND-003", "Northwind Logistics", "Third-party warehousing and last-mile delivery with EDI integration",
     "Logistics / operations", "Head of Supply Chain", "Confidential", "Critical", "Read / write", "No",
     "EU + UK", date(2026, 12, 31), "Active",
     "Receives customer delivery addresses by EDI. Contract renewal due; include updated clauses."),
    ("VND-004", "Litware Insight", "AI-driven demand-forecasting analytics (SaaS)",
     "Data processor / analytics", "Head of Data & Analytics", "Confidential", "Medium", "Read-only", "Yes",
     "US", date(2027, 9, 30), "Active",
     "Sales history exported nightly. Vendor trains models on aggregated customer data - confirm opt-out."),
    ("VND-005", "Proseware Managed IT", "Outsourced service desk and endpoint administration",
     "Managed service provider", "IT Operations Manager", "Confidential", "High", "Privileged / integrated", "No",
     "EU (remote access)", date(2027, 1, 31), "Active",
     "Holds domain-admin equivalent rights through a PAM solution. Quarterly access review required."),
    ("VND-006", "Wingtip Print & Promo", "Printed marketing material and branded merchandise",
     "Professional services", "Marketing Manager", "Public", "Low", "None", "No", "Local", date(2027, 12, 31), "Active",
     "No access to systems or personal data. Receives approved artwork only."),
]

# --------------------------------------------------------------------------- #
# Questionnaire: (id, domain, question, weight, evidence requested)
# Weight: 3 = critical control, 2 = important, 1 = good practice
# --------------------------------------------------------------------------- #
DOMAINS = [
    ("GOV", "Governance & Risk"),
    ("ACC", "Access Control"),
    ("DAT", "Data Protection & Privacy"),
    ("ENC", "Encryption"),
    ("VUL", "Vulnerability & Patch Management"),
    ("LOG", "Logging & Monitoring"),
    ("INC", "Incident Response & Notification"),
    ("BCP", "Business Continuity & Resilience"),
    ("SUB", "Sub-processors & Supply Chain"),
    ("DEV", "Secure Development"),
    ("AI", "AI Usage"),
]

QUESTIONS = [
    # Governance & Risk
    ("GOV-01", "GOV", "Do you maintain an information security programme with a named accountable executive (CISO or equivalent)?", 2, "Security organisation chart or policy extract naming the role"),
    ("GOV-02", "GOV", "Do you hold a current independent attestation or certification covering the service in scope (for example ISO/IEC 27001 or SOC 2 Type II)?", 3, "Certificate with scope statement, or SOC 2 Type II report under NDA"),
    ("GOV-03", "GOV", "Are information security policies approved by management, reviewed at least annually and communicated to all staff?", 2, "Policy index with approval and review dates"),
    ("GOV-04", "GOV", "Do you perform a formal information security risk assessment at least annually, with documented treatment plans?", 2, "Risk assessment summary or methodology description"),
    ("GOV-05", "GOV", "Are all staff and contractors subject to background screening appropriate to their role before being granted access?", 1, "Screening policy extract"),
    ("GOV-06", "GOV", "Do all staff sign confidentiality agreements and receive security awareness training at hire and at least annually?", 2, "Training completion statistics for the last 12 months"),
    # Access Control
    ("ACC-01", "ACC", "Is multi-factor authentication enforced for all staff access to systems that store or process customer data?", 3, "MFA policy and screenshot of enforcement configuration"),
    ("ACC-02", "ACC", "Is privileged (administrative) access restricted to named individuals, granted on a least-privilege basis and reviewed at least quarterly?", 3, "Last privileged access review record (redacted)"),
    ("ACC-03", "ACC", "Are user access rights removed or adjusted within one business day of a leaver or role change?", 2, "Joiner / mover / leaver procedure"),
    ("ACC-04", "ACC", "Does the service support single sign-on (SAML or OpenID Connect) and role-based access for customer users?", 2, "Product documentation for SSO and roles"),
    ("ACC-05", "ACC", "Is remote and administrative access to production performed only through a managed, logged channel (for example a bastion host or privileged access management tool)?", 2, "Architecture description of the administrative access path"),
    ("ACC-06", "ACC", "Are shared or generic accounts prohibited for production systems, with any exceptions documented and controlled?", 1, "Account management standard"),
    # Data Protection & Privacy
    ("DAT-01", "DAT", "Is customer data classified and handled according to a documented data-handling standard?", 2, "Data classification standard"),
    ("DAT-02", "DAT", "Is customer data logically or physically segregated from other customers' data?", 3, "Multi-tenancy architecture description"),
    ("DAT-03", "DAT", "Can you confirm the countries or regions where customer data is stored and processed, and are transfers outside those regions contractually controlled?", 3, "Data location statement and transfer mechanism"),
    ("DAT-04", "DAT", "Is customer data securely deleted or returned within an agreed period after contract termination, with written confirmation?", 2, "Data retention and deletion procedure"),
    ("DAT-05", "DAT", "Do you have a privacy programme (including a privacy contact and a process for data-subject requests) where personal data is processed?", 2, "Privacy notice or data processing addendum"),
    ("DAT-06", "DAT", "Are data-loss-prevention or equivalent controls in place to detect or block unauthorised bulk export of customer data?", 1, "Description of DLP or export controls"),
    # Encryption
    ("ENC-01", "ENC", "Is customer data encrypted in transit using current protocol versions (TLS 1.2 or higher) for all external interfaces?", 3, "TLS configuration summary or external scan result"),
    ("ENC-02", "ENC", "Is customer data encrypted at rest, including backups, using industry-accepted algorithms?", 3, "Encryption-at-rest statement for storage and backups"),
    ("ENC-03", "ENC", "Are encryption keys managed in a dedicated key management system with restricted access and documented rotation?", 2, "Key management standard"),
    ("ENC-04", "ENC", "Can the customer hold or control its own encryption keys (BYOK / HYOK) if required?", 1, "Product documentation"),
    ("ENC-05", "ENC", "Are secrets (API keys, passwords, certificates) stored in a secrets vault rather than in code or configuration files?", 2, "Secrets management standard"),
    # Vulnerability & Patch Management
    ("VUL-01", "VUL", "Are systems in scope scanned for vulnerabilities at least monthly, with authenticated scans where possible?", 2, "Scan schedule and summary of last scan (no technical detail required)"),
    ("VUL-02", "VUL", "Are critical vulnerabilities remediated within 14 days and high within 30 days, or compensated and risk-accepted with a documented reason?", 3, "Patch SLA policy and compliance metric for the last quarter"),
    ("VUL-03", "VUL", "Is an independent penetration test of the service performed at least annually, with findings tracked to closure?", 3, "Latest penetration test summary letter"),
    ("VUL-04", "VUL", "Are hardened configuration baselines applied to servers, containers and cloud resources, and checked for drift?", 2, "Hardening standard reference"),
    ("VUL-05", "VUL", "Do you operate a responsible-disclosure or bug-bounty channel for external researchers?", 1, "Public disclosure policy link"),
    # Logging & Monitoring
    ("LOG-01", "LOG", "Are security-relevant events (authentication, privilege use, data access, configuration changes) logged for all in-scope systems?", 3, "Logging standard"),
    ("LOG-02", "LOG", "Are logs centralised, protected against tampering and retained for at least 12 months?", 2, "Log retention statement"),
    ("LOG-03", "LOG", "Is there 24x7 security monitoring (in-house or outsourced SOC) with defined escalation paths?", 3, "Monitoring service description"),
    ("LOG-04", "LOG", "Are customer-facing audit logs available to the customer (via console or API) for their own tenant?", 2, "Product documentation"),
    ("LOG-05", "LOG", "Are clocks on in-scope systems synchronised to a reliable time source?", 1, "Statement"),
    # Incident Response & Notification
    ("INC-01", "INC", "Do you maintain a documented incident response plan that is tested at least annually?", 3, "Plan table of contents and date of last exercise"),
    ("INC-02", "INC", "Will you notify the customer of a confirmed security incident affecting its data or service within 24 hours of confirmation?", 3, "Contractual notification commitment"),
    ("INC-03", "INC", "Does the notification include the nature of the incident, data affected, actions taken and a named contact?", 2, "Notification template"),
    ("INC-04", "INC", "Are post-incident reviews performed and lessons learned tracked to closure?", 1, "Post-incident review template"),
    ("INC-05", "INC", "Do you have cyber insurance or equivalent financial cover for incidents affecting customers?", 1, "Insurance certificate summary"),
    ("INC-06", "INC", "Have you had a security incident affecting customer data in the last 24 months? If yes, please describe the root cause and remediation. (Answer 'Yes' if NO incident occurred or if an incident was fully remediated and disclosed.)", 2, "Incident summary if applicable"),
    # Business Continuity & Resilience
    ("BCP-01", "BCP", "Do you have a business continuity and disaster recovery plan covering the service, tested at least annually?", 3, "Last DR test summary with date and outcome"),
    ("BCP-02", "BCP", "Are recovery time and recovery point objectives (RTO / RPO) for the service defined and contractually committed?", 2, "Service-level description"),
    ("BCP-03", "BCP", "Are backups taken at least daily, stored in a separate location or account, and restore-tested at least quarterly?", 3, "Backup and restore test policy"),
    ("BCP-04", "BCP", "Is the service deployed with redundancy (multiple availability zones or sites) to avoid a single point of failure?", 2, "Architecture summary"),
    ("BCP-05", "BCP", "Do you publish service availability and planned maintenance to customers, and report against the committed SLA?", 1, "Status page link or SLA report"),
    # Sub-processors & Supply Chain
    ("SUB-01", "SUB", "Do you maintain and publish a list of sub-processors that handle customer data, with their location and purpose?", 3, "Sub-processor list"),
    ("SUB-02", "SUB", "Are customers notified in advance of new sub-processors, with a right to object?", 2, "Contractual clause or notification process"),
    ("SUB-03", "SUB", "Do you assess the security of your own critical suppliers before onboarding and periodically thereafter?", 2, "Supplier risk management procedure"),
    ("SUB-04", "SUB", "Do you flow down equivalent security, confidentiality and notification obligations to sub-processors?", 2, "Standard sub-processor contract clauses"),
    ("SUB-05", "SUB", "Do you maintain a software bill of materials (SBOM) or equivalent inventory of third-party components in the service?", 1, "Statement or sample SBOM"),
    # Secure Development
    ("DEV-01", "DEV", "Do you follow a documented secure development life cycle with security requirements, threat modelling and code review?", 2, "SDLC overview"),
    ("DEV-02", "DEV", "Are static and dependency vulnerability scans run automatically in the build pipeline, with blocking thresholds for critical findings?", 2, "Pipeline description"),
    ("DEV-03", "DEV", "Are development, test and production environments separated, and is production customer data excluded from non-production environments (or masked)?", 3, "Environment separation standard"),
    ("DEV-04", "DEV", "Are changes to production approved, tested and traceable to a change record, with emergency changes reviewed afterwards?", 2, "Change management procedure"),
    ("DEV-05", "DEV", "Are developers trained in secure coding at least annually?", 1, "Training record summary"),
    # AI Usage
    ("AI-01", "AI", "Does the service use AI or machine-learning components (including third-party large language models) to process customer data? If yes, are they documented and disclosed to customers?", 3, "AI feature inventory and disclosure"),
    ("AI-02", "AI", "Is customer data excluded from training or fine-tuning of models that serve other customers, unless the customer explicitly opts in?", 3, "Data-use terms for AI features"),
    ("AI-03", "AI", "Where third-party AI providers are used, are prompts and outputs not retained by the provider (zero-retention) or retained only under contract?", 2, "Third-party AI provider terms"),
    ("AI-04", "AI", "Are AI features subject to an impact or risk assessment covering accuracy, bias, misuse and data leakage before release?", 2, "AI impact assessment summary"),
    ("AI-05", "AI", "Is there human oversight for AI outputs that affect individuals or material business decisions, and can the customer disable AI features?", 2, "Product documentation for AI controls"),
    ("AI-06", "AI", "Is AI system behaviour monitored in production (drift, abuse, prompt injection) with a process to roll back or disable a model?", 1, "AI monitoring description"),
]
assert len(QUESTIONS) == 60, len(QUESTIONS)

# Sample answers for the worked example (VND-002 Fabrikam People Cloud)
SAMPLE_VENDOR = "VND-002"
SAMPLE_ANSWERS = {
    "GOV-01": "Yes", "GOV-02": "Yes", "GOV-03": "Yes", "GOV-04": "Yes", "GOV-05": "Partial", "GOV-06": "Yes",
    "ACC-01": "Yes", "ACC-02": "Yes", "ACC-03": "Partial", "ACC-04": "Yes", "ACC-05": "Yes", "ACC-06": "Yes",
    "DAT-01": "Yes", "DAT-02": "Yes", "DAT-03": "Yes", "DAT-04": "Partial", "DAT-05": "Yes", "DAT-06": "No",
    "ENC-01": "Yes", "ENC-02": "Yes", "ENC-03": "Yes", "ENC-04": "No", "ENC-05": "Yes",
    "VUL-01": "Yes", "VUL-02": "Partial", "VUL-03": "Yes", "VUL-04": "Yes", "VUL-05": "Yes",
    "LOG-01": "Yes", "LOG-02": "Yes", "LOG-03": "Yes", "LOG-04": "Partial", "LOG-05": "Yes",
    "INC-01": "Yes", "INC-02": "Partial", "INC-03": "Yes", "INC-04": "Yes", "INC-05": "Yes", "INC-06": "Yes",
    "BCP-01": "Yes", "BCP-02": "Yes", "BCP-03": "Yes", "BCP-04": "Yes", "BCP-05": "Yes",
    "SUB-01": "Yes", "SUB-02": "Yes", "SUB-03": "Partial", "SUB-04": "Yes", "SUB-05": "No",
    "DEV-01": "Yes", "DEV-02": "Yes", "DEV-03": "Yes", "DEV-04": "Yes", "DEV-05": "Partial",
    "AI-01": "Yes", "AI-02": "Yes", "AI-03": "Partial", "AI-04": "Partial", "AI-05": "Yes", "AI-06": "No",
}
SAMPLE_COMMENTS = {
    "DAT-06": "Vendor: export controls limited to role-based permissions; DLP on roadmap for next year.",
    "INC-02": "Vendor commits to 48 hours; negotiate 24 hours in the renewal.",
    "VUL-02": "Critical patch SLA is 30 days; compensating WAF controls described.",
    "AI-03": "LLM provider retains prompts for 30 days for abuse monitoring.",
    "AI-06": "No drift monitoring for the HR assistant yet.",
}

# --------------------------------------------------------------------------- #
# Contract clauses: (id, clause, why it matters, tier1, tier2, tier3)
# R = Required, S = Recommended, O = Optional
# --------------------------------------------------------------------------- #
CLAUSES = [
    ("CL-01", "Confidentiality and non-disclosure", "Protects information shared before and during the contract.", "R", "R", "R"),
    ("CL-02", "Information security obligations (reference to a security schedule or standard)", "Makes the controls assessed in the questionnaire contractually binding.", "R", "R", "S"),
    ("CL-03", "Data processing terms (roles, purpose, instructions, personal-data obligations)", "Required wherever personal data is processed on your behalf.", "R", "R", "S"),
    ("CL-04", "Data location and cross-border transfer restrictions", "Keeps data in approved regions and documents the transfer mechanism.", "R", "R", "O"),
    ("CL-05", "Security incident notification within a defined time (for example 24 hours)", "Lets you meet your own regulatory and customer notification deadlines.", "R", "R", "S"),
    ("CL-06", "Right to audit or to receive independent assurance reports annually", "Gives you evidence between assessments without relying on self-attestation.", "R", "S", "O"),
    ("CL-07", "Sub-processor transparency, prior notice and right to object", "Prevents your data from flowing to parties you have not assessed.", "R", "R", "O"),
    ("CL-08", "Data return and secure deletion at termination, with certificate", "Closes the risk at the end of the relationship.", "R", "R", "S"),
    ("CL-09", "Service levels with RTO / RPO and service credits", "Aligns the vendor's resilience with your business-continuity needs.", "R", "S", "O"),
    ("CL-10", "Business continuity and disaster-recovery commitments with annual testing", "Ensures the vendor can actually recover, not just promise to.", "R", "S", "O"),
    ("CL-11", "Access control and MFA requirements for vendor staff accessing your systems", "Essential where the vendor holds privileged or remote access.", "R", "S", "O"),
    ("CL-12", "Vulnerability management and patching commitments with timelines", "Turns the patch SLA from an answer into an obligation.", "R", "S", "O"),
    ("CL-13", "Cooperation during incidents, investigations and regulatory enquiries", "Avoids delays when you need logs or support under pressure.", "R", "R", "S"),
    ("CL-14", "Liability and indemnity for security and data breaches (cap appropriate to the data)", "Allocates financial consequences of a breach.", "R", "S", "O"),
    ("CL-15", "Cyber insurance minimum cover", "Backs the liability clause with real financial capacity.", "R", "S", "O"),
    ("CL-16", "Exit assistance and transition period", "Reduces concentration and lock-in risk for critical services.", "R", "S", "O"),
    ("CL-17", "Change notification for material changes to the service, architecture or security posture", "Triggers a reassessment when the risk profile changes.", "S", "S", "O"),
    ("CL-18", "AI usage terms: disclosure of AI features, no training on your data without consent, human oversight", "Addresses the specific risks of AI-enabled services.", "R", "R", "S"),
]
CLAUSE_LEVELS = {"R": "Required", "S": "Recommended", "O": "Optional"}


# --------------------------------------------------------------------------- #
# Style helpers
# --------------------------------------------------------------------------- #
def f(bold: bool = False, color: str = "000000", size: int = 10, italic: bool = False) -> Font:
    return Font(name=FONT, bold=bold, color=color, size=size, italic=italic)


def fill(hex_color: str) -> PatternFill:
    return PatternFill("solid", start_color=hex_color, end_color=hex_color)


def put(ws, ref: str, value=None, *, font=None, bg=None, align=None, border=False, fmt=None):
    cell = ws[ref]
    if value is not None:
        cell.value = value
    cell.font = font or f()
    if bg:
        cell.fill = fill(bg)
    cell.alignment = align or Alignment(vertical="top", wrap_text=True)
    if border:
        cell.border = BORDER
    if fmt:
        cell.number_format = fmt
    return cell


def header(ws, row: int, labels, *, start_col: int = 1, height: int = 34, bg: str = NAVY):
    for i, label in enumerate(labels):
        c = ws.cell(row=row, column=start_col + i, value=label)
        c.font = f(bold=True, color="FFFFFF")
        c.fill = fill(bg)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDER
    ws.row_dimensions[row].height = height


def title(ws, text: str, subtitle: str | None = None, width_cols: int = 8):
    ws["A1"].value = text
    ws["A1"].font = f(bold=True, color="FFFFFF", size=16)
    ws["A1"].alignment = Alignment(vertical="center")
    for col in range(1, width_cols + 1):
        ws.cell(row=1, column=col).fill = fill(NAVY)
    ws.row_dimensions[1].height = 34
    if subtitle:
        ws["A2"].value = subtitle
        ws["A2"].font = f(italic=True, color="404040")
        ws["A2"].alignment = Alignment(vertical="center")
        ws.row_dimensions[2].height = 22


def widths(ws, mapping: dict[str, float]):
    for col, w in mapping.items():
        ws.column_dimensions[col].width = w


def page_setup(ws, landscape: bool = True):
    ws.page_setup.orientation = "landscape" if landscape else "portrait"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_options.horizontalCentered = True


def list_dv(options, *, warn: bool = False) -> DataValidation:
    dv = DataValidation(type="list", formula1='"' + ",".join(options) + '"', allow_blank=True)
    dv.showErrorMessage = True
    dv.errorStyle = "warning" if warn else "stop"
    dv.errorTitle = "Invalid entry"
    dv.error = "Please choose a value from the list."
    return dv


def date_dv() -> DataValidation:
    dv = DataValidation(type="date", operator="greaterThanOrEqual", formula1="36526", allow_blank=True)
    dv.errorStyle = "warning"
    dv.showErrorMessage = True
    dv.error = "Enter a valid date (yyyy-mm-dd)."
    return dv


def band_rules(ws, rng: str, first_cell: str, bands):
    """Colour cells whose text equals a band label."""
    for name, bg, fg in bands:
        ws.conditional_formatting.add(
            rng, FormulaRule(formula=[f'{first_cell}="{name}"'], fill=fill(bg),
                             font=Font(name=FONT, bold=True, color=fg), stopIfTrue=True))


# --------------------------------------------------------------------------- #
# 01_Methodology
# --------------------------------------------------------------------------- #
# Fixed cell addresses of the lookup tables (used by formulas elsewhere)
M_DATA = "'01_Methodology'!$A$10:$B$13"
M_CRIT = "'01_Methodology'!$D$10:$E$13"
M_ACCESS = "'01_Methodology'!$G$10:$H$13"
M_AI = "'01_Methodology'!$J$10:$K$11"
M_CADENCE = "'01_Methodology'!$A$22:$C$24"   # tier, cadence months, due-diligence depth
M_RESIDUAL = "'01_Methodology'!$A$30:$E$32"  # tier x score band matrix


def build_methodology(wb: Workbook):
    ws = wb.active
    ws.title = S_METH
    ws.sheet_properties.tabColor = NAVY
    ws.sheet_view.showGridLines = False
    title(ws, "Vendor Risk Assessment Template (TPRM)",
          "Tiering  |  Questionnaire  |  Residual rating  |  Contract clauses  |  ISO/IEC 27001 A.5.19-A.5.23  |  NIST CSF 2.0 GV.SC  |  SOC 2 CC9.2  |  ISO/IEC 42001 A.10",
          width_cols=11)
    widths(ws, {"A": 22, "B": 11, "C": 4, "D": 22, "E": 11, "F": 4, "G": 24, "H": 11, "I": 4, "J": 14, "K": 11, "L": 60})
    ws["A1"].comment = Comment(
        "OPEN SOURCE: released under the MIT License. Free to use, copy, modify and redistribute. "
        "Provided 'as is' without warranty. All sample vendors are fictional.", "Template", width=360, height=100)

    put(ws, "A3", "Version 1.0  -  Open source (MIT)  -  All sample vendors are fictional  -  Blue text = input, black on grey = formula",
        font=f(italic=True, color="595959"))

    # ---- Step 1: inherent risk model
    put(ws, "A5", "1. INHERENT RISK AND TIERING", font=f(bold=True, color="FFFFFF", size=11), bg=MID_BLUE)
    for col in "BCDEFGHIJKL":
        ws[f"{col}5"].fill = fill(MID_BLUE)
    put(ws, "A6", "Inherent score = Data classification x Business criticality x Access type x AI use    (range 1 to 128)",
        font=f(bold=True))
    put(ws, "A7", f"Tier 1 (critical) if score >= {TIER1_MIN}   -   Tier 2 (important) if score >= {TIER2_MIN}   -   Tier 3 (standard) otherwise. "
        "Scores are computed automatically in 02_Vendor_Inventory from the four drop-downs. Edit the factor values below to re-calibrate.",
        font=f(color="404040"))
    ws.merge_cells("A6:L6")
    ws.merge_cells("A7:L7")
    ws.row_dimensions[7].height = 30

    tables = [
        ("A", "Data classification", DATA_CLASS),
        ("D", "Business criticality", CRITICALITY),
        ("G", "Access to our systems / data", ACCESS),
        ("J", "AI processes our data?", AI_USE),
    ]
    for col, label, rows in tables:
        c2 = get_column_letter(ws[f"{col}1"].column + 1)
        header(ws, 9, [label, "Factor"], start_col=ws[f"{col}1"].column, height=30)
        for i, (name, val) in enumerate(rows):
            r = 10 + i
            put(ws, f"{col}{r}", name, align=Alignment(horizontal="left", vertical="center"), border=True)
            put(ws, f"{c2}{r}", val, font=f(bold=True, color=INPUT_BLUE),
                align=Alignment(horizontal="center", vertical="center"), border=True, fmt="0")
    put(ws, "L9", "How to read the factors", font=f(bold=True, color="FFFFFF"), bg=NAVY,
        align=Alignment(horizontal="center", vertical="center"), border=True)
    ws.row_dimensions[9].height = 30
    put(ws, "L10", "Data classification: the most sensitive class of information the vendor stores, processes or can see.", border=True)
    put(ws, "L11", "Business criticality: what happens to your operations if the vendor fails for a week (Critical = core process stops).", border=True)
    put(ws, "L12", "Access type: the vendor's technical reach into your environment. 'Privileged / integrated' covers admin rights, API integration with write access, or hosting your production systems.", border=True)
    put(ws, "L13", "AI use: 'Yes' when the vendor applies AI / machine learning (including third-party LLMs) to your data - this doubles the score so AI-enabled services are assessed earlier and deeper.", border=True)
    for r in (10, 11, 12, 13):
        ws.row_dimensions[r].height = 40

    # worked examples
    put(ws, "A15", "Examples:  Restricted (4) x Critical (4) x Privileged (4) x No AI (1) = 64 -> Tier 1   |   Confidential (3) x Medium (2) x Read-only (2) x AI (2) = 24 -> Tier 2   |   Internal (2) x Low (1) x None (1) x No (1) = 2 -> Tier 3",
        font=f(italic=True, color="404040"))
    ws.merge_cells("A15:L15")
    ws.row_dimensions[15].height = 30

    # ---- Step 2: due diligence depth and cadence
    put(ws, "A18", "2. DUE-DILIGENCE DEPTH AND REVIEW CADENCE PER TIER", font=f(bold=True, color="FFFFFF", size=11), bg=MID_BLUE)
    for col in "BCDEFGHIJKL":
        ws[f"{col}18"].fill = fill(MID_BLUE)
    put(ws, "A19", "The review cadence (months) drives the 'Next review' date in 04_Assessment_Summary. Change the blue values to match your policy.",
        font=f(color="404040"))
    ws.merge_cells("A19:L19")
    header(ws, 21, ["Tier", "Cadence (months)", "Due-diligence depth"], height=30)
    ws.merge_cells("C21:L21")
    depth = {
        "Tier 1": "Full questionnaire (all 60 questions) with evidence for every weight-3 question; independent assurance report (ISO/IEC 27001 certificate with scope, or SOC 2 Type II) reviewed; penetration test summary and DR test result requested; "
                  "architecture / data-flow walkthrough with the vendor; all 'Required' contract clauses in place before go-live; executive risk owner signs the residual rating.",
        "Tier 2": "Full questionnaire; evidence for weight-3 questions only; certificate or attestation reviewed when available; 'Required' clauses for Tier 2 in place; business owner signs the residual rating.",
        "Tier 3": "Short-form review: governance, access, data protection and incident domains only (or vendor's published security page); standard contract terms; business owner confirms no system access and no confidential data before onboarding.",
    }
    for i, (tier, bg, fg) in enumerate(TIERS):
        r = 22 + i
        put(ws, f"A{r}", tier, font=f(bold=True, color=fg), bg=bg, align=Alignment(horizontal="center", vertical="center"), border=True)
        put(ws, f"B{r}", CADENCE_MONTHS[tier], font=f(bold=True, color=INPUT_BLUE),
            align=Alignment(horizontal="center", vertical="center"), border=True, fmt="0")
        ws.merge_cells(f"C{r}:L{r}")
        put(ws, f"C{r}", depth[tier], border=True)
        ws.row_dimensions[r].height = 64

    # ---- Step 3: questionnaire scoring and residual rating
    put(ws, "A26", "3. QUESTIONNAIRE SCORING AND RESIDUAL RATING", font=f(bold=True, color="FFFFFF", size=11), bg=MID_BLUE)
    for col in "BCDEFGHIJKL":
        ws[f"{col}26"].fill = fill(MID_BLUE)
    put(ws, "A27", "Each answer earns points x weight: Yes = 1, Partial = 0.5, No = 0, N/A = excluded. Domain score = points obtained / points available. "
        "Score band: Strong >= 85 %, Adequate >= 70 %, Weak >= 50 %, Poor < 50 %. The residual rating combines the tier (inherent) with the score band (control strength):",
        font=f(color="404040"))
    ws.merge_cells("A27:L27")
    ws.row_dimensions[27].height = 30
    header(ws, 29, ["Tier \\ Score band", "Strong", "Adequate", "Weak", "Poor"], height=26)
    for i, (tier, bg, fg) in enumerate(TIERS):
        r = 30 + i
        put(ws, f"A{r}", tier, font=f(bold=True, color=fg), bg=bg, align=Alignment(horizontal="center", vertical="center"), border=True)
        for j, band in enumerate(["Strong", "Adequate", "Weak", "Poor"]):
            col = get_column_letter(2 + j)
            put(ws, f"{col}{r}", RESIDUAL[tier][band], font=f(bold=True, color=INPUT_BLUE),
                align=Alignment(horizontal="center", vertical="center"), border=True)
    band_rules(ws, "B30:E32", "B30", RATINGS)
    put(ws, "G29", "Rating", font=f(bold=True, color="FFFFFF"), bg=NAVY, align=Alignment(horizontal="center", vertical="center"), border=True)
    ws.merge_cells("H29:L29")
    put(ws, "H29", "Expected response", font=f(bold=True, color="FFFFFF"), bg=NAVY, align=Alignment(horizontal="center", vertical="center"), border=True)
    responses = {
        "Critical": "Do not onboard (or suspend expansion) until remediation is agreed with dates; executive sign-off required to continue; re-assess within 3 months.",
        "High": "Remediation plan with owner and dates before go-live or renewal; compensating controls on your side; re-assess within 6 months.",
        "Medium": "Track open findings in the summary; include fixes in the next renewal; review at the tier cadence.",
        "Low": "Accept; review at the tier cadence or on material change.",
    }
    for i, name in enumerate(RATING_ORDER):
        r = 30 + i
        bg, fg = next((b, c) for n, b, c in RATINGS if n == name)
        put(ws, f"G{r}", name, font=f(bold=True, color=fg), bg=bg, align=Alignment(horizontal="center", vertical="center"), border=True)
        ws.merge_cells(f"H{r}:L{r}")
        put(ws, f"H{r}", responses[name], border=True)
        ws.row_dimensions[r].height = 34
    put(ws, "A34", "Override: if a single critical finding (for example no MFA for privileged access, or a recent unresolved breach) justifies a harsher rating, use the 'Override rating' column in 04_Assessment_Summary and record the reason.",
        font=f(italic=True, color="404040"))
    ws.merge_cells("A34:L34")
    ws.row_dimensions[34].height = 30

    # ---- Step 4: process
    put(ws, "A36", "4. STEP-BY-STEP", font=f(bold=True, color="FFFFFF", size=11), bg=MID_BLUE)
    for col in "BCDEFGHIJKL":
        ws[f"{col}36"].fill = fill(MID_BLUE)
    steps = [
        ("Step 1 - Inventory", "Record every vendor with access to systems or data in 02_Vendor_Inventory. Pick the four risk factors from the drop-downs; the score and tier are computed."),
        ("Step 2 - Send", "Send questionnaire/vendor-questionnaire.md (or the CSV) to the vendor. Tier 3 vendors answer the short form only."),
        ("Step 3 - Assess", "Select the vendor at the top of 03_Questionnaire, enter the answers, read the evidence, note gaps. Domain and overall scores are computed."),
        ("Step 4 - Rate", "Copy the overall score into 04_Assessment_Summary (one row per vendor). The residual rating, next review date and overdue flag are computed. Use the override only with a written reason."),
        ("Step 5 - Contract", "In 05_Contract_Clauses_Checklist, select the vendor and mark each clause Y/N against the contract. Missing 'Required' clauses are counted."),
        ("Step 6 - Report", "06_Dashboard gives counts by tier and rating, overdue reviews and coverage, for management review and audit evidence."),
        ("Step 7 - Repeat", "Re-assess at the tier cadence, at renewal, after an incident, or when the service changes materially (new AI feature, new sub-processor, new data)."),
    ]
    for i, (label, text) in enumerate(steps):
        r = 37 + i
        put(ws, f"A{r}", label, font=f(bold=True))
        ws.merge_cells(f"B{r}:L{r}")
        put(ws, f"B{r}", text)
        ws.row_dimensions[r].height = 30

    # ---- Step 5: standards, conventions, notes
    put(ws, "A45", "5. STANDARDS ALIGNMENT (identifiers only - see docs/standards-mapping.md)", font=f(bold=True, color="FFFFFF", size=11), bg=MID_BLUE)
    for col in "BCDEFGHIJKL":
        ws[f"{col}45"].fill = fill(MID_BLUE)
    for i, (label, text) in enumerate([
        ("ISO/IEC 27001:2022", "Annex A.5.19 (supplier relationships), A.5.20 (addressing security in supplier agreements), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services), A.5.23 (cloud services)."),
        ("NIST CSF 2.0", "GV.SC-01 to GV.SC-10 (cybersecurity supply chain risk management), plus ID.RA and GV.RM for the tiering criteria."),
        ("SOC 2", "CC9.2 (vendor and business partner risk management) - and the trust-services criteria the vendor's own report covers."),
        ("ISO/IEC 42001:2023", "Annex A.10 (third-party and customer relationships) for AI-enabled vendors, together with A.5 (impact assessment) and A.7 (data for AI systems)."),
    ]):
        r = 46 + i
        put(ws, f"A{r}", label, font=f(bold=True))
        ws.merge_cells(f"B{r}:L{r}")
        put(ws, f"B{r}", text)
        ws.row_dimensions[r].height = 30

    put(ws, "A51", "6. CONVENTIONS AND NOTES", font=f(bold=True, color="FFFFFF", size=11), bg=MID_BLUE)
    for col in "BCDEFGHIJKL":
        ws[f"{col}51"].fill = fill(MID_BLUE)
    for i, (label, text) in enumerate([
        ("Blue text", "Input cells - type or pick from the drop-down."),
        ("Black on grey", "Formulas - do not overwrite."),
        ("Red date", "Next review date in the past and assessment not complete = overdue."),
        ("No personal data", "Use roles (e.g. 'Head of HR'), never names. Keep vendor evidence outside this file; record only where it is stored."),
        ("Disclaimer", "This template supports, but does not replace, legal review of contracts, professional judgement or a certification audit."),
    ]):
        r = 52 + i
        put(ws, f"A{r}", label, font=f(bold=True, color=INPUT_BLUE if label == "Blue text" else "000000"))
        ws.merge_cells(f"B{r}:L{r}")
        put(ws, f"B{r}", text)
        ws.row_dimensions[r].height = 20
    page_setup(ws)


# --------------------------------------------------------------------------- #
# 02_Vendor_Inventory
# --------------------------------------------------------------------------- #
INV_HEADERS = ["Vendor ID", "Vendor Name", "Service / What they do for us", "Category", "Business Owner (role)",
               "Data Classification", "Business Criticality", "Access Type", "AI Use?", "Inherent Score", "Inherent Tier",
               "Data Location", "Contract End", "Status", "Notes"]
INV_COL = {k: get_column_letter(i + 1) for i, k in enumerate(
    ["id", "name", "service", "cat", "owner", "data", "crit", "access", "ai", "score", "tier", "loc", "end", "status", "notes"])}


def build_inventory(wb: Workbook):
    ws = wb.create_sheet(S_INV)
    ws.sheet_properties.tabColor = "548235"
    title(ws, "Vendor Inventory", "One row per vendor with access to systems or data. Blue = input; score and tier are computed. Sample vendors are fictional.", width_cols=15)
    widths(ws, {"A": 10, "B": 26, "C": 40, "D": 26, "E": 22, "F": 14, "G": 13, "H": 20, "I": 9, "J": 10, "K": 10,
                "L": 16, "M": 12, "N": 13, "O": 50})
    header(ws, 4, INV_HEADERS, height=40)
    C = INV_COL
    formula_cols = {C["score"], C["tier"]}
    center = {C["id"], C["data"], C["crit"], C["access"], C["ai"], C["score"], C["tier"], C["end"], C["status"]}

    for r in range(INV_FIRST, INV_LAST + 1):
        idx = r - INV_FIRST
        sample = VENDORS[idx] if idx < len(VENDORS) else None
        values: dict[str, object] = {}
        if sample:
            keys = ["id", "name", "service", "cat", "owner", "data", "crit", "access", "ai", "loc", "end", "status", "notes"]
            values = {C[k]: v for k, v in zip(keys, sample)}
        values[C["score"]] = (
            f'=IF(OR({C["data"]}{r}="",{C["crit"]}{r}="",{C["access"]}{r}="",{C["ai"]}{r}=""),"",'
            f'IFERROR(VLOOKUP({C["data"]}{r},{M_DATA},2,FALSE)*VLOOKUP({C["crit"]}{r},{M_CRIT},2,FALSE)'
            f'*VLOOKUP({C["access"]}{r},{M_ACCESS},2,FALSE)*VLOOKUP({C["ai"]}{r},{M_AI},2,FALSE),"check lists"))'
        )
        values[C["tier"]] = (
            f'=IF({C["score"]}{r}="","",IF(ISNUMBER({C["score"]}{r}),IF({C["score"]}{r}>={TIER1_MIN},"Tier 1",'
            f'IF({C["score"]}{r}>={TIER2_MIN},"Tier 2","Tier 3")),""))'
        )
        for ci in range(1, len(INV_HEADERS) + 1):
            col = get_column_letter(ci)
            c = ws[f"{col}{r}"]
            if col in values:
                c.value = values[col]
            is_formula = col in formula_cols
            c.font = f(color="000000" if is_formula else INPUT_BLUE, bold=(is_formula or col == C["id"]))
            if is_formula:
                c.fill = fill(PALE)
            c.border = BORDER
            c.alignment = Alignment(vertical="top", wrap_text=True, horizontal="center" if col in center else "left")
        ws[f"{C['end']}{r}"].number_format = "yyyy-mm-dd"
        if sample:
            ws.row_dimensions[r].height = 44

    rng = lambda col: f"{col}{INV_FIRST}:{col}{INV_LAST}"
    for key, opts in (("cat", CATEGORIES), ("data", [n for n, _ in DATA_CLASS]), ("crit", [n for n, _ in CRITICALITY]),
                      ("access", [n for n, _ in ACCESS]), ("ai", [n for n, _ in AI_USE]), ("status", STATUS_INV)):
        dv = list_dv(opts)
        ws.add_data_validation(dv)
        dv.add(rng(C[key]))
    dv = date_dv()
    ws.add_data_validation(dv)
    dv.add(rng(C["end"]))

    band_rules(ws, rng(C["tier"]), f"{C['tier']}{INV_FIRST}", TIERS)
    # contract ending within 90 days -> amber
    ws.conditional_formatting.add(
        rng(C["end"]),
        FormulaRule(formula=[f'AND(ISNUMBER({C["end"]}{INV_FIRST}),{C["end"]}{INV_FIRST}-TODAY()<=90,{C["status"]}{INV_FIRST}="Active")'],
                    font=Font(name=FONT, bold=True, color="7F3200"), fill=fill("FCE4D6")))
    ws.freeze_panes = "C5"
    ws.auto_filter.ref = f"A4:{get_column_letter(len(INV_HEADERS))}{INV_LAST}"
    page_setup(ws)


# --------------------------------------------------------------------------- #
# 03_Questionnaire
# --------------------------------------------------------------------------- #
Q_FIRST = 22                      # first question row
Q_LAST = Q_FIRST + len(QUESTIONS) - 1
Q_VENDOR_CELL = "C3"              # selected vendor ID
Q_OVERALL_CELL = "C8"             # overall score (%)
Q_BAND_CELL = "C9"
DOM_FIRST = 8                     # domain table starts here (right-hand block, columns H..L)


def build_questionnaire(wb: Workbook):
    ws = wb.create_sheet(S_Q)
    ws.sheet_properties.tabColor = "C55A11"
    ws.sheet_view.showGridLines = False
    title(ws, "Security Questionnaire (one vendor per copy)",
          "Select the vendor, enter each answer from the drop-down, record the evidence reviewed. Scores update automatically. Yes = 1, Partial = 0.5, No = 0, N/A = excluded.",
          width_cols=12)
    widths(ws, {"A": 9, "B": 24, "C": 64, "D": 11, "E": 8, "F": 38, "G": 38, "H": 30, "I": 10, "J": 10, "K": 10, "L": 11})

    # ---- header block (left)
    put(ws, "B3", "Vendor ID", font=f(bold=True), bg=LIGHT_BLUE, border=True)
    put(ws, Q_VENDOR_CELL, SAMPLE_VENDOR, font=f(bold=True, color=INPUT_BLUE), border=True,
        align=Alignment(horizontal="left", vertical="center"))
    put(ws, "B4", "Vendor name", font=f(bold=True), bg=LIGHT_BLUE, border=True)
    put(ws, "C4", f'=IF({Q_VENDOR_CELL}="","",IFERROR(INDEX(\'{S_INV}\'!$B${INV_FIRST}:$B${INV_LAST},MATCH({Q_VENDOR_CELL},\'{S_INV}\'!$A${INV_FIRST}:$A${INV_LAST},0)),"ID not in inventory"))',
        bg=PALE, border=True, align=Alignment(horizontal="left", vertical="center"))
    put(ws, "B5", "Inherent tier", font=f(bold=True), bg=LIGHT_BLUE, border=True)
    put(ws, "C5", f'=IF({Q_VENDOR_CELL}="","",IFERROR(INDEX(\'{S_INV}\'!${INV_COL["tier"]}${INV_FIRST}:${INV_COL["tier"]}${INV_LAST},MATCH({Q_VENDOR_CELL},\'{S_INV}\'!$A${INV_FIRST}:$A${INV_LAST},0)),""))',
        bg=PALE, border=True, align=Alignment(horizontal="left", vertical="center"), font=f(bold=True))
    put(ws, "B6", "Assessment date", font=f(bold=True), bg=LIGHT_BLUE, border=True)
    put(ws, "C6", date(2026, 10, 12), font=f(color=INPUT_BLUE), border=True, fmt="yyyy-mm-dd",
        align=Alignment(horizontal="left", vertical="center"))
    put(ws, "B7", "Assessor (role)", font=f(bold=True), bg=LIGHT_BLUE, border=True)
    put(ws, "C7", "Security Analyst, GRC team", font=f(color=INPUT_BLUE), border=True, align=Alignment(horizontal="left", vertical="center"))

    # points: SUMPRODUCT over all questions
    ans = f"$D${Q_FIRST}:$D${Q_LAST}"
    wgt = f"$E${Q_FIRST}:$E${Q_LAST}"
    obtained = f'(SUMPRODUCT(({ans}="Yes")*{wgt})+0.5*SUMPRODUCT(({ans}="Partial")*{wgt}))'
    available = f'(SUMPRODUCT(({ans}="Yes")*{wgt})+SUMPRODUCT(({ans}="Partial")*{wgt})+SUMPRODUCT(({ans}="No")*{wgt}))'
    put(ws, "B8", "OVERALL SCORE", font=f(bold=True, color="FFFFFF"), bg=NAVY, border=True)
    put(ws, Q_OVERALL_CELL, f'=IF({available}=0,"",{obtained}/{available})', font=f(bold=True, size=14, color=NAVY), bg=LIGHT_BLUE,
        border=True, fmt="0.0%", align=Alignment(horizontal="left", vertical="center"))
    put(ws, "B9", "Score band", font=f(bold=True), bg=LIGHT_BLUE, border=True)
    put(ws, Q_BAND_CELL, f'=IF({Q_OVERALL_CELL}="","",IF({Q_OVERALL_CELL}>=0.85,"Strong",IF({Q_OVERALL_CELL}>=0.7,"Adequate",IF({Q_OVERALL_CELL}>=0.5,"Weak","Poor"))))',
        font=f(bold=True), bg=PALE, border=True, align=Alignment(horizontal="left", vertical="center"))
    put(ws, "B10", "Answered / total", font=f(bold=True), bg=LIGHT_BLUE, border=True)
    put(ws, "C10", f'=COUNTA({ans})&" / "&COUNTA($A${Q_FIRST}:$A${Q_LAST})&"   (N/A: "&COUNTIF({ans},"N/A")&")"',
        bg=PALE, border=True, align=Alignment(horizontal="left", vertical="center"))
    put(ws, "B11", "Weight-3 questions answered 'No'", font=f(bold=True), bg=LIGHT_BLUE, border=True)
    put(ws, "C11", f'=COUNTIFS({ans},"No",{wgt},3)', font=f(bold=True), bg=PALE, border=True, fmt="0",
        align=Alignment(horizontal="left", vertical="center"))
    put(ws, "B12", "Copy the overall score to 04_Assessment_Summary when the review is complete. Save one copy of this sheet per vendor, or keep the evidence folder reference in the Reviewer notes.",
        font=f(italic=True, color="595959"))
    ws.merge_cells("B12:G12")
    ws.row_dimensions[12].height = 30
    for r in range(3, 12):
        ws.row_dimensions[r].height = 20
    ws.row_dimensions[8].height = 26

    dv_vendor = DataValidation(type="list", formula1=f"='{S_INV}'!$A${INV_FIRST}:$A${INV_LAST}", allow_blank=True)
    dv_vendor.showErrorMessage = True
    dv_vendor.errorStyle = "warning"
    dv_vendor.error = "This ID is not in 02_Vendor_Inventory."
    ws.add_data_validation(dv_vendor)
    dv_vendor.add(Q_VENDOR_CELL)
    dv = date_dv()
    ws.add_data_validation(dv)
    dv.add("C6")

    # ---- domain scores (right block, H..L)
    put(ws, "H6", "DOMAIN SCORES", font=f(bold=True, color=NAVY, size=11))
    header(ws, 7, ["Domain", "Points obtained", "Points available", "Score", "Band"], start_col=8, height=30)
    dom_rng = f"$B${Q_FIRST}:$B${Q_LAST}"
    for i, (code, name) in enumerate(DOMAINS):
        r = DOM_FIRST + i
        put(ws, f"H{r}", name, border=True, align=Alignment(vertical="center"))
        put(ws, f"I{r}", f'=SUMPRODUCT(({dom_rng}=$H{r})*({ans}="Yes")*{wgt})+0.5*SUMPRODUCT(({dom_rng}=$H{r})*({ans}="Partial")*{wgt})',
            bg=PALE, border=True, fmt="0.0", align=Alignment(horizontal="center", vertical="center"))
        put(ws, f"J{r}", f'=SUMPRODUCT(({dom_rng}=$H{r})*(({ans}="Yes")+({ans}="Partial")+({ans}="No"))*{wgt})',
            bg=PALE, border=True, fmt="0", align=Alignment(horizontal="center", vertical="center"))
        put(ws, f"K{r}", f'=IF(J{r}=0,"",I{r}/J{r})', font=f(bold=True), bg=PALE, border=True, fmt="0%",
            align=Alignment(horizontal="center", vertical="center"))
        put(ws, f"L{r}", f'=IF(K{r}="","",IF(K{r}>=0.85,"Strong",IF(K{r}>=0.7,"Adequate",IF(K{r}>=0.5,"Weak","Poor"))))',
            font=f(bold=True), bg=PALE, border=True, align=Alignment(horizontal="center", vertical="center"))
        ws.row_dimensions[r].height = 18
    dom_last = DOM_FIRST + len(DOMAINS) - 1
    band_fills = {"Strong": ("C6E0B4", "1E4620"), "Adequate": ("FFE699", "7F6000"), "Weak": ("F4B183", "7F3200"), "Poor": ("C00000", "FFFFFF")}
    for band, (bg, fg) in band_fills.items():
        for rng_, first in ((f"L{DOM_FIRST}:L{dom_last}", f"L{DOM_FIRST}"), (f"{Q_BAND_CELL}:{Q_BAND_CELL}", Q_BAND_CELL)):
            ws.conditional_formatting.add(rng_, FormulaRule(formula=[f'{first}="{band}"'], fill=fill(bg),
                                                           font=Font(name=FONT, bold=True, color=fg), stopIfTrue=True))

    # ---- questions table
    header(ws, Q_FIRST - 1, ["ID", "Domain", "Question", "Answer", "Weight", "Evidence requested", "Vendor response / evidence reviewed", "Reviewer notes / gap"], height=34)
    ws.row_dimensions[Q_FIRST - 2].height = 8
    dom_name = dict(DOMAINS)
    for i, (qid, dcode, text, weight, evidence) in enumerate(QUESTIONS):
        r = Q_FIRST + i
        put(ws, f"A{r}", qid, font=f(bold=True), border=True, align=Alignment(horizontal="center", vertical="top"))
        put(ws, f"B{r}", dom_name[dcode], border=True)
        put(ws, f"C{r}", text, border=True)
        put(ws, f"D{r}", SAMPLE_ANSWERS.get(qid), font=f(bold=True, color=INPUT_BLUE), border=True,
            align=Alignment(horizontal="center", vertical="top"))
        put(ws, f"E{r}", weight, font=f(color=INPUT_BLUE), border=True, fmt="0", align=Alignment(horizontal="center", vertical="top"))
        put(ws, f"F{r}", evidence, border=True)
        put(ws, f"G{r}", None, font=f(color=INPUT_BLUE), border=True)
        put(ws, f"H{r}", SAMPLE_COMMENTS.get(qid), font=f(color=INPUT_BLUE), border=True)
        ws.row_dimensions[r].height = 46
        # domain separator shading on the ID/domain cells
        if i == 0 or QUESTIONS[i - 1][1] != dcode:
            ws[f"B{r}"].font = f(bold=True, color=NAVY)

    dv_ans = list_dv(ANSWERS)
    ws.add_data_validation(dv_ans)
    dv_ans.add(f"D{Q_FIRST}:D{Q_LAST}")
    dv_w = list_dv(["1", "2", "3"])
    dv_w.error = "Weight must be 1, 2 or 3."
    ws.add_data_validation(dv_w)
    dv_w.add(f"E{Q_FIRST}:E{Q_LAST}")

    arng = f"D{Q_FIRST}:D{Q_LAST}"
    ws.conditional_formatting.add(arng, FormulaRule(formula=[f'$D{Q_FIRST}="Yes"'], fill=fill("C6E0B4"), stopIfTrue=True))
    ws.conditional_formatting.add(arng, FormulaRule(formula=[f'$D{Q_FIRST}="Partial"'], fill=fill("FFE699"), stopIfTrue=True))
    ws.conditional_formatting.add(arng, FormulaRule(formula=[f'$D{Q_FIRST}="No"'], fill=fill("F4B183"), stopIfTrue=True))
    ws.conditional_formatting.add(arng, FormulaRule(formula=[f'$D{Q_FIRST}="N/A"'], fill=fill(PALE), stopIfTrue=True))
    # weight-3 'No' -> whole question row flagged red text on ID
    ws.conditional_formatting.add(f"A{Q_FIRST}:A{Q_LAST}",
                                  FormulaRule(formula=[f'AND($D{Q_FIRST}="No",$E{Q_FIRST}=3)'],
                                              font=Font(name=FONT, bold=True, color="FF0000")))
    ws.freeze_panes = f"D{Q_FIRST}"
    ws.auto_filter.ref = f"A{Q_FIRST - 1}:H{Q_LAST}"
    page_setup(ws)
    ws.print_title_rows = f"{Q_FIRST - 1}:{Q_FIRST - 1}"


# --------------------------------------------------------------------------- #
# 04_Assessment_Summary
# --------------------------------------------------------------------------- #
SUM_HEADERS = ["Vendor ID", "Vendor Name", "Inherent Tier", "Assessment Status", "Questionnaire Score (%)", "Score Band",
               "Computed Rating", "Override Rating", "Override Reason", "Final Residual Rating", "Open Findings",
               "Weight-3 'No' Answers", "Last Assessment", "Next Review", "Overdue?", "Risk Owner (role)", "Evidence Location / Notes"]
SUM_COL = {k: get_column_letter(i + 1) for i, k in enumerate(
    ["id", "name", "tier", "status", "score", "band", "computed", "override", "reason", "final", "findings", "w3no",
     "last", "next", "overdue", "owner", "notes"])}

# (id, status, score, override, reason, findings, w3no, last, owner, notes)
SUM_SAMPLES = [
    ("VND-001", "Complete", 0.91, None, None, 1, 0, date(2026, 2, 10), "Head of Infrastructure", "SOC 2 Type II reviewed (period ending 2025-12). Finding: exit plan not documented."),
    ("VND-002", "Complete", None, None, None, 5, 0, date(2026, 10, 12), "Head of HR", "Worked example - score pulled live from 03_Questionnaire. Evidence folder: TPRM/VND-002/2026."),
    ("VND-003", "Complete", 0.64, "High", "Downgraded from Critical: the ENC-01 gap (unencrypted EDI link) is compensated by our own outbound encryption gateway; executive sign-off recorded.", 4, 1, date(2025, 8, 20), "Head of Supply Chain", "Overdue: Tier 1 cadence is 12 months. Re-assessment to be combined with contract renewal."),
    ("VND-004", "Complete", 0.72, None, None, 3, 1, date(2026, 5, 5), "Head of Data & Analytics", "AI-02 answered 'No': vendor trains on customer data by default. Opt-out letter requested."),
    ("VND-005", "In review", 0.78, None, None, 2, 0, date(2026, 9, 28), "IT Operations Manager", "Awaiting penetration test summary and PAM access review export."),
    ("VND-006", "Complete", 0.80, None, None, 0, 0, date(2026, 3, 1), "Marketing Manager", "Short-form review: no system access, public data only."),
]


def build_summary(wb: Workbook):
    ws = wb.create_sheet(S_SUM)
    ws.sheet_properties.tabColor = "7030A0"
    title(ws, "Assessment Summary", "One row per vendor assessed. Blue = input; grey = formula. Rating, next review and overdue flag are computed. Row highlighted in yellow = vendor currently loaded in 03_Questionnaire.", width_cols=17)
    widths(ws, {"A": 10, "B": 24, "C": 10, "D": 16, "E": 13, "F": 11, "G": 11, "H": 11, "I": 30, "J": 12, "K": 9, "L": 10,
                "M": 12, "N": 12, "O": 9, "P": 22, "Q": 44})
    header(ws, 5, SUM_HEADERS, height=46)
    put(ws, "A3", f"Score: type the overall score from 03_Questionnaire (as a percentage). For the vendor selected in 03_Questionnaire the score is pulled automatically when the cell is left blank.",
        font=f(italic=True, color="595959"))
    ws.merge_cells("A3:Q3")
    C = SUM_COL
    formula_cols = {C["name"], C["tier"], C["band"], C["computed"], C["final"], C["next"], C["overdue"]}
    center = {C["id"], C["tier"], C["status"], C["score"], C["band"], C["computed"], C["override"], C["final"],
              C["findings"], C["w3no"], C["last"], C["next"], C["overdue"]}
    inv_id = f"'{S_INV}'!$A${INV_FIRST}:$A${INV_LAST}"
    inv_name = f"'{S_INV}'!$B${INV_FIRST}:$B${INV_LAST}"
    inv_tier = f"'{S_INV}'!${INV_COL['tier']}${INV_FIRST}:${INV_COL['tier']}${INV_LAST}"
    q_vendor = f"'{S_Q}'!${Q_VENDOR_CELL[0]}${Q_VENDOR_CELL[1:]}"
    q_score = f"'{S_Q}'!${Q_OVERALL_CELL[0]}${Q_OVERALL_CELL[1:]}"
    q_w3 = f"'{S_Q}'!$C$11"

    for r in range(SUM_FIRST, SUM_LAST + 1):
        idx = r - SUM_FIRST
        sample = SUM_SAMPLES[idx] if idx < len(SUM_SAMPLES) else None
        values: dict[str, object] = {}
        if sample:
            keys = ["id", "status", "score", "override", "reason", "findings", "w3no", "last", "owner", "notes"]
            values = {C[k]: v for k, v in zip(keys, sample) if v is not None}
        id_ = f"{C['id']}{r}"
        values[C["name"]] = f'=IF({id_}="","",IFERROR(INDEX({inv_name},MATCH({id_},{inv_id},0)),"ID not in inventory"))'
        values[C["tier"]] = f'=IF({id_}="","",IFERROR(INDEX({inv_tier},MATCH({id_},{inv_id},0)),""))'
        # effective score: typed value, or live from the questionnaire for the loaded vendor
        eff = f'IF(ISNUMBER({C["score"]}{r}),{C["score"]}{r},IF(AND({id_}<>"",{id_}={q_vendor},ISNUMBER({q_score})),{q_score},""))'
        values[C["band"]] = f'=IF({eff}="","",IF({eff}>=0.85,"Strong",IF({eff}>=0.7,"Adequate",IF({eff}>=0.5,"Weak","Poor"))))'
        values[C["computed"]] = (
            f'=IF(OR({C["tier"]}{r}="",{C["band"]}{r}=""),"",IFERROR(INDEX({M_RESIDUAL},MATCH({C["tier"]}{r},\'01_Methodology\'!$A$30:$A$32,0),'
            f'MATCH({C["band"]}{r},\'01_Methodology\'!$A$29:$E$29,0)),""))'
        )
        values[C["final"]] = f'=IF({C["override"]}{r}<>"",{C["override"]}{r},{C["computed"]}{r})'
        values[C["next"]] = (
            f'=IF(OR({C["last"]}{r}="",{C["tier"]}{r}=""),"",IFERROR(EDATE({C["last"]}{r},VLOOKUP({C["tier"]}{r},{M_CADENCE},2,FALSE)),""))'
        )
        values[C["overdue"]] = (
            f'=IF({C["next"]}{r}="","",IF(AND(ISNUMBER({C["next"]}{r}),{C["next"]}{r}<TODAY()),"OVERDUE",'
            f'IF(AND(ISNUMBER({C["next"]}{r}),{C["next"]}{r}-TODAY()<=60,{C["next"]}{r}-TODAY()>=0),"Due soon","OK")))'
        )
        if sample and sample[0] == SAMPLE_VENDOR:
            # worked example: w3no is pulled live from the questionnaire
            values[C["w3no"]] = f'=IF({id_}={q_vendor},{q_w3},"")'
        for ci in range(1, len(SUM_HEADERS) + 1):
            col = get_column_letter(ci)
            c = ws[f"{col}{r}"]
            if col in values:
                c.value = values[col]
            is_formula = col in formula_cols
            c.font = f(color="000000" if is_formula else INPUT_BLUE, bold=(col in {C["id"], C["final"], C["tier"]}))
            if is_formula:
                c.fill = fill(PALE)
            c.border = BORDER
            c.alignment = Alignment(vertical="top", wrap_text=True, horizontal="center" if col in center else "left")
        ws[f"{C['score']}{r}"].number_format = "0%"
        ws[f"{C['last']}{r}"].number_format = "yyyy-mm-dd"
        ws[f"{C['next']}{r}"].number_format = "yyyy-mm-dd"
        ws[f"{C['findings']}{r}"].number_format = "0"
        ws[f"{C['w3no']}{r}"].number_format = "0"
        if sample:
            ws.row_dimensions[r].height = 46

    first, last = SUM_FIRST, SUM_LAST
    rng = lambda col: f"{col}{first}:{col}{last}"
    dv_vendor = DataValidation(type="list", formula1=f"='{S_INV}'!$A${INV_FIRST}:$A${INV_LAST}", allow_blank=True)
    dv_vendor.showErrorMessage = True
    dv_vendor.errorStyle = "warning"
    dv_vendor.error = "This ID is not in 02_Vendor_Inventory. Add the vendor there first."
    ws.add_data_validation(dv_vendor)
    dv_vendor.add(rng(C["id"]))
    for key, opts in (("status", STATUS_ASSESS), ("override", RATING_ORDER)):
        dv = list_dv(opts)
        ws.add_data_validation(dv)
        dv.add(rng(C[key]))
    dv_pct = DataValidation(type="decimal", operator="between", formula1="0", formula2="1", allow_blank=True)
    dv_pct.showErrorMessage = True
    dv_pct.errorStyle = "stop"
    dv_pct.error = "Enter the score as a percentage between 0 % and 100 %."
    ws.add_data_validation(dv_pct)
    dv_pct.add(rng(C["score"]))
    dv = date_dv()
    ws.add_data_validation(dv)
    dv.add(rng(C["last"]))

    for key in ("computed", "override", "final"):
        band_rules(ws, rng(C[key]), f"{C[key]}{first}", RATINGS)
    band_rules(ws, rng(C["tier"]), f"{C['tier']}{first}", TIERS)
    ws.conditional_formatting.add(rng(C["overdue"]), FormulaRule(formula=[f'{C["overdue"]}{first}="OVERDUE"'],
                                                                 font=Font(name=FONT, bold=True, color="FFFFFF"), fill=fill("C00000"), stopIfTrue=True))
    ws.conditional_formatting.add(rng(C["overdue"]), FormulaRule(formula=[f'{C["overdue"]}{first}="Due soon"'],
                                                                 font=Font(name=FONT, bold=True, color="7F3200"), fill=fill("FFE699"), stopIfTrue=True))
    ws.conditional_formatting.add(rng(C["next"]), FormulaRule(formula=[f'{C["overdue"]}{first}="OVERDUE"'],
                                                              font=Font(name=FONT, bold=True, color="FF0000")))
    # override without reason -> flag
    ws.conditional_formatting.add(rng(C["reason"]), FormulaRule(formula=[f'AND({C["override"]}{first}<>"",{C["reason"]}{first}="")'],
                                                                fill=fill("FFD9D9")))
    # vendor loaded in the questionnaire -> highlight row
    ws.conditional_formatting.add(f"A{first}:{get_column_letter(len(SUM_HEADERS))}{last}",
                                  FormulaRule(formula=[f'AND($A{first}<>"",$A{first}={q_vendor})'], fill=fill(HIGHLIGHT)))
    ws.freeze_panes = "C6"
    ws.auto_filter.ref = f"A5:{get_column_letter(len(SUM_HEADERS))}{last}"
    page_setup(ws)
    ws.print_title_rows = "5:5"


# --------------------------------------------------------------------------- #
# 05_Contract_Clauses_Checklist
# --------------------------------------------------------------------------- #
CL_FIRST = 9
CL_LAST = CL_FIRST + len(CLAUSES) - 1
CL_VENDOR_CELL = "B3"


def build_clauses(wb: Workbook):
    ws = wb.create_sheet(S_CLAUSE)
    ws.sheet_properties.tabColor = "595959"
    ws.sheet_view.showGridLines = False
    title(ws, "Contract Clauses Checklist", "Select the vendor; the 'Required for this vendor' column follows its tier. Mark Y/N against the signed contract. Missing required clauses are counted.", width_cols=10)
    widths(ws, {"A": 8, "B": 52, "C": 44, "D": 12, "E": 12, "F": 12, "G": 15, "H": 10, "I": 18, "J": 40})

    put(ws, "A3", "Vendor ID", font=f(bold=True), bg=LIGHT_BLUE, border=True)
    put(ws, CL_VENDOR_CELL, "VND-003", font=f(bold=True, color=INPUT_BLUE), border=True, align=Alignment(horizontal="left", vertical="center"))
    put(ws, "A4", "Vendor", font=f(bold=True), bg=LIGHT_BLUE, border=True)
    put(ws, "B4", f'=IF({CL_VENDOR_CELL}="","",IFERROR(INDEX(\'{S_INV}\'!$B${INV_FIRST}:$B${INV_LAST},MATCH({CL_VENDOR_CELL},\'{S_INV}\'!$A${INV_FIRST}:$A${INV_LAST},0)),"ID not in inventory"))',
        bg=PALE, border=True, align=Alignment(horizontal="left", vertical="center"))
    put(ws, "A5", "Tier", font=f(bold=True), bg=LIGHT_BLUE, border=True)
    put(ws, "B5", f'=IF({CL_VENDOR_CELL}="","",IFERROR(INDEX(\'{S_INV}\'!${INV_COL["tier"]}${INV_FIRST}:${INV_COL["tier"]}${INV_LAST},MATCH({CL_VENDOR_CELL},\'{S_INV}\'!$A${INV_FIRST}:$A${INV_LAST},0)),""))',
        font=f(bold=True), bg=PALE, border=True, align=Alignment(horizontal="left", vertical="center"))
    put(ws, "A6", "Required clauses missing", font=f(bold=True), bg=LIGHT_BLUE, border=True)
    put(ws, "B6", f'=COUNTIFS($G${CL_FIRST}:$G${CL_LAST},"Required",$H${CL_FIRST}:$H${CL_LAST},"N")&" missing, "&COUNTIFS($G${CL_FIRST}:$G${CL_LAST},"Required",$H${CL_FIRST}:$H${CL_LAST},"")&" not yet checked, of "&COUNTIF($G${CL_FIRST}:$G${CL_LAST},"Required")&" required"',
        font=f(bold=True), bg=PALE, border=True, align=Alignment(horizontal="left", vertical="center"))
    for r in (3, 4, 5, 6):
        ws.row_dimensions[r].height = 20
    band_rules(ws, "B5:B5", "B5", TIERS)
    ws.conditional_formatting.add("B6:B6", FormulaRule(formula=[f'COUNTIFS($G${CL_FIRST}:$G${CL_LAST},"Required",$H${CL_FIRST}:$H${CL_LAST},"N")>0'],
                                                       font=Font(name=FONT, bold=True, color="FF0000")))
    dv_vendor = DataValidation(type="list", formula1=f"='{S_INV}'!$A${INV_FIRST}:$A${INV_LAST}", allow_blank=True)
    dv_vendor.showErrorMessage = True
    dv_vendor.errorStyle = "warning"
    ws.add_data_validation(dv_vendor)
    dv_vendor.add(CL_VENDOR_CELL)

    header(ws, CL_FIRST - 1, ["ID", "Clause", "Why it matters", "Tier 1", "Tier 2", "Tier 3", "Required for this vendor", "In contract? (Y/N)", "Contract reference", "Notes / negotiation status"], height=36)
    sample_yn = {"CL-01": "Y", "CL-02": "Y", "CL-03": "Y", "CL-04": "N", "CL-05": "N", "CL-06": "Y", "CL-07": "N", "CL-08": "Y",
                 "CL-09": "Y", "CL-10": "N", "CL-11": "Y", "CL-12": "N", "CL-13": "Y", "CL-14": "Y", "CL-15": "Y", "CL-16": "N", "CL-17": "N", "CL-18": "N"}
    sample_notes = {"CL-04": "Add to renewal: UK sub-contractor used for returns.", "CL-05": "Current contract says 'without undue delay' - replace with 24 h.",
                    "CL-07": "Request sub-processor list in the renewal.", "CL-10": "Vendor to provide DR test summary.", "CL-18": "Not applicable today; include for future AI routing features."}
    for i, (cid, clause, why, t1, t2, t3) in enumerate(CLAUSES):
        r = CL_FIRST + i
        put(ws, f"A{r}", cid, font=f(bold=True), border=True, align=Alignment(horizontal="center", vertical="top"))
        put(ws, f"B{r}", clause, border=True)
        put(ws, f"C{r}", why, border=True)
        for col, lvl in zip("DEF", (t1, t2, t3)):
            put(ws, f"{col}{r}", CLAUSE_LEVELS[lvl], font=f(color=INPUT_BLUE), border=True, align=Alignment(horizontal="center", vertical="top"))
        put(ws, f"G{r}", f'=IF($B$5="","",IFERROR(INDEX($D{r}:$F{r},1,MATCH($B$5,$D${CL_FIRST - 1}:$F${CL_FIRST - 1},0)),""))',
            font=f(bold=True), bg=PALE, border=True, align=Alignment(horizontal="center", vertical="top"))
        put(ws, f"H{r}", sample_yn.get(cid), font=f(bold=True, color=INPUT_BLUE), border=True, align=Alignment(horizontal="center", vertical="top"))
        put(ws, f"I{r}", None, font=f(color=INPUT_BLUE), border=True)
        put(ws, f"J{r}", sample_notes.get(cid), font=f(color=INPUT_BLUE), border=True)
        ws.row_dimensions[r].height = 34
    dv_lvl = list_dv(list(CLAUSE_LEVELS.values()))
    ws.add_data_validation(dv_lvl)
    dv_lvl.add(f"D{CL_FIRST}:F{CL_LAST}")
    dv_yn = list_dv(YN)
    ws.add_data_validation(dv_yn)
    dv_yn.add(f"H{CL_FIRST}:H{CL_LAST}")
    # required & N -> red ; required & blank -> amber ; Y -> green
    ws.conditional_formatting.add(f"H{CL_FIRST}:H{CL_LAST}", FormulaRule(formula=[f'AND($G{CL_FIRST}="Required",$H{CL_FIRST}="N")'],
                                                                         fill=fill("C00000"), font=Font(name=FONT, bold=True, color="FFFFFF"), stopIfTrue=True))
    ws.conditional_formatting.add(f"H{CL_FIRST}:H{CL_LAST}", FormulaRule(formula=[f'AND($G{CL_FIRST}="Required",$H{CL_FIRST}="")'],
                                                                         fill=fill("FFE699"), stopIfTrue=True))
    ws.conditional_formatting.add(f"H{CL_FIRST}:H{CL_LAST}", FormulaRule(formula=[f'$H{CL_FIRST}="Y"'], fill=fill("C6E0B4"), stopIfTrue=True))
    ws.conditional_formatting.add(f"G{CL_FIRST}:G{CL_LAST}", FormulaRule(formula=[f'$G{CL_FIRST}="Required"'], font=Font(name=FONT, bold=True, color="C00000")))
    ws.freeze_panes = f"C{CL_FIRST}"
    page_setup(ws)
    ws.print_title_rows = f"{CL_FIRST - 1}:{CL_FIRST - 1}"


# --------------------------------------------------------------------------- #
# 06_Dashboard
# --------------------------------------------------------------------------- #
def build_dashboard(wb: Workbook):
    ws = wb.create_sheet(S_DASH)
    ws.sheet_properties.tabColor = "C00000"
    ws.sheet_view.showGridLines = False
    title(ws, "TPRM Dashboard", f"Figures update automatically from {S_INV} and {S_SUM}.", width_cols=14)
    widths(ws, {"A": 26, "B": 14, "C": 14, "D": 14, "E": 14, "F": 4, "G": 14, "H": 14, "I": 14, "J": 14, "K": 14, "L": 14, "M": 4, "N": 4})
    I = INV_COL
    S = SUM_COL
    inv = lambda k: f"'{S_INV}'!${I[k]}${INV_FIRST}:${I[k]}${INV_LAST}"
    summ = lambda k: f"'{S_SUM}'!${S[k]}${SUM_FIRST}:${S[k]}${SUM_LAST}"

    kpis = [
        ("Vendors in inventory", f"=COUNTA({inv('id')})", "0"),
        ("Tier 1 vendors", f'=COUNTIF({inv("tier")},"Tier 1")', "0"),
        ("Vendors assessed (rated)", f'=COUNTIF({summ("final")},"?*")', "0"),
        ("Critical / High residual", f'=COUNTIF({summ("final")},"Critical")+COUNTIF({summ("final")},"High")', "0"),
        ("Reviews overdue", f'=COUNTIF({summ("overdue")},"OVERDUE")', "0"),
        ("Tier 1 coverage", f'=IF(COUNTIF({inv("tier")},"Tier 1")=0,"–",COUNTIFS({summ("tier")},"Tier 1",{summ("overdue")},"<>OVERDUE",{summ("final")},"?*")/COUNTIF({inv("tier")},"Tier 1"))', "0%"),
    ]
    positions = [("A", "A"), ("B", "C"), ("D", "E"), ("G", "H"), ("I", "J"), ("K", "L")]
    for (label, formula, fmt), (c1, c2) in zip(kpis, positions):
        if c1 != c2:
            ws.merge_cells(f"{c1}4:{c2}4")
            ws.merge_cells(f"{c1}5:{c2}5")
        put(ws, f"{c1}4", label, font=f(bold=True, color="FFFFFF"), bg=MID_BLUE, align=Alignment(horizontal="center", vertical="center", wrap_text=True))
        put(ws, f"{c1}5", formula, font=f(bold=True, size=18, color=NAVY), bg=LIGHT_BLUE, align=Alignment(horizontal="center", vertical="center"), fmt=fmt)
        for cc in {c1, c2}:
            ws[f"{cc}4"].fill = fill(MID_BLUE)
            ws[f"{cc}5"].fill = fill(LIGHT_BLUE)
    ws.row_dimensions[4].height = 30
    ws.row_dimensions[5].height = 40
    ws.conditional_formatting.add("G5:H5", FormulaRule(formula=["G5>0"], font=Font(name=FONT, bold=True, size=18, color="C00000")))
    ws.conditional_formatting.add("I5:J5", FormulaRule(formula=["I5>0"], font=Font(name=FONT, bold=True, size=18, color="C00000")))

    # ---- by tier
    put(ws, "A7", "VENDORS BY INHERENT TIER", font=f(bold=True, color=NAVY, size=11))
    header(ws, 8, ["Tier", "In inventory", "Assessed", "Overdue", "Cadence (months)"], height=28)
    for i, (tier, bg, fg) in enumerate(TIERS):
        r = 9 + i
        put(ws, f"A{r}", tier, font=f(bold=True, color=fg), bg=bg, align=Alignment(horizontal="center", vertical="center"), border=True)
        put(ws, f"B{r}", f'=COUNTIF({inv("tier")},$A{r})', font=f(bold=True), align=Alignment(horizontal="center", vertical="center"), border=True)
        put(ws, f"C{r}", f'=COUNTIFS({summ("tier")},$A{r},{summ("final")},"?*")', font=f(bold=True), align=Alignment(horizontal="center", vertical="center"), border=True)
        put(ws, f"D{r}", f'=COUNTIFS({summ("tier")},$A{r},{summ("overdue")},"OVERDUE")', font=f(bold=True), align=Alignment(horizontal="center", vertical="center"), border=True)
        put(ws, f"E{r}", f'=VLOOKUP($A{r},{M_CADENCE},2,FALSE)', align=Alignment(horizontal="center", vertical="center"), border=True, fmt="0")
        ws.row_dimensions[r].height = 22
    put(ws, "A12", "Total", font=f(bold=True), bg=PALE, align=Alignment(horizontal="center", vertical="center"), border=True)
    for col in "BCD":
        put(ws, f"{col}12", f"=SUM({col}9:{col}11)", font=f(bold=True), bg=PALE, align=Alignment(horizontal="center", vertical="center"), border=True)
    put(ws, "E12", "", bg=PALE, border=True)
    ws.conditional_formatting.add("D9:D11", FormulaRule(formula=["D9>0"], font=Font(name=FONT, bold=True, color="C00000")))

    # ---- by residual rating
    put(ws, "A14", "VENDORS BY FINAL RESIDUAL RATING", font=f(bold=True, color=NAVY, size=11))
    header(ws, 15, ["Rating", "Vendors", "of which Tier 1", "Share"], height=28)
    for i, name in enumerate(RATING_ORDER):
        r = 16 + i
        bg, fg = next((b, c) for n, b, c in RATINGS if n == name)
        put(ws, f"A{r}", name, font=f(bold=True, color=fg), bg=bg, align=Alignment(horizontal="center", vertical="center"), border=True)
        put(ws, f"B{r}", f'=COUNTIF({summ("final")},$A{r})', font=f(bold=True), align=Alignment(horizontal="center", vertical="center"), border=True)
        put(ws, f"C{r}", f'=COUNTIFS({summ("final")},$A{r},{summ("tier")},"Tier 1")', font=f(bold=True), align=Alignment(horizontal="center", vertical="center"), border=True)
        put(ws, f"D{r}", f'=IF($B$20=0,"–",B{r}/$B$20)', align=Alignment(horizontal="center", vertical="center"), border=True, fmt="0%")
        ws.row_dimensions[r].height = 22
    put(ws, "A20", "Total rated", font=f(bold=True), bg=PALE, align=Alignment(horizontal="center", vertical="center"), border=True)
    put(ws, "B20", "=SUM(B16:B19)", font=f(bold=True), bg=PALE, align=Alignment(horizontal="center", vertical="center"), border=True)
    put(ws, "C20", "=SUM(C16:C19)", font=f(bold=True), bg=PALE, align=Alignment(horizontal="center", vertical="center"), border=True)
    put(ws, "D20", "", bg=PALE, border=True)

    # ---- by assessment status
    put(ws, "A22", "BY ASSESSMENT STATUS", font=f(bold=True, color=NAVY, size=11))
    header(ws, 23, ["Status", "Count"], height=24)
    for i, s in enumerate(STATUS_ASSESS):
        r = 24 + i
        put(ws, f"A{r}", s, align=Alignment(horizontal="left", vertical="center"), border=True)
        put(ws, f"B{r}", f'=COUNTIF({summ("status")},$A{r})', font=f(bold=True), align=Alignment(horizontal="center", vertical="center"), border=True)
    put(ws, "A29", "Not in summary yet", align=Alignment(horizontal="left", vertical="center"), border=True)
    put(ws, "B29", f'=COUNTA({inv("id")})-COUNTIF({summ("id")},"?*")', font=f(bold=True), align=Alignment(horizontal="center", vertical="center"), border=True)

    # ---- charts
    chart = BarChart()
    chart.type = "col"
    chart.grouping = "clustered"
    chart.title = "Vendors by final residual rating"
    chart.y_axis.title = "Vendors"
    chart.y_axis.majorGridlines = None
    data = Reference(ws, min_col=2, max_col=3, min_row=15, max_row=19)
    cats = Reference(ws, min_col=1, min_row=16, max_row=19)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.height = 8
    chart.width = 16
    chart.series[0].graphicalProperties.solidFill = "2F5597"
    chart.series[1].graphicalProperties.solidFill = "C00000"
    ws.add_chart(chart, "G7")

    chart2 = BarChart()
    chart2.type = "bar"
    chart2.grouping = "clustered"
    chart2.title = "Vendors by tier: inventory vs assessed"
    chart2.y_axis.majorGridlines = None
    data2 = Reference(ws, min_col=2, max_col=3, min_row=8, max_row=11)
    cats2 = Reference(ws, min_col=1, min_row=9, max_row=11)
    chart2.add_data(data2, titles_from_data=True)
    chart2.set_categories(cats2)
    chart2.height = 7
    chart2.width = 16
    chart2.series[0].graphicalProperties.solidFill = "8EA9DB"
    chart2.series[1].graphicalProperties.solidFill = "548235"
    ws.add_chart(chart2, "G24")

    # ---- guidance
    put(ws, "A31", "HOW TO USE THESE NUMBERS", font=f(bold=True, color=NAVY, size=11))
    tips = [
        "1. Tier 1 coverage below 100 % means a critical dependency has no current assessment - schedule it before anything else.",
        "2. Every Critical or High residual rating needs a remediation plan with an owner and a date, tracked in the summary notes.",
        "3. Overdue reviews are audit findings waiting to happen (ISO 27001 A.5.22, NIST CSF GV.SC-07): clear them or document the deferral.",
        "4. Vendors 'not in summary yet' have a tier but no assessment - Tier 3 can use the short form; Tier 1 and 2 cannot be skipped.",
        "5. Re-run the tiering when a vendor adds AI features, new sub-processors or new data: the inherent score may change tier.",
    ]
    for i, t in enumerate(tips):
        r = 32 + i
        ws.merge_cells(f"A{r}:L{r}")
        put(ws, f"A{r}", t, align=Alignment(vertical="center", wrap_text=True))
        ws.row_dimensions[r].height = 20
    page_setup(ws)


# --------------------------------------------------------------------------- #
# Questionnaire exports (same questions, sendable formats)
# --------------------------------------------------------------------------- #
def write_csv(path: Path):
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["id", "domain", "question", "weight", "evidence_requested", "answer", "vendor_comment"])
        dom_name = dict(DOMAINS)
        for qid, dcode, text, weight, evidence in QUESTIONS:
            w.writerow([qid, dom_name[dcode], text, weight, evidence, "", ""])
    print(f"Wrote {path}")


def write_markdown(path: Path):
    lines: list[str] = [
        "# Vendor security questionnaire",
        "",
        "Please answer every question with **Yes**, **Partial**, **No** or **N/A** and attach or reference the evidence requested.",
        "Where you answer *Partial* or *No*, describe the compensating control or the remediation date in the comment column.",
        "Weight shows how much the question counts in our scoring (3 = critical control, 2 = important, 1 = good practice).",
        "",
        "| Field | Your answer |",
        "|-------|-------------|",
        "| Vendor name | |",
        "| Service in scope | |",
        "| Completed by (role) | |",
        "| Date | |",
        "| Current certifications / attestations (ISO/IEC 27001, SOC 2, other) | |",
        "",
        "Answering tips: *N/A* is accepted only when the control cannot apply (for example no AI features, no sub-processors). "
        "Our reviewer may ask for a short call to walk through the evidence. Evidence is handled under NDA and deleted after the review.",
        "",
    ]
    dom_name = dict(DOMAINS)
    for code, name in DOMAINS:
        lines += [f"## {name}", "", "| ID | Question | Weight | Evidence requested | Answer | Comment |", "|----|----------|:------:|--------------------|--------|---------|"]
        for qid, dcode, text, weight, evidence in QUESTIONS:
            if dcode == code:
                lines.append(f"| {qid} | {text} | {weight} | {evidence} | | |")
        lines.append("")
    lines += [
        "## Declaration",
        "",
        "| | |",
        "|--|--|",
        "| I confirm the answers above are accurate to the best of my knowledge and that material changes will be notified. | |",
        "| Name / role | |",
        "| Date | |",
        "",
        "*This questionnaire is part of the open-source Vendor Risk Assessment Template (MIT licence). The scoring workbook that consumes these answers is `Vendor-Risk-Assessment-Template.xlsx`.*",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"Wrote {path}")


# --------------------------------------------------------------------------- #
def main(out: Path):
    wb = Workbook()
    build_methodology(wb)
    build_inventory(wb)
    build_questionnaire(wb)
    build_summary(wb)
    build_clauses(wb)
    build_dashboard(wb)
    wb.properties.title = "Vendor Risk Assessment Template"
    wb.properties.subject = "Third-party risk management: tiering, questionnaire, residual rating, contract clauses"
    wb.properties.creator = "Open-source contributors"
    wb.properties.description = "MIT-licensed template. All sample vendors are fictional."
    wb.calculation.fullCalcOnLoad = True
    wb.active = 0
    wb.save(out)
    print(f"Wrote {out}")
    qdir = out.parent / "questionnaire"
    qdir.mkdir(exist_ok=True)
    write_csv(qdir / "vendor-questionnaire.csv")
    write_markdown(qdir / "vendor-questionnaire.md")


if __name__ == "__main__":
    default = Path(__file__).resolve().parent.parent / "Vendor-Risk-Assessment-Template.xlsx"
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else default)
