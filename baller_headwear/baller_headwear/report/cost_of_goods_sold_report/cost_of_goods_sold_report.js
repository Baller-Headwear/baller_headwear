// Copyright (c) 2025, manan@unifyxperts.com and contributors
// For license information, please see license.txt

frappe.query_reports["Cost of Goods Sold Report"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "reqd": 1
        },
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 1
        }
    ],

    onload: function (report) {
        report.page.add_inner_button(__("Refresh Report"), function () {
            let filters = frappe.query_report.get_filter_values();

            if (!filters.from_date || !filters.to_date || !filters.company) {
                frappe.msgprint(__("Please select From Date, To Date, and Company before running the report."));
                return;
            }

            frappe.query_report.refresh();
        });
    }
};
