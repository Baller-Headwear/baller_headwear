import frappe

def set_workstation_from_production_plan(doc, method=None):
    if not doc.production_plan:
        return

    custom_work_station = None
    pp = frappe.get_doc("Production Plan", doc.production_plan)

    production_plan_item = getattr(doc, "production_plan_item", None)
    production_plan_sub_assembly_item = getattr(doc, "production_plan_sub_assembly_item", None)
    if production_plan_item:
        for row in pp.po_items:
            if row.name == production_plan_item:
                custom_work_station = row.get("custom_work_station")
                print(custom_work_station)
                break

    if not custom_work_station and production_plan_sub_assembly_item:
        for row in pp.sub_assembly_items:
            if row.name == production_plan_sub_assembly_item:
                custom_work_station = row.get("custom_work_station")
                break

    if not custom_work_station:
        return

    for op in doc.operations or []:
        if op.operation == "Assembly Line":
            op.workstation = custom_work_station