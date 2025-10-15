
import frappe

def execute(filters=None):
    data = get_data(filters)
    columns = get_columns()
    return columns, data

def get_columns():
    columns = [
        {"label": "Stock entry Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 150},
        {"label": "Stock entry Code", "fieldname": "se_name", "fieldtype": "Data", "width": 150},
        {"label": "Stock entry type", "fieldname": "movement_type", "fieldtype": "Data", "width": 150},
        {"label": "Bom", "fieldname": "bom_name", "fieldtype": "Data", "width": 150},
        {"label": "Work Order", "fieldname": "work_order", "fieldtype": "Data", "width": 150},
        {"label": "Request Item", "fieldname": "rm_item", "fieldtype": "Link", "options": "Item", "width": 140},
        {"label": "FG Item", "fieldname": "fg_item", "fieldtype": "Link", "options": "Item", "width": 140},
        {"label": "UOM", "fieldname": "uom", "fieldtype": "Data", "width": 60},
        # {"label": "Balance Qty", "fieldname": "balance_qty", "fieldtype": "Float", "width": 150},
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
    page_length = int(filters.get("page_length") or 50)
    offset = (page - 1) * page_length
    conditions = ""
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    fg_item = filters.get("fg_item")
    return []
    if filters.get("from_date") and filters.get("to_date"):
        conditions += " AND se.posting_date BETWEEN %(from_date)s AND %(to_date)s "

    if filters.get("fg_item"):
        conditions += " AND wo.production_item = %(fg_item)s "
    
    if warehouse:
        conditions += " AND sed.s_warehouse = %(warehouse)s "

    if conditions:
       page_length = 1000

    data = frappe.db.sql(f"""
        SELECT se.posting_date, bom_doc.name as bom_name, 
        wo.name as work_order, 
        bom_item.item_code as rm_item,
        wo.production_item AS fg_item,
        bom_item.uom,
        se.name as se_name,
        se.stock_entry_type,
        sed.s_warehouse,
        sed.t_warehouse,
        ROUND(sed.transfer_qty, 2) AS out_qty,
        sed.basic_rate as unit_price,
        ROUND(sed.basic_amount, 0) AS out_amount
        FROM `tabWork Order` wo
        LEFT JOIN `tabWork Order Item` woItem ON woItem.parent = wo.name
        LEFT JOIN `tabBOM` bom_doc ON bom_doc.name = wo.bom_no
        LEFT JOIN `tabBOM Item` bom_item ON bom_item.parent = bom_doc.name
        LEFT JOIN `tabStock Entry` se ON se.work_order = wo.name
        LEFT JOIN `tabStock Entry Detail` sed ON sed.parent = se.name AND sed.item_code = bom_item.item_code
        WHERE
            se.docstatus = 1
            {conditions}    
                LIMIT {page_length} OFFSET {offset};
    """, filters, as_dict=True)

    return data