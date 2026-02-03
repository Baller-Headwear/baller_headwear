import frappe
from frappe.utils import get_datetime
from frappe.utils import format_datetime
import json

def execute(filters=None):
    columns = get_columns()
    data = get_data_report(filters)
    return columns, data

def get_columns():
    return [
        {"label": "QTN Number", "fieldname": "quotation", "fieldtype": "Link", "options": "Quotation", "width": 200},
        {"label": "Sales Order Number", "fieldname": "sale_order_code", "fieldtype": "Link", "options": "Sales Order", "width": 200},
        # {"label": "Item Code", "fieldname": "item_code", "fieldtype": "text","width": 200},
        {"label": "Initital Order Amount", "fieldname": "old_rate", "fieldtype": "Currency", "width": 180},
        {"label": "Updated Order Amount", "fieldname": "new_rate", "fieldtype": "Currency","width": 180},
        {"label": "Remark", "fieldname": "remark", "fieldtype": "Data", "width": 200}
    ]

def is_grand_total_changed(version_row):
    data = json.loads(version_row.data or "{}")
    return any(c[0] == "base_grand_total" for c in data.get("changed", []))

def get_grand_total_change(version_row):
    data = json.loads(version_row.data or "{}")
    for field, old, new in data.get("changed", []):
        if field == "base_grand_total":
            return old, new

    return None, None

def safe_float(val):
    try:
        print(val)
        return float(val)
    except (TypeError, ValueError):
        return None


def get_data_report(filters):
    data = []
    from_date = get_datetime(filters.from_date + " 00:00:00")
    to_date = get_datetime(filters.to_date + " 23:59:59")
    sale_order = filters.get('sales_order')

    filters_dict = {
        "from_date": from_date,
        "to_date": to_date,
        "sales_order": sale_order
    }

    query = f"""
        SELECT so.name as so_code, so.transaction_date, so.base_grand_total, soi.prevdoc_docname as quotation, v.`data`, v.creation
        FROM `tabVersion` v
        JOIN (
            SELECT
                docname,
                MIN(creation) AS first_creation
            FROM `tabVersion`
            WHERE ref_doctype = 'Sales Order'
            AND JSON_EXTRACT(data, '$.changed') IS NOT NULL
            AND JSON_SEARCH(data, 'one', 'base_grand_total') IS NOT NULL
            GROUP BY docname
        ) x
        ON v.docname = x.docname
        JOIN `tabSales Order` so on so.name = v.docname 
        JOIN (
            SELECT
                parent,
                MIN(prevdoc_docname) AS prevdoc_docname
            FROM `tabSales Order Item`
            WHERE prevdoc_docname IS NOT NULL
            GROUP BY parent
        ) soi
            ON soi.parent = so.name
        WHERE soi.prevdoc_docname is not null
        AND v.creation = x.first_creation
        AND so.customer ='International Headwear Pty Ltd'
        AND so.transaction_date BETWEEN %(from_date)s AND %(to_date)s
    """
    version_sales_order_items = frappe.db.sql(query, filters_dict, as_dict=True)

    try:
        for item in version_sales_order_items:

            old_rate, new_rate = get_grand_total_change(item)
            data.append({
                "quotation": item.quotation or  '',
                "sale_order_code": item.so_code or  '',
                "old_rate": old_rate,
                "new_rate": item.base_grand_total,
                "remark": ""
            })
    except ValueError as e:
        frappe.log_error(
            message=f"Invalid Version.data",
            title="Rate Change Report Error"
        )

    return data

