# Copyright (c) 2025, LavaLoon and Contributors
# See license.txt

"""
Helper methods for creating test invoices and payment entries in ZATCA tests.
Provides reusable methods to reduce code redundancy across test files.
"""

import frappe
from frappe.utils import flt

from ksa_compliance.test.test_constants import (
    SAUDI_CURRENCY,
    TEST_COMPANY_NAME,
    TEST_STANDARD_CUSTOMER_NAME,
    TEST_TAX_ACCOUNT_NAME,
    TEST_TAX_TEMPLATE_NAME,
)

# ============================================================================
# ZATCA Settings Helpers
# ============================================================================


def get_active_zatca_settings(company=TEST_COMPANY_NAME):
    """
    Get the active ZATCA Business Settings for a company.

    Args:
        company (str): Company name (defaults to TEST_COMPANY_NAME)

    Returns:
        Document: Active ZATCA Business Settings document

    Raises:
        AssertionError: If no active settings found
    """
    active_settings = frappe.get_all(
        "ZATCA Business Settings",
        filters={"company": company, "status": "Active"},
        fields=["name"],
        limit=1,
    )

    if not active_settings:
        frappe.throw(f"No active ZATCA Business Settings found for company {company}")

    return frappe.get_doc("ZATCA Business Settings", active_settings[0]["name"])


def update_zatca_advance_payment_mode(mode="Sales Invoice"):
    """
    Update ZATCA Business Settings advance payment depends on mode.

    Args:
        mode (str): Either "Sales Invoice" or "Payment Entry"
    """
    settings = get_active_zatca_settings()
    if settings.advance_payment_depends_on != mode:
        settings.advance_payment_depends_on = mode
        settings.save()
        frappe.db.commit()


# ============================================================================
# Item Helpers
# ============================================================================


def ensure_test_item_exists(item_name="Test Item"):
    """
    Ensure a test item exists in the system.

    Args:
        item_name (str): Name of the test item

    Returns:
        str: Item name
    """
    if not frappe.db.exists("Item", item_name):
        item_doc = frappe.new_doc("Item")
        item_doc.item_code = item_name
        item_doc.item_name = item_name
        item_doc.item_group = "All Item Groups"
        item_doc.is_stock_item = 0
        item_doc.insert(ignore_permissions=True)
    return item_name


# ============================================================================
# Company/Customer Helpers
# ============================================================================


def get_company_abbr(company=TEST_COMPANY_NAME):
    """Get company abbreviation."""
    return frappe.db.get_value("Company", company, "abbr")


def get_customer_tax_category(customer):
    """Get customer's tax category."""
    return frappe.db.get_value("Customer", customer, "tax_category")


# ============================================================================
# Sales Invoice Creation Helpers
# ============================================================================


def create_normal_sales_invoice(
    customer=TEST_STANDARD_CUSTOMER_NAME,
    company=TEST_COMPANY_NAME,
    item_code=None,
    item_rate=500,
    qty=1,
    tax_template=None,
    submit=True,
    additional_discount_percentage=0,
    apply_discount_on=None,
):
    """
    Create a normal (non-advance) Sales Invoice.

    Args:
        customer (str): Customer name
        company (str): Company name
        item_code (str): Item code (if None, uses Test Item)
        item_rate (float): Item rate
        qty (float): Item quantity
        tax_template (str): Tax template name (if None, uses default)
        submit (bool): Whether to submit the invoice
        additional_discount_percentage (float): Additional discount percentage
        apply_discount_on (str): Apply discount on ("Net Total" or "Grand Total")

    Returns:
        Document: Sales Invoice document
    """
    if item_code is None:
        item_code = ensure_test_item_exists()

    company_abbr = get_company_abbr(company)
    customer_tax_category = get_customer_tax_category(customer)

    if tax_template is None:
        tax_template = TEST_TAX_TEMPLATE_NAME

    # Append company abbr if not already included
    if not tax_template.endswith(f" - {company_abbr}"):
        full_template_name = f"{tax_template} - {company_abbr}"
    else:
        full_template_name = tax_template

    invoice = frappe.new_doc("Sales Invoice")
    invoice.customer = customer
    invoice.company = company
    invoice.currency = SAUDI_CURRENCY
    invoice.posting_date = frappe.utils.nowdate()
    invoice.due_date = frappe.utils.nowdate()
    invoice.debit_to = f"Debtors - {company_abbr}"
    invoice.tax_category = customer_tax_category
    invoice.taxes_and_charges = full_template_name

    # Apply discount if specified
    if additional_discount_percentage > 0:
        invoice.additional_discount_percentage = additional_discount_percentage
        invoice.apply_discount_on = apply_discount_on or "Net Total"

    # Add item
    invoice.append(
        "items",
        {
            "item_code": item_code,
            "qty": qty,
            "rate": item_rate,
            "income_account": f"Sales - {company_abbr}",
            "cost_center": f"Main - {company_abbr}",
        },
    )

    # Add taxes from template
    template_doc = frappe.get_doc("Sales Taxes and Charges Template", full_template_name)
    for tax_row in template_doc.taxes:
        invoice.append(
            "taxes",
            {
                "charge_type": tax_row.charge_type,
                "account_head": tax_row.account_head,
                "cost_center": tax_row.cost_center,
                "description": tax_row.description,
                "rate": tax_row.rate,
            },
        )

    invoice.insert()

    if submit:
        invoice.submit()

    return invoice


