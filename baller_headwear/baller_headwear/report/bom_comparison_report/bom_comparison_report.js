frappe.query_reports["BOM Comparison Report"] = {
    "filters": [
        // {
        //     "fieldname": "sales_invoice",
        //     "label": __("Sales Invoice"),
        //     "fieldtype": "Link",
        //     "options": "Sales Invoice"
        // },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today()
        },
        {
            "fieldname": "fg_item",
            "label": __("Item code"),
            "fieldtype": "Link",
            "options": "Item"
        }
    ]
}
