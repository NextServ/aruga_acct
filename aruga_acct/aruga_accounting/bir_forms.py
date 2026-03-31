import frappe
from frappe import _
from frappe.utils.pdf import get_pdf
from frappe.utils import getdate, flt, cint, add_days, add_months, cstr, get_datetime, nowdate, today
from datetime import datetime
from aruga_acct.aruga_accounting.utils import get_company_information, get_supplier_information, get_employee_information, report_is_permitted, get_bir_form_images
import pytz
import json

options = {
    "margin-left": "0mm",
    "margin-right": "0mm",
    "margin-top": "0mm",
    "margin-bottom": "0mm"
}

@frappe.whitelist()
def bir_2307(company, supplier, employee, doctype, purchase_invoice, payment_entry, expense_claim, from_date, to_date, response_type="pdf"):
    report_is_permitted('BIR 2307')

    from aruga_acct.aruga_accounting.report.bir_2307.bir_2307 import get_data as get_data_bir_2307
    data = get_data_bir_2307(company, supplier, employee, doctype, purchase_invoice, payment_entry, expense_claim, from_date, to_date)

    data_ip = []
    data_mp = []

    ip_month_1_total = 0
    ip_month_2_total = 0
    ip_month_3_total = 0
    ip_grand_total = 0
    ip_tax_withheld_for_the_quarter_total = 0

    mp_month_1_total = 0
    mp_month_2_total = 0
    mp_month_3_total = 0
    mp_grand_total = 0
    mp_tax_withheld_for_the_quarter_total = 0

    for entry in data:
        if entry.payment_type == 'Income Payment':
            ip_month_1_total = ip_month_1_total + entry.month_1
            ip_month_2_total = ip_month_2_total + entry.month_2
            ip_month_3_total = ip_month_3_total + entry.month_3
            ip_grand_total = ip_grand_total + entry.total
            ip_tax_withheld_for_the_quarter_total = ip_tax_withheld_for_the_quarter_total + entry.tax_withheld_for_the_quarter

            data_ip.append(entry)
        elif entry.payment_type == 'Money Payment':
            mp_month_1_total = mp_month_1_total + entry.month_1
            mp_month_2_total = mp_month_2_total + entry.month_2
            mp_month_3_total = mp_month_3_total + entry.month_3
            mp_grand_total = mp_grand_total + entry.total
            mp_tax_withheld_for_the_quarter_total = mp_tax_withheld_for_the_quarter_total + entry.tax_withheld_for_the_quarter

            data_mp.append(entry)

    
    payee_information = {
        'employee_name': "",
        'employee_type': "",
        'contact_first_name': "",
        'contact_middle_name': "",
        'contact_last_name': "",
        'address': "",
        'address_line1': "",
        'address_line2': '',
        'city': '',
        'state': '',
        'tin': '',
        'tin_with_dash': '',
        'branch_code': '',
        'zipcode': "",
        'phone': "",
    }
    if employee:
        payee_information = get_employee_information(employee)
    else:
        payee_information = get_supplier_information(supplier)

    context = {
        'from_date': getdate(from_date),
        'to_date': getdate(to_date),
        'payor': get_company_information(company),
        'payee': payee_information,
        'data_ip': data_ip,
        'ip_month_1_total': ip_month_1_total,
        'ip_month_2_total': ip_month_2_total,
        'ip_month_3_total': ip_month_3_total,
        'ip_grand_total': ip_grand_total,
        'ip_tax_withheld_for_the_quarter_total': ip_tax_withheld_for_the_quarter_total,
        'data_mp': data_mp,
        'mp_month_1_total': mp_month_1_total,
        'mp_month_2_total': mp_month_2_total,
        'mp_month_3_total': mp_month_3_total,
        'mp_grand_total': mp_grand_total,
        'mp_tax_withheld_for_the_quarter_total': mp_tax_withheld_for_the_quarter_total
    }

    filename = "BIR 2307 {} {} {} {}".format(company, supplier, from_date, to_date)
    
    context["build_version"] = frappe.utils.get_build_version()
    context["bir_form_images"] = get_bir_form_images("2307-1.png")
    html = frappe.render_template("templates/bir_forms/bir_2307_template.html", context)
    options["page-size"] = "Legal"

    return_pdf_document(html, filename, options, response_type)

