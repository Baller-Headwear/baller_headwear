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
        },
        {
            "fieldname": "cost_center",
            "label": __("Cost Center"),
            "fieldtype": "Link",
            "options": "Cost Center",
            "reqd": 0,
            "get_query": function () {
                let company = frappe.query_report.get_filter_value("company");
                if (company) {
                    return {
                        filters: { company: company }
                    };
                }
            }
        }
    ],

    onload: function (report) {
        // Add Reset Button
        report.page.add_inner_button(__("Reset"), function () {
            // Clear all filter values
            frappe.query_report.filters.forEach(filter => {
                frappe.query_report.set_filter_value(filter.df.fieldname, null);
            });

            // Refresh report after clearing filters
            frappe.query_report.refresh();
        });
    }
};
