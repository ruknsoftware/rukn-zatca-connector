import xml.etree.ElementTree as ET


def parse_xml_to_dict(xml_string):
    NAMESPACES = {
        "": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
        "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    }

    root = ET.fromstring(xml_string)

    def get_text(node, path):
        if node is None:
            return None
        elem = node.find(path, NAMESPACES)
        if elem is not None and elem.text:
            text = elem.text.strip()
            if text.startswith("{{") and "no such element" in text.lower():
                return None
            return text
        return None

    def get_scheme_name(scheme_id):
        mapping = {
            "CRN": "Commercial Registration Number",
            "MOM": "Momra Identification",
            "MLSD": "MLSD Identification",
            "700": "700 Number",
            "SAG": "SAGIA Identification",
            "NAT": "National ID",
            "GCC": "GCC ID",
            "IQA": "Iqama Number",
            "PAS": "Passport ID",
            "OTH": "Other ID",
        }
        return mapping.get(scheme_id, scheme_id)

    data = {"invoice": {}, "seller_details": {}, "buyer_details": {}, "business_settings": {}}

    # Invoice Data
    data["invoice"]["id"] = get_text(root, "./cbc:ID")
    data["invoice"]["uuid"] = get_text(root, "./cbc:UUID")
    data["invoice"]["issue_date"] = get_text(root, "./cbc:IssueDate")
    data["invoice"]["issue_time"] = get_text(root, "./cbc:IssueTime")
    data["invoice"]["invoice_type_code"] = get_text(root, "./cbc:InvoiceTypeCode")
    elem = root.find("./cbc:InvoiceTypeCode", NAMESPACES)
    data["invoice"]["invoice_type_transaction"] = elem.get("name") if elem is not None else None

    data["invoice"]["currency_code"] = get_text(root, "./cbc:DocumentCurrencyCode")
    data["invoice"]["tax_currency"] = get_text(root, "./cbc:TaxCurrencyCode")

    data["invoice"]["purchase_order_reference"] = get_text(root, "./cac:OrderReference/cbc:ID")

    # Billing References
    billing_refs = []
    for br in root.findall("./cac:BillingReference/cac:InvoiceDocumentReference", NAMESPACES):
        billing_refs.append(get_text(br, "./cbc:ID"))
    data["invoice"]["billing_references"] = billing_refs

    # Additional Doc References (ICV, PIH, QR)
    for ref in root.findall("./cac:AdditionalDocumentReference", NAMESPACES):
        ref_id = get_text(ref, "./cbc:ID")
        if ref_id == "ICV":
            data["invoice"]["invoice_counter_value"] = get_text(ref, "./cbc:UUID")
        elif ref_id == "PIH":
            data["invoice"]["pih"] = get_text(
                ref, "./cac:Attachment/cbc:EmbeddedDocumentBinaryObject"
            )
        elif ref_id == "QR":
            data["invoice"]["qr_code"] = get_text(
                ref, "./cac:Attachment/cbc:EmbeddedDocumentBinaryObject"
            )

    # Seller
    seller = root.find("./cac:AccountingSupplierParty/cac:Party", NAMESPACES)
    if seller is not None:
        data["seller_details"]["street_name"] = get_text(
            seller, "./cac:PostalAddress/cbc:StreetName"
        )
        data["seller_details"]["building_number"] = get_text(
            seller, "./cac:PostalAddress/cbc:BuildingNumber"
        )
        data["seller_details"]["address_additional_number"] = get_text(
            seller, "./cac:PostalAddress/cbc:PlotIdentification"
        )
        data["seller_details"]["city_subdivision_name"] = get_text(
            seller, "./cac:PostalAddress/cbc:CitySubdivisionName"
        )
        data["seller_details"]["city_name"] = get_text(seller, "./cac:PostalAddress/cbc:CityName")
        data["seller_details"]["postal_zone"] = get_text(
            seller, "./cac:PostalAddress/cbc:PostalZone"
        )
        data["seller_details"]["province"] = get_text(
            seller, "./cac:PostalAddress/cbc:CountrySubentity"
        )
        data["seller_details"]["country_code"] = get_text(
            seller, "./cac:PostalAddress/cac:Country/cbc:IdentificationCode"
        )

        tax_scheme = seller.find("./cac:PartyTaxScheme", NAMESPACES)
        if tax_scheme is not None:
            scheme_id = get_text(tax_scheme, "./cac:TaxScheme/cbc:ID")
            company_id = get_text(tax_scheme, "./cbc:CompanyID")
            if scheme_id == "VAT":
                data["business_settings"]["company_id"] = company_id
            else:
                data["seller_details"]["party_identifications"] = {scheme_id: company_id}

        pid = seller.find("./cac:PartyIdentification", NAMESPACES)
        if pid is not None:
            pid_elem = pid.find("./cbc:ID", NAMESPACES)
            if pid_elem is not None:
                scheme = pid_elem.get("schemeID")
                val = pid_elem.text
                if "party_identifications" not in data["seller_details"]:
                    data["seller_details"]["party_identifications"] = {}
                data["seller_details"]["party_identifications"][scheme] = val
                data["seller_details"]["other_id_name"] = get_scheme_name(scheme)
                data["seller_details"]["other_id_value"] = val

        data["business_settings"]["registration_name"] = get_text(
            seller, "./cac:PartyLegalEntity/cbc:RegistrationName"
        )

    # Buyer
    buyer = root.find("./cac:AccountingCustomerParty/cac:Party", NAMESPACES)
    if buyer is not None:
        data["buyer_details"]["street_name"] = get_text(
            buyer, "./cac:PostalAddress/cbc:StreetName"
        )
        data["buyer_details"]["building_number"] = get_text(
            buyer, "./cac:PostalAddress/cbc:BuildingNumber"
        )
        data["buyer_details"]["address_additional_number"] = get_text(
            buyer, "./cac:PostalAddress/cbc:PlotIdentification"
        )
        data["buyer_details"]["city_subdivision_name"] = get_text(
            buyer, "./cac:PostalAddress/cbc:CitySubdivisionName"
        )
        data["buyer_details"]["city_name"] = get_text(buyer, "./cac:PostalAddress/cbc:CityName")
        data["buyer_details"]["postal_zone"] = get_text(
            buyer, "./cac:PostalAddress/cbc:PostalZone"
        )
        data["buyer_details"]["province"] = get_text(
            buyer, "./cac:PostalAddress/cbc:CountrySubentity"
        )
        data["buyer_details"]["country_code"] = get_text(
            buyer, "./cac:PostalAddress/cac:Country/cbc:IdentificationCode"
        )

        tax_scheme = buyer.find("./cac:PartyTaxScheme", NAMESPACES)
        if tax_scheme is not None:
            data["buyer_details"]["company_id"] = get_text(tax_scheme, "./cbc:CompanyID")

        pid = buyer.find("./cac:PartyIdentification", NAMESPACES)
        if pid is not None:
            pid_elem = pid.find("./cbc:ID", NAMESPACES)
            if pid_elem is not None:
                scheme = pid_elem.get("schemeID")
                val = pid_elem.text
                data["buyer_details"]["party_identifications"] = {scheme: val}
                data["buyer_details"]["other_id_name"] = get_scheme_name(scheme)
                data["buyer_details"]["other_id_value"] = val

        data["buyer_details"]["registration_name"] = get_text(
            buyer, "./cac:PartyLegalEntity/cbc:RegistrationName"
        )

    data["invoice"]["delivery_date"] = get_text(root, "./cac:Delivery/cbc:ActualDeliveryDate")
    data["invoice"]["payment_means_type_code"] = get_text(
        root, "./cac:PaymentMeans/cbc:PaymentMeansCode"
    )
    data["invoice"]["instruction_note"] = get_text(root, "./cac:PaymentMeans/cbc:InstructionNote")

    # Totals
    lmt = root.find("./cac:LegalMonetaryTotal", NAMESPACES)
    if lmt is not None:
        data["invoice"]["line_extension_amount"] = get_text(lmt, "./cbc:LineExtensionAmount")
        data["invoice"]["net_total"] = get_text(lmt, "./cbc:TaxExclusiveAmount")
        data["invoice"]["grand_total"] = get_text(lmt, "./cbc:TaxInclusiveAmount")
        data["invoice"]["allowance_total_amount"] = get_text(lmt, "./cbc:AllowanceTotalAmount")
        data["invoice"]["rounding_adjustment"] = get_text(lmt, "./cbc:PayableRoundingAmount")
        data["invoice"]["payable_amount"] = get_text(lmt, "./cbc:PayableAmount")

    tax_totals = root.findall("./cac:TaxTotal", NAMESPACES)
    if tax_totals:
        data["invoice"]["total_taxes_and_charges"] = get_text(tax_totals[0], "./cbc:TaxAmount")
        if len(tax_totals) > 1:
            data["invoice"]["base_total_taxes_and_charges"] = get_text(
                tax_totals[1], "./cbc:TaxAmount"
            )

        tax_categories = []
        for st in tax_totals[0].findall("./cac:TaxSubtotal", NAMESPACES):
            tc = st.find("./cac:TaxCategory", NAMESPACES)
            tax_categories.append(
                {
                    "taxable_amount": get_text(st, "./cbc:TaxableAmount"),
                    "tax_amount": get_text(st, "./cbc:TaxAmount"),
                    "tax_category_code": get_text(tc, "./cbc:ID"),
                    "tax_percent": get_text(tc, "./cbc:Percent"),
                    "tax_exemption_reason_code": get_text(tc, "./cbc:TaxExemptionReasonCode"),
                    "tax_exemption_reason": get_text(tc, "./cbc:TaxExemptionReason"),
                }
            )
        data["invoice"]["tax_categories"] = tax_categories

    # Items and Prepayments
    item_lines = []
    prepayment_info = []
    for line in root.findall("./cac:InvoiceLine", NAMESPACES):
        qty = get_text(line, "./cbc:InvoicedQuantity")
        if qty in ["0.000000", "0.0"]:
            # Prepayment line
            doc_ref = get_text(line, "./cac:DocumentReference/cbc:ID")
            tax_subtotal = line.find("./cac:TaxTotal/cac:TaxSubtotal", NAMESPACES)
            taxable_amt = (
                get_text(tax_subtotal, "./cbc:TaxableAmount")
                if tax_subtotal is not None
                else "0.0"
            )
            tax_amt = (
                get_text(tax_subtotal, "./cbc:TaxAmount") if tax_subtotal is not None else "0.0"
            )
            tax_percent = (
                get_text(tax_subtotal, "./cac:TaxCategory/cbc:Percent")
                if tax_subtotal is not None
                else "0.0"
            )
            prepayment_data = {
                "idx": get_text(line, "./cbc:ID"),
                "advance_payment_invoice": doc_ref,
                "amount": taxable_amt,
                "tax_amount": tax_amt,
                "tax_percent": tax_percent,
                "allocated_amount": str(float(taxable_amt or 0) + float(tax_amt or 0)),
            }
            prepayment_info.append(prepayment_data)
            continue

        item_data = {
            "idx": get_text(line, "./cbc:ID"),
            "qty": qty,
            "amount": get_text(line, "./cbc:LineExtensionAmount"),
            "tax_amount": get_text(line, "./cac:TaxTotal/cbc:TaxAmount"),
            "total_amount": get_text(line, "./cac:TaxTotal/cbc:RoundingAmount"),
            "item_name": get_text(line, "./cac:Item/cbc:Name"),
            "tax_category_code": get_text(line, "./cac:Item/cac:ClassifiedTaxCategory/cbc:ID"),
            "tax_percent": get_text(line, "./cac:Item/cac:ClassifiedTaxCategory/cbc:Percent"),
            "tax_exemption_reason_code": get_text(
                line, "./cac:Item/cac:ClassifiedTaxCategory/cbc:TaxExemptionReasonCode"
            ),
            "tax_exemption_reason": get_text(
                line, "./cac:Item/cac:ClassifiedTaxCategory/cbc:TaxExemptionReason"
            ),
            "rate": "0.0",
        }
        price = line.find("./cac:Price", NAMESPACES)
        if price is not None:
            item_data["rate"] = get_text(price, "./cbc:PriceAmount")
            allowance = price.find("./cac:AllowanceCharge", NAMESPACES)
            if allowance is not None:
                item_data["discount_amount"] = get_text(allowance, "./cbc:Amount")
                item_data["base_amount"] = get_text(allowance, "./cbc:BaseAmount")
        item_lines.append(item_data)

    data["invoice"]["item_lines"] = item_lines
    data["invoice"]["prepayment_info"] = prepayment_info

    return data
