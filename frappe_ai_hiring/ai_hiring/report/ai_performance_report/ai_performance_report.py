# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

import frappe
from typing import List, Dict, Any


def execute(filters=None):
	"""
	AI Performance Report
	Analyzes AI system accuracy and performance
	"""
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	
	return columns, data, None, chart


def get_columns() -> List[Dict[str, Any]]:
	"""Define report columns"""
	
	return [
		{
			"fieldname": "ai_decision",
			"label": "AI Decision",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "final_status",
			"label": "Final Outcome",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "count",
			"label": "Count",
			"fieldtype": "Int",
			"width": 80
		},
		{
			"fieldname": "avg_fit_score",
			"label": "Avg Fit Score",
			"fieldtype": "Percent",
			"width": 100
		},
		{
			"fieldname": "accuracy",
			"label": "Accuracy",
			"fieldtype": "Data",
			"width": 100
		}
	]


def get_data(filters: Dict[str, Any]) -> List[List[Any]]:
	"""Get report data"""
	
	# Build date filter
	date_condition = ""
	if filters and filters.get("from_date"):
		date_condition = f"AND asr.creation >= '{filters['from_date']}'"
	if filters and filters.get("to_date"):
		date_condition += f" AND asr.creation <= '{filters['to_date']}'"
	
	query = f"""
		SELECT 
			asr.decision as ai_decision,
			ja.status as final_status,
			COUNT(*) as count,
			AVG(asr.fit_score) as avg_fit_score,
			CASE 
				WHEN (asr.decision = 'Shortlist' AND ja.status = 'Accepted') OR 
					 (asr.decision = 'Reject' AND ja.status = 'Rejected')
				THEN 'Correct'
				WHEN ja.status IN ('Accepted', 'Rejected')
				THEN 'Incorrect'
				ELSE 'Pending'
			END as accuracy
		FROM `tabAI Shortlisting Result` asr
		JOIN `tabJob Applicant` ja ON asr.job_applicant = ja.name
		WHERE 1=1 {date_condition}
		GROUP BY asr.decision, ja.status
		ORDER BY asr.decision, ja.status
	"""
	
	data = frappe.db.sql(query, as_list=True)
	
	return data


def get_chart_data(data: List[List[Any]]) -> Dict[str, Any]:
	"""Generate chart data"""
	
	# Count correct vs incorrect predictions
	correct = sum([row[2] for row in data if row[4] == "Correct"])
	incorrect = sum([row[2] for row in data if row[4] == "Incorrect"])
	pending = sum([row[2] for row in data if row[4] == "Pending"])
	
	return {
		"data": {
			"labels": ["Correct Predictions", "Incorrect Predictions", "Pending"],
			"datasets": [
				{
					"name": "AI Performance",
					"values": [correct, incorrect, pending]
				}
			]
		},
		"type": "pie",
		"colors": ["#28a745", "#dc3545", "#ffc107"]
	}
