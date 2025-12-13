# Overview

This file should contain release notes between tagged versions of the product. Please update this file with your pull
requests so that whoever deploys a given version can file the relevant changes under the corresponding version.

Add changes to the "Unreleased Changes" section. Once you create a version (and tag it), move the unreleased changes
to a section with the version name.

## ⚠️ Compatibility Notice
> The following updates (**v0.53.8 → v0.54.9**) were **developed and tested on ERPNext v14**.  
> Compatibility with **ERPNext v15** has **not been verified**.  
> Use these versions **at your own risk** on v15.

## Unreleased Changes
## 0.66.9
* Fix fetch Tax Category-id on Advance Payment Entry

## 0.66.8
* FIX show Advance Payment Section on Sales invoice

## 0.66.7
* Fix Advance Payment Greater than Grand Total

## 0.66.6
* Fix Regional Overflow Call Override Function

## 0.66.5
* Fix Calculate tax allocation Depends On Advance Payment

## 0.66.4
* Fix Sales Invoice Return Against Null Check in Tax GL Entries
  * Handle Return Invoices Without Return Against Field Set

## 0.66.3
* Fix Cancellation Invoices according to ZATCA

## 0.66.2
* Fix Update Outstanding for Self Depends on Invoice Has advance Item

## 0.66.1
* Return exceeds outstanding on sales invoices paid from payment advance

## 0.66.0
* Settling Return Invoice paid from Advance Payment Entry
  * Enable Return Invoices
  * Update Tax Allocations
  * Mapped Outstanding Amount When return the Invoice
  * Calculate Advance Tax Depends on Sales Invoice Advances Allocation tax

## 0.55.9
* Fix Automated Setup Wizard Completion

## 0.55.8
* Update Advance Payment Entry Sales Taxes and Charges Filed Depends On

## 0.55.7
* Prevent Send Payment Entry to ZATCA when Party Type not Customer

## 0.55.6
* Skip VAT Compliance Validation for Payment Entries that are Not Against Customers to Avoid Lookup Errors when Saving Supplier Payments
## 0.55.5
* Add Advance Payment Entry log Sales Invoice Advance Payment table

## 0.55.4
* Add ZATCA integration safeguards across modules
  * Implement is_zatca_enabled check to prevent processing when ZATCA integration is disabled
  * Update ZATCA integration checks across Branch, GL Entry, Payment Entry, Payment Reconciliation, and Sales Invoice modules
  * Add ZATCA enabled validation in Sales Invoice Advance, Unreconcile Payment, and return invoice utilities
* Remove required property setter for custom_zatca_payment_means_code in Mode of Payment
* Remove after_migrate hook from install process
* Add automated test script for ZATCA setup and validation

## 0.55.3
* Cap the Calculated Tax Amount at the unallocated_tax value Advance Payment Entry.

## 0.55.2
* Add Patche to fetch Advance Payment Entry on Journal Entry

## 0.55.1
* Return Amount From Advance Payment Entry
  * Added a new button, “Return Advance Payment,” on the Payment Entry form.
  * Includes a dialog for specifying the return amount with validation against the unallocated amount.
  * Journal Entry Creation
  * Implemented automatic creation of a Journal Entry when returning an advance payment.
  * Avoid canceling Journal Entries involved in ZATCA submissions.

## 0.55.0
* ⚠️ Payment Entry option is still in Beta on Version 15 — use at your own risk.

## 0.54.9
* ZATCA Phase 2 Advance Payment Print Format

## 0.54.8
* Fix Passing Prepayment Invoices depends on Advance Payment
* Read Prepayment info depends on Advance Payment for Print Formate

## 0.54.7
* Prevent Cancellation of Advance Payment Entry when Advance Payment depends on Payment Entry

## 0.54.6
* Fix Settings Tax Allocation on Advance Payment Entry

## 0.54.5
* Fix Passing Payment Entry on check IS Advance Payment Depends On Entry

## 0.54.4
* Avoid Return Invoice Paid Settling From Advance Payment Entry
* Handle Payment Reconciliation with Advance Payment Depends On

## 0.54.3
* Add taxes when settling Sales Invoice from advance payment entry
* Apply Advance Payment Depends On applicable payments

* 
## 0.54.2
* Enhance Test Performance

## 0.54.1
* Reverse GL Entries for Advance Payment Taxes

