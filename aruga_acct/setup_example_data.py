"""
Aruga Accounting - Example Data Setup Script
=============================================
Run with:  bench --site localhost execute aruga_acct.setup_example_data.setup

This creates all the sample data you need to test:
  - Company address & tax ID
  - PH Localization Company Setup
  - Tax Declaration Company Setup
  - Tax templates (Sales, Purchase, Item Tax)
  - Customers & Suppliers with TINs and addresses
  - Items
  - Sample Sales Invoices (VAT, Zero-Rated, Exempt)
  - Sample Purchase Invoices (with EWT / withholding taxes)
  - Sample Payment Entries
  - Sample Expense Claims
"""

import frappe
from frappe.utils import today, add_days, add_months, getdate, nowdate
from erpnext.setup.utils import enable_all_roles_and_domains


COMPANY = "ARUGA"
COMPANY_ABBR = "A"
CURRENCY = "PHP"


def setup():
    frappe.flags.ignore_permissions = True
    frappe.flags.mute_emails = True
    frappe.flags.mute_messages = True

    print("=" * 60)
    print("  Aruga Accounting - Example Data Setup")
    print("=" * 60)

    setup_company()
    create_accounts()
    create_tax_templates()
    create_item_tax_templates()
    setup_ph_localization()
    setup_tax_declaration()
    create_customers()
    create_suppliers()
    create_items()

    frappe.db.commit()  # commit setup data before creating invoices

    create_sales_invoices()
    create_purchase_invoices()
    create_payment_entries()

    frappe.db.commit()
    print("\n✓ All example data created successfully!")
    print("  You can now test BIR forms, reports, and tax workflows.")


# ── 1. Company ────────────────────────────────────────────────
def setup_company():
    print("\n[1/11] Setting up Company...")
    company = frappe.get_doc("Company", COMPANY)

    # Set TIN (Tax Identification Number)
    if not company.tax_id:
        company.tax_id = "123-456-789-000"
        company.save()
        print("  → Set company TIN: 123-456-789-000")

    # Create company address if none exists
    if not frappe.db.exists("Dynamic Link", {
        "link_doctype": "Company",
        "link_name": COMPANY,
        "parenttype": "Address"
    }):
        addr = frappe.get_doc({
            "doctype": "Address",
            "address_title": COMPANY,
            "address_type": "Office",
            "address_line1": "123 Rizal Avenue",
            "address_line2": "Brgy. San Antonio",
            "city": "Makati City",
            "state": "Metro Manila",
            "country": "Philippines",
            "pincode": "1200",
            "phone": "+63 2 8888 1234",
            "email_id": "accounting@aruga.ph",
            "links": [{
                "link_doctype": "Company",
                "link_name": COMPANY
            }]
        })
        addr.insert()
        print(f"  → Created company address: {addr.name}")
    else:
        print("  → Company address already exists")


# ── 2. Accounts ───────────────────────────────────────────────
def create_accounts():
    print("\n[2/11] Creating accounts...")

    accounts_to_create = [
        {
            "account_name": "EWT Payable",
            "parent_account": f"Duties and Taxes - {COMPANY_ABBR}",
            "account_type": "Tax",
            "root_type": "Liability",
        },
        {
            "account_name": "Input VAT",
            "parent_account": f"Tax Assets - {COMPANY_ABBR}",
            "account_type": "Tax",
            "root_type": "Asset",
        },
        {
            "account_name": "Output VAT",
            "parent_account": f"Duties and Taxes - {COMPANY_ABBR}",
            "account_type": "Tax",
            "root_type": "Liability",
        },
        {
            "account_name": "Withholding Tax Payable",
            "parent_account": f"Duties and Taxes - {COMPANY_ABBR}",
            "account_type": "Tax",
            "root_type": "Liability",
        },
        {
            "account_name": "BDO Checking",
            "parent_account": f"Bank Accounts - {COMPANY_ABBR}",
            "account_type": "Bank",
            "root_type": "Asset",
        },
    ]

    for acct_data in accounts_to_create:
        full_name = f"{acct_data['account_name']} - {COMPANY_ABBR}"
        if not frappe.db.exists("Account", full_name):
            acct = frappe.get_doc({
                "doctype": "Account",
                "company": COMPANY,
                "account_name": acct_data["account_name"],
                "parent_account": acct_data["parent_account"],
                "account_type": acct_data["account_type"],
                "root_type": acct_data["root_type"],
                "is_group": 0,
            })
            acct.insert()
            print(f"  → Created account: {full_name}")
        else:
            print(f"  → Account exists: {full_name}")

    # Set BDO Checking as a Mode of Payment account
    if not frappe.db.exists("Mode of Payment", "Bank Transfer"):
        mop = frappe.get_doc({
            "doctype": "Mode of Payment",
            "mode_of_payment": "Bank Transfer",
            "type": "Bank",
            "accounts": [{
                "company": COMPANY,
                "default_account": f"BDO Checking - {COMPANY_ABBR}"
            }]
        })
        mop.insert()
        print("  → Created Mode of Payment: Bank Transfer")
    else:
        # Ensure account mapping exists
        mop = frappe.get_doc("Mode of Payment", "Bank Transfer")
        has_company = any(a.company == COMPANY for a in mop.accounts)
        if not has_company:
            mop.append("accounts", {
                "company": COMPANY,
                "default_account": f"BDO Checking - {COMPANY_ABBR}"
            })
            mop.save()


