# Copyright (c) 2013, SERVIO Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, flt, cint
from datetime import datetime
from aruga_acct.aruga_accounting.utils import get_company_information, report_is_permitted, get_bir_form_images
from aruga_acct.aruga_accounting.bir_forms import return_pdf_document, first_month_in_quarter
from frappe import _
import json
import calendar
from dateutil.relativedelta import relativedelta

options = {
    "margin-left": "0mm",
    "margin-right": "0mm",
    "margin-top": "0mm",
    "margin-bottom": "0mm"
}

def execute(filters=None):
    company = filters.company
    try:
        tax_declaration_company_setup = frappe.get_doc('Tax Declaration Company Setup', company)
    except:
        frappe.throw("Please create a Tax Declaration Company Setup record for {0}".format(company))

    columns, data = [], []
    data = get_data(filters)
    columns = get_columns()
    return columns, data

def compute_totals(company, year, quarter, input_tax_carried_over_from_previous_period=0,
                  input_tax_deferred_on_capital_goods_exceeding_1m_from_previous_period=0,
                  transitional_input_tax=0, presumptive_input_tax=0, allowable_input_tax_others=0,
                  input_tax_deferred_on_capital_goods_from_previous_period_1m_up=0,
                  input_tax_directly_attributable_to_exempt_sales=0, vat_refund_tcc_claimed=0,
                  less_deductions_from_input_tax_others=0, surcharge=0, compromise=0, interest=0):
    year = int(year)
    quarter = int(quarter)
    first_month = first_month_in_quarter(quarter)
    from_date = getdate(datetime(year, first_month, 1))
    to_date = getdate(datetime(year, first_month + 2, calendar.monthrange(year, first_month + 2)[1]))

    try:
        tax_declaration_company_setup = frappe.get_doc('Tax Declaration Company Setup', company)
    except:
        frappe.throw("Please create a Tax Declaration Company Setup record for {0}".format(company))

    totals = {
        'vat_sales': {'total_base_tax_base': 0, 'total_base_tax_amount': 0},
        'sales_to_government': {'total_base_tax_base': 0, 'total_base_tax_amount': 0},
        'zero_rated_sales': {'total_base_tax_base': 0, 'total_base_tax_amount': 0},
        'exempt_sales': {'total_base_tax_base': 0, 'total_base_tax_amount': 0},
        'total_sales_receipts': 0,
        'total_output_tax_due': 0,
        'less_allowable_input_tax': {
            'input_tax_carried_over_from_previous_period': flt(input_tax_carried_over_from_previous_period, 2),
            'input_tax_deferred_on_capital_goods_exceeding_1m_from_previous_period': flt(input_tax_deferred_on_capital_goods_exceeding_1m_from_previous_period, 2),
            'transitional_input_tax': flt(transitional_input_tax, 2),
            'presumptive_input_tax': flt(presumptive_input_tax, 2),
            'allowable_input_tax_others': flt(allowable_input_tax_others, 2),
        },
        'total_other_allowable_input_tax': 0,
        'capital_goods': {'total_base_tax_base': 0, 'total_base_tax_amount': 0},
        'capital_goods_exceeding_1m': {'total_base_tax_base': 0, 'total_base_tax_amount': 0},
        'domestic_purchases_of_goods': {'total_base_tax_base': 0, 'total_base_tax_amount': 0},
        'importation_of_goods': {'total_base_tax_base': 0, 'total_base_tax_amount': 0},
        'domestic_purchase_of_services': {'total_base_tax_base': 0, 'total_base_tax_amount': 0},
        'services_rendered_by_non_residents': {'total_base_tax_base': 0, 'total_base_tax_amount': 0},
        'purchases_not_qualified_for_input_tax': {'total_base_tax_base': 0, 'total_base_tax_amount': 0},
        'others': {'total_base_tax_base': 0, 'total_base_tax_amount': 0},
        'total_current_purchases': 0,
        'total_available_input_tax': 0,
        'less_deductions_from_input_tax': {
            'input_tax_deferred_on_capital_goods_from_previous_period_1m_up': flt(input_tax_deferred_on_capital_goods_from_previous_period_1m_up, 2),
            'input_tax_directly_attributable_to_exempt_sales': flt(input_tax_directly_attributable_to_exempt_sales, 2),
            'amount_of_input_tax_not_directly_attributable': 0,
            'input_tax_allocable_to_exempt_sales': 0,
            'vat_refund_tcc_claimed': flt(vat_refund_tcc_claimed, 2),
            'less_deductions_from_input_tax_others': flt(less_deductions_from_input_tax_others, 2),
        },
        'ratable_portion_of_input_tax_not_directly_attributable': 0,
        'total_deductions_from_input_tax': 0,
        'total_allowable_input_tax': 0,
        'net_vat_payable': 0,
        'total_tax_credit_payments': 0,
        'tax_still_payable': 0,
        'penalties': {
            'surcharge': flt(surcharge, 2),
            'interest': flt(interest, 2),
            'compromise': flt(compromise, 2),
            'total': flt(surcharge, 2) + flt(interest, 2) + flt(compromise, 2)
        },
        'total_amount_payable': 0,
    }

    pi_base_net_amounts = frappe.db.sql("""
        SELECT 
            pi.name, 
            (COALESCE(NULLIF(pii.item_code, ''), pii.item_name)) AS item_name, 
            pii.item_tax_template, 
            pi.taxes_and_charges, 
            SUM(base_net_amount) AS base_net_amount 
        FROM
            `tabPurchase Invoice Item` pii
        LEFT JOIN
            `tabPurchase Invoice` pi
        ON
            pii.parent = pi.name
        WHERE
            pi.docstatus = 1
            AND pi.company = %s
            AND pi.posting_date >= %s
            AND pi.posting_date <= %s
        GROUP BY pi.name, (COALESCE(NULLIF(pii.item_code, ''), pii.item_name)), pii.item_tax_template, pi.taxes_and_charges;
        """, (company, from_date, to_date), as_dict=1)

    pi_base_tax_amounts = frappe.db.sql("""
        SELECT
            pi.name,
            CASE WHEN pi.is_return = 1 THEN -ptac.base_tax_amount ELSE ptac.base_tax_amount END AS base_tax_amount,
            ptac.item_wise_tax_detail
        FROM
            `tabPurchase Invoice` pi
        INNER JOIN
            `tabPurchase Taxes and Charges` ptac
        ON
            pi.name = ptac.parent
        INNER JOIN
            `tabAccount` a
        ON
            ptac.account_head = a.name
        WHERE
            pi.docstatus = 1
            AND (a.account_type IN ('Tax', 'Payable', '') OR a.account_type IS NULL)
            AND a.name NOT LIKE '%%Withholding%%'
            AND pi.company = %s
            AND pi.posting_date >= %s
            AND pi.posting_date <= %s
        """, (company, from_date, to_date), as_dict=1)

    si_base_net_amounts = frappe.db.sql("""
        SELECT 
            si.name, 
            (COALESCE(NULLIF(sii.item_code, ''), sii.item_name)) AS item_name,  
            sii.item_tax_template, 
            si.taxes_and_charges, 
            SUM(base_net_amount) AS base_net_amount 
        FROM
            `tabSales Invoice Item` sii
        LEFT JOIN
            `tabSales Invoice` si
        ON
            sii.parent = si.name
        WHERE
            si.docstatus = 1
            AND si.company = %s
            AND si.posting_date >= %s
            AND si.posting_date <= %s
        GROUP BY si.name, (COALESCE(NULLIF(sii.item_code, ''), sii.item_name)), sii.item_tax_template, si.taxes_and_charges;
        """, (company, from_date, to_date), as_dict=1)

    si_base_tax_amounts = frappe.db.sql("""
        SELECT
            si.name,
            CASE WHEN si.is_return = 1 THEN -stac.base_tax_amount ELSE stac.base_tax_amount END AS base_tax_amount,
            stac.item_wise_tax_detail
        FROM
            `tabSales Invoice` si
        INNER JOIN
            `tabSales Taxes and Charges` stac
        ON
            si.name = stac.parent
        INNER JOIN
            `tabAccount` a
        ON
            stac.account_head = a.name
        WHERE
            si.docstatus = 1
            AND (a.account_type IN ('Tax', 'Payable', '') OR a.account_type IS NULL)
            AND a.name NOT LIKE '%%Withholding%%'
            AND si.company = %s
            AND si.posting_date >= %s
            AND si.posting_date <= %s
        """, (company, from_date, to_date), as_dict=1)

    for tax_line in si_base_tax_amounts:
        item_wise_tax_detail = json.loads(tax_line.item_wise_tax_detail)
        for item in item_wise_tax_detail.keys():
            for item_net_amount in si_base_net_amounts:
                if item_net_amount.name == tax_line.name and item_net_amount.item_name == item:
                    item_tax_template = item_net_amount.item_tax_template
                    taxes_and_charges = item_net_amount.taxes_and_charges
                    if tax_declaration_company_setup.item_vat_sales and item_tax_template == tax_declaration_company_setup.item_vat_sales:
                        totals['vat_sales']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['vat_sales']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    elif tax_declaration_company_setup.vat_sales and taxes_and_charges == tax_declaration_company_setup.vat_sales:
                        totals['vat_sales']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['vat_sales']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    elif tax_declaration_company_setup.item_sales_to_government and item_tax_template == tax_declaration_company_setup.item_sales_to_government:
                        totals['sales_to_government']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['sales_to_government']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    elif tax_declaration_company_setup.sales_to_government and taxes_and_charges == tax_declaration_company_setup.sales_to_government:
                        totals['sales_to_government']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['sales_to_government']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    elif tax_declaration_company_setup.item_zero_rated_sales and item_tax_template == tax_declaration_company_setup.item_zero_rated_sales:
                        totals['zero_rated_sales']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['zero_rated_sales']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    elif tax_declaration_company_setup.zero_rated_sales and taxes_and_charges == tax_declaration_company_setup.zero_rated_sales:
                        totals['zero_rated_sales']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['zero_rated_sales']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    elif tax_declaration_company_setup.item_exempt_sales and item_tax_template == tax_declaration_company_setup.item_exempt_sales:
                        totals['exempt_sales']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['exempt_sales']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    elif tax_declaration_company_setup.exempt_sales and taxes_and_charges == tax_declaration_company_setup.exempt_sales:
                        totals['exempt_sales']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['exempt_sales']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    break

    for tax_line in pi_base_tax_amounts:
        item_wise_tax_detail = json.loads(tax_line.item_wise_tax_detail)
        for item in item_wise_tax_detail.keys():
            for item_net_amount in pi_base_net_amounts:
                if item_net_amount.name == tax_line.name and item_net_amount.item_name == item:
                    item_tax_template = item_net_amount.item_tax_template
                    taxes_and_charges = item_net_amount.taxes_and_charges
                    if tax_declaration_company_setup.item_capital_goods and item_tax_template == tax_declaration_company_setup.item_capital_goods:
                        if flt(tax_line.base_tax_amount, 2) < 1000000:
                            totals['capital_goods']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                            totals['capital_goods']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                        else:
                            totals['capital_goods_exceeding_1m']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                            totals['capital_goods_exceeding_1m']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    elif tax_declaration_company_setup.capital_goods and taxes_and_charges == tax_declaration_company_setup.capital_goods:
                        if flt(tax_line.base_tax_amount, 2) < 1000000:
                            totals['capital_goods']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                            totals['capital_goods']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                        else:
                            totals['capital_goods_exceeding_1m']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                            totals['capital_goods_exceeding_1m']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    elif tax_declaration_company_setup.item_domestic_purchases_of_goods and item_tax_template == tax_declaration_company_setup.item_domestic_purchases_of_goods:
                        totals['domestic_purchases_of_goods']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['domestic_purchases_of_goods']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    elif tax_declaration_company_setup.domestic_purchases_of_goods and taxes_and_charges == tax_declaration_company_setup.domestic_purchases_of_goods:
                        totals['domestic_purchases_of_goods']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['domestic_purchases_of_goods']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    elif tax_declaration_company_setup.item_importation_of_goods and item_tax_template == tax_declaration_company_setup.item_importation_of_goods:
                        totals['importation_of_goods']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['importation_of_goods']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    elif tax_declaration_company_setup.importation_of_goods and taxes_and_charges == tax_declaration_company_setup.importation_of_goods:
                        totals['importation_of_goods']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['importation_of_goods']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    elif tax_declaration_company_setup.item_domestic_purchase_of_services and item_tax_template == tax_declaration_company_setup.item_domestic_purchase_of_services:
                        totals['domestic_purchase_of_services']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['domestic_purchase_of_services']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    elif tax_declaration_company_setup.domestic_purchase_of_services and taxes_and_charges == tax_declaration_company_setup.domestic_purchase_of_services:
                        totals['domestic_purchase_of_services']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['domestic_purchase_of_services']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    elif tax_declaration_company_setup.item_services_rendered_by_non_residents and item_tax_template == tax_declaration_company_setup.item_services_rendered_by_non_residents:
                        totals['services_rendered_by_non_residents']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['services_rendered_by_non_residents']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    elif tax_declaration_company_setup.services_rendered_by_non_residents and taxes_and_charges == tax_declaration_company_setup.services_rendered_by_non_residents:
                        totals['services_rendered_by_non_residents']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['services_rendered_by_non_residents']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    elif tax_declaration_company_setup.item_zero_rated_purchase and item_tax_template == tax_declaration_company_setup.item_zero_rated_purchase:
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    elif tax_declaration_company_setup.zero_rated_purchase and taxes_and_charges == tax_declaration_company_setup.zero_rated_purchase:
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    elif tax_declaration_company_setup.item_exempt_purchase and item_tax_template == tax_declaration_company_setup.item_exempt_purchase:
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    elif tax_declaration_company_setup.exempt_purchase and taxes_and_charges == tax_declaration_company_setup.exempt_purchase:
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    elif tax_declaration_company_setup.item_others and item_tax_template == tax_declaration_company_setup.item_others:
                        totals['others']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['others']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    elif tax_declaration_company_setup.others and taxes_and_charges == tax_declaration_company_setup.others:
                        totals['others']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['others']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    else:
                        totals['others']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['others']['total_base_tax_amount'] += flt(tax_line.base_tax_amount, 2)
                    break

    totals['total_sales_receipts'] = (
        totals['vat_sales']['total_base_tax_base'] +
        totals['sales_to_government']['total_base_tax_base'] +
        totals['zero_rated_sales']['total_base_tax_base'] +
        totals['exempt_sales']['total_base_tax_base']
    )

    totals['total_output_tax_due'] = (
        totals['vat_sales']['total_base_tax_amount'] +
        totals['sales_to_government']['total_base_tax_amount']
    )

    totals['total_other_allowable_input_tax'] = (
        totals['less_allowable_input_tax']['input_tax_carried_over_from_previous_period'] +
        totals['less_allowable_input_tax']['input_tax_deferred_on_capital_goods_exceeding_1m_from_previous_period'] +
        totals['less_allowable_input_tax']['transitional_input_tax'] +
        totals['less_allowable_input_tax']['presumptive_input_tax'] +
        totals['less_allowable_input_tax']['allowable_input_tax_others']
    )

    totals['total_current_purchases'] = (
        totals['capital_goods']['total_base_tax_base'] +
        totals['capital_goods_exceeding_1m']['total_base_tax_base'] +
        totals['domestic_purchases_of_goods']['total_base_tax_base'] +
        totals['importation_of_goods']['total_base_tax_base'] +
        totals['domestic_purchase_of_services']['total_base_tax_base'] +
        totals['services_rendered_by_non_residents']['total_base_tax_base'] +
        totals['purchases_not_qualified_for_input_tax']['total_base_tax_base'] +
        totals['others']['total_base_tax_base']
    )

    totals['total_available_input_tax'] = (
        totals['total_other_allowable_input_tax'] +
        totals['capital_goods']['total_base_tax_amount'] +
        totals['capital_goods_exceeding_1m']['total_base_tax_amount'] +
        totals['domestic_purchases_of_goods']['total_base_tax_amount'] +
        totals['importation_of_goods']['total_base_tax_amount'] +
        totals['domestic_purchase_of_services']['total_base_tax_amount'] +
        totals['services_rendered_by_non_residents']['total_base_tax_amount'] +
        totals['others']['total_base_tax_amount']
    )

    totals['less_deductions_from_input_tax']['amount_of_input_tax_not_directly_attributable'] = (
        totals['total_available_input_tax'] -
        totals['less_deductions_from_input_tax']['input_tax_directly_attributable_to_exempt_sales']
    )

    if totals['total_sales_receipts'] > 0:
        totals['ratable_portion_of_input_tax_not_directly_attributable'] = flt(
            (totals['exempt_sales']['total_base_tax_base'] / totals['total_sales_receipts']) *
            totals['less_deductions_from_input_tax']['amount_of_input_tax_not_directly_attributable'], 2
        )
        totals['less_deductions_from_input_tax']['input_tax_allocable_to_exempt_sales'] = (
            totals['less_deductions_from_input_tax']['input_tax_directly_attributable_to_exempt_sales'] +
            totals['ratable_portion_of_input_tax_not_directly_attributable']
        )
    else:
        totals['ratable_portion_of_input_tax_not_directly_attributable'] = 0
        totals['less_deductions_from_input_tax']['input_tax_allocable_to_exempt_sales'] = (
            totals['less_deductions_from_input_tax']['input_tax_directly_attributable_to_exempt_sales']
        )

    totals['total_deductions_from_input_tax'] = (
        totals['less_deductions_from_input_tax']['input_tax_deferred_on_capital_goods_from_previous_period_1m_up'] +
        totals['less_deductions_from_input_tax']['input_tax_allocable_to_exempt_sales'] +
        totals['less_deductions_from_input_tax']['vat_refund_tcc_claimed'] +
        totals['less_deductions_from_input_tax']['less_deductions_from_input_tax_others']
    )

    totals['total_allowable_input_tax'] = totals['total_available_input_tax'] - totals['total_deductions_from_input_tax']
    totals['net_vat_payable'] = totals['total_output_tax_due'] - totals['total_allowable_input_tax']
    totals['tax_still_payable'] = totals['net_vat_payable'] - totals['total_tax_credit_payments']
    totals['total_amount_payable'] = totals['tax_still_payable'] + totals['penalties']['total']

    return totals, from_date, to_date