## 0.54.0
* Fix Read Zatca Category from Tax Category

## 0.53.9
* Fix Adding Advance Payment Tax Account

## 0.53.8
* Add Methods Advance Payment Depends on Payment Entry and Sales Invoice
* Add new Settings for Advance Payment Taxes
* Send Advance Payment Entry to ZATCA

## 0.53.7
* Add Rounding App to Test Site

## 0.53.6
* Prepare Test System for ZATCA Integration

## 0.53.5
* Create Intal Test for ZATCA Buissness Settings Phase 1

## 0.53.4
* Create Intal Test for ZATCA EGS

## 0.53.3
* Create Intal Test for SI Counting Settings

## 0.53.2
* Create Intal Test for Precomputed Sales Invoice
* Fix Bug in Handling QR for Precomputed Sales Invoice

## 0.53.1
* FIX No Permission for ZATCA Business Settings

## 0.53.0
* Reduce Time for Github Actions

## 0.52.9
* Refactor Test and Create Initial Test for Sales Invoice Additional Fields

## 0.52.8
* Add Mode Of Payment Account Custom Filed
* Fetch Mode of Payment Account and Setup Reference Fields Depends on This
## 0.52.7
* Refactor Test and Move Logic to Buissness ZATCA Phase 2

## 0.52.6
* Allow Activate Phase 1 if Phase 2 not Active and Vise Versa

## 0.52.5
* Fix Issue for Logger on Version 14

## 0.52.4
* Link Party Party type  with Advance payment account in advance invoice Ledger

## 0.52.3
* Fix github action approval first befor test

## 0.52.2
* Prevent Show Return Invoice Against Paid From Advance Payment

## 0.52.1
* Settling Advance Payment Entry from Payment References on return Advance Payment invoice

## 0.52.0
* Feat Run Github Actions only after Code Review

## 0.51.9
* Fix Calculate Item Tax Amount depends on Tax included in Basic Rate
* Calculate Total Tax and Charges Amount from Items Tax Amounts
* Return Advance Item Rate depends on Tax included in Basic Rate

## 0.51.8
* Fix Prevent missing ZATCA Business Settings on sales return 
## 0.51.7
* Enhanced ZATCA compliance checks with improved test feedback
* Improved compliance test output formatting for both simplified and standard invoices

## 0.51.6
* Enable return invoice paid from advance payment
* Settlement process
  * Get advance payments allocated to the original (return_against) invoice. 
  * Create GL entries to reflect settlement for the advance invoice. 
  * Unreconcile the advance payment from the Payment Entry. 
  * Create GL entries for settlement for the return_against invoice. 
  * Reconcile any difference in allocated amounts.
* Fix Remove advances from Sales Invoice on Unreconcile by remove unliked payment or update allocated_amount

## 0.51.5
* Add Reference No And Reference Date for Advance Payment Invoice On Mode of Payment is Bank
* Fix Call Read Mode of Payment Account on VERSION 15 controller

## 0.51.4
* Added defualt bussnies settings data in setup for dev

## 0.51.3
* Fix Default Other IDs by moving logic to clint-side

## 0.51.2
* Fix Default Other IDs Handling by moving population logic to server-side and adding update method

## 0.51.1
* Fix Return Zero Qty

## 0.51.0
* Fix Make Custom Property Setter On VERSION 14
## 0.50.9
* Install Payments Before Run App Tests

## 0.50.8
* Avoid Check Pay Payment Entries from non reconciled invoices IS Advance Invoice

## 0.50.7
* Fix Setup ZATCA Custom Fields When Install

## 0.50.6
* Apply advance payments before validate hook to ensure passing updates for totals
* Remove Apply Applicable Advances on validate form script

## 0.50.5
* Add CI/CD GITHUB Actions Config
* Apply Pre-commit on Project
* FIX Frappe Semgrep on Project

## 0.50.4
* FIX Apply Applicable Advances on validate form script

## 0.50.3
* FIX Settling Zero Amount On Advance Payment Invoice

## 0.50.2
* Calculate Prepaid Amount on Generate EInvoice xml
* Set Amounts is ZERO on Prepayment Invoice Lines

## 0.50.1
* Set Update Outstanding for Self Read Only On Return Advance Payment Invoice

## 0.50.0
* Fix Cannot pay to Customer without any negative outstanding invoice
* Handle Transaction Currency and Rate fileds on version 15