@frappe.whitelist()
def bir_2550m(company, year, month, 
    input_tax_carried_over_from_previous_period, input_tax_deferred_on_capital_goods_exceeding_1m_from_previous_period,
    transitional_input_tax, presumptive_input_tax, allowable_input_tax_others,
    input_tax_deferred_on_capital_goods_from_previous_period_1m_up,
    input_tax_directly_attributable_to_exempt_sales, vat_refund_tcc_claimed, less_deductions_from_input_tax_others,
    surcharge, compromise, interest,
    response_type="pdf"):
    precision = cint(frappe.db.get_default("currency_precision")) or 2
    report_is_permitted('BIR 2550M')

    tax_declaration_company_setup = frappe.get_doc('Tax Declaration Company Setup', company)
    tax_declaration_company_setup = None
    try:
        tax_declaration_company_setup = frappe.get_doc('Tax Declaration Company Setup', company)
    except:
        frappe.throw("Please create a Tax Declaration Company Setup record for {0}".format(company))

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
        'less_allowable_input_tax': {
            'input_tax_carried_over_from_previous_period': flt(input_tax_carried_over_from_previous_period, 2),
            'input_tax_deferred_on_capital_goods_exceeding_1m_from_previous_period': flt(input_tax_deferred_on_capital_goods_exceeding_1m_from_previous_period, 2),
            'transitional_input_tax': flt(transitional_input_tax, 2),
            'presumptive_input_tax': flt(presumptive_input_tax, 2),
            'allowable_input_tax_others': flt(allowable_input_tax_others, 2),
        },
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
        # 'directly_attributable_to_exempt_sales': {
        #     'total_base_tax_base': 0,
        #     'total_base_tax_amount': 0
        # },
        # 'directly_attributable_to_sale_to_government': {
        #     'total_base_tax_base': 0,
        #     'total_base_tax_amount': 0
        # }
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
            AND (a.account_type in ('Tax', 'Payable', '') or a.account_type is NULL)
            # AND ptac.base_tax_amount >= 0 AND ptac.add_deduct_tax = 'Add'
            AND a.name NOT LIKE '%%Withholding%%'
            AND pi.company = %s
            AND YEAR(pi.posting_date) = %s
            AND MONTH(pi.posting_date) = %s
        """, (company, year, month), as_dict=1)
    
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
            AND (a.account_type in ('Tax', 'Payable', '') or a.account_type is NULL)
            AND a.name NOT LIKE '%%Withholding%%'
            # AND stac.base_tax_amount >= 0
            AND si.company = %s
            AND YEAR(si.posting_date) = %s
            AND MONTH(si.posting_date) = %s
        """, (company, year, month), as_dict=1)
    
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
                
    totals['total_sales_receipts'] = totals['vat_sales']['total_base_tax_base'] + totals['sales_to_government']['total_base_tax_base'] \
        + totals['zero_rated_sales']['total_base_tax_base'] + totals['exempt_sales']['total_base_tax_base']

    totals['total_output_tax_due'] = totals['vat_sales']['total_base_tax_amount'] + totals['sales_to_government']['total_base_tax_amount']

    totals['total_other_allowable_input_tax'] = totals['less_allowable_input_tax']['input_tax_carried_over_from_previous_period'] \
        + totals['less_allowable_input_tax']['input_tax_deferred_on_capital_goods_exceeding_1m_from_previous_period'] \
        + totals['less_allowable_input_tax']['transitional_input_tax'] + totals['less_allowable_input_tax']['presumptive_input_tax'] \
        + totals['less_allowable_input_tax']['allowable_input_tax_others']

    totals['total_current_purchases'] = totals['capital_goods']['total_base_tax_base'] + totals['capital_goods_exceeding_1m']['total_base_tax_base'] \
        + totals['domestic_purchases_of_goods']['total_base_tax_base'] + totals['importation_of_goods']['total_base_tax_base'] \
        + totals['domestic_purchase_of_services']['total_base_tax_base'] + totals['services_rendered_by_non_residents']['total_base_tax_base'] \
        + totals['purchases_not_qualified_for_input_tax']['total_base_tax_base'] + totals['others']['total_base_tax_base']

    totals['total_available_input_tax'] = totals['total_other_allowable_input_tax'] + totals['capital_goods']['total_base_tax_amount'] + totals['capital_goods_exceeding_1m']['total_base_tax_amount'] \
        + totals['domestic_purchases_of_goods']['total_base_tax_amount'] + totals['importation_of_goods']['total_base_tax_amount'] + totals['domestic_purchase_of_services']['total_base_tax_amount'] \
        + totals['services_rendered_by_non_residents']['total_base_tax_amount'] + totals['others']['total_base_tax_amount']
    
    totals['less_deductions_from_input_tax']['amount_of_input_tax_not_directly_attributable'] = totals['total_available_input_tax'] - totals['less_deductions_from_input_tax']['input_tax_directly_attributable_to_exempt_sales']

    if totals['total_sales_receipts'] > 0:
        totals['ratable_portion_of_input_tax_not_directly_attributable'] = (flt((totals['exempt_sales']['total_base_tax_base'] / totals['total_sales_receipts']) * totals['less_deductions_from_input_tax']['amount_of_input_tax_not_directly_attributable'], 2))
        totals['less_deductions_from_input_tax']['input_tax_allocable_to_exempt_sales'] = totals['less_deductions_from_input_tax']['input_tax_directly_attributable_to_exempt_sales'] \
            + totals['ratable_portion_of_input_tax_not_directly_attributable']
    else:
        totals['ratable_portion_of_input_tax_not_directly_attributable'] = 0
        totals['less_deductions_from_input_tax']['input_tax_allocable_to_exempt_sales'] = totals['less_deductions_from_input_tax']['input_tax_directly_attributable_to_exempt_sales']

    totals['total_deductions_from_input_tax'] = totals['less_deductions_from_input_tax']['input_tax_deferred_on_capital_goods_from_previous_period_1m_up'] \
        + totals['less_deductions_from_input_tax']['input_tax_allocable_to_exempt_sales'] + totals['less_deductions_from_input_tax']['vat_refund_tcc_claimed'] \
        + totals['less_deductions_from_input_tax']['less_deductions_from_input_tax_others']

    totals['total_allowable_input_tax'] = totals['total_available_input_tax'] - totals['total_deductions_from_input_tax']
    totals['net_vat_payable'] = totals['total_output_tax_due'] - totals['total_allowable_input_tax']
    totals['tax_still_payable'] = totals['net_vat_payable'] - totals['total_tax_credit_payments']
    totals['total_amount_payable'] = totals['tax_still_payable'] + totals['penalties']['total']

    context = {
        'company': get_company_information(company),
        'year': year,
        'month': month,
        'totals': totals
    }

    filename = "BIR 2550M {} {} {}".format(company, year, month)
    
    context["build_version"] = frappe.utils.get_build_version()
    context["bir_form_images"] = get_bir_form_images("bir2550m-1.png", "bir2550m-2.png")
    html = frappe.render_template("templates/bir_forms/bir_2550m_template.html", context)
    options["page-size"] = "Legal"

    return_pdf_document(html, filename, options, response_type)

