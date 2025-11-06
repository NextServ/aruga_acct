// Copyright (c) 2016, SERVIO Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

{% include 'aruga_acct/public/js/utils.js' %}

frappe.query_reports["BIR 1601-EQ"] = {
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
            "fieldname": "year",
            "label": __("Year"),
            "fieldtype": "Select",
            "options": get_years(),
            "reqd": 1
        },
        {
            "fieldname": "quarter",
            "label": __("Quarter"),
            "fieldtype": "Select",
            "options": [1, 2, 3, 4],
            "reqd": 1
        }
    ],
    "onload": function (report) {
        report.page.add_inner_button(__("Print BIR 1601-EQ"), function () {
            let filter_values = {
                'company': frappe.query_report.get_filter_value('company'),
                'year': frappe.query_report.get_filter_value('year'),
                'quarter': frappe.query_report.get_filter_value('quarter'),
            };
            let u = new URLSearchParams(filter_values).toString();

            var bir_form_url = frappe.urllib.get_full_url('/api/method/aruga_acct.aruga_accounting.bir_forms.bir_1601_eq?' + u + '&response_type=pdf');
            let bir_form = window.open(bir_form_url);
        });

        report.page.add_inner_button(__("Download QAP"), function () {
            let filter_values = {
                'company': frappe.query_report.get_filter_value('company'),
                'year': frappe.query_report.get_filter_value('year'),
                'quarter': frappe.query_report.get_filter_value('quarter'),
            };
            let u = new URLSearchParams(filter_values).toString();

            var bir_form_url = frappe.urllib.get_full_url('/api/method/aruga_acct.aruga_accounting.bir_forms.bir_1601_eq_qap?' + u + '&response_type=download');
            let bir_form = window.open(bir_form_url);
        });
    },
    "formatter": function (value, row, column, data) {
        // Bold only the "Total" label in the atc column
        if (column.fieldname === "atc" && data.atc === "Total") {
            return `<span style="font-weight: 900;">${value}</span>`;
        }
        // Handle empty or undefined values in tax_rate, base_tax_base, tax_still_due, and total_amount_still_due
        if ((column.fieldname === "tax_rate" ||
            column.fieldname === "base_tax_base" ||
            column.fieldname === "tax_still_due" ||
            column.fieldname === "total_amount_still_due") &&
            (value === null || value === "" || value === undefined)) {
            return "";  // Display dash for null/empty/undefined values
        }
        // Format tax_rate with percent sign and right-align
        if (column.fieldname === "tax_rate" && value !== null && value !== "" && value !== undefined) {
            return `<span style="display: block; text-align: right;">${parseInt(value)}%</span>`;
        }
        return value;
    }
};