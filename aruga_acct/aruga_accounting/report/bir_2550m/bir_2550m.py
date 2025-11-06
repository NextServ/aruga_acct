# Copyright (c) 2013, SERVIO Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, getdate
from frappe import _
import json

def execute(filters=None):
    if not filters:
        filters = {}
    
    company = filters.get("company")
    year = filters.get("year")
    month = filters.get("month")
    
    try:
        tax_declaration_company_setup = frappe.get_doc('Tax Declaration Company Setup', company)
    except:
        frappe.throw("Please create a Tax Declaration Company Setup record for {0}".format(company))

    columns, data = [], []
    data = get_data(filters, tax_declaration_company_setup)
    columns = get_columns()
    return columns, data

def get_data(filters, tax_declaration_company_setup):
    company = filters.get("company")
    year = filters.get("year")
    month = filters.get("month")

    totals = {
        'vat_sales': {
            'total_base_tax_base': 0,
            'total_base_tax_amount': 0
        },
        'sales_to_government': {
            'total_base_tax_base': 0,
            'total_base_tax_amount': 0
        },
        'zero_rated_sales': {
            'total_base_tax_base': 0,
            'total_base_tax_amount': 0
        },
        'exempt_sales': {
            'total_base_tax_base': 0,
            'total_base_tax_amount': 0
        },
        'total_sales_receipts': 0,
        'total_output_tax_due': 0,

        'total_other_allowable_input_tax': 0, 
        'capital_goods': {
            'total_base_tax_base': 0,
            'total_base_tax_amount': 0
        },
        'capital_goods_exceeding_1m': {
            'total_base_tax_base': 0,
            'total_base_tax_amount': 0
        },
        'domestic_purchases_of_goods': {
            'total_base_tax_base': 0,
            'total_base_tax_amount': 0
        },
        'importation_of_goods': {
            'total_base_tax_base': 0,
            'total_base_tax_amount': 0
        },
        'domestic_purchase_of_services': {
            'total_base_tax_base': 0,
            'total_base_tax_amount': 0
        },
        'services_rendered_by_non_residents': {
            'total_base_tax_base': 0,
            'total_base_tax_amount': 0
        },
        'purchases_not_qualified_for_input_tax': {
            'total_base_tax_base': 0,
            'total_base_tax_amount': 0
        },
        'others': {
            'total_base_tax_base': 0,
            'total_base_tax_amount': 0
        },
        'total_current_purchases': 0,
        'total_available_input_tax': 0,
        'ratable_portion_of_input_tax_not_directly_attributable': 0,
        'total_deductions_from_input_tax': 0,
        'total_allowable_input_tax': 0,
        'net_vat_payable': 0,
        'total_tax_credit_payments': 0,
        'tax_still_payable': 0,
   
        'total_amount_payable': 0,
        # 'directly_attributable_to_exempt_sales': {
        #     'total_base_tax_base': 0,
        #     'total_base_tax_amount': 0
        # },
        # 'directly_attributable_to_sale_to_government': {
        #     'total_base_tax_base': 0,
        #     'total_base_tax_amount': 0
        # }
    }

    # Fetch Sales Invoice data
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
            si.company = %s
            AND si.docstatus = 1
            AND YEAR(si.posting_date) = %s
            AND MONTH(si.posting_date) = %s
        GROUP BY si.name, (COALESCE(NULLIF(sii.item_code, ''), sii.item_name)), sii.item_tax_template, si.taxes_and_charges;
        """, (company, year, month), as_dict=1)

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
            AND YEAR(si.posting_date) = %s
            AND MONTH(si.posting_date) = %s
        """, (company, year, month), as_dict=1)

    # Fetch Purchase Invoice data
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
            pi.company = %s
            AND pi.docstatus = 1
            AND YEAR(pi.posting_date) = %s
            AND MONTH(pi.posting_date) = %s
        GROUP BY pi.name, (COALESCE(NULLIF(pii.item_code, ''), pii.item_name)), pii.item_tax_template, pi.taxes_and_charges;
        """, (company, year, month), as_dict=1)

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
            AND YEAR(pi.posting_date) = %s
            AND MONTH(pi.posting_date) = %s
        """, (company, year, month), as_dict=1)

    # Process Sales Invoices
    for tax_line in si_base_tax_amounts:
        item_wise_tax_detail = json.loads(tax_line.item_wise_tax_detail)
        for item in item_wise_tax_detail.keys():
            # loop to find net amount
            for item_net_amount in si_base_net_amounts:                
                if item_net_amount.name == tax_line.name and item_net_amount.item_name == item:
                    item_tax_template = item_net_amount.item_tax_template
                    taxes_and_charges = item_net_amount.taxes_and_charges

                    if tax_declaration_company_setup.item_vat_sales and item_tax_template == tax_declaration_company_setup.item_vat_sales:
                        totals['vat_sales']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['vat_sales']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                    elif tax_declaration_company_setup.vat_sales and taxes_and_charges == tax_declaration_company_setup.vat_sales:
                        totals['vat_sales']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['vat_sales']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        
                    if tax_declaration_company_setup.item_sales_to_government and item_tax_template == tax_declaration_company_setup.item_sales_to_government:
                        totals['sales_to_government']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['sales_to_government']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                    elif tax_declaration_company_setup.sales_to_government and taxes_and_charges == tax_declaration_company_setup.sales_to_government:
                        totals['sales_to_government']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['sales_to_government']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        
                    if tax_declaration_company_setup.item_zero_rated_sales and item_tax_template == tax_declaration_company_setup.item_zero_rated_sales:
                        totals['zero_rated_sales']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['zero_rated_sales']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                    elif tax_declaration_company_setup.zero_rated_sales and taxes_and_charges == tax_declaration_company_setup.zero_rated_sales:
                        totals['zero_rated_sales']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['zero_rated_sales']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        
                    if tax_declaration_company_setup.item_exempt_sales and item_tax_template == tax_declaration_company_setup.item_exempt_sales:
                        totals['exempt_sales']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['exempt_sales']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                    elif tax_declaration_company_setup.exempt_sales and taxes_and_charges == tax_declaration_company_setup.exempt_sales:
                        totals['exempt_sales']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['exempt_sales']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)

                    # net amount row is found, exit loop
                    break

    # Process Purchase Invoices
    # item_wise_tax_detail looks like {"FF01":[5.0,599.0506],"1234":[12.0,146.20896],"Item 8":[12.0,60.006594]} 
    for tax_line in pi_base_tax_amounts:
        item_wise_tax_detail = json.loads(tax_line.item_wise_tax_detail)
        for item in item_wise_tax_detail.keys():
            # loop to find net amount
            for item_net_amount in pi_base_net_amounts:                
                if item_net_amount.name == tax_line.name and item_net_amount.item_name == item:
                    item_tax_template = item_net_amount.item_tax_template
                    taxes_and_charges = item_net_amount.taxes_and_charges
                    
                    if tax_declaration_company_setup.item_capital_goods and item_tax_template == tax_declaration_company_setup.item_capital_goods:
                        if flt(item_wise_tax_detail[item][1], 2) < 1000000:
                            totals['capital_goods']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                            totals['capital_goods']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        else:
                            totals['capital_goods_exceeding_1m']['total_base_tax_base'] = flt(item_net_amount.base_net_amount, 2)
                            totals['capital_goods_exceeding_1m']['total_base_tax_amount'] = flt(item_wise_tax_detail[item][1], 2)
                    elif tax_declaration_company_setup.capital_goods and taxes_and_charges == tax_declaration_company_setup.capital_goods:
                        if flt(item_wise_tax_detail[item][1], 2) < 1000000:
                            totals['capital_goods']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                            totals['capital_goods']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        else:
                            totals['capital_goods_exceeding_1m']['total_base_tax_base'] = flt(item_net_amount.base_net_amount, 2)
                            totals['capital_goods_exceeding_1m']['total_base_tax_amount'] = flt(item_wise_tax_detail[item][1], 2)
                        
                    elif tax_declaration_company_setup.item_domestic_purchases_of_goods and item_tax_template == tax_declaration_company_setup.item_domestic_purchases_of_goods:
                        totals['domestic_purchases_of_goods']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['domestic_purchases_of_goods']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                    elif tax_declaration_company_setup.domestic_purchases_of_goods and taxes_and_charges == tax_declaration_company_setup.domestic_purchases_of_goods:
                        totals['domestic_purchases_of_goods']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['domestic_purchases_of_goods']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        
                    elif tax_declaration_company_setup.item_importation_of_goods and item_tax_template == tax_declaration_company_setup.item_importation_of_goods:
                        totals['importation_of_goods']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['importation_of_goods']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                    elif tax_declaration_company_setup.importation_of_goods and taxes_and_charges == tax_declaration_company_setup.importation_of_goods:
                        totals['importation_of_goods']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['importation_of_goods']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        
                    elif tax_declaration_company_setup.item_domestic_purchase_of_services and item_tax_template == tax_declaration_company_setup.item_domestic_purchase_of_services:
                        totals['domestic_purchase_of_services']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['domestic_purchase_of_services']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                    elif tax_declaration_company_setup.domestic_purchase_of_services and taxes_and_charges == tax_declaration_company_setup.domestic_purchase_of_services:
                        totals['domestic_purchase_of_services']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['domestic_purchase_of_services']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        
                    elif tax_declaration_company_setup.item_services_rendered_by_non_residents and item_tax_template == tax_declaration_company_setup.item_services_rendered_by_non_residents:
                        totals['services_rendered_by_non_residents']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['services_rendered_by_non_residents']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                    elif tax_declaration_company_setup.services_rendered_by_non_residents and taxes_and_charges == tax_declaration_company_setup.services_rendered_by_non_residents:
                        totals['services_rendered_by_non_residents']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['services_rendered_by_non_residents']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        
                    # not qualified for input tax (zero rated and exempt)
                    elif tax_declaration_company_setup.item_zero_rated_purchase and item_tax_template == tax_declaration_company_setup.item_zero_rated_purchase:
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                    elif tax_declaration_company_setup.zero_rated_purchase and taxes_and_charges == tax_declaration_company_setup.zero_rated_purchase:
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        
                    elif tax_declaration_company_setup.item_exempt_purchase and item_tax_template == tax_declaration_company_setup.item_exempt_purchase:
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                    elif tax_declaration_company_setup.exempt_purchase and taxes_and_charges == tax_declaration_company_setup.exempt_purchase:
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                    # end - not qualified for input tax 
                        
                    elif tax_declaration_company_setup.item_others and item_tax_template == tax_declaration_company_setup.item_others:
                        totals['others']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['others']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                    elif tax_declaration_company_setup.others and taxes_and_charges == tax_declaration_company_setup.others:
                        totals['others']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['others']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                    
                    # others special handling, blank tax templates go to others
                    else:
                        totals['others']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['others']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                    
                    # TODO: exempt / government
                    # elif tax_declaration_company_setup.item_directly_attributable_to_exempt_sales and item_tax_template == tax_declaration_company_setup.item_directly_attributable_to_exempt_sales:
                    #     totals['directly_attributable_to_exempt_sales']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                    #     totals['directly_attributable_to_exempt_sales']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                    # elif tax_declaration_company_setup.directly_attributable_to_exempt_sales and taxes_and_charges == tax_declaration_company_setup.directly_attributable_to_exempt_sales:
                    #     totals['directly_attributable_to_exempt_sales']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                    #     totals['directly_attributable_to_exempt_sales']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        
                    # elif tax_declaration_company_setup.item_directly_attributable_to_sale_to_government and item_tax_template == tax_declaration_company_setup.item_directly_attributable_to_sale_to_government:
                    #     totals['directly_attributable_to_sale_to_government']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                    #     totals['directly_attributable_to_sale_to_government']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                    # elif tax_declaration_company_setup.directly_attributable_to_sale_to_government and taxes_and_charges == tax_declaration_company_setup.directly_attributable_to_sale_to_government:
                    #     totals['directly_attributable_to_sale_to_government']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                    #     totals['directly_attributable_to_sale_to_government']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)

                    # net amount row is found, exit loop
                    break

    # capital goods base exceeds 1m, move amounts
    # if totals['capital_goods']['total_base_tax_base'] > 1000000:
    #     totals['capital_goods_exceeding_1m']['total_base_tax_base'] = totals['capital_goods']['total_base_tax_base']
    #     totals['capital_goods_exceeding_1m']['total_base_tax_amount'] = totals['capital_goods']['total_base_tax_amount']

    #     totals['capital_goods']['total_base_tax_base'] = 0
    #     totals['capital_goods']['total_base_tax_amount'] = 0

    # Calculate totals
    totals['total_sales_receipts'] = totals['vat_sales']['total_base_tax_base'] + totals['sales_to_government']['total_base_tax_base'] \
        + totals['zero_rated_sales']['total_base_tax_base'] + totals['exempt_sales']['total_base_tax_base']

    totals['total_output_tax_due'] = totals['vat_sales']['total_base_tax_amount'] + totals['sales_to_government']['total_base_tax_amount']


    totals['total_current_purchases'] = totals['capital_goods']['total_base_tax_base'] + totals['capital_goods_exceeding_1m']['total_base_tax_base'] \
        + totals['domestic_purchases_of_goods']['total_base_tax_base'] + totals['importation_of_goods']['total_base_tax_base'] \
        + totals['domestic_purchase_of_services']['total_base_tax_base'] + totals['services_rendered_by_non_residents']['total_base_tax_base'] \
        + totals['purchases_not_qualified_for_input_tax']['total_base_tax_base'] + totals['others']['total_base_tax_base']

    totals['total_available_input_tax'] = totals['total_other_allowable_input_tax'] + totals['capital_goods']['total_base_tax_amount'] + totals['capital_goods_exceeding_1m']['total_base_tax_amount'] \
        + totals['domestic_purchases_of_goods']['total_base_tax_amount'] + totals['importation_of_goods']['total_base_tax_amount'] + totals['domestic_purchase_of_services']['total_base_tax_amount'] \
        + totals['services_rendered_by_non_residents']['total_base_tax_amount'] + totals['others']['total_base_tax_amount']



    totals['total_allowable_input_tax'] = totals['total_available_input_tax'] - totals['total_deductions_from_input_tax']
    totals['net_vat_payable'] = totals['total_output_tax_due'] - totals['total_allowable_input_tax']
    totals['tax_still_payable'] = totals['net_vat_payable'] - totals['total_tax_credit_payments']
    totals['total_amount_payable'] = totals['tax_still_payable'] # + totals['penalties']['total']

    totals['total_allowable_input_tax'] = totals['total_allowable_input_tax'] 
  
    # Format data for report
    data = [
        {
            'bir_2550m': '✓',
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
            "fieldname": "bir_2550m",
            "label": _("BIR 2550M"),
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