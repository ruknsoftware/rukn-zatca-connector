import frappe
from frappe.utils import now_datetime

def custom_erpnext_setup():
	frappe.clear_cache()
	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	if not frappe.db.a_row_exists("Company"):
		current_year = now_datetime().year
		setup_complete(
            {
                "currency": "SAR",
                "company_name": "_Test KSA Company",
                "country": "Saudi Arabia",                
                "full_name": "Test User",
                "timezone": "Asia/Riyadh",
                "company_abbr": "_TKC",
                "industry": "Manufacturing",
                "fy_start_date": f"{current_year}-01-01",
                "fy_end_date": f"{current_year}-12-31",
                "language": "english",
                "company_tagline": "ZATCA Testing",
                "email": "test@example.com",
                "password": "test",
                "chart_of_accounts": "Standard",
            }
		)

	frappe.db.sql("delete from `tabItem Price`")

	frappe.db.commit()