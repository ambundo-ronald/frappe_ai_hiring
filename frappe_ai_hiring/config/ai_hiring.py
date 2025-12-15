"""
AI Hiring Module Configuration
"""

from frappe import _


def get_data():
	return [
		{
			"label": _("Configuration"),
			"items": [
				{
					"type": "doctype",
					"name": "AI Settings",
					"description": _("Configure AI/LLM provider settings"),
				},
			],
		},
		{
			"label": _("Candidate Processing"),
			"items": [
				{
					"type": "doctype",
					"name": "AI Candidate Profile",
					"description": _("AI-parsed candidate profiles"),
				},
				{
					"type": "doctype",
					"name": "AI Shortlisting Result",
					"description": _("Candidate shortlisting decisions"),
				},
			],
		},
		{
			"label": _("Questionnaires"),
			"items": [
				{
					"type": "doctype",
					"name": "AI Question Set",
					"description": _("Technical screening questions"),
				},
				{
					"type": "doctype",
					"name": "AI Evaluation Result",
					"description": _("Questionnaire evaluation results"),
				},
			],
		},
		{
			"label": _("Interview Support"),
			"items": [
				{
					"type": "doctype",
					"name": "AI Interview Brief",
					"description": _("Interviewer preparation briefs"),
				},
			],
		},
	]
