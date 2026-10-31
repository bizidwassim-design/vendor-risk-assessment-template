# Vendor security questionnaire

Please answer every question with **Yes**, **Partial**, **No** or **N/A** and attach or reference the evidence requested.
Where you answer *Partial* or *No*, describe the compensating control or the remediation date in the comment column.
Weight shows how much the question counts in our scoring (3 = critical control, 2 = important, 1 = good practice).

| Field | Your answer |
|-------|-------------|
| Vendor name | |
| Service in scope | |
| Completed by (role) | |
| Date | |
| Current certifications / attestations (ISO/IEC 27001, SOC 2, other) | |

Answering tips: *N/A* is accepted only when the control cannot apply (for example no AI features, no sub-processors). Our reviewer may ask for a short call to walk through the evidence. Evidence is handled under NDA and deleted after the review.

## Governance & Risk

| ID | Question | Weight | Evidence requested | Answer | Comment |
|----|----------|:------:|--------------------|--------|---------|
| GOV-01 | Do you maintain an information security programme with a named accountable executive (CISO or equivalent)? | 2 | Security organisation chart or policy extract naming the role | | |
| GOV-02 | Do you hold a current independent attestation or certification covering the service in scope (for example ISO/IEC 27001 or SOC 2 Type II)? | 3 | Certificate with scope statement, or SOC 2 Type II report under NDA | | |
| GOV-03 | Are information security policies approved by management, reviewed at least annually and communicated to all staff? | 2 | Policy index with approval and review dates | | |
| GOV-04 | Do you perform a formal information security risk assessment at least annually, with documented treatment plans? | 2 | Risk assessment summary or methodology description | | |
| GOV-05 | Are all staff and contractors subject to background screening appropriate to their role before being granted access? | 1 | Screening policy extract | | |
| GOV-06 | Do all staff sign confidentiality agreements and receive security awareness training at hire and at least annually? | 2 | Training completion statistics for the last 12 months | | |

## Access Control

| ID | Question | Weight | Evidence requested | Answer | Comment |
|----|----------|:------:|--------------------|--------|---------|
| ACC-01 | Is multi-factor authentication enforced for all staff access to systems that store or process customer data? | 3 | MFA policy and screenshot of enforcement configuration | | |
| ACC-02 | Is privileged (administrative) access restricted to named individuals, granted on a least-privilege basis and reviewed at least quarterly? | 3 | Last privileged access review record (redacted) | | |
| ACC-03 | Are user access rights removed or adjusted within one business day of a leaver or role change? | 2 | Joiner / mover / leaver procedure | | |
| ACC-04 | Does the service support single sign-on (SAML or OpenID Connect) and role-based access for customer users? | 2 | Product documentation for SSO and roles | | |
| ACC-05 | Is remote and administrative access to production performed only through a managed, logged channel (for example a bastion host or privileged access management tool)? | 2 | Architecture description of the administrative access path | | |
| ACC-06 | Are shared or generic accounts prohibited for production systems, with any exceptions documented and controlled? | 1 | Account management standard | | |

## Data Protection & Privacy

| ID | Question | Weight | Evidence requested | Answer | Comment |
|----|----------|:------:|--------------------|--------|---------|
| DAT-01 | Is customer data classified and handled according to a documented data-handling standard? | 2 | Data classification standard | | |
| DAT-02 | Is customer data logically or physically segregated from other customers' data? | 3 | Multi-tenancy architecture description | | |
| DAT-03 | Can you confirm the countries or regions where customer data is stored and processed, and are transfers outside those regions contractually controlled? | 3 | Data location statement and transfer mechanism | | |
| DAT-04 | Is customer data securely deleted or returned within an agreed period after contract termination, with written confirmation? | 2 | Data retention and deletion procedure | | |
| DAT-05 | Do you have a privacy programme (including a privacy contact and a process for data-subject requests) where personal data is processed? | 2 | Privacy notice or data processing addendum | | |
| DAT-06 | Are data-loss-prevention or equivalent controls in place to detect or block unauthorised bulk export of customer data? | 1 | Description of DLP or export controls | | |

