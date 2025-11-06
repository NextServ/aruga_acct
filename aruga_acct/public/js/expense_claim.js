frappe.ui.form.on('Expense Claim', {
    refresh: function(frm) {
        if( frm.doc.docstatus == 1) {
            // frm.add_custom_button(__('BIR 2306'), function() {
            //     frappe.route_options = {
            //         company: frm.doc.company,
            //         supplier: frm.doc.supplier,
            //         doctype: 'Expense Claim',
            //         expense_claim: frm.doc.name,
            //         employee: frm.doc.employee,
            //         from_date: moment(frm.doc.posting_date).format('YYYY-MM-DD'),
            //         to_date: moment(frm.doc.posting_date).format('YYYY-MM-DD')
            //     };
            //     frappe.set_route("query-report", "BIR 2306");
            // }, __("View"));

            frm.add_custom_button(__('BIR 2307'), function() {
                frappe.route_options = {
                    company: frm.doc.company,
                    doctype: 'Expense Claim',
                    expense_claim: frm.doc.name,
                    employee: frm.doc.employee,
                    from_date: moment(frm.doc.expenses[0].expense_date).format('YYYY-MM-DD'),
                    to_date: moment(frm.doc.expenses[0].expense_date).format('YYYY-MM-DD')
                };
                frappe.set_route("query-report", "BIR 2307");
            }, __("View"));
        }
    },
});

frappe.ui.form.on('Expense Taxes and Charges', {    
    atc_rate: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (frm.doc.docstatus == 0 && row.charge_type != 'Actual') {
            frappe.model.set_value(cdt, cdn, "rate", -row.atc_rate);
            refresh_field("rate");
        }
    },

    atc: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (frm.doc.docstatus == 0 && !row.atc) {
            frappe.model.set_value(cdt, cdn, "atc_rate", 0);
            refresh_field("atc_rate");
        }
    }
});