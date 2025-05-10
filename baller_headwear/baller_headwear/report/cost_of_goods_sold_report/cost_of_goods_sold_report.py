import frappe

def execute(filters=None):
    if not filters:
        filters = {}

    # Validate required filters
    if not filters.get("from_date") or not filters.get("to_date") or not filters.get("company"):
        frappe.throw("Please select From Date, To Date, and Company.")

    cost_accounts = get_cost_accounts()

    # Get total cost per category
    total_costs = {key: get_total_cost(accounts, filters) for key, accounts in cost_accounts.items()}

    # Fetch item-wise sales data
    sales_data = frappe.db.sql("""
        SELECT sii.item_code, SUM(sii.qty) AS total_qty
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON sii.parent = si.name
        WHERE si.company = %(company)s AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY sii.item_code
    """, filters, as_dict=True)

    total_qty_all_items = sum(item["total_qty"] for item in sales_data) or 1  # Avoid division by zero

    data = []
    total_summary = {key: 0 for key in total_costs}
    total_summary["total_qty"] = 0
    total_summary["total"] = 0

    for item in sales_data:
        row = {"item_code": item["item_code"], "total_qty": item["total_qty"]}

        row_total = 0
        for key, total_cost in total_costs.items():
            allocated_cost = (item["total_qty"] / total_qty_all_items) * total_cost
            row[key] = allocated_cost
            row_total += allocated_cost
            total_summary[key] += allocated_cost  # Accumulate totals

        row["total"] = row_total
        row["cost_of_goods"] = row_total / item["total_qty"] if item["total_qty"] else 0  # Avoid division by zero

        total_summary["total_qty"] += item["total_qty"]
        total_summary["total"] += row_total

        data.append(row)

    # Append total row
    total_summary["item_code"] = "Total"
    total_summary["cost_of_goods"] = total_summary["total"] / total_summary["total_qty"] if total_summary["total_qty"] else 0
    data.append(total_summary)

    # Define report columns
    columns = [
        {"fieldname": "item_code", "label": "Item Code", "fieldtype": "Data", "width": 200},
        {"fieldname": "direct_material", "label": "Direct Material", "fieldtype": "Currency", "width": 150},
        {"fieldname": "labour_cost", "label": "Labour Cost", "fieldtype": "Currency", "width": 150},
        {"fieldname": "machinery_depreciation", "label": "Machinery Depreciation", "fieldtype": "Currency", "width": 150},
        {"fieldname": "factory_rental_cost", "label": "Factory Rental Cost", "fieldtype": "Currency", "width": 150},
        {"fieldname": "production_tool_cost", "label": "Production Tool Cost", "fieldtype": "Currency", "width": 150},
        {"fieldname": "custom_and_shipping", "label": "Custom and Shipping", "fieldtype": "Currency", "width": 150},
        {"fieldname": "material_cost", "label": "Material Cost", "fieldtype": "Currency", "width": 150},
        {"fieldname": "factory_staff_cost", "label": "Factory Staff Cost", "fieldtype": "Currency", "width": 150},
        {"fieldname": "other_costs", "label": "Other Expenses", "fieldtype": "Currency", "width": 150},
        {"fieldname": "total", "label": "Total", "fieldtype": "Currency", "width": 150},
        {"fieldname": "total_qty", "label": "Finished Goods Qty", "fieldtype": "Float", "width": 150},
        {"fieldname": "cost_of_goods", "label": "Cost of Production", "fieldtype": "Currency", "width": 150}
    ]

    return columns, data


def get_total_cost(accounts, filters):
    """Fetch total cost including child accounts and applying cost center filter if selected."""
    cost_center_condition = ""
    params = {
        "company": filters["company"],
        "from_date": filters["from_date"],
        "to_date": filters["to_date"]
    }

    # Fetch child accounts for the selected parent accounts
    expanded_accounts = get_child_accounts(accounts)
    params["accounts"] = tuple(expanded_accounts)

    # Apply cost center filter only if it's selected
    if filters.get("cost_center"):
        cost_center_condition = "AND cost_center = %(cost_center)s"
        params["cost_center"] = filters["cost_center"]

    return frappe.db.sql(f"""
        SELECT COALESCE(SUM(debit_in_account_currency), 0)
        FROM `tabGL Entry`
        WHERE account IN %(accounts)s
        AND company = %(company)s
        AND posting_date BETWEEN %(from_date)s AND %(to_date)s
        {cost_center_condition}
    """, params, as_list=True)[0][0] or 0


def get_child_accounts(accounts):
    """Fetch all child accounts for the given list of accounts."""
    expanded_accounts = list(accounts)  # Start with given accounts

    for account in accounts:
        child_accounts = frappe.db.sql("""
            SELECT name FROM `tabAccount`
            WHERE parent_account = %s
        """, (account,), as_list=True)

        for child in child_accounts:
            expanded_accounts.append(child[0])
            expanded_accounts.extend(get_child_accounts([child[0]]))  # Recursively fetch deeper children

    return expanded_accounts


def get_cost_accounts():
    """Fetch accounts dynamically from Cogs Settings child tables."""
    cogs_settings_doc = frappe.get_doc("Cogs Settings")

    cost_accounts = {}

    for child in cogs_settings_doc.get("direct_material"):
        cost_accounts.setdefault("direct_material", []).append(child.account_name)

    for child in cogs_settings_doc.get("machinery_depreciation"):
        cost_accounts.setdefault("machinery_depreciation", []).append(child.account_name)

    for child in cogs_settings_doc.get("production_tool_cost"):
        cost_accounts.setdefault("production_tool_cost", []).append(child.account_name)

    for child in cogs_settings_doc.get("material_cost"):
        cost_accounts.setdefault("material_cost", []).append(child.account_name)

    for child in cogs_settings_doc.get("factory_staff_cost"):
        cost_accounts.setdefault("factory_staff_cost", []).append(child.account_name)

    for child in cogs_settings_doc.get("other_expenses"):
        cost_accounts.setdefault("other_costs", []).append(child.account_name)

    for child in cogs_settings_doc.get("labour_cost"):
        cost_accounts.setdefault("labour_cost", []).append(child.account_name)

    for child in cogs_settings_doc.get("factory_rental_cost"):
        cost_accounts.setdefault("factory_rental_cost", []).append(child.account_name)

    for child in cogs_settings_doc.get("customs_and_shipping"):
        cost_accounts.setdefault("custom_and_shipping", []).append(child.account_name)

    return cost_accounts
