import frappe
from frappe.utils import flt, rounded, getdate
from frappe import _
from erpnext import __version__
import json
import re

@frappe.whitelist()
def get_custom_formatted_address(address):
    result = ""
    if frappe.db.exists("Address", {'name': address}):
        address_doc = frappe.get_doc("Address", address)
        result = address_doc.address_line1 or ''

        if result and address_doc.address_line2:
            result = result + ', ' + address_doc.address_line2
        elif not result and address_doc.address_line2:
            result = address_doc.address_line2
        
        if result and address_doc.city:
            result = result + ', ' + address_doc.city
        elif not result and address_doc.city:
            result = address_doc.city

        if result and address_doc.state:
            result = result + ', ' + address_doc.state
        elif not result and address_doc.state:
            result = address_doc.state
    return result

@frappe.whitelist()
def get_company_information(company):
    company_doc = frappe.get_doc('Company', company)
    company_address_doc = None

    company_address = ''
    company_address_text = ''
    zipcode = ''
    phone = ''
    email_id = ''
    company_address_dynamic_link_doc = None

    if frappe.db.exists("Dynamic Link", {'link_doctype': 'Company', 'link_name': company, 'parenttype': 'Address'}):
        company_address_dynamic_link_doc = frappe.get_last_doc('Dynamic Link', filters={'link_doctype': 'Company', 'link_name': company, 'parenttype': 'Address'})
    

    if company_address_dynamic_link_doc:
        zipcode = frappe.db.get_value('Address', company_address_dynamic_link_doc.parent, 'pincode')
        email_id = frappe.db.get_value('Address', company_address_dynamic_link_doc.parent, 'email_id')
        zipcode = zipcode if zipcode else ''

        phone = frappe.db.get_value('Address', company_address_dynamic_link_doc.parent, 'phone')
        phone = phone if phone else ''

        company_address = company_address_dynamic_link_doc.parent if company_address_dynamic_link_doc.parent else ''
    
    if company_address:
        company_address_doc = frappe.get_doc('Address', company_address)
        company_address_text = get_custom_formatted_address(company_address)

    aruga_accounting_company_setup = None
    try:
        aruga_accounting_company_setup = frappe.get_doc('PH Localization Company Setup', company)
    except:
        frappe.throw("Please create a PH Localization Company Setup record for {0}".format(company))
    
    registered_name = aruga_accounting_company_setup.registered_name
    permit_no = aruga_accounting_company_setup.permit_no
    permit_date_issued = aruga_accounting_company_setup.permit_date_issued
    rdo_code = aruga_accounting_company_setup.rdo_code
    vat_industry = aruga_accounting_company_setup.vat_industry
    withholding_agent_category = aruga_accounting_company_setup.withholding_agent_category

    authorized_representative_1 = aruga_accounting_company_setup.authorized_representative_1 or ""
    title_1 = aruga_accounting_company_setup.title_1 or ""
    tin_of_signatory_1 = aruga_accounting_company_setup.tin_of_signatory_1 or ""
    authorized_representative_2 = aruga_accounting_company_setup.authorized_representative_2 or ""
    title_2 = aruga_accounting_company_setup.title_2 or ""
    tin_of_signatory_2 = aruga_accounting_company_setup.tin_of_signatory_2 or ""
    
    fiscal_month_end = aruga_accounting_company_setup.fiscal_month_end
    fiscal_month_end = (fiscal_month_end if fiscal_month_end else 12)

    result = {
        'company_name': company_doc.name,
        'registered_name': registered_name if registered_name else company_doc.name,
        'address': company_address_text if company_address_text else '',
        'address_line1': company_address_doc.address_line1 if company_address_doc and company_address_doc.address_line1 else '',
        'address_line2': company_address_doc.address_line2 if company_address_doc and company_address_doc.address_line2 else '',
        'city': company_address_doc.city if company_address_doc and company_address_doc.city else '',
        'state': company_address_doc.state if company_address_doc and company_address_doc.state else '',
        'tin': preformat_tin(company_doc.tax_id if company_doc.tax_id else ''),
        'tin_with_dash': preformat_tin_with_dash(company_doc.tax_id if company_doc.tax_id else ''),
        'branch_code': preformat_tin(company_doc.tax_id if company_doc.tax_id else '')[9:13], # bir structure length = 3, alphalist validation module = 4
        'zipcode': zipcode,
        'erpnext_version': __version__,
        'permit_no': permit_no if permit_no else '',
        'permit_date_issued': permit_date_issued if permit_date_issued else '',
        'rdo_code': rdo_code if rdo_code else '',
        'vat_industry': vat_industry if vat_industry else '',
        'withholding_agent_category': withholding_agent_category if withholding_agent_category else '',
        'phone': phone if phone else '',
        'email_id': email_id if email_id else '',
        'authorized_representative_1': authorized_representative_1,
        'title_1': title_1,
        'tin_of_signatory_1': preformat_tin(tin_of_signatory_1),
        'authorized_representative_2': authorized_representative_2,
        'title_2': title_2,
        'tin_of_signatory_2': preformat_tin(tin_of_signatory_2),
        'fiscal_month_end': fiscal_month_end
    }

    return result

