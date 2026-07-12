import os
from typing import Any

import frappe
from frappe_ai_hiring.ai_hiring.utils.hrms_compat import (
	attach_resume_to_applicant,
	build_job_applicant_doc,
)


def _as_list(value: Any) -> list:
	if isinstance(value, str):
		value = frappe.parse_json(value)
	return value if isinstance(value, list) else []


@frappe.whitelist()
def create_applicants_from_resumes(job_opening: str, file_urls: Any) -> dict:
	"""
	Create Job Applicant records from already-uploaded resume files.

	The standard Job Applicant after_insert hook queues AI parsing and shortlisting
	for each created applicant.
	"""
	if not frappe.has_permission("Job Applicant", "create"):
		frappe.throw("Insufficient permissions to create Job Applicants")

	if not frappe.db.exists("Job Opening", job_opening):
		frappe.throw(f"Job Opening not found: {job_opening}")

	files = _as_list(file_urls)
	if not files:
		frappe.throw("At least one resume file is required")

	results = {"created": [], "failed": []}

	for file_url in files:
		try:
			file_doc = frappe.get_doc("File", {"file_url": file_url})
			base_name = os.path.splitext(file_doc.file_name or os.path.basename(file_url))[0]

			applicant = frappe.get_doc(build_job_applicant_doc(job_opening, base_name or "Resume Applicant", file_url))
			applicant.flags.skip_ai_hiring_auto_enqueue = True
			applicant.insert()
			attach_resume_to_applicant(applicant.name, file_url)

			from frappe_ai_hiring.ai_hiring.jobs.process_new_applicant import enqueue_applicant_processing

			enqueue_applicant_processing(applicant.name)

			results["created"].append(
				{
					"job_applicant": applicant.name,
					"resume_attachment": file_url,
				}
			)
		except Exception as exc:
			results["failed"].append({"resume_attachment": file_url, "error": str(exc)})

	return {
		"success": len(results["created"]) > 0,
		"results": results,
	}
