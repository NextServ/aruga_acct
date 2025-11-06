// Copyright (c) 2021, SERVIO Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on('Tax Declaration Company Setup', {
    refresh: function (frm) {
        if (!frm.doc.__unsaved) {
            frm.add_custom_button(__('Generate Tax Templates'), function () {
                let company = frm.doc.company;
                if (company) {
                    frappe.call({
                        method: "aruga_acct.aruga_accounting.utils.generate_company_tax_templates",
                        type: "POST",
                        args: {
                            'company': company
                        },
                        callback: function (r) {
                            if (!r.exc) {
                                let n = r.message;
                                frappe.msgprint(`Tax template(s) successfully created: <strong>${n}</strong>`);
                                frm.doc.reload();
                            }
                        }
                    });
                }
                else {
                    frappe.msgprint(`Select a company.`);
                }
            });
        }
        // sales taxes and charges template
        frm.set_query('vat_sales', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        frm.set_query('sales_to_government', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        frm.set_query('zero_rated_sales', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        frm.set_query('exempt_sales', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        // sales item tax template
        frm.set_query('item_vat_sales', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        frm.set_query('item_sales_to_government', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        frm.set_query('item_zero_rated_sales', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        frm.set_query('item_exempt_sales', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        //purchase taxes and charges template

        frm.set_query('capital_goods', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        frm.set_query('domestic_purchases_of_goods', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        frm.set_query('importation_of_goods', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        frm.set_query('domestic_purchase_of_services', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        frm.set_query('services_rendered_by_non_residents', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        frm.set_query('others', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        frm.set_query('directly_attributable_to_exempt_sales', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        frm.set_query('directly_attributable_to_sale_to_government', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        // purchase item tax template

        frm.set_query('item_capital_goods', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        frm.set_query('item_domestic_purchases_of_goods', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        frm.set_query('item_importation_of_goods', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        frm.set_query('item_domestic_purchase_of_services', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        frm.set_query('item_services_rendered_by_non_residents', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        frm.set_query('item_others', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        frm.set_query('item_directly_attributable_to_exempt_sales', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        frm.set_query('item_directly_attributable_to_sale_to_government', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        //purchases not qualified for input tax

        frm.set_query('zero_rated_purchase', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        frm.set_query('exempt_purchase', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        //purchases not qualified for input tax item tax template

        frm.set_query('item_zero_rated_purchase', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        frm.set_query('item_exempt_purchase', function () {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

    }
});
