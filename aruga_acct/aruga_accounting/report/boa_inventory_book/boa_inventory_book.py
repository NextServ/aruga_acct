# Copyright (c) 2013, SERVIO Technologies and contributors
# For license information, please see license.txt

# Copyright (c) 2013, SERVIO Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import (getdate, get_time, cint)
from frappe import _

def execute(filters=None):
    columns, data = [], []
    data = get_data(filters)
    columns = get_columns()
    return columns, data

# todo implement as at time
def get_data(filters):
    precision = cint(frappe.db.get_default("currency_precision")) or 2
    result = frappe.db.sql("""
    SELECT 
        sle.posting_date as max_posting_date,
        sle.item_code,
        i.name,
        i.item_name,
        ROUND(sle.qty_after_transaction, {precision}) AS actual_qty,
        (CASE WHEN sle.qty_after_transaction = 0 THEN 0 ELSE ROUND(sle.valuation_rate, {precision}) END) AS price_per_unit,
        ROUND(sle.stock_value, {precision}) AS amount
    FROM 
        `tabItem` i
    INNER JOIN 
        `tabStock Ledger Entry` sle
    ON sle.name = 
        (SELECT 
            name 
        FROM 
            `tabStock Ledger Entry` 
        WHERE 
            is_cancelled = 0
            and posting_date <= %s
            and company = %s
            and item_code = i.name
        ORDER BY 
            posting_date DESC
        LIMIT 1)
    WHERE
        i.disabled = 0
        and i.is_stock_item = 1
    ORDER BY
        i.name ASC
    """.format(precision=precision), (getdate(filters.as_at_date), filters.company), as_dict=1)

    return result

def get_columns():
    columns = [
        {
            "fieldname": "max_posting_date",
            "label": _("Date"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "name",
            "label": _("Item Code"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "item_name",
            "label": _("Item Name"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "actual_qty",
            "label": _("Unit"),
            "fieldtype": "Float",
            "width": 150
        },
        {
            "fieldname": "price_per_unit",
            "label": _("Price per Unit"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "amount",
            "label": _("Amount"),
            "fieldtype": "Currency",
            "width": 150
        },
    ]

    return columns
