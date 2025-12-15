"""
Frappe AI Hiring Desktop Configuration
"""

from frappe import _


def get_data():
	return [
		{
			"module_name": "AI Hiring",
			"color": "blue",
			"icon": "octicon octicon-robot",
			"type": "module",
			"label": _("AI Hiring"),
			"description": _("AI-Driven Hiring Automation System"),
		}
	]