def create_advance_sales_invoice(
    customer=TEST_STANDARD_CUSTOMER_NAME,
    company=TEST_COMPANY_NAME,
    rate=1000,
    qty=1,
    tax_template=None,
    submit=True,
):
    """
    Create an advance payment Sales Invoice.

    This sets advance_payment_depends_on to "Sales Invoice" in ZATCA settings
    and uses the advance_payment_item from settings.

    Args:
        customer (str): Customer name
        company (str): Company name
        rate (float): Advance payment amount
        qty (float): Quantity
        tax_template (str): Tax template name (if None, uses default)
        submit (bool): Whether to submit the invoice

    Returns:
        Document: Sales Invoice document (advance payment)
    """
    # Update ZATCA settings to use Sales Invoice for advance payments
    update_zatca_advance_payment_mode("Sales Invoice")

    # Get ZATCA settings to retrieve advance_payment_item
    settings = get_active_zatca_settings(company)
    advance_item = settings.advance_payment_item

    company_abbr = get_company_abbr(company)
    customer_tax_category = get_customer_tax_category(customer)

    if tax_template is None:
        tax_template = TEST_TAX_TEMPLATE_NAME

    # Append company abbr if not already included
    if not tax_template.endswith(f" - {company_abbr}"):
        full_template_name = f"{tax_template} - {company_abbr}"
    else:
        full_template_name = tax_template

    invoice = frappe.new_doc("Sales Invoice")
    invoice.customer = customer
    invoice.company = company
    invoice.currency = SAUDI_CURRENCY
    invoice.posting_date = frappe.utils.nowdate()
    invoice.due_date = frappe.utils.nowdate()
    invoice.debit_to = f"Debtors - {company_abbr}"
    invoice.mode_of_payment = "Cash"  # Required for advance invoice
    invoice.tax_category = customer_tax_category
    invoice.taxes_and_charges = full_template_name

    # Add advance payment item
    invoice.append(
        "items",
        {
            "item_code": advance_item,
            "qty": qty,
            "rate": rate,
            "income_account": f"Sales - {company_abbr}",
            "cost_center": f"Main - {company_abbr}",
        },
    )

    # Add taxes from template
    template_doc = frappe.get_doc("Sales Taxes and Charges Template", full_template_name)
    for tax_row in template_doc.taxes:
        invoice.append(
            "taxes",
            {
                "charge_type": tax_row.charge_type,
                "account_head": tax_row.account_head,
                "cost_center": tax_row.cost_center,
                "description": tax_row.description,
                "rate": tax_row.rate,
            },
        )

    invoice.insert()

    if submit:
        invoice.submit()

    return invoice


# ============================================================================
# Payment Entry Creation Helpers
# ============================================================================


def create_normal_payment_entry(
    customer=TEST_STANDARD_CUSTOMER_NAME,
    company=TEST_COMPANY_NAME,
    paid_amount=1000,
    payment_type="Receive",
    mode_of_payment="Cash",
    submit=True,
):
    """
    Create a normal (non-advance) Payment Entry.

    Args:
        customer (str): Customer name
        company (str): Company name
        paid_amount (float): Payment amount
        payment_type (str): Payment type ("Receive" or "Pay")
        mode_of_payment (str): Mode of payment
        submit (bool): Whether to submit the payment entry

    Returns:
        Document: Payment Entry document
    """
    company_abbr = get_company_abbr(company)

    payment_entry = frappe.new_doc("Payment Entry")
    payment_entry.payment_type = payment_type
    payment_entry.company = company
    payment_entry.posting_date = frappe.utils.nowdate()
    payment_entry.mode_of_payment = mode_of_payment

    if payment_type == "Receive":
        payment_entry.party_type = "Customer"
        payment_entry.party = customer
        payment_entry.paid_to = f"Cash - {company_abbr}"
        payment_entry.paid_from = f"Debtors - {company_abbr}"
    else:
        payment_entry.party_type = "Supplier"
        payment_entry.party = customer  # Can be supplier name
        payment_entry.paid_from = f"Cash - {company_abbr}"
        payment_entry.paid_to = f"Creditors - {company_abbr}"

    payment_entry.paid_amount = paid_amount
    payment_entry.received_amount = paid_amount
    payment_entry.target_exchange_rate = 1
    payment_entry.source_exchange_rate = 1

    payment_entry.insert()

    if submit:
        payment_entry.submit()

    return payment_entry