@frappe.whitelist()
def get_employee_information(employee):
    employee_doc = frappe.get_doc('Employee', employee)
    employee_address = ''
    zipcode = ''
    phone = ''
    employee_address_dynamic_link_doc = None
    employee_contact_dynamic_link_doc = None
    employee_address_doc = None
    contact_doc = None
    contact_first_name = ''
    contact_middle_name = ''
    contact_last_name = ''
    employment_type = employee_doc.employment_type

    # if frappe.db.exists("Dynamic Link", {'link_doctype': 'employee', 'link_name': employee, 'parenttype': 'Address'}):
    #     employee_address_dynamic_link_doc = frappe.get_last_doc('Dynamic Link', filters={'link_doctype': 'employee', 'link_name': employee, 'parenttype': 'Address'})
    # if hasattr(employee_doc, 'employee_primary_address'):
    #     if employee_doc.employee_primary_address and frappe.db.exists("Address", {'name': employee_doc.employee_primary_address}):
    #         employee_address_doc = frappe.get_doc('Address', employee_doc.employee_primary_address)
    # else:
    #     if frappe.db.exists("Dynamic Link", {'link_doctype': 'employee', 'link_name': employee, 'parenttype': 'Address'}):
    #         employee_address_dynamic_link_doc = frappe.get_last_doc('Dynamic Link', filters={'link_doctype': 'employee', 'link_name': employee, 'parenttype': 'Address'})
    #         employee_address_doc = frappe.get_doc('Address', employee_address_dynamic_link_doc.parent)

    # if hasattr(employee_doc, 'employee_primary_contact'):
    #     if employee_doc.employee_primary_contact and frappe.db.exists("Contact", {'name': employee_doc.employee_primary_contact}):
    #         contact_doc = frappe.get_doc('Contact', employee_doc.employee_primary_contact)
    # else:
    #     employee_contact_dynamic_link_doc = frappe.get_last_doc('Dynamic Link', filters={'link_doctype': 'employee', 'link_name': employee, 'parenttype': 'Contact'})
    #     contact_doc = frappe.get_doc('Contact', employee_contact_dynamic_link_doc.parent)

    # if contact_doc:
    #     contact_first_name = contact_doc.first_name if contact_doc.first_name else ''
    #     contact_middle_name = contact_doc.middle_name if contact_doc.middle_name else ''
    #     contact_last_name = contact_doc.last_name if contact_doc.last_name else ''
    
    # if employee_address_doc:
    #     zipcode = employee_address_doc.pincode if employee_address_doc.pincode else ''
    #     phone = employee_address_doc.phone if employee_address_doc.phone else ''
    #     employee_address = employee_address_doc.name
    
    # if employee_address:
    #     employee_address = get_custom_formatted_address(employee_address)
    # tin = preformat_tin(employee_doc.tax_id if employee_doc.tax_id else '')
    # branch_code = tin[9:13] # bir structure length = 3, alphalist validation module = 4

    # todo: branch_code and tin
    result = {
        'employee_name': employee_doc.employee_name,
        'employment_type': employment_type,
        'contact_first_name': employee_doc.first_name,
        'contact_middle_name': employee_doc.middle_name,
        'contact_last_name': employee_doc.last_name,
        'address': employee_doc.current_address,
        'address_line1': employee_doc.current_address,
        'address_line2': '',
        'city': '',
        'state': '',
        # 'city': employee_address_doc.city if employee_address_doc and employee_address_doc.city else '',
        # 'state': employee_address_doc.state if employee_address_doc and employee_address_doc.state else '',
        # 'tin': preformat_tin(employee_doc.tax_id if employee_doc.tax_id else ''),
        # 'tin_with_dash': preformat_tin_with_dash(employee_doc.tax_id if employee_doc.tax_id else ''),
        'tin': '',
        'tin_with_dash': '',
        'branch_code': '',
        'zipcode': zipcode,
        'phone': employee_doc.cell_number or ''
    }

    return result

