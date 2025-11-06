from __future__ import unicode_literals
from frappe import _
import frappe

from frappe.utils import (add_days, cstr, flt, get_datetime, getdate, nowdate, today)

def sales_invoice_validate(doc, method):
    validate_item_tax_template(doc)
    validate_taxes_and_charges(doc)

def purchase_invoice_validate(doc, method):
    validate_item_tax_template(doc)
    validate_taxes_and_charges(doc)

def validate_item_tax_template(doc):
    message = ''
    multiple_distinct_item_tax_template = []

    for i in doc.items:
        if i.item_code in multiple_distinct_item_tax_template:
            break
        for j in doc.items:
            if i.idx != j.idx and i.item_code == j.item_code and i.item_tax_template != j.item_tax_template:
                if not i.item_code in multiple_distinct_item_tax_template:
                    multiple_distinct_item_tax_template.append(i.item_code)
                    break
        
    if multiple_distinct_item_tax_template:
        message = "The following item(s) cannot be assigned to multiple different tax templates: <ul>"
        for i in multiple_distinct_item_tax_template:
            message = message + "<li><strong>" + i + "</strong></li>"
        message = message + "</ul>"

        frappe.throw(
            title="Item Tax Template",
            msg=message
        )
    
def payment_entry_validate(doc, method):
    for item in doc.taxes:
        if item.tax_amount < 0:
            message = "Tax amount cannot be negative <strong>{}</strong>.".format(item.tax_amount)
            frappe.throw(
                title="Advance Taxes and Charges",
                msg=message
            )
    
    validate_taxes_and_charges(doc)
    
def validate_taxes_and_charges(doc):
    if doc.doctype == 'Sales Invoice' or doc.doctype == 'Purchase Invoice':
        if not doc.taxes_and_charges:
            tax_row = next((row for row in doc.taxes if row.get('base_tax_amount') > 0), None)
            if tax_row:
                frappe.msgprint(_("Please enter a Taxes and Charges Template."), indicator='orange', alert=True)
    elif doc.doctype == 'Payment Entry' and doc.party_type == 'Customer':
        if not doc.sales_taxes_and_charges_template:
            tax_row = next((row for row in doc.taxes if row.get('base_tax_amount') > 0), None)
            if tax_row:
                frappe.msgprint(_("Please enter a Taxes and Charges Template."), indicator='orange', alert=True)
    elif doc.doctype == 'Payment Entry' and doc.party_type == 'Supplier':
        if not doc.purchase_taxes_and_charges_template:
            tax_row = next((row for row in doc.taxes if row.get('base_tax_amount') > 0), None)
            if tax_row:
                frappe.msgprint(_("Please enter a Taxes and Charges Template."), indicator='orange', alert=True)