# Copyright (c) 2013, SERVIO Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import (getdate)
from aruga_acct.aruga_accounting.bir_forms import return_pdf_document
from aruga_acct.aruga_accounting.utils import get_company_information, get_supplier_information, report_is_permitted, get_bir_form_images
from frappe import _

options = {
    "margin-left": "0mm",
    "margin-right": "0mm",
    "margin-top": "0mm",
    "margin-bottom": "0mm"
}

def execute(filters=None):
    columns, data = [], []
    data = get_data(filters.company, filters.supplier, filters.doctype, filters.purchase_invoice, filters.payment_entry, filters.from_date, filters.to_date)
    columns = get_columns()
    return columns, data

# works on net total only
# TODO: custom tax base
def get_data(company, supplier, doctype, purchase_invoice, payment_entry, from_date, to_date):
    result = []
    data_pi = []
    data_pe = []
    pi_condition = ''
    pe_condition = ''
    
    if doctype == "Purchase Invoice" and purchase_invoice:
        pi_condition += ' AND pi.name = %s' % frappe.db.escape(purchase_invoice)

    if doctype == "Payment Entry" and payment_entry:
        pe_condition += ' AND pe.name = %s' % frappe.db.escape(payment_entry)

    if not payment_entry:
        data_pi = frappe.db.sql("""
            SELECT
                temp.atc,
                temp.description,
                SUM(temp.total) AS total,
                SUM(temp.tax_withheld) AS tax_withheld
            FROM
            (
                SELECT 
                    ptac.atc AS atc,
                    atc.description AS description,
                    pi.base_net_total AS total,
                    ABS(ptac.base_tax_amount) AS tax_withheld
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
                    and ptac.atc IN (SELECT atc FROM `tabATC` WHERE form_type IN ('2306','2307'))
                    and (a.account_type in ('Tax', 'Payable', '') or a.account_type is NULL)
                    and pi.supplier = %s
                    and pi.posting_date >= %s
                    and pi.posting_date <= %s
                    and pi.company = %s {0}
            ) temp
            GROUP BY
                temp.atc,
                temp.description
            """.format(pi_condition), (supplier, getdate(from_date), getdate(to_date), company), as_dict=1)
    
        result.extend(data_pi)
    
    if not purchase_invoice:
        data_pe = frappe.db.sql("""
            SELECT
                temp.atc,
                temp.description,
                SUM(temp.total) AS total,
                SUM(temp.tax_withheld) AS tax_withheld
            FROM
            (
                SELECT 
                    atac.atc AS atc,
                    atc.description AS description,
                    (pe.base_paid_amount_after_tax) AS total,
                    ABS(atac.base_tax_amount) AS tax_withheld
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
                    # and ((atac.base_tax_amount < 0 and atac.add_deduct_tax != 'Deduct') or (atac.base_tax_amount >= 0 and atac.add_deduct_tax = 'Deduct'))
                    and atac.atc IN (SELECT atc FROM `tabATC` WHERE form_type IN ('2306','2307'))
                    and (a.account_type in ('Tax', 'Payable', '') or a.account_type is NULL)
                    and pe.party = %s
                    and pe.posting_date >= %s
                    and pe.posting_date <= %s
                    and pe.company = %s {0}
            ) temp
            GROUP BY
                temp.atc,
                temp.description
            """.format(pe_condition), (supplier, getdate(from_date), getdate(to_date), company), as_dict=1)
    
        result.extend(data_pe)

    return result

@frappe.whitelist()
def bir_2306(company, supplier, doctype, purchase_invoice, payment_entry, from_date, to_date, response_type="pdf"):
    report_is_permitted('BIR 2306')

    data = get_data(company, supplier, doctype, purchase_invoice, payment_entry, from_date, to_date)

    data_ip = []
    data_mp = []

    ip_month_1_total = 0
    ip_month_2_total = 0
    ip_month_3_total = 0
    ip_grand_total = 0
    ip_tax_withheld_total = 0

    mp_month_1_total = 0
    mp_month_2_total = 0
    mp_month_3_total = 0
    mp_grand_total = 0
    mp_tax_withheld_total = 0

    for entry in data:
        ip_grand_total = ip_grand_total + entry.total
        ip_tax_withheld_total = ip_tax_withheld_total + entry.tax_withheld

        data_ip.append(entry)

    context = {
        'from_date': getdate(from_date),
        'to_date': getdate(to_date),
        'payor': get_company_information(company),
        'payee': get_supplier_information(supplier),
        'data_ip': data_ip,
        'ip_month_1_total': ip_month_1_total,
        'ip_month_2_total': ip_month_2_total,
        'ip_month_3_total': ip_month_3_total,
        'ip_grand_total': ip_grand_total,
        'ip_tax_withheld_total': ip_tax_withheld_total,
        'data_mp': data_mp,
        'mp_month_1_total': mp_month_1_total,
        'mp_month_2_total': mp_month_2_total,
        'mp_month_3_total': mp_month_3_total,
        'mp_grand_total': mp_grand_total,
        'mp_tax_withheld_total': mp_tax_withheld_total
    }

    filename = "BIR 2306 {} {} {} {}".format(company, supplier, from_date, to_date)
    
    context["build_version"] = frappe.utils.get_build_version()
    context["bir_form_images"] = get_bir_form_images("2306 Jan 2018 ENCS v3 Annex A-1.png")
    html = frappe.render_template("templates/bir_forms/bir_2306_template.html", context)
    options["page-size"] = "Legal"

    return_pdf_document(html, filename, options, response_type)

def get_columns():
    columns = [
        {
            "fieldname": "atc",
            "label": _("ATC"),
            "fieldtype": "Link",
            "options": "ATC",
            "width": 60
        },
        {
            "fieldname": "description",
            "label": _("Nature of Income Payment"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "total",
            "label": _("Amount of Payment"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "tax_withheld",
            "label": _("Tax Withheld"),
            "fieldtype": "Currency",
            "width": 150
        }
    ]


    return columns