@frappe.whitelist()
def bir_1601_eq(company, year, quarter, response_type="pdf"):
    precision = cint(frappe.db.get_default("currency_precision")) or 2
    report_is_permitted('BIR 1601-EQ')

    year = int(year)
    quarter = int(quarter)
    total_remittances_made = 0
    total_taxes_withheld = 0
    tax_still_due = 0
    total_penalties = 0
    total_amount_still_due = 0

    data = []
    data_pi = []
    data_pe = []

    # TODO: custom base amount
    data = frappe.db.sql("""
        SELECT 
            temp.atc,
            temp.base_tax_base,
            a.rate AS tax_rate,
            temp.base_tax_withheld
        FROM
            (
            SELECT 
                source.atc AS atc,
                SUM(source.base_total) AS base_tax_base,
                SUM(ABS(source.base_tax_amount)) AS base_tax_withheld
            FROM
                (
                SELECT 
                    ptac.atc,
                    pi.base_total,
                    ptac.base_tax_amount
                FROM 
                    `tabPurchase Invoice` pi
                LEFT JOIN
                    `tabPurchase Taxes and Charges` ptac
                ON
                    pi.name = ptac.parent
                INNER JOIN
                    `tabAccount` a
                ON
                    ptac.account_head = a.name
                WHERE
                    pi.docstatus = 1
                    and pi.is_return = 0
                    and ((ptac.base_tax_amount < 0 and ptac.add_deduct_tax != 'Deduct') or (ptac.base_tax_amount >= 0 and ptac.add_deduct_tax = 'Deduct'))
                    and (a.account_type in ('Tax', 'Payable', '') or a.account_type is NULL)
                    and pi.company = %s
                    and YEAR(pi.posting_date) = %s
                    and QUARTER(pi.posting_date) = %s
                UNION ALL
                SELECT 
                    atac.atc,
                    pe.base_paid_amount,
                    atac.base_tax_amount
                FROM
                    `tabPayment Entry` pe
                LEFT JOIN
                    `tabAdvance Taxes and Charges` atac
                ON
                    pe.name = atac.parent
                INNER JOIN
                    `tabAccount` a
                ON
                    atac.account_head = a.name
                WHERE
                    pe.docstatus = 1
                    and pe.payment_type = 'Pay'
                    and pe.party_type = 'Supplier'
                    and ((atac.base_tax_amount < 0 and atac.add_deduct_tax != 'Deduct') or (atac.base_tax_amount >= 0 and atac.add_deduct_tax = 'Deduct'))
                    and (a.account_type in ('Tax', 'Payable', '') or a.account_type is NULL)
                    and pe.company = %s
                    and YEAR(pe.posting_date) = %s
                    and QUARTER(pe.posting_date) = %s
                ) source
            GROUP BY
                source.atc
            ) AS temp
        INNER JOIN 
            `tabATC` as a
        ON
            temp.atc = a.name
        WHERE
            a.tax_type_code IN ('WE', 'WB', 'WV') and a.form_type = '2307'
        """, (company, year, quarter, company, year, quarter), as_dict=1)

    for entry in data:
        total_taxes_withheld += entry.base_tax_withheld
    
    tax_still_due = total_taxes_withheld - total_remittances_made
    total_amount_still_due = tax_still_due + total_penalties

    context = {
        'company': get_company_information(company),
        'year': year,
        'quarter': quarter,
        'data': data,
        'total_taxes_withheld': total_taxes_withheld,
        'total_remittances_made': total_remittances_made,
        'tax_still_due': tax_still_due,
        'total_penalties': total_penalties,
        'total_amount_still_due': total_amount_still_due
    }

    filename = "BIR 1601-EQ {} {} {}".format(company, year, quarter)
    
    context["build_version"] = frappe.utils.get_build_version()
    context["bir_form_images"] = get_bir_form_images("1601-EQ January 2019 ENCS final-1.png")
    html = frappe.render_template("templates/bir_forms/bir_1601_eq_template.html", context)
    options["page-size"] = "Legal"

    return_pdf_document(html, filename, options, response_type)

