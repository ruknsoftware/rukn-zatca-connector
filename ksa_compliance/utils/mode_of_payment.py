import frappe

def set_zatca_code_on_default_mop(doc, method):
    payment_code_map = {
        "Cash": "10",          
        "Cheque": "20",      
        "Credit Card": "54",  
        "Wire Transfer": "30", #Credit transfer
        "Bank Draft": "21"     
    }

    if not doc.custom_zatca_payment_means_code:
        zatca_code = payment_code_map.get(doc.mode_of_payment)
        if zatca_code:
            doc.custom_zatca_payment_means_code = zatca_code
