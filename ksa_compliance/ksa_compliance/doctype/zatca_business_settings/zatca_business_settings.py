# Copyright (c) 2024, LavaLoon and contributors
# For license information, please see license.txt
import base64
import json
import os
from typing import Literal, NoReturn, Optional, cast

# import frappe
import frappe
from erpnext.accounts.doctype.account.account import Account
from erpnext.accounts.doctype.item_tax_template.item_tax_template import ItemTaxTemplate
from erpnext.accounts.doctype.sales_taxes_and_charges_template.sales_taxes_and_charges_template import (
    SalesTaxesandChargesTemplate,
)
from erpnext.accounts.doctype.tax_category.tax_category import TaxCategory

# noinspection PyProtectedMember
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder.functions import Count
from frappe.utils import get_url, get_url_to_list
from frappe.utils.data import get_link_to_form
from pathvalidate import sanitize_filename
from result import is_err

import ksa_compliance.zatca_api as api
import ksa_compliance.zatca_cli as cli
import ksa_compliance.zatca_files
from ksa_compliance import logger
from ksa_compliance.invoice import InvoiceMode
from ksa_compliance.throw import fthrow
from ksa_compliance.translation import ft


class ZATCABusinessSettings(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        from ksa_compliance.ksa_compliance.doctype.additional_seller_ids.additional_seller_ids import (
            AdditionalSellerIDs,
        )

        account_name: DF.Data | None
        account_number: DF.Data | None
        additional_street: DF.Data | None
        automatic_vat_account_configuration: DF.Check
        block_invoice_on_invalid_xml: DF.Check
        building_number: DF.Data | None
        city: DF.Data | None
        cli_setup: DF.Literal["Automatic", "Manual"]
        company: DF.Link
        company_address: DF.Link
        company_category: DF.Data
        company_unit: DF.Data
        company_unit_serial: DF.Data
        compliance_request_id: DF.Data | None
        country: DF.Link
        country_code: DF.Data | None
        csr: DF.SmallText | None
        currency: DF.Link
        district: DF.Data | None
        enable_branch_configuration: DF.Check
        enable_zatca_integration: DF.Check
        fatoora_server: DF.Literal["Sandbox", "Simulation", "Production"]
        java_home: DF.Data | None
        linked_tax_account: DF.Link | None
        other_ids: DF.Table[AdditionalSellerIDs]
        override_cli_download_url: DF.Data | None
        override_jre_download_url: DF.Data | None
        postal_code: DF.Data | None
        production_request_id: DF.Data | None
        production_secret: DF.Password | None
        production_security_token: DF.SmallText | None
        secret: DF.Password | None
        security_token: DF.SmallText | None
        seller_name: DF.Data
        street: DF.Data | None
        sync_with_zatca: DF.Literal["Live", "Batches"]
        tax_rate: DF.Percent
        type_of_business_transactions: DF.Literal[
            "Let the system decide (both)", "Simplified Tax Invoices", "Standard Tax Invoices"
        ]
        validate_generated_xml: DF.Check
        vat_registration_number: DF.Data
        zatca_cli_path: DF.Data | None
        zatca_tax_category: DF.Literal[
            "",
            "Standard rate",
            "Services outside scope of tax / Not subject to VAT || {manual entry}",
            "Exempt from Tax || Financial services mentioned in Article 29 of the VAT Regulations",
            "Exempt from Tax || Life insurance services mentioned in Article 29 of the VAT Regulations",
            "Exempt from Tax || Real estate transactions mentioned in Article 30 of the VAT Regulations",
            "Exempt from Tax || Qualified Supply of Goods in Duty Free area",
            "Zero rated goods || Export of goods",
            "Zero rated goods || Export of services",
            "Zero rated goods || The international transport of Goods",
            "Zero rated goods || International transport of passengers",
            "Zero rated goods || Services directly connected and incidental to a Supply of international passenger transport",
            "Zero rated goods || Supply of a qualifying means of transport",
            "Zero rated goods || Any services relating to Goods or passenger transportation as defined in article twenty five of these Regulations",
            "Zero rated goods || Medicines and medical equipment",
            "Zero rated goods || Qualifying metals",
            "Zero rated goods || Private education to citizen",
            "Zero rated goods || Private healthcare to citizen",
            "Zero rated goods || Supply of qualified military goods",
        ]
    # end: auto-generated types

    def validate(self):
        """Validates business settings and prevents conflicts"""
        if self.is_new() and self.production_request_id:
            fthrow(
                msg=_("Cannot create new settings with a pre-added Production CSID."),
                title=_("Invalid Configuration"),
            )

        if self.enable_zatca_integration:
            phase_1_settings = frappe.get_value(
                "ZATCA Phase 1 Business Settings",
                {"company": self.company},
                ["name", "status"],
                as_dict=True,
            )
            if phase_1_settings and phase_1_settings.status == "Active":
                link = get_link_to_form("ZATCA Phase 1 Business Settings", phase_1_settings.name)
                frappe.throw(
                    _(
                        "ZATCA Phase 1 Business Settings already enabled for company {0}: {1}"
                    ).format(self.company, link),
                    title=_("Another Setting Already Enabled"),
                )
        self.throw_if_duplicate_active_or_pending_settings()

    def throw_if_duplicate_active_or_pending_settings(self):
        """
        Throws an error if there is already an Active or Pending Activation ZATCA Business Settings for the same company (excluding self).
        """
        doctype_name = "ZATCA Business Settings"
        company = getattr(self, "company", None)
        source_name = getattr(self, "name", None)
        if not company:
            return
        existing_settings = frappe.db.get_value(
            doctype_name,
            {
                "company": company,
                "status": ["in", ["Active", "Pending Activation"]],
                "name": ["!=", source_name],
            },
            ["name", "status"],
            as_dict=True,
        )
        if existing_settings:
            settings_link = get_link_to_form(doctype_name, existing_settings.name)
            fthrow(
                _(
                    "Cannot duplicate configuration: Company {0} already has {1} settings: {2}. "
                    "Please withdraw or complete the existing configuration first."
                ).format(company, existing_settings.status, settings_link),
                title=_("Duplicate Configuration Not Allowed"),
            )

    def after_insert(self):
        invoice_counting_doc = frappe.new_doc("ZATCA Invoice Counting Settings")
        invoice_counting_doc.business_settings_reference = self.name
        invoice_counting_doc.invoice_counter = 0
        invoice_counting_doc.previous_invoice_hash = "NWZlY2ViNjZmZmM4NmYzOGQ5NTI3ODZjNmQ2OTZjNzljMmRiYzIzOWRkNGU5MWI0NjcyOWQ3M2EyN2ZiNTdlOQ=="
        invoice_counting_doc.insert(ignore_permissions=True)

    def before_insert(self):
        if self.automatic_vat_account_configuration == 1:
            # Create Tax Account under Duties and Taxes Account
            tax_account_id = self.create_tax_account()
            # Create Tax Category based on ZATCA Tax Category in business settings
            tax_category_id = self.create_zatca_tax_category()
            # Create Sales Taxes and Charges Template
            self.create_sales_taxes_and_charges_template(
                tax_category=tax_category_id, account_head=tax_account_id
            )
            # Create Item Tax Template
            self.create_item_tax_template(account_head=tax_account_id)

    @property
    def is_live_sync(self) -> bool:
        return self.sync_with_zatca.lower() == "live"

    @property
    def invoice_mode(self) -> InvoiceMode:
        return InvoiceMode.from_literal(self.type_of_business_transactions)

    @property
    def has_production_csid(self) -> bool:
        return (
            bool(self.production_security_token)
            and bool(self.production_secret)
            and bool(self.production_request_id)
        )

    @property
    def file_prefix(self) -> str:
        """
        Returns the prefix for generated ZATCA files related to this business settings instance (certificate, key, etc.)
        """
        return sanitize_filename(self.name)

    @property
    def cert_path(self) -> str:
        return ksa_compliance.zatca_files.get_cert_path(self.file_prefix)

    @property
    def compliance_cert_path(self) -> str:
        return ksa_compliance.zatca_files.get_compliance_cert_path(self.file_prefix)

    @property
    def private_key_path(self) -> str:
        if self.is_sandbox_server:
            return self._sandbox_private_key_path

        return ksa_compliance.zatca_files.get_private_key_path(self.file_prefix)

    @property
    def is_sandbox_server(self) -> bool:
        return self.fatoora_server_url.startswith(
            "https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal"
        )

    @property
    def is_simulation_server(self) -> bool:
        return self.fatoora_server_url.startswith(
            "https://gw-fatoora.zatca.gov.sa/e-invoicing/simulation"
        )

    @property
    def _sandbox_private_key_path(self) -> str:
        """
        Returns the path of the sandbox private key

        The sandbox environment returns a fixed certificate that corresponds to this private key. If we try to sign
        with the real private key, signature validation will fail
        """
        key = (
            "MHQCAQEEIL14JV+5nr/sE8Sppaf2IySovrhVBtt8+yz"
            "+g4NRKyz8oAcGBSuBBAAKoUQDQgAEoWCKa0Sa9FIErTOv0uAkC1VIKXxU9nPpx2vlf4yhMejy8c02XJblDq7tPydo8mq0ahOMmNo8gwni7Xt1KT9UeA=="
        )
        path = ksa_compliance.zatca_files.get_sandbox_private_key_path()
        if not os.path.isfile(path):
            with open(path, "wb") as f:
                f.write(key.encode("utf-8"))
        return path

    @property
    def fatoora_server_url(self) -> str:
        if self.fatoora_server == "Sandbox":
            return "https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal/"
        if self.fatoora_server == "Simulation":
            return "https://gw-fatoora.zatca.gov.sa/e-invoicing/simulation/"
        if self.fatoora_server == "Production":
            return "https://gw-fatoora.zatca.gov.sa/e-invoicing/core/"
        fthrow(
            f"Invalid Fatoora Server, Please update {self.company} Fatoora Server in ZATCA Business Settings"
        )

    def onboard(self, otp: str) -> NoReturn:
        """Creates a CSR and issues a compliance CSID request. On success, updates the document with the CSR,
        compliance request ID, as well as credentials (security token and secret).

        This is meant for consumption from Desk. It displays an error or a success dialog."""
        if not self.zatca_cli_path:
            fthrow(_("Please configure 'Zatca CLI Path'"))

        self._throw_if_api_config_missing()

        csr_result = self._generate_csr()
        compliance_result, status_code = api.get_compliance_csid(
            self.fatoora_server_url, csr_result.csr, otp
        )
        if is_err(compliance_result):
            fthrow(compliance_result.err_value, title=_("Compliance API Error"))

        self.csr = csr_result.csr
        self.security_token = compliance_result.ok_value.security_token
        self.secret = compliance_result.ok_value.secret
        self.compliance_request_id = compliance_result.ok_value.request_id
        self.save()

        with open(self.compliance_cert_path, "wb+") as cert:
            cert.write(b"-----BEGIN CERTIFICATE-----\n")
            cert.write(base64.b64decode(compliance_result.ok_value.security_token))
            cert.write(b"\n-----END CERTIFICATE-----")

        frappe.msgprint(_("Onboarding completed successfully"), title=_("Success"))

    def get_production_csid(self, otp: str) -> NoReturn:
        """Uses the compliance response to issue a production CSID. On success, updates the document with the CSID
        request ID and credentials.

        This is meant for consumption from Desk. It displays an error or a success dialog."""
        self._throw_if_api_config_missing()
        if not self.compliance_request_id:
            fthrow(_("Please onboard first to generate a 'Compliance Request ID'"))

        csid_result, status_code = api.get_production_csid(
            self.fatoora_server_url,
            self.compliance_request_id,
            otp,
            self.security_token,
            self.get_password("secret"),
        )
        if is_err(csid_result):
            fthrow(csid_result.err_value, title=_("Production CSID Error"))

        self.production_request_id = csid_result.ok_value.request_id
        self.production_security_token = csid_result.ok_value.security_token
        self.production_secret = csid_result.ok_value.secret
        self.status = "Active"
        self.save()

        with open(self.cert_path, "wb+") as cert:
            cert.write(b"-----BEGIN CERTIFICATE-----\n")
            cert.write(base64.b64decode(csid_result.ok_value.security_token))
            cert.write(b"\n-----END CERTIFICATE-----")

        frappe.msgprint(_("Production CSID generated successfully"), title=_("Success"))

    @property
    def csr_config(self) -> dict:
        if self.invoice_mode == InvoiceMode.Standard:
            invoice_type = "1000"
        elif self.invoice_mode == InvoiceMode.Simplified:
            invoice_type = "0100"
        else:
            invoice_type = "1100"

        return {
            "unit_common_name": self.company_unit,  # Review: Same as unit_name
            "unit_serial_number": self.company_unit_serial,
            "vat_number": self.vat_registration_number,
            "unit_name": self.company_unit or "Main Branch",  # Review: Use default value?
            "organization_name": self.seller_name,
            "country": self.country_code.upper(),
            "invoice_type": invoice_type,
            "address": self._format_address(),
            "category": self.company_category,
        }

    @staticmethod
    def for_invoice(
        invoice_id: str, doctype: Literal["Sales Invoice", "POS Invoice", "Payment Entry"]
    ) -> Optional["ZATCABusinessSettings"]:
        company_id = frappe.db.get_value(doctype, invoice_id, ["company"])
        if not company_id:
            return None
        invoice = frappe.get_doc(doctype, invoice_id)
        return ZATCABusinessSettings.for_company(company_id, invoice)

    @staticmethod
    def for_company(company_id: str, invoice=None) -> Optional["ZATCABusinessSettings"]:
        """Retrieves active business settings for a company"""
        filters = {
            "company": company_id,
        }
        if invoice and hasattr(invoice, "is_perform_compliance_checks"):
            filters["status"] = "Active"
        business_settings_id = frappe.db.get_value("ZATCA Business Settings", filters=filters)

        if not business_settings_id:
            return None

        return cast(
            ZATCABusinessSettings, frappe.get_doc("ZATCA Business Settings", business_settings_id)
        )

    @staticmethod
    def is_withdrawn_for_company(company_id: str) -> bool:
        """Checks if business settings have been withdrawn for a company"""
        filters = {"company": company_id, "status": "Withdrawn"}
        business_settings_id = frappe.db.get_value("ZATCA Business Settings", filters=filters)
        return bool(business_settings_id)

    @staticmethod
    def is_enabled_for_company(company_id: str) -> bool:
        """Checks if ZATCA integration is enabled and active for a company"""
        filters = {"company": company_id, "status": "Active", "enable_zatca_integration": True}
        return bool(frappe.db.get_value("ZATCA Business Settings", filters=filters))

    @staticmethod
    def is_branch_config_enabled(company_id: str) -> bool:
        """Checks if branch configuration is enabled for an active company"""
        filters = {"company": company_id, "status": "Active", "enable_branch_configuration": True}
        return bool(frappe.db.get_value("ZATCA Business Settings", filters=filters))

    def _generate_csr(self) -> cli.CsrResult:
        config = frappe.render_template(
            "ksa_compliance/templates/csr-config.properties", is_path=True, context=self.csr_config
        )

        logger.info(f"CSR config: {config}")
        return cli.generate_csr(
            self.zatca_cli_path,
            self.java_home,
            self.file_prefix,
            config,
            simulation=self.is_simulation_server,
        )

    def _format_address(self) -> str:
        """
        Formats an address for use in ZATCA in the form 'Building number, street, district, city'

        TODO: We should use a national short address instead (https://splonline.com.sa/en/national-address-1/) if
          available. It should be added to the Address doctype.
        """
        address = ""
        if self.building_number:
            address += self.building_number + " "

        address += self.street
        if self.district:
            address += ", " + self.district

        address += ", " + self.city
        return address

    def _throw_if_api_config_missing(self) -> None:
        if not self.fatoora_server_url:
            fthrow(_("Please configure 'Fatoora Server URL'"))

    def on_trash(self) -> NoReturn:
        fthrow(
            msg=_("You cannot Delete a configured ZATCA Business Settings"),
            title=_("This Action Is Not Allowed"),
        )

    def create_tax_account(self) -> str:
        account_doc = cast(Account, frappe.new_doc("Account"))

        # Since ERPNext Translates account_name "_" in _("Duties and Taxes") must be used to translate the account_name to current system language.
        parent_account = frappe.get_value(
            "Account", {"company": self.company, "account_name": _("Duties and Taxes")}, "name"
        )
        account_doc.parent_account = parent_account
        account_doc.company = self.company
        account_doc.account_name = self.account_name
        account_doc.account_number = self.account_number
        account_doc.account_type = "Tax"
        account_doc.tax_rate = self.tax_rate
        account_doc.insert(ignore_permissions=True)
        self.linked_tax_account = account_doc.name
        return account_doc.name

    def create_zatca_tax_category(self) -> str:
        tax_category_name = self.zatca_tax_category.split(" || ")[-1]
        tax_category_id = frappe.db.exists("Tax Category", tax_category_name)
        if tax_category_id:
            return tax_category_id
        tax_category_doc = cast(TaxCategory, frappe.new_doc("Tax Category"))
        tax_category_doc.title = tax_category_name
        tax_category_doc.custom_zatca_category = self.zatca_tax_category
        tax_category_doc.insert(ignore_permissions=True, ignore_mandatory=True)
        return tax_category_doc.name

    def create_sales_taxes_and_charges_template(self, tax_category: str, account_head: str):
        sales_taxes_and_charges_template_doc = cast(
            SalesTaxesandChargesTemplate, frappe.new_doc("Sales Taxes and Charges Template")
        )
        sales_taxes_and_charges_template_doc.title = f"VAT - {self.tax_rate}%"
        sales_taxes_and_charges_template_doc.company = self.company
        sales_taxes_and_charges_template_doc.tax_category = tax_category
        sales_taxes_and_charges_template_doc.append(
            "taxes",
            {
                "charge_type": "On Net Total",
                "account_head": account_head,
                "description": "VAT Account",
                "rate": self.tax_rate,
            },
        )
        sales_taxes_and_charges_template_doc.insert(ignore_permissions=True)

    def create_item_tax_template(self, account_head: str):
        item_tax_template_doc = cast(ItemTaxTemplate, frappe.new_doc("Item Tax Template"))
        item_tax_template_doc.title = f"VAT - {self.tax_rate}%"
        item_tax_template_doc.company = self.company
        item_tax_template_doc.custom_zatca_item_tax_category = self.zatca_tax_category
        item_tax_template_doc.append(
            "taxes", {"tax_type": account_head, "tax_rate": self.tax_rate}
        )
        item_tax_template_doc.insert(ignore_permissions=True, ignore_mandatory=True)


@frappe.whitelist()
def fetch_company_addresses(company_name):
    company_list_dict = frappe.get_all(
        "Dynamic Link", filters={"link_name": company_name}, fields=["parent"]
    )
    company_list = [address.parent for address in company_list_dict]
    return company_list


@frappe.whitelist()
def onboard(business_settings_id: str, otp: str) -> NoReturn:
    settings = cast(
        ZATCABusinessSettings, frappe.get_doc("ZATCA Business Settings", business_settings_id)
    )
    settings.onboard(otp)


@frappe.whitelist()
def get_production_csid(business_settings_id: str, otp: str) -> NoReturn:
    settings = cast(
        ZATCABusinessSettings, frappe.get_doc("ZATCA Business Settings", business_settings_id)
    )
    settings.get_production_csid(otp)


@frappe.whitelist()
def duplicate_configuration(source_name: str, target_doc=None):
    """Creates a new configuration from a withdrawn settings document, excluding credentials"""

    doctype_name = "ZATCA Business Settings"

    # Get company from source document
    source_doc = frappe.get_doc(doctype_name, source_name)
    company = source_doc.company

    # Check if company already has Active or Pending Activation settings
    # Use the new method for duplicate check
    temp_doc = frappe.new_doc(doctype_name)
    temp_doc.company = company
    temp_doc.name = source_name
    temp_doc.throw_if_duplicate_active_or_pending_settings()

    # Credential fields to exclude from duplication
    excluded_credential_fields = [
        "csr",
        "security_token",
        "secret",
        "compliance_request_id",
        "production_security_token",
        "production_secret",
        "production_request_id",
    ]

    mapping_config = {
        doctype_name: {
            "doctype": doctype_name,
            "field_no_map": excluded_credential_fields,
        },
        "Additional Seller IDs": {
            "doctype": "Additional Seller IDs",
            "field_map": {"type_name": "type_name", "type_code": "type_code", "value": "value"},
        },
    }

    new_doc = get_mapped_doc(doctype_name, source_name, mapping_config, target_doc)
    return new_doc


@frappe.whitelist()
def withdraw_settings(settings_id: str, company: str):
    """Withdraws ZATCA integration for a business settings configuration"""

    # Validate no pending invoices before withdrawal
    SalesInvoice = frappe.qb.DocType("Sales Invoice")
    POSInvoice = frappe.qb.DocType("POS Invoice")
    JournalEntry = frappe.qb.DocType("Journal Entry")
    PaymentEntry = frappe.qb.DocType("Payment Entry")
    AdditionalFields = frappe.qb.DocType("Sales Invoice Additional Fields")

    query = (
        frappe.qb.from_(AdditionalFields)
        .select(Count(AdditionalFields.name).as_("pending_count"))
        .left_join(SalesInvoice)
        .on(SalesInvoice.name == AdditionalFields.sales_invoice)
        .left_join(POSInvoice)
        .on(POSInvoice.name == AdditionalFields.sales_invoice)
        .left_join(JournalEntry)
        .on(JournalEntry.name == AdditionalFields.sales_invoice)
        .left_join(PaymentEntry)
        .on(PaymentEntry.name == AdditionalFields.sales_invoice)
        .where(
            (
                (AdditionalFields.invoice_doctype == "Sales Invoice")
                & (SalesInvoice.company == company)
            )
            | (
                (AdditionalFields.invoice_doctype == "POS Invoice")
                & (POSInvoice.company == company)
            )
            | (
                (AdditionalFields.invoice_doctype == "Journal Entry")
                & (JournalEntry.company == company)
            )
            | (
                (AdditionalFields.invoice_doctype == "Payment Entry")
                & (PaymentEntry.company == company)
            )
        )
        .where(AdditionalFields.docstatus == 0)
    )

    result = query.run(as_dict=True)
    pending_invoice_count = result[0]["pending_count"] if result else 0

    if pending_invoice_count > 0:
        # Build error message with helpful links
        sync_url = get_url(uri="/app/e-invoicing-sync")
        sync_link = f'<a href="{sync_url}">{ft("Sync Invoices Page")}</a>'

        list_url = get_url_to_list("Sales Invoice Additional Fields")
        pending_link = f'<a href="{list_url}?docstatus=0">{ft("pending invoice(s)")}</a>'

        fthrow(
            msg=ft(
                "Cannot withdraw: $num $pending_link require synchronization. "
                "Please sync all pending invoices using the $sync_link before withdrawing.",
                num=pending_invoice_count,
                pending_link=pending_link,
                sync_link=sync_link,
            ),
            title=ft("Pending Invoices Found"),
        )

    # Update status to Withdrawn
    settings_doc = frappe.get_doc("ZATCA Business Settings", settings_id)
    settings_doc.status = "Withdrawn"
    settings_doc.save()

    frappe.msgprint(
        _("ZATCA integration has been successfully withdrawn."),
        title=_("Withdrawn Successfully"),
    )