@frappe.whitelist()
def bir_1601_eq_qap(company, year, quarter, response_type="download"):
    precision = cint(frappe.db.get_default("currency_precision")) or 2
    report_is_permitted('BIR 1601-EQ')

    year = int(year)
    quarter = int(quarter)
    total_remittances_made = 0
    total_taxes_withheld = 0
    tax_still_due = 0
    total_penalties = 0
    total_amount_still_due = 0

    # TODO: custom base amount
    # (CASE 
    #                 WHEN EXISTS(SELECT 1 FROM `tabPurchase Taxes and Charges` temp 
    #                         WHERE temp.parent = ptac.parent AND temp.name <> ptac.name and (temp.base_tax_amount < 0 or temp.add_deduct_tax = 'Deduct')) /*multiple atc in one doc*/
    #                 THEN
    #                     ROUND((ABS(ptac.base_tax_amount) / (a.rate / 100)), 2)
    #                 ELSE
    #                     pi.base_total
    #             END)
    data = frappe.db.sql("""
        SELECT
            temp.supplier,
            temp.year,
            temp.month,
            temp.atc,
            a.rate,
            temp.base_tax_base,
            temp.base_tax_withheld
        FROM
            (
            SELECT 
                source.supplier,
                YEAR(source.posting_date) AS year,
                MONTH(source.posting_date) AS month,
                source.atc AS atc,
                SUM(source.base_total) AS base_tax_base,
                SUM(ABS(source.base_tax_amount)) AS base_tax_withheld
            FROM
            (
                SELECT 
                    pi.supplier,
                    pi.posting_date,
                    ptac.atc AS atc,
                    pi.base_total,
                    ptac.base_tax_amount
                FROM 
                    `tabPurchase Invoice` pi
                LEFT JOIN
                    `tabPurchase Taxes and Charges` ptac
                ON
                    pi.name = ptac.parent
                INNER JOIN
                    `tabAccount` a
                ON
                    ptac.account_head = a.name
                WHERE
                    pi.docstatus = 1
                    and pi.is_return = 0
                    and ((ptac.base_tax_amount < 0 and ptac.add_deduct_tax != 'Deduct') or (ptac.base_tax_amount >= 0 and ptac.add_deduct_tax = 'Deduct'))
                    and (a.account_type in ('Tax', 'Payable', '') or a.account_type is NULL)
                    and pi.company = %s
                    and YEAR(pi.posting_date) = %s
                    and QUARTER(pi.posting_date) = %s
                UNION ALL
                SELECT 
                    pe.party,
                    pe.posting_date,
                    atac.atc AS atc,
                    pe.base_paid_amount,
                    atac.base_tax_amount
                FROM 
                    `tabPayment Entry` pe
                LEFT JOIN
                    `tabAdvance Taxes and Charges` atac
                ON
                    pe.name = atac.parent
                INNER JOIN
                    `tabAccount` a
                ON
                    atac.account_head = a.name
                WHERE
                    pe.docstatus = 1
                    and pe.payment_type = 'Pay'
                    and pe.party_type = 'Supplier'
                    and ((atac.base_tax_amount < 0 and atac.add_deduct_tax != 'Deduct') or (atac.base_tax_amount >= 0 and atac.add_deduct_tax = 'Deduct'))
                    and (a.account_type in ('Tax', 'Payable', '') or a.account_type is NULL)
                    and pe.company = %s
                    and YEAR(pe.posting_date) = %s
                    and QUARTER(pe.posting_date) = %s
            ) source
            GROUP BY
                source.supplier,
                YEAR(source.posting_date),
                MONTH(source.posting_date),
                source.atc
            ) AS temp
        INNER JOIN 
            `tabATC` as a
        ON
            temp.atc = a.name
        WHERE 
            a.tax_type_code IN ('WE', 'WB', 'WV') and a.form_type = '2307'
        """, (company, year, quarter, company, year, quarter), as_dict=1)

    for entry in data:
        total_taxes_withheld += entry.base_tax_withheld
    
    tax_still_due = total_taxes_withheld - total_remittances_made
    total_amount_still_due = tax_still_due + total_penalties

    company_information = get_company_information(company)
    context = {
        'company': get_company_information(company),
        'year': year,
        'quarter': quarter,
        'data': data,
        'total_taxes_withheld': total_taxes_withheld,
        'total_remittances_made': total_remittances_made,
        'tax_still_due': tax_still_due,
        'total_penalties': total_penalties,
        'total_amount_still_due': total_amount_still_due
    }
    file_extension = "dat"
    
    context["build_version"] = frappe.utils.get_build_version()

    content = ''
    header = ''

    return_period = '{MM}/{YYYY}'.format(MM=('0' + str(first_month_in_quarter(quarter)))[-2:], YYYY=year)
    return_period_no_slash = '{MM}{YYYY}'.format(MM=('0' + str(first_month_in_quarter(quarter)))[-2:], YYYY=year)

    header = '{next}'.format(header=header, next='HQAP'[:5])
    header = '{header},{next}'.format(header=header, next='H1601EQ'[:7])
    header = '{header},{next}'.format(header=header, next=company_information['tin'][:9])
    header = '{header},{next}'.format(header=header, next=company_information['tin'][9:13])
    header = '{header},"{next}"'.format(header=header, next=company_information['company_name'][:50])
    header = '{header},{next}'.format(header=header, next=return_period[:7])
    header = '{header},{next}'.format(header=header, next=company_information['rdo_code'][:3])

    content = header + '\n'
    details = ''
    i = 0
    total_base_tax_base = 0
    total_base_tax_withheld = 0
    for entry in data:
        i += 1
        payee_information = get_supplier_information(entry.supplier)
        details = details + '{next}'.format(details=details, next='D1'[:2])
        details = '{details},{next}'.format(details=details, next='1601EQ'[:6])
        details = '{details},{next}'.format(details=details, next=str(i)[:8])
        details = '{details},{next}'.format(details=details, next=payee_information['tin'][:9])
        details = '{details},{next}'.format(details=details, next=payee_information['tin'][9:13])
        details = '{details},"{next}"'.format(details=details, next=payee_information['supplier_name'][:50])
        
        details = '{details},"{next}"'.format(details=details, next=(payee_information['contact_last_name'][:30] if payee_information['supplier_type'] == 'Individual' else ''))
        details = '{details},"{next}"'.format(details=details, next=(payee_information['contact_first_name'][:30] if payee_information['supplier_type'] == 'Individual' else ''))
        details = '{details},"{next}"'.format(details=details, next=(payee_information['contact_middle_name'][:30] if payee_information['supplier_type'] == 'Individual' else ''))

        detail_return_period = '{MM}/{YYYY}'.format(MM=('0' + str(entry.month))[-2:], YYYY=entry.year)
        details = '{details},{next}'.format(details=details, next=detail_return_period[:7])
        details = '{details},{next}'.format(details=details, next=entry.atc[:5])
        details = '{details},{next}'.format(details=details, next="{:.2f}".format(flt(entry.rate, 2)))
        details = '{details},{next}'.format(details=details, next="{:.2f}".format(flt(entry.base_tax_base, 2)))
        details = '{details},{next}'.format(details=details, next="{:.2f}".format(flt(entry.base_tax_withheld, 2)))

        total_base_tax_base += entry.base_tax_base
        total_base_tax_withheld += entry.base_tax_withheld
        details = details + '\n'
    
    content = content + details

    controls = ''
    controls = '{next}'.format(controls=controls, next='C1'[:5])
    controls = '{controls},{next}'.format(controls=controls, next='1601EQ'[:6])
    controls = '{controls},{next}'.format(controls=controls, next=company_information['tin'][:9])
    controls = '{controls},{next}'.format(controls=controls, next=company_information['tin'][9:13])
    controls = '{controls},{next}'.format(controls=controls, next=return_period[:7])
    controls = '{controls},{next}'.format(controls=controls, next="{:.2f}".format(flt(total_base_tax_base, 2)))
    controls = '{controls},{next}'.format(controls=controls, next="{:.2f}".format(flt(total_base_tax_withheld, 2)))

    content = content + controls
    
    filename = "{tin}{branch_code}{return_period}{form_type}".format(tin=company_information['tin'][:9],branch_code=company_information['tin'][9:13],return_period=return_period_no_slash,form_type='1601EQ')

    return_document(content, filename, file_extension, response_type)

