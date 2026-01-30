import frappe
from frappe.utils import cint, flt, get_datetime

def execute(filters):
    data = get_data(filters)
    columns = get_columns()
    return columns, data or []

def get_columns():
    columns = [
        {"label": "Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 150},
        {"label": "Voucher #", "fieldname": "se_name", "fieldtype": "Data", "width": 150},
        {"label": "Voucher Type", "fieldname": "stock_entry_type", "fieldtype": "Data", "width": 150},
        {"label": "Bom", "fieldname": "bom_name", "fieldtype": "Data", "width": 150},
        # {"label": "Work Order", "fieldname": "work_order", "fieldtype": "Data", "width": 150},
        {"label": "Cost Subject", "fieldname": "top_item", "fieldtype": "Data", "width": 150},
        {"label": "Request Item", "fieldname": "rm_item", "fieldtype": "Link", "options": "Item", "width": 140},
        {"label": "FG Item", "fieldname": "fg_item", "fieldtype": "Link", "options": "Item", "width": 140},
        {"label": "UOM", "fieldname": "uom", "fieldtype": "Data", "width": 60},
        {"label": "Unit Price", "fieldname": "unit_price", "fieldtype": "Currency", "width": 150},
        {"label": "In Qty", "fieldname": "in_qty", "fieldtype": "Float", "width": 150},
        {"label": "In Amount", "fieldname": "in_amount", "fieldtype": "Currency", "width": 250},
        {"label": "Out Qty", "fieldname": "out_qty", "fieldtype": "Float", "width": 150},
        {"label": "Out Amount", "fieldname": "out_amount", "fieldtype": "Currency", "width": 250},
        {"label": "Balance Qty", "fieldname": "balance_qty", "fieldtype": "Float", "width": 150},
        {"label": "Balance Value", "fieldname": "balance_value", "fieldtype": "Float", "width": 150},
    ]

    return columns

def get_data(filters):
    from_date = get_datetime(filters.from_date + " 00:00:00")
    to_date = get_datetime(filters.to_date + " 23:59:59")
    warehouse = filters.warehouse
    cost_subject = filters.cost_subject
    params = {
        'from_date': from_date,
        'to_date': to_date,
        'warehouse': warehouse,
        'cost_subject': cost_subject
    }

    conditions = ""
    if warehouse:
        conditions += " AND sed.s_warehouse = %(warehouse)s"
    if cost_subject:
        conditions += " AND bt.top_item = %(cost_subject)s"
    if from_date and to_date:
        conditions += " AND se.posting_date BETWEEN %(from_date)s AND %(to_date)s"

    data = frappe.db.sql(f"""
        WITH RECURSIVE bom_tree AS (
            SELECT b.name AS bom_name,
            b.item AS top_item
            FROM `tabBOM` b
            JOIN `tabItem` t ON b.item = t.name 
            WHERE b.is_active = 1 AND b.is_default = 1 AND t.item_group IN ('Trucker Cap', 'CAP', 'Stubby Cooler')
            UNION ALL
            SELECT child_bom.name, bt.top_item
            FROM `tabBOM Item` bi
            JOIN `tabBOM` child_bom ON bi.bom_no = child_bom.name
            JOIN bom_tree bt ON bi.parent = bt.bom_name
        )
        SELECT
            bt.top_item,
            bt.bom_name,
            se.posting_date,
            se.name AS se_name,
            se.stock_entry_type,
            sed.item_code AS rm_item,
            sed.uom,
            sed.s_warehouse,
            sed.t_warehouse,
            ROUND(sed.basic_rate,2) as unit_price,
            wo.production_item AS fg_item,
            CASE 
                WHEN se.stock_entry_type IN ('Material Transfer for Manufacture','Manufacture') AND sed.s_warehouse IS NOT NULL THEN ROUND(sed.qty,3) ELSE 0 END AS out_qty,
            CASE 
                WHEN se.stock_entry_type IN ('Material Transfer for Manufacture','Manufacture') AND sed.s_warehouse IS NOT NULL THEN ROUND(sed.basic_amount,2) ELSE 0 END AS out_amount,
            CASE 
                WHEN se.stock_entry_type = 'Manufacture' AND sed.t_warehouse IS NOT NULL THEN ROUND(sed.qty,3) ELSE 0 END AS in_qty,
            CASE 
                WHEN se.stock_entry_type = 'Manufacture' AND sed.t_warehouse IS NOT NULL THEN ROUND(sed.basic_amount,2) ELSE 0 END AS in_amount,
            sle.qty_after_transaction AS balance_qty,
            sle.stock_value AS balance_value
        FROM bom_tree bt
        JOIN `tabWork Order` wo ON bt.bom_name = wo.bom_no
        JOIN `tabStock Entry` se ON wo.name = se.work_order
        LEFT JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        LEFT JOIN `tabStock Ledger Entry` sle
            ON sle.item_code = sed.item_code AND sle.voucher_detail_no = sed.name
        WHERE se.docstatus = 1
        {conditions}
        GROUP BY se_name, bt.bom_name, sed.item_code
        ORDER BY se.posting_date ASC
    """, params, as_dict=True)

    return data
