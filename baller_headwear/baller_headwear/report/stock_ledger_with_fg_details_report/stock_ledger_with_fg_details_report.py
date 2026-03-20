import frappe
from frappe.utils import cint, flt, get_datetime

def execute(filters):
    data = get_data(filters)
    columns = get_columns()
    return columns, data or []

def get_columns():
    columns = [
        {"label": "Warehouse", "fieldname": "warehouse", "fieldtype": "Data", "width": 150},
        {"label": "Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 150},
        {"label": "Voucher #", "fieldname": "se_name", "fieldtype": "Link", "options": 'Stock Entry', "width": 150},
        {"label": "Voucher Type", "fieldname": "stock_entry_type", "fieldtype": "Data", "width": 150},
        {"label": "Bom", "fieldname": "bom_name", "fieldtype": "Data", "width": 150},
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
        {"label": "Balance Value", "fieldname": "balance_value", "fieldtype": "Float", "width": 150}
    ]

    return columns

def get_data(filters):
    from_date = get_datetime(filters.from_date + " 00:00:00")
    to_date = get_datetime(filters.to_date + " 23:59:59")
    voucher_type = filters.voucher_type
    warehouse = filters.warehouse
    cost_subject = filters.cost_subject
    params = {
        'from_date': from_date,
        'to_date': to_date,
        'warehouse': warehouse,
        'cost_subject': cost_subject,
        'voucher_type': voucher_type
    }

    conditions = ""
    if warehouse:
        conditions += " AND sle.warehouse = %(warehouse)s"
    if cost_subject:
        conditions += " AND bt.top_item = %(cost_subject)s"
    if from_date and to_date:
        conditions += " AND se.posting_date BETWEEN %(from_date)s AND %(to_date)s"

    if voucher_type:
        conditions += " AND se.stock_entry_type  = %(voucher_type)s"

    data = frappe.db.sql(f"""
        WITH RECURSIVE bom_tree AS (
            SELECT 
                b.name AS bom_name,
                b.item AS top_item
            FROM `tabBOM` b
            JOIN `tabItem` t 
                ON b.item = t.name
            WHERE b.is_active = 1
                AND b.is_default = 1
                AND t.item_group IN ('CAP', 'Trucker Cap', 'Stubby Cooler', 'Bucket Hat')
            UNION ALL
            SELECT 
                child_bom.name,
                bt.top_item
            FROM `tabBOM Item` bi
            JOIN `tabBOM` child_bom 
                ON bi.bom_no = child_bom.name
            JOIN bom_tree bt 
                ON bi.parent = bt.bom_name
        )
        SELECT
            COALESCE(bt1.top_item, bt2.top_item) AS top_item,
            COALESCE(bt1.bom_name, bt2.bom_name) AS bom_name,
            se.posting_date,
            se.name AS se_name,
            se.stock_entry_type,
            sed.item_code AS rm_item,
            sed.uom,
            sed.s_warehouse,
            sed.t_warehouse,
            sle.warehouse,
            ROUND(sed.basic_rate, 2) AS unit_price,
            wo.production_item AS fg_item,
            CASE 
                WHEN sle.warehouse = sed.s_warehouse
                THEN ROUND(ABS(sle.actual_qty), 3)
                ELSE 0
            END AS out_qty,
            CASE 
                WHEN sle.warehouse = sed.s_warehouse
                THEN ROUND(ABS(sle.stock_value_difference), 2)
                ELSE 0
            END AS out_amount,
            CASE 
                WHEN sle.warehouse = sed.t_warehouse
                THEN ROUND(sle.actual_qty, 3)
                ELSE 0
            END AS in_qty,
            CASE 
                WHEN sle.warehouse = sed.t_warehouse
                THEN ROUND(sle.stock_value_difference, 2)
                ELSE 0
            END AS in_amount,
            sle.qty_after_transaction AS balance_qty,
            sle.stock_value AS balance_value
        FROM `tabStock Entry Detail` sed
        JOIN `tabStock Entry` se
            ON se.name = sed.parent
            AND se.docstatus = 1
            AND se.stock_entry_type IN (
                'Material Transfer for Manufacture',
                'Material Transfer',
                'Material Issue',
                'Manufacture'
            )
        LEFT JOIN `tabWork Order` wo
            ON wo.name = se.work_order
        LEFT JOIN bom_tree bt1
            ON bt1.bom_name = wo.bom_no
        LEFT JOIN bom_tree bt2
            ON bt2.top_item = sed.item_code
        LEFT JOIN `tabStock Ledger Entry` sle
            ON sle.voucher_detail_no = sed.name
            AND sle.item_code = sed.item_code
        LEFT JOIN `tabItem` itm
            ON itm.name = sed.item_code
        WHERE 1=1
            {conditions}
        AND IFNULL(itm.item_group, '') != 'Semi-finished'
        AND IFNULL(itm.item_group, '') NOT IN ('CAP', 'Trucker Cap', 'Stubby Cooler', 'Bucket Hat')
        ORDER BY sle.warehouse DESC, se.posting_date ASC
    """, params, as_dict=True)

    return data
