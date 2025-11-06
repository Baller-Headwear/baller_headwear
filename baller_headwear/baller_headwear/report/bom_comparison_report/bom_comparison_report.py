import frappe
from frappe.utils import get_datetime

def execute(filters=None):
    data = get_data(filters)
    columns = get_columns()
    return columns, data

def get_columns():
    columns = [
        {"label": "FG Item", "fieldname": "fg_good_item", "fieldtype": "Data", "width": 200},
        {"label": "Work Order", "fieldname": "work_order", "fieldtype": "Data", "width": 150},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 150},
        {"label": "Bom", "fieldname": "bom_no", "fieldtype": "Data", "width": 150},
        {"label": "Request Item Code", "fieldname": "raw_material_item", "fieldtype": "Link", "options": "Item", "width": 140},
        {"label": "Request Item Name", "fieldname": "raw_material_item_name", "fieldtype": "Link", "options": "Item", "width": 140},
        {"label": "UOM", "fieldname": "stock_uom", "fieldtype": "Data", "width": 60},
        {"label": "Theoretical Qty (BOM)", "fieldname": "theoretical_qty", "fieldtype": "Float", "width": 130},
        {"label": "Actual Qty (Consumed)", "fieldname": "consumed_qty", "fieldtype": "Float", "width": 130},
        {"label": "Diff Qty", "fieldname": "diff_qty", "fieldtype": "Float", "width": 100},
        {"label": "Required Qty", "fieldname": "required_qty", "fieldtype": "Float", "width": 130},
        {"label": "Transferred Qty", "fieldname": "transferred_qty", "fieldtype": "Float", "width": 130}
    ]

    return columns

def get_data(filters):
    if not filters:
        filters = {}

    from_date = get_datetime(filters.from_date + " 00:00:00")
    to_date = get_datetime(filters.to_date + " 23:59:59")

    conditions = ""

    if from_date and to_date:
        conditions += " AND wo.actual_start_date BETWEEN %(from_date)s AND %(to_date)s "

    if filters.get("fg_item"):
        conditions += " AND wo.production_item = %(fg_item)s "

    if not conditions:
        return
        
    data = frappe.db.sql(f"""
        SELECT
            wo.production_item AS fg_good_item,
            wo.name AS work_order,
            wo.bom_no,
            wo.actual_start_date,
            wo.status,
            bei.item_code AS raw_material_item,
            i.item_name AS raw_material_item_name,
            bei.stock_uom,
            ROUND(bei.stock_qty * wo.qty, 6) AS theoretical_qty,
            woItem.consumed_qty,
            ROUND(woItem.consumed_qty - (bei.stock_qty * wo.qty), 6) AS diff_qty,
            woItem.required_qty,
            woItem.transferred_qty
        FROM `tabWork Order` wo
        JOIN `tabBOM Explosion Item` bei ON bei.parent = wo.bom_no
        JOIN `tabItem` i ON i.name = bei.item_code
        JOIN `tabWork Order Item` woItem 
            ON woItem.parent = wo.name 
            AND woItem.item_code = bei.item_code
        {conditions}
        AND wo.status in ('In Process', 'Completed')
        GROUP BY
            wo.name,
            bei.item_code,
            i.item_name,
            bei.stock_uom,
            wo.production_item, 
            wo.actual_start_date
        ORDER BY wo.actual_start_date;
    """, filters, as_dict=True)

    return data