def first_month_in_quarter(quarter):
    return ((quarter - 1) * 3) + 1

@frappe.whitelist()
def bir_1601_fq(company, year, quarter, response_type="pdf"):
    precision = cint(frappe.db.get_default("currency_precision")) or 2
    report_is_permitted('BIR 1601-FQ')

    year = int(year)
    quarter = int(quarter)
    total_remittances_made = 0
    total_taxes_withheld = 0
    tax_still_due = 0
    total_penalties = 0
    total_amount_still_due = 0

    # TODO: custom base amount
    data = frappe.db.sql("""
        SELECT 
            temp.atc,
            temp.base_tax_base,
            a.rate AS tax_rate,
            temp.base_tax_withheld
        FROM
            (
            SELECT 
                source.atc AS atc,
                SUM(source.base_total) AS base_tax_base,
                SUM(ABS(source.base_tax_amount)) AS base_tax_withheld
            FROM
                (
                SELECT 
                    ptac.atc,
                    pi.base_total,
                    ptac.base_tax_amount
                FROM 
                    `tabPurchase Invoice` pi
                LEFT JOIN
                    `tabPurchase Taxes and Charges` ptac
                ON
                    pi.name = ptac.parent
                INNER JOIN
                    `tabAccount` a
                ON
                    ptac.account_head = a.name
                WHERE
                    pi.docstatus = 1
                    and pi.is_return = 0
                    and ((ptac.base_tax_amount < 0 and ptac.add_deduct_tax != 'Deduct') or (ptac.base_tax_amount >= 0 and ptac.add_deduct_tax = 'Deduct'))
                    and (a.account_type in ('Tax', 'Payable', '') or a.account_type is NULL)
                    and pi.company = %s
                    and YEAR(pi.posting_date) = %s
                    and QUARTER(pi.posting_date) = %s
                UNION ALL
                SELECT 
                    atac.atc,
                    pe.base_paid_amount,
                    atac.base_tax_amount
                FROM
                    `tabPayment Entry` pe
                LEFT JOIN
                    `tabAdvance Taxes and Charges` atac
                ON
                    pe.name = atac.parent
                INNER JOIN
                    `tabAccount` a
                ON
                    atac.account_head = a.name
                WHERE
                    pe.docstatus = 1
                    and pe.payment_type = 'Pay'
                    and pe.party_type = 'Supplier'
                    and ((atac.base_tax_amount < 0 and atac.add_deduct_tax != 'Deduct') or (atac.base_tax_amount >= 0 and atac.add_deduct_tax = 'Deduct'))
                    and (a.account_type in ('Tax', 'Payable', '') or a.account_type is NULL)
                    and pe.company = %s
                    and YEAR(pe.posting_date) = %s
                    and QUARTER(pe.posting_date) = %s
                ) source
            GROUP BY
                source.atc
            ) AS temp
        INNER JOIN 
            `tabATC` as a
        ON
            temp.atc = a.name
        # WHERE
        #     a.form_type = '2306'
        """, (company, year, quarter, company, year, quarter), as_dict=1)

    for entry in data:
        total_taxes_withheld += entry.base_tax_withheld
    
    tax_still_due = total_taxes_withheld - total_remittances_made
    total_amount_still_due = tax_still_due + total_penalties

    context = {
        'company': get_company_information(company),
        'year': year,
        'quarter': quarter,
        'data': data,
        'total_taxes_withheld': total_taxes_withheld,
        'total_remittances_made': total_remittances_made,
        'tax_still_due': tax_still_due,
        'total_penalties': total_penalties,
        'total_amount_still_due': total_amount_still_due
    }

    filename = "BIR 1601-FQ {} {} {}".format(company, year, quarter)
    
    context["build_version"] = frappe.utils.get_build_version()
    context["bir_form_images"] = get_bir_form_images("1601-FQ 2020 final-1.png")
    html = frappe.render_template("templates/bir_forms/bir_1601_fq_template.html", context)
    options["page-size"] = "Legal"

    return_pdf_document(html, filename, options, response_type)

