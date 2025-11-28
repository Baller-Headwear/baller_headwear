import frappe
from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict
from frappe.utils import get_datetime
from frappe.utils import format_datetime

def execute(filters=None):
    columns = get_columns()
    data = get_report_root_item(filters)

    return columns, data


def get_columns():
    return [
        {"label": "FG Item", "fieldname": "root_item", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": "Work Order", "fieldname": "work_order", "fieldtype": "Link", "options": "Work Order", "width": 120},
        {"label": "BOM", "fieldname": "bom", "fieldtype": "Data","width": 120},
        {"label": "Start Date", "fieldname": "actual_start_date", "fieldtype": "Data", "width": 120},
        {"label": "Status", "fieldname": "work_order_status", "fieldtype": "Data","width": 120},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Data", "width": 150},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 200},
        {"label": "Stock Uom", "fieldname": "uom", "fieldtype": "Data", "width": 100},
        {"label": "Qty", "fieldname": "bom_qty", "fieldtype": "Float", "width": 120},
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
    production_item = filters.get('fg_item')
    from_date = filters.from_date
    to_date = filters.to_date

    if not from_date:
        return

    if not to_date:
        return
    
    from_date = get_datetime(filters.from_date + " 00:00:00")
    to_date = get_datetime(filters.to_date + " 23:59:59")

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

    filter_query = f"""
        SELECT 
            wo.production_item,
            wo.name,
            wo.bom_no,
            wo.qty,
            wo.status,
            wo.actual_start_date,
            wo.produced_qty
        FROM `tabWork Order` wo
        WHERE wo.docstatus = 1
        AND wo.status IN ('In Process', 'Completed')
        AND wo.actual_start_date BETWEEN '2025-10-01' AND '2025-10-31'
        AND wo.production_item IN (
            SELECT wo2.production_item
            FROM `tabWork Order` wo2
            JOIN `tabItem` i2 ON i2.name = wo2.production_item
            WHERE wo2.docstatus = 1
                AND wo2.status IN ('In Process', 'Completed')
                AND wo2.actual_start_date BETWEEN '2025-10-01' AND '2025-10-31'
                AND i2.item_group IN ('CAP', 'Trucker Cap', 'Stubby Cooler')
            GROUP BY wo2.production_item
            HAVING COUNT(DISTINCT wo2.name) = 2
        )
        group by bom_no 
        ORDER BY wo.production_item, wo.name
    """
    work_order_filters = frappe.db.sql(filter_query, as_dict=True)
    work_order_not_show = [r.name for r in work_order_filters]

    if work_order_not_show:
        condition = " AND wo.name NOT IN %(exclude)s"
        filters = {
            "from_date": from_date,
            "to_date": to_date,
            "production_item": production_item,
            "exclude": work_order_not_show
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
        {condition}
        AND i.item_group IN ('CAP', 'Trucker Cap', 'Stubby Cooler')
        ORDER BY wo.actual_start_date DESC
    """

    work_orders = frappe.db.sql(query, filters, as_dict=True)

    for wo in work_orders:
        root_item = wo.production_item
        bom_items = get_bom_items_as_dict(wo.bom_no, wo.qty)

        for item_code, item in bom_items.items():
            item_group = frappe.db.get_value("Item", item_code, "item_group")
            parent_qty = item.qty or 0
            if item_group == 'Semi-finished':
                bom_list = frappe.get_all(
                    "BOM",
                    filters={"item": item_code, "is_default": 1, "docstatus": 1},
                    fields=["name"],
                    limit=1
                )

                if bom_list:
                    bom = bom_list[0].name
                    sub_bom_items = get_bom_items_as_dict(bom, 1)
                    for item_code, item in sub_bom_items.items():
                        data.append({
                            "root_item": root_item,
                            "work_order": wo.name,
                            "actual_start_date": format_datetime(wo.actual_start_date, 'dd-MM-yyyy HH:mm'),
                            "item_code": item_code,
                            "uom": item.stock_uom,
                            'work_order_status': wo.status,
                            "bom": wo.bom_no,
                            "item_name": item.item_name,
                            "bom_qty": item.qty * parent_qty,
                            "remark": bom
                        })

            if item_group == 'Semi-finished':
                continue

            data.append({
                "root_item": root_item,
                "work_order": wo.name,
                "actual_start_date": format_datetime(wo.actual_start_date, 'dd-MM-yyyy HH:mm'),
                "item_code": item_code,
                "uom": item.stock_uom,
                'work_order_status': wo.status,
                "bom": wo.bom_no,
                "item_name": item.item_name,
                "bom_qty": item.qty,
                "remark": ""
            })

    return data


