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


@frappe.whitelist()
def generate_questions(job_applicant: str, difficulty: str = "Medium", num_questions: int = 15):
	"""
	Manually generate screening questions for the applicant's job role.

	Args:
		job_applicant: Job Applicant name
		difficulty: Difficulty level (Easy/Medium/Hard)
		num_questions: Number of questions to generate

	Returns:
		Dict with created question_set name
	"""
	if not frappe.has_permission("Job Applicant", "write", job_applicant):
		frappe.throw("Insufficient permissions")

	try:
		applicant = frappe.get_doc("Job Applicant", job_applicant)

		if not applicant.job_title:
			frappe.throw("Job title is required to generate questions")

		# Fetch job opening description if available
		job_description = ""
		if applicant.job_title:
			job_opening_name = frappe.db.get_value(
				"Job Opening", {"job_title": applicant.job_title}, "name", order_by="creation desc"
			)
			if job_opening_name:
				job_opening = frappe.get_doc("Job Opening", job_opening_name)
				job_description = job_opening.description or ""

		from frappe_ai_hiring.ai_hiring.services.question_generator import create_question_set

		question_set_name = create_question_set(
			job_role=applicant.job_title,
			job_description=job_description,
			difficulty_level=difficulty,
			num_questions=num_questions,
		)

		# Inform via comment on applicant
		applicant.add_comment("Comment", f"Question set generated: {question_set_name}")

		frappe.msgprint(
			f"✅ Question set generated: {question_set_name}", indicator="green", alert=True
		)
		return {"success": True, "question_set": question_set_name}

	except Exception as e:
		frappe.throw(f"Failed to generate questions: {str(e)}")


@frappe.whitelist()
def send_rejection_email(job_applicant: str):
	"""
	Send a rejection email to the candidate (manual action).

	Args:
		job_applicant: Job Applicant name

	Returns:
		Dict with success flag
	"""
	if not frappe.has_permission("Job Applicant", "write", job_applicant):
		frappe.throw("Insufficient permissions")

	try:
		applicant = frappe.get_doc("Job Applicant", job_applicant)
		from frappe_ai_hiring.ai_hiring.utils.notifications import NotificationManager

		success = NotificationManager.send_candidate_notification(
			job_applicant=job_applicant,
			notification_type="rejection_notice",
		)

		if success:
			frappe.msgprint(
				f"✅ Rejection email sent to {applicant.email_id}", indicator="green", alert=True
			)
			return {"success": True}
		else:
			frappe.throw("Failed to send rejection email")

	except Exception as e:
		frappe.throw(f"Failed to send rejection email: {str(e)}")


@frappe.whitelist()
def process_candidate(job_applicant: str):
	"""
	Queue AI processing for a Job Applicant (manual trigger from UI).

	Args:
		job_applicant: Job Applicant name

	Returns:
		Dict with queued flag
	"""
	if not frappe.has_permission("Job Applicant", "write", job_applicant):
		frappe.throw("Insufficient permissions")

	from frappe_ai_hiring.ai_hiring.jobs.process_new_applicant import enqueue_applicant_processing

	try:
		enqueue_applicant_processing(job_applicant)
		frappe.msgprint(
			f"✅ Candidate processing queued for {job_applicant}", indicator="green", alert=True
		)
		return {"queued": True}
	except Exception as e:
		frappe.throw(f"Failed to queue processing: {str(e)}")
