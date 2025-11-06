// Copyright (c) 2016, SERVIO Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

{% include 'aruga_acct/public/js/utils.js' %}

frappe.query_reports["BOA Cash Receipts Journal"] = {
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
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_days(frappe.datetime.add_months(frappe.datetime.get_today(), -12), 1),
            reqd: 1,
            on_change: function () {
                frappe.query_report.set_filter_value("to_date", frappe.datetime.add_days(frappe.datetime.add_months(frappe.query_report.get_filter_value('from_date'), 12), -1));
                frappe.query_report.refresh();
            }
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1
        },
        {
            fieldname: "include_cash_and_bank_journal_entries",
            label: __("Include Cash and Bank Journal Entries"),
            fieldtype: "Check",
            default: 0
        }
    ],

    "formatter": function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        let subtotal_fields = ['account_name', 'debit', 'credit'];
        if (data && data['is_subtotal_row'] == 1 && subtotal_fields.includes(column.fieldname)) {
            value = "<div style='font-weight: bold;'>" + value + "</div>";
        }

        return value;
    },
};