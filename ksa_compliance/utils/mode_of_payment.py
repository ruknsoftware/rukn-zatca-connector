import frappe

def set_zatca_code_on_default_mop(doc, method):

    default_modes = ["Cash", "Cheque", "Credit Card", "Wire Transfer", "Bank Draft"]
    
    if doc.mode_of_payment in default_modes and not doc.custom_zatca_payment_means_code:
        doc.custom_zatca_payment_means_code = "4461"