# Copyright (c) 2013, SERVIO Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import (getdate)
from frappe import _

def execute(filters=None):
    columns, data = [], []
    data = get_data(filters)
    columns = get_columns()
    return columns, data

def get_data(filters):
    data = [
        {
            'bir_0619_f': '✓'
        }
    ]

    return data

def get_columns():
    columns = [
        {
            "fieldname": "bir_0619_f",
            "label": _("BIR 0619-F"),
            "fieldtype": "Data",
            "width": 120
        }
    ]

    return columns