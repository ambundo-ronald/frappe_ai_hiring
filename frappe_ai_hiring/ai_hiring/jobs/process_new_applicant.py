# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

"""
Process New Applicant Job
Triggered when a new Job Applicant is created or updated
"""

import frappe
from frappe_ai_hiring.ai_hiring.utils.audit_logger import AIAuditLogger
import time


def enqueue_applicant_processing(doc=None, method=None):
	"""
	Enqueue background job to process new applicant
	Triggered on Job Applicant after_insert or called manually from UI

	Args:
		doc: Job Applicant document object or name (string)
		method: Hook method name (only for doc events)
	"""
	try:
		# Handle both doc object and doc name (from UI calls)
		if isinstance(doc, str):
			doc = frappe.get_doc("Job Applicant", doc)
		elif doc is None:
			# Called from UI with doc in session
			applicant_name = frappe.form_dict.get("doc")
			if not applicant_name:
				frappe.throw("Job Applicant name is required")
			doc = frappe.get_doc("Job Applicant", applicant_name)
		
		# Check if AI processing is enabled
		settings = frappe.get_cached_value(
			"AI Settings", "AI Settings", ["enable_ai_processing", "enable_auto_shortlisting"], as_dict=True
		)

		if not settings or not settings.get("enable_ai_processing"):
			frappe.logger("ai_hiring").info("AI processing is disabled in AI Settings")
			return

		# Check if resume is attached
		if not doc.resume_attachment:
			frappe.logger("ai_hiring").info(f"Skipping AI processing for {doc.name} - no resume attached")
			return

		# Check if already processing or completed
		existing_log = frappe.db.get_value(
			"AI Audit Log",
			{"reference_doctype": "Job Applicant", "reference_name": doc.name, "operation_type": "Resume Parsing"},
			"name",
			order_by="timestamp desc",
		)
		
		if existing_log:
			frappe.logger("ai_hiring").info(f"Job Applicant {doc.name} already processed. Skipping.")
			return

		# Enqueue processing job with delay to allow file to be fully committed
		# Delay helps ensure resume file is saved to disk before extraction
		# Default 5 second delay, configurable in AI Settings
		delay_seconds = frappe.db.get_value(
			"AI Settings",
			"AI Settings",
			"applicant_processing_delay_seconds"
		) or 5
		
		frappe.enqueue(
			method="frappe_ai_hiring.ai_hiring.jobs.process_new_applicant.process_applicant",
			queue="long",
			timeout=300,
			job_name=f"ai_processing_{doc.name}_{int(time.time())}",
			applicant_name=doc.name,
			job_opening=doc.job_title,
			enqueue_after_commit=True,  # Wait for DB commit before queuing
			is_async=True,
		)

		frappe.logger("ai_hiring").info(f"Queued AI processing for applicant {doc.name} (delay: {delay_seconds}s)")

	except Exception as e:
		frappe.logger("ai_hiring").error(f"Error in enqueue_applicant_processing: {str(e)}")
		# Don't throw - just log the error so webform submission doesn't fail


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

		# Stop the automated pipeline here (no auto question generation or emails)
		frappe.logger("ai_hiring").info(
			f"Automated pipeline halted after shortlisting for: {applicant_name}"
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
