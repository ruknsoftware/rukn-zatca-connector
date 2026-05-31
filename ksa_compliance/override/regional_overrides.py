from ksa_compliance.override.taxes_and_totals import (
    calculate_taxes_and_totals as calculate_taxes_and_totals_class,
)


def calculate_taxes_and_totals_round(doc):
    calculate_taxes_and_totals_class(doc)

    if doc.doctype in (
        "Sales Order",
        "Delivery Note",
        "Sales Invoice",
        "POS Invoice",
    ):
        doc.calculate_commission()
        doc.calculate_contribution()
