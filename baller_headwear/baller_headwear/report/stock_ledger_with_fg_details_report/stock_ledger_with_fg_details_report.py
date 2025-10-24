import frappe

def execute(filters=None):
    data = get_data(filters)
    columns = get_columns()
    return columns, data or []

def get_columns():
    columns = [
        {"label": "Stock Entry Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 150},
        {"label": "Stock Entry Code", "fieldname": "se_name", "fieldtype": "Data", "width": 150},
        {"label": "Stock Entry type", "fieldname": "stock_entry_type", "fieldtype": "Data", "width": 150},
        {"label": "Bom", "fieldname": "bom_name", "fieldtype": "Data", "width": 150},
        {"label": "Work Order", "fieldname": "work_order", "fieldtype": "Data", "width": 150},
        {"label": "Cost Subject", "fieldname": "root_bom_item", "fieldtype": "Data", "width": 150},
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
    if not filters:
        filters = {}

    warehouse = filters.get("warehouse")
    page = int(filters.get("page") or 1)
    page_length = int(filters.get("page_length") or 100)
    offset = 0

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    cost_subject = filters.get("cost_subject")
    conditions = ""
    if warehouse:
        conditions += " AND sed.s_warehouse = %(warehouse)s "
    
    if cost_subject:
       conditions += " AND t.root_item = %(cost_subject)s "

    if conditions:
       page_length = 1000

    if from_date and to_date:
       conditions += " AND se.posting_date BETWEEN %(from_date)s AND %(to_date)s "

    data = frappe.db.sql(f"""
        WITH RECURSIVE bom_tree AS (
            SELECT
                b.name AS bom_name,
                b.item AS root_item
            FROM `tabBOM` b
            UNION ALL
            SELECT
                parent_bom.name AS bom_name,
                parent_bom.item AS root_item
            FROM `tabBOM` parent_bom
            JOIN `tabBOM Item` bi ON bi.parent = parent_bom.name
            JOIN bom_tree t ON bi.bom_no = t.bom_name
        )
        SELECT
            se.posting_date,
            se.name as se_name,
            wo.name AS work_order,
            se.stock_entry_type,
            se.from_warehouse,
            se.to_warehouse,
            bom_doc.name as bom_name,
            sed.item_code,
            sed.uom,
            t.root_item AS root_bom_item,
            sed.item_code AS rm_item,
            wo.production_item AS fg_item,
            ROUND(sed.basic_rate,2) as unit_price,
            (CASE 
                WHEN se.stock_entry_type = 'Manufacture' 
                    AND sed.t_warehouse IS NOT NULL 
                    AND sed.item_code = wo.production_item THEN ROUND(sed.qty,2) 
                ELSE 0 
            END) AS in_qty,
            (CASE 
                WHEN se.stock_entry_type = 'Manufacture' 
                    AND sed.t_warehouse IS NOT NULL 
                    AND sed.item_code = wo.production_item THEN ROUND(sed.basic_amount, 0)
                ELSE 0 
            END) AS in_amount,
            (CASE 
                WHEN se.stock_entry_type IN ('Material Transfer for Manufacture', 'Manufacture') 
                    AND sed.s_warehouse IS NOT NULL THEN ROUND(sed.qty, 2)
                ELSE 0 
            END) AS out_qty,
            (CASE 
                WHEN se.stock_entry_type IN ('Material Transfer for Manufacture', 'Manufacture') 
                    AND sed.s_warehouse IS NOT NULL THEN ROUND(sed.basic_amount, 0)
                ELSE 0 
            END) AS out_amount,
            ROUND(sle.qty_after_transaction, 2) AS balance_qty,
            ROUND(sle.stock_value, 2) balance_value
        FROM `tabWork Order` wo
        LEFT JOIN `tabStock Entry` se ON se.work_order = wo.name
        LEFT JOIN `tabBOM` bom_doc ON wo.bom_no = bom_doc.name
        LEFT JOIN `tabBOM Item` bom_item ON bom_item.parent = bom_doc.name
        LEFT JOIN `bom_tree` t ON t.bom_name = bom_doc.name
        LEFT JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        LEFT JOIN `tabStock Ledger Entry` sle on sle.voucher_detail_no = sed.name
        WHERE se.docstatus = 1
        {conditions}
        GROUP BY 
            wo.name, 
            item_code, 
            bom_doc.name, 
            wo.production_item
        ORDER BY in_qty ASC
    """, filters, as_dict=True)

    return data