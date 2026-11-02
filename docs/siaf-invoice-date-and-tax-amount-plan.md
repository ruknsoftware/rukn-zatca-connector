# Plan: Issue Date, Issue Time, Tax Amounts and Invoice Type on Sales Invoice Additional Fields

Status: planned, not implemented.

## Goal

Add read-only fields to the **Sales Invoice Additional Fields** (SIAF) doctype that show the invoice issue date, issue time and tax amounts **exactly as they appear in the ZATCA XML** for that SIAF. Users can see them on the SIAF form, and filter the SIAF list by issue date, without opening the XML or the source invoice.

Also add an **Invoice Type** field that shows the text for the invoice type code. Today the SIAF only shows the code (`invoice_type_code`, e.g. `381`). The new field shows its meaning (e.g. "Credit Note"), based on the `InvoiceTypeCode` enum in `ksa_compliance/invoice.py`.

## Approach

**New SIAFs: fill the fields while the XML is built.** `_prepare_for_zatca()` builds an e-invoice data dict (`einvoice.result`) and renders it into the XML with `generate_xml_file()`. The fields are filled from that same dict, so they hold the same values as the XML. They are stored in normal Frappe format (Date, Time, and Currency with the field's own precision), not with the XML template's text formatting. The XML is not parsed for this.

**Existing SIAFs (backfill patch): read the stored XML.** For records created before this change, the built data dict no longer exists, so the patch parses each record's stored XML.

Copying from the source invoice is not used, because the values in the XML differ from it in several known cases:

| Case | Source document | ZATCA XML |
|---|---|---|
| Credit notes (returns) | Tax is negative | Tax is positive (`get_float_value` applies `abs()`) |
| Journal Entry (advance payment) | No tax total field | Tax computed by `AdvancePaymentEntry`; issue time taken from the linked Payment Entry |

The `abs()` and the Journal Entry overrides are already applied inside `einvoice.result`, so reading from it gives the same values as the XML.

## 1. Schema

File: `ksa_compliance/ksa_compliance/doctype/sales_invoice_additional_fields/sales_invoice_additional_fields.json`

Fieldnames mirror the keys in `einvoice.result["invoice"]` and the XML elements they become. Insert them right after `sales_invoice` (first section, right column):

| fieldname | label | fieldtype | options | `einvoice.result["invoice"]` key | XML element | flags |
|---|---|---|---|---|---|---|
| `issue_date` | Issue Date | Date | — | `issue_date` | `cbc:IssueDate` | `read_only`, `in_list_view`, `in_standard_filter` |
| `issue_time` | Issue Time | Time | — | `issue_time` | `cbc:IssueTime` | `read_only` |
| `currency_code` | Document Currency | Data | — | `currency_code` | `cbc:DocumentCurrencyCode` | `read_only` |
| `total_taxes_and_charges` | Total Tax Amount | Currency | `currency_code` | `total_taxes_and_charges` | first `cac:TaxTotal/cbc:TaxAmount` | `read_only` |
| `base_total_taxes_and_charges` | Total Tax Amount (SAR) | Currency | `tax_currency` | `base_total_taxes_and_charges` | second `cac:TaxTotal/cbc:TaxAmount` | `read_only` |

The tax amounts are shown only on the form, not as list view columns. The existing `tax_currency` field (`cbc:TaxCurrencyCode`) is reused as-is.

Insert the invoice type field right after the existing `invoice_type_code` field, so the code and its text sit together:

| fieldname | label | fieldtype | options | source | flags |
|---|---|---|---|---|---|
| `invoice_type_code_label` | Invoice Type | Select | `Tax Invoice`, `Credit Note`, `Debit Note`, `Prepayment Invoice` | `InvoiceTypeCode(invoice_type_code).label` | `read_only`, `in_standard_filter` |

A Select field rather than Data, so the list can be filtered by type and each option is translated like any other Select option.

Also:

- Bump the doctype `modified` timestamp.
- Update the auto-generated type hints at the top of the controller. Developer mode regenerates them on save.
- Add Arabic translations for the new labels in `ksa_compliance/translations/ar.csv`, including the invoice type options:

  | English | Arabic |
  |---|---|
  | Invoice Type | نوع الفاتورة |
  | Tax Invoice | فاتورة ضريبية (already in `ar.csv`) |
  | Credit Note | إشعار دائن |
  | Debit Note | إشعار مدين |
  | Prepayment Invoice | فاتورة دفعة مقدمة |

## 2. Invoice type text in `invoice.py`

File: `ksa_compliance/invoice.py`

Keep the text next to the codes, in the `InvoiceTypeCode` enum, so there is one place that maps a code to its meaning:

```python
class InvoiceTypeCode(Enum):
    INVOICE_RETURN = "381"
    INVOICE_DEBIT_NOTE = "383"
    ADVANCE_PAYMENT = "386"
    EINVOICE = "388"

    @property
    def label(self) -> str:
        return _INVOICE_TYPE_CODE_LABELS[self]


_INVOICE_TYPE_CODE_LABELS = {
    InvoiceTypeCode.INVOICE_RETURN: "Credit Note",
    InvoiceTypeCode.INVOICE_DEBIT_NOTE: "Debit Note",
    InvoiceTypeCode.ADVANCE_PAYMENT: "Prepayment Invoice",
    InvoiceTypeCode.EINVOICE: "Tax Invoice",
}
```

- The labels are stored in English, like every Select value in Frappe. The desk shows them translated.
- The Select options in the JSON must list exactly these four labels. A test checks that they match (section 5).
- A code the enum doesn't know raises `ValueError` from `InvoiceTypeCode(code)`. That can't happen for SIAFs built here, because `_get_invoice_type_code()` only returns enum values.

## 3. Filling the fields while the XML is built

File: `ksa_compliance/ksa_compliance/doctype/sales_invoice_additional_fields/sales_invoice_additional_fields.py`

Add one method that takes the invoice part of the built data dict and stores the values in normal Frappe format:

```python
def _set_xml_summary_fields(self, invoice: dict) -> None:
    self.issue_date = getdate(invoice.get("issue_date"))
    self.issue_time = invoice.get("issue_time")
    self.currency_code = invoice.get("currency_code")
    self.total_taxes_and_charges = flt(
        invoice.get("total_taxes_and_charges"), self.precision("total_taxes_and_charges")
    )
    self.base_total_taxes_and_charges = flt(
        invoice.get("base_total_taxes_and_charges"), self.precision("base_total_taxes_and_charges")
    )
    self.invoice_type_code_label = InvoiceTypeCode(invoice.get("invoice_type_code")).label
```

`invoice["invoice_type_code"]` is the code written to `cbc:InvoiceTypeCode`, so the text always describes the code in the XML.

- `getdate` and `flt` are the standard `frappe.utils` helpers.
- Amounts use the Currency field's own precision, like any other Frappe currency field. They are not formatted with the template's `rounded(..., 2)` expressions.
- With the usual currency precision of 2, the stored amount equals the XML amount.

Call it in `_prepare_for_zatca()`, right after the XML is generated:

```python
invoice_xml = generate_xml_file(einvoice.result)
self._set_xml_summary_fields(einvoice.result["invoice"])
```

This one call site covers every doctype, because both builders put their final values into `einvoice.result`:

- **Sales Invoice / POS Invoice** (`SalesEinvoice`): values come from the invoice, with `abs()` already applied.
- **Payment Entry / Journal Entry** (`AdvancePaymentEntry`): the computed advance-payment tax is in `result["invoice"]["total_taxes_and_charges"]` and `["base_total_taxes_and_charges"]`, and the Journal Entry issue time is overridden from the linked Payment Entry before rendering.

If XML validation blocks the invoice, `_prepare_for_zatca()` throws and the SIAF is never inserted, so values set on an invalid document are discarded.

The "Fix Rejection" flow creates a new SIAF that goes through `_prepare_for_zatca()`, so it picks up the fields automatically.

### Precomputed invoices

Precomputed invoices skip `_prepare_for_zatca()`. Their XML is generated elsewhere and copied in by `use_precomputed_invoice()`, so there is no build step here to fill the fields from. For these, fill the fields by parsing `precomputed_invoice.invoice_xml` with the same function the backfill patch uses (section 4), called inside `use_precomputed_invoice()`.

`use_precomputed_invoice()` doesn't set `invoice_type_code` today, so precomputed SIAFs show no code. The same parse fills both `invoice_type_code` and `invoice_type_code_label` from `cbc:InvoiceTypeCode`.

## 4. Backfill patch for existing records (reads the XML)

New file: `ksa_compliance/patches/<date>_set_siaf_xml_summary_fields.py`, registered in `ksa_compliance/patches.txt` under `[post_model_sync]` so the new columns exist before it runs.

Parse the stored XML with the existing parser `ksa_compliance/utils/xml_parser.py` → `parse_xml_to_dict()` (also used by the ZATCA PDF print in `jinja.py`). It already extracts every value needed:

| SIAF field | `parse_xml_to_dict(xml)["invoice"]` key |
|---|---|
| `issue_date` | `issue_date` |
| `issue_time` | `issue_time` |
| `currency_code` | `currency_code` |
| `tax_currency` (only if empty) | `tax_currency` |
| `total_taxes_and_charges` | `total_taxes_and_charges` (first `TaxTotal`) |
| `base_total_taxes_and_charges` | `base_total_taxes_and_charges` (second `TaxTotal`) |
| `invoice_type_code` (only if empty) | `invoice_type_code` |
| `invoice_type_code_label` | `InvoiceTypeCode(invoice_type_code).label` |

Steps:

- Process SIAFs where `issue_date` is not set, in batches with an explicit page length (for example 500), fetching `name` and `invoice_xml`.
- Parse each XML and convert the text values to normal Frappe format, the same as for new SIAFs: `getdate()` for the date, and `flt()` with the field precision for the amounts. Write them with `frappe.db.set_value(..., update_modified=False)`.
- For old records whose XML is an attachment rather than in `invoice_xml`, load the doc and use `get_signed_xml()`.
- Commit after each batch. Log and skip records with no XML, XML that won't parse, or an invoice type code the enum doesn't know, without failing the migration.

This works for every doctype, Journal Entry included, because every SIAF stores its XML.

## 5. Tests

File: `ksa_compliance/ksa_compliance/doctype/sales_invoice_additional_fields/test_sales_invoice_additional_fields.py`

The tests check that the fields filled during the build hold the same values as the XML. Parsing the XML is used here only to verify, not to fill the fields. For each case, compare every new field with `parse_xml_to_dict(siaf.invoice_xml)` by value, not as text: `getdate()` for the date, and `flt()` for the amounts.

- A regular taxed invoice: also check `issue_date == posting_date`, `issue_time == posting_time` (to the second), `base_total_taxes_and_charges == flt(invoice.base_total_taxes_and_charges, precision)` and `invoice_type_code_label == "Tax Invoice"`.
- A credit note: tax amounts are positive, matching the XML, and `invoice_type_code_label == "Credit Note"`.
- The Select options of `invoice_type_code_label` in the doctype JSON equal the set of `InvoiceTypeCode` labels, so adding a code to the enum without adding its option fails the test.
- A foreign-currency invoice (if test fixtures allow): `total_taxes_and_charges` is in the document currency, and `base_total_taxes_and_charges` is in SAR.
- The backfill function: clear the fields on an existing SIAF, run it, and assert it restores the same values.

Verification on `zatca.localhost`:

```bash
bench --site zatca.localhost run-tests --app ksa_compliance --doctype "Sales Invoice Additional Fields"
bench --site zatca.localhost migrate   # confirm the patch backfills existing SIAF records
```

## Decisions

| Question | Decision |
|---|---|
| Show a tax amount in the list view? | No. Both tax amounts appear on the form only. |
| Add `issue_time` (`cbc:IssueTime`)? | Yes. |
| How are the fields filled for new SIAFs? | In `_prepare_for_zatca()`, from `einvoice.result` while the XML is built. Stored in normal Frappe format (Date, Time, Currency with field precision), not the XML template's formatting. Not parsed from the XML. |
| How are existing SIAFs backfilled? | By parsing each record's stored XML with `parse_xml_to_dict()`. |
| Credit notes: positive or negative tax? | Positive, because the XML stores it that way. |
| Backfill old Journal Entry records? | Yes. The patch reads each record's stored XML, which works for every doctype. |
| Invoice type text: where does it come from? | A `label` property on `InvoiceTypeCode` in `invoice.py`, filled from the code in `einvoice.result`. Shown in a read-only Select field next to `invoice_type_code`. |
| Invoice type text: include Standard/Simplified (e.g. "Simplified Tax Invoice Credit Note", as the ZATCA PDF print does)? | **To confirm.** Planned as the code's meaning only. Standard/Simplified comes from `invoice_type_transaction`, a separate field. |
| Precomputed invoices (no local build step)? | **To confirm.** Recommended: parse the precomputed XML, as the patch does, since that XML is the only source of the values. |

## Out of scope

- No change to the generated XML or what is sent to ZATCA. The new fields are for display and filtering only.
