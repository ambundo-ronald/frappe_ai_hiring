# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

"""
Common Utility Functions
"""

import frappe
import json
from typing import Any, Dict, Optional
from frappe_ai_hiring.ai_hiring.utils.hrms_compat import get_resume_file_url


def get_job_description(job_opening: str) -> str:
	"""
	Get job description text from Job Opening

	Args:
		job_opening: Job Opening name

	Returns:
		Job description as string
	"""
	if not frappe.db.exists("Job Opening", job_opening):
		frappe.throw(f"Job Opening {job_opening} not found")

	job_doc = frappe.get_doc("Job Opening", job_opening)

	# Build comprehensive job description
	description_parts = []

	designation = getattr(job_doc, "designation", None) or getattr(job_doc, "job_title", None)
	if designation:
		description_parts.append(f"Position: {designation}")

	if job_doc.description:
		description_parts.append(f"Description:\n{job_doc.description}")

	# Add requirements if available (custom field)
	if hasattr(job_doc, "requirements") and job_doc.requirements:
		description_parts.append(f"Requirements:\n{job_doc.requirements}")

	# Add skills if available (custom field)
	if hasattr(job_doc, "skills_required") and job_doc.skills_required:
		description_parts.append(f"Skills Required:\n{job_doc.skills_required}")

	return "\n\n".join(description_parts)


def get_applicant_resume_text(applicant: str) -> Optional[str]:
	"""
	Get resume text from Job Applicant

	Args:
		applicant: Job Applicant name

	Returns:
		Resume text or None
	"""
	if not frappe.db.exists("Job Applicant", applicant):
		frappe.throw(f"Job Applicant {applicant} not found")

	applicant_doc = frappe.get_doc("Job Applicant", applicant)

	# Check if resume is attached
	file_url = get_resume_file_url(applicant_doc)
	if not file_url:
		return None

	# Get file content
	try:
		file_doc = frappe.get_doc("File", {"file_url": file_url})

		# For now, return file path - actual text extraction would use libraries
		# like PyPDF2, python-docx, etc.
		return f"Resume file: {file_doc.file_url}"

	except Exception as e:
		frappe.log_error(f"Failed to get resume: {str(e)}", "Get Applicant Resume")
		return None


def safe_json_loads(text: str, default: Any = None) -> Any:
	"""
	Safely load JSON with fallback

	Args:
		text: JSON string
		default: Default value if parsing fails

	Returns:
		Parsed JSON or default value
	"""
	try:
		return json.loads(text)
	except (json.JSONDecodeError, TypeError):
		return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
	"""
	Safely dump JSON with fallback

	Args:
		obj: Object to serialize
		default: Default value if serialization fails

	Returns:
		JSON string or default value
	"""
	try:
		return json.dumps(obj, indent=2, ensure_ascii=False)
	except (TypeError, ValueError):
		return default


def validate_json_schema(data: Dict[str, Any], required_fields: list) -> bool:
	"""
	Validate that JSON data has required fields

	Args:
		data: Data dictionary
		required_fields: List of required field names

	Returns:
		True if valid, raises exception otherwise
	"""
	missing_fields = [field for field in required_fields if field not in data]

	if missing_fields:
		frappe.throw(f"Missing required fields: {', '.join(missing_fields)}")

	return True


def get_pipeline_state_order() -> list:
	"""
	Get ordered list of pipeline states

	Returns:
		List of state names in order
	"""
	return [
		"Applied",
		"AI Parsed",
		"AI Shortlisted",
		"Questionnaire Sent",
		"Questionnaire Passed",
		"Interview Scheduled",
		"Interview Completed",
		"Offer",
		"Rejected",
	]


def update_applicant_status(applicant: str, status: str, notes: Optional[str] = None):
	"""
	Update Job Applicant status

	Args:
		applicant: Job Applicant name
		status: New status
		notes: Optional notes to add
	"""
	try:
		doc = frappe.get_doc("Job Applicant", applicant)
		doc.status = status

		if notes:
			doc.add_comment("Comment", notes)

		doc.save(ignore_permissions=True)
		frappe.db.commit()

	except Exception as e:
		frappe.log_error(f"Failed to update applicant status: {str(e)}", "Update Applicant Status")
		raise


def create_notification(
	doctype: str,
	docname: str,
	subject: str,
	message: str,
	users: Optional[list] = None,
):
	"""
	Create notification for users

	Args:
		doctype: Reference DocType
		docname: Reference document name
		subject: Notification subject
		message: Notification message
		users: List of users to notify (defaults to HR Managers)
	"""
	try:
		if not users:
			# Get all HR Managers
			users = frappe.get_all(
				"Has Role",
				filters={"role": "HR Manager", "parenttype": "User"},
				fields=["parent"],
				pluck="parent",
			)

		for user in users:
			frappe.get_doc(
				{
					"doctype": "Notification Log",
					"subject": subject,
					"email_content": message,
					"for_user": user,
					"document_type": doctype,
					"document_name": docname,
					"type": "Alert",
				}
			).insert(ignore_permissions=True)

		frappe.db.commit()

	except Exception as e:
		frappe.log_error(f"Failed to create notification: {str(e)}", "Create Notification")
