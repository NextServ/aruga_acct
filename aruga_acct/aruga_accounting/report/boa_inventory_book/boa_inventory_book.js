// Copyright (c) 2016, SERVIO Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

{% include 'aruga_acct/public/js/utils.js' %}

frappe.query_reports["BOA Inventory Book"] = {
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
            fieldname: "as_at_date",
            label: __("As At Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1
        },
        // {
        //     fieldname:"as_at_time",
        //     label: __("As At Time"),
        //     fieldtype: "Time",
        //     default: '23:59:59',
        //     reqd: 1
        // },
    ]
};
