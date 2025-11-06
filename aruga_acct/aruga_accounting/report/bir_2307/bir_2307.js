// Copyright (c) 2016, SERVIO Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

{% include 'aruga_acct/public/js/utils.js' %}

frappe.query_reports["BIR 2307"] = {
    "filters": [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd: 1
        },
        {
            fieldname: "supplier",
            label: __("Supplier"),
            fieldtype: "Link",
            options: "Supplier",
            reqd: 0
        },
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee",
            reqd: 0
        },
        {
            fieldname: "doctype",
            label: __("Document Type"),
            fieldtype: "Select",
            options: ["Purchase Invoice", "Payment Entry", "Expense Claim"],
            reqd: 0,
            on_change: function () {
                let filter_based_on = frappe.query_report.get_filter_value('doctype');
                frappe.query_report.toggle_filter_display('purchase_invoice', filter_based_on != 'Purchase Invoice');
                frappe.query_report.toggle_filter_display('payment_entry', filter_based_on != 'Payment Entry');
                frappe.query_report.toggle_filter_display('expense_claim', filter_based_on != 'Expense Claim');

                frappe.query_report.toggle_filter_display('employee', filter_based_on != 'Expense Claim');
                frappe.query_report.toggle_filter_display('supplier', filter_based_on == 'Expense Claim');

                if (filter_based_on == 'Purchase Invoice') {
                    frappe.query_report.set_filter_value("payment_entry", "");
                    frappe.query_report.set_filter_value("expense_claim", "");
                    frappe.query_report.set_filter_value("employee", "");
                }

                if (filter_based_on == 'Payment Entry') {
                    frappe.query_report.set_filter_value("purchase_invoice", "");
                    frappe.query_report.set_filter_value("expense_claim", "");
                    frappe.query_report.set_filter_value("employee", "");
                }

                if (filter_based_on == 'Expense Claim') {
                    frappe.query_report.set_filter_value("purchase_invoice", "");
                    frappe.query_report.set_filter_value("payment_entry", "");
                    frappe.query_report.set_filter_value("supplier", "");
                }
            }
        },
        {
            fieldname: "purchase_invoice",
            label: __("Purchase Invoice"),
            fieldtype: "Link",
            default: "",
            options: "Purchase Invoice",
            hidden: 1,
            get_query: () => {
                var supplier = frappe.query_report.get_filter_value('supplier');
                return {
                    filters: {
                        'supplier': supplier,
                        'docstatus': 1
                    }
                }
            },
            reqd: 0
        },
        {
            fieldname: "payment_entry",
            label: __("Payment Entry"),
            fieldtype: "Link",
            default: "",
            options: "Payment Entry",
            hidden: 1,
            get_query: () => {
                var supplier = frappe.query_report.get_filter_value('supplier');
                return {
                    filters: {
                        'party_type': 'Supplier',
                        'party': supplier,
                        'payment_type': 'Pay',
                        'docstatus': 1
                    }
                }
            },
            reqd: 0
        },
        {
            fieldname: "expense_claim",
            label: __("Expense Claim"),
            fieldtype: "Link",
            default: "",
            options: "Expense Claim",
            hidden: 1,
            get_query: () => {
                var employee = frappe.query_report.get_filter_value('employee');
                return {
                    filters: {
                        'employee': employee,
                        'docstatus': 1
                    }
                }
            },
            reqd: 0
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: moment(frappe.datetime.get_today()).startOf('quarter'),
            reqd: 1

        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: moment(frappe.datetime.get_today()).endOf('quarter'),
            reqd: 1
        }
    ],
    onload: function (report) {
        report.page.add_inner_button(__("Print BIR 2307"), function () {
            let filter_values = {
                'company': frappe.query_report.get_filter_value('company'),
                'supplier': frappe.query_report.get_filter_value('supplier'),
                'employee': frappe.query_report.get_filter_value('employee'),
                'doctype': frappe.query_report.get_filter_value('doctype'),
                'purchase_invoice': frappe.query_report.get_filter_value('purchase_invoice') ? frappe.query_report.get_filter_value('purchase_invoice') : "",
                'payment_entry': frappe.query_report.get_filter_value('payment_entry') ? frappe.query_report.get_filter_value('payment_entry') : "",
                'expense_claim': frappe.query_report.get_filter_value('expense_claim') ? frappe.query_report.get_filter_value('expense_claim') : "",
                'from_date': frappe.query_report.get_filter_value('from_date'),
                'to_date': frappe.query_report.get_filter_value('to_date'),
            };
            let u = new URLSearchParams(filter_values).toString();

            var bir_form_url = frappe.urllib.get_full_url('/api/method/aruga_acct.aruga_accounting.bir_forms.bir_2307?' + u + '&response_type=pdf')
            let bir_form = window.open(bir_form_url);
        });

        let filter_based_on = frappe.query_report.get_filter_value('doctype');
        frappe.query_report.toggle_filter_display('purchase_invoice', filter_based_on != 'Purchase Invoice');
        frappe.query_report.toggle_filter_display('payment_entry', filter_based_on != 'Payment Entry');
        frappe.query_report.toggle_filter_display('expense_claim', filter_based_on != 'Expense Claim');
    },
};