@frappe.whitelist()
def get_supplier_information(supplier):
    supplier_doc = frappe.get_doc('Supplier', supplier)
    supplier_address = ''
    zipcode = ''
    phone = ''
    supplier_address_dynamic_link_doc = None
    supplier_contact_dynamic_link_doc = None
    supplier_address_doc = None
    contact_doc = None
    contact_first_name = ''
    contact_middle_name = ''
    contact_last_name = ''
    supplier_type = supplier_doc.supplier_type

    # if frappe.db.exists("Dynamic Link", {'link_doctype': 'Supplier', 'link_name': supplier, 'parenttype': 'Address'}):
    #     supplier_address_dynamic_link_doc = frappe.get_last_doc('Dynamic Link', filters={'link_doctype': 'Supplier', 'link_name': supplier, 'parenttype': 'Address'})
    if hasattr(supplier_doc, 'supplier_primary_address'):
        if supplier_doc.supplier_primary_address and frappe.db.exists("Address", {'name': supplier_doc.supplier_primary_address}):
            supplier_address_doc = frappe.get_doc('Address', supplier_doc.supplier_primary_address)
    else:
        if frappe.db.exists("Dynamic Link", {'link_doctype': 'Supplier', 'link_name': supplier, 'parenttype': 'Address'}):
            supplier_address_dynamic_link_doc = frappe.get_last_doc('Dynamic Link', filters={'link_doctype': 'Supplier', 'link_name': supplier, 'parenttype': 'Address'})
            supplier_address_doc = frappe.get_doc('Address', supplier_address_dynamic_link_doc.parent)

    if hasattr(supplier_doc, 'supplier_primary_contact'):
        if supplier_doc.supplier_primary_contact and frappe.db.exists("Contact", {'name': supplier_doc.supplier_primary_contact}):
            contact_doc = frappe.get_doc('Contact', supplier_doc.supplier_primary_contact)
    else:
        supplier_contact_dynamic_link_doc = frappe.get_last_doc('Dynamic Link', filters={'link_doctype': 'Supplier', 'link_name': supplier, 'parenttype': 'Contact'})
        contact_doc = frappe.get_doc('Contact', supplier_contact_dynamic_link_doc.parent)

    if contact_doc:
        contact_first_name = contact_doc.first_name if contact_doc.first_name else ''
        contact_middle_name = contact_doc.middle_name if contact_doc.middle_name else ''
        contact_last_name = contact_doc.last_name if contact_doc.last_name else ''

    # if supplier_address_dynamic_link_doc:
    #     zipcode = frappe.db.get_value('Address', supplier_address_dynamic_link_doc.parent, 'pincode')
    #     zipcode = zipcode if zipcode else ''

    #     phone = frappe.db.get_value('Address', supplier_address_dynamic_link_doc.parent, 'phone')
    #     phone = phone if phone else ''
        
    #     supplier_address = supplier_address_dynamic_link_doc.parent if supplier_address_dynamic_link_doc.parent else ''
    
    if supplier_address_doc:
        zipcode = supplier_address_doc.pincode if supplier_address_doc.pincode else ''
        phone = supplier_address_doc.phone if supplier_address_doc.phone else ''
        supplier_address = supplier_address_doc.name
    
    if supplier_address:
        supplier_address = get_custom_formatted_address(supplier_address)
    tin = preformat_tin(supplier_doc.tax_id if supplier_doc.tax_id else '')
    branch_code = tin[9:13] # bir structure length = 3, alphalist validation module = 4

    result = {
        'supplier_name': supplier_doc.supplier_name,
        'supplier_type': supplier_type,
        'contact_first_name': contact_first_name,
        'contact_middle_name': contact_middle_name,
        'contact_last_name': contact_last_name,
        'address': supplier_address if supplier_address else '',
        'address_line1': supplier_address_doc.address_line1 if supplier_address_doc and supplier_address_doc.address_line1 else '',
        'address_line2': supplier_address_doc.address_line2 if supplier_address_doc and supplier_address_doc.address_line2 else '',
        'city': supplier_address_doc.city if supplier_address_doc and supplier_address_doc.city else '',
        'state': supplier_address_doc.state if supplier_address_doc and supplier_address_doc.state else '',
        'tin': preformat_tin(supplier_doc.tax_id if supplier_doc.tax_id else ''),
        'tin_with_dash': preformat_tin_with_dash(supplier_doc.tax_id if supplier_doc.tax_id else ''),
        'branch_code': branch_code,
        'zipcode': zipcode,
        'phone': phone if phone else ''
    }

    return result

