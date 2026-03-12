// Copyright (c) 2016, SERVIO Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

{% include 'aruga_acct/public/js/utils.js' %}

frappe.query_reports["BIR 0619-E"] = {
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
            fieldname: "due_date",
            label: __("Due Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1
        },
        {
            fieldname: "amended_form",
            label: __("Amended Form?"),
            fieldtype: "Check"
        },
        {
            fieldname: "any_taxes_withheld",
            label: __("Any Taxes Withheld?"),
            fieldtype: "Check"
        }
    ],
    "onload": function (report) {
        report.page.add_inner_button(__("Print BIR 0619-E"), function () {
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
                        label: 'Remittances',
                        fieldname: 'remittances_section',
                        fieldtype: 'Section Break'
                    },
                    {
                        label: 'Amount of Remittance',
                        fieldname: 'amount_of_remittance',
                        fieldtype: 'Currency',
                        options: 'Company:company:default_currency'
                    },
                    {
                        label: '',
                        fieldname: 'remittances_section_column_break',
                        fieldtype: 'Column Break'
                    },
                    {
                        label: 'Less: Amount Remitted',
                        fieldname: 'amount_remitted',
                        fieldtype: 'Currency',
                        options: 'Company:company:default_currency'
                    },
                    {
                        label: 'Penalties',
                        fieldname: 'penalties_section',
                        fieldtype: 'Section Break'
                    },
                    {
                        label: 'Surcharge',
                        fieldname: 'surcharge',
                        fieldtype: 'Currency',
                        options: 'Company:company:default_currency'
                    },
                    {
                        label: 'Interest',
                        fieldname: 'interest',
                        fieldtype: 'Currency',
                        options: 'Company:company:default_currency'
                    },
                    {
                        label: '',
                        fieldname: 'penalties_section_column_break',
                        fieldtype: 'Column Break'
                    },
                    {
                        label: 'Compromise',
                        fieldname: 'compromise',
                        fieldtype: 'Currency',
                        options: 'Company:company:default_currency'
                    },
                    /* cash */
                    {
                        label: 'Cash/Bank Debit Memo',
                        fieldname: 'cash_section',
                        fieldtype: 'Section Break'
                    },
                    {
                        label: 'Bank/Agency',
                        fieldname: 'cash_drawee_bank',
                        fieldtype: 'Data',
                        length: 5
                    },
                    {
                        label: '',
                        fieldname: 'cash_section_column_break_1',
                        fieldtype: 'Column Break'
                    },
                    {
                        label: 'Number',
                        fieldname: 'cash_number',
                        fieldtype: 'Data',
                        length: 6
                    },
                    {
                        label: '',
                        fieldname: 'cash_section_column_break_2',
                        fieldtype: 'Column Break'
                    },
                    {
                        label: 'Date',
                        fieldname: 'cash_date',
                        fieldtype: 'Date'
                    },
                    {
                        label: '',
                        fieldname: 'cash_section_column_break_3',
                        fieldtype: 'Column Break'
                    },
                    {
                        label: 'Amount',
                        fieldname: 'cash_amount',
                        fieldtype: 'Currency',
                        options: 'Company:company:default_currency'
                    },
                    /* check */
                    {
                        label: 'Check',
                        fieldname: 'check_section',
                        fieldtype: 'Section Break'
                    },
                    {
                        label: 'Bank/Agency',
                        fieldname: 'check_drawee_bank',
                        fieldtype: 'Data',
                        length: 5
                    },
                    {
                        label: '',
                        fieldname: 'check_section_column_break_1',
                        fieldtype: 'Column Break'
                    },
                    {
                        label: 'Number',
                        fieldname: 'check_number',
                        fieldtype: 'Data',
                        length: 6
                    },
                    {
                        label: '',
                        fieldname: 'check_section_column_break_2',
                        fieldtype: 'Column Break'
                    },
                    {
                        label: 'Date',
                        fieldname: 'check_date',
                        fieldtype: 'Date'
                    },
                    {
                        label: '',
                        fieldname: 'check_section_column_break_3',
                        fieldtype: 'Column Break'
                    },
                    {
                        label: 'Amount',
                        fieldname: 'check_amount',
                        fieldtype: 'Currency',
                        options: 'Company:company:default_currency'
                    },
                    /* tax debit memo */
                    {
                        label: 'Tax Debit Memo',
                        fieldname: 'tax_debit_memo_section',
                        fieldtype: 'Section Break'
                    },
                    {
                        label: 'Number',
                        fieldname: 'tax_debit_memo_number',
                        fieldtype: 'Data',
                        length: 6
                    },
                    {
                        label: '',
                        fieldname: 'tax_debit_memo_section_column_break_1',
                        fieldtype: 'Column Break'
                    },
                    {
                        label: 'Date',
                        fieldname: 'tax_debit_memo_date',
                        fieldtype: 'Date'
                    },
                    {
                        label: '',
                        fieldname: 'tax_debit_memo_section_column_break_2',
                        fieldtype: 'Column Break'
                    },
                    {
                        label: 'Amount',
                        fieldname: 'tax_debit_memo_amount',
                        fieldtype: 'Currency',
                        options: 'Company:company:default_currency'
                    },
                    /* others */
                    {
                        label: 'Others',
                        fieldname: 'others_section',
                        fieldtype: 'Section Break'
                    },
                    {
                        label: 'Particular',
                        fieldname: 'others_name',
                        fieldtype: 'Data',
                        length: 7
                    },
                    {
                        label: '',
                        fieldname: 'others_section_column_break_0',
                        fieldtype: 'Column Break'
                    },
                    {
                        label: 'Bank/Agency',
                        fieldname: 'others_drawee_bank',
                        fieldtype: 'Data',
                        length: 5
                    },
                    {
                        label: '',
                        fieldname: 'others_section_column_break_1',
                        fieldtype: 'Column Break'
                    },
                    {
                        label: 'Number',
                        fieldname: 'others_number',
                        fieldtype: 'Data',
                        length: 6
                    },
                    {
                        label: '',
                        fieldname: 'others_section_column_break_2',
                        fieldtype: 'Column Break'
                    },
                    {
                        label: 'Date',
                        fieldname: 'others_date',
                        fieldtype: 'Date'
                    },
                    {
                        label: '',
                        fieldname: 'others_section_column_break_3',
                        fieldtype: 'Column Break'
                    },
                    {
                        label: 'Amount',
                        fieldname: 'others_amount',
                        fieldtype: 'Currency',
                        options: 'Company:company:default_currency'
                    },
                ],
                primary_action_label: 'Submit',
                primary_action(values) {
                    console.log(values);
                    d.hide();

                    let filters = {
                        'company': frappe.query_report.get_filter_value('company'),
                        'year': frappe.query_report.get_filter_value('year'),
                        'month': frappe.query_report.get_filter_value('month'),
                        'due_date': frappe.query_report.get_filter_value('due_date'),
                        'amended_form': frappe.query_report.get_filter_value('amended_form'),
                        'any_taxes_withheld': frappe.query_report.get_filter_value('any_taxes_withheld'),
                    };
                    let context = Object.assign({}, filters, values);
                    let u = new URLSearchParams(context).toString();

                    var bir_form_url = frappe.urllib.get_full_url('/api/method/aruga_acct.aruga_accounting.bir_forms.bir_0619_e?' + u + '&response_type=pdf');
                    let bir_form = window.open(bir_form_url);
                }
            });

            d.show();
        });
    }
};