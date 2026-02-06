import frappe
import json

def execute(filters=None):
    columns = get_columns()
    data = get_data_report(filters)
    return columns, data

def get_columns():
    return [
        {"label": "Quotation Number", "fieldname": "quotation", "fieldtype": "Link", "options": "Quotation", "width": 160},
        {"label": "Sales Order", "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 160},
        {"label": "Voucher Code", "fieldname": "voucher_code", "fieldtype": "Link", "options": "Sales Invoice", "width": 200},
        {"label": "Debit Amount", "fieldname": "debit_amount", "fieldtype": "Currency", "width": 160},
        {"label": "Credit Amount", "fieldname": "credit_amount", "fieldtype": "Currency", "width": 160},
        {"label": "Total Amount Adjustment", "fieldname": "amount_update", "fieldtype": "Currency", "width": 200},
        {"label": "Remark", "fieldname": "remark", "fieldtype": "Text", "width": 300}
    ]

def get_voucher_notes(filters):
    data = []
    credit_note_query = f"""
        SELECT
            si.name as code,
            si.customer AS customer,
            'Credit Note' AS credit_note,
            si.name AS note_number,
            0 AS debit_amount,
            si.grand_total AS amount,
            si.remarks AS remark,
            si.posting_date,
            si.is_debit_note,
            (
                SELECT MAX(sii.sales_order)
                FROM `tabSales Invoice Item` sii
                WHERE sii.parent = si.name
                AND sii.sales_order IS NOT NULL
            ) AS sales_order
        FROM `tabSales Invoice` si
        WHERE si.docstatus = 1
        AND (
                si.is_return = 1
                OR si.is_debit_note = 1
            )
        AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND si.customer = 'International Headwear Pty Ltd'
    """
    data = frappe.db.sql(credit_note_query, filters, as_dict=True)
    return data

def get_rate_change(data):
    data = json.loads(data or "{}")
    for field, old, new in data.get("changed", []):
        if field == "rate":
            return old, new

    return None, None

def get_data_report(filters):
    voucher_notes = get_voucher_notes(filters)

    data = []
    remark = ''
    for item in voucher_notes:
        sale_order = item.get("sales_order")
        amount_update = 0
        quotation = ''
        if sale_order:
            sale_order_items = frappe.db.get_all(
                "Sales Order Item",
                filters={"parent": sale_order},
                fields=[
                    "name",
                    "rate",
                    "qty",
                    "item_code",
                    "prevdoc_docname"
                ]
            )

            for sale_order_item in sale_order_items:
                if not quotation:
                    quotation = sale_order_item.get('prevdoc_docname')

                query = f"""
                    SELECT
                        docname,
                        MIN(creation) AS first_creation,
                        data
                    FROM `tabVersion`
                    WHERE ref_doctype = 'Sales Order Item'
                    AND JSON_EXTRACT(data, '$.changed') IS NOT NULL
                    AND JSON_SEARCH(data, 'one', 'rate') IS NOT NULL
                    AND docname IS NOT NULL
                    AND docname = %(docname)s
                """
                version = frappe.db.sql(query, {"docname": sale_order_item.get('name')}, as_dict=True)
                first_version = version[0] if version else None
                if first_version.get('data'):
                
                    old_rate, new_rate = get_rate_change(first_version.get('data'))
                    current_rate = sale_order_item.get('rate', 0)
                    if isinstance(current_rate, str):
                        current_rate = float(current_rate.replace(",", ""))

                    if isinstance(old_rate, str):
                        old_rate = float(old_rate.replace(",", ""))

                    balance = current_rate - old_rate
                    amount_update = amount_update + (balance * float(sale_order_item.get('qty')))
                    remark += (
                        f"{sale_order_item.get('item_code')}"
                        f" change from {old_rate} to {current_rate} <br>"
                    )

            

        if item.get('is_debit_note'):
            data.append({
                'quotation': quotation,
                'sales_order': item.get('sales_order', ''),
                'voucher_code': item.get('code', ''),
                'voucher_code_debit': item.get('code', ''),
                'voucher_type': 'Debit Note',
                'posting_date': item.get('posting_date', ''),
                'debit_amount': item.get('amount', 0),
                'amount_credit_note': 0,
                'amount_update': amount_update,
                'remark': remark
            })
        else:
            data.append({
                'quotation': quotation,
                'sales_order': item.get('sales_order', ''),
                'voucher_code': item.get('code', ''),
                'voucher_code_debit':'',
                'voucher_type': 'Credit Note',
                'posting_date': item.get('posting_date', ''),
                'amount_debit_note': 0,
                'credit_amount': item.get('amount', 0),
                'amount_update': amount_update,
                'remark': remark
            })

    return data

