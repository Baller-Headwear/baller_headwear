frappe.query_reports["Theoretical BOM Standard Report"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1)
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            default: frappe.datetime.get_today()
        },
        {
            "fieldname": "fg_item",
            "label": __("FG Item"),
            "fieldtype": "Link",
            "options": "Item"
        }
    ]
}
