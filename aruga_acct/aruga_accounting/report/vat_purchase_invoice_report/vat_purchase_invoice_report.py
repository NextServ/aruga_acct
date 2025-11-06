# Copyright (c) 2013, SERVIO Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate
from frappe import _

def execute(filters=None):
    columns, data = [], []
    data = get_data(filters)
    columns = get_columns()
    return columns, data

def get_data(filters):
    result = []
    # Prepare filter conditions for exclude_debit_notes, vat_ewt_category, and status
    exclude_credit_debit_condition = "AND pi.is_return = 0" if filters.get("exclude_debit_notes") else ""
    vat_ewt_condition = ""
    if filters.get("vat_ewt_category"):
        if filters.vat_ewt_category == "WITH VAT AND WITH EWT":
            vat_ewt_condition = "AND IFNULL(ptac_add.tax_amount_after_discount_amount, 0) != 0 AND ABS(IFNULL(ptac_deduct.tax_amount_after_discount_amount, 0)) != 0"
        elif filters.vat_ewt_category == "WITHOUT VAT WITH EWT":
            vat_ewt_condition = "AND IFNULL(ptac_add.tax_amount_after_discount_amount, 0) = 0 AND ABS(IFNULL(ptac_deduct.tax_amount_after_discount_amount, 0)) != 0"
        elif filters.vat_ewt_category == "WITH VAT WITHOUT EWT":
            vat_ewt_condition = "AND IFNULL(ptac_add.tax_amount_after_discount_amount, 0) != 0 AND ABS(IFNULL(ptac_deduct.tax_amount_after_discount_amount, 0)) = 0"
        elif filters.vat_ewt_category == "WITHOUT VAT WITHOUT EWT":
            vat_ewt_condition = "AND IFNULL(ptac_add.tax_amount_after_discount_amount, 0) = 0 AND ABS(IFNULL(ptac_deduct.tax_amount_after_discount_amount, 0)) = 0"
    status_condition = ""
    if filters.get("status"):
        if filters.status == "Pending":
            status_condition = "AND pi.docstatus = 0"
        elif filters.status == "Approved":
            status_condition = "AND pi.docstatus = 1"
        elif filters.status == "Cancelled":
            status_condition = "AND pi.docstatus = 2"
    params = [getdate(filters.from_date), getdate(filters.to_date), filters.company]

    # Query for regular purchase invoices
    data_pi = frappe.db.sql("""
    SELECT 
        pi.posting_date, 
        COALESCE(pi.tax_id, s.tax_id, '') AS tax_id,
        pi.supplier,
        s.supplier_name,
        pi.name,
        pi.currency,
        pi.is_return,
        pi.net_total as total,
        pi.base_discount_amount as net_discount,
        IFNULL(ptac_add.tax_amount_after_discount_amount, 0) as tax_amount,
        ABS(IFNULL(ptac_deduct.tax_amount_after_discount_amount, 0)) as withholding_tax_amount,
        IFNULL(ptac_add.total, 0) as invoice_amount,
        IFNULL(ptac_add.total, 0) as non_vat,
        IFNULL(ptac_add.total, 0) as purchase_with_vat,
        IFNULL(ptac_add.total, 0) as with_ewt,
        IFNULL(ptac_add.total, 0) as without_ewt,
        CASE 
            WHEN pi.docstatus = 0 THEN 'Pending'
            WHEN pi.docstatus = 1 THEN 'Approved'
            WHEN pi.docstatus = 2 THEN 'Cancelled'
        END as status
    FROM
        `tabPurchase Invoice` pi
    LEFT JOIN
        `tabSupplier` s ON pi.supplier = s.name
    LEFT JOIN
        (
            SELECT 
                ptac.parent, 
                SUM(ptac.tax_amount) AS tax_amount, 
                SUM(ptac.tax_amount_after_discount_amount) AS tax_amount_after_discount_amount, 
                SUM(ptac.base_tax_amount_after_discount_amount) AS base_tax_amount_after_discount_amount,
                SUM(ptac.total) AS total
            FROM `tabPurchase Taxes and Charges` ptac
            INNER JOIN `tabAccount` a ON ptac.account_head = a.name
            WHERE ptac.tax_amount_after_discount_amount >= 0
                AND (a.account_type IN ('Tax', 'Payable', '') OR a.account_type IS NULL)
            GROUP BY ptac.parent
        ) ptac_add ON pi.name = ptac_add.parent
    LEFT JOIN
        (
            SELECT 
                ptac.parent, 
                SUM(ptac.tax_amount) AS tax_amount, 
                SUM(ptac.tax_amount_after_discount_amount) AS tax_amount_after_discount_amount, 
                SUM(ptac.base_tax_amount_after_discount_amount) AS base_tax_amount_after_discount_amount
            FROM `tabPurchase Taxes and Charges` ptac
            INNER JOIN `tabAccount` a ON ptac.account_head = a.name
            WHERE ptac.tax_amount_after_discount_amount < 0
                AND (a.account_type IN ('Tax', 'Payable', '') OR a.account_type IS NULL)
            GROUP BY ptac.parent
        ) ptac_deduct ON pi.name = ptac_deduct.parent
    WHERE
        pi.is_return = 0
        AND pi.posting_date >= %s
        AND pi.posting_date <= %s
        AND pi.company = %s
        {exclude_credit_debit_condition}
        {vat_ewt_condition}
        {status_condition}
    ORDER BY
        pi.posting_date ASC
    """.format(exclude_credit_debit_condition=exclude_credit_debit_condition, vat_ewt_condition=vat_ewt_condition, status_condition=status_condition), params, as_dict=1)

    result.extend(data_pi)

    # Query for return purchase invoices, only if exclude_debit_notes is not checked
    if not filters.get("exclude_debit_notes"):
        data_return = frappe.db.sql("""
        SELECT 
            pi.posting_date, 
            COALESCE(pi.tax_id, s.tax_id, '') AS tax_id,
            pi.supplier,
            s.supplier_name,
            pi.name,
            pi.currency,
            pi.is_return,
            pi.net_total as total,
            pi.base_discount_amount as net_discount,
            IFNULL(ptac_add.tax_amount_after_discount_amount, 0) as tax_amount,
            IFNULL(-ptac_deduct.tax_amount_after_discount_amount, 0) as withholding_tax_amount,
            IFNULL(ptac_add.total, 0) as invoice_amount,
            IFNULL(ptac_add.total, 0) as non_vat,
            IFNULL(ptac_add.total, 0) as purchase_with_vat,
            IFNULL(ptac_add.total, 0) as with_ewt,
            IFNULL(ptac_add.total, 0) as without_ewt,
            CASE 
                WHEN pi.docstatus = 0 THEN 'Pending'
                WHEN pi.docstatus = 1 THEN 'Approved'
                WHEN pi.docstatus = 2 THEN 'Cancelled'
        END as status
        FROM
            `tabPurchase Invoice` pi
        LEFT JOIN
            `tabSupplier` s ON pi.supplier = s.name
        LEFT JOIN
            (
                SELECT 
                    ptac.parent, 
                    SUM(ptac.tax_amount) AS tax_amount, 
                    SUM(ptac.tax_amount_after_discount_amount) AS tax_amount_after_discount_amount, 
                    SUM(ptac.base_tax_amount_after_discount_amount) AS base_tax_amount_after_discount_amount,
                    SUM(ptac.total) AS total
                FROM `tabPurchase Taxes and Charges` ptac
                INNER JOIN `tabAccount` a ON ptac.account_head = a.name
                WHERE ptac.tax_amount_after_discount_amount < 0
                    AND (a.account_type IN ('Tax', 'Payable', '') OR a.account_type IS NULL)
                GROUP BY ptac.parent
            ) ptac_add ON pi.name = ptac_add.parent
        LEFT JOIN
            (
                SELECT 
                    ptac.parent, 
                    SUM(ptac.tax_amount) AS tax_amount, 
                    SUM(ptac.tax_amount_after_discount_amount) AS tax_amount_after_discount_amount, 
                    SUM(ptac.base_tax_amount_after_discount_amount) AS base_tax_amount_after_discount_amount
                FROM `tabPurchase Taxes and Charges` ptac
                INNER JOIN `tabAccount` a ON ptac.account_head = a.name
                WHERE ptac.tax_amount_after_discount_amount >= 0
                    AND (a.account_type IN ('Tax', 'Payable', '') OR a.account_type IS NULL)
                GROUP BY ptac.parent
            ) ptac_deduct ON pi.name = ptac_deduct.parent
        WHERE
            pi.is_return = 1
            AND pi.posting_date >= %s
            AND pi.posting_date <= %s
            AND pi.company = %s
            {exclude_credit_debit_condition}
            {vat_ewt_condition}
            {status_condition}
        ORDER BY
            pi.posting_date ASC
        """.format(exclude_credit_debit_condition=exclude_credit_debit_condition, vat_ewt_condition=vat_ewt_condition, status_condition=status_condition), params, as_dict=1)

        result.extend(data_return)

    result = sorted(result, key=lambda row: row.posting_date)

    # Apply VAT and EWT logic
    for row in result:
        # For Cancelled invoices, set all monetary fields to None
        if row['status'] == 'Cancelled':
            row['total'] = None
            row['net_discount'] = None
            row['tax_amount'] = None
            row['withholding_tax_amount'] = None
            row['invoice_amount'] = None
            row['non_vat'] = None
            row['purchase_with_vat'] = None
            row['with_ewt'] = None
            row['without_ewt'] = None
        else:
            # VAT logic: Set total to None if tax_amount is 0, and non_vat to None if tax_amount is not 0
            if row['tax_amount'] == 0:
                row['total'] = None
                row['purchase_with_vat'] = None
            else:
                row['non_vat'] = None
            # EWT logic: Set with_ewt to None if withholding_tax_amount is 0, and total (without_ewt) to None if withholding_tax_amount is not 0
            if row['withholding_tax_amount'] == 0:
                row['with_ewt'] = None
            else:
                row['without_ewt'] = None

    return result

def get_columns():
    columns = [
        {
            "fieldname": "name",
            "label": _("Document No"),
            "fieldtype": "Link",
            "options": "Purchase Invoice",
            "width": 150
        },
        {
            "fieldname": "posting_date",
            "label": _("Posting Date"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "supplier_name",
            "label": _("Supplier Name"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "tax_id",
            "label": _("TIN NO."),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "invoice_amount",
            "label": _("INVOICE AMOUNT"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "non_vat",
            "label": _("NON-VAT ZERO RATED"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "tax_amount",
            "label": _("12% VAT"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "total",
            "label": _("Net of Vat"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "purchase_with_vat",
            "label": _("Total Purchase W/ VAT"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "with_ewt",
            "label": _("WITH E.W.T."),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "without_ewt",
            "label": _("WITHOUT E.W.T."),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "withholding_tax_amount",
            "label": _("TOTAL EWT"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 100
        }
    ]

    return columns