import json
import frappe
from frappe.utils import get_datetime
from frappe import _, msgprint
from datetime import datetime, date 
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder.functions import Sum
from frappe.utils import cint, cstr, flt, get_link_to_form, getdate, new_line_sep, nowdate
from erpnext.manufacturing.doctype.job_card.job_card import make_material_request
from erpnext.buying.utils import check_on_hold_or_closed_status, validate_for_items
from erpnext.controllers.buying_controller import BuyingController
from erpnext.manufacturing.doctype.work_order.work_order import get_item_details
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.stock_balance import get_indented_qty, update_bin_qty
import sys
from frappe.integrations.utils import make_post_request
from frappe.integrations.utils import make_get_request
from frappe.utils import now_datetime
from datetime import datetime, timedelta
from frappe.utils import format_time
from openpyxl import load_workbook
import os
import re

auth_endpoint = 'http://14.241.121.152:8080/jwt-api-token-auth/'
transaction_endpoint = 'http://14.241.121.152:8080/iclock/api/transactions/'
username = 'ballerheadwear'
password = '2023/B@ller'
headers = {
    "Content-Type": "application/json"
}

def login_get_token():
    authParams = {
        'username': username,
        'password': password
    }
    try:
     response = make_post_request(url=auth_endpoint, json=authParams, headers=headers)
     return response['token']
    except Exception as e:
        frappe.log_error(
            title="Get Transaction Error",
            message=frappe.get_traceback()
        )
        print("ERROR:", str(e))
        return None 
        
def get_transaction_by_employee(jwt_token, params):
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": "JWT " + jwt_token
        }
        response = make_get_request(url=transaction_endpoint, params=params, headers=headers)
        print(params)
        return response.get('data', [])
    except Exception as e:
        frappe.log_error(
            title="Get Transaction Error",
            message=frappe.get_traceback()
        )
        return [] 

def create_employee_checkin(employee_code, employee_name, time, log_type, device_id=None):
    try:
        doc = frappe.db.sql(
            """
            SELECT name
            FROM `tabEmployee Checkin`
            WHERE employee = %s
              AND log_type = %s
              AND DATE(time) = DATE(%s)
            LIMIT 1
            """,
            (employee_code, log_type, time),
            as_dict=True
        )
    
        if doc:
            frappe.db.set_value(
                "Employee Checkin",
                doc[0].name,
                {
                    "time": time,
                    "device_id": device_id,
                    "employee_name": employee_name,
                    "offshift": 0,
                    "skip_auto_attendance": 1
                }
            )
            print("✅ UPDATED:")
        else:
            doc = frappe.get_doc({
                "doctype": "Employee Checkin",
                "employee": employee_code,
                "employee_name": employee_name,
                "time": time,
                "log_type": log_type,
                "device_id": device_id,
                "offshift": 0,
                "skip_auto_attendance": 1
            })
            doc.insert(ignore_permissions=True)
    except Exception as e:
        return None

def run(employees):
    jwt_token = login_get_token()
    end_date = frappe.utils.getdate(frappe.utils.today())
    start_date = frappe.utils.getdate("2026-01-01")
    for employee in employees:
        current_date = start_date
        while current_date <= end_date:
            print(current_date)
            process_date = current_date
            process_date_previous_shift = frappe.utils.add_to_date(current_date, days=-2)
            current_date = frappe.utils.add_to_date(current_date, days=1)
          
            params_shift = {
                "emp_code": employee.get('attendance_device_id'),
                "start_time": f"{process_date} 05:30",
                "end_time": f"{process_date} 21:00",
                "page_size": 2000
            }
            params_previous_shift = {
                "emp_code": employee.get('attendance_device_id'),
                "start_time":  f"{process_date_previous_shift} 21:30",
                "end_time": f"{process_date_previous_shift} 23:59",
                "page_size": 2000
            }

            transations_previous_shift = get_transaction_by_employee(jwt_token, params_previous_shift)
            transations = get_transaction_by_employee(jwt_token, params_shift)

            if not transations:
                continue

            for transaction in transations:
                emp_code = transaction['emp_code'] or ''
                if not emp_code:
                    continue
                
                current_employee = None
                for employee in employees:
                    if employee.get('attendance_device_id') == emp_code:
                        current_employee = employee
                        break

                if not current_employee:
                    continue
                
                employee_name = current_employee['employee_name'] or ''
                employee_code = current_employee['name'] or ''
                attendance_device_id = current_employee['attendance_device_id'] or ''
                record = None
                for row in transations_previous_shift:
                    if row.get("emp_code") == attendance_device_id:
                        record = row
                        create_employee_checkin(employee_code, employee_name, record['punch_time'], 'IN', device_id=None)
                        transations_previous_shift.remove(row)
                        break

                if record:
                    create_employee_checkin(employee_code, employee_name, transaction['punch_time'], 'OUT', device_id=None)
                    transations.remove(transaction)
                    continue

                records = sorted(
                    [row for row in transations if row.get("emp_code") == emp_code],
                    key=lambda x: x.get("punch_time")
                )
                if not records:
                    continue

                if len(records) > 1:
                    start_transaction = records[0]
                    end_transaction = records[-1]
                    create_employee_checkin(employee_code, employee_name, start_transaction['punch_time'], 'IN', device_id=None)
                    create_employee_checkin(employee_code, employee_name, end_transaction['punch_time'], 'OUT', device_id=None)
                else:
                    create_employee_checkin(employee_code, employee_name, transaction['punch_time'], 'IN', device_id=None)
