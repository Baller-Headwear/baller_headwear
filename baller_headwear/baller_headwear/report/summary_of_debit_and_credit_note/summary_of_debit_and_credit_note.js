frappe.query_reports["Summary of Debit and Credit Note"] = {
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
    ]
}
