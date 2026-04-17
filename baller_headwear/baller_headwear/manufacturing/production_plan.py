import frappe


def collect_sub_assembly_boms(parent_bom, result):
    bom_items = frappe.get_all(
        "BOM Item",
        filters={"parent": parent_bom},
        fields=["item_code", "bom_no"]
    )

    for item in bom_items:
        child_item_code = item.get("item_code")
        child_bom_no = item.get("bom_no")

        if child_bom_no:
            result.append({
                "item_code": child_item_code,
                "bom_no": child_bom_no
            })
            collect_sub_assembly_boms(child_bom_no, result)


def before_submit_production_plan(doc, method):
    sub_map = {}

    for row in doc.po_items:
        root_bom_no = row.get("bom_no")
        work_station = row.get("custom_work_station")

        if not root_bom_no or not work_station:
            print('1111111')
            continue

        result = []
        collect_sub_assembly_boms(root_bom_no, result)

        for r in result:
            if r.get("bom_no"):
                sub_map[r.get("bom_no")] = work_station
            if r.get("item_code"):
                sub_map[r.get("item_code")] = work_station

    for sub in doc.sub_assembly_items:
        sub_bom_no = sub.get("bom_no")
        sub_item_code = sub.get("sub_assembly_item_code")
        print(sub_map[sub_bom_no])
        if sub_bom_no in sub_map:
            sub.custom_work_station = sub_map[sub_bom_no]
        elif sub_item_code in sub_map:
            sub.custom_work_station = sub_map[sub_item_code]

    for item in doc.po_items:
        frappe.logger().info(f"PO Item workstation: {item.get('custom_work_station')}")