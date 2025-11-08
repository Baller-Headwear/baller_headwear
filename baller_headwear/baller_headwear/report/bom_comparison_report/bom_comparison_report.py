import frappe
from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict
from frappe.utils import get_datetime
from frappe.utils import format_datetime

def execute(filters=None):
    columns = get_columns()
    data = []
    from_date = get_datetime(filters.from_date + " 00:00:00")
    to_date = get_datetime(filters.to_date + " 23:59:59")
    fg_item = filters.get('fg_item')

    if not from_date:
        return

    if not to_date:
        return
    
    filters = {
        "from_date": from_date,
        "to_date": to_date,
    }

    query = """
        SELECT 
            wo.name, wo.bom_no, wo.qty, wo.status,
            wo.actual_start_date, wo.produced_qty, wo.production_item
        FROM `tabWork Order` wo
        JOIN `tabItem` i ON i.name = wo.production_item
        WHERE wo.docstatus = 1
        AND wo.status IN ('In Process', 'Completed')
        AND wo.actual_start_date BETWEEN %(from_date)s AND %(to_date)s
        AND wo.produced_qty > 0
        AND i.item_group IN ('CAP', 'Trucker Cap')
        ORDER BY wo.actual_start_date DESC
    """

    if fg_item:
        query += " AND wo.production_item = %(fg_item)s"
        filters["fg_item"] = fg_item

    work_orders = frappe.db.sql(query, filters, as_dict=True)

    for wo in work_orders:
        root_item = wo.production_item
        child_boms = get_child_boms(wo.production_item)
        work_orders_in_tree = frappe.get_all(
            "Work Order",
            filters={"bom_no": ["in", child_boms], "docstatus": 1},
            pluck="name"
        )

        if not work_orders_in_tree:
            continue

        bom_items = get_bom_items_as_dict(wo.bom_no, wo.qty)
        bom_item_codes = list(bom_items.keys())

        actual_items = frappe.db.sql("""
            SELECT ste.name as stock_code, sti.item_code, SUM(sti.qty) AS actual_qty, sti.uom
            FROM `tabStock Entry` ste
            JOIN `tabStock Entry Detail` sti ON sti.parent = ste.name
            JOIN `tabItem` i ON i.name = sti.item_code
            WHERE ste.docstatus = 1
            AND ste.work_order IN %(work_orders)s
        
            AND ste.purpose IN ('Material Transfer for Manufacture')
            GROUP BY sti.item_code
        """, {"work_orders": tuple(work_orders_in_tree)}, as_dict=True)

        actual_map = {a.item_code: a.actual_qty for a in actual_items}

        for item_code, item in bom_items.items():
  
            bom_total = item.qty * wo.qty
            actual_qty = actual_map.get(item_code, 0)
            variance = actual_qty - bom_total
            data.append({
                "root_item": root_item,
                "work_order": wo.name,
                "actual_start_date": format_datetime(wo.actual_start_date, 'dd-MM-yyyy HH:mm'),
                "item_code": item_code,
                "uom": item.stock_uom,
                "produced_qty": wo.produced_qty,
                "transferred_qty": actual_qty,
                "amount": item.rate * bom_total,
                'work_order_status': wo.status,
                "bom": wo.bom_no,
                "item_name": item.item_name,
                "bom_qty": bom_total,
                "actual_qty": actual_qty,
                "unit_price": item.rate,
                "theoretical_amount": bom_total * item.rate,
                "actual_amount": actual_qty * item.rate,
                "variance": variance,
                "remark": ""
            })

        for a in actual_items:
            if a.item_code not in bom_item_codes:
                data.append({
                    "root_item": root_item,
                    "work_order": wo.name,
                    "actual_start_date": format_datetime(wo.actual_start_date, 'dd-MM-yyyy HH:mm'),
                    "item_code": a.item_code,
                    "uom": a.uom,
                    "produced_qty": wo.produced_qty,
                    "transferred_qty": a.actual_qty,
                    'work_order_status': wo.status,
                    "bom": wo.bom_no,
                    "item_name": frappe.db.get_value("Item", a.item_code, "item_name"),
                    "bom_qty": 0,
                    "actual_qty": a.actual_qty,
                    "unit_price": item.rate,
                    "theoretical_amount": 0,
                    "actual_amount": a.actual_qty * item.rate,
                    "variance": a.actual_qty,
                    "remark": "Not in BOM"
                })

    return columns, data


def get_columns():
    return [
        {"label": "FG Item", "fieldname": "root_item", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": "Work Order", "fieldname": "work_order", "fieldtype": "Link", "options": "Work Order", "width": 120},
        {"label": "Start Date", "fieldname": "actual_start_date", "fieldtype": "Data", "width": 120},
        {"label": "Status", "fieldname": "work_order_status", "fieldtype": "Data","width": 120},
        {"label": "BOM", "fieldname": "bom", "fieldtype": "Data","width": 120},
        {"label": "Request Item Code", "fieldname": "item_code", "fieldtype": "Data", "width": 150},
        {"label": "Request Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 200},
        {"label": "UOM", "fieldname": "uom", "fieldtype": "Data", "width": 100},
        {"label": "Manufactured Qty", "fieldname": "produced_qty", "fieldtype": "Float", "width": 120},
        {"label": "Unit Price", "fieldname": "unit_price", "fieldtype": "Float", "width": 120},
        {"label": "Theoretical Qty (BOM)", "fieldname": "bom_qty", "fieldtype": "Float", "width": 120},
        {"label": "Actual Qty (Consumed)", "fieldname": "actual_qty", "fieldtype": "Float", "width": 120},
        {"label": "Transferred Qty", "fieldname": "transferred_qty", "fieldtype": "Float", "width": 120},
        {"label": "Diff Qty", "fieldname": "variance", "fieldtype": "Float", "width": 120},
        {"label": "Theoretical Amount", "fieldname": "theoretical_amount", "fieldtype": "Float", "width": 120},
        {"label": "Actual Amount", "fieldname": "actual_amount", "fieldtype": "Float", "width": 120},
        # {"label": "Variance %", "fieldname": "variance_pct", "fieldtype": "Percent", "width": 100},
        {"label": "Remark", "fieldname": "remark", "fieldtype": "Data", "width": 150},
    ]

def get_child_boms(root_bom_item):
    result = frappe.db.sql("""
        WITH RECURSIVE bom_tree AS (
            SELECT 
                b.name AS bom_name,
                b.item AS top_item
            FROM `tabBOM` b
            JOIN `tabItem` t ON b.item = t.name 
            WHERE 
                b.item = %(root_bom_item)s
                AND b.is_active = 1
                AND b.is_default = 1
                AND t.item_group IN ('Trucker Cap', 'CAP')
            UNION ALL
            SELECT 
                child_bom.name,
                bt.top_item
            FROM `tabBOM Item` bi
            JOIN `tabBOM` child_bom ON bi.bom_no = child_bom.name
            JOIN bom_tree bt ON bi.parent = bt.bom_name
        )
        SELECT bom_name 
        FROM bom_tree
    """, {"root_bom_item": root_bom_item}, as_dict=True)

    return [r.bom_name for r in result]

