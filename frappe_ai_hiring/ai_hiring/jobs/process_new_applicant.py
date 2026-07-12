# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

"""
Process New Applicant Job
Triggered when a new Job Applicant is created or updated
"""

import frappe
from frappe_ai_hiring.ai_hiring.utils.audit_logger import AIAuditLogger
from frappe_ai_hiring.ai_hiring.utils.hrms_compat import (
	get_job_opening_from_applicant,
	get_resume_file_url,
)
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

		if getattr(getattr(doc, "flags", None), "skip_ai_hiring_auto_enqueue", False):
			return
		
		frappe.logger("ai_hiring").error(f"[ENQUEUE] Processing triggered for applicant: {doc.name}")
		
		# Check if AI processing is enabled
		settings = frappe.get_cached_value(
			"AI Settings", "AI Settings", ["enable_ai_processing", "enable_auto_shortlisting"], as_dict=True
		)

		if not settings or not settings.get("enable_ai_processing"):
			frappe.logger("ai_hiring").error(f"[ENQUEUE] Skipping AI processing for {doc.name} - AI processing disabled in settings")
			return

		resume_file_url = get_resume_file_url(doc)
		if not resume_file_url:
			frappe.logger("ai_hiring").error(f"[ENQUEUE] Skipping AI processing for {doc.name} - no resume attached")
			return

		job_opening = get_job_opening_from_applicant(doc)
		if not job_opening:
			frappe.logger("ai_hiring").error(f"[ENQUEUE] Skipping AI processing for {doc.name} - no job opening found")
			return

		# Check if already processing or completed
		# existing_log = frappe.db.get_value(
		# 	"AI Audit Log",
		# 	{"reference_doctype": "Job Applicant", "reference_name": doc.name, "operation_type": "Resume Parsing"},
		# 	"name",
		# 	order_by="timestamp desc",
		# )

		# Get delay setting
		delay_seconds = frappe.db.get_value(
			"AI Settings",
			"AI Settings",
			"applicant_processing_delay_seconds"
		) or 5
		
		# Create unique job name with timestamp
		job_id = f"ai_processing_{doc.name}_{int(time.time())}"
		
		# Enqueue processing job with delay to allow file to be fully committed
		result = frappe.enqueue(
			method="frappe_ai_hiring.ai_hiring.jobs.process_new_applicant.process_applicant",
			queue="long",
			timeout=300,
			job_name=job_id,
			applicant_name=doc.name,
			job_opening=job_opening,
			enqueue_after_commit=True,  # Wait for DB commit before queuing
			is_async=True,
		)

		frappe.logger("ai_hiring").error(f"[ENQUEUE] Job enqueued successfully. Job ID: {job_id}")

	except Exception as e:
		try:
			if isinstance(doc, str):
				applicant_id = doc
			else:
				applicant_id = getattr(doc, 'name', 'unknown')
		except:
			applicant_id = 'unknown'
		frappe.logger("ai_hiring").error(f"[ENQUEUE] Error in enqueue_applicant_processing for {applicant_id}: {str(e)}")
		frappe.logger("ai_hiring").error(f"[ENQUEUE] Traceback: {frappe.get_traceback()}")
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
		frappe.logger("ai_hiring").error(f"[PROCESS] ===== JOB STARTED ===== Applicant: {applicant_name}")

		# Step 1: Parse resume
		from frappe_ai_hiring.ai_hiring.services.resume_parser import create_candidate_profile

		candidate_profile_name = create_candidate_profile(applicant_name, job_opening)

		if not candidate_profile_name:
			raise Exception("Resume parsing failed")

		# Step 2: Shortlist candidate
		from frappe_ai_hiring.ai_hiring.services.shortlisting_service import create_shortlisting_result

		shortlisting_result_name = create_shortlisting_result(applicant_name, job_opening)

		if not shortlisting_result_name:
			raise Exception("Shortlisting failed")

		shortlisting_result = frappe.get_doc("AI Shortlisting Result", shortlisting_result_name)
		fit_score = shortlisting_result.fit_score
		threshold_met = bool(shortlisting_result.threshold_met)

		# Step 3: Update applicant status based on the HR-configured threshold
		if threshold_met:
			status = "AI Shortlisted"
			notes = f"AI Shortlisted with fit score: {fit_score}%"
		else:
			status = "Rejected"
			notes = f"AI Rejected with fit score: {fit_score}%"

		from frappe_ai_hiring.ai_hiring.utils.common import update_applicant_status

		update_applicant_status(applicant_name, status, notes)

		if not threshold_met:
			from frappe_ai_hiring.ai_hiring.utils.notifications import NotificationManager

			email_sent = NotificationManager.send_candidate_notification(
				job_applicant=applicant_name,
				notification_type="rejection_notice",
			)
			applicant = frappe.get_doc("Job Applicant", applicant_name)
			comment = "Automatic rejection email sent." if email_sent else "Automatic rejection email could not be sent."
			applicant.add_comment("Comment", comment)
			applicant.save(ignore_permissions=True)
		else:
			from frappe_ai_hiring.ai_hiring.utils.notifications import NotificationManager

			NotificationManager.send_hr_notification(
				job_applicant=applicant_name,
				notification_type="candidate_shortlisted",
				additional_data={"fit_score": fit_score},
			)

		# Stop the automated pipeline here (no auto question generation)
		frappe.logger("ai_hiring").error(
			f"[PROCESS] ===== JOB COMPLETED ===== Applicant: {applicant_name}, Status: {status}, Score: {fit_score}%"
		)
		frappe.db.commit()

	except Exception as e:
		error_msg = f"Failed to process applicant {applicant_name}: {str(e)}"
		frappe.logger("ai_hiring").error(f"[PROCESS] ===== JOB FAILED =====")
		frappe.logger("ai_hiring").error(f"[PROCESS] Applicant: {applicant_name}")
		frappe.logger("ai_hiring").error(f"[PROCESS] Error Message: {error_msg}")
		frappe.logger("ai_hiring").error(f"[PROCESS] Traceback: {frappe.get_traceback()}")
		frappe.log_error(title=f"AI Processing Error: {applicant_name}", message=error_msg)

		AIAuditLogger.log_error(
			operation="Other",
			error_message=error_msg,
			metadata={"doctype": "Job Applicant", "docname": applicant_name, "job_opening": job_opening},
		)

		# Update applicant with error
		try:
			applicant = frappe.get_doc("Job Applicant", applicant_name)
			applicant.add_comment("Comment", f"⚠️ AI Processing Error: {str(e)}")
			applicant.save(ignore_permissions=True)
			frappe.db.commit()
		except:
			pass
