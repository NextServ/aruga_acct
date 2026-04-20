# Copyright (c) 2013, SERVIO Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate
from aruga_acct.aruga_accounting.utils import get_company_information, get_customer_information, get_formatted_full_name
from aruga_acct.aruga_accounting.bir_forms import return_document
import json
import calendar

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
            COALESCE(stac_totals.final_total, si.total) as invoice_total,
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
        LEFT JOIN
            (
                SELECT 
                    stac.parent, 
                    SUM(stac.total) as final_total
                FROM `tabSales Taxes and Charges` stac
                INNER JOIN `tabAccount` a ON stac.account_head = a.name
                WHERE stac.tax_amount_after_discount_amount >= 0
                    AND (a.account_type IN ('Tax', 'Payable', '') OR a.account_type IS NULL)
                GROUP BY stac.parent
            ) stac_totals
        ON
            si.name = stac_totals.parent
        WHERE
            si.docstatus = 1
            AND si.is_return = 0
            AND si.company = %s
            AND YEAR(si.posting_date) = %s
            AND MONTH(si.posting_date) = %s
        GROUP BY si.name, si.customer, (COALESCE(NULLIF(sii.item_code, ''), sii.item_name)), sii.item_tax_template, si.taxes_and_charges;
        """, (company, year, month), as_dict=1)

    si_base_tax_amounts = frappe.db.sql("""
        SELECT
            si.name,
            si.customer,
            COALESCE(stac_totals.final_total, si.total) as invoice_total,
            stac.account_head,
            stac.base_tax_amount,
            stac.item_wise_tax_detail
        FROM
            `tabSales Invoice` si
        LEFT JOIN
            `tabSales Taxes and Charges` stac
        ON
            si.name = stac.parent
        LEFT JOIN
            `tabAccount` a
        ON
            stac.account_head = a.name
        LEFT JOIN
            (
                SELECT 
                    stac2.parent, 
                    SUM(stac2.total) as final_total
                FROM `tabSales Taxes and Charges` stac2
                INNER JOIN `tabAccount` a2 ON stac2.account_head = a2.name
                WHERE stac2.tax_amount_after_discount_amount >= 0
                    AND (a2.account_type IN ('Tax', 'Payable', '') OR a2.account_type IS NULL)
                GROUP BY stac2.parent
            ) stac_totals
        ON
            si.name = stac_totals.parent
        WHERE
            si.docstatus = 1
            AND si.is_return = 0
            AND (a.account_type in ('Tax', 'Payable', '') or a.account_type is NULL OR a.account_type IS NULL)
            AND si.company = %s
            AND YEAR(si.posting_date) = %s
            AND MONTH(si.posting_date) = %s
        """, (company, year, month), as_dict=1)
        
    last_day_of_the_month = '{MM}/{DD}/{YYYY}'.format(MM=('0' + str(month))[-2:],DD=calendar.monthrange(int(year), int(month))[1], YYYY=year)

    # Process invoices with taxes
    for tax_line in si_base_tax_amounts:
        if tax_line.item_wise_tax_detail:
            item_wise_tax_detail = json.loads(tax_line.item_wise_tax_detail)
            account_head = tax_line.get('account_head', '')
            
            for item in item_wise_tax_detail.keys():
                matched = False
                
                # loop to find net amount
                for item_net_amount in si_base_net_amounts:                
                    if item_net_amount.name == tax_line.name and item_net_amount.item_name == item:
                        item_tax_template = item_net_amount.item_tax_template
                        taxes_and_charges = item_net_amount.taxes_and_charges
                        
                        document_row = None
                        document_row = next((row for row in data if row.get('sales_invoice') == item_net_amount.name), None)
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
                                'invoice_total': flt(item_net_amount.invoice_total, 2),
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
                        if not matched and tax_declaration_company_setup.item_vat_sales and item_tax_template == tax_declaration_company_setup.item_vat_sales:
                            document_row['taxable_net'] += flt(item_net_amount.base_net_amount, 2)
                            document_row['output_tax'] += flt(item_wise_tax_detail[item][1], 2)
                            matched = True
                        elif not matched and tax_declaration_company_setup.vat_sales and (taxes_and_charges == tax_declaration_company_setup.vat_sales or account_matches_template(account_head, tax_declaration_company_setup.vat_sales)):
                            document_row['taxable_net'] += flt(item_net_amount.base_net_amount, 2)
                            document_row['output_tax'] += flt(item_wise_tax_detail[item][1], 2)
                            matched = True
                            
                        if not matched and tax_declaration_company_setup.item_zero_rated_sales and item_tax_template == tax_declaration_company_setup.item_zero_rated_sales:
                            document_row['zero_rated'] += flt(item_net_amount.base_net_amount, 2)
                            matched = True
                        elif not matched and tax_declaration_company_setup.zero_rated_sales and (taxes_and_charges == tax_declaration_company_setup.zero_rated_sales or account_matches_template(account_head, tax_declaration_company_setup.zero_rated_sales)):
                            document_row['zero_rated'] += flt(item_net_amount.base_net_amount, 2)
                            matched = True
                            
                        if not matched and tax_declaration_company_setup.item_exempt_sales and item_tax_template == tax_declaration_company_setup.item_exempt_sales:
                            document_row['exempt'] += flt(item_net_amount.base_net_amount, 2)
                            matched = True
                        elif not matched and tax_declaration_company_setup.exempt_sales and (taxes_and_charges == tax_declaration_company_setup.exempt_sales or account_matches_template(account_head, tax_declaration_company_setup.exempt_sales)):
                            document_row['exempt'] += flt(item_net_amount.base_net_amount, 2)
                            matched = True

                        # Fallback: match based on account head naming pattern if no template matched
                        if not matched and 'VAT' in account_head:
                            document_row['taxable_net'] += flt(item_net_amount.base_net_amount, 2)
                            document_row['output_tax'] += flt(item_wise_tax_detail[item][1], 2)
                            matched = True
                        elif not matched and 'Zero' in account_head:
                            document_row['zero_rated'] += flt(item_net_amount.base_net_amount, 2)
                            matched = True
                        elif not matched and 'Exempt' in account_head:
                            document_row['exempt'] += flt(item_net_amount.base_net_amount, 2)
                            matched = True

                        # net amount row is found, exit loop
                        break
    
    # Process invoices WITHOUT taxes - default to taxable
    for item_net_amount in si_base_net_amounts:
        # Check if this invoice already processed (has taxes)
        existing_row = next((row for row in data if row.get('sales_invoice') == item_net_amount.name), None)
        if not existing_row:
            # This invoice has no taxes, create row with items as taxable
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
                'invoice_total': flt(item_net_amount.invoice_total, 2),
                'total_sales': flt(item_net_amount.invoice_total, 2),
                'zero_rated': 0,
                'exempt': 0,
                'gross_taxable': flt(item_net_amount.invoice_total, 2),
                'taxable_net': flt(item_net_amount.base_net_amount, 2),
                'output_tax': 0,
            }
            
            data.append(document_row)

    for row in data:
        row['gross_taxable'] = row['invoice_total']
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