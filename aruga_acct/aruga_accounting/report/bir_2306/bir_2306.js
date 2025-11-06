// Copyright (c) 2016, SERVIO Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

{% include 'aruga_acct/public/js/utils.js' %}

frappe.query_reports["BIR 2306"] = {
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
            reqd: 1
        },
        {
            fieldname: "doctype",
            label: __("Document Type"),
            fieldtype: "Select",
            options: ["Purchase Invoice", "Payment Entry"],
            reqd: 0,
            on_change: function () {
                let filter_based_on = frappe.query_report.get_filter_value('doctype');
                frappe.query_report.toggle_filter_display('purchase_invoice', filter_based_on != 'Purchase Invoice');
                frappe.query_report.toggle_filter_display('payment_entry', filter_based_on != 'Payment Entry');

                if (filter_based_on == 'Purchase Invoice') {
                    frappe.query_report.set_filter_value("payment_entry", "");
                }

                if (filter_based_on == 'Payment Entry') {
                    frappe.query_report.set_filter_value("purchase_invoice", "");
                }
            }
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
        report.page.add_inner_button(__("Print BIR 2306"), function () {
            let filter_values = {
                'company': frappe.query_report.get_filter_value('company'),
                'supplier': frappe.query_report.get_filter_value('supplier'),
                'doctype': frappe.query_report.get_filter_value('doctype'),
                'purchase_invoice': frappe.query_report.get_filter_value('purchase_invoice') ? frappe.query_report.get_filter_value('purchase_invoice') : "",
                'payment_entry': frappe.query_report.get_filter_value('payment_entry') ? frappe.query_report.get_filter_value('payment_entry') : "",
                'from_date': frappe.query_report.get_filter_value('from_date'),
                'to_date': frappe.query_report.get_filter_value('to_date'),
            };
            let u = new URLSearchParams(filter_values).toString();

            var bir_form_url = frappe.urllib.get_full_url('/api/method/aruga_acct.aruga_accounting.report.bir_2306.bir_2306.bir_2306?' + u + '&response_type=pdf')
            let bir_form = window.open(bir_form_url);
        });

        let filter_based_on = frappe.query_report.get_filter_value('doctype');
        frappe.query_report.toggle_filter_display('purchase_invoice', filter_based_on != 'Purchase Invoice');
        frappe.query_report.toggle_filter_display('payment_entry', filter_based_on != 'Payment Entry');
    },
};