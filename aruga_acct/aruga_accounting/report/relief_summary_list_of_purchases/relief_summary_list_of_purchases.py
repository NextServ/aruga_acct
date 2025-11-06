# Copyright (c) 2013, SERVIO Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate
from aruga_acct.aruga_accounting.utils import get_company_information, get_supplier_information, get_formatted_full_name
from aruga_acct.aruga_accounting.bir_forms import return_document
import json
import calendar

def execute(filters=None):
    columns, data = [], []

    data = get_data(filters.company, filters.year, filters.month)
    columns = get_columns()

    return columns, data

def get_data(company, year, month):
    data = []

    tax_declaration_company_setup = None
    try:
        tax_declaration_company_setup = frappe.get_doc('Tax Declaration Company Setup', company)
    except:
        frappe.throw("Please create a Tax Declaration Company Setup record for {0}".format(company))

    pi_base_net_amounts = frappe.db.sql("""
        SELECT 
            pi.name, 
            pi.supplier,
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
            AND YEAR(pi.posting_date) = %s
            AND MONTH(pi.posting_date) = %s
        GROUP BY pi.name, pi.supplier, (COALESCE(NULLIF(pii.item_code, ''), pii.item_name)), pii.item_tax_template, pi.taxes_and_charges;
        """, (company, year, month), as_dict=1)

    pi_base_tax_amounts = frappe.db.sql("""
        SELECT
            pi.name,
            pi.supplier,
            ptac.base_tax_amount,
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
            AND ptac.base_tax_amount >= 0 AND ptac.add_deduct_tax = 'Add'
            AND (a.account_type in ('Tax', 'Payable', '') or a.account_type is NULL)
            AND pi.company = %s
            AND YEAR(pi.posting_date) = %s
            AND MONTH(pi.posting_date) = %s
        """, (company, year, month), as_dict=1)

    last_day_of_the_month = '{MM}/{DD}/{YYYY}'.format(MM=('0' + str(month))[-2:],DD=calendar.monthrange(int(year), int(month))[1], YYYY=year)

    for tax_line in pi_base_tax_amounts:
        item_wise_tax_detail = json.loads(tax_line.item_wise_tax_detail)
        for item in item_wise_tax_detail.keys():
            # loop to find net amount
            for item_net_amount in pi_base_net_amounts:
                if item_net_amount.name == tax_line.name and item_net_amount.item_name == item:
                    item_tax_template = item_net_amount.item_tax_template
                    taxes_and_charges = item_net_amount.taxes_and_charges
                    
                    document_row = None
                    document_row = next((row for row in data if row.get('purchase_invoice') == item_net_amount.name), None)
                    # document_row = (row for row in data if row.get('supplier') == item_net_amount.supplier)
                    if not document_row:
                        supplier_information = get_supplier_information(item_net_amount.supplier)
                        document_row = {
                            'purchase_invoice': item_net_amount.name,
                            'taxable_month': last_day_of_the_month,
                            'supplier': item_net_amount.supplier,
                            'full_name': get_formatted_full_name(supplier_information['contact_last_name'], 
                                supplier_information['contact_first_name'], supplier_information['contact_middle_name']),
                            'supplier_type': supplier_information['supplier_type'],
                            'tin': supplier_information['tin'],
                            'branch_code': supplier_information['branch_code'],
                            'tin_with_dash': supplier_information['tin_with_dash'][:11],
                            'contact_first_name': supplier_information['contact_first_name'],
                            'contact_middle_name': supplier_information['contact_middle_name'],
                            'contact_last_name': supplier_information['contact_last_name'],
                            'address_line1': supplier_information['address_line1'],
                            'address_line2': supplier_information['address_line2'],
                            'city': supplier_information['city'],
                            'address': supplier_information['address_line1']
                                 + (" {0}".format(supplier_information['address_line2']) if supplier_information['address_line2'] else "")
                                 + (" {0}".format(supplier_information['city']) if supplier_information['city'] else ""),
                            'zero_rated': 0,
                            'exempt': 0,
                            'gross_taxable': 0,
                            'services': 0,
                            'other_than_capital_goods': 0,
                            'capital_goods': 0,
                            'taxable_net': 0,
                            'input_tax': 0,
                        }

                        data.append(document_row)
                        
                    if tax_declaration_company_setup.item_zero_rated_purchase and item_tax_template == tax_declaration_company_setup.item_zero_rated_purchase:
                        document_row['zero_rated'] += flt(item_net_amount.base_net_amount, 2)
                    elif tax_declaration_company_setup.zero_rated_purchase and taxes_and_charges == tax_declaration_company_setup.zero_rated_purchase:
                        document_row['zero_rated'] += flt(item_net_amount.base_net_amount, 2)
                        
                    if tax_declaration_company_setup.item_exempt_purchase and item_tax_template == tax_declaration_company_setup.item_exempt_purchase:
                        document_row['exempt'] += flt(item_net_amount.base_net_amount, 2)
                    elif tax_declaration_company_setup.exempt_purchase and taxes_and_charges == tax_declaration_company_setup.exempt_purchase:
                        document_row['exempt'] += flt(item_net_amount.base_net_amount, 2)

                    if tax_declaration_company_setup.item_domestic_purchase_of_services and item_tax_template == tax_declaration_company_setup.item_domestic_purchase_of_services:
                        document_row['services'] += flt(item_net_amount.base_net_amount, 2)
                        document_row['input_tax'] += flt(item_wise_tax_detail[item][1], 2)
                    elif tax_declaration_company_setup.domestic_purchase_of_services and taxes_and_charges == tax_declaration_company_setup.domestic_purchase_of_services:
                        document_row['services'] += flt(item_net_amount.base_net_amount, 2)
                        document_row['input_tax'] += flt(item_wise_tax_detail[item][1], 2)
                        
                    if tax_declaration_company_setup.item_domestic_purchases_of_goods and item_tax_template == tax_declaration_company_setup.item_domestic_purchases_of_goods:
                        document_row['other_than_capital_goods'] += flt(item_net_amount.base_net_amount, 2)
                        document_row['input_tax'] += flt(item_wise_tax_detail[item][1], 2)
                    elif tax_declaration_company_setup.domestic_purchases_of_goods and taxes_and_charges == tax_declaration_company_setup.domestic_purchases_of_goods:
                        document_row['other_than_capital_goods'] += flt(item_net_amount.base_net_amount, 2)
                        document_row['input_tax'] += flt(item_wise_tax_detail[item][1], 2)
                        
                    if tax_declaration_company_setup.item_capital_goods and item_tax_template == tax_declaration_company_setup.item_capital_goods:
                        document_row['capital_goods'] += flt(item_net_amount.base_net_amount, 2)
                        document_row['input_tax'] += flt(item_wise_tax_detail[item][1], 2)
                    elif tax_declaration_company_setup.capital_goods and taxes_and_charges == tax_declaration_company_setup.capital_goods:
                        document_row['capital_goods'] += flt(item_net_amount.base_net_amount, 2)
                        document_row['input_tax'] += flt(item_wise_tax_detail[item][1], 2)

                    # net amount row is found, exit loop
                    break

    for row in data:
        row['taxable_net'] = row['services'] + row['other_than_capital_goods'] + row['capital_goods']
        row['gross_taxable'] = row['taxable_net'] + row['input_tax']
        row['total_purchases'] = row['taxable_net'] + row['zero_rated'] + row['exempt']
        # row['total_purchases'] = frappe.db.get_value('Purchase Invoice', row['purchase_invoice'], 'base_grand_total')

    return data

