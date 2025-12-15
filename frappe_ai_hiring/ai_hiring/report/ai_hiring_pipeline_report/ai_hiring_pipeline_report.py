# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

import frappe
from typing import List, Dict, Any


def execute(filters=None):
	"""
	AI Hiring Pipeline Report
	Shows comprehensive view of all candidates in the pipeline
	"""
	columns = get_columns()
	data = get_data(filters)
	
	return columns, data


def get_columns() -> List[Dict[str, Any]]:
	"""Define report columns"""
	
	return [
		{
			"fieldname": "applicant_name",
			"label": "Candidate Name",
			"fieldtype": "Link",
			"options": "Job Applicant",
			"width": 180
		},
		{
			"fieldname": "job_title",
			"label": "Position",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "application_date",
			"label": "Applied On",
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "status",
			"label": "Status",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "ai_parsed",
			"label": "Resume Parsed",
			"fieldtype": "Check",
			"width": 80
		},
		{
			"fieldname": "ai_decision",
			"label": "AI Decision",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "fit_score",
			"label": "Fit Score",
			"fieldtype": "Percent",
			"width": 80
		},
		{
			"fieldname": "questionnaire_score",
			"label": "Questionnaire",
			"fieldtype": "Percent",
			"width": 100
		},
		{
			"fieldname": "interview_status",
			"label": "Interview",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "ai_recommendation",
			"label": "AI Recommendation",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "interviewer_recommendation",
			"label": "Interviewer Recommendation",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "days_in_pipeline",
			"label": "Days in Pipeline",
			"fieldtype": "Int",
			"width": 100
		}
	]


def get_data(filters: Dict[str, Any]) -> List[List[Any]]:
	"""Get report data"""
	
	# Build filter conditions
	conditions = ["1=1"]
	
	if filters and filters.get("job_title"):
		conditions.append(f"ja.job_title = '{filters['job_title']}'")
	
	if filters and filters.get("status"):
		conditions.append(f"ja.status = '{filters['status']}'")
	
	if filters and filters.get("from_date"):
		conditions.append(f"ja.creation >= '{filters['from_date']}'")
	
	if filters and filters.get("to_date"):
		conditions.append(f"ja.creation <= '{filters['to_date']}'")
	
	where_clause = " AND ".join(conditions)
	
	# Main query
	query = f"""
		SELECT 
			ja.name as applicant_name,
			ja.job_title,
			ja.creation as application_date,
			ja.status,
			CASE WHEN acp.name IS NOT NULL THEN 1 ELSE 0 END as ai_parsed,
			asr.decision as ai_decision,
			asr.fit_score,
			aer.percentage_score as questionnaire_score,
			CASE 
				WHEN aib.name IS NOT NULL THEN 'Brief Ready'
				ELSE NULL
			END as interview_status,
			aib.hire_recommendation as ai_recommendation,
			aib.interviewer_rating as interviewer_recommendation,
			DATEDIFF(CURDATE(), ja.creation) as days_in_pipeline
		FROM `tabJob Applicant` ja
		LEFT JOIN `tabAI Candidate Profile` acp ON ja.name = acp.job_applicant
		LEFT JOIN `tabAI Shortlisting Result` asr ON ja.name = asr.job_applicant
		LEFT JOIN `tabAI Evaluation Result` aer ON ja.name = aer.job_applicant
		LEFT JOIN `tabAI Interview Brief` aib ON ja.name = aib.job_applicant
		WHERE {where_clause}
		ORDER BY ja.creation DESC
	"""
	
	data = frappe.db.sql(query, as_list=True)
	
	return data
