# Copyright (c) 2013, SERVIO Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate
from aruga_acct.aruga_accounting.utils import get_company_information, get_customer_information
from aruga_acct.aruga_accounting.bir_forms import return_document

def execute(filters=None):
    columns, data = [], []

    data = get_data(filters.company, filters.year, filters.month)
    columns = get_columns()

    company_information = get_company_information(filters.company)

    return columns, data, None, None, None, company_information

@frappe.whitelist()
def generate_sawt_data_file(company, year, month, sawt_form, response_type="download"):
    # file structure: https://www.bir.gov.ph/images/bir_files/old_files/pdf/27815rmc%20no.%203-2006_annex%20a.pdf
    data = get_data(company, year, month)
    company_information = get_company_information(company)
    file_extension = "dat"

    content = ''
    header = ''

    return_period = '{MM}/{YYYY}'.format(MM=('0' + str(month))[-2:], YYYY=year)
    return_period_no_slash = '{MM}{YYYY}'.format(MM=('0' + str(month))[-2:], YYYY=year)

    header = '{next}'.format(header=header, next='HSAWT'[:5])
    header = '{header},{next}'.format(header=header, next='H{}'.format(sawt_form)[:6])
    header = '{header},{next}'.format(header=header, next=company_information['tin'][:9])
    header = '{header},{next}'.format(header=header, next=company_information['branch_code'][:4]) # branch code - 3 chars only
    header = '{header},"{next}"'.format(header=header, next=company_information['company_name'].upper()[:50])
    header = '{header},"{next}"'.format(header=header, next='') # blank last, first, middle name? EN user will always be company
    header = '{header},"{next}"'.format(header=header, next='')
    header = '{header},"{next}"'.format(header=header, next='')
    header = '{header},{next}'.format(header=header, next=return_period[:7])
    header = '{header},{next}'.format(header=header, next=company_information['rdo_code'][:3])

    content = header + '\n'
    details = ''
    i = 0
    total_base_tax_base = 0
    total_base_tax_withheld = 0

    for entry in data:
        i += 1
        details = details + '{next}'.format(details=details, next='DSAWT'[:5]) # alpha type
        details = '{details},{next}'.format(details=details, next='D{}'.format(sawt_form)[:6]) # type code
        details = '{details},{next}'.format(details=details, next=str(i)[:8]) # seq_num
        details = '{details},{next}'.format(details=details, next=entry['tin'][:9])
        details = '{details},{next}'.format(details=details, next=entry['branch_code'][:4])
        details = '{details},"{next}"'.format(details=details, next=entry['registered_name'].upper()[:50])
        
        details = '{details},"{next}"'.format(details=details, next=(entry['contact_last_name'].upper()[:30] if entry['customer_type'] == 'Individual' else ''))
        details = '{details},"{next}"'.format(details=details, next=(entry['contact_first_name'].upper()[:30] if entry['customer_type'] == 'Individual' else ''))
        details = '{details},"{next}"'.format(details=details, next=(entry['contact_middle_name'].upper()[:30] if entry['customer_type'] == 'Individual' else ''))

        details = '{details},{next}'.format(details=details, next=return_period[:7])
        details = '{details},{next}'.format(details=details, next='') # nature of payment = blank. blank in bir alphalist
        details = '{details},{next}'.format(details=details, next=entry['atc'][:5])
        details = '{details},{next}'.format(details=details, next="{:.2f}".format(flt(entry['atc_rate'], 2)))
        details = '{details},{next}'.format(details=details, next="{:.2f}".format(flt(entry['income_payment'], 2)))
        details = '{details},{next}'.format(details=details, next="{:.2f}".format(flt(entry['tax_withheld'], 2)))

        total_base_tax_base += entry['income_payment']
        total_base_tax_withheld += entry['tax_withheld']
        details = details + '\n'
    
    content = content + details

    control = ''
    control = '{next}'.format(control=control, next='CSAWT'[:5])
    control = '{control},{next}'.format(control=control, next='C{}'.format(sawt_form)[:6])
    control = '{control},{next}'.format(control=control, next=company_information['tin'][:9])
    control = '{control},{next}'.format(control=control, next=company_information['branch_code'][:4])
    control = '{control},{next}'.format(control=control, next=return_period[:7])
    control = '{control},{next}'.format(control=control, next="{:.2f}".format(flt(total_base_tax_base, 2)))
    control = '{control},{next}'.format(control=control, next="{:.2f}".format(flt(total_base_tax_withheld, 2)))

    content = content + control

    filename = "{tin}{branch_code}{return_period}{form_type}".format(tin=company_information['tin'][:9],branch_code=company_information['branch_code'][:3],return_period=return_period_no_slash,form_type=sawt_form)

    return_document(content, filename, file_extension, response_type)

