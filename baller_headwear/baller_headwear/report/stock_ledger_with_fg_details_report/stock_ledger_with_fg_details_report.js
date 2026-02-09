frappe.query_reports["Stock Ledger with FG Details Report"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1)
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today()
        },
        {
            fieldname: "cost_subject",
            label: __("Cost subject"),
            fieldtype: "Link",
            options: "Item"
        },
        {
            fieldname: "warehouse",
            label: __("Warehouse"),
            fieldtype: "Link",
            options: "Warehouse"
        },
        {
            fieldtype: "Select",
            fieldname: "voucher_type",
            label: __("Voucher Type"),
            options: [
                "",
                'Material Transfer',
                "Material Transfer for Manufacture",
                "Material Issue",
                "Manufacture",
            ].join("\n")
        }
    ]
};
