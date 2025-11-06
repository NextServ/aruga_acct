// Copyright (c) 2016, SERVIO Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

{% include 'aruga_acct/public/js/utils.js' %}

frappe.query_reports["RELIEF Summary List of Purchases"] = {
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
    ],
    "onload": function (report) {
        report.page.remove_inner_button(__("Set Chart"));
        report.page.add_inner_button(__("Generate Data File (.DAT)"), function () {
            let total_input_tax = 0;
            if (frappe.query_report.data.length > 0) {
                total_input_tax = flt(frappe.query_report.data[frappe.query_report.data.length - 1]['input_tax']);
            }
            console.log("total_input_tax: " + total_input_tax);

            let d = new frappe.ui.Dialog({
                title: 'Enter details',
                fields: [
                    {
                        label: 'Non-Creditable',
                        fieldname: 'non_creditable',
                        fieldtype: 'Currency',
                        default: 0
                    },
                ],

                primary_action_label: 'Submit',

                primary_action(values) {
                    d.hide();
                    console.log("values['non_creditable']: " + values['non_creditable']);
                    let non_creditable = flt(values['non_creditable']);

                    if (non_creditable > total_input_tax) {
                        frappe.throw(`Non Creditable should not be greater than the Total Input Tax of ${total_input_tax}.`);
                        return;
                    }

                    let filters = {
                        'company': frappe.query_report.get_filter_value('company'),
                        'year': frappe.query_report.get_filter_value('year'),
                        'month': frappe.query_report.get_filter_value('month'),
                    };
                    let context = Object.assign({}, filters, values);
                    let u = new URLSearchParams(context).toString();

                    var sls_url = frappe.urllib.get_full_url('/api/method/aruga_acct.aruga_accounting.report.relief_summary_list_of_purchases.relief_summary_list_of_purchases.generate_slp_data_file?' + u + '&response_type=download');
                    let sls = window.open(sls_url);
                }
            });

            d.show();
        });
    }
};
