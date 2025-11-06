function get_years() {
    let result = [];
    frappe.call({
        async: false,
        method: "aruga_acct.aruga_accounting.utils.get_years",
        type: "GET",
        callback: function (r) {
            if (!r.exc) {
                result = r.message;
            }
        }
    });
    return result;
}

function remove_commas(str) {
    while (str.search(",") >= 0) {
        str = (str + "").replace(',', '');
    }
    return str;
};

function get_company_information(company) {
    let company_information = {};
    frappe.call({
        async: false,
        method: "aruga_acct.aruga_accounting.utils.get_company_information",
        type: "GET",
        args: {
            'company': company
        },
        callback: function (r) {
            if (!r.exc) {
                company_information = r.message;
            }
        }
    });
    return company_information
}