## 0.49.9
* Fix Calculate Advance Item Rate on return Advance Payment Invoice 
* Add Condtion Invoice Not Return on Prevent Settling Advance Invoice on Pyment Entry Refernaces 
* Fix Calculation Amounts For Payment Entry referances type of "PAY"

## 0.49.8
* Fix Return Advance Payment Invoice on version 14 because of unexistance of serial and batch fields

## 0.49.7
* Allow Return Advance Payment Invoice
  * Return Outstanding Amount for Invoice 
  * Make "Pay" Payment Entry For Return Invoice
  * Settling GL Entries For Advance Invoice
  * Settling GL Entries For Advance Pyment Entry

## 0.49.6
* Auto Apply Advance Payments functionality for Sales Invoice
  * Skip Adding Advances when Allocated Amount is ZERO on Submit the Invoice
* Payment Reconciliation
  * Handle the Deference between version 14 AND 15 on getting Outstanding Invoices
  * HANDLE CHANGING ON LOGIC ON GETTING PAYMENT ENTRIES BETWEEN VERSION 14 AND 15
* Payment Entry
  * FIX Cancellation non Advance Payments
  * Prevent Settling Advance Invoices from Payment Entry References

## 0.49.5
* Install pypdf for version 14
* Add Auto Apply Advance Payments functionality for Sales Invoice
  * Automatically retrieves and applies customer advance payments to sales invoices
  * Filters advance payments by customer, payment type, and unallocated amounts
  * Calculates optimal allocation amounts based on invoice grand total
  * Integrates with ZATCA Business Settings for configuration control

## 0.48.5

### Advanced Payment Entry System
* Implemented dedicated Advance Payment Item configuration:
  * Added special item type for advance payments
  * Enforced item configuration lock after initial setup
  * Integrated with ZATCA Business Settings

* Enhanced Sales Invoice Processing:
  * Added support for advance payment identification and handling
  * Implemented automatic Payment Entry generation with correct payment type and mode
  * Added new child table 'Advance Payment Invoices' for tracking
  * Integrated mode of payment tracking for advance invoices

* Payment Entry Enhancements:
  * Added advance payment flags and validation
  * Implemented safeguards against unauthorized unreconciliation
  * Added invoice type tracking and validation
  * Enhanced payment entry workflow for advance scenarios

* Advanced Payment Settlement:
  * Implemented comprehensive settlement calculation system:
    * Automated tax amount calculation based on allocation
    * Proper handling of base amounts and tax percentages
    * Integration with XML e-invoice generation
  * Added validation for return invoice scenarios
  * Implemented GL Entry tracking and validation

* Payment Reconciliation Controls:
  * Implemented strict controls for advance payment reconciliation
  * Added validation rules for advance invoices
  * Restricted reconciliation operations for return invoices
  * Enhanced error handling and user feedback

## 0.47.0

* Support displaying `Return Against Additional References` in `ZATCA Phase 2 print format`.
* Fix letter head in ZATCA print formats.
* Add Additional IDs translation.

## 0.46.0

* Use ZATCA CLI 2.7.0

## 0.45.1

