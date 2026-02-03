frappe.query_reports["Sales Price Audit Report"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            default: frappe.datetime.year_start()
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            default: frappe.datetime.get_today()
        }
        // {
        //     "fieldname": "sale_order",
        //     "label": __("Sales Order"),
        //     "fieldtype": "Link",
        //     "options": "Sales Order"
        // }
    ]
}