# ── 3. Tax Templates ─────────────────────────────────────────
def create_tax_templates():
    print("\n[3/11] Creating tax templates...")

    # --- Sales Tax Templates ---
    sales_templates = [
        {
            "title": "VAT Sales 12%",
            "taxes": [{
                "charge_type": "On Net Total",
                "account_head": f"Output VAT - {COMPANY_ABBR}",
                "rate": 12,
                "description": "VAT 12%",
            }]
        },
        {
            "title": "Zero Rated Sales",
            "taxes": [{
                "charge_type": "On Net Total",
                "account_head": f"Output VAT - {COMPANY_ABBR}",
                "rate": 0,
                "description": "Zero Rated",
            }]
        },
        {
            "title": "Exempt Sales",
            "taxes": [{
                "charge_type": "On Net Total",
                "account_head": f"Output VAT - {COMPANY_ABBR}",
                "rate": 0,
                "description": "VAT Exempt",
            }]
        },
        {
            "title": "Sales to Government",
            "taxes": [{
                "charge_type": "On Net Total",
                "account_head": f"Output VAT - {COMPANY_ABBR}",
                "rate": 12,
                "description": "VAT 12% - Gov't",
            }]
        },
    ]

    for tmpl_data in sales_templates:
        name = f"{tmpl_data['title']} - {COMPANY_ABBR}"
        if not frappe.db.exists("Sales Taxes and Charges Template", name):
            tmpl = frappe.get_doc({
                "doctype": "Sales Taxes and Charges Template",
                "title": tmpl_data["title"],
                "company": COMPANY,
                "taxes": tmpl_data["taxes"],
            })
            tmpl.insert()
            print(f"  → Created Sales Template: {tmpl.name}")

    # --- Purchase Tax Templates ---
    purchase_templates = [
        {
            "title": "Domestic Purchase of Goods - VAT",
            "taxes": [
                {
                    "category": "Total",
                    "add_deduct_tax": "Add",
                    "charge_type": "On Net Total",
                    "account_head": f"Input VAT - {COMPANY_ABBR}",
                    "rate": 12,
                    "description": "Input VAT 12%",
                },
                {
                    "category": "Total",
                    "add_deduct_tax": "Deduct",
                    "charge_type": "On Net Total",
                    "account_head": f"EWT Payable - {COMPANY_ABBR}",
                    "rate": 1,
                    "description": "EWT 1%",
                },
            ]
        },
        {
            "title": "Domestic Purchase of Services - VAT",
            "taxes": [
                {
                    "category": "Total",
                    "add_deduct_tax": "Add",
                    "charge_type": "On Net Total",
                    "account_head": f"Input VAT - {COMPANY_ABBR}",
                    "rate": 12,
                    "description": "Input VAT 12%",
                },
                {
                    "category": "Total",
                    "add_deduct_tax": "Deduct",
                    "charge_type": "On Net Total",
                    "account_head": f"EWT Payable - {COMPANY_ABBR}",
                    "rate": 2,
                    "description": "EWT 2%",
                },
            ]
        },
        {
            "title": "Professional Fees - EWT 5%",
            "taxes": [
                {
                    "category": "Total",
                    "add_deduct_tax": "Add",
                    "charge_type": "On Net Total",
                    "account_head": f"Input VAT - {COMPANY_ABBR}",
                    "rate": 12,
                    "description": "Input VAT 12%",
                },
                {
                    "category": "Total",
                    "add_deduct_tax": "Deduct",
                    "charge_type": "On Net Total",
                    "account_head": f"EWT Payable - {COMPANY_ABBR}",
                    "rate": 5,
                    "description": "EWT 5% Professional",
                },
            ]
        },
        {
            "title": "Capital Goods - VAT",
            "taxes": [
                {
                    "category": "Total",
                    "add_deduct_tax": "Add",
                    "charge_type": "On Net Total",
                    "account_head": f"Input VAT - {COMPANY_ABBR}",
                    "rate": 12,
                    "description": "Input VAT 12%",
                },
            ]
        },
        {
            "title": "Zero Rated Purchase",
            "taxes": [{
                "category": "Total",
                "add_deduct_tax": "Add",
                "charge_type": "On Net Total",
                "account_head": f"Input VAT - {COMPANY_ABBR}",
                "rate": 0,
                "description": "Zero Rated",
            }]
        },
        {
            "title": "Exempt Purchase",
            "taxes": [{
                "category": "Total",
                "add_deduct_tax": "Add",
                "charge_type": "On Net Total",
                "account_head": f"Input VAT - {COMPANY_ABBR}",
                "rate": 0,
                "description": "VAT Exempt",
            }]
        },
    ]

    for tmpl_data in purchase_templates:
        name = f"{tmpl_data['title']} - {COMPANY_ABBR}"
        if not frappe.db.exists("Purchase Taxes and Charges Template", name):
            tmpl = frappe.get_doc({
                "doctype": "Purchase Taxes and Charges Template",
                "title": tmpl_data["title"],
                "company": COMPANY,
                "taxes": tmpl_data["taxes"],
            })
            tmpl.insert()
            print(f"  → Created Purchase Template: {tmpl.name}")