* Use ZATCA CLI 2.6.0
  * This fixes an issue with invoice ZATCA validation prior to submission
  * Refer to the [CLI release](https://github.com/lavaloon-eg/zatca-cli/releases/tag/2.6.0) for details

## 0.45.0

* Add `Return Against` in `ZATCA Phase 2 Print Format` for Debit & Credit Notes.

## 0.44.0

* Support multiple billing references for return invoices
  * Add `Return Against Additional References` custom field to sales invoice
  * The field has no ERPNext impact. The additional references are included in the XML for ZATCA
  * The field allows submitted non-return invoices for the same company/customer/supplier as the current invoice

## 0.43.2

* Fetch buyer’s postal zone from buyer details in SIAF instead of incorrectly using the seller’s postal zone.

## 0.43.1

* Consider multiple tax categories in invoice allowance amount.

## 0.43.0

* Support selecting Print Format and Language when downloading PDF/A-3b.

## 0.42.0

* Add support to generate PDF/A-3b for invoices
  * Uses ZATCA CLI 2.5.0

## 0.41.2

* Update ZATCA Phase 2 Print Format for both Sales Invoice and POS Invoice.
  * Consider missing seller and buyer other ids.
  * Consider New Feature `Enable Branch Configuration` to display branch CRN and Address.

## 0.41.1

* Add Arabic translations for multi-branch support

## 0.41.0

* Update ZATCA Business Settings and add checkbox `Enable Branch Configuration`.
* Update Branch doctype add fields for
  * Company
  * Address
  * Branch Commercial Registration Number (CRN)
* When enabling this configuration sales invoice will not be submittable without a branch specified in the sales invoice, 
this requires manual configuration of an accounting dimension for branch and company.

## 0.40.1

* Fix `TaxAmount` rounding in XML if system precision > 2.

## 0.40.0

* CLI setup now grabs version 2.4.0

## 0.39.4

* Fix item line tax amount calculation if invoice is not in `SAR`.

## 0.39.3

* Use flt instead of round when calculating line amount for tax included items to ensure we use the system-configured
  rounding method
* Update "Return Reason" label in sales invoice to "Return/Debit Reason" since it's used in both cases
* Update print formats to be translatable (English/Arabic out of the box)

## 0.39.2

* Fix error messages not showing on frappe versions older than v15.17.0

## 0.39.1

* Prevent cancellation of invoices only when ZATCA phase 2 integration is enabled for the company

## 0.39.0

* CLI setup now grabs version 2.3.0

## 0.38.0

* Fix invalid tax amounts if an item is added to multiple lines
  * We now use ERPNext-computed line-level tax totals instead of item-wise tax details
  * Print formats now use line-level tax totals if present and fall back to item-wise tax details if not, to accomodate
    invoices issued prior to this change

## 0.37.2

* Fix invoice being rejected when pricing rule is applied with discount amount and margin.

## 0.37.1

* Fix various return invoice regressions in 0.37.0
  * Fix negative total and line value errors
  * Fix payable and rounding adjustment amount warnings in case of return

## 0.37.0

* Improve ZATCA validation error messages on submitting invoices (if blocking on invalid invoices is enabled)
  * We now only show errors/warnings headers if we actually have errors/warnings
  * The errors and generated XML is put into the `Error Log` to make it easier to troubleshoot instead of hunting for 
  the XML file in /tmp
* Improve XML generation to avoid excessive blank lines
* Support "Rounded Total" if enabled
  * Output rounding adjustment as is (positive or negative); previously, we used the absolute value which is wrong
  * Use the rounded total (`rounded_total`) as the payable amount instead of the grand total.
    `rounded_total = grand_total + rounding adjustment`

## 0.36.1

* Fix Return Invoice rejection when adding discount amount as amount (not percentage) on grand total

## 0.36.0

* CLI setup now grabs version 2.2.0

# 0.35.0

* Fix handling of B2B customers
  * A B2B customer has a VAT or at least one of the other IDs (TIN, CRN, etc.)
  * The compliance dialog now uses an updated filter for simplified/standard customers that respects this definition
  * When saving an invoice for a company configured to use "Standard Tax Invoices" only, we validate that the customer
    has a valid ID (VAT or other)
  * When generating XML for ZATCA, we no longer include other IDs as a `CompanyID` inside the `PartyTaxScheme` because 
    it results in validation failure

# 0.34.0

* Fix seller additional ids were returned empty in the xml if not filled.
* Include buyer additional ids in case if no vat registration number is provided for the buyer.

# 0.33.1

* Fix JRE extraction error if it was previously extracted

## 0.33.0

* Fix compliance check not showing the error message if an exception occurs
  * This happens for missing configurations, e.g. not having a sales taxes and charges template set for the company
* Migrate ZATCA files under the site directory to avoid loss upon update on frappe cloud
  * Certificates, keys, and CSRs are now stored in `{site}/zatca-files`
  * Tools (CLI and JRE) are now stored in `{site}/zatca-tools`
  * A patch migrates existing files if any, but it'll only work for self-hosted instances (on frappe cloud, the files
    would be lost before the patch is run)

## 0.32.2

* Fix print format company filter for POS Invoice Phase 2
* Fix return POS invoices getting rejected due to missing reason
  * Use hard-coded return reason "Return of goods"

## 0.32.1

* Fix invoice rejection when user increases the item rate on sales invoice.

## 0.32.0

