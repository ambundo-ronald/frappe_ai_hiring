import os
from typing import Any, Optional

import frappe


RESUME_FIELD_CANDIDATES = ("resume_attachment", "resume", "resume_file", "attach_resume")
JOB_OPENING_FIELD_CANDIDATES = ("job_title", "job_opening")
EMAIL_FIELD_CANDIDATES = ("email_id", "email")
PHONE_FIELD_CANDIDATES = ("phone", "phone_number", "mobile_no", "contact_number")
APPLICANT_LINK_FIELD_CANDIDATES = ("applicant", "job_applicant")


def has_field(doctype: str, fieldname: str) -> bool:
	"""Return true when a DocType has a field in the current HRMS schema."""
	return bool(frappe.get_meta(doctype).has_field(fieldname))


def get_first_field(doc: Any, fieldnames: tuple[str, ...]) -> Optional[str]:
	"""Return the first present field value from a document."""
	for fieldname in fieldnames:
		if hasattr(doc, fieldname):
			value = getattr(doc, fieldname)
			if value:
				return value
	return None


def set_first_available_field(doc: Any, fieldnames: tuple[str, ...], value: Any) -> Optional[str]:
	"""Set the first schema-backed empty field from the provided candidates."""
	for fieldname in fieldnames:
		if doc.meta.has_field(fieldname) and not getattr(doc, fieldname, None):
			setattr(doc, fieldname, value)
			return fieldname
	return None


def get_applicant_link_filter(doctype: str, job_applicant: str) -> dict:
	"""Return a filter for custom AI DocTypes that may use applicant or job_applicant."""
	for fieldname in APPLICANT_LINK_FIELD_CANDIDATES:
		if has_field(doctype, fieldname):
			return {fieldname: job_applicant}
	return {"applicant": job_applicant}


def get_job_opening_from_applicant(applicant: Any) -> Optional[str]:
	"""Get the linked Job Opening from a Job Applicant across HRMS versions."""
	if isinstance(applicant, str):
		applicant = frappe.get_doc("Job Applicant", applicant)

	job_opening = get_first_field(applicant, JOB_OPENING_FIELD_CANDIDATES)
	if job_opening and frappe.db.exists("Job Opening", job_opening):
		return job_opening

	if job_opening:
		return frappe.db.get_value("Job Opening", {"job_title": job_opening}, "name")

	return None


def get_job_title(job_opening: Optional[str] = None, applicant: Any = None) -> str:
	"""Return a display job title from a Job Opening or Job Applicant."""
	if job_opening and frappe.db.exists("Job Opening", job_opening):
		job = frappe.get_doc("Job Opening", job_opening)
		return getattr(job, "job_title", None) or getattr(job, "designation", None) or job.name

	if applicant:
		if isinstance(applicant, str):
			applicant = frappe.get_doc("Job Applicant", applicant)
		return get_first_field(applicant, JOB_OPENING_FIELD_CANDIDATES) or ""

	return ""


def get_resume_file_url(applicant: Any) -> Optional[str]:
	"""Find the applicant resume from schema fields or linked File attachments."""
	if isinstance(applicant, str):
		applicant = frappe.get_doc("Job Applicant", applicant)

	file_url = get_first_field(applicant, RESUME_FIELD_CANDIDATES)
	if file_url:
		return file_url

	files = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "Job Applicant", "attached_to_name": applicant.name},
		fields=["file_url", "file_name"],
		order_by="creation desc",
	)
	for file_doc in files:
		ext = os.path.splitext(file_doc.get("file_name") or file_doc.get("file_url") or "")[1].lower()
		if ext in (".pdf", ".docx", ".doc", ".txt"):
			return file_doc.get("file_url")

	return None


def attach_resume_to_applicant(applicant_name: str, file_url: str) -> Optional[str]:
	"""Persist resume against Job Applicant using the best field or File link."""
	applicant = frappe.get_doc("Job Applicant", applicant_name)
	fieldname = set_first_available_field(applicant, RESUME_FIELD_CANDIDATES, file_url)
	if fieldname:
		applicant.save(ignore_permissions=True)
		return fieldname

	file_doc = frappe.get_doc("File", {"file_url": file_url})
	file_doc.attached_to_doctype = "Job Applicant"
	file_doc.attached_to_name = applicant_name
	file_doc.save(ignore_permissions=True)
	return None


def build_job_applicant_doc(job_opening: str, applicant_name: str, resume_file_url: Optional[str] = None) -> dict:
	"""Build a Job Applicant payload using fields available in the installed HRMS schema."""
	job = frappe.get_doc("Job Opening", job_opening)
	payload = {
		"doctype": "Job Applicant",
		"applicant_name": applicant_name,
		"status": "Open",
	}

	if has_field("Job Applicant", "designation"):
		payload["designation"] = getattr(job, "designation", None) or getattr(job, "job_title", None)

	for fieldname in JOB_OPENING_FIELD_CANDIDATES:
		if has_field("Job Applicant", fieldname):
			payload[fieldname] = job_opening
			break

	if resume_file_url:
		for fieldname in RESUME_FIELD_CANDIDATES:
			if has_field("Job Applicant", fieldname):
				payload[fieldname] = resume_file_url
				break

	return payload
