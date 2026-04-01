import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field


def execute():
    add_manual_doc_no_field()
    add_branch_field()


def add_manual_doc_no_field():
    if frappe.db.exists("Custom Field", {"dt": "Purchase Invoice", "fieldname": "custom_manual_doc_no"}):
        return

    create_custom_field("Purchase Invoice", {
        "label": "Manual Doc No.",
        "fieldname": "custom_manual_doc_no",
        "fieldtype": "Data",
        "insert_after": "title",
        "reqd": 0,
    })


def add_branch_field():
    if frappe.db.exists("Custom Field", {"dt": "Purchase Invoice", "fieldname": "branch"}):
        return

    create_custom_field("Purchase Invoice", {
        "label": "Branch",
        "fieldname": "branch",
        "fieldtype": "Data",
        "insert_after": "custom_manual_doc_no",
        "reqd": 0,
    })
