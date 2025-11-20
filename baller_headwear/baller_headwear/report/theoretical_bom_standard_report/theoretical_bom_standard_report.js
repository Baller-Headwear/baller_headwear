frappe.query_reports["Theoretical BOM Standard Report"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            default: ""
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            default: ""
        },
        {
            "fieldname": "fg_item",
            "label": __("FG Item"),
            "fieldtype": "Link",
            "options": "Item"
        }
    ]
}
