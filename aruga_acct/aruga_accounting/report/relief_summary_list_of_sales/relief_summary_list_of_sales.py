# Copyright (c) 2013, SERVIO Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate
from aruga_acct.aruga_accounting.utils import get_company_information, get_customer_information, get_formatted_full_name
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

    # si_customers = frappe.db.sql("""
    #     SELECT 
    #         si.customer
    #     FROM
    #         `tabSales Invoice` si
    #     WHERE
    #         si.company = %s
    #         AND si.docstatus = 1
    #         AND YEAR(si.posting_date) = %s
    #         AND MONTH(si.posting_date) = %s
    #     GROUP BY si.name, item_name, sii.item_tax_template, si.taxes_and_charges;
    #     """, (company, year, month), as_dict=1)

    # for row in si_customers:
    #     customer_information = get_customer_information(row.customer)
    #     row = {
    #         'customer': row.customer,
    #         'tin_with_dash': customer_information['tin_with_dash'],
    #         'total_sales': 0,
    #         'zero_rated': 0,
    #         'exempt': 0,
    #         'gross_taxable': 0,
    #         'taxable_net': 0,
    #         'output_tax': 0,
    #     }

    #     data.append(row)

    si_base_net_amounts = frappe.db.sql("""
        SELECT 
            si.name, 
            si.customer, 
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
            AND YEAR(si.posting_date) = %s
            AND MONTH(si.posting_date) = %s
        GROUP BY si.name, si.customer, (COALESCE(NULLIF(sii.item_code, ''), sii.item_name)), sii.item_tax_template, si.taxes_and_charges;
        """, (company, year, month), as_dict=1)

    si_base_tax_amounts = frappe.db.sql("""
        SELECT
            si.name,
            si.customer,
            stac.base_tax_amount,
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
            AND stac.base_tax_amount >= 0
            AND (a.account_type in ('Tax', 'Payable', '') or a.account_type is NULL)
            AND si.company = %s
            AND YEAR(si.posting_date) = %s
            AND MONTH(si.posting_date) = %s
        """, (company, year, month), as_dict=1)
        
    last_day_of_the_month = '{MM}/{DD}/{YYYY}'.format(MM=('0' + str(month))[-2:],DD=calendar.monthrange(int(year), int(month))[1], YYYY=year)

    for tax_line in si_base_tax_amounts:
        item_wise_tax_detail = json.loads(tax_line.item_wise_tax_detail)
        for item in item_wise_tax_detail.keys():
            # loop to find net amount
            for item_net_amount in si_base_net_amounts:                
                if item_net_amount.name == tax_line.name and item_net_amount.item_name == item:
                    item_tax_template = item_net_amount.item_tax_template
                    taxes_and_charges = item_net_amount.taxes_and_charges
                    
                    document_row = None
                    document_row = next((row for row in data if row.get('sales_invoice') == item_net_amount.name), None)
                    # document_row = (row for row in data if row.get('customer') == item_net_amount.customer)
                    if not document_row:
                        customer_information = get_customer_information(item_net_amount.customer)
                        document_row = {
                            'sales_invoice': item_net_amount.name,
                            'taxable_month': last_day_of_the_month,
                            'customer': item_net_amount.customer,
                            'full_name': get_formatted_full_name(customer_information['contact_last_name'], 
                                customer_information['contact_first_name'], customer_information['contact_middle_name']),
                            'customer_type': customer_information['customer_type'],
                            'tin': customer_information['tin'],
                            'branch_code': customer_information['branch_code'],
                            'tin_with_dash': customer_information['tin_with_dash'][:11],
                            'contact_first_name': customer_information['contact_first_name'],
                            'contact_middle_name': customer_information['contact_middle_name'],
                            'contact_last_name': customer_information['contact_last_name'],
                            'address_line1': customer_information['address_line1'],
                            'address_line2': customer_information['address_line2'],
                            'city': customer_information['city'],
                            'address': customer_information['address_line1']
                                 + (" {0}".format(customer_information['address_line2']) if customer_information['address_line2'] else "")
                                 + (" {0}".format(customer_information['city']) if customer_information['city'] else ""),
                            'total_sales': 0,
                            'zero_rated': 0,
                            'exempt': 0,
                            'gross_taxable': 0,
                            'taxable_net': 0,
                            'output_tax': 0,
                        }

                        data.append(document_row)

                    # taxable_net, zero_rated, exempt
                    # total_sales, gross_taxable, output_tax
                    if tax_declaration_company_setup.item_vat_sales and item_tax_template == tax_declaration_company_setup.item_vat_sales:
                        document_row['taxable_net'] += flt(item_net_amount.base_net_amount, 2)
                        document_row['output_tax'] += flt(item_wise_tax_detail[item][1], 2)
                    elif tax_declaration_company_setup.vat_sales and taxes_and_charges == tax_declaration_company_setup.vat_sales:
                        document_row['taxable_net'] += flt(item_net_amount.base_net_amount, 2)
                        document_row['output_tax'] += flt(item_wise_tax_detail[item][1], 2)
                        
                    if tax_declaration_company_setup.item_zero_rated_sales and item_tax_template == tax_declaration_company_setup.item_zero_rated_sales:
                        document_row['zero_rated'] += flt(item_net_amount.base_net_amount, 2)
                    elif tax_declaration_company_setup.zero_rated_sales and taxes_and_charges == tax_declaration_company_setup.zero_rated_sales:
                        document_row['zero_rated'] += flt(item_net_amount.base_net_amount, 2)
                        
                    if tax_declaration_company_setup.item_exempt_sales and item_tax_template == tax_declaration_company_setup.item_exempt_sales:
                        document_row['exempt'] += flt(item_net_amount.base_net_amount, 2)
                    elif tax_declaration_company_setup.exempt_sales and taxes_and_charges == tax_declaration_company_setup.exempt_sales:
                        document_row['exempt'] += flt(item_net_amount.base_net_amount, 2)

                    # net amount row is found, exit loop
                    break

    for row in data:
        row['gross_taxable'] = row['taxable_net'] + row['output_tax']
        row['total_sales'] = row['taxable_net'] + row['zero_rated'] + row['exempt']

    return data

