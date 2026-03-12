// Copyright (c) 2016, SERVIO Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

{% include 'aruga_acct/public/js/utils.js' %}

frappe.query_reports["BIR 2550M"] = {
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
        report.page.add_inner_button(__("Print BIR 2550M"), function () {
            if (!frappe.query_report.data || frappe.query_report.data.length === 0) {
                frappe.msgprint({
                    title: __('No Data'),
                    indicator: 'orange',
                    message: __('No data available for the selected filters. Please adjust your filters and try again.')
                });
                return;
            }

            let d = new frappe.ui.Dialog({
                title: 'Enter details',
                fields: [
                    {
                        label: 'Less: Allowable Input Tax',
                        fieldname: 'less_allowable_input_tax_section',
                        fieldtype: 'Section Break',
                    },
                    {
                        label: 'Input Tax Carried Over from Previous Period',
                        fieldname: 'input_tax_carried_over_from_previous_period',
                        fieldtype: 'Currency',
                        default: 0
                    },
                    {
                        label: 'Input Tax Deferred on Capital Goods Exceeding 1M from Previous Period',
                        fieldname: 'input_tax_deferred_on_capital_goods_exceeding_1m_from_previous_period',
                        fieldtype: 'Currency',
                        default: 0
                    },
                    {
                        label: 'Transitional Input Tax',
                        fieldname: 'transitional_input_tax',
                        fieldtype: 'Currency',
                        default: 0
                    },
                    {
                        label: '',
                        fieldname: 'less_allowable_input_tax_column_break',
                        fieldtype: 'Column Break'
                    },
                    {
                        label: 'Presumptive Input Tax',
                        fieldname: 'presumptive_input_tax',
                        fieldtype: 'Currency',
                        default: 0
                    },
                    {
                        label: 'Others',
                        fieldname: 'allowable_input_tax_others',
                        fieldtype: 'Currency',
                        default: 0
                    },
                    {
                        label: 'Less: Deductions from Input Tax',
                        fieldname: 'less_deductions_from_input_tax_section',
                        fieldtype: 'Section Break',
                    },
                    {
                        label: 'Input Tax on Purchases of Capital Goods Deferred for the Succeeding Period Exceeding 1M',
                        fieldname: 'input_tax_deferred_on_capital_goods_from_previous_period_1m_up',
                        fieldtype: 'Currency',
                        default: 0
                    },
                    {
                        label: 'Input Tax on Directly Attributable to Exempt Sales',
                        fieldname: 'input_tax_directly_attributable_to_exempt_sales',
                        fieldtype: 'Currency',
                        default: 0
                    },
                    {
                        label: '',
                        fieldname: 'less_deductions_from_input_tax_column_break',
                        fieldtype: 'Column Break'
                    },
                    {
                        label: 'VAT Refund/TCC claimed',
                        fieldname: 'vat_refund_tcc_claimed',
                        fieldtype: 'Currency',
                        default: 0
                    },
                    {
                        label: 'Others',
                        fieldname: 'less_deductions_from_input_tax_others',
                        fieldtype: 'Currency',
                        default: 0
                    },
                    {
                        label: 'Penalties',
                        fieldname: 'penalties_section',
                        fieldtype: 'Section Break',
                    },
                    {
                        label: 'Surcharge',
                        fieldname: 'surcharge',
                        fieldtype: 'Currency',
                        default: 0
                    },
                    {
                        label: '',
                        fieldname: 'penalties_column_break1',
                        fieldtype: 'Column Break'
                    },
                    {
                        label: 'Interest',
                        fieldname: 'interest',
                        fieldtype: 'Currency',
                        default: 0
                    },
                    {
                        label: '',
                        fieldname: 'penalties_column_break2',
                        fieldtype: 'Column Break'
                    },
                    {
                        label: 'Compromise',
                        fieldname: 'compromise',
                        fieldtype: 'Currency',
                        default: 0
                    },
                ],

                primary_action_label: 'Submit',

                primary_action(values) {
                    d.hide();

                    let filters = {
                        'company': frappe.query_report.get_filter_value('company'),
                        'year': frappe.query_report.get_filter_value('year'),
                        'month': frappe.query_report.get_filter_value('month'),
                    };
                    let context = Object.assign({}, filters, values);
                    let u = new URLSearchParams(context).toString();

                    var bir_form_url = frappe.urllib.get_full_url('/api/method/aruga_acct.aruga_accounting.bir_forms.bir_2550m?' + u + '&response_type=pdf');
                    let bir_form = window.open(bir_form_url);
                }
            });

            d.show();
        });
    }
};