import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data_report(filters)
    return columns, data

def get_columns():
    return [
        {"label": "Voucher Code", "fieldname": "code", "fieldtype": "Data", "width": 200},
        {"label": "Voucher Type", "fieldname": "voucher_type", "fieldtype": "Data", "width": 200},
        {"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 180},
        {"label": "Remark", "fieldname": "remark", "fieldtype": "Data", "width": 200}
    ]

def get_debit_notes(filters):
    data = []
    debit_note_query = f"""
        SELECT
            je.name as code,
            jea.party AS customer,
            'Debit Note' AS note_type,
            je.name AS note_number,
            jea.debit AS amount,
            je.remark AS remark
        FROM `tabJournal Entry Account` jea
        JOIN `tabJournal Entry` je
            ON je.name = jea.parent
        WHERE je.docstatus = 1
        AND jea.party_type = 'Customer'
        AND jea.debit > 0
        AND jea.party = 'International Headwear Pty Ltd'
        AND je.posting_date BETWEEN %(from_date)s AND %(to_date)s
    """
    data = frappe.db.sql(debit_note_query, filters, as_dict=True)
    return data

def get_credit_notes(filters):
    data = []
    credit_note_query = f"""
        SELECT
            si.name as code,
            si.customer AS customer,
            'Credit Note' AS note_type,
            si.name AS note_number,
            0 AS debit_amount,
            si.base_grand_total AS amount,
            si.remarks AS remark,
            si.posting_date
        FROM `tabSales Invoice` si
        WHERE si.docstatus = 1
            AND si.is_return = 1
        AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND si.customer = 'International Headwear Pty Ltd'
    """
    data = frappe.db.sql(credit_note_query, filters, as_dict=True)
    return data

def get_data_report(filters):
    credit_notes = get_credit_notes(filters)
    debit_notes = get_debit_notes(filters)

    data = []

    for item in credit_notes:
        data.append({
            'code': item.get('code', ''),
            'voucher_type': item.get('note_type', ''),
            'amount': item.get('amount', 0),
            'remark': item.get('remark', '')
        })

    for item in debit_notes:
        data.append({
            'code': item.get('code', ''),
            'voucher_type': item.get('note_type', ''),
            'amount': item.get('amount', 0),
            'remark': item.get('remark', '')
        })

    return data

