# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

"""
Process New Applicant Job
Triggered when a new Job Applicant is created or updated
"""

import frappe
from frappe_ai_hiring.ai_hiring.utils.audit_logger import AIAuditLogger


def enqueue_applicant_processing(doc, method=None):
	"""
	Enqueue background job to process new applicant
	Triggered on Job Applicant after_insert

	Args:
		doc: Job Applicant document
		method: Hook method name
	"""
	# Check if AI processing is enabled
	settings = frappe.get_cached_value(
		"AI Settings", "AI Settings", ["enable_ai_processing", "enable_auto_shortlisting"], as_dict=True
	)

	if not settings or not settings.get("enable_ai_processing"):
		return

	# Check if resume is attached
	if not doc.resume_attachment:
		frappe.logger("ai_hiring").info(
			f"Skipping AI processing for {doc.name} - no resume attached"
		)
		return

	# Enqueue processing job
	frappe.enqueue(
		method="frappe_ai_hiring.ai_hiring.jobs.process_new_applicant.process_applicant",
		queue="long",
		timeout=300,
		applicant_name=doc.name,
		job_opening=doc.job_title,
	)

	frappe.msgprint(
		f"AI processing queued for applicant {doc.applicant_name}",
		indicator="blue",
		alert=True,
	)


def on_applicant_update(doc, method=None):
	"""
	Handle Job Applicant updates
	Triggered on Job Applicant on_update

	Args:
		doc: Job Applicant document
		method: Hook method name
	"""
	# Check if resume was just added
	if doc.has_value_changed("resume_attachment") and doc.resume_attachment:
		enqueue_applicant_processing(doc, method)