* Delete obsolete print formats
* Add phase 2 support for POS Invoice
  * `Sales Invoice Additional Fields` and `ZATCA Integration Log` can now link to `POS Invoice`
  * `Sales Invoice Additional Fields` are now created for POS invoices and skipped for consolidated sales invoice 
    (created from POS invoices when closing the POS)
  * Added phase 2 print format for POS Invoice that includes the QR from the corresponding additional fields doc

## 0.31.0

* Support invoice discount on `Grand Total`.

## 0.30.3

* Enhance Fatoora Server Url patch to remove spaces for each company fatoora server url.

## 0.30.2

* Fix `ZATCA Integration Log` to store the actual raw response returned by ZATCA instead of a JSON serialization of
  a parsed response. This ensures we can catch bugs in our parsing logic, as well as unexpected changes in the ZATCA
  response format
* Use `clearanceStatus` from ZATCA responses as `ZATCA Integration Log` status instead of `status`. This fixes
  blank status for cleared invoices

## 0.30.1

* Use ZATCA CLI 2.1.1 which includes updated schematrons for validation

## 0.30.0

* Add ZATCA Integration Summary and ZATCA Integration details reports.
* Add Checkbox for automatic configuration for VAT accounts in `ZATCA Business Settings`
* Fix automatic creation of Tax account on creating new `ZATCA Business Settings` when System Language is not English.

## 0.29.1

* Hot Fix for print format displaying last ZATCA Business Settings info. instead of current company settings.

## 0.29.0

* Support blocking sales invoice submission on ZATCA validation failure
  * Add a new setting `Block Invoice on Invalid XML` to `ZATCA Business Settings`
  * CLI setup now grabs version 2.1.0 (required for blocking support)
  * Upon sales invoice submission, we now throw an exception and show errors/warnings from ZATCA validation if any

## 0.28.0

* Support multiple tax categories in sales invoice.
* Add new ZATCA Tax Category
  * Code: VATEX-SA-DUTYFREE,
  * Reason: Qualified Supply of Goods in Duty Free area

## 0.27.0

* Add a new tab in ZATCA Phase 2 Business Settings for configuration of the tax account per company.
* Create Tax Category, Sales Taxes and Charges template and Item tax template and link them to the tax account created on creating new ZATCA Business Settings
* Set ZATCA Business Settings Fields to Be readonly only after onboarding except for system manager.
  * Updated fields: Company, Unit Name, Unit Serial, Address, seller name, VAT Registration Number and additional ids.

## 0.26.0

* Remove `Fatoora Server Url` field and replace it with `Fatoora Server` Select Field with 3 options `['Sandbox', 'Simulation', 'Production']`
* Automatic update of the new `Fatoora server` field with the server that was already in the `Fatoora Server Url` field. 

## 0.25.1

* Merge hot fixes from master (from 0.23.2)

## 0.25.0

* Support item tax included in basic rate.

## 0.24.2