# ── 4. Item Tax Templates ────────────────────────────────────
def create_item_tax_templates():
    print("\n[4/11] Creating item tax templates...")

    item_tax_templates = [
        {
            "title": "VAT 12%",
            "taxes": [{"tax_type": f"Output VAT - {COMPANY_ABBR}", "tax_rate": 12}]
        },
        {
            "title": "Zero Rated",
            "taxes": [{"tax_type": f"Output VAT - {COMPANY_ABBR}", "tax_rate": 0}]
        },
        {
            "title": "VAT Exempt",
            "taxes": [{"tax_type": f"Output VAT - {COMPANY_ABBR}", "tax_rate": 0}]
        },
        {
            "title": "Input VAT 12%",
            "taxes": [{"tax_type": f"Input VAT - {COMPANY_ABBR}", "tax_rate": 12}]
        },
    ]

    for tmpl_data in item_tax_templates:
        name = f"{tmpl_data['title']} - {COMPANY_ABBR}"
        if not frappe.db.exists("Item Tax Template", name):
            tmpl = frappe.get_doc({
                "doctype": "Item Tax Template",
                "title": tmpl_data["title"],
                "company": COMPANY,
                "taxes": tmpl_data["taxes"],
            })
            tmpl.insert()
            print(f"  → Created Item Tax Template: {tmpl.name}")


# ── 5. PH Localization Company Setup ─────────────────────────
def setup_ph_localization():
    print("\n[5/11] Setting up PH Localization Company Setup...")

    if not frappe.db.exists("PH Localization Company Setup", COMPANY):
        doc = frappe.get_doc({
            "doctype": "PH Localization Company Setup",
            "company": COMPANY,
            "registered_name": "ARUGA TECHNOLOGIES INC.",
            "permit_no": "0000-AU-2024-001234",
            "permit_date_issued": "2024-01-15",
            "rdo_code": "049",
            "vat_industry": "Other Service Activities",
            "withholding_agent_category": "Private",
            "fiscal_month_end": "12",
            "authorized_representative_1": "JUAN DELA CRUZ",
            "title_1": "President & CEO",
            "tin_of_signatory_1": "123456789000",
            "authorized_representative_2": "MARIA SANTOS",
            "title_2": "Chief Finance Officer",
            "tin_of_signatory_2": "987654321000",
        })
        doc.insert()
        print(f"  → Created PH Localization setup for {COMPANY}")
    else:
        print(f"  → PH Localization already exists for {COMPANY}")


# ── 6. Tax Declaration Company Setup ─────────────────────────
def setup_tax_declaration():
    print("\n[6/11] Setting up Tax Declaration Company Setup...")

    if not frappe.db.exists("Tax Declaration Company Setup", COMPANY):
        doc = frappe.get_doc({
            "doctype": "Tax Declaration Company Setup",
            "company": COMPANY,
            # Sales templates
            "vat_sales": f"VAT Sales 12% - {COMPANY_ABBR}",
            "sales_to_government": f"Sales to Government - {COMPANY_ABBR}",
            "zero_rated_sales": f"Zero Rated Sales - {COMPANY_ABBR}",
            "exempt_sales": f"Exempt Sales - {COMPANY_ABBR}",
            # Sales item tax templates
            "item_vat_sales": f"VAT 12% - {COMPANY_ABBR}",
            "item_sales_to_government": f"VAT 12% - {COMPANY_ABBR}",
            "item_zero_rated_sales": f"Zero Rated - {COMPANY_ABBR}",
            "item_exempt_sales": f"VAT Exempt - {COMPANY_ABBR}",
            # Purchase templates
            "capital_goods": f"Capital Goods - VAT - {COMPANY_ABBR}",
            "domestic_purchases_of_goods": f"Domestic Purchase of Goods - VAT - {COMPANY_ABBR}",
            "domestic_purchase_of_services": f"Domestic Purchase of Services - VAT - {COMPANY_ABBR}",
            "zero_rated_purchase": f"Zero Rated Purchase - {COMPANY_ABBR}",
            "exempt_purchase": f"Exempt Purchase - {COMPANY_ABBR}",
            # Purchase item tax templates
            "item_capital_goods": f"Input VAT 12% - {COMPANY_ABBR}",
            "item_domestic_purchases_of_goods": f"Input VAT 12% - {COMPANY_ABBR}",
            "item_domestic_purchase_of_services": f"Input VAT 12% - {COMPANY_ABBR}",
        })
        doc.insert()
        print(f"  → Created Tax Declaration setup for {COMPANY}")
    else:
        print(f"  → Tax Declaration already exists for {COMPANY}")


