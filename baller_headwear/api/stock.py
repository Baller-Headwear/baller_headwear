import json
import frappe
from frappe.utils import get_datetime
from erpnext.stock.stock_ledger import get_previous_sle


@frappe.whitelist()
def get_stock_actual_qty(items):
    """
    Check actual stock at EXACT posting datetime (ERPNext core logic)
    """

    # 1️⃣ Parse input
    if isinstance(items, str):
        items = json.loads(items)

    results = []

    for item in items:
        item_code = item.get("item_code")
        warehouse = item.get("source_warehouse")
        required_qty = float(item.get("not_yet_issued") or 0)
        posting_time_raw = item.get("posting_time")

        # 2️⃣ Validate
        if not item_code or not warehouse or not posting_time_raw:
            results.append({
                "item_code": item_code,
                "warehouse": warehouse,
                "status": "ERROR",
                "message": "Missing item_code / warehouse / posting_time"
            })
            continue

        posting_dt = get_datetime(posting_time_raw)

        # 3️⃣ CORE ERPNext: get stock at that datetime
        sle = get_previous_sle({
            "item_code": item_code,
            "warehouse": warehouse,
            "posting_date": posting_dt.date(),
            "posting_time": posting_dt.time()
        })

        available_qty = sle.get("qty_after_transaction", 0) if sle else 0

        # 4️⃣ Compare
        if required_qty > available_qty:
            shortage = required_qty - available_qty
            results.append({
                "item_code": item_code,
                "warehouse": warehouse,
                "available_qty": available_qty,
                "required_qty": required_qty,
                "shortage_qty": shortage,
                "status": "INSUFFICIENT",
                "message": f"Insufficient stock (short {shortage})"
            })
        else:
            results.append({
                "item_code": item_code,
                "warehouse": warehouse,
                "available_qty": available_qty,
                "required_qty": required_qty,
                "shortage_qty": 0,
                "status": "OK",
                "message": "Sufficient stock"
            })

    return results
