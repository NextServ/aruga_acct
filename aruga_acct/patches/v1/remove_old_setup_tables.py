import frappe

def execute():
    remove_ph_localization_setup()
    remove_tax_declaration_setup()

def remove_ph_localization_setup():
    print("Deleting PH Localization Setup")
    frappe.db.sql("""delete from `tabDocType` where name = 'PH Localization Setup' """)
    frappe.db.sql("""delete from `tabSingles` where doctype = 'PH Localization Setup' """)

def remove_tax_declaration_setup():
    print("Deleting Tax Declaration Setup")
    frappe.db.sql("""delete from `tabDocType` where name = 'Tax Declaration Setup' """)
    frappe.db.sql("""delete from `tabSingles` where doctype = 'Tax Declaration Setup' """)