@frappe.whitelist()
def bir_1601_fq_qap(company, year, quarter, response_type="download"):
    precision = cint(frappe.db.get_default("currency_precision")) or 2
    report_is_permitted('BIR 1601-FQ')

    year = int(year)
    quarter = int(quarter)
    total_remittances_made = 0
    total_taxes_withheld = 0
    tax_still_due = 0
    total_penalties = 0
    total_amount_still_due = 0

    # TODO: custom base amount
    # (CASE 
    #                 WHEN EXISTS(SELECT 1 FROM `tabPurchase Taxes and Charges` temp 
    #                         WHERE temp.parent = ptac.parent AND temp.name <> ptac.name and (temp.base_tax_amount < 0 or temp.add_deduct_tax = 'Deduct')) /*multiple atc in one doc*/
    #                 THEN
    #                     ROUND((ABS(ptac.base_tax_amount) / (a.rate / 100)), 2)
    #                 ELSE
    #                     pi.base_total
    #             END)
    data = frappe.db.sql("""
        SELECT
            temp.supplier,
            temp.year,
            temp.month,
            temp.atc,
            a.rate,
            temp.base_tax_base,
            temp.base_tax_withheld
        FROM
            (
            SELECT 
                source.supplier,
                YEAR(source.posting_date) AS year,
                MONTH(source.posting_date) AS month,
                source.atc AS atc,
                SUM(source.base_total) AS base_tax_base,
                SUM(ABS(source.base_tax_amount)) AS base_tax_withheld
            FROM
            (
                SELECT 
                    pi.supplier,
                    pi.posting_date,
                    ptac.atc AS atc,
                    pi.base_total,
                    ptac.base_tax_amount
                FROM 
                    `tabPurchase Invoice` pi
                LEFT JOIN
                    `tabPurchase Taxes and Charges` ptac
                ON
                    pi.name = ptac.parent
                INNER JOIN
                    `tabAccount` a
                ON
                    ptac.account_head = a.name
                WHERE
                    pi.docstatus = 1
                    and pi.is_return = 0
                    and ((ptac.base_tax_amount < 0 and ptac.add_deduct_tax != 'Deduct') or (ptac.base_tax_amount >= 0 and ptac.add_deduct_tax = 'Deduct'))
                    and (a.account_type in ('Tax', 'Payable', '') or a.account_type is NULL)
                    and pi.company = %s
                    and YEAR(pi.posting_date) = %s
                    and QUARTER(pi.posting_date) = %s
                UNION ALL
                SELECT 
                    pe.party,
                    pe.posting_date,
                    atac.atc AS atc,
                    pe.base_paid_amount,
                    atac.base_tax_amount
                FROM 
                    `tabPayment Entry` pe
                LEFT JOIN
                    `tabAdvance Taxes and Charges` atac
                ON
                    pe.name = atac.parent
                INNER JOIN
                    `tabAccount` a
                ON
                    atac.account_head = a.name
                WHERE
                    pe.docstatus = 1
                    and pe.payment_type = 'Pay'
                    and pe.party_type = 'Supplier'
                    and ((atac.base_tax_amount < 0 and atac.add_deduct_tax != 'Deduct') or (atac.base_tax_amount >= 0 and atac.add_deduct_tax = 'Deduct'))
                    and (a.account_type in ('Tax', 'Payable', '') or a.account_type is NULL)
                    and pe.company = %s
                    and YEAR(pe.posting_date) = %s
                    and QUARTER(pe.posting_date) = %s
            ) source
            GROUP BY
                source.supplier,
                YEAR(source.posting_date),
                MONTH(source.posting_date),
                source.atc
            ) AS temp
        INNER JOIN 
            `tabATC` as a
        ON
            temp.atc = a.name
        WHERE 
            a.form_type = '2306'
        """, (company, year, quarter, company, year, quarter), as_dict=1)

    for entry in data:
        total_taxes_withheld += entry.base_tax_withheld
    
    tax_still_due = total_taxes_withheld - total_remittances_made
    total_amount_still_due = tax_still_due + total_penalties

    company_information = get_company_information(company)
    context = {
        'company': get_company_information(company),
        'year': year,
        'quarter': quarter,
        'data': data,
        'total_taxes_withheld': total_taxes_withheld,
        'total_remittances_made': total_remittances_made,
        'tax_still_due': tax_still_due,
        'total_penalties': total_penalties,
        'total_amount_still_due': total_amount_still_due
    }
    file_extension = "dat"
    
    context["build_version"] = frappe.utils.get_build_version()

    content = ''
    header = ''

    return_period = '{MM}/{YYYY}'.format(MM=('0' + str(first_month_in_quarter(quarter)))[-2:], YYYY=year)
    return_period_no_slash = '{MM}{YYYY}'.format(MM=('0' + str(first_month_in_quarter(quarter)))[-2:], YYYY=year)

    header = '{next}'.format(header=header, next='HQAP'[:5])
    header = '{header},{next}'.format(header=header, next='H1601FQ'[:7])
    header = '{header},{next}'.format(header=header, next=company_information['tin'][:9])
    header = '{header},{next}'.format(header=header, next=company_information['tin'][9:13])
    header = '{header},"{next}"'.format(header=header, next=company_information['company_name'][:50])
    header = '{header},{next}'.format(header=header, next=return_period[:7])
    header = '{header},{next}'.format(header=header, next=company_information['rdo_code'][:3])

    content = header + '\n'
    details = ''
    i = 0
    total_base_tax_base = 0
    total_base_tax_withheld = 0
    for entry in data:
        i += 1
        payee_information = get_supplier_information(entry.supplier)
        details = details + '{next}'.format(details=details, next='D1'[:2])
        details = '{details},{next}'.format(details=details, next='1601FQ'[:6])
        details = '{details},{next}'.format(details=details, next=payee_information['tin'][:9])
        details = '{details},{next}'.format(details=details, next=payee_information['tin'][9:13])
        details = '{details},"{next}"'.format(details=details, next=payee_information['supplier_name'][:50])
        
        details = '{details},"{next}"'.format(details=details, next=(payee_information['contact_last_name'][:30] if payee_information['supplier_type'] == 'Individual' else ''))
        details = '{details},"{next}"'.format(details=details, next=(payee_information['contact_first_name'][:30] if payee_information['supplier_type'] == 'Individual' else ''))
        details = '{details},"{next}"'.format(details=details, next=(payee_information['contact_middle_name'][:30] if payee_information['supplier_type'] == 'Individual' else ''))

        detail_return_period = '{MM}/{YYYY}'.format(MM=('0' + str(entry.month))[-2:], YYYY=entry.year)
        details = '{details},{next}'.format(details=details, next=detail_return_period[:7])
        details = '{details},{next}'.format(details=details, next=str(i)[:8])
        details = '{details},{next}'.format(details=details, next=entry.atc[:5])
        details = '{details},{next}'.format(details=details, next="{:.2f}".format(flt(entry.rate, 2)))
        details = '{details},{next}'.format(details=details, next="{:.2f}".format(flt(entry.base_tax_base, 2)))
        details = '{details},{next}'.format(details=details, next="{:.2f}".format(flt(entry.base_tax_withheld, 2)))

        total_base_tax_base += entry.base_tax_base
        total_base_tax_withheld += entry.base_tax_withheld
        details = details + '\n'
    
    content = content + details

    controls = ''
    controls = '{next}'.format(controls=controls, next='C1'[:5])
    controls = '{controls},{next}'.format(controls=controls, next='1601FQ'[:6])
    controls = '{controls},{next}'.format(controls=controls, next=company_information['tin'][:9])
    controls = '{controls},{next}'.format(controls=controls, next=company_information['tin'][9:13])
    controls = '{controls},{next}'.format(controls=controls, next=return_period[:7])
    controls = '{controls},{next}'.format(controls=controls, next="{:.2f}".format(flt(total_base_tax_base, 2)))
    controls = '{controls},{next}'.format(controls=controls, next="{:.2f}".format(flt(total_base_tax_withheld, 2)))

    content = content + controls
    
    filename = "{tin}{branch_code}{return_period}{form_type}".format(tin=company_information['tin'][:9],branch_code=company_information['tin'][9:13],return_period=return_period_no_slash,form_type='1601FQ')

    return_document(content, filename, file_extension, response_type)

