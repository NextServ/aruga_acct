/* Copyright (c) 2013, SERVIO Technologies and contributors
 * For license information, please see license.txt
 */

/* eslint-disable */

frappe.query_reports["EWT Report"] = {
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
            "default": frappe.datetime.get_today(),
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
            "fieldname": "exclude_credit_notes",
            "label": "Exclude Debit Notes",
            "fieldtype": "Check",
            "default": 1
        }
    ]
};