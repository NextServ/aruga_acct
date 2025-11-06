// Copyright (c) 2016, SERVIO Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

{% include 'aruga_acct/public/js/utils.js' %}

frappe.query_reports["Summary Alphalist of Withholding Taxes"] = {
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
            "default": moment(frappe.datetime.get_today()).year(),
            "reqd": 1
        },
        {
            "fieldname": "month",
            "label": __("Month"),
            "fieldtype": "Select",
            "options": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            "default": moment(frappe.datetime.get_today()).month(),
            "reqd": 1
        },
        {
            label: 'SAWT Form',
            fieldname: 'sawt_form',
            fieldtype: 'Select',
            options: ['1700', '1701', '1701Q', '1702', '1702Q', '2550M', '2550Q', '2551M', '2553'],
            default: '1700'
        },
    ],
    "onload": function (report) {
        report.page.remove_inner_button(__("Set Chart"));
        report.page.add_inner_button(__("Generate Data File (.DAT)"), function () {
            let filters = {
                'company': frappe.query_report.get_filter_value('company'),
                'year': frappe.query_report.get_filter_value('year'),
                'month': frappe.query_report.get_filter_value('month'),
                'sawt_form': frappe.query_report.get_filter_value('sawt_form'),
                // 'amended_form': frappe.query_report.get_filter_value('amended_form'),
            };
            let u = new URLSearchParams(filters).toString();

            var sawt_data_url = frappe.urllib.get_full_url('/api/method/aruga_acct.aruga_accounting.report.summary_alphalist_of_withholding_taxes.summary_alphalist_of_withholding_taxes.generate_sawt_data_file?' + u + '&response_type=download');
            let sawt_data = window.open(sawt_data_url);
        });
    }
};