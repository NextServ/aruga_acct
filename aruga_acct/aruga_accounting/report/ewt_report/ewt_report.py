import frappe
from frappe.utils import getdate
from erpnext.accounts.utils import get_fiscal_year


# Fixed set of ATCs required by the user/file template
TARGET_ATCS = [
    "WV010", "WC158", "WC160", "WC120", "WC157", "WV020", "WC640"
]


def execute(filters=None):
    filters = frappe._dict(filters or {})
    rows = get_data(filters)
    columns = get_columns()
    return columns, rows


def get_columns():
    columns = [
        {"label": "TIN #", "fieldname": "tin", "fieldtype": "Data", "width": 120},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 140},
        {"label": "Branch", "fieldname": "branch", "fieldtype": "Data", "width": 120},
        {"label": "Name of Customer", "fieldname": "customer", "fieldtype": "Data", "width": 200},
        {"label": "Manual Doc No.", "fieldname": "manual_doc_no", "fieldtype": "Data", "width": 130},
        {"label": "Invoice No.", "fieldname": "invoice_no", "fieldtype": "Link", "options": "Purchase Invoice", "width": 140},
        {"label": "Payment Entry", "fieldname": "payment_entry", "fieldtype": "Link", "options": "Payment Entry", "width": 140},
        {"label": "Invoice Date", "fieldname": "invoice_date", "fieldtype": "Date", "width": 110},
        {"label": "Due Date", "fieldname": "due_date", "fieldtype": "Date", "width": 110},
        {"label": "Period From", "fieldname": "period_from", "fieldtype": "Date", "width": 110},
        {"label": "Invoice Amount", "fieldname": "invoice_amount", "fieldtype": "Currency", "width": 130},
    ]

    for atc in TARGET_ATCS:
        columns.append({
            "label": atc,
            "fieldname": atc.lower(),
            "fieldtype": "Currency",
            "width": 110
        })

    columns.append({"label": "Fiscal Year", "fieldname": "fiscal_year", "fieldtype": "Data", "width": 110})

    return columns


def get_data(filters):
    # Exclude debit/credit notes unless explicitly unchecked
    exclude_returns = filters.get("exclude_credit_notes", 1)

    base_filters = {
        "docstatus": 1,
        "posting_date": ["between", [getdate(filters.from_date), getdate(filters.to_date)]],
        "company": filters.company,
    }

    if exclude_returns:
        base_filters["is_return"] = 0

    has_manual_doc = frappe.db.has_column("Purchase Invoice", "custom_manual_doc_no")
    has_branch = frappe.db.has_column("Purchase Invoice", "branch")

    fields = [
        "name",
        "posting_date",
        "due_date",
        "company",
        "supplier",
        "base_grand_total",
        "tax_id",
    ]

    if has_manual_doc:
        fields.append("custom_manual_doc_no as manual_doc_no")
    if has_branch:
        fields.append("branch")

    invoices = frappe.get_all(
        "Purchase Invoice",
        filters=base_filters,
        fields=fields,
        order_by="posting_date asc, name asc",
    )

    data = []

    for inv in invoices:
        supplier_info = frappe.db.get_value(
            "Supplier", inv.supplier, ["supplier_name", "tax_id"], as_dict=True
        ) or {}

        payment_entry = frappe.db.get_value(
            "Payment Entry Reference",
            {"reference_doctype": "Purchase Invoice", "reference_name": inv.name},
            "parent",
        )

        row = {
            "tin": inv.tax_id or supplier_info.get("tax_id") or "",
            "company": inv.company,
            "branch": getattr(inv, "branch", ""),
            "customer": supplier_info.get("supplier_name") or inv.supplier,
            "manual_doc_no": getattr(inv, "manual_doc_no", "") or getattr(inv, "custom_manual_doc_no", ""),
            "invoice_no": inv.name,
            "payment_entry": payment_entry or "",
            "invoice_date": inv.posting_date,
            "due_date": inv.due_date,
            "period_from": filters.get("from_date") or inv.posting_date,
            "invoice_amount": inv.base_grand_total,
            "fiscal_year": get_fiscal_year(inv.posting_date, company=inv.company)[0],
        }

        atc_rows = frappe.get_all(
            "Purchase Taxes and Charges",
            filters={"parent": inv.name, "atc": ["in", TARGET_ATCS]},
            fields=["atc", "tax_amount"],
        )

        for atc_row in atc_rows:
            fieldname = atc_row.atc.lower()
            row[fieldname] = abs(atc_row.tax_amount or 0)

        data.append(row)

    return data
