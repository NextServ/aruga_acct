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
    # Prepare filter conditions for exclude_credit_notes, vat_ewt_category, and status
    exclude_credit_debit_condition = "AND si.is_debit_note = 0" if filters.get("exclude_credit_notes") else ""
    vat_ewt_condition = ""
    if filters.get("vat_ewt_category"):
        if filters.vat_ewt_category == "WITH VAT AND WITH EWT":
            vat_ewt_condition = "AND IFNULL(stac_add.tax_amount_after_discount_amount, 0) != 0 AND ABS(IFNULL(stac_deduct.tax_amount_after_discount_amount, 0)) != 0"
        elif filters.vat_ewt_category == "WITHOUT VAT WITH EWT":
            vat_ewt_condition = "AND IFNULL(stac_add.tax_amount_after_discount_amount, 0) = 0 AND ABS(IFNULL(stac_deduct.tax_amount_after_discount_amount, 0)) != 0"
        elif filters.vat_ewt_category == "WITH VAT WITHOUT EWT":
            vat_ewt_condition = "AND IFNULL(stac_add.tax_amount_after_discount_amount, 0) != 0 AND ABS(IFNULL(stac_deduct.tax_amount_after_discount_amount, 0)) = 0"
        elif filters.vat_ewt_category == "WITHOUT VAT WITHOUT EWT":
            vat_ewt_condition = "AND IFNULL(stac_add.tax_amount_after_discount_amount, 0) = 0 AND ABS(IFNULL(stac_deduct.tax_amount_after_discount_amount, 0)) = 0"
    status_condition = ""
    if filters.get("status"):
        if filters.status == "Pending":
            status_condition = "AND si.docstatus = 0"
        elif filters.status == "Approved":
            status_condition = "AND si.docstatus = 1"
        elif filters.status == "Cancelled":
            status_condition = "AND si.docstatus = 2"
    params = [getdate(filters.from_date), getdate(filters.to_date), filters.company]

    # Query for regular invoices
    data_si = frappe.db.sql("""
    SELECT 
        si.posting_date, 
        COALESCE(si.tax_id, c.tax_id, '') AS tax_id,
        si.customer,
        c.customer_name,
        si.name,
        si.currency,
        si.is_return,
        si.po_no,
        si.net_total as total,
        si.base_discount_amount as net_discount,
        IFNULL(stac_add.tax_amount_after_discount_amount, 0) as tax_amount,
        ABS(IFNULL(stac_deduct.tax_amount_after_discount_amount, 0)) as withholding_tax_amount,
        IFNULL(stac_add.total, 0) as invoice_amount,
        IFNULL(stac_add.total, 0) as non_vat,
        IFNULL(stac_add.total, 0) as sales_with_vat,
        IFNULL(stac_add.total, 0) as with_ewt,
        IFNULL(stac_add.total, 0) as without_ewt,
        CASE 
            WHEN si.docstatus = 0 THEN 'Pending'
            WHEN si.docstatus = 1 THEN 'Approved'
            WHEN si.docstatus = 2 THEN 'Cancelled'
        END as status
    FROM
        `tabSales Invoice` si
    LEFT JOIN
        `tabCustomer` c ON si.customer = c.name
    LEFT JOIN
        (
            SELECT 
                stac.parent, 
                SUM(stac.tax_amount) AS tax_amount, 
                SUM(stac.tax_amount_after_discount_amount) AS tax_amount_after_discount_amount, 
                SUM(stac.base_tax_amount_after_discount_amount) AS base_tax_amount_after_discount_amount,
                SUM(stac.total) AS total
            FROM `tabSales Taxes and Charges` stac
            INNER JOIN `tabAccount` a ON stac.account_head = a.name
            WHERE stac.tax_amount_after_discount_amount >= 0
                AND (a.account_type IN ('Tax', 'Payable', '') OR a.account_type IS NULL)
            GROUP BY stac.parent
        ) stac_add ON si.name = stac_add.parent
    LEFT JOIN
        (
            SELECT 
                stac.parent, 
                SUM(stac.tax_amount) AS tax_amount, 
                SUM(stac.tax_amount_after_discount_amount) AS tax_amount_after_discount_amount, 
                SUM(stac.base_tax_amount_after_discount_amount) AS base_tax_amount_after_discount_amount
            FROM `tabSales Taxes and Charges` stac
            INNER JOIN `tabAccount` a ON stac.account_head = a.name
            WHERE stac.tax_amount_after_discount_amount < 0
                AND (a.account_type IN ('Tax', 'Payable', '') OR a.account_type IS NULL)
            GROUP BY stac.parent
        ) stac_deduct ON si.name = stac_deduct.parent
    WHERE
        si.is_return = 0
        AND si.posting_date >= %s
        AND si.posting_date <= %s
        AND si.company = %s
        {exclude_credit_debit_condition}
        {vat_ewt_condition}
        {status_condition}
    ORDER BY
        si.posting_date ASC
    """.format(exclude_credit_debit_condition=exclude_credit_debit_condition, vat_ewt_condition=vat_ewt_condition, status_condition=status_condition), params, as_dict=1)

    result.extend(data_si)

    # Query for return invoices, only if exclude_credit_notes is not checked
    if not filters.get("exclude_credit_notes"):
        data_return = frappe.db.sql("""
        SELECT 
            si.posting_date, 
            COALESCE(si.tax_id, c.tax_id, '') AS tax_id,
            si.customer,
            c.customer_name,
            si.name,
            si.currency,
            si.is_return,
            si.po_no,
            si.net_total as total,
            si.base_discount_amount as net_discount,
            IFNULL(stac_add.tax_amount_after_discount_amount, 0) as tax_amount,
            IFNULL(-stac_deduct.tax_amount_after_discount_amount, 0) as withholding_tax_amount,
            IFNULL(stac_add.total, 0) as invoice_amount,
            IFNULL(stac_add.total, 0) as non_vat,
            IFNULL(stac_add.total, 0) as sales_with_vat,
            IFNULL(stac_add.total, 0) as with_ewt,
            IFNULL(stac_add.total, 0) as without_ewt,
            CASE 
                WHEN si.docstatus = 0 THEN 'Pending'
                WHEN si.docstatus = 1 THEN 'Approved'
                WHEN si.docstatus = 2 THEN 'Cancelled'
            END as status
        FROM
            `tabSales Invoice` si
        LEFT JOIN
            `tabCustomer` c ON si.customer = c.name
        LEFT JOIN
            (
                SELECT 
                    stac.parent, 
                    SUM(stac.tax_amount) AS tax_amount, 
                    SUM(stac.tax_amount_after_discount_amount) AS tax_amount_after_discount_amount, 
                    SUM(stac.base_tax_amount_after_discount_amount) AS base_tax_amount_after_discount_amount,
                    SUM(stac.total) AS total
                FROM `tabSales Taxes and Charges` stac
                INNER JOIN `tabAccount` a ON stac.account_head = a.name
                WHERE stac.tax_amount_after_discount_amount < 0
                    AND (a.account_type IN ('Tax', 'Payable', '') OR a.account_type IS NULL)
                GROUP BY stac.parent
            ) stac_add ON si.name = stac_add.parent
        LEFT JOIN
            (
                SELECT 
                    stac.parent, 
                    SUM(stac.tax_amount) AS tax_amount, 
                    SUM(stac.tax_amount_after_discount_amount) AS tax_amount_after_discount_amount, 
                    SUM(stac.base_tax_amount_after_discount_amount) AS base_tax_amount_after_discount_amount
                FROM `tabSales Taxes and Charges` stac
                INNER JOIN `tabAccount` a ON stac.account_head = a.name
                WHERE stac.tax_amount_after_discount_amount >= 0
                    AND (a.account_type IN ('Tax', 'Payable', '') OR a.account_type IS NULL)
                GROUP BY stac.parent
            ) stac_deduct ON si.name = stac_deduct.parent
        WHERE
            si.is_return = 1
            AND si.posting_date >= %s
            AND si.posting_date <= %s
            AND si.company = %s
            {exclude_credit_debit_condition}
            {vat_ewt_condition}
            {status_condition}
        ORDER BY
            si.posting_date ASC
        """.format(exclude_credit_debit_condition=exclude_credit_debit_condition, vat_ewt_condition=vat_ewt_condition, status_condition=status_condition), params, as_dict=1)

        result.extend(data_return)

    result = sorted(result, key=lambda row: row.posting_date)

    # Apply VAT and EWT logic
    for row in result:
        sign = -1 if row.get("is_return") else 1
        for key in (
            "total",
            "net_discount",
            "tax_amount",
            "withholding_tax_amount",
            "invoice_amount",
            "non_vat",
            "sales_with_vat",
            "with_ewt",
            "without_ewt",
        ):
            if row.get(key) is not None:
                row[key] = row[key] * sign
        # For Cancelled invoices, set all monetary fields to None
        if row['status'] == 'Cancelled':
            row['total'] = None
            row['net_discount'] = None
            row['tax_amount'] = None
            row['withholding_tax_amount'] = None
            row['invoice_amount'] = None
            row['non_vat'] = None
            row['sales_with_vat'] = None
            row['with_ewt'] = None
            row['without_ewt'] = None
        else:
            # VAT logic: Set total to None if tax_amount is 0, and non_vat to None if tax_amount is not 0
            if row['tax_amount'] == 0:
                row['total'] = None
                row['sales_with_vat'] = None
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
            "options": "Sales Invoice",
            "width": 150
        },
        {
            "fieldname": "posting_date",
            "label": _("Posting Date"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "customer_name",
            "label": _("Customer Name"),
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
            "fieldname": "sales_with_vat",
            "label": _("Total Sales W/ VAT"),
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
        },
    ]

    return columns