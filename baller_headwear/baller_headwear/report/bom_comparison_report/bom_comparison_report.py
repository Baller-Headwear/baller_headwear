import frappe

def execute(filters=None):
    data = get_data(filters)
    columns = get_columns()
    return columns, data

def get_columns():
    columns = [
        {"label": "Sales Invoice Date", "fieldname": "sale_invoice_date", "fieldtype": "Date", "width": 150},
        # {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        # {"label": "Sales Order", "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 150},
        # {"label": "Work Order", "fieldname": "work_order", "fieldtype": "Link", "options": "Work Order", "width": 150},
        {"label": "Bom", "fieldname": "bom_doc_name", "fieldtype": "Data", "width": 150},
        {"label": "Item", "fieldname": "item_code", "fieldtype": "Data", "width": 150},
        {"label": "Request Item", "fieldname": "rm_item", "fieldtype": "Link", "options": "Item", "width": 140},
        {"label": "FG Item", "fieldname": "fg_item", "fieldtype": "Link", "options": "Item", "width": 140},
        {"label": "UOM", "fieldname": "uom", "fieldtype": "Data", "width": 60},
        {"label": "Theoretical Qty (BOM)", "fieldname": "theoretical_qty", "fieldtype": "Float", "width": 150},
        {"label": "Actual Qty (Consumed)", "fieldname": "actual_qty", "fieldtype": "Float", "width": 250},
        # {"label": "Variance", "fieldname": "variance", "fieldtype": "Float", "width": 120},
        # {"label": "% Variance", "fieldname": "variance_percent", "fieldtype": "Percent", "width": 120}
    ]

    return columns

def get_data(filters):
    if not filters:
        filters = {}

    if not filters:
        filters = {}

    page = int(filters.get("page") or 1)
    page_length = int(filters.get("page_length") or 1000)
    offset = (page - 1) * page_length
    conditions = ""
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    fg_item = filters.get("fg_item")

    if filters.get("from_date") and filters.get("to_date"):
        conditions += " AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s "

    if filters.get("fg_item"):
        conditions += " AND wo.production_item = %(fg_item)s "

    data = frappe.db.sql(f"""
        SELECT si.posting_date as sale_invoice_date,
            so.name AS sales_order,
            wo.name AS work_order,
            bom_doc.name as bom_doc_name,
            bom_doc.item as item_code,
            bom_item.item_code AS rm_item,
            wo.production_item AS fg_item,
            bom_doc.name AS bom_no,
            bom_item.qty AS theoretical_qty,
            bom_item.uom,
            ROUND(woItem.consumed_qty / NULLIF(wo.produced_qty, 0), 6) AS actual_qty
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        LEFT JOIN `tabSales Order` so ON so.name = sii.sales_order
        LEFT JOIN `tabSales Order Item` soi ON soi.parent = so.name AND soi.item_code = sii.item_code
        LEFT JOIN `tabWork Order` wo ON wo.sales_order = so.name AND wo.production_item = sii.item_code
        LEFT JOIN `tabWork Order Item` woItem ON woItem.parent = wo.name
        LEFT JOIN `tabBOM` bom_doc ON bom_doc.name = wo.bom_no
        LEFT JOIN `tabBOM Item` bom_item ON bom_item.parent = bom_doc.name
        LEFT JOIN `tabStock Entry` se ON se.work_order = wo.name
        LEFT JOIN `tabStock Entry Detail` sed ON sed.parent = se.name AND sed.item_code = bom_item.item_code
        WHERE
            si.docstatus = 1
            AND se.docstatus = 1
            {conditions}   
        GROUP BY bom_doc.item, bom_item.item_code, wo.production_item
        ORDER BY 
            si.posting_date DESC
                LIMIT {page_length} OFFSET {offset};
    """, filters, as_dict=True)

    return data