* Hot fix for customer creation on frappe v15.38.0 ([Issue](https://github.com/lavaloon-eg/ksa_compliance/issues/86))
* Fix showing done only without displaying error message on Perform Compliance Check when there is an issue in company setup.

## 0.24.1

* Fix not showing additional buyer ids for customer when creating a new customer using quick entry.

## 0.24.0

* Support item discounts

## 0.23.3

* Hot Fix for print format displaying last ZATCA Business Settings info. instead of current company settings.

## 0.23.2

* Hot fix: Use seller name instead of company name when generating CSR. Seller name is meant to be the company name
  in communications with ZATCA, and can be edited directly (whereas company name is internal)
* Hot fix: When parsing ZATCA errors, handle plain string errors without code or category. In certain cases, like the 
  seller name being too long, the ZATCA response included plain errors which caused error parsing itself to fail prior
  to logging the failure

## 0.23.1

* Hot fix for customer creation on frappe v15.38.0 ([Issue](https://github.com/lavaloon-eg/ksa_compliance/issues/86))

## 0.23.0

* Support submitting sales invoice with different currencies as per ZATCA acceptance criteria.
* Show print format of POS, Phase 1 and Phase 2 in current invoice currency.

## 0.22.1

* Include ZATCA Validation on sales taxes and charges table only if company has active phase 1 or phase 2 business settings

## 0.22.0

* Add ZATCA phase 1 print format for `POS Invoice`

## 0.21.1

* Fix compliance errors when specifying "simplified" or "standard" explicitly

## 0.21.0

* Track which `Sales Invoice Additional Fields` is latest in case of multiple submissions for the same invoice  due to
  rejection
* Limit fixing rejection to the latest sales invoice additional fields document
* Fix dashboard rejected invoice count
  * If an invoice receives multiple rejections, it counts as one rejected invoice now.

## 0.20.2

* Validate that sales invoice has tax rate in Sales Taxes and Charges Table in Phase 1 and Phase 2.
* Show all validation errors in one message on saving sales invoice.

## 0.20.1

* Fix parsing of ZATCA API responses
  * This should result in displaying actual error messages instead of just reporting the HTTP exception
* Fix simulation environment compliance CSID request
  * Requires ZATCA CLI version >= 2.0.1

## 0.20.0

* Update ZATCA workspace
  * Add link to overall integration dashboard
  * Add link to phase 1 business settings
  * Add link to tax categories
* Use `item_code` instead of `item_name` when accessing item tax details in print format of phase 1 and phase 2
* Fix a bug in phase 1 print format where the company address is displayed for the buyer instead of the buyer address in case 
  of Standard Tax Invoice
* Fix calculation of sum of allowance on invoice to be (invoice discount amount) + (sum discount amount on item)
* Validate that sales invoice has tax rate in Sales Taxes and Charges Table in case of enabled ZATCA Phase 2 integration

## 0.19.0

* Update compliance to handle both simplified and standard checks based on the configured type of transactions
  * If it's "Let the system decide", we prompt the user for simplified and standard customers and perform compliance
    for both
* Do not require a tax category if the sales invoice company does not have an enabled ZATCA phase 2 integration (`ZATCA
  Business Settings` with `Enable ZATCA Integration` checked)

## 0.18.0

* Support arabic translation for ZATCA tax categories.
* Add link for related integration log in Sales Invoice Additional Fields.
* Fix buyer country code in ZATCA XML
  * We used to include the country ID itself (e.g. Saudi Arabia) instead of the code (SA)
* Fix detection of standard sales invoices when ZATCA business settings is set to "Let the system decide"
  * We rely on whether the buyer has a VAT registration number, but we were setting buyer info after we've already
    detected invoice type, resulting in always thinking it's a simplified invoice.
* Specify invoice types when generating CSR
  * We used to hard code 0100 (simplified). Now we generate 1000 (standard), 0100 (simplified), or 1100 (both) depending
    on the configuration in ZATCA business settings
  * Note that this requires redoing the onboarding (production only) if the setting is changed because it requires 
    doing compliance checks for that invoice type.
* Update clearance API integration to send the "Clearance-Status" flag
* Fix company ID in buyer details (XML)
* Use due date as delivery date for standard invoices
* Rely on standard calculations of item tax details in print format.
  * Remove custom tax total and custom total after tax from sales invoice items.
* Remove custom qr code field in sales invoice

## 0.17.0

* Fix errors from non-escaped content in simplified invoice XML: Customer name, item name, etc.
* Fix and revamp simplified invoice compliance checks
  * Move compliance checks to the background queue to avoid timeouts
  * Add progress reporting
  * Tax category is now required for the compliance check since we've added a validation for it on invoice validate
  * Require all fields in the compliance prompt
  * Report the detailed ZATCA responses in an error log and link to it after the operation to enable users to report 
    problems

## 0.16.0

* Default to "Standard rate" if a sales invoice doesn't specify a tax category
  * We added a validation check to ensure a tax category is present, but that doesn't work for old submitted invoices.
    Such invoices could have been rejected for a variety of reasons, and we need to default to S tax category if they
    don't specify one when attempting to fix the rejection.
* Support fixing rejected sales invoices 
  * A fixable rejection can happen in mainly two cases:
    1) Bad or missing ZATCA configuration that leads to rejection. These cases can be fixed by updating the 
       configuration and generating another 'Sales Invoice Additional Fields' document for the invoice to submit to
       ZATCA
    2) An application bug that results in generating an invalid XML. These cases can be fixed by updating the app to a 
       later version that fixes the issue, then generating another 'Sales Invoice Additional Fields' document to submit
       to ZATCA
  * This change adds a custom button to the 'Sales Invoice Additional Fields' document that allows users to trigger the
    aforementioned generation.
  * Also, the invoice counter was appended to the 'Sales Invoice Additional Fields' name expression to ensure uniqueness.

## 0.15.0

* Add invoice line tax category and taxable amount in ZATCA XML
* Filter addresses in ZATCA phase 1 settings based on company

## 0.14.0

* Add QR code as a scannable image in Sales Invoice Additional Fields.
* Add ZATCA tax category exemption reason and code if applicable
* Remove negative values in print format on credit note issue

## 0.13.0

* Add automatic ZATCA CLI setup
  * There's now a new "CLI" tab in "ZATCA Business Settings"
  * In "Automatic" mode, we download the JRE and CLI automatically and fill in the CLI path and Java home path
  * In "Manual" mode, CLI path is specified by the user. Java home path is optional
  * Existing "ZATCA Business Settings" are automatically set to "Manual" by a patch upon deploying this change
  * New "ZATCA Business Settings" default to "Automatic"

## 0.12.1

* Use ZATCA phase 1 settings in phase 1 print format
* Fix tax calculation for tax templates with tax included in basic rate.

## 0.12.0

* Add ZATCA Phase 1 Print Format.
* Prevent Cancellation of Sales Invoice and Sales Invoice Additional Fields.
* Prevent Deletion of a Configured ZATCA Business Settings, ZATCA EGS, ZATCA Invoice Counting & ZATCA Precomputed Invoice.

## 0.11.0

* Add ZATCA workspace and dashboard
* Remove spurious ZATCA error logs (useless results/validation errors)
* Rework submission to ZATCA to avoid committing partial invoices

This rework addresses a problem in live sync mode, where we immediately submit
invoices to ZATCA upon invoice submission.

Here's how it worked before this change. When an invoice is submitted
(`on_submit` hook), we create an associated 'Sales Invoice Additional Fields'
document (SIAF for short) which produces the signed XML that'll be sent to
ZATCA. If live sync is enabled, we immediately committed at this point
before submitting the SIAF, which submits it to ZATCA in the `before_submit`
method. The db commit was added as part of handling the 'Resend' scenario in
ZATCA where there's an internal ZATCA error requiring us to resend the XML as
is later. In that case, we wanted to keep the SIAF as draft, which we did by
raising an exception in `before_submit`. The database commit was added to
preserve the SIAF, as frappe rolls back the transaction when an exception is
raised.

During frappe's review, they pointed out that committing during the `on_submit`
hook is problematic, since it may involve other apps with hooks that haven't
been called yet. These apps may raise an error that requires rolling back the
invoice submission transaction, only that won't work because we've already
committed.

The old logic has several issues:
* It makes submitting the document submit to ZATCA. Aborting a document
submission requires raising an exception, which gave us no choice other than to
make the problematic commit or switch some tables to MyISAM or Aria
non-transactional engines. If we reverse the notion--i.e. we submit to ZATCA,
and only if that results in a non-Resend status, we submit the document--we
no longer have to raise an exception to abort anything. Submission only happens
when everything's fine, and no custom logic is needed in `before_submit`.
* It runs too much logic in the context of invoice submission. Initially, we
thought it would be a good idea to abort invoice submission completely if it
failed ZATCA integration. However, as the ZATCA integration got more complicated
(e.g. resend), this behavior no longer makes sense. If an ERPNext invoice is
submitted successfully, it should go through. If ZATCA integration fails later
(e.g. due to a misconfiguration), the invoice can be corrected after
fixing the configuration with debit/credit notes.

The new behavior is as follows:

Upon invoice submission, we insert the SIAF as "Ready for Batch". If live sync
is enabled, we queue the submission to ZATCA `submit_to_zatca` after commit
(`enqueue_after_commit=True`). If the transaction rolls back, we're fine because
the ZATCA submission won't run. If the invoice submission commits, our ZATCA
submission logic doesn't run in the context of a document submission, so it
doesn't raise any exceptions. It chugs along, creating logs, updating itself
with the result received from ZATCA. If the integration status is anything
other than 'Resend', it submits itself.

As part of this new behavior, we're removing the permission to "Submit" SIAF
from Desk from users. We'll likely add a new action on the SIAF to submit to
ZATCA at some point. For now, such cases are covered by running the sync process
manually from the 'EInvoicing Sync' page.

## 0.10.1

* Fix jinja error if taxes are not defined for any lines in the invoice
    * Previously, our tax logic only added the relevant fields if tax details were found in the item wise tax details on
      taxes and charges template for the invoice. That meant if this info was missing for any reason, our template would
      raise an excpetion when trying to round the non-existent "total_amount" for the item line
    * We now properly set the tax percent and tax amount to 0 if they're missing
    * This will generate a proper invoice which will later fail ZATCA validation (e.g. during compliance)

## 0.10.0

* Create ZATCA phase 1 business settings.
* Add phase 1 QR code generator jinja function: `get_zatca_phase_1_qr_for_invoice`, which accepts a single
  parameter: `invoice_name`
* Fix `Sales Invoice Additional Fields` not created for standard tax invoices
* Update item tax calculation to use sales taxes and charges if item has no item tax template.
* Rename KSA Simplfied print format to ZATCA Phase 2 Print Format.

## 0.9.0

* Fix tax calculation to consider items quantities.
* Remove references to 'Lava' from the app (mainly lava-cli to zatca-cli)

## 0.8.0

* Add Qr Image to sales invoice additional fields, to be used in print format.
* Create print format for all types of invoices
* Add Purchase Order Reference to Zatca generated XML file.

## 0.7.0

* Ignore permissions when inserting ZATCA integration log
* Fix item total amount in sales invoice additional fields for return invoices
* Abort submission for sales invoice additional field document if the status is resend.
* Update ZATCA integration log with Zatca status.
* Autoname method for ZATCA integration log.
* Add Last Attempt field in additional field doctype.
* Update incorrect sales invoice additional fields.
    * Set blank integration status to Resend.
    * Draft the updated documents to resend them again.
* Update NULL last attempt in sales invoice additional fields set equal to modified.
* Fix invoice submission error when lava_custom is not installed

## 0.6.0

* Add support for precomputed invoices from POS devices
* Make precomputed invoice and sales invoice additional fields UUID unique to safeguard against bugs causing double
  ZATCA submissions

## 0.5.0

* Update e-invoice sync patch
    * Change timeout to 58 minutes so that we can run it hourly
    * Run it hourly
    * Sort additional fields by creation (oldest first)
    * Run in batches (of 100 by default)
    * Add more logging

## 0.4.0

* Ignore permissions when creating sales invoice additional fields
* Skip additional fields for invoices issued before 2024-03-01
* Add a flag to control ZATCA XML validation and make it disabled by default
* Switch signed invoice XML from an attachment to a field for performance reasons

## 0.3.0

* Submit Sales invoice additional field directly only if the sync mode is live.
* Initialize e_invoicing_sync page to run the batch mode.
* Fix error when storing ZATCA API result
* Update invoice counter/hash logic to use locking to guarantee serialization
* Fix buyer details street name being included in the XML if not defined (used to insert an error as the street name)
* Fix payable amount in XML to be set using grand total.
* Adding Tax Total with Subtotal in XML To handle sending tax currency code.
* Adding integration status field in sales invoice additional fields depends on response status code.
* Set invoice hash in sales invoice additional fields read only.
* E Invoicing Sync page to be shown in search bar.
* Fix taxable amount and Line price amount in XML to be net amount.
* Fix Credit note invoice submission issue.
* Skip additional fields if ZATCA settings are missing or setup is incomplete
* Add mode of payment "payment means code" custom field
* Use payment means code when generating XML to pass credit note validation
* Add support for compliance checks

## 0.2.0

* Use a hard-coded private key if the configured URL is for the sandbox environment
* Do not use ':' in XML filenames (from timestamp)
* Various fixes to simplified invoice format to pass validation
* Add invoice validation; messages/errors show up on a validation tab on the Sales Invoice Additional Fields doctype
* Improve API response handling

## 0.1.3

* Make the temp prefix is random

## 0.1.2

* Use a temporary prefix with temp file names to avoid clashes

## 0.1.1

* Fix certificate extraction from production CSID
* Fix previous invoice hash

## 0.1.0

* XML Templates:
    * Create Tax invoice template.
    * Create Simplified tax invoice template.
    * Add a method to generate XML regarding invoice type.
* Create E-Invoicing-Sync page to run the sync batch.
    * Initiate the batch flow to Sync E-invoices Individually.
* ZATCA Business Settings
    * Onboarding: Compliance and production CSID support
    * Signing and QR generation
    * Invoice reporting and clearance support, although it currently fails with bad request
