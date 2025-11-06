import frappe

def execute(filters=None):
    # Step 1: Get all invoice data with ATC info (respect filter for credit notes)
    invoices, atc_usage = get_data(filters)

    # Step 2: Build columns dynamically based on used ATCs
    columns = get_columns(atc_usage)

    return columns, invoices


def get_columns(used_atcs):
    columns = [
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Data", "width": 180},
        {"label": "TIN", "fieldname": "tin", "fieldtype": "Data", "width": 130},
        {"label": "Invoice No", "fieldname": "invoice_no", "fieldtype": "Link", "options": "Sales Invoice", "width": 140},
        {"label": "Invoice Date", "fieldname": "invoice_date", "fieldtype": "Date", "width": 110},
        {"label": "Due Date", "fieldname": "due_date", "fieldtype": "Date", "width": 110},
        {"label": "Payment Entry", "fieldname": "payment_entry", "fieldtype": "Link", "options": "Payment Entry", "width": 140},
        {"label": "Invoice Amount", "fieldname": "invoice_amount", "fieldtype": "Currency", "width": 130}
    ]

    # Only include ATC columns that actually appeared in invoices
    for atc in used_atcs:
        columns.append({
            "label": atc,
            "fieldname": atc.lower().replace("-", "_"),
            "fieldtype": "Currency",
            "width": 120
        })

    return columns


def get_data(filters):
    # Default: exclude credit notes unless checkbox is unchecked
    exclude_credit_notes = filters.get("exclude_credit_notes")

    invoice_filters = {"docstatus": 1}

    if exclude_credit_notes:
        invoice_filters["is_return"] = 0  # Exclude credit notes
    # else: include all (no filter for is_return)

    invoices_raw = frappe.get_all(
        "Sales Invoice",
        fields=["name", "customer", "posting_date", "due_date", "base_grand_total"],
        filters=invoice_filters
    )

    data = []
    used_atcs = set()  # Track only the ATCs that have non-zero or existing values

    for inv in invoices_raw:
        customer_info = frappe.db.get_value("Customer", inv.customer, ["tax_id"], as_dict=True)
        payment_entry = frappe.db.get_value("Payment Entry Reference", {"reference_name": inv.name}, "parent")

        row = {
            "customer": inv.customer,
            "tin": customer_info.tax_id if customer_info else "",
            "invoice_no": inv.name,
            "invoice_date": inv.posting_date,
            "due_date": inv.due_date,
            "payment_entry": payment_entry or "",
            "invoice_amount": inv.base_grand_total
        }

        # Fetch ATC charges (non-empty only)
        atc_items = frappe.get_all(
            "Sales Taxes and Charges",
            filters={"parent": inv.name},
            fields=["atc", "tax_amount"]
        )

        for atc in atc_items:
            if atc.atc and atc.tax_amount:
                key = atc.atc.lower().replace("-", "_")
                row[key] = atc.tax_amount
                used_atcs.add(atc.atc)

        data.append(row)

    return data, used_atcs
