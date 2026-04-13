import frappe
from frappe.utils import getdate
from frappe import _

def execute(filters=None):
    columns, data = [], []
    data = get_data(filters)
    columns = get_columns()
    return columns, data

def get_data(filters):
    # Extract filters
    company = filters.get("company")
    year = filters.get("year")
    quarter = filters.get("quarter")

    if not company or not year or not quarter:
        frappe.throw(_("Company, Year, and Quarter are required filters"))

    # Replicate the SQL query from bir_1601_fq
    data = frappe.db.sql("""
        SELECT 
            temp.atc,
            temp.base_tax_base,
            a.rate AS tax_rate,
            temp.base_tax_withheld
        FROM
            (
            SELECT 
                source.atc AS atc,
                SUM(source.base_total) AS base_tax_base,
                SUM(ABS(source.base_tax_amount)) AS base_tax_withheld
            FROM
                (
                SELECT 
                    ptac.atc,
                    pi.base_net_total AS base_total,
                    ptac.base_tax_amount
                FROM 
                    `tabPurchase Invoice` pi
                LEFT JOIN
                    `tabPurchase Taxes and Charges` ptac
                ON
                    pi.name = ptac.parent
                INNER JOIN
                    `tabAccount` a
                ON
                    ptac.account_head = a.name
                WHERE
                    pi.docstatus = 1
                    AND pi.is_return = 0
                    AND ((ptac.base_tax_amount < 0 AND ptac.add_deduct_tax != 'Deduct') OR (ptac.base_tax_amount >= 0 AND ptac.add_deduct_tax = 'Deduct'))
                    AND (a.account_type IN ('Tax', 'Payable', '') OR a.account_type IS NULL)
                    AND pi.company = %s
                    AND YEAR(pi.posting_date) = %s
                    AND QUARTER(pi.posting_date) = %s
                UNION ALL
                SELECT 
                    atac.atc,
                    pe.base_paid_amount_after_tax AS base_total,
                    atac.base_tax_amount
                FROM
                    `tabPayment Entry` pe
                LEFT JOIN
                    `tabAdvance Taxes and Charges` atac
                ON
                    pe.name = atac.parent
                INNER JOIN
                    `tabAccount` a
                ON
                    atac.account_head = a.name
                WHERE
                    pe.docstatus = 1
                    AND pe.payment_type = 'Pay'
                    AND pe.party_type = 'Supplier'
                    AND ((atac.base_tax_amount < 0 AND atac.add_deduct_tax != 'Deduct') OR (atac.base_tax_amount >= 0 AND atac.add_deduct_tax = 'Deduct'))
                    AND (a.account_type IN ('Tax', 'Payable', '') OR a.account_type IS NULL)
                    AND pe.company = %s
                    AND YEAR(pe.posting_date) = %s
                    AND QUARTER(pe.posting_date) = %s
                ) source
            GROUP BY
                source.atc
            ) AS temp
        INNER JOIN 
            `tabATC` AS a
        ON
            temp.atc = a.name
        # WHERE
        #     a.form_type = '2306'
    """, (company, year, quarter, company, year, quarter), as_dict=1)

    # Format tax_rate and add tax_still_due, total_amount_still_due for all rows
    for row in data:
        gross_tax_base = row.get("base_tax_base") or 0
        tax_withheld = row.get("base_tax_withheld") or 0
        row["base_tax_base"] = gross_tax_base - tax_withheld

        if row.get("tax_rate") is not None:
            row["tax_rate"] = f"{int(row['tax_rate'])}%"
        else:
            row["tax_rate"] = "-"  # Handle null tax_rate

        # Add tax_still_due and total_amount_still_due for non-total rows
        row["tax_still_due"] = ""
        row["total_amount_still_due"] = ""

    # Calculate totals
    total_taxes_withheld = sum(entry.get("base_tax_withheld", 0) for entry in data)
    total_remittances_made = 0  # Adjust if you have logic to calculate this
    tax_still_due = total_taxes_withheld - total_remittances_made
    total_penalties = 0  # Adjust if you have logic to calculate this
    total_amount_still_due = tax_still_due + total_penalties

    # Add totals row with bold flag for styling
    data.append({
        "atc": "Total",
        "base_tax_base": " ",  # Dash for null
        "tax_rate": "",  # Dash for null
        "base_tax_withheld": total_taxes_withheld,
        "tax_still_due": tax_still_due,
        "total_amount_still_due": total_amount_still_due,
        "bold": 1  # Used for conditional styling in formatter
    })

    return data

def get_columns():
    columns = [
        {
            "fieldname": "atc",
            "label": _("ATC Code"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "base_tax_base",
            "label": _("Tax Base"),
            "fieldtype": "Data",  # Use Data to support dash
            "width": 150
        },
        {
            "fieldname": "tax_rate",
            "label": _("Tax Rate (%)"),
            "fieldtype": "Data",  # Use Data for string with percent sign
            "width": 150
        },
        {
            "fieldname": "base_tax_withheld",
            "label": _("Tax Withheld"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "tax_still_due",
            "label": _("Tax Still Due"),
            "fieldtype": "Data",  # Changed to Data to support dash
            "width": 150
        },
        {
            "fieldname": "total_amount_still_due",
            "label": _("Total Amount Still Due"),
            "fieldtype": "Data",  # Changed to Data to support dash
            "width": 150
        }
    ]
    return columns