@frappe.whitelist()
def get_customer_information(customer):
    customer_doc = frappe.get_doc('Customer', customer)
    customer_address = ''
    zipcode = ''
    phone = ''
    customer_address_dynamic_link_doc = None
    customer_address_doc = None
    contact_doc = None
    contact_first_name = ''
    contact_middle_name = ''
    contact_last_name = ''
    customer_type = customer_doc.customer_type

    # if frappe.db.exists("Dynamic Link", {'link_doctype': 'Customer', 'link_name': customer, 'parenttype': 'Address'}):
    #     customer_address_dynamic_link_doc = frappe.get_last_doc('Dynamic Link', filters={'link_doctype': 'Customer', 'link_name': customer, 'parenttype': 'Address'})
    if customer_doc.customer_primary_address and frappe.db.exists("Address", {'name': customer_doc.customer_primary_address}):
        customer_address_doc = frappe.get_doc('Address', customer_doc.customer_primary_address)

    if customer_doc.customer_primary_contact and frappe.db.exists("Contact", {'name': customer_doc.customer_primary_contact}):
        contact_doc = frappe.get_doc('Contact', customer_doc.customer_primary_contact)
        contact_first_name = contact_doc.first_name if contact_doc.first_name else ''
        contact_middle_name = contact_doc.middle_name if contact_doc.middle_name else ''
        contact_last_name = contact_doc.last_name if contact_doc.last_name else ''

    # if customer_address_dynamic_link_doc:
    #     zipcode = frappe.db.get_value('Address', customer_address_dynamic_link_doc.parent, 'pincode')
    #     zipcode = zipcode if zipcode else ''

    #     phone = frappe.db.get_value('Address', customer_address_dynamic_link_doc.parent, 'phone')
    #     phone = phone if phone else ''
        
    #     customer_address = customer_address_dynamic_link_doc.parent if customer_address_dynamic_link_doc.parent else ''
    
    if customer_address_doc:
        zipcode = customer_address_doc.pincode if customer_address_doc.pincode else ''
        phone = customer_address_doc.phone if customer_address_doc.phone else ''
        customer_address = customer_address_doc.name
    
    if customer_address:
        customer_address = get_custom_formatted_address(customer_address)
    tin = preformat_tin(customer_doc.tax_id if customer_doc.tax_id else '')
    branch_code = tin[9:13] # bir structure length = 3, alphalist validation module = 4

    result = {
        'customer_name': customer_doc.customer_name,
        'customer_type': customer_type,
        'contact_first_name': contact_first_name,
        'contact_middle_name': contact_middle_name,
        'contact_last_name': contact_last_name,
        'address': customer_address if customer_address else '',
        'address_line1': customer_address_doc.address_line1 if customer_address_doc and customer_address_doc.address_line1 else '',
        'address_line2': customer_address_doc.address_line2 if customer_address_doc and customer_address_doc.address_line2 else '',
        'city': customer_address_doc.city if customer_address_doc and customer_address_doc.city else '',
        'state': customer_address_doc.state if customer_address_doc and customer_address_doc.state else '',
        'tin': preformat_tin(customer_doc.tax_id if customer_doc.tax_id else ''),
        'tin_with_dash': preformat_tin_with_dash(customer_doc.tax_id if customer_doc.tax_id else ''),
        'branch_code': branch_code, # bir structure length = 3, alphalist validation module = 4
        'zipcode': zipcode,
        'phone': phone if phone else ''
    }

    return result