@frappe.whitelist()
def generate_slp_data_file(company, year, month, non_creditable=0, response_type="download"):
    fiscal_month_end = None
    try:
        fiscal_month_end = frappe.db.get_value('PH Localization Company Setup', company, 'fiscal_month_end')
    except:
        frappe.throw("Please create a PH Localization Company Setup record for {0}".format(company))

    data = get_data(company, year, month)

    fiscal_month_end = (fiscal_month_end if fiscal_month_end else 12)

    sum_exempt = sum(item['exempt'] for item in data)
    sum_zero_rated = sum(item['zero_rated'] for item in data)
    
    sum_services = sum(item['services'] for item in data)    
    sum_other_than_capital_goods = sum(item['other_than_capital_goods'] for item in data)    
    sum_capital_goods = sum(item['capital_goods'] for item in data)

    sum_taxable_net = sum(item['taxable_net'] for item in data)
    sum_input_tax = sum(item['input_tax'] for item in data)
    sum_gross_taxable = sum(item['gross_taxable'] for item in data)
    sum_total_purchases = sum(item['total_purchases'] for item in data)

    non_creditable_input_tax = flt(non_creditable)
    creditable_input_tax = sum_input_tax - non_creditable_input_tax

    company_information = get_company_information(company)
    file_extension = "dat"

    content = ''
    header = ''

    return_period = '{MM}/{YYYY}'.format(MM=('0' + str(month))[-2:], YYYY=year)
    return_period_no_slash = '{MM}{YYYY}'.format(MM=('0' + str(month))[-2:], YYYY=year)
    last_day_of_the_month = '{MM}/{DD}/{YYYY}'.format(MM=('0' + str(month))[-2:],DD=calendar.monthrange(int(year), int(month))[1], YYYY=year)

    header = '{next}'.format(header=header, next='H')
    header = '{header},{next}'.format(header=header, next='P')
    header = '{header},"{next}"'.format(header=header, next=company_information['tin'].upper()[:9])
    header = '{header},"{next}"'.format(header=header, next=company_information['company_name'].upper()[:50])
    header = '{header},"{next}"'.format(header=header, next='') # blank last, first, middle name? EN user will always be company
    header = '{header},"{next}"'.format(header=header, next='')
    header = '{header},"{next}"'.format(header=header, next='')
    header = '{header},"{next}"'.format(header=header, next=company_information['registered_name'].upper()[:50])
    header = '{header},"{next}"'.format(header=header, next=(company_information['address_line1'] + ' ' + company_information['address_line2']).upper().strip()[:50])
    header = '{header},"{next}"'.format(header=header, next=company_information['city'].upper().strip()[:50])
    header = '{header},{next}'.format(header=header, next="{:.2f}".format(flt(sum_exempt, 2)))
    header = '{header},{next}'.format(header=header, next="{:.2f}".format(flt(sum_zero_rated, 2)))
    header = '{header},{next}'.format(header=header, next="{:.2f}".format(flt(sum_services, 2)))
    header = '{header},{next}'.format(header=header, next="{:.2f}".format(flt(sum_capital_goods, 2)))
    header = '{header},{next}'.format(header=header, next="{:.2f}".format(flt(sum_other_than_capital_goods, 2)))
    header = '{header},{next}'.format(header=header, next="{:.2f}".format(flt(sum_input_tax, 2)))
    header = '{header},{next}'.format(header=header, next="{:.2f}".format(flt(creditable_input_tax, 2)))
    header = '{header},{next}'.format(header=header, next="{:.2f}".format(flt(non_creditable_input_tax, 2)))
    header = '{header},{next}'.format(header=header, next=company_information['rdo_code'][:3])
    header = '{header},{next}'.format(header=header, next=last_day_of_the_month[:10])
    header = '{header},{next}'.format(header=header, next=fiscal_month_end)

    content = header + '\n'
    details = ''
    total_base_tax_base = 0
    total_base_tax_withheld = 0

    for entry in data:
        details = details + '{next}'.format(details=details, next='D')
        details = '{details},{next}'.format(details=details, next='P')
        details = '{details},"{next}"'.format(details=details, next=entry['tin'][:9])
        details = '{details},"{next}"'.format(details=details, next=entry['supplier'].upper()[:50])
        
        details = '{details},"{next}"'.format(details=details, next=(entry['contact_last_name'].upper()[:30] if entry['supplier_type'] == 'Individual' else ''))
        details = '{details},"{next}"'.format(details=details, next=(entry['contact_first_name'].upper()[:30] if entry['supplier_type'] == 'Individual' else ''))
        details = '{details},"{next}"'.format(details=details, next=(entry['contact_middle_name'].upper()[:30] if entry['supplier_type'] == 'Individual' else ''))

        details = '{details},"{next}"'.format(details=details, next=entry['address_line1'].upper()[:50])
        details = '{details},"{next}"'.format(details=details, next=entry['city'].upper()[:50])
        details = '{details},{next}'.format(details=details, next="{:.2f}".format(flt(entry['exempt'], 2)))
        details = '{details},{next}'.format(details=details, next="{:.2f}".format(flt(entry['zero_rated'], 2)))
        details = '{details},{next}'.format(details=details, next="{:.2f}".format(flt(entry['services'], 2)))
        details = '{details},{next}'.format(details=details, next="{:.2f}".format(flt(entry['capital_goods'], 2)))
        details = '{details},{next}'.format(details=details, next="{:.2f}".format(flt(entry['other_than_capital_goods'], 2)))
        details = '{details},{next}'.format(details=details, next="{:.2f}".format(flt(entry['input_tax'], 2)))
        details = '{details},{next}'.format(details=details, next=company_information['tin'].upper()[:9])
        details = '{details},{next}'.format(details=details, next=last_day_of_the_month[:10])

        details = details + '\n'
    
    content = content + details

    filename = "{tin}P{return_period}".format(tin=company_information['tin'][:9],return_period=return_period_no_slash)

    return_document(content, filename, file_extension, response_type)

def get_columns():
    columns = [
        {
            "fieldname": "taxable_month",
            "label": _("Taxable Month"),
            "fieldtype": "Date",
            "width": 180
        },
        {
            "fieldname": "tin_with_dash",
            "label": _("TIN"),
            "fieldtype": "Data",
            "width": 180
        },
        {
            "fieldname": "supplier",
            "label": _("Registered Name"),
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 200
        },
        {
            "fieldname": "full_name",
            "label": _("Name of Supplier"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "address",
            "label": _("Supplier's Address"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "total_purchases",
            "label": _("Total Purchases"),
            "fieldtype": "Currency",
            "width": 200
        },
        {
            "fieldname": "exempt",
            "label": _("Exempt"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "zero_rated",
            "label": _("Zero Rated"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "taxable_net",
            "label": _("Taxable Net"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "services",
            "label": _("Services"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "capital_goods",
            "label": _("Capital Goods"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "other_than_capital_goods",
            "label": _("Other Than Capital Goods"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "input_tax",
            "label": _("Input Tax"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "gross_taxable",
            "label": _("Gross Taxable"),
            "fieldtype": "Currency",
            "width": 150
        },
    ]

    return columns