def process_applicant(applicant_name: str, job_opening: str):
	"""
	Background job to process applicant
	This orchestrates the entire AI pipeline

	Args:
		applicant_name: Job Applicant name
		job_opening: Job Opening name
	"""
	try:
		frappe.logger("ai_hiring").info(f"Starting AI pipeline for applicant: {applicant_name}")

		# Step 1: Parse resume
		frappe.logger("ai_hiring").info(f"Step 1/5: Parsing resume for {applicant_name}")
		from frappe_ai_hiring.ai_hiring.services.resume_parser import create_candidate_profile

		candidate_profile_name = create_candidate_profile(applicant_name, job_opening)

		if not candidate_profile_name:
			raise Exception("Resume parsing failed")

		frappe.logger("ai_hiring").info(f"Resume parsed successfully: {candidate_profile_name}")

		# Step 2: Shortlist candidate
		frappe.logger("ai_hiring").info(f"Step 2/5: Evaluating candidate fit for {applicant_name}")
		from frappe_ai_hiring.ai_hiring.services.shortlisting_service import create_shortlisting_result

		shortlisting_result_name = create_shortlisting_result(applicant_name, job_opening)

		if not shortlisting_result_name:
			raise Exception("Shortlisting failed")

		shortlisting_result = frappe.get_doc("AI Shortlisting Result", shortlisting_result_name)
		decision = shortlisting_result.decision
		fit_score = shortlisting_result.fit_score

		frappe.logger("ai_hiring").info(
			f"Shortlisting complete: Decision={decision}, Score={fit_score}"
		)

		# Step 3: Update applicant status based on decision
		if decision == "Shortlist":
			status = "AI Shortlisted"
			notes = f"AI Shortlisted with fit score: {fit_score}%"
		elif decision == "Reject":
			status = "Rejected"
			notes = f"AI Rejected with fit score: {fit_score}%"
		else:  # Review
			status = "Open"
			notes = f"Flagged for manual review. Fit score: {fit_score}%"

		from frappe_ai_hiring.ai_hiring.utils.common import update_applicant_status

		update_applicant_status(applicant_name, status, notes)

		# Step 4: Generate questionnaire for shortlisted candidates
		settings = frappe.get_cached_value(
			"AI Settings",
			"AI Settings",
			["enable_questionnaire_generation", "auto_generate_questions"],
			as_dict=True,
		)

		if decision == "Shortlist" and settings.get("enable_questionnaire_generation"):
			try:
				frappe.logger("ai_hiring").info(
					f"Step 3/5: Generating screening questions for {applicant_name}"
				)
				from frappe_ai_hiring.ai_hiring.services.question_generator import (
					create_question_set,
				)

				# Get job description
				job_doc = frappe.get_doc("Job Opening", job_opening)
				job_description = job_doc.description or ""

				question_set_name = create_question_set(
					job_role=job_doc.job_title,
					job_description=job_description,
					difficulty_level="Medium",
					num_questions=15,
				)

				frappe.logger("ai_hiring").info(
					f"Question set created: {question_set_name}"
				)

				# Link question set to applicant (via comment for now)
				applicant = frappe.get_doc("Job Applicant", applicant_name)
				applicant.add_comment(
					"Comment",
					f"AI-generated question set ready: {question_set_name}",
				)

			except Exception as e:
				frappe.logger("ai_hiring").warning(
					f"Question generation failed for {applicant_name}: {str(e)}"
				)
				# Don't fail the entire pipeline for question generation errors

		# Step 5: Generate interview brief for highly qualified candidates
		if decision == "Shortlist" and fit_score >= 75:
			try:
				frappe.logger("ai_hiring").info(
					f"Step 4/5: Generating interview brief for {applicant_name}"
				)
				from frappe_ai_hiring.ai_hiring.services.interview_brief_service import (
					create_interview_brief,
				)

				brief_name = create_interview_brief(
					job_applicant=applicant_name, include_questionnaire=False
				)

				frappe.logger("ai_hiring").info(f"Interview brief created: {brief_name}")

				# Notify that brief is ready
				from frappe_ai_hiring.ai_hiring.utils.common import create_notification

				create_notification(
					doctype="Job Applicant",
					docname=applicant_name,
					subject=f"Interview Brief Ready: {applicant_name}",
					message=f"AI-generated interview brief is available. Fit Score: {fit_score}%",
				)

			except Exception as e:
				frappe.logger("ai_hiring").warning(
					f"Interview brief generation failed for {applicant_name}: {str(e)}"
				)
				# Don't fail the entire pipeline

		# Step 6: Final notification
		frappe.logger("ai_hiring").info(f"Step 5/5: Sending completion notification")
		from frappe_ai_hiring.ai_hiring.utils.common import create_notification

		notification_msg = f"""AI Processing Complete for {applicant_name}

Status: {status}
Fit Score: {fit_score}%
Decision: {decision}

Next Steps:
"""
		if decision == "Shortlist":
			notification_msg += "- Review the AI-generated interview brief\n"
			notification_msg += "- Send screening questionnaire to candidate\n"
			notification_msg += "- Schedule interview if questionnaire passes\n"
		elif decision == "Review":
			notification_msg += "- Manual review required\n"
			notification_msg += "- Check AI Shortlisting Result for details\n"
		else:
			notification_msg += "- Candidate did not meet minimum requirements\n"

		create_notification(
			doctype="Job Applicant",
			docname=applicant_name,
			subject=f"AI Processing Complete: {applicant_name}",
			message=notification_msg,
		)

		frappe.logger("ai_hiring").info(
			f"Successfully completed AI pipeline for: {applicant_name}"
		)
		frappe.db.commit()

	except Exception as e:
		error_msg = f"Failed to process applicant {applicant_name}: {str(e)}"
		frappe.logger("ai_hiring").error(error_msg)
		frappe.log_error(title=f"AI Processing Error: {applicant_name}", message=error_msg)

		AIAuditLogger.log_error(
			operation="applicant_processing",
			error_message=error_msg,
			metadata={"applicant": applicant_name, "job_opening": job_opening},
		)

		# Update applicant with error
		try:
			applicant = frappe.get_doc("Job Applicant", applicant_name)
			applicant.add_comment("Comment", f"⚠️ AI Processing Error: {str(e)}")
			applicant.save(ignore_permissions=True)
			frappe.db.commit()
		except:
			pass