# ── 7. Customers ─────────────────────────────────────────────
def create_customers():
    print("\n[7/11] Creating customers...")

    customers = [
        {
            "customer_name": "ABC Trading Corporation",
            "tax_id": "111-222-333-000",
            "customer_group": "Commercial",
            "territory": "Philippines",
            "address": {
                "address_line1": "456 Ayala Avenue",
                "city": "Makati City",
                "state": "Metro Manila",
                "pincode": "1200",
            },
        },
        {
            "customer_name": "DEF Manufacturing Inc.",
            "tax_id": "222-333-444-000",
            "customer_group": "Commercial",
            "territory": "Philippines",
            "address": {
                "address_line1": "789 EDSA Cor. Shaw Blvd",
                "city": "Mandaluyong City",
                "state": "Metro Manila",
                "pincode": "1550",
            },
        },
        {
            "customer_name": "Government Health Agency",
            "tax_id": "000-999-888-000",
            "customer_group": "Government",
            "territory": "Philippines",
            "address": {
                "address_line1": "DOH Compound, Rizal Avenue",
                "city": "Manila",
                "state": "Metro Manila",
                "pincode": "1003",
            },
        },
        {
            "customer_name": "GHI Export Company",
            "tax_id": "333-444-555-000",
            "customer_group": "Commercial",
            "territory": "Philippines",
            "address": {
                "address_line1": "10 Bonifacio High Street",
                "city": "Taguig City",
                "state": "Metro Manila",
                "pincode": "1634",
            },
        },
    ]

    # Ensure Customer Groups exist
    for grp in ["Commercial", "Government"]:
        if not frappe.db.exists("Customer Group", grp):
            frappe.get_doc({"doctype": "Customer Group", "customer_group_name": grp}).insert()

    for cust_data in customers:
        if not frappe.db.exists("Customer", cust_data["customer_name"]):
            cust = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": cust_data["customer_name"],
                "tax_id": cust_data["tax_id"],
                "customer_group": cust_data["customer_group"],
                "territory": cust_data["territory"],
                "customer_type": "Company",
            })
            cust.insert()

            # Create address
            addr_data = cust_data["address"]
            addr = frappe.get_doc({
                "doctype": "Address",
                "address_title": cust_data["customer_name"],
                "address_type": "Billing",
                "address_line1": addr_data["address_line1"],
                "city": addr_data["city"],
                "state": addr_data.get("state", ""),
                "country": "Philippines",
                "pincode": addr_data.get("pincode", ""),
                "links": [{
                    "link_doctype": "Customer",
                    "link_name": cust.name
                }]
            })
            addr.insert()
            print(f"  → Created customer: {cust.name} (TIN: {cust_data['tax_id']})")
        else:
            print(f"  → Customer exists: {cust_data['customer_name']}")