@frappe.whitelist()
def preformat_tin(tin):
    tin = re.sub("[^0-9]", "", tin)
    result = "{0}000000000000".format(tin)
    # tin is 12 or 13? digits
    return result[:13]

    
@frappe.whitelist()
def preformat_tin_with_dash(tin):
    tin = re.sub("[^0-9]", "", tin)
    result = "{0}000000000000".format(tin)
    # tin is 12 or 13? digits
    result = "{0}-{1}-{2}-{3}".format(result[:3], result[3:6], result[6:9], result[9:13])
    return result[:16]

@frappe.whitelist()
def get_years():
    result = []
    q = frappe.db.sql("""
        SELECT 
            year(min(year_start_date)) as min_year, 
            year(max(year_end_date)) as max_year 
        FROM 
            `tabFiscal Year`;
        """, (), as_dict=1)

    if q[0]:
        start = q[0].min_year
        end = q[0].max_year + 1

        for x in range(start, end):
            result.append(x)
    
    return result

def report_is_permitted(report_name):
    doc = frappe.get_doc("Report", report_name)
    doc.custom_columns = []

    if not doc.is_permitted():
        frappe.throw(
            _("You don't have access to Report: {0}").format(report_name),
            frappe.PermissionError,
        )

@frappe.whitelist()
def is_local_dev():
    # ence.local:8002 (has local port = True)
    # erpnextsandbox.serviotech.com (no local port = False)
    return len(frappe.utils.get_host_name().split(':')) == 2

