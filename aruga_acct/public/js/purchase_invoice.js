frappe.provide("aruga_acct.purchase_invoice");

frappe.ui.form.on('Purchase Invoice', {
    refresh: function (frm) {
        if (frm.doc.is_return == 0 && frm.doc.docstatus == 1) {
            frm.add_custom_button(__('BIR 2306'), function () {
                frappe.route_options = {
                    company: frm.doc.company,
                    supplier: frm.doc.supplier,
                    doctype: 'Purchase Invoice',
                    purchase_invoice: frm.doc.name,
                    from_date: moment(frm.doc.posting_date).format('YYYY-MM-DD'),
                    to_date: moment(frm.doc.posting_date).format('YYYY-MM-DD')
                };
                frappe.set_route("query-report", "BIR 2306");
            }, __("View"));
            frm.add_custom_button(__('BIR 2307'), function () {
                frappe.route_options = {
                    company: frm.doc.company,
                    supplier: frm.doc.supplier,
                    doctype: 'Purchase Invoice',
                    purchase_invoice: frm.doc.name,
                    from_date: moment(frm.doc.posting_date).format('YYYY-MM-DD'),
                    to_date: moment(frm.doc.posting_date).format('YYYY-MM-DD')
                };
                frappe.set_route("query-report", "BIR 2307");
            }, __("View"));
        }
    },

    conversion_rate: function (frm) {
        $.each(frm.doc.taxes, function (index, row) {
            if (row.charge_type == 'Actual' && row.use_custom_tax_base) {
                frappe.model.set_value(row.doctype, row.name, "use_custom_tax_base", 0);
                frappe.model.set_value(row.doctype, row.name, "custom_tax_base", 0);

                // frappe.model.set_value(row.doctype, row.name, "custom_tax_base", flt(row.custom_tax_base / frm.doc.conversion_rate, precision("custom_tax_base", row)));
                // refresh_field("custom_tax_base");
            }
        });
    },
});

frappe.ui.form.on('Purchase Taxes and Charges', {
    charge_type: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.charge_type != 'Actual') {
            frappe.model.set_value(cdt, cdn, "use_custom_tax_base", 0);

            frm.trigger('rate');
        }
    },
    use_custom_tax_base: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.charge_type != 'Actual') {
            return;
        }

        if (row.use_custom_tax_base) {
            frappe.model.set_value(cdt, cdn, "custom_tax_base", frm.doc.net_total);
            refresh_field("custom_tax_base");
        }
        else {
            frappe.model.set_value(cdt, cdn, "custom_tax_base", 0);
            refresh_field("custom_tax_base");
        }

        aruga_acct.purchase_invoice.calculate_custom_tax_amount(frm, cdt, cdn);
    },

    custom_tax_base: function (frm, cdt, cdn) {
        aruga_acct.purchase_invoice.calculate_custom_tax_amount(frm, cdt, cdn);
        aruga_acct.purchase_invoice.set_custom_base_tax_base(frm, cdt, cdn);
    },

    form_render: function (frm, cdt, cdn) {
        aruga_acct.purchase_invoice.set_dynamic_labels(frm, cdt, cdn);
    },

    atc_rate: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (frm.doc.docstatus == 0 && row.charge_type != 'Actual') {
            frappe.model.set_value(cdt, cdn, "rate", row.atc_rate);
            refresh_field("rate");
        }

        aruga_acct.purchase_invoice.calculate_custom_tax_amount(frm, cdt, cdn);
    },

    atc: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (frm.doc.docstatus == 0 && !row.atc) {
            frappe.model.set_value(cdt, cdn, "atc_rate", 0);
            refresh_field("atc_rate");
        }
    }
});

$.extend(aruga_acct.purchase_invoice, {
    calculate_custom_tax_amount: function (frm, cdt, cdn) {
        if (frm.doc.docstatus != 0) {
            return;
        }

        let row = locals[cdt][cdn];

        if (row.charge_type != 'Actual') {
            return;
        }

        if (row.custom_tax_base > frm.doc.net_total) {
            frappe.model.set_value(cdt, cdn, "custom_tax_base", frm.doc.net_total);
            refresh_field("custom_tax_base");
            frappe.throw(__(`Tax base cannot be more than the net total of ${frm.doc.net_total}.`));
        }

        let tax_amount = row.custom_tax_base * (row.atc_rate / 100)
        frappe.model.set_value(cdt, cdn, "tax_amount", tax_amount);
        refresh_field("tax_amount");
    },

    set_custom_base_tax_base: function (frm, cdt, cdn) {
        let company_currency = erpnext.get_currency(frm.doc.company);
        let conversion_rate = 1;
        if (company_currency != frm.doc.currency) {
            conversion_rate = frm.doc.conversion_rate;
        }

        let row = locals[cdt][cdn];
        let custom_base_tax_base = flt(flt(row.custom_tax_base) * conversion_rate, precision("custom_base_tax_base", row));
        frappe.model.set_value(cdt, cdn, "custom_base_tax_base", custom_base_tax_base);
        let hidden = frm.doc.currency != company_currency ? 0 : 1;
        let df = frappe.meta.get_docfield('Purchase Taxes and Charges', 'custom_base_tax_base', cdn);
        df.hidden = hidden;
        refresh_field("custom_base_tax_base");
    },

    set_dynamic_labels: function (frm, cdt, cdn) {
        let company_currency = erpnext.get_currency(frm.doc.company);

        frm.set_currency_labels(["custom_base_tax_base"], company_currency, "taxes");
        frm.set_currency_labels(["custom_tax_base"], frm.doc.currency, "taxes");

        let df_custom_tax_base = frappe.meta.get_docfield(cdt, 'custom_tax_base', cdn);

        let hidden = (frm.doc.currency != company_currency ? 0 : 1) || df_custom_tax_base.hidden;
        let df_custom_base_tax_base = frappe.meta.get_docfield(cdt, 'custom_base_tax_base', cdn);
        df_custom_base_tax_base.hidden = hidden;

        refresh_field("custom_base_tax_base");
        refresh_field("custom_tax_base");
    },
});