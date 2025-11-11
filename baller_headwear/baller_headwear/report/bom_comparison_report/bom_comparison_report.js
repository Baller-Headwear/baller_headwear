frappe.query_reports["BOM Comparison Report"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": ""
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": ""
        },
        {
        "fieldname": "filter_type",
        "label": __("Type Filter"),
        "fieldtype": "Select",
        "options": "\nRoot Item\nDetail",
        "default": "Root Item"
        },
        {
            "fieldname": "fg_item",
            "label": __("FG Item"),
            "fieldtype": "Link",
            "options": "Item"
        }
    ]
}