# ── 8. Suppliers ──────────────────────────────────────────────
def create_suppliers():
    print("\n[8/11] Creating suppliers...")

    suppliers = [
        {
            "supplier_name": "Manila Office Supplies Co.",
            "tax_id": "444-555-666-000",
            "supplier_group": "Local",
            "supplier_type": "Company",
            "address": {
                "address_line1": "100 Quezon Boulevard",
                "city": "Quezon City",
                "state": "Metro Manila",
                "pincode": "1100",
            },
        },
        {
            "supplier_name": "PH Tech Solutions Inc.",
            "tax_id": "555-666-777-000",
            "supplier_group": "Local",
            "supplier_type": "Company",
            "address": {
                "address_line1": "200 Ortigas Center",
                "city": "Pasig City",
                "state": "Metro Manila",
                "pincode": "1600",
            },
        },
        {
            "supplier_name": "CPA Associates",
            "tax_id": "666-777-888-000",
            "supplier_group": "Local",
            "supplier_type": "Company",
            "address": {
                "address_line1": "Suite 501, Pacific Star Bldg",
                "address_line2": "Makati Avenue cor. Gil Puyat Ave",
                "city": "Makati City",
                "state": "Metro Manila",
                "pincode": "1200",
            },
        },
        {
            "supplier_name": "Juan Reyes (Freelancer)",
            "tax_id": "777-888-999-000",
            "supplier_group": "Local",
            "supplier_type": "Individual",
            "address": {
                "address_line1": "Block 5 Lot 10 Greenfields Subd.",
                "city": "San Pedro",
                "state": "Laguna",
                "pincode": "4023",
            },
        },
        {
            "supplier_name": "Global Imports Ltd.",
            "tax_id": "888-999-000-000",
            "supplier_group": "Local",
            "supplier_type": "Company",
            "address": {
                "address_line1": "Port Area, South Harbor",
                "city": "Manila",
                "state": "Metro Manila",
                "pincode": "1018",
            },
        },
    ]

    # Ensure Supplier Group exists
    if not frappe.db.exists("Supplier Group", "Local"):
        frappe.get_doc({"doctype": "Supplier Group", "supplier_group_name": "Local"}).insert()

    for supp_data in suppliers:
        if not frappe.db.exists("Supplier", supp_data["supplier_name"]):
            supp = frappe.get_doc({
                "doctype": "Supplier",
                "supplier_name": supp_data["supplier_name"],
                "tax_id": supp_data["tax_id"],
                "supplier_group": supp_data["supplier_group"],
                "supplier_type": supp_data["supplier_type"],
                "country": "Philippines",
            })
            supp.insert()

            addr_data = supp_data["address"]
            addr = frappe.get_doc({
                "doctype": "Address",
                "address_title": supp_data["supplier_name"],
                "address_type": "Billing",
                "address_line1": addr_data["address_line1"],
                "address_line2": addr_data.get("address_line2", ""),
                "city": addr_data["city"],
                "state": addr_data.get("state", ""),
                "country": "Philippines",
                "pincode": addr_data.get("pincode", ""),
                "links": [{
                    "link_doctype": "Supplier",
                    "link_name": supp.name
                }]
            })
            addr.insert()
            print(f"  → Created supplier: {supp.name} (TIN: {supp_data['tax_id']})")
        else:
            print(f"  → Supplier exists: {supp_data['supplier_name']}")


# ── 9. Items ─────────────────────────────────────────────────
def create_items():
    print("\n[9/11] Creating items...")

    items = [
        # Sales items
        {"item_code": "SVC-001", "item_name": "IT Consulting Services", "item_group": "Services",
         "is_stock_item": 0, "description": "Hourly IT consulting and support services"},
        {"item_code": "SVC-002", "item_name": "Software Development", "item_group": "Services",
         "is_stock_item": 0, "description": "Custom software development services"},
        {"item_code": "SVC-003", "item_name": "Cloud Hosting Services", "item_group": "Services",
         "is_stock_item": 0, "description": "Monthly cloud server hosting"},
        {"item_code": "GOODS-001", "item_name": "Computer Hardware Bundle", "item_group": "Products",
         "is_stock_item": 1, "description": "Desktop computer package"},
        {"item_code": "GOODS-002", "item_name": "Network Equipment", "item_group": "Products",
         "is_stock_item": 1, "description": "Router, switch, cables bundle"},
        # Purchase items
        {"item_code": "PURCH-001", "item_name": "Office Supplies", "item_group": "Raw Material",
         "is_stock_item": 0, "description": "Assorted office supplies"},
        {"item_code": "PURCH-002", "item_name": "Accounting Services", "item_group": "Services",
         "is_stock_item": 0, "description": "Monthly bookkeeping and tax compliance"},
        {"item_code": "PURCH-003", "item_name": "Office Furniture", "item_group": "Products",
         "is_stock_item": 0, "description": "Office desks and chairs"},
        {"item_code": "PURCH-004", "item_name": "Web Design Services", "item_group": "Services",
         "is_stock_item": 0, "description": "Freelance web design"},
        {"item_code": "PURCH-005", "item_name": "Imported Server Parts", "item_group": "Products",
         "is_stock_item": 1, "description": "Server components from overseas"},
    ]

    # Ensure item groups exist
    for grp in ["Services", "Products", "Raw Material"]:
        if not frappe.db.exists("Item Group", grp):
            frappe.get_doc({"doctype": "Item Group", "item_group_name": grp, "parent_item_group": "All Item Groups"}).insert()

    for item_data in items:
        if not frappe.db.exists("Item", item_data["item_code"]):
            item = frappe.get_doc({
                "doctype": "Item",
                "item_code": item_data["item_code"],
                "item_name": item_data["item_name"],
                "item_group": item_data["item_group"],
                "is_stock_item": item_data.get("is_stock_item", 0),
                "description": item_data.get("description", ""),
                "stock_uom": "Nos",
            })
            item.insert()
            print(f"  → Created item: {item.item_code} - {item.item_name}")
        else:
            print(f"  → Item exists: {item_data['item_code']}")


