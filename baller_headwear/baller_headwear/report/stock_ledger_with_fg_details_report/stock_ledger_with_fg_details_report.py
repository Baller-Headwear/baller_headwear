import frappe

def execute(filters=None):
    data = get_data(filters)
    columns = get_columns()
    return columns, data

def get_columns():
    columns = [
        {"label": "Stock entry Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 150},
        {"label": "Stock entry Code", "fieldname": "se_name", "fieldtype": "Data", "width": 150},
        {"label": "Stock entry type", "fieldname": "stock_entry_type", "fieldtype": "Data", "width": 150},
        {"label": "Bom", "fieldname": "bom_name", "fieldtype": "Data", "width": 150},
        {"label": "Work Order", "fieldname": "work_order", "fieldtype": "Data", "width": 150},
        {"label": "Cost Subject", "fieldname": "bom_item", "fieldtype": "Data", "width": 150},
        {"label": "Request Item", "fieldname": "rm_item", "fieldtype": "Link", "options": "Item", "width": 140},
        {"label": "FG Item", "fieldname": "fg_item", "fieldtype": "Link", "options": "Item", "width": 140},
        {"label": "UOM", "fieldname": "uom", "fieldtype": "Data", "width": 60},
        {"label": "Unit Price", "fieldname": "unit_price", "fieldtype": "Currency", "width": 150},
        {"label": "Out Qty", "fieldname": "out_qty", "fieldtype": "Float", "width": 150},
        {"label": "Out Amount", "fieldname": "out_amount", "fieldtype": "Currency", "width": 250},
    ]

    return columns

def get_data(filters):
    if not filters:
        filters = {}

    if not filters:
        filters = {}
    warehouse = filters.get("warehouse")
    page = int(filters.get("page") or 1)
    page_length = int(filters.get("page_length") or 100)
    offset = 0
    conditions = ""
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    fg_item = filters.get("fg_item")

    if filters.get("from_date") and filters.get("to_date"):
        conditions += " AND se.posting_date BETWEEN %(from_date)s AND %(to_date)s "

    if filters.get("fg_item"):
        conditions += " parent_bom.item = %(fg_item)s "
    
    if warehouse:
        conditions += " AND sed.s_warehouse = %(warehouse)s "

    if conditions:
       page_length = 1000
    data = frappe.db.sql(f"""
        SELECT 
            se.posting_date,
            wo.name AS work_order,
            bom_doc.name AS bom_name,
            COALESCE(parent_bom.item, bom_doc.item) AS bom_item, 
            bom_item.item_code AS rm_item,
            wo.production_item AS fg_item,
            bom_item.uom,
            se.name AS se_name,
            se.stock_entry_type,
            sed.s_warehouse,
            sed.t_warehouse,
            ROUND(sed.transfer_qty, 2) AS out_qty,
            sed.basic_rate AS unit_price,
            ROUND(sed.basic_amount, 0) AS out_amount
        FROM `tabWork Order` wo
        LEFT JOIN `tabBOM` bom_doc 
            ON bom_doc.name = wo.bom_no
        LEFT JOIN `tabBOM Item` bom_item 
            ON bom_item.parent = bom_doc.name
        LEFT JOIN (
            SELECT 
                bi.bom_no AS child_bom,  
                b.item AS item,
                b.name AS parent_bom_name
            FROM `tabBOM Item` bi
            INNER JOIN `tabBOM` b ON b.name = bi.parent
        ) AS parent_bom
            ON parent_bom.child_bom = bom_doc.name
        INNER JOIN `tabStock Entry` se 
            ON se.work_order = wo.name
        LEFT JOIN `tabStock Entry Detail` sed 
            ON sed.parent = se.name 
            AND sed.item_code = bom_item.item_code
        WHERE 
            se.docstatus = 1
            {conditions}
        GROUP BY se.posting_date,
            wo.name,
            bom_doc.name,
            COALESCE(parent_bom.item, bom_doc.item),
            bom_item.item_code,
            wo.production_item
            LIMIT {page_length} OFFSET {offset}
    """, filters, as_dict=True)

    return data