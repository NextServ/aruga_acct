// Copyright (c) 2016, SERVIO Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

{% include 'aruga_acct/public/js/utils.js' %}

frappe.query_reports["VAT Purchase Invoice Report"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "vat_ewt_category",
            "label": __("VAT/EWT Category"),
            "fieldtype": "Select",
            "options": ["", "WITH VAT AND WITH EWT", "WITHOUT VAT WITH EWT", "WITH VAT WITHOUT EWT", "WITHOUT VAT WITHOUT EWT"],
            "default": ""
        },
        {
            "fieldname": "status",
            "label": __("Status"),
            "fieldtype": "Select",
            "options": ["", "Pending", "Approved", "Cancelled"],
            "default": ""
        },
        {
            "fieldname": "exclude_debit_notes",
            "label": __("Exclude Credit Note"),
            "fieldtype": "Check",
            "default": 1
        },
    ]
}