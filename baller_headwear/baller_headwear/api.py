import json
import frappe
from frappe.utils import get_datetime
from frappe import _, msgprint
from datetime import datetime, date 
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder.functions import Sum
from frappe.utils import cint, cstr, flt, get_link_to_form, getdate, new_line_sep, nowdate

from erpnext.buying.utils import check_on_hold_or_closed_status, validate_for_items
from erpnext.controllers.buying_controller import BuyingController
from erpnext.manufacturing.doctype.work_order.work_order import get_item_details
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.stock_balance import get_indented_qty, update_bin_qty

@frappe.whitelist()
def make_stock_entry(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		qty = (
			flt(flt(obj.stock_qty) - flt(obj.ordered_qty)) / target.conversion_factor
			if flt(obj.stock_qty) > flt(obj.ordered_qty)
			else 0
		)
		target.qty = qty
		target.transfer_qty = qty * obj.conversion_factor
		target.conversion_factor = obj.conversion_factor

		if (
			source_parent.material_request_type == "Material Transfer"
			or source_parent.material_request_type == "Customer Provided"
		):
			target.t_warehouse = obj.warehouse
		else:
			target.s_warehouse = obj.warehouse

		if source_parent.material_request_type == "Customer Provided":
			target.allow_zero_valuation_rate = 1

		if source_parent.material_request_type == "Material Transfer":
			target.s_warehouse = obj.from_warehouse

	def set_missing_values(source, target):
		# target.purpose = source.material_request_type
		target.purpose = "Material Transfer for Manufacture"
		target.from_warehouse = source.set_from_warehouse
		target.to_warehouse = source.set_warehouse

		if source.job_card:
			target.purpose = "Material Transfer for Manufacture"

		if source.material_request_type == "Customer Provided":
			target.purpose = "Material Receipt"

		target.set_transfer_qty()
		target.set_actual_qty()
		target.calculate_rate_and_amount(raise_error_if_no_rate=False)
		target.stock_entry_type = target.purpose
		target.set_job_card_data()

		if source.job_card:
			job_card_details = frappe.get_all(
				"Job Card", filters={"name": source.job_card}, fields=["bom_no", "for_quantity"]
			)

			if job_card_details and job_card_details[0]:
				target.bom_no = job_card_details[0].bom_no
				target.fg_completed_qty = job_card_details[0].for_quantity
				target.from_bom = 1

	doclist = get_mapped_doc(
		"Material Request",
		source_name,
		{
			"Material Request": {
				"doctype": "Stock Entry",
				"validation": {
					"docstatus": ["=", 1],
					"material_request_type": [
						"in",
						["Material Transfer", "Material Issue", "Customer Provided"],
					],
				},
			},
			"Material Request Item": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"name": "material_request_item",
					"parent": "material_request",
					"uom": "stock_uom",
					"job_card_item": "job_card_item",
				},
				"postprocess": update_item,
				"condition": lambda doc: (
					flt(doc.ordered_qty, doc.precision("ordered_qty"))
					< flt(doc.stock_qty, doc.precision("ordered_qty"))
				),
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist

# @frappe.whitelist()
# def set_custom_id_fields_for_transaction_date(doc, method):

#     if doc.transaction_date:

#         transaction_date = datetime.strptime(doc.transaction_date, '%Y-%m-%d')

#         month = transaction_date.month
#         year = transaction_date.year
        

#         year_formatted = str(year)[-2:]  
#         month_formatted = f"{month:02d}" 
        

#         doc.custom_id_month = month_formatted
#         doc.custom_id_year = year_formatted

@frappe.whitelist()
def set_custom_id_fields_for_transaction_date(doc, method):
    if doc.transaction_date:
        if isinstance(doc.transaction_date, str):
            transaction_date = datetime.strptime(doc.transaction_date, '%Y-%m-%d')
        else:
            transaction_date = doc.transaction_date

        month = transaction_date.month
        year = transaction_date.year

        year_formatted = str(year)[-2:]  
        month_formatted = f"{month:02d}" 

        doc.custom_id_month = month_formatted
        doc.custom_id_year = year_formatted

# @frappe.whitelist()
# def set_custom_id_fields_for_posting_date(doc, method):

#     if doc.posting_date:

#         posting_date = datetime.strptime(doc.posting_date, '%Y-%m-%d')

#         month = posting_date.month
#         year = posting_date.year
        

#         year_formatted = str(year)[-2:]  
#         month_formatted = f"{month:02d}" 
        

#         doc.custom_id_month = month_formatted
#         doc.custom_id_year = year_formatted

@frappe.whitelist()
def set_custom_id_fields_for_posting_date(doc, method):

    if doc.posting_date:
        if isinstance(doc.posting_date, str):
            posting_date = datetime.strptime(doc.posting_date, '%Y-%m-%d')
        else:
            posting_date = doc.posting_date


        month = posting_date.month
        year = posting_date.year
        

        year_formatted = str(year)[-2:]  
        month_formatted = f"{month:02d}" 
        

        doc.custom_id_month = month_formatted
        doc.custom_id_year = year_formatted

def parse_date(date_string):
    try:
        return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S.%f')
    except ValueError:
        return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')


@frappe.whitelist() 
def set_custom_id_fields_for_work_order(doc, method):
    if doc.planned_start_date:
        planned_start_date = parse_date(doc.planned_start_date)

        month = planned_start_date.month
        year = planned_start_date.year

        year_formatted = str(year)[-2:]  
        month_formatted = f"{month:02d}" 

        doc.custom_id_month = month_formatted
        doc.custom_id_year = year_formatted


@frappe.whitelist()
def set_custom_id_fields_for_posting_date_jv(doc, method):
    company_settings = frappe.get_doc("Company Settings")
    if doc.posting_date:
        if isinstance(doc.posting_date, str):
            posting_date = datetime.strptime(doc.posting_date, '%Y-%m-%d').date()
        elif isinstance(doc.posting_date, datetime):  
            posting_date = doc.posting_date.date()
        elif isinstance(doc.posting_date, date):
            posting_date = doc.posting_date
        else:
            raise ValueError("Posting date is neither a string nor a datetime.date object.")

        posting_date = datetime.combine(posting_date, datetime.min.time())

        month = posting_date.month
        year = posting_date.year

        year_formatted = str(year)[-2:]  
        month_formatted = f"{month:02d}" 

        doc.custom_id_month = month_formatted
        doc.custom_id_year = year_formatted
        
        if doc.naming_series == "ACC-JV-2024-":
            doc.naming_series = "ACC-JV-2024-" 
        elif doc.company == company_settings.vietnam_company_name:
            doc.naming_series = ".{custom_abbr}.-JV-.{custom_id_year}.-.{custom_id_month}.-.####"
        else:
            doc.naming_series = "ACC-JV-.YYYY.-"
            
@frappe.whitelist()
def set_custom_id_fields_for_posting_date_payment_entry(doc, method):
    company_settings = frappe.get_doc("Company Settings")
    if doc.posting_date:

        posting_date = datetime.strptime(doc.posting_date, '%Y-%m-%d')

        month = posting_date.month
        year = posting_date.year
        

        year_formatted = str(year)[-2:]  
        month_formatted = f"{month:02d}" 
        

        doc.custom_id_month = month_formatted
        doc.custom_id_year = year_formatted

        if doc.naming_series == "ACC-PAY-2024-":
            doc.naming_series = "ACC-PAY-2024-" 
        elif doc.company == company_settings.vietnam_company_name:
            doc.naming_series = ".{custom_abbr}.-PAY-.{custom_id_year}.-.{custom_id_month}.-.####"
        else:
            doc.naming_series = "ACC-PAY-.YYYY.-"

@frappe.whitelist()
def set_custom_id_fields_for_asset(doc, method):
    company_settings = frappe.get_doc("Company Settings")

    if doc.purchase_date:

        purchase_date = datetime.strptime(doc.purchase_date, '%Y-%m-%d')

        month = purchase_date.month
        year = purchase_date.year
        

        year_formatted = str(year)[-2:]  
        month_formatted = f"{month:02d}" 
        

        doc.custom_id_month = month_formatted
        doc.custom_id_year = year_formatted

        if doc.naming_series == "ACC-ASS-2024-":
            doc.naming_series = "ACC-ASS-2024-" 
        elif doc.company == company_settings.vietnam_company_name:
            doc.naming_series = ".{custom_abbr}.-ASS-.{custom_id_year}.-.{custom_id_month}.-.####"
        else:
            doc.naming_series = "ACC-ASS-.YYYY.-"


@frappe.whitelist()
def get_item_image(item_code):
    image = frappe.db.get_value("Item", item_code, "image")
    return image

@frappe.whitelist()
def get_work_orders_for_cutting(from_date=None, to_date=None, item=None):
    filters = {
        "status": "Not Started"
    }

    if item:
        filters["production_item"] = item

    if from_date and to_date:
        from_datetime = get_datetime(from_date + " 00:00:00")
        to_datetime = get_datetime(to_date + " 23:59:59")
        filters["planned_start_date"] = ["between", [from_datetime, to_datetime]]

    if not item and not (from_date and to_date):
        return []

    work_orders = frappe.get_list(
        "Work Order",
        filters=filters,
        fields=["name"],
        order_by="planned_start_date asc"
    )

    result = []

    for wo in work_orders:
        work_order_doc = frappe.get_doc("Work Order", wo.name)
        for item in work_order_doc.required_items:
            item_doc = frappe.get_doc("Item", item.item_code)
            if item_doc.item_group == "Fabric":
                result.append({
                    "work_order": wo.name,
                    "item_fabric": item.item_code,
                    "qty": item.required_qty
                })

    return result

# @frappe.whitelist()
# def get_work_orders_for_cutting(from_date, to_date):
#     from_datetime = get_datetime(from_date + " 00:00:00")
#     to_datetime = get_datetime(to_date + " 23:59:59")

#     work_orders = frappe.get_list(
#         "Work Order",
#         filters={
#             "planned_start_date": ["between", [from_datetime, to_datetime]],
#             "status": "Not Started"
#         },
#         fields=["name"],
#         order_by="planned_start_date asc"
#     )

#     result = []

#     for wo in work_orders:
#         work_order_doc = frappe.get_doc("Work Order", wo.name)
#         for item in work_order_doc.required_items:
#             item_doc = frappe.get_doc("Item", item.item_code)
#             if item_doc.item_group == "Fabric":
#                 result.append({
#                     "work_order": wo.name,
#                     "item_fabric": item.item_code,
#                     "qty": item.required_qty
#                 })

#     return result