def create_advance_payment_entry(
    customer=TEST_STANDARD_CUSTOMER_NAME,
    company=TEST_COMPANY_NAME,
    paid_amount=1000,
    payment_type="Receive",
    mode_of_payment="Cash",
    tax_template=None,
    submit=True,
):
    """
    Create an advance Payment Entry.

    This sets:
    - advance_payment_depends_on to "Payment Entry" in ZATCA settings
    - is_advance_payment_depends_on_entry = 1
    - Applies taxes from advance_payment_entry_taxes_and_charges

    Args:
        customer (str): Customer name
        company (str): Company name
        paid_amount (float): Payment amount
        payment_type (str): Payment type ("Receive" or "Pay")
        mode_of_payment (str): Mode of payment
        tax_template (str): Tax template name for advance payment taxes
        submit (bool): Whether to submit the payment entry

    Returns:
        Document: Payment Entry document (advance payment)
    """
    # Update ZATCA settings to use Payment Entry for advance payments
    update_zatca_advance_payment_mode("Payment Entry")

    # Get ZATCA settings
    settings = get_active_zatca_settings(company)

    company_abbr = get_company_abbr(company)

    # Get advance payment tax template from settings if not provided
    if tax_template is None:
        advance_tax_template = settings.get("advance_payment_entry_taxes_and_charges")
    else:
        # Append company abbr if not already included
        if not tax_template.endswith(f" - {company_abbr}"):
            advance_tax_template = f"{tax_template} - {company_abbr}"
        else:
            advance_tax_template = tax_template

    payment_entry = frappe.new_doc("Payment Entry")
    payment_entry.payment_type = payment_type
    payment_entry.company = company
    payment_entry.posting_date = frappe.utils.nowdate()
    payment_entry.mode_of_payment = mode_of_payment

    # Mark as advance payment entry
    payment_entry.is_advance_payment_depends_on_entry = 1

    if payment_type == "Receive":
        payment_entry.party_type = "Customer"
        payment_entry.party = customer
        payment_entry.paid_to = f"Cash - {company_abbr}"
        payment_entry.paid_from = f"Debtors - {company_abbr}"
    else:
        payment_entry.party_type = "Supplier"
        payment_entry.party = customer  # Can be supplier name
        payment_entry.paid_from = f"Cash - {company_abbr}"
        payment_entry.paid_to = f"Creditors - {company_abbr}"

    payment_entry.paid_amount = paid_amount
    payment_entry.received_amount = paid_amount
    payment_entry.target_exchange_rate = 1
    payment_entry.source_exchange_rate = 1

    # Apply advance payment taxes if template is set
    if advance_tax_template:
        payment_entry.advance_payment_entry_taxes_and_charges = advance_tax_template

        # Add taxes from template
        try:
            template_doc = frappe.get_doc("Sales Taxes and Charges Template", advance_tax_template)
            for tax_row in template_doc.taxes:
                payment_entry.append(
                    "taxes",
                    {
                        "charge_type": tax_row.charge_type,
                        "account_head": tax_row.account_head,
                        "cost_center": tax_row.cost_center,
                        "description": tax_row.description,
                        "rate": tax_row.rate,
                    },
                )
        except frappe.DoesNotExistError:
            frappe.logger().warning(f"Tax template {advance_tax_template} not found")

    payment_entry.insert()

    if submit:
        payment_entry.submit()

    return payment_entry


# ============================================================================
# Convenience Helpers
# ============================================================================


def get_total_advance_allocated(invoice):
    """
    Calculate total advance allocated to an invoice.

    Args:
        invoice (Document): Sales Invoice or POS Invoice document

    Returns:
        float: Total advance allocated amount
    """
    return sum(flt(adv.allocated_amount) for adv in invoice.advances)


def verify_outstanding_is_zero(invoice, message=None):
    """
    Verify that invoice outstanding amount is zero.

    Args:
        invoice (Document): Sales Invoice or POS Invoice document
        message (str): Custom assertion message

    Raises:
        AssertionError: If outstanding is not zero
    """
    invoice.reload()
    outstanding = flt(invoice.outstanding_amount)

    if message is None:
        message = f"Outstanding should be 0 but got {outstanding}"

    if outstanding != 0.0:
        frappe.throw(message)


def log_invoice_details(invoice, label="Invoice"):
    """
    Log invoice details for debugging.

    Args:
        invoice (Document): Sales Invoice or POS Invoice document
        label (str): Label for log message
    """
    frappe.logger().info(f"   {label}: {invoice.name}")
    frappe.logger().info(f"   Net Total: {invoice.net_total} {invoice.currency}")
    frappe.logger().info(f"   Grand Total: {invoice.grand_total} {invoice.currency}")
    frappe.logger().info(f"   Outstanding: {invoice.outstanding_amount} {invoice.currency}")

    if hasattr(invoice, "advances") and invoice.advances:
        total_advance = get_total_advance_allocated(invoice)
        frappe.logger().info(f"   Total Advance: {total_advance} {invoice.currency}")
        frappe.logger().info(f"   Number of advances: {len(invoice.advances)}")
