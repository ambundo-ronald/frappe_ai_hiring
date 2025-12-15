# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

"""
AI Audit Log Report
Query and display all AI interactions
"""

import frappe


def execute(filters=None):
	"""Generate AI Audit Log report"""
	filters = filters or {}
	
	columns = [
		{
			"fieldname": "name",
			"label": "Log ID",
			"fieldtype": "Link",
			"options": "AI Audit Log",
			"width": 120,
		},
		{
			"fieldname": "timestamp",
			"label": "Timestamp",
			"fieldtype": "Datetime",
			"width": 150,
		},
		{
			"fieldname": "operation_type",
			"label": "Operation",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"fieldname": "applicant",
			"label": "Applicant",
			"fieldtype": "Link",
			"options": "Job Applicant",
			"width": 150,
		},
		{
			"fieldname": "job_opening",
			"label": "Job Opening",
			"fieldtype": "Link",
			"options": "Job Opening",
			"width": 150,
		},
		{
			"fieldname": "model_used",
			"label": "AI Model",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"fieldname": "status",
			"label": "Status",
			"fieldtype": "Select",
			"width": 100,
		},
		{
			"fieldname": "success",
			"label": "Success",
			"fieldtype": "Check",
			"width": 80,
		},
		{
			"fieldname": "execution_time_ms",
			"label": "Exec Time (ms)",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"fieldname": "user",
			"label": "User",
			"fieldtype": "Data",
			"width": 120,
		},
	]
	
	# Build query
	query = frappe.db.get_list(
		"AI Audit Log",
		filters=filters,
		fields=[
			"name",
			"timestamp",
			"operation_type",
			"applicant",
			"job_opening",
			"model_used",
			"status",
			"success",
			"execution_time_ms",
			"user",
		],
		order_by="timestamp desc",
		limit_page_length=500,
	)
	
	data = []
	for row in query:
		data.append([
			row.name,
			row.timestamp,
			row.operation_type,
			row.applicant or "",
			row.job_opening or "",
			row.model_used,
			row.status,
			row.success,
			row.execution_time_ms or 0,
			row.user,
		])
	
	return columns, data