# ── 10. Sales Invoices ────────────────────────────────────────
def create_sales_invoices():
    print("\n[10/11] Creating sales invoices...")

    base_date = add_months(today(), -2)  # 2 months ago for quarterly testing
    quarter_start = getdate(base_date).replace(day=1)

    invoices = [
        {
            "customer": "ABC Trading Corporation",
            "posting_date": str(quarter_start),
            "taxes_and_charges": f"VAT Sales 12% - {COMPANY_ABBR}",
            "items": [
                {"item_code": "SVC-001", "qty": 40, "rate": 2500,
                 "item_tax_template": f"VAT 12% - {COMPANY_ABBR}"},
                {"item_code": "SVC-002", "qty": 1, "rate": 150000,
                 "item_tax_template": f"VAT 12% - {COMPANY_ABBR}"},
            ],
            "description": "VAT Sales - IT Services",
        },
        {
            "customer": "DEF Manufacturing Inc.",
            "posting_date": str(add_days(quarter_start, 15)),
            "taxes_and_charges": f"VAT Sales 12% - {COMPANY_ABBR}",
            "items": [
                {"item_code": "GOODS-001", "qty": 5, "rate": 45000,
                 "item_tax_template": f"VAT 12% - {COMPANY_ABBR}"},
                {"item_code": "GOODS-002", "qty": 3, "rate": 25000,
                 "item_tax_template": f"VAT 12% - {COMPANY_ABBR}"},
            ],
            "description": "VAT Sales - Hardware",
        },
        {
            "customer": "Government Health Agency",
            "posting_date": str(add_days(quarter_start, 20)),
            "taxes_and_charges": f"Sales to Government - {COMPANY_ABBR}",
            "items": [
                {"item_code": "SVC-003", "qty": 12, "rate": 15000,
                 "item_tax_template": f"VAT 12% - {COMPANY_ABBR}"},
            ],
            "description": "Sales to Gov't - Cloud Hosting",
        },
        {
            "customer": "GHI Export Company",
            "posting_date": str(add_days(quarter_start, 30)),
            "taxes_and_charges": f"Zero Rated Sales - {COMPANY_ABBR}",
            "items": [
                {"item_code": "SVC-002", "qty": 1, "rate": 500000,
                 "item_tax_template": f"Zero Rated - {COMPANY_ABBR}"},
            ],
            "description": "Zero Rated - Export Software Dev",
        },
        {
            "customer": "ABC Trading Corporation",
            "posting_date": str(add_days(quarter_start, 45)),
            "taxes_and_charges": f"Exempt Sales - {COMPANY_ABBR}",
            "items": [
                {"item_code": "SVC-001", "qty": 10, "rate": 3000,
                 "item_tax_template": f"VAT Exempt - {COMPANY_ABBR}"},
            ],
            "description": "Exempt Sales - Consulting",
        },
    ]

    for inv_data in invoices:
        # Check if similar invoice already exists
        existing = frappe.db.exists("Sales Invoice", {
            "customer": inv_data["customer"],
            "posting_date": inv_data["posting_date"],
            "docstatus": ["in", [0, 1]],
            "company": COMPANY,
        })
        if existing:
            print(f"  → Sales Invoice exists for {inv_data['customer']} on {inv_data['posting_date']}")
            continue

        items = []
        for item in inv_data["items"]:
            row = {
                "item_code": item["item_code"],
                "qty": item["qty"],
                "rate": item["rate"],
                "income_account": f"Sales - {COMPANY_ABBR}",
            }
            if item.get("item_tax_template"):
                row["item_tax_template"] = item["item_tax_template"]
            items.append(row)

        si = frappe.get_doc({
            "doctype": "Sales Invoice",
            "company": COMPANY,
            "customer": inv_data["customer"],
            "posting_date": inv_data["posting_date"],
            "set_posting_time": 1,
            "due_date": add_days(inv_data["posting_date"], 30),
            "taxes_and_charges": inv_data["taxes_and_charges"],
            "items": items,
            "debit_to": f"Debtors - {COMPANY_ABBR}",
            "currency": CURRENCY,
            "update_stock": 0,
        })
        si.insert()
        si.submit()
        print(f"  → Created & submitted SI: {si.name} ({inv_data['description']}) = ₱{si.grand_total:,.2f}")