@frappe.whitelist()
def bir_0619_e(company, year, month, due_date, amended_form, any_taxes_withheld,
    amount_of_remittance=0, amount_remitted=0,
    surcharge=0, compromise=0, interest=0,
    cash_drawee_bank='', cash_number='', cash_date=None, cash_amount=0,
    check_drawee_bank='', check_number='', check_date=None, check_amount=0,
    tax_debit_memo_number='', tax_debit_memo_date=None, tax_debit_memo_amount=0,
    others_name='', others_drawee_bank='', others_number='', others_date=None, others_amount=0,
    response_type="pdf"):
    precision = cint(frappe.db.get_default("currency_precision")) or 2
    report_is_permitted('BIR 0619-E')

    year = int(year)
    month = ("0" + str(month))[:2]
    due_date = getdate(due_date)

    context = {
        'company': get_company_information(company),
        'year': year,
        'month': month,
        'due_date': due_date,
        'amended_form': int(amended_form),
        'any_taxes_withheld': int(any_taxes_withheld),
        'amount_of_remittance': flt(amount_of_remittance, precision), 
        'amount_remitted': flt(amount_remitted, precision), 
        'surcharge': flt(surcharge, precision), 
        'compromise': flt(compromise, precision), 
        'interest': flt(interest, precision), 
        'cash_drawee_bank': cash_drawee_bank, 
        'cash_number': cash_number, 
        'cash_date': getdate(cash_date) if cash_date else None, 
        'cash_amount': flt(cash_amount, precision), 
        'check_drawee_bank': check_drawee_bank, 
        'check_number': check_number, 
        'check_date': getdate(check_date) if check_date else None, 
        'check_amount': flt(check_amount, precision), 
        'tax_debit_memo_number': tax_debit_memo_number, 
        'tax_debit_memo_date': getdate(tax_debit_memo_date) if tax_debit_memo_date else None, 
        'tax_debit_memo_amount': flt(tax_debit_memo_amount, precision), 
        'others_name': others_name, 
        'others_drawee_bank': others_drawee_bank, 
        'others_number': others_number, 
        'others_date': getdate(others_date) if others_date else None, 
        'others_amount': flt(others_amount, precision), 
    }

    filename = "BIR 0619-E {} {} {}".format(company, year, month)
    
    context["build_version"] = frappe.utils.get_build_version()
    context["bir_form_images"] = get_bir_form_images("0619-E Jan 2018 rev final-1.png")
    html = frappe.render_template("templates/bir_forms/bir_0619_e_template.html", context)
    options["page-size"] = "Letter"

    return_pdf_document(html, filename, options, response_type)

