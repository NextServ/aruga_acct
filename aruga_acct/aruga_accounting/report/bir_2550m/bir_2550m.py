# Copyright (c) 2013, SERVIO Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, getdate
from frappe import _
import json

def get_accounts_from_template(template_name):
    """
    Fetch all account_head values from a Sales Taxes and Charges Template.
    Returns a list of account names configured in the template.
    """
    if not template_name:
        return []
    
    try:
        template_doc = frappe.get_doc('Sales Taxes and Charges Template', template_name)
        accounts = []
        for tax_row in template_doc.taxes:
            if hasattr(tax_row, 'account_head') and tax_row.account_head:
                accounts.append(tax_row.account_head)
        return accounts
    except:
        return []

def get_accounts_from_purchase_template(template_name):
    """
    Fetch all account_head values from a Purchase Taxes and Charges Template.
    Returns a list of account names configured in the template.
    """
    if not template_name:
        return []
    
    try:
        template_doc = frappe.get_doc('Purchase Taxes and Charges Template', template_name)
        accounts = []
        for tax_row in template_doc.taxes:
            if hasattr(tax_row, 'account_head') and tax_row.account_head:
                accounts.append(tax_row.account_head)
        return accounts
    except:
        return []

def account_matches_template(account_head, template_name):
    """
    Check if account_head matches a template.
    Supports:
    1. Direct match: account_head == template_name
    2. Template match: account_head is in the list of accounts configured in template
    """
    if not account_head or not template_name:
        return False
    
    # Direct match fallback
    if account_head == template_name:
        return True
    
    # Check if account is in template's accounts list
    template_accounts = get_accounts_from_template(template_name)
    return account_head in template_accounts