## Encryption

| ID | Question | Weight | Evidence requested | Answer | Comment |
|----|----------|:------:|--------------------|--------|---------|
| ENC-01 | Is customer data encrypted in transit using current protocol versions (TLS 1.2 or higher) for all external interfaces? | 3 | TLS configuration summary or external scan result | | |
| ENC-02 | Is customer data encrypted at rest, including backups, using industry-accepted algorithms? | 3 | Encryption-at-rest statement for storage and backups | | |
| ENC-03 | Are encryption keys managed in a dedicated key management system with restricted access and documented rotation? | 2 | Key management standard | | |
| ENC-04 | Can the customer hold or control its own encryption keys (BYOK / HYOK) if required? | 1 | Product documentation | | |
| ENC-05 | Are secrets (API keys, passwords, certificates) stored in a secrets vault rather than in code or configuration files? | 2 | Secrets management standard | | |

## Vulnerability & Patch Management

| ID | Question | Weight | Evidence requested | Answer | Comment |
|----|----------|:------:|--------------------|--------|---------|
| VUL-01 | Are systems in scope scanned for vulnerabilities at least monthly, with authenticated scans where possible? | 2 | Scan schedule and summary of last scan (no technical detail required) | | |
| VUL-02 | Are critical vulnerabilities remediated within 14 days and high within 30 days, or compensated and risk-accepted with a documented reason? | 3 | Patch SLA policy and compliance metric for the last quarter | | |
| VUL-03 | Is an independent penetration test of the service performed at least annually, with findings tracked to closure? | 3 | Latest penetration test summary letter | | |
| VUL-04 | Are hardened configuration baselines applied to servers, containers and cloud resources, and checked for drift? | 2 | Hardening standard reference | | |
| VUL-05 | Do you operate a responsible-disclosure or bug-bounty channel for external researchers? | 1 | Public disclosure policy link | | |

## Logging & Monitoring

| ID | Question | Weight | Evidence requested | Answer | Comment |
|----|----------|:------:|--------------------|--------|---------|
| LOG-01 | Are security-relevant events (authentication, privilege use, data access, configuration changes) logged for all in-scope systems? | 3 | Logging standard | | |
| LOG-02 | Are logs centralised, protected against tampering and retained for at least 12 months? | 2 | Log retention statement | | |
| LOG-03 | Is there 24x7 security monitoring (in-house or outsourced SOC) with defined escalation paths? | 3 | Monitoring service description | | |
| LOG-04 | Are customer-facing audit logs available to the customer (via console or API) for their own tenant? | 2 | Product documentation | | |
| LOG-05 | Are clocks on in-scope systems synchronised to a reliable time source? | 1 | Statement | | |

## Incident Response & Notification

| ID | Question | Weight | Evidence requested | Answer | Comment |
|----|----------|:------:|--------------------|--------|---------|
| INC-01 | Do you maintain a documented incident response plan that is tested at least annually? | 3 | Plan table of contents and date of last exercise | | |
| INC-02 | Will you notify the customer of a confirmed security incident affecting its data or service within 24 hours of confirmation? | 3 | Contractual notification commitment | | |
| INC-03 | Does the notification include the nature of the incident, data affected, actions taken and a named contact? | 2 | Notification template | | |
| INC-04 | Are post-incident reviews performed and lessons learned tracked to closure? | 1 | Post-incident review template | | |
| INC-05 | Do you have cyber insurance or equivalent financial cover for incidents affecting customers? | 1 | Insurance certificate summary | | |
| INC-06 | Have you had a security incident affecting customer data in the last 24 months? If yes, please describe the root cause and remediation. (Answer 'Yes' if NO incident occurred or if an incident was fully remediated and disclosed.) | 2 | Incident summary if applicable | | |

## Business Continuity & Resilience