# ── 11. Purchase Invoices ─────────────────────────────────────
def create_purchase_invoices():
    print("\n[11/11] Creating purchase invoices...")

    base_date = add_months(today(), -2)
    quarter_start = getdate(base_date).replace(day=1)

    # Get some ATC codes for the taxes
    atc_ewt_goods = "WC010"  # Purchase of goods - 1%
    atc_ewt_services = "WC100"  # Purchase of services - 2%
    atc_professional = "WI010"  # Professional fees - 5%

    # Verify these ATCs exist
    for atc_code in [atc_ewt_goods, atc_ewt_services, atc_professional]:
        if not frappe.db.exists("ATC", atc_code):
            # Find any existing ATC as fallback
            existing_atc = frappe.get_all("ATC", filters={"form_type": "2307"}, limit=1, pluck="name")
            if existing_atc:
                print(f"  ⚠ ATC {atc_code} not found, using {existing_atc[0]} as fallback")

    invoices = [
        {
            "supplier": "Manila Office Supplies Co.",
            "posting_date": str(add_days(quarter_start, 5)),
            "taxes_and_charges": f"Domestic Purchase of Goods - VAT - {COMPANY_ABBR}",
            "items": [
                {"item_code": "PURCH-001", "qty": 1, "rate": 15000},
            ],
            "taxes": [
                {"category": "Total", "add_deduct_tax": "Add", "charge_type": "On Net Total",
                 "account_head": f"Input VAT - {COMPANY_ABBR}", "rate": 12, "description": "Input VAT 12%"},
                {"category": "Total", "add_deduct_tax": "Deduct", "charge_type": "On Net Total",
                 "account_head": f"EWT Payable - {COMPANY_ABBR}", "rate": 1, "description": "EWT 1%"},
            ],
            "atc": atc_ewt_goods,
            "description": "Domestic Goods Purchase with EWT 1%",
        },
        {
            "supplier": "PH Tech Solutions Inc.",
            "posting_date": str(add_days(quarter_start, 12)),
            "taxes_and_charges": f"Domestic Purchase of Services - VAT - {COMPANY_ABBR}",
            "items": [
                {"item_code": "SVC-003", "qty": 6, "rate": 10000},
            ],
            "taxes": [
                {"category": "Total", "add_deduct_tax": "Add", "charge_type": "On Net Total",
                 "account_head": f"Input VAT - {COMPANY_ABBR}", "rate": 12, "description": "Input VAT 12%"},
                {"category": "Total", "add_deduct_tax": "Deduct", "charge_type": "On Net Total",
                 "account_head": f"EWT Payable - {COMPANY_ABBR}", "rate": 2, "description": "EWT 2%"},
            ],
            "atc": atc_ewt_services,
            "description": "Service Purchase with EWT 2%",
        },
        {
            "supplier": "CPA Associates",
            "posting_date": str(add_days(quarter_start, 18)),
            "taxes_and_charges": f"Professional Fees - EWT 5% - {COMPANY_ABBR}",
            "items": [
                {"item_code": "PURCH-002", "qty": 1, "rate": 50000},
            ],
            "taxes": [
                {"category": "Total", "add_deduct_tax": "Add", "charge_type": "On Net Total",
                 "account_head": f"Input VAT - {COMPANY_ABBR}", "rate": 12, "description": "Input VAT 12%"},
                {"category": "Total", "add_deduct_tax": "Deduct", "charge_type": "On Net Total",
                 "account_head": f"EWT Payable - {COMPANY_ABBR}", "rate": 5, "description": "EWT 5% Professional"},
            ],
            "atc": atc_professional,
            "description": "Professional Fees with EWT 5%",
        },
        {
            "supplier": "Juan Reyes (Freelancer)",
            "posting_date": str(add_days(quarter_start, 25)),
            "taxes_and_charges": f"Professional Fees - EWT 5% - {COMPANY_ABBR}",
            "items": [
                {"item_code": "PURCH-004", "qty": 1, "rate": 35000},
            ],
            "taxes": [
                {"category": "Total", "add_deduct_tax": "Add", "charge_type": "On Net Total",
                 "account_head": f"Input VAT - {COMPANY_ABBR}", "rate": 12, "description": "Input VAT 12%"},
                {"category": "Total", "add_deduct_tax": "Deduct", "charge_type": "On Net Total",
                 "account_head": f"EWT Payable - {COMPANY_ABBR}", "rate": 5, "description": "EWT 5% Professional"},
            ],
            "atc": atc_professional,
            "description": "Freelancer Fees with EWT 5%",
        },
        {
            "supplier": "Global Imports Ltd.",
            "posting_date": str(add_days(quarter_start, 35)),
            "taxes_and_charges": f"Capital Goods - VAT - {COMPANY_ABBR}",
            "items": [
                {"item_code": "PURCH-003", "qty": 10, "rate": 12000},
            ],
            "taxes": [
                {"category": "Total", "add_deduct_tax": "Add", "charge_type": "On Net Total",
                 "account_head": f"Input VAT - {COMPANY_ABBR}", "rate": 12, "description": "Input VAT 12%"},
            ],
            "atc": None,
            "description": "Capital Goods - Equipment",
        },
        {
            "supplier": "Manila Office Supplies Co.",
            "posting_date": str(add_days(quarter_start, 40)),
            "taxes_and_charges": f"Exempt Purchase - {COMPANY_ABBR}",
            "items": [
                {"item_code": "PURCH-001", "qty": 1, "rate": 5000},
            ],
            "taxes": [
                {"category": "Total", "add_deduct_tax": "Add", "charge_type": "On Net Total",
                 "account_head": f"Input VAT - {COMPANY_ABBR}", "rate": 0, "description": "VAT Exempt"},
            ],
            "atc": None,
            "description": "Exempt Purchase",
        },
    ]

    for inv_data in invoices:
        existing = frappe.db.exists("Purchase Invoice", {
            "supplier": inv_data["supplier"],
            "posting_date": inv_data["posting_date"],
            "docstatus": ["in", [0, 1]],
            "company": COMPANY,
        })
        if existing:
            print(f"  → Purchase Invoice exists for {inv_data['supplier']} on {inv_data['posting_date']}")
            continue

        items = []
        for item in inv_data["items"]:
            items.append({
                "item_code": item["item_code"],
                "qty": item["qty"],
                "rate": item["rate"],
                "expense_account": f"Cost of Goods Sold - {COMPANY_ABBR}",
            })

        pi = frappe.get_doc({
            "doctype": "Purchase Invoice",
            "company": COMPANY,
            "supplier": inv_data["supplier"],
            "posting_date": inv_data["posting_date"],
            "set_posting_time": 1,
            "bill_date": inv_data["posting_date"],
            "due_date": add_days(inv_data["posting_date"], 30),
            "taxes_and_charges": inv_data["taxes_and_charges"],
            "items": items,
            "taxes": inv_data.get("taxes", []),
            "credit_to": f"Creditors - {COMPANY_ABBR}",
            "currency": CURRENCY,
            "update_stock": 0,
        })
        pi.insert()

        # Set ATC on tax rows if applicable
        if inv_data.get("atc") and frappe.db.exists("ATC", inv_data["atc"]):
            for tax_row in pi.taxes:
                if "EWT" in (tax_row.description or "") or "Withholding" in (tax_row.description or ""):
                    frappe.db.set_value("Purchase Taxes and Charges", tax_row.name, "atc", inv_data["atc"])

        pi.submit()
        print(f"  → Created & submitted PI: {pi.name} ({inv_data['description']}) = ₱{pi.grand_total:,.2f}")


