# Copyright (c) 2013, SERVIO Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import (getdate)
from frappe import _

def execute(filters=None):
    columns, data = [], []
    data = get_data(filters.company, filters.supplier, filters.employee, filters.doctype, filters.purchase_invoice, filters.payment_entry, filters.expense_claim, filters.from_date, filters.to_date)
    columns = get_columns()
    return columns, data

# works on net total only
# TODO: custom tax base
def get_data(company, supplier, employee, doctype, purchase_invoice, payment_entry, expense_claim, from_date, to_date):
    result = []
    data_pi = []
    data_pe = []
    pi_condition = ''
    pe_condition = ''
    
    if doctype == "Purchase Invoice" and purchase_invoice:
        pi_condition += ' AND pi.name = %s' % frappe.db.escape(purchase_invoice)

    if doctype == "Payment Entry" and payment_entry:
        pe_condition += ' AND pe.name = %s' % frappe.db.escape(payment_entry)

    if doctype == "Expense Claim" and expense_claim:
        pe_condition += ' AND ec.name = %s' % frappe.db.escape(expense_claim)


    if doctype == "Purchase Invoice":
        data_pi = frappe.db.sql("""
            SELECT
                temp.payment_type,
                temp.atc,
                temp.description,
                SUM(temp.month_1) AS month_1,
                SUM(temp.month_2) AS month_2,
                SUM(temp.month_3) AS month_3,
                SUM(temp.total) AS total,
                SUM(temp.tax_withheld_for_the_quarter) AS tax_withheld_for_the_quarter
            FROM
            (
                SELECT 
                    (CASE 
                        WHEN ptac.atc IN (SELECT atc FROM `tabATC` WHERE LEFT(atc, 2) IN ('WI', 'WC')) 
                            THEN 'Income Payment' 
                        WHEN ptac.atc IN (SELECT atc FROM `tabATC` WHERE LEFT(atc, 2) IN ('WB', 'WV'))  
                            THEN 'Money Payment' 
                    END) AS payment_type,
                    ptac.atc AS atc,
                    atc.description AS description,
                    pi.name AS document_no,
                    (CASE WHEN MONTH(pi.posting_date) IN (1, 4, 7, 10) THEN pi.base_net_total ELSE 0 END) AS month_1,
                    (CASE WHEN MONTH(pi.posting_date) IN (2, 5, 8, 11) THEN pi.base_net_total ELSE 0 END) AS month_2,
                    (CASE WHEN MONTH(pi.posting_date) IN (3, 6, 9, 12) THEN pi.base_net_total ELSE 0 END) AS month_3,
                    pi.base_net_total AS total,
                    ABS(ptac.base_tax_amount) AS tax_withheld_for_the_quarter
                FROM 
                    `tabPurchase Invoice` pi
                LEFT JOIN
                    `tabPurchase Taxes and Charges` ptac
                ON
                    pi.name = ptac.parent
                LEFT JOIN 
                    `tabSupplier` as s
                ON
                    pi.supplier = s.name
                INNER JOIN
                    `tabAccount` a
                ON
                    ptac.account_head = a.name
                INNER JOIN
                    `tabATC` atc
                ON
                    ptac.atc = atc.name
                WHERE
                    pi.docstatus = 1
                    and pi.is_return = 0
                    # and ((ptac.base_tax_amount < 0 and ptac.add_deduct_tax != 'Deduct') or (ptac.base_tax_amount >= 0 and ptac.add_deduct_tax = 'Deduct'))
                    and ptac.atc IN (SELECT atc FROM `tabATC` WHERE tax_type_code IN ('WE', 'WB', 'WV') and form_type = '2307')
                    and (a.account_type in ('Tax', 'Payable', 'Expense Account', 'Chargeable', '') or a.account_type is NULL)
                    and pi.supplier = %s
                    and pi.posting_date >= %s
                    and pi.posting_date <= %s
                    and pi.company = %s {0}
            ) temp
            GROUP BY
                temp.payment_type,
                temp.atc,
                temp.description
            """.format(pi_condition), (supplier, getdate(from_date), getdate(to_date), company), as_dict=1)
    
        result.extend(data_pi)
    
    if doctype == "Payment Entry":
        data_pe = frappe.db.sql("""
            SELECT
                temp.payment_type,
                temp.atc,
                temp.description,
                SUM(temp.month_1) AS month_1,
                SUM(temp.month_2) AS month_2,
                SUM(temp.month_3) AS month_3,
                SUM(temp.total) AS total,
                SUM(temp.tax_withheld_for_the_quarter) AS tax_withheld_for_the_quarter
            FROM
            (
                SELECT 
                    (CASE 
                        WHEN atac.atc IN (SELECT atc FROM `tabATC` WHERE LEFT(atc, 2) IN ('WI', 'WC')) 
                            THEN 'Income Payment' 
                        WHEN atac.atc IN (SELECT atc FROM `tabATC` WHERE LEFT(atc, 2) IN ('WB', 'WV'))  
                            THEN 'Money Payment' 
                    END) AS payment_type,
                    atac.atc AS atc,
                    atc.description AS description,
                    pe.name AS document_no,
                    (CASE WHEN MONTH(pe.posting_date) IN (1, 4, 7, 10) THEN (pe.base_paid_amount_after_tax) ELSE 0 END) AS month_1,
                    (CASE WHEN MONTH(pe.posting_date) IN (2, 5, 8, 11) THEN (pe.base_paid_amount_after_tax) ELSE 0 END) AS month_2,
                    (CASE WHEN MONTH(pe.posting_date) IN (3, 6, 9, 12) THEN (pe.base_paid_amount_after_tax) ELSE 0 END) AS month_3,
                    (pe.base_paid_amount_after_tax) AS total,
                    ABS(atac.base_tax_amount) AS tax_withheld_for_the_quarter
                FROM 
                    `tabPayment Entry` pe
                LEFT JOIN
                    `tabAdvance Taxes and Charges` atac
                ON
                    pe.name = atac.parent
                LEFT JOIN 
                    `tabSupplier` as s
                ON
                    pe.party = s.name
                INNER JOIN
                    `tabAccount` a
                ON
                    atac.account_head = a.name
                INNER JOIN
                    `tabATC` atc
                ON
                    atac.atc = atc.name
                WHERE
                    pe.docstatus = 1
                    and pe.payment_type = 'Pay'
                    and pe.party_type = 'Supplier'
                    and ((atac.base_tax_amount < 0 and atac.add_deduct_tax != 'Deduct') or (atac.base_tax_amount >= 0 and atac.add_deduct_tax = 'Deduct'))
                    and atac.atc IN (SELECT atc FROM `tabATC` WHERE tax_type_code IN ('WE', 'WB', 'WV') and form_type = '2307')
                    and (a.account_type in ('Tax', 'Payable', 'Expense Account', 'Chargeable', '') or a.account_type is NULL)
                    and pe.party = %s
                    and pe.posting_date >= %s
                    and pe.posting_date <= %s
                    and pe.company = %s {0}
            ) temp
            GROUP BY
                temp.payment_type,
                temp.atc,
                temp.description
            """.format(pe_condition), (supplier, getdate(from_date), getdate(to_date), company), as_dict=1)
    
        result.extend(data_pe)
    
    if doctype == "Expense Claim":
        data_ec = frappe.db.sql("""
            SELECT
                temp.payment_type,
                temp.atc,
                temp.description,
                SUM(temp.month_1) AS month_1,
                SUM(temp.month_2) AS month_2,
                SUM(temp.month_3) AS month_3,
                SUM(temp.total) AS total,
                SUM(temp.tax_withheld_for_the_quarter) AS tax_withheld_for_the_quarter
            FROM
            (
                SELECT 
                    (CASE 
                        WHEN etac.atc IN (SELECT atc FROM `tabATC` WHERE LEFT(atc, 2) IN ('WI', 'WC')) 
                            THEN 'Income Payment' 
                        WHEN etac.atc IN (SELECT atc FROM `tabATC` WHERE LEFT(atc, 2) IN ('WB', 'WV'))  
                            THEN 'Money Payment' 
                    END) AS payment_type,
                    etac.atc AS atc,
                    atc.description AS description,
                    ec.name AS document_no,
                    (CASE WHEN MONTH(ecd.expense_date) IN (1, 4, 7, 10) THEN (ec.grand_total - ec.total_taxes_and_charges) ELSE 0 END) AS month_1,
                    (CASE WHEN MONTH(ecd.expense_date) IN (2, 5, 8, 11) THEN (ec.grand_total - ec.total_taxes_and_charges) ELSE 0 END) AS month_2,
                    (CASE WHEN MONTH(ecd.expense_date) IN (3, 6, 9, 12) THEN (ec.grand_total - ec.total_taxes_and_charges) ELSE 0 END) AS month_3,
                    (ec.grand_total - ec.total_taxes_and_charges) AS total,
                    ABS(etac.tax_amount) AS tax_withheld_for_the_quarter
                FROM 
                    `tabExpense Claim` ec
                LEFT JOIN `tabExpense Claim Detail` ecd
                ON
                    ecd.parent = ec.name
                    and ecd.idx = 1
                LEFT JOIN
                    `tabExpense Taxes and Charges` etac
                ON
                    ec.name = etac.parent
                LEFT JOIN 
                    `tabEmployee` as e
                ON
                    ec.employee = e.name
                INNER JOIN
                    `tabAccount` a
                ON
                    etac.account_head = a.name
                INNER JOIN
                    `tabATC` atc
                ON
                    etac.atc = atc.name
                WHERE
                    ec.docstatus = 1
                    and (etac.tax_amount < 0)
                    and etac.atc IN (SELECT atc FROM `tabATC` WHERE tax_type_code IN ('WE', 'WB', 'WV') and form_type = '2307')
                    and (a.account_type in ('Tax', 'Payable', 'Expense Account', 'Chargeable', '') or a.account_type is NULL)
                    and ec.employee = %s
                    and ecd.expense_date >= %s
                    and ecd.expense_date <= %s
                    and ec.company = %s {0}
            ) temp
            GROUP BY
                temp.atc,
                temp.description
            """.format(pe_condition), (employee, getdate(from_date), getdate(to_date), company), as_dict=1)
    
        result.extend(data_ec)

    return result

def get_columns():
    columns = [
        {
            "fieldname": "payment_type",
            "label": _("Type"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "atc",
            "label": _("ATC"),
            "fieldtype": "Link",
            "options": "ATC",
            "width": 60
        },
        {
            "fieldname": "description",
            "label": _("Description"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "month_1",
            "label": _("1st Month"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "month_2",
            "label": _("2nd Month"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "month_3",
            "label": _("3rd Month"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "total",
            "label": _("Total"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "tax_withheld_for_the_quarter",
            "label": _("Tax Withheld"),
            "fieldtype": "Currency",
            "width": 150
        }
    ]


    return columns