| ID | Question | Weight | Evidence requested | Answer | Comment |
|----|----------|:------:|--------------------|--------|---------|
| BCP-01 | Do you have a business continuity and disaster recovery plan covering the service, tested at least annually? | 3 | Last DR test summary with date and outcome | | |
| BCP-02 | Are recovery time and recovery point objectives (RTO / RPO) for the service defined and contractually committed? | 2 | Service-level description | | |
| BCP-03 | Are backups taken at least daily, stored in a separate location or account, and restore-tested at least quarterly? | 3 | Backup and restore test policy | | |
| BCP-04 | Is the service deployed with redundancy (multiple availability zones or sites) to avoid a single point of failure? | 2 | Architecture summary | | |
| BCP-05 | Do you publish service availability and planned maintenance to customers, and report against the committed SLA? | 1 | Status page link or SLA report | | |

## Sub-processors & Supply Chain

| ID | Question | Weight | Evidence requested | Answer | Comment |
|----|----------|:------:|--------------------|--------|---------|
| SUB-01 | Do you maintain and publish a list of sub-processors that handle customer data, with their location and purpose? | 3 | Sub-processor list | | |
| SUB-02 | Are customers notified in advance of new sub-processors, with a right to object? | 2 | Contractual clause or notification process | | |
| SUB-03 | Do you assess the security of your own critical suppliers before onboarding and periodically thereafter? | 2 | Supplier risk management procedure | | |
| SUB-04 | Do you flow down equivalent security, confidentiality and notification obligations to sub-processors? | 2 | Standard sub-processor contract clauses | | |
| SUB-05 | Do you maintain a software bill of materials (SBOM) or equivalent inventory of third-party components in the service? | 1 | Statement or sample SBOM | | |

## Secure Development

| ID | Question | Weight | Evidence requested | Answer | Comment |
|----|----------|:------:|--------------------|--------|---------|
| DEV-01 | Do you follow a documented secure development life cycle with security requirements, threat modelling and code review? | 2 | SDLC overview | | |
| DEV-02 | Are static and dependency vulnerability scans run automatically in the build pipeline, with blocking thresholds for critical findings? | 2 | Pipeline description | | |
| DEV-03 | Are development, test and production environments separated, and is production customer data excluded from non-production environments (or masked)? | 3 | Environment separation standard | | |
| DEV-04 | Are changes to production approved, tested and traceable to a change record, with emergency changes reviewed afterwards? | 2 | Change management procedure | | |
| DEV-05 | Are developers trained in secure coding at least annually? | 1 | Training record summary | | |

## AI Usage

| ID | Question | Weight | Evidence requested | Answer | Comment |
|----|----------|:------:|--------------------|--------|---------|
| AI-01 | Does the service use AI or machine-learning components (including third-party large language models) to process customer data? If yes, are they documented and disclosed to customers? | 3 | AI feature inventory and disclosure | | |
| AI-02 | Is customer data excluded from training or fine-tuning of models that serve other customers, unless the customer explicitly opts in? | 3 | Data-use terms for AI features | | |
| AI-03 | Where third-party AI providers are used, are prompts and outputs not retained by the provider (zero-retention) or retained only under contract? | 2 | Third-party AI provider terms | | |
| AI-04 | Are AI features subject to an impact or risk assessment covering accuracy, bias, misuse and data leakage before release? | 2 | AI impact assessment summary | | |
| AI-05 | Is there human oversight for AI outputs that affect individuals or material business decisions, and can the customer disable AI features? | 2 | Product documentation for AI controls | | |
| AI-06 | Is AI system behaviour monitored in production (drift, abuse, prompt injection) with a process to roll back or disable a model? | 1 | AI monitoring description | | |

## Declaration

| | |
|--|--|
| I confirm the answers above are accurate to the best of my knowledge and that material changes will be notified. | |
| Name / role | |
| Date | |

*This questionnaire is part of the open-source Vendor Risk Assessment Template (MIT licence). The scoring workbook that consumes these answers is `Vendor-Risk-Assessment-Template.xlsx`.*