def get_data(filters):
    company = filters.get("company")
    year = filters.get("year")
    quarter = filters.get("quarter")

    totals, _, _ = compute_totals(company, year, quarter)

    data = [
        {
            'bir_2550q': '✓',
            'total_sales_receipts': totals['total_sales_receipts'],
            'total_output_tax_due': totals['total_output_tax_due'],
            'total_current_purchases': totals['total_current_purchases'],
            'total_allowable_input_tax': totals['total_allowable_input_tax'],
            'total_amount_payable': totals['total_amount_payable']
        }
    ]
    return data

def get_columns():
    columns = [
        {
            "fieldname": "bir_2550q",
            "label": _("BIR 2550Q"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "total_sales_receipts",
            "label": _("Total Sales/Receipts (Item 14D)"),
            "fieldtype": "Currency",
            "width": 200
        },
        {
            "fieldname": "total_output_tax_due",
            "label": _("Total Output Tax"),
            "fieldtype": "Currency",
            "width": 200
        },
        {
            "fieldname": "total_current_purchases",
            "label": _("Total Current Purchase (Item 18P)"),
            "fieldtype": "Currency",
            "width": 200
        },
        {
            "fieldname": "total_allowable_input_tax",
            "label": _("Total Input Tax"),
            "fieldtype": "Currency",
            "width": 200
        },
         {
            "fieldname": "total_amount_payable",
            "label": _("Total Amount Payable"),
            "fieldtype": "Currency",
            "width": 200
        }
    ]

    return columns

@frappe.whitelist()
def bir_2550q(company, year, quarter, 
              input_tax_carried_over_from_previous_period, input_tax_deferred_on_capital_goods_exceeding_1m_from_previous_period,
              transitional_input_tax, presumptive_input_tax, allowable_input_tax_others,
              input_tax_deferred_on_capital_goods_from_previous_period_1m_up,
              input_tax_directly_attributable_to_exempt_sales, vat_refund_tcc_claimed, less_deductions_from_input_tax_others,
              surcharge, compromise, interest,
              response_type="pdf"):
    precision = cint(frappe.db.get_default("currency_precision")) or 2
    report_is_permitted('BIR 2550Q')

    totals, from_date, to_date = compute_totals(
        company, year, quarter,
        input_tax_carried_over_from_previous_period,
        input_tax_deferred_on_capital_goods_exceeding_1m_from_previous_period,
        transitional_input_tax, presumptive_input_tax, allowable_input_tax_others,
        input_tax_deferred_on_capital_goods_from_previous_period_1m_up,
        input_tax_directly_attributable_to_exempt_sales, vat_refund_tcc_claimed,
        less_deductions_from_input_tax_others, surcharge, compromise, interest
    )

    context = {
        'company': get_company_information(company),
        'year': year,
        'quarter': quarter,
        'from_date': from_date,
        'to_date': to_date,
        'totals': totals
    }

    filename = "BIR 2550Q {} {} {}".format(company, year, quarter)
    
    context["build_version"] = frappe.utils.get_build_version()
    context["bir_form_images"] = get_bir_form_images("2550Q-1.png", "2550Q-2.png", "2550Q-3.png")
    html = frappe.render_template("templates/bir_forms/bir_2550q_template.html", context)
    options["page-size"] = "Legal"

    return_pdf_document(html, filename, options, response_type)