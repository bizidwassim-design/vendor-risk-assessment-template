# Contributing

Thanks for helping improve this template. Useful contributions include better-worded questions, additional
evidence suggestions, new contract clauses, mapping corrections, translations of the questionnaire and
new fictional worked examples.

## Ground rules

* **Fictional data only.** No real vendors, client names, people, e-mail addresses, hostnames or contract extracts.
* **Vendor-neutral and standards-based.** Reference standards by clause or control identifier; never paste their text.
* **No macros or add-ins.** The workbook must stay a plain `.xlsx` that opens in Excel, LibreOffice and Google Sheets.
* Be kind — see the [Code of Conduct](CODE_OF_CONDUCT.md).

## How the files are built

`scripts/build_template.py` is the single source of truth. It holds the question list, the clause list, the
tiering factors and the sample vendors, and it writes:

* `Vendor-Risk-Assessment-Template.xlsx`
* `questionnaire/vendor-questionnaire.csv`
* `questionnaire/vendor-questionnaire.md`

**Change the script, not the generated files.** CI rebuilds them and fails if the committed copies differ.

```bash
pip install openpyxl
python scripts/build_template.py
```

## Making a change

1. Open an issue describing the idea (optional for small fixes).
2. Fork, branch (`feat/question-dat-07`, `fix/clause-wording`).
3. Edit `scripts/build_template.py` and/or the Markdown docs. If you add a question, keep the `assert len(QUESTIONS)`
   line in sync and give it a weight and an evidence request.
4. Rebuild, open the workbook and check that:
   * no cell shows an error (`#REF!`, `#NAME?`, `#VALUE!`, `#N/A`);
   * empty rows stay empty (formulas return `""`);
   * domain scores, the overall score, the residual rating and the overdue flag still compute;
   * text is Arial, inputs blue, formulas black on grey.
5. Commit the script **and** the regenerated files.
6. Open a pull request describing what changed and why.

## Style notes

* Questions are closed (answerable with Yes / Partial / No / N/A), one control per question, with the evidence a
  reviewer would reasonably ask for.
* Weights: 3 = a control whose absence alone is a serious finding, 2 = important, 1 = good practice.
* Clause levels per tier: Required / Recommended / Optional. Tier 1 should never have fewer requirements than Tier 2.
* British English.

## Licensing of contributions

By contributing you agree that your work is released under the repository's [MIT License](LICENSE).