@frappe.whitelist()
def generate_company_tax_templates(company):
    n = 0

    sales_tax_templates = {
        'VAT Sales':'',
        'Sales to Government':'',
        'Zero Rated Sales':'',
        'Exempt Sales':''
    }

    item_sales_tax_templates = {
        'VAT Sales':'',
        'Sales to Government':'',
        'Zero Rated Sales':'',
        'Exempt Sales':''
    }

    purchase_tax_templates = {
        'Capital Goods':'',
        'Domestic Purchases of Goods':'',
        'Importation of Goods':'',
        'Domestic Purchase of Services':'',
        'Services Rendered by Non-residents':'',
        'Zero Rated Purchase':'',
        'Exempt Purchase':'',
        'Others':'',
        # 'Directly Attributable to Exempt Sales':'',
        # 'Directly Attributable to Sale to Government':''
    }

    item_purchase_tax_templates = {
        'Capital Goods':'',
        'Domestic Purchases of Goods':'',
        'Importation of Goods':'',
        'Domestic Purchase of Services':'',
        'Services Rendered by Non-residents':'',
        'Zero Rated Purchase':'',
        'Exempt Purchase':'',
        'Others':'',
        # 'Directly Attributable to Exempt Sales':'',
        # 'Directly Attributable to Sale to Government':''
    }

    for t in sales_tax_templates:
        if not frappe.db.exists('Sales Taxes and Charges Template', {'company': company, 'title': t}):
            stac = frappe.get_doc({
                'doctype': 'Sales Taxes and Charges Template',
                'title': t,
                'company': company
            })
            stac.insert()
            sales_tax_templates[t] = stac.name
            n += 1
        else:
            sales_tax_templates[t] = frappe.get_value('Sales Taxes and Charges Template', {'company': company, 'title': t}, 'name')

    for t in item_sales_tax_templates:
        if not frappe.db.exists('Item Tax Template', {'company': company, 'title': t}):
            itt = frappe.get_doc({
                'doctype': 'Item Tax Template',
                'title': t,
                'company': company
            })

            itt.flags.ignore_mandatory = True
            itt.insert()
            item_sales_tax_templates[t] = itt.name
            n += 1
        else:
            item_sales_tax_templates[t] = frappe.get_value('Item Tax Template', {'company': company, 'title': t}, 'name')

    for t in purchase_tax_templates:
        if not frappe.db.exists('Purchase Taxes and Charges Template', {'company': company, 'title': t}):
            ptac = frappe.get_doc({
                'doctype': 'Purchase Taxes and Charges Template',
                'title': t,
                'company': company
            })
            ptac.insert()
            purchase_tax_templates[t] = ptac.name
            n += 1
        else:
            purchase_tax_templates[t] = frappe.get_value('Purchase Taxes and Charges Template', {'company': company, 'title': t}, 'name')

    for t in item_purchase_tax_templates:
        if not frappe.db.exists('Item Tax Template', {'company': company, 'title': t}):
            itt = frappe.get_doc({
                'doctype': 'Item Tax Template',
                'title': t,
                'company': company
            })

            itt.flags.ignore_mandatory = True
            itt.insert()
            item_purchase_tax_templates[t] = itt.name
            n += 1
        else:
            item_purchase_tax_templates[t] = frappe.get_value('Item Tax Template', {'company': company, 'title': t}, 'name')
    
    tax_declaration_company_setup = None
    if frappe.db.exists("Tax Declaration Company Setup", {'name': company}):
        tax_declaration_company_setup = frappe.get_doc('Tax Declaration Company Setup', company)
    else:
        tax_declaration_company_setup = frappe.get_doc({
            'doctype': 'Tax Declaration Company Setup',
            'company': company
            })
        tax_declaration_company_setup.insert()
        tax_declaration_company_setup.reload()
    
    tax_declaration_company_setup.vat_sales = sales_tax_templates['VAT Sales']
    tax_declaration_company_setup.sales_to_government = tax_declaration_company_setup.sales_to_government or sales_tax_templates['Sales to Government']
    tax_declaration_company_setup.zero_rated_sales = tax_declaration_company_setup.zero_rated_sales or sales_tax_templates['Zero Rated Sales']
    tax_declaration_company_setup.exempt_sales = tax_declaration_company_setup.exempt_sales or sales_tax_templates['Exempt Sales']

    tax_declaration_company_setup.item_vat_sales = tax_declaration_company_setup.item_vat_sales or item_sales_tax_templates['VAT Sales']
    tax_declaration_company_setup.item_sales_to_government = tax_declaration_company_setup.item_sales_to_government or item_sales_tax_templates['Sales to Government']
    tax_declaration_company_setup.item_zero_rated_sales = tax_declaration_company_setup.item_zero_rated_sales or item_sales_tax_templates['Zero Rated Sales']
    tax_declaration_company_setup.item_exempt_sales = tax_declaration_company_setup.item_exempt_sales or item_sales_tax_templates['Exempt Sales']

    tax_declaration_company_setup.capital_goods = tax_declaration_company_setup.capital_goods or purchase_tax_templates['Capital Goods']
    tax_declaration_company_setup.domestic_purchases_of_goods = tax_declaration_company_setup.domestic_purchases_of_goods or purchase_tax_templates['Domestic Purchases of Goods']
    tax_declaration_company_setup.importation_of_goods = tax_declaration_company_setup.importation_of_goods or purchase_tax_templates['Importation of Goods']
    tax_declaration_company_setup.domestic_purchase_of_services = tax_declaration_company_setup.domestic_purchase_of_services or purchase_tax_templates['Domestic Purchase of Services']
    tax_declaration_company_setup.services_rendered_by_non_residents = tax_declaration_company_setup.services_rendered_by_non_residents or purchase_tax_templates['Services Rendered by Non-residents']
    tax_declaration_company_setup.zero_rated_purchase = tax_declaration_company_setup.zero_rated_purchase or purchase_tax_templates['Zero Rated Purchase']
    tax_declaration_company_setup.exempt_purchase = tax_declaration_company_setup.exempt_purchase or purchase_tax_templates['Exempt Purchase']
    tax_declaration_company_setup.others = tax_declaration_company_setup.others or purchase_tax_templates['Others']
    # tax_declaration_company_setup.directly_attributable_to_exempt_sales = tax_declaration_company_setup.directly_attributable_to_exempt_sales or purchase_tax_templates['Directly Attributable to Exempt Sales']
    # tax_declaration_company_setup.directly_attributable_to_sale_to_government = tax_declaration_company_setup.directly_attributable_to_sale_to_government or purchase_tax_templates['Directly Attributable to Sale to Government']
    
    tax_declaration_company_setup.item_capital_goods = tax_declaration_company_setup.item_capital_goods or item_purchase_tax_templates['Capital Goods']
    tax_declaration_company_setup.item_domestic_purchases_of_goods = tax_declaration_company_setup.item_domestic_purchases_of_goods or item_purchase_tax_templates['Domestic Purchases of Goods']
    tax_declaration_company_setup.item_importation_of_goods = tax_declaration_company_setup.item_importation_of_goods or item_purchase_tax_templates['Importation of Goods']
    tax_declaration_company_setup.item_domestic_purchase_of_services = tax_declaration_company_setup.item_domestic_purchase_of_services or item_purchase_tax_templates['Domestic Purchase of Services']
    tax_declaration_company_setup.item_services_rendered_by_non_residents = tax_declaration_company_setup.item_services_rendered_by_non_residents or item_purchase_tax_templates['Services Rendered by Non-residents']
    tax_declaration_company_setup.item_zero_rated_purchase = tax_declaration_company_setup.item_zero_rated_purchase or purchase_tax_templates['Zero Rated Purchase']
    tax_declaration_company_setup.item_exempt_purchase = tax_declaration_company_setup.item_exempt_purchase or purchase_tax_templates['Exempt Purchase']
    tax_declaration_company_setup.item_others = tax_declaration_company_setup.item_others or item_purchase_tax_templates['Others']
    # tax_declaration_company_setup.item_directly_attributable_to_exempt_sales = tax_declaration_company_setup.item_directly_attributable_to_exempt_sales or item_purchase_tax_templates['Directly Attributable to Exempt Sales']
    # tax_declaration_company_setup.item_directly_attributable_to_sale_to_government = tax_declaration_company_setup.item_directly_attributable_to_sale_to_government or item_purchase_tax_templates['Directly Attributable to Sale to Government']

    tax_declaration_company_setup.save()
    
    frappe.msgprint(_('Tax template(s) successfully created: <strong>{0}</strong>'.format(n)))

    return n

@frappe.whitelist()
def get_formatted_full_name(last_name, first_name, middle_name):
    return "{0}, {1}".format(last_name, first_name) + " {0}".format(middle_name) if middle_name else ""