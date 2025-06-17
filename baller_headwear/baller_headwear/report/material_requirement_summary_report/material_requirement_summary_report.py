import frappe
from frappe.utils import getdate

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": "BOM Creator", "fieldname": "parent", "fieldtype": "Link", "options": "BOM Creator", "width": 180},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Data", "width": 150},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 200},
        {"label": "UOM", "fieldname": "uom", "fieldtype": "Data", "width": 80},
        {"label": "Planned Fabric Needed", "fieldname": "custom_planned_fabric_needed", "fieldtype": "Float", "width": 180},
        {"label": "Creation Date", "fieldname": "creation", "fieldtype": "Datetime", "width": 180}
    ]

def get_data(filters):
    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))

    return frappe.db.sql("""
        SELECT
            bc.name AS parent,
            i.item_code,
            i.item_name,
            i.uom,
            i.custom_planned_fabric_needed,
            bc.creation
        FROM
            `tabBOM Creator` bc
        JOIN
            `tabBOM Creator Item` i ON i.parent = bc.name
        WHERE
            bc.creation BETWEEN %s AND %s
        ORDER BY
            bc.creation DESC
    """, (from_date, to_date), as_dict=True)
