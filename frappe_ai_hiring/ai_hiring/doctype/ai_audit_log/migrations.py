# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

"""
AI Audit Log migrations and setup
"""

import frappe


def create_index_for_audit_logs():
	"""Create database index for efficient audit log queries"""
	frappe.db.create_index(
		"AI Audit Log",
		["applicant", "timestamp"],
	)
	frappe.db.create_index(
		"AI Audit Log",
		["operation_type", "timestamp"],
	)
