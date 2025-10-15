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
            "fieldname": "fg_item",
            "label": __("FG Item"),
            "fieldtype": "Link",
            "options": "Item"
        }
    ],
    onload: function(report) {
        report.current_page = 1;
        report.page_length = 50;
        report.setup_paging_area = function() {
            let $paging = $(`
                <div class="list-paging-area level">
                    <button class="btn btn-default btn-sm btn-load-more">Load More</button>
                </div>
            `);
            report.$paging_area = $paging;
            $(report.page.wrapper).find(".report-result").append($paging);

            $paging.find(".btn-load-more").on("click", function () {
                report.current_page += 1;
                report.refresh();
            });
        };

        report.setup_paging_area();
    },
}
