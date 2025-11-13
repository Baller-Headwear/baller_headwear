import frappe
from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict
from frappe.utils import get_datetime
from frappe.utils import format_datetime

def execute(filters=None):
    columns = get_columns()
    filter_type = filters.get('filter_type') or 'Root Item'
    if filter_type == 'Detail':
        data = get_report_with_child(filters)
    else:
        data = get_report_root_item(filters)

    return columns, data


def get_columns():
    return [
        {"label": "FG Item", "fieldname": "root_item", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": "Work Order", "fieldname": "work_order", "fieldtype": "Link", "options": "Work Order", "width": 120},
        {"label": "BOM", "fieldname": "bom", "fieldtype": "Data","width": 120},
        {"label": "Start Date", "fieldname": "actual_start_date", "fieldtype": "Data", "width": 120},
        {"label": "Status", "fieldname": "work_order_status", "fieldtype": "Data","width": 120},
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
        {"label": "Remark", "fieldname": "remark", "fieldtype": "Data", "width": 150},
    ]

def get_child_boms(name):
    result = frappe.db.sql("""
        WITH RECURSIVE bom_tree AS (
            SELECT 
                b.name AS bom_name,
                b.item AS item_code
            FROM `tabWork Order` wo
            JOIN `tabBOM` b ON wo.bom_no = b.name
            WHERE 
                wo.name = %(name)s
            UNION ALL
            SELECT 
                child_bom.name AS bom_name,
                child_bom.item AS item_code
            FROM `tabBOM Item` bi
            JOIN `tabBOM` child_bom ON bi.bom_no = child_bom.name
            JOIN bom_tree bt ON bi.parent = bt.bom_name
        )
        SELECT 
            bt.bom_name
        FROM bom_tree bt
    """, {"name": name}, as_dict=True)

    return [r.bom_name for r in result]

def get_report_root_item(filters):
    data = []
    from_date = get_datetime(filters.from_date + " 00:00:00")
    to_date = get_datetime(filters.to_date + " 23:59:59")
    production_item = filters.get('fg_item')

    if not from_date:
        return

    if not to_date:
        return
    
    filters = {
        "from_date": from_date,
        "to_date": to_date,
    }

    condition = ""
    if production_item:
        condition = " AND wo.production_item = %(production_item)s"
        filters = {
            "from_date": from_date,
            "to_date": to_date,
            "production_item": production_item
        }

    query = f"""
        SELECT 
            wo.name, wo.bom_no, wo.qty, wo.status,
            wo.actual_start_date, wo.produced_qty, wo.production_item
        FROM `tabWork Order` wo
        JOIN `tabItem` i ON i.name = wo.production_item
        WHERE wo.docstatus = 1
        AND wo.status IN ('In Process', 'Completed')
        AND wo.actual_start_date BETWEEN %(from_date)s AND %(to_date)s
        AND wo.produced_qty > 0
        {condition}
        AND i.item_group IN ('CAP', 'Trucker Cap')
        ORDER BY wo.actual_start_date DESC
    """

    work_orders = frappe.db.sql(query, filters, as_dict=True)

    for wo in work_orders:
        root_item = wo.production_item
        child_boms = get_child_boms(wo.name)
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
            AND i.item_group NOT IN ('Semi-finished')
            AND ste.purpose IN ('Manufacture')
            AND sti.t_warehouse IS NULL
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

    return data

def get_report_with_child(filters):
    data = []
    from_date = get_datetime(filters.from_date + " 00:00:00")
    to_date = get_datetime(filters.to_date + " 23:59:59")
    fg_item = filters.get('fg_item')

    if not from_date:
        return

    if not to_date:
        return
    
    condition = ""

    if fg_item:
        condition = " AND wo.production_item = %(fg_item)s"

    query = f"""
        SELECT 
            wo.name AS work_order,
            wo.bom_no,
            wo.qty,
            wo.status,
            wo.actual_start_date,
            wo.produced_qty,
            wo.production_item,
            woItem.item_code,
            woItem.item_name,
            woItem.required_qty,
            woItem.consumed_qty,
            woItem.stock_uom
        FROM `tabWork Order` wo
        JOIN `tabWork Order Item` woItem ON wo.name = woItem.parent
        WHERE wo.docstatus = 1
        AND wo.status IN ('In Process', 'Completed')
        {condition}
        AND wo.actual_start_date BETWEEN %(from_date)s AND %(to_date)s
        AND wo.produced_qty > 0
        ORDER BY wo.actual_start_date DESC
    """

    work_orders = frappe.db.sql(query, filters, as_dict=True)
    if not work_orders:
        return []
    
    work_orders_in_tree = [r.work_order for r in work_orders]

    actual_items = frappe.db.sql("""
        SELECT ste.name as stock_code, sti.item_code, sti.qty AS actual_qty, sti.uom, sti.valuation_rate, ste.work_order,
            wo.production_item, wo.produced_qty, wo.actual_start_date, sti.uom, wo.status, wo.bom_no, sti.item_name
        FROM `tabStock Entry` ste
        JOIN `tabStock Entry Detail` sti ON sti.parent = ste.name
        LEFT JOIN `tabWork Order` wo on wo.name = ste.work_order
        LEFT JOIN `tabBOM` tbBom on tbBom.name = wo.bom_no  
        WHERE ste.docstatus = 1
        AND ste.work_order IN %(work_orders)s
        AND sti.t_warehouse IS NULL
        AND ste.purpose IN ('Manufacture')
    """, {"work_orders": tuple(work_orders_in_tree)}, as_dict=True)

    actual_map_unit_price = {a.item_code: a.valuation_rate for a in actual_items}

    actual_map = {}

    for a in actual_items:
        wo_name = a.get("work_order")
        if not wo_name:
            continue

        if wo_name not in actual_map:
            actual_map[wo_name] = {}

        actual_map[wo_name] = {
            "item_code": a["item_code"],
            "actual_qty": a["actual_qty"],
            "unit_price": a.get("valuation_rate") or 0,
            "uom": a["uom"]
        }

    for wo in work_orders: 
        unit_price = actual_map_unit_price.get(wo.item_code, 0)
        bom_total = wo.required_qty
        actual_qty = wo.consumed_qty 
        variance = actual_qty - bom_total
        data.append({
            "root_item": wo.production_item,
            "work_order": wo.work_order,
            "actual_start_date": format_datetime(wo.actual_start_date, 'dd-MM-yyyy HH:mm'),
            "item_code": wo.item_code,
            "item_name": wo.item_name,
            "uom": wo.stock_uom,
            "produced_qty": wo.produced_qty,
            "transferred_qty": actual_qty,
            "amount": unit_price * bom_total,
            'work_order_status': wo.status,
            "bom": wo.bom_no,
            "bom_qty": bom_total,
            "actual_qty": actual_qty,
            "unit_price": unit_price,
            "theoretical_amount": bom_total * unit_price,
            "actual_amount": actual_qty * unit_price,
            "variance": variance,
            "remark": ""
        })

    data_keys = {(d["work_order"], d["item_code"]) for d in data}

    for item in actual_items:
        key = (item["work_order"], item["item_code"])
        if key not in data_keys:
            data.append({
                "root_item": item['production_item'],
                "work_order": item['work_order'],
                "actual_start_date": format_datetime(item['actual_start_date'], 'dd-MM-yyyy HH:mm'),
                "item_code": item['item_code'],
                "uom": item['uom'],
                "produced_qty": item['produced_qty'],
                "transferred_qty": item['actual_qty'],
                "amount": 0,
                'work_order_status': item['status'],
                "bom": item['bom_no'],
                "item_name": item['item_name'],
                "bom_qty": 0,
                "actual_qty": item['actual_qty'],
                "unit_price": item['valuation_rate'],
                "theoretical_amount": 0,
                "actual_amount": item['actual_qty'] * item['valuation_rate'],
                "variance": item['actual_qty'],
                "remark": "Not in BOM"
            })
  
    sorted_data = sorted(data, key=lambda x: x['work_order'])
    return sorted_data



