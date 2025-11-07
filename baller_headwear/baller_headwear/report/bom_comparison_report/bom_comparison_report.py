import frappe
from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict
from frappe.utils import get_datetime, formatdate

def execute(filters=None):
    columns = get_columns()
    data = []
    from_date = get_datetime(filters.from_date + " 00:00:00")
    to_date = get_datetime(filters.to_date + " 23:59:59")
    fg_item = filters.get('fg_item')

    conditions = ""

    if from_date and to_date:
        conditions += " AND wo.actual_start_date BETWEEN %(from_date)s AND %(to_date)s "

    if not conditions:
        return

    work_order_filter = {
        "docstatus": 1,  
        "status": ["in", ["In Process", "Completed"]],
        "actual_start_date": ["between", [from_date, to_date]]
    }

    if fg_item: 
        work_order_filter = {
            "docstatus": 1,
            'production_item':fg_item, 
            "status": ["in", ["In Process", "Completed"]],
            "actual_start_date": ["between", [from_date, to_date]]
        }

    work_orders = frappe.get_all("Work Order", 
        filters=work_order_filter, 
        fields=["name", "bom_no", "qty", "status", "actual_start_date", "produced_qty", "production_item"]
    )

    for wo in work_orders:
        root_item = wo.production_item
        bom_items = get_bom_items_as_dict(wo.bom_no, wo.qty)
        bom_item_codes = list(bom_items.keys())

        actual_items = frappe.db.sql("""
            SELECT sti.item_code, SUM(sti.qty) AS actual_qty, sti.uom
            FROM `tabStock Entry` ste
            JOIN `tabStock Entry Detail` sti ON sti.parent = ste.name
            WHERE ste.docstatus = 1
              AND ste.work_order = %s
              AND ste.purpose IN ('Material Transfer for Manufacture')
            GROUP BY sti.item_code
        """, wo.name, as_dict=True)

        actual_map = {a.item_code: a.actual_qty for a in actual_items}

        for item_code, item in bom_items.items():
  
            bom_total = item.qty * wo.qty
            actual_qty = actual_map.get(item_code, 0)
            variance = actual_qty - bom_total
            data.append({
                "root_item": root_item,
                "work_order": wo.name,
                "actual_start_date": formatdate(wo.actual_start_date, 'dd-mm-yyyy'),
                "item_code": item_code,
                "uom": item.stock_uom,
                "produced_qty": wo.produced_qty,
                "transferred_qty": actual_qty,
                'work_order_status': wo.status,
                "bom": wo.bom_no,
                "item_name": item.item_name,
                "bom_qty": bom_total,
                "actual_qty": actual_qty,
                "variance": variance,
                "remark": ""
            })

        for a in actual_items:
            if a.item_code not in bom_item_codes:
                data.append({
                    "root_item": root_item,
                    "work_order": wo.name,
                    "actual_start_date": formatdate(wo.actual_start_date, 'dd-mm-yyyy'),
                    "item_code": a.item_code,
                    "uom": a.uom,
                    "produced_qty": wo.produced_qty,
                    "transferred_qty": a.actual_qty,
                    'work_order_status': wo.status,
                    "bom": wo.bom_no,
                    "item_name": frappe.db.get_value("Item", a.item_code, "item_name"),
                    "bom_qty": 0,
                    "actual_qty": a.actual_qty,
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
        {"label": "Theoretical Qty (BOM)", "fieldname": "bom_qty", "fieldtype": "Float", "width": 120},
        {"label": "Actual Qty (Consumed)", "fieldname": "actual_qty", "fieldtype": "Float", "width": 120},
        {"label": "Transferred Qty", "fieldname": "transferred_qty", "fieldtype": "Float", "width": 120},
        {"label": "Diff Qty", "fieldname": "variance", "fieldtype": "Float", "width": 120},
        # {"label": "Variance %", "fieldname": "variance_pct", "fieldtype": "Percent", "width": 100},
        {"label": "Remark", "fieldname": "remark", "fieldtype": "Data", "width": 150},
    ]
