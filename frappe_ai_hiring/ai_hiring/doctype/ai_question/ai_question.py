# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AIQuestion(Document):
	"""AI Question DocType (Child Table)"""
	
	def validate(self):
		"""Validate question data"""
		if self.weight and self.weight < 0:
			frappe.throw("Weight cannot be negative")
