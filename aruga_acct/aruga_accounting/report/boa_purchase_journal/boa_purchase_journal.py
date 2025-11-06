# Copyright (c) 2013, SERVIO Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import (getdate)
from frappe import _

def execute(filters=None):
    columns, data = [], []
    data = get_data(filters)
    columns = get_columns()
    return columns, data

def get_data(filters):
    result = []

    data_pi = frappe.db.sql("""
    SELECT 
        pi.posting_date, 
        (CASE WHEN IFNULL(pi.tax_id, '') = '' THEN s.tax_id ELSE pi.tax_id END) AS tax_id,
        pi.supplier,
        s.supplier_name,
        /* pi.supplier_address, */
        pi.name,
        pi.currency,
        pi.is_return,
        pi.bill_no,
        (pi.base_net_total + pi.base_discount_amount) as total,
        (pi.base_discount_amount) as net_discount,
        IFNULL(ptac_totals.base_taxes_and_charges_added, 0) as tax_amount,
        IFNULL(ptac_totals.base_taxes_and_charges_deducted, 0) as withholding_tax_amount,
        pi.base_grand_total as grand_total
    FROM
        `tabPurchase Invoice` pi
    LEFT JOIN
        `tabSupplier` s
    ON 
        pi.supplier = s.name
    LEFT JOIN
        (
            SELECT 
                ptac.parent,
                SUM(ABS(
                    CASE 
                    WHEN (ptac.base_tax_amount > 0 and ptac.add_deduct_tax = 'Add') or (ptac.base_tax_amount < 0 and ptac.add_deduct_tax = 'Deduct') 
                        THEN ptac.base_tax_amount 
                    ELSE 
                        0 
                    END)) AS base_taxes_and_charges_added,
                SUM(ABS(
                    CASE 
                    WHEN (ptac.base_tax_amount < 0 and ptac.add_deduct_tax = 'Add') or (ptac.base_tax_amount > 0 and ptac.add_deduct_tax = 'Deduct') 
                        THEN ptac.base_tax_amount 
                    ELSE 
                        0 
                    END)) AS base_taxes_and_charges_deducted
            FROM
                `tabPurchase Taxes and Charges` ptac
            /*LEFT JOIN
                `tabPurchase Invoice` parent
            ON
                ptac.parent = parent.name
            WHERE
                parent.docstatus = 1
                and parent.is_return = 0*/
            INNER JOIN
                `tabAccount` a
            ON
                ptac.account_head = a.name
            WHERE (a.account_type in ('Tax', 'Payable', '') or a.account_type is NULL)
            GROUP BY ptac.parent
        ) AS ptac_totals
    ON 
        pi.name = ptac_totals.parent
    WHERE
        pi.docstatus = 1
        and pi.is_return = 0
        and pi.posting_date >= %s
        and pi.posting_date <= %s
        and pi.company = %s
    """, (getdate(filters.from_date), getdate(filters.to_date), filters.company), as_dict=1)

    result.extend(data_pi)

    # separate return query for simplicity
    data_return = frappe.db.sql("""
    SELECT 
        pi.posting_date, 
        (CASE WHEN IFNULL(pi.tax_id, '') = '' THEN s.tax_id ELSE pi.tax_id END) AS tax_id,
        pi.supplier,
        s.supplier_name,
        /* pi.supplier_address, */
        pi.name,
        pi.currency,
        pi.is_return,
        pi.bill_no,
        (pi.base_net_total + pi.base_discount_amount) as total,
        (pi.base_discount_amount) as net_discount,
        IFNULL(-ptac_totals.base_taxes_and_charges_added, 0) as tax_amount,
        IFNULL(-ptac_totals.base_taxes_and_charges_deducted, 0) as withholding_tax_amount,
        pi.base_grand_total as grand_total
    FROM
        `tabPurchase Invoice` pi
    LEFT JOIN
        `tabSupplier` s
    ON 
        pi.supplier = s.name
    LEFT JOIN
        (
            SELECT 
                ptac.parent,
                SUM(ABS(
                    CASE 
                    WHEN (ptac.base_tax_amount < 0 and ptac.add_deduct_tax = 'Add') or (ptac.base_tax_amount > 0 and ptac.add_deduct_tax = 'Deduct') 
                        THEN ptac.base_tax_amount 
                    ELSE 
                        0 
                    END)) AS base_taxes_and_charges_added,
                SUM(ABS(
                    CASE 
                    WHEN (ptac.base_tax_amount > 0 and ptac.add_deduct_tax = 'Add') or (ptac.base_tax_amount < 0 and ptac.add_deduct_tax = 'Deduct') 
                        THEN ptac.base_tax_amount 
                    ELSE 
                        0 
                    END)) AS base_taxes_and_charges_deducted
            FROM
                `tabPurchase Taxes and Charges` ptac
            /*LEFT JOIN
                `tabPurchase Invoice` parent
            ON
                ptac.parent = parent.name
            WHERE
                parent.docstatus = 1
                and parent.is_return = 0*/
            INNER JOIN
                `tabAccount` a
            ON
                ptac.account_head = a.name
            WHERE (a.account_type in ('Tax', 'Payable', '') or a.account_type is NULL)
            GROUP BY ptac.parent
        ) AS ptac_totals
    ON 
        pi.name = ptac_totals.parent
    WHERE
        pi.docstatus = 1
        and pi.is_return = 1
        and pi.posting_date >= %s
        and pi.posting_date <= %s
        and pi.company = %s
    """, (getdate(filters.from_date), getdate(filters.to_date), filters.company), as_dict=1)

    result.extend(data_return)
    result = sorted(result, key=lambda row: row.posting_date)

    return result

def get_columns():
    columns = [
        {
            "fieldname": "posting_date",
            "label": _("Date"),
            "fieldtype": "Date",
            "width": 120
        },
        # {
        #     "fieldname": "supplier",
        #     "label": _("Supplier Code"),
        #     "fieldtype": "Link",
        #     "options": "Supplier",
        #     "width": 150
        # },
        {
            "fieldname": "supplier_name",
            "label": _("Supplier Name"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "name",
            "label": _("Document No"),
            "fieldtype": "Link",
            "options": "Purchase Invoice",
            "width": 200
        },
        {
            "fieldname": "tax_id",
            "label": _("TIN"),
            "fieldtype": "Data",
            "width": 120
        },
        # {
        #     "fieldname": "is_return",
        #     "label": _("Return"),
        #     "fieldtype": "Check",
        #     "width": 10
        # },
        {
            "fieldname": "bill_no",
            "label": _("Supplier Invoice No"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "total",
            "label": _("Amount"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "net_discount",
            "label": _("Discount"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "tax_amount",
            "label": _("VAT"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "withholding_tax_amount",
            "label": _("Withholding Tax"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "grand_total",
            "label": _("Net Purchases"),
            "fieldtype": "Currency",
            "width": 150
        }
    ]

    return columns