def get_data(company, year, month):
    result = []

    data = frappe.db.sql("""
        SELECT 
            temp.customer,
            temp.atc,
            atc.description,
            temp.income_payment,
            temp.atc_rate,
            temp.tax_withheld
        FROM
            (
            SELECT 
                si.company,
                si.posting_date,
                si.customer,
                stac.atc AS atc,
                si.name AS document_no,
                si.base_net_total as income_payment,
                stac.atc_rate,
                ABS(stac.base_tax_amount) as tax_withheld
            FROM 
                `tabSales Invoice` si
            LEFT JOIN
                `tabSales Taxes and Charges` stac
            ON
                si.name = stac.parent
            LEFT JOIN 
                `tabCustomer` as c
            ON
                si.customer = c.name
            INNER JOIN
                `tabAccount` a
            ON
                stac.account_head = a.name
            WHERE
                si.docstatus = 1
                and si.is_return = 0
                and stac.base_tax_amount < 0 
                # and stac.atc IN (SELECT atc FROM `tabATC` WHERE tax_type_code IN ('WE', 'WB', 'WV'))
                and (a.account_type in ('Tax', 'Payable', '') or a.account_type is NULL)
            UNION ALL
            SELECT 
                pe.company,
                pe.posting_date,
                pe.party,
                atac.atc AS atc,
                pe.name AS document_no,
                (pe.base_paid_amount_after_tax) as income_payment,
                atac.atc_rate,
                ABS(atac.base_tax_amount) as tax_withheld
            FROM 
                `tabPayment Entry` pe
            LEFT JOIN
                `tabAdvance Taxes and Charges` atac
            ON
                pe.name = atac.parent
            LEFT JOIN 
                `tabCustomer` as c
            ON
                pe.party = c.name
            INNER JOIN
                `tabAccount` a
            ON
                atac.account_head = a.name
            WHERE
                pe.docstatus = 1
                and ((atac.base_tax_amount < 0 and atac.add_deduct_tax != 'Deduct') or (atac.base_tax_amount >= 0 and atac.add_deduct_tax = 'Deduct'))
                # and atac.atc IN (SELECT atc FROM `tabATC` WHERE tax_type_code IN ('WE', 'WB', 'WV'))
                and pe.party_type = 'Customer'
                and (a.account_type in ('Tax', 'Payable', '') or a.account_type is NULL)
            ) temp
        LEFT JOIN
            `tabATC` atc
        ON
            temp.atc = atc.name
        WHERE 
            temp.company = %s
            and YEAR(temp.posting_date) = %s
            and MONTH(temp.posting_date) = %s
        GROUP BY
            temp.customer,
            temp.atc,
            atc.description,
            temp.atc_rate
    """, (company, year, month), as_dict=1)

    for entry in data:
        customer_information = get_customer_information(entry.customer)

        # blank registered_name if individual?
        row = {
            'tin': customer_information['tin'],
            'tin_with_dash': customer_information['tin_with_dash'],
            'branch_code': customer_information['branch_code'],
            'registered_name': entry.customer,
            'individual': '' if customer_information['customer_type'] == 'Company' 
                else "{0}, {1} {2}".format(customer_information['contact_last_name'], customer_information['contact_first_name'], customer_information['contact_middle_name']),
            'contact_last_name': customer_information['contact_last_name'],
            'contact_first_name': customer_information['contact_first_name'],
            'contact_middle_name': customer_information['contact_middle_name'],
            'customer_type': customer_information['customer_type'],
            'atc': entry.atc,
            'description': entry.description,
            'income_payment': entry.income_payment,
            'formatted_atc_rate': "{:.0%}".format(entry.atc_rate / 100),
            'atc_rate': entry.atc_rate,
            'tax_withheld': entry.tax_withheld
        }

        result.append(row)
    
    return result

def get_columns():
    columns = [
        {
            "fieldname": "tin_with_dash",
            "label": _("TIN"),
            "fieldtype": "Data",
            "width": 180
        },
        {
            "fieldname": "registered_name",
            "label": _("Registered Name"),
            "fieldtype": "Link",
            "options": "Customer",
            "width": 200
        },
        {
            "fieldname": "individual",
            "label": _("Individual"),
            "fieldtype": "Data",
            "width": 220
        },
        {
            "fieldname": "atc",
            "label": _("ATC"),
            "fieldtype": "Link",
            "options": "ATC",
            "width": 80
        },
        {
            "fieldname": "description",
            "label": _("Nature of Income Payment"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "income_payment",
            "label": _("Income Payment"),
            "fieldtype": "Currency",
            "width": 200
        },
        {
            "fieldname": "formatted_atc_rate",
            "label": _("Tax Rate"),
            "fieldtype": "Data",
            "width": 80
        },
        {
            "fieldname": "tax_withheld",
            "label": _("Tax Withheld"),
            "fieldtype": "Currency",
            "width": 200
        },
    ]

    return columns