@frappe.whitelist()
def bir_0619_f(company, year, month, due_date, amended_form, any_taxes_withheld,
    amount_of_remittance_wmf10=0, amount_of_remittance_wmf20=0, amount_remitted=0,
    surcharge=0, compromise=0, interest=0,
    cash_drawee_bank='', cash_number='', cash_date=None, cash_amount=0,
    check_drawee_bank='', check_number='', check_date=None, check_amount=0,
    tax_debit_memo_number='', tax_debit_memo_date=None, tax_debit_memo_amount=0,
    others_name='', others_drawee_bank='', others_number='', others_date=None, others_amount=0,
    response_type="pdf"):
    precision = cint(frappe.db.get_default("currency_precision")) or 2
    report_is_permitted('BIR 0619-F')

    year = int(year)
    month = ("0" + str(month))[:2]
    due_date = getdate(due_date)

    context = {
        'company': get_company_information(company),
        'year': year,
        'month': month,
        'due_date': due_date,
        'amended_form': int(amended_form),
        'any_taxes_withheld': int(any_taxes_withheld),
        'amount_of_remittance_wmf10': flt(amount_of_remittance_wmf10, precision), 
        'amount_of_remittance_wmf20': flt(amount_of_remittance_wmf20, precision), 
        'amount_remitted': flt(amount_remitted, precision), 
        'surcharge': flt(surcharge, precision), 
        'compromise': flt(compromise, precision), 
        'interest': flt(interest, precision), 
        'cash_drawee_bank': cash_drawee_bank, 
        'cash_number': cash_number, 
        'cash_date': getdate(cash_date) if cash_date else None, 
        'cash_amount': flt(cash_amount, precision), 
        'check_drawee_bank': check_drawee_bank, 
        'check_number': check_number, 
        'check_date': getdate(check_date) if check_date else None, 
        'check_amount': flt(check_amount, precision), 
        'tax_debit_memo_number': tax_debit_memo_number, 
        'tax_debit_memo_date': getdate(tax_debit_memo_date) if tax_debit_memo_date else None, 
        'tax_debit_memo_amount': flt(tax_debit_memo_amount, precision), 
        'others_name': others_name, 
        'others_drawee_bank': others_drawee_bank, 
        'others_number': others_number, 
        'others_date': getdate(others_date) if others_date else None, 
        'others_amount': flt(others_amount, precision), 
    }

    filename = "BIR 0619-F {} {} {}".format(company, year, month)
    
    context["build_version"] = frappe.utils.get_build_version()
    context["bir_form_images"] = get_bir_form_images("0619-F Jan 2018 rev final-1.png")
    html = frappe.render_template("templates/bir_forms/bir_0619_f_template.html", context)
    options["page-size"] = "Letter"

    return_pdf_document(html, filename, options, response_type)

@frappe.whitelist()
def return_pdf_document(html, filename="document", options=options, response_type="download"):
    frappe.local.response.filename = "{filename}.pdf".format(filename=filename)
    frappe.local.response.filecontent = get_pdf(html, options)
    frappe.local.response.type = response_type

@frappe.whitelist()
def return_document(content, filename, file_extension, response_type="download"):
    frappe.local.response.filename = "{filename}.{file_extension}".format(filename=filename, file_extension=file_extension)
    frappe.local.response.filecontent = content
    frappe.local.response.type = response_type

def make_ordinal(n):
    '''
    Convert an integer into its ordinal representation::

        make_ordinal(0)   => '0th'
        make_ordinal(3)   => '3rd'
        make_ordinal(122) => '122nd'
        make_ordinal(213) => '213th'
    '''
    n = int(n)
    suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    if 11 <= (n % 100) <= 13:
        suffix = 'th'

    return str(n) + suffix
