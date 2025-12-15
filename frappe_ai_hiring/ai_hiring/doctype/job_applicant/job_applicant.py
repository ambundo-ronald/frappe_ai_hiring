# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

"""
Job Applicant Extensions
Adds AI Hiring actions to Job Applicant doctype
"""

import frappe


@frappe.whitelist()
def reprocess_candidate(job_applicant: str, stages: list = None):
	"""
	Reprocess a job applicant through selected AI stages.

	Args:
		job_applicant: Job Applicant name
		stages: List of stages to reprocess (default: all)

	Returns:
		Result dictionary
	"""
	if not frappe.has_permission("Job Applicant", "write", job_applicant):
		frappe.throw("Insufficient permissions")

	if not stages:
		stages = ["parsing", "shortlisting", "interview_brief"]

	from frappe_ai_hiring.ai_hiring.utils.job_manager import reprocess_applicant

	try:
		result = reprocess_applicant(job_applicant, stages)
		frappe.msgprint(
			f"✅ Reprocessing queued for {len(result.get('reprocessed', []))} stage(s)",
			indicator="green",
			alert=True,
		)
		return result
	except Exception as e:
		frappe.throw(f"Reprocessing failed: {str(e)}")


@frappe.whitelist()
def send_questionnaire(job_applicant: str):
	"""
	Send screening questionnaire to shortlisted candidate.

	Args:
		job_applicant: Job Applicant name

	Returns:
		Result dictionary
	"""
	if not frappe.has_permission("Job Applicant", "write", job_applicant):
		frappe.throw("Insufficient permissions")

	try:
		applicant = frappe.get_doc("Job Applicant", job_applicant)

		# Check if candidate is shortlisted
		shortlisting = frappe.db.get_value(
			"AI Shortlisting Result",
			{"applicant": job_applicant},
			["decision", "fit_score"],
			as_dict=True,
		)

		if not shortlisting or shortlisting.decision != "Shortlist":
			frappe.throw(
				"Candidate must be shortlisted before sending questionnaire"
			)

		# Get or create question set
		question_set = frappe.db.get_value(
			"AI Question Set",
			{"job_role": applicant.job_title},
			"name",
			order_by="creation desc",
		)

		if not question_set:
			frappe.throw(
				f"No question set found for {applicant.job_title}. Please generate one first."
			)

		# Send notification
		from frappe_ai_hiring.ai_hiring.utils.notifications import NotificationManager

		success = NotificationManager.send_candidate_notification(
			job_applicant=job_applicant,
			notification_type="questionnaire_invitation",
			additional_data={
				"questionnaire_link": frappe.utils.get_url_to_form(
					"AI Question Set", question_set
				)
			},
		)

		if success:
			frappe.msgprint(
				f"✅ Questionnaire sent to {applicant.applicant_name}",
				indicator="green",
				alert=True,
			)
		else:
			frappe.throw("Failed to send questionnaire")

		return {"success": True, "question_set": question_set}

	except Exception as e:
		frappe.throw(f"Failed to send questionnaire: {str(e)}")


@frappe.whitelist()
def get_processing_status(job_applicant: str):
	"""
	Get AI processing status for job applicant.

	Args:
		job_applicant: Job Applicant name

	Returns:
		Status dictionary
	"""
	from frappe_ai_hiring.ai_hiring.utils.job_manager import get_applicant_processing_status

	return get_applicant_processing_status(job_applicant)
