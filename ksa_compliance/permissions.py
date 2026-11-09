import frappe

ZATCA_WORKSPACE = "ZATCA"


def has_app_permission() -> bool:
    """Show the ZATCA tile on /apps only to users who can open the ZATCA workspace."""
    from frappe.desk.desktop import Workspace

    try:
        # Same check the desk sidebar uses: workspace roles, custom page roles and module access
        return bool(Workspace({"name": ZATCA_WORKSPACE}, minimal=True).is_permitted())
    except (frappe.DoesNotExistError, frappe.PermissionError):
        # v14/v15 raise PermissionError from Workspace() when the user's module is blocked
        frappe.clear_last_message()
        return False