def account_matches_purchase_template(account_head, template_name):
    """
    Check if account_head matches a purchase template.
    Supports:
    1. Direct match: account_head == template_name
    2. Template match: account_head is in the list of accounts configured in template
    """
    if not account_head or not template_name:
        return False
    
    # Direct match fallback
    if account_head == template_name:
        return True
    
    # Check if account is in template's accounts list
    template_accounts = get_accounts_from_purchase_template(template_name)
    return account_head in template_accounts

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
            AND si.is_return = 0
            AND YEAR(si.posting_date) = %s
            AND MONTH(si.posting_date) = %s
        GROUP BY si.name, (COALESCE(NULLIF(sii.item_code, ''), sii.item_name)), sii.item_tax_template, si.taxes_and_charges;
        """, (company, year, month), as_dict=1)

    si_base_tax_amounts = frappe.db.sql("""
        SELECT
            si.name,
            stac.account_head,
            stac.base_tax_amount AS base_tax_amount,
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
            AND si.is_return = 0
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
            AND pi.is_return = 0
            AND YEAR(pi.posting_date) = %s
            AND MONTH(pi.posting_date) = %s
        GROUP BY pi.name, (COALESCE(NULLIF(pii.item_code, ''), pii.item_name)), pii.item_tax_template, pi.taxes_and_charges;
        """, (company, year, month), as_dict=1)

    pi_base_tax_amounts = frappe.db.sql("""
        SELECT
            pi.name,
            ptac.account_head,
            ptac.base_tax_amount AS base_tax_amount,
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
            AND pi.is_return = 0
            AND (a.account_type IN ('Tax', 'Payable', '') OR a.account_type IS NULL)
            AND a.name NOT LIKE '%%Withholding%%'
            AND pi.company = %s
            AND YEAR(pi.posting_date) = %s
            AND MONTH(pi.posting_date) = %s
        """, (company, year, month), as_dict=1)

    # Process Sales Invoices
    for tax_line in si_base_tax_amounts:
        item_wise_tax_detail = json.loads(tax_line.item_wise_tax_detail)
        account_head = tax_line.get('account_head', '')
        
        for item in item_wise_tax_detail.keys():
            matched = False
            
            # loop to find net amount
            for item_net_amount in si_base_net_amounts:                
                if item_net_amount.name == tax_line.name and item_net_amount.item_name == item:
                    item_tax_template = item_net_amount.item_tax_template
                    taxes_and_charges = item_net_amount.taxes_and_charges

                    # VAT Sales matching (template or account)
                    if not matched and tax_declaration_company_setup.item_vat_sales and item_tax_template == tax_declaration_company_setup.item_vat_sales:
                        totals['vat_sales']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['vat_sales']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        matched = True
                    elif not matched and tax_declaration_company_setup.vat_sales and (taxes_and_charges == tax_declaration_company_setup.vat_sales or account_matches_template(account_head, tax_declaration_company_setup.vat_sales)):
                        totals['vat_sales']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['vat_sales']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        matched = True
                        
                    # Sales to Government matching
                    if not matched and tax_declaration_company_setup.item_sales_to_government and item_tax_template == tax_declaration_company_setup.item_sales_to_government:
                        totals['sales_to_government']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['sales_to_government']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        matched = True
                    elif not matched and tax_declaration_company_setup.sales_to_government and (taxes_and_charges == tax_declaration_company_setup.sales_to_government or account_matches_template(account_head, tax_declaration_company_setup.sales_to_government)):
                        totals['sales_to_government']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['sales_to_government']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        matched = True
                        
                    # Zero Rated Sales matching
                    if not matched and tax_declaration_company_setup.item_zero_rated_sales and item_tax_template == tax_declaration_company_setup.item_zero_rated_sales:
                        totals['zero_rated_sales']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['zero_rated_sales']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        matched = True
                    elif not matched and tax_declaration_company_setup.zero_rated_sales and (taxes_and_charges == tax_declaration_company_setup.zero_rated_sales or account_matches_template(account_head, tax_declaration_company_setup.zero_rated_sales)):
                        totals['zero_rated_sales']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['zero_rated_sales']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        matched = True
                        
                    # Exempt Sales matching
                    if not matched and tax_declaration_company_setup.item_exempt_sales and item_tax_template == tax_declaration_company_setup.item_exempt_sales:
                        totals['exempt_sales']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['exempt_sales']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        matched = True
                    elif not matched and tax_declaration_company_setup.exempt_sales and (taxes_and_charges == tax_declaration_company_setup.exempt_sales or account_matches_template(account_head, tax_declaration_company_setup.exempt_sales)):
                        totals['exempt_sales']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['exempt_sales']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        matched = True

                    # Fallback: if no template matching rules apply, add to VAT Sales (for reports without templates)
                    if not matched:
                        totals['vat_sales']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['vat_sales']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)

                    # net amount row is found, exit loop
                    break

    # Process Purchase Invoices
    # item_wise_tax_detail looks like {"FF01":[5.0,599.0506],"1234":[12.0,146.20896],"Item 8":[12.0,60.006594]} 
    for tax_line in pi_base_tax_amounts:
        item_wise_tax_detail = json.loads(tax_line.item_wise_tax_detail)
        account_head = tax_line.get('account_head', '')
        
        for item in item_wise_tax_detail.keys():
            matched = False
            
            # loop to find net amount
            for item_net_amount in pi_base_net_amounts:                
                if item_net_amount.name == tax_line.name and item_net_amount.item_name == item:
                    item_tax_template = item_net_amount.item_tax_template
                    taxes_and_charges = item_net_amount.taxes_and_charges
                    
                    # Capital Goods matching
                    if not matched and tax_declaration_company_setup.item_capital_goods and item_tax_template == tax_declaration_company_setup.item_capital_goods:
                        if flt(item_wise_tax_detail[item][1], 2) < 1000000:
                            totals['capital_goods']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                            totals['capital_goods']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        else:
                            totals['capital_goods_exceeding_1m']['total_base_tax_base'] = flt(item_net_amount.base_net_amount, 2)
                            totals['capital_goods_exceeding_1m']['total_base_tax_amount'] = flt(item_wise_tax_detail[item][1], 2)
                        matched = True
                    elif not matched and tax_declaration_company_setup.capital_goods and (taxes_and_charges == tax_declaration_company_setup.capital_goods or account_matches_purchase_template(account_head, tax_declaration_company_setup.capital_goods)):
                        if flt(item_wise_tax_detail[item][1], 2) < 1000000:
                            totals['capital_goods']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                            totals['capital_goods']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        else:
                            totals['capital_goods_exceeding_1m']['total_base_tax_base'] = flt(item_net_amount.base_net_amount, 2)
                            totals['capital_goods_exceeding_1m']['total_base_tax_amount'] = flt(item_wise_tax_detail[item][1], 2)
                        matched = True
                        
                    # Domestic Purchases of Goods matching
                    elif not matched and tax_declaration_company_setup.item_domestic_purchases_of_goods and item_tax_template == tax_declaration_company_setup.item_domestic_purchases_of_goods:
                        totals['domestic_purchases_of_goods']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['domestic_purchases_of_goods']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        matched = True
                    elif not matched and tax_declaration_company_setup.domestic_purchases_of_goods and (taxes_and_charges == tax_declaration_company_setup.domestic_purchases_of_goods or account_matches_purchase_template(account_head, tax_declaration_company_setup.domestic_purchases_of_goods)):
                        totals['domestic_purchases_of_goods']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['domestic_purchases_of_goods']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        matched = True
                        
                    # Importation of Goods matching
                    elif not matched and tax_declaration_company_setup.item_importation_of_goods and item_tax_template == tax_declaration_company_setup.item_importation_of_goods:
                        totals['importation_of_goods']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['importation_of_goods']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        matched = True
                    elif not matched and tax_declaration_company_setup.importation_of_goods and (taxes_and_charges == tax_declaration_company_setup.importation_of_goods or account_matches_purchase_template(account_head, tax_declaration_company_setup.importation_of_goods)):
                        totals['importation_of_goods']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['importation_of_goods']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        matched = True
                        
                    # Domestic Purchase of Services matching
                    elif not matched and tax_declaration_company_setup.item_domestic_purchase_of_services and item_tax_template == tax_declaration_company_setup.item_domestic_purchase_of_services:
                        totals['domestic_purchase_of_services']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['domestic_purchase_of_services']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        matched = True
                    elif not matched and tax_declaration_company_setup.domestic_purchase_of_services and (taxes_and_charges == tax_declaration_company_setup.domestic_purchase_of_services or account_matches_purchase_template(account_head, tax_declaration_company_setup.domestic_purchase_of_services)):
                        totals['domestic_purchase_of_services']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['domestic_purchase_of_services']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        matched = True
                        
                    # Services Rendered by Non-Residents matching
                    elif not matched and tax_declaration_company_setup.item_services_rendered_by_non_residents and item_tax_template == tax_declaration_company_setup.item_services_rendered_by_non_residents:
                        totals['services_rendered_by_non_residents']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['services_rendered_by_non_residents']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        matched = True
                    elif not matched and tax_declaration_company_setup.services_rendered_by_non_residents and (taxes_and_charges == tax_declaration_company_setup.services_rendered_by_non_residents or account_matches_purchase_template(account_head, tax_declaration_company_setup.services_rendered_by_non_residents)):
                        totals['services_rendered_by_non_residents']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['services_rendered_by_non_residents']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        matched = True
                        
                    # Not qualified for input tax (zero rated and exempt) matching
                    elif not matched and tax_declaration_company_setup.item_zero_rated_purchase and item_tax_template == tax_declaration_company_setup.item_zero_rated_purchase:
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        matched = True
                    elif not matched and tax_declaration_company_setup.zero_rated_purchase and (taxes_and_charges == tax_declaration_company_setup.zero_rated_purchase or account_matches_purchase_template(account_head, tax_declaration_company_setup.zero_rated_purchase)):
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        matched = True
                        
                    elif not matched and tax_declaration_company_setup.item_exempt_purchase and item_tax_template == tax_declaration_company_setup.item_exempt_purchase:
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        matched = True
                    elif not matched and tax_declaration_company_setup.exempt_purchase and (taxes_and_charges == tax_declaration_company_setup.exempt_purchase or account_matches_purchase_template(account_head, tax_declaration_company_setup.exempt_purchase)):
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['purchases_not_qualified_for_input_tax']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)
                        matched = True
                    
                    # Others category (fallback for unmatched items)
                    if not matched:
                        totals['others']['total_base_tax_base'] += flt(item_net_amount.base_net_amount, 2)
                        totals['others']['total_base_tax_amount'] += flt(item_wise_tax_detail[item][1], 2)

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