# ── 12. Payment Entries ───────────────────────────────────────
def create_payment_entries():
    print("\n[12/12] Creating payment entries...")

    # Find submitted sales invoices to pay
    unpaid_si = frappe.get_all("Sales Invoice", filters={
        "company": COMPANY,
        "docstatus": 1,
        "outstanding_amount": [">", 0],
    }, fields=["name", "customer", "grand_total", "outstanding_amount"], limit=2)

    for si_data in unpaid_si:
        pe = frappe.get_doc({
            "doctype": "Payment Entry",
            "company": COMPANY,
            "payment_type": "Receive",
            "party_type": "Customer",
            "party": si_data["customer"],
            "paid_from": f"Debtors - {COMPANY_ABBR}",
            "paid_to": f"BDO Checking - {COMPANY_ABBR}",
            "paid_amount": si_data["outstanding_amount"],
            "received_amount": si_data["outstanding_amount"],
            "reference_no": f"OR-{si_data['name']}",
            "reference_date": today(),
            "mode_of_payment": "Bank Transfer",
            "references": [{
                "reference_doctype": "Sales Invoice",
                "reference_name": si_data["name"],
                "allocated_amount": si_data["outstanding_amount"],
            }],
        })
        pe.insert()
        pe.submit()
        print(f"  → Created Payment (Receive): {pe.name} for SI {si_data['name']} = ₱{pe.paid_amount:,.2f}")

    # Find submitted purchase invoices to pay
    unpaid_pi = frappe.get_all("Purchase Invoice", filters={
        "company": COMPANY,
        "docstatus": 1,
        "outstanding_amount": [">", 0],
    }, fields=["name", "supplier", "grand_total", "outstanding_amount"], limit=2)

    for pi_data in unpaid_pi:
        pe = frappe.get_doc({
            "doctype": "Payment Entry",
            "company": COMPANY,
            "payment_type": "Pay",
            "party_type": "Supplier",
            "party": pi_data["supplier"],
            "paid_from": f"BDO Checking - {COMPANY_ABBR}",
            "paid_to": f"Creditors - {COMPANY_ABBR}",
            "paid_amount": pi_data["outstanding_amount"],
            "received_amount": pi_data["outstanding_amount"],
            "reference_no": f"CHK-{pi_data['name']}",
            "reference_date": today(),
            "mode_of_payment": "Bank Transfer",
            "references": [{
                "reference_doctype": "Purchase Invoice",
                "reference_name": pi_data["name"],
                "allocated_amount": pi_data["outstanding_amount"],
            }],
        })
        pe.insert()
        pe.submit()
        print(f"  → Created Payment (Pay): {pe.name} for PI {pi_data['name']} = ₱{pe.paid_amount:,.2f}")


if __name__ == "__main__":
    setup()