@frappe.whitelist()
def generate_sls_data_file(company, year, month, response_type="download"):
    fiscal_month_end = None
    try:
        fiscal_month_end = frappe.db.get_value('PH Localization Company Setup', company, 'fiscal_month_end')
    except:
        frappe.throw("Please create a PH Localization Company Setup record for {0}".format(company))

    data = get_data(company, year, month)    
    
    fiscal_month_end = (fiscal_month_end if fiscal_month_end else 12)

    sum_exempt = sum(item['exempt'] for item in data)
    sum_zero_rated = sum(item['zero_rated'] for item in data)
    sum_taxable_net = sum(item['taxable_net'] for item in data)
    sum_output_tax = sum(item['output_tax'] for item in data)
    sum_gross_taxable = sum(item['gross_taxable'] for item in data)

    company_information = get_company_information(company)
    file_extension = "dat"

    content = ''
    header = ''

    return_period = '{MM}/{YYYY}'.format(MM=('0' + str(month))[-2:], YYYY=year)
    return_period_no_slash = '{MM}{YYYY}'.format(MM=('0' + str(month))[-2:], YYYY=year)
    last_day_of_the_month = '{MM}/{DD}/{YYYY}'.format(MM=('0' + str(month))[-2:],DD=calendar.monthrange(int(year), int(month))[1], YYYY=year)

    header = '{next}'.format(header=header, next='H')
    header = '{header},{next}'.format(header=header, next='S')
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
    header = '{header},{next}'.format(header=header, next="{:.2f}".format(flt(sum_taxable_net, 2)))
    header = '{header},{next}'.format(header=header, next="{:.2f}".format(flt(sum_output_tax, 2)))
    header = '{header},{next}'.format(header=header, next=company_information['rdo_code'][:3])
    header = '{header},{next}'.format(header=header, next=last_day_of_the_month[:10])
    header = '{header},{next}'.format(header=header, next=fiscal_month_end)

    content = header + '\n'
    details = ''
    total_base_tax_base = 0
    total_base_tax_withheld = 0

    for entry in data:
        details = details + '{next}'.format(details=details, next='D')
        details = '{details},{next}'.format(details=details, next='S')
        details = '{details},"{next}"'.format(details=details, next=entry['tin'][:9])
        details = '{details},"{next}"'.format(details=details, next=entry['customer'].upper()[:50])
        
        details = '{details},"{next}"'.format(details=details, next=(entry['contact_last_name'].upper()[:30] if entry['customer_type'] == 'Individual' else ''))
        details = '{details},"{next}"'.format(details=details, next=(entry['contact_first_name'].upper()[:30] if entry['customer_type'] == 'Individual' else ''))
        details = '{details},"{next}"'.format(details=details, next=(entry['contact_middle_name'].upper()[:30] if entry['customer_type'] == 'Individual' else ''))

        details = '{details},"{next}"'.format(details=details, next=entry['address_line1'].upper()[:50])
        details = '{details},"{next}"'.format(details=details, next=entry['city'].upper()[:50])
        details = '{details},{next}'.format(details=details, next="{:.2f}".format(flt(entry['exempt'], 2)))
        details = '{details},{next}'.format(details=details, next="{:.2f}".format(flt(entry['zero_rated'], 2)))
        details = '{details},{next}'.format(details=details, next="{:.2f}".format(flt(entry['taxable_net'], 2)))
        details = '{details},{next}'.format(details=details, next="{:.2f}".format(flt(entry['output_tax'], 2)))
        details = '{details},{next}'.format(details=details, next=company_information['tin'].upper()[:9])
        details = '{details},{next}'.format(details=details, next=last_day_of_the_month[:10])

        details = details + '\n'
    
    content = content + details

    filename = "{tin}S{return_period}".format(tin=company_information['tin'][:9],return_period=return_period_no_slash)

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
            "fieldname": "customer",
            "label": _("Registered Name"),
            "fieldtype": "Link",
            "options": "Customer",
            "width": 200
        },
        {
            "fieldname": "full_name",
            "label": _("Name of Customer"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "address",
            "label": _("Customer's Address"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "total_sales",
            "label": _("Total Sales"),
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
            "fieldname": "output_tax",
            "label": _("Output Tax"),
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