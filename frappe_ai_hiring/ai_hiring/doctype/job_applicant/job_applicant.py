# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

"""
Job Applicant Extensions
Adds AI Hiring actions to Job Applicant doctype
"""

import frappe
import re
import html
from html.parser import HTMLParser
from frappe_ai_hiring.ai_hiring.utils.hrms_compat import (
	EMAIL_FIELD_CANDIDATES,
	get_first_field,
	get_job_opening_from_applicant,
	get_job_title,
)


class HTMLStripper(HTMLParser):
	"""Simple HTML tag stripper for Quill and standard HTML content."""
	def __init__(self):
		super().__init__()
		self.reset()
		self.strict = False
		self.convert_charrefs = True
		self.text = []
	
	def handle_data(self, data):
		if data.strip():  # Only append non-whitespace data
			self.text.append(data.strip())
	
	def get_data(self):
		return ' '.join(self.text)  # Join with spaces


def strip_html_tags(html_text: str) -> str:
	"""Remove HTML tags from text, returning plain text only.
	
	Handles:
	- Standard HTML tags
	- Quill Rich Text Editor markup
	- HTML entities (&amp;, &quot;, etc.)
	- Multiple nested styles and attributes
	- Empty spans and div wrappers
	"""
	if not html_text:
		return ""
	
	try:
		# Step 1: Use HTMLParser to extract text content
		stripper = HTMLStripper()
		stripper.feed(html_text)
		plain_text = stripper.get_data()
		
		# Step 2: Decode any remaining HTML entities
		plain_text = html.unescape(plain_text)
		
		# Step 3: Clean up whitespace
		plain_text = re.sub(r'\s+', ' ', plain_text).strip()
		
		return plain_text
	except Exception as e:
		# Fallback: use regex-based stripping if HTMLParser fails
		frappe.logger("ai_hiring").warn(f"HTMLParser failed, using regex fallback: {str(e)}")
		
		# Remove all HTML tags
		plain_text = re.sub(r'<[^>]+>', '', html_text)
		
		# Decode HTML entities
		plain_text = html.unescape(plain_text)
		
		# Clean up whitespace
		plain_text = re.sub(r'\s+', ' ', plain_text).strip()
		
		return plain_text


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
		stages = ["parsing", "shortlisting"]

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
		job_opening = get_job_opening_from_applicant(applicant)
		job_title = get_job_title(job_opening, applicant)

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
			{"job_role": job_title},
			"name",
			order_by="creation desc",
		)

		if not question_set:
			frappe.throw(
				f"No question set found for {job_title}. Please generate one first."
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
def generate_questions(job_applicant: str, difficulty: str = "Medium", num_questions: int = 15, personalized: int = 1):
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
		job_opening = get_job_opening_from_applicant(applicant)
		applicant_job_title = get_job_title(job_opening, applicant)

		if not applicant_job_title:
			frappe.throw("Job title is required to generate questions")

		# Fetch job opening description if available
		job_description = ""
		role_title = ""
		if job_opening:
			job_opening_doc = frappe.get_doc("Job Opening", job_opening)
			job_description = strip_html_tags(job_opening_doc.description or "")
			role_title = (
				getattr(job_opening_doc, "job_title", None)
				or getattr(job_opening_doc, "designation", None)
				or ""
			)
		
		# If no description found, try fetching recent openings by job title
		if not job_description or not job_description.strip():
			openings = frappe.get_all(
				"Job Opening",
				filters={"job_title": applicant_job_title},
				fields=["name", "description", "job_title"],
				order_by="creation desc",
				limit=5
			)
			for op in openings:
				if op.get("description") and op.get("description").strip():
					job_description = strip_html_tags(op.get("description")).strip()
					if op.get("job_title"):
						role_title = op.get("job_title").strip()
					break
		
		# Enforce mandatory job description
		if not job_description or not job_description.strip():
			frappe.throw("Job description is required (no Job Opening with description found for this job title)")

		from frappe_ai_hiring.ai_hiring.services.question_generator import create_question_set

		question_set_name = create_question_set(
			job_role=role_title or applicant_job_title,
			job_description=job_description,
			difficulty_level=difficulty,
			num_questions=num_questions,
			applicant_name=job_applicant if personalized else None,
		)

		# Inform via comment on applicant
		applicant.add_comment("Comment", f"Question set generated: {question_set_name}")

		frappe.msgprint(
			f"✅ Question set generated: {question_set_name}" + (" (personalized)" if personalized else ""),
			indicator="green",
			alert=True
		)
		return {"success": True, "question_set": question_set_name}

	except Exception as e:
		_safe_applicant = locals().get("applicant")
		_safe_job_title = locals().get("applicant_job_title") or (
			get_job_title(get_job_opening_from_applicant(_safe_applicant), _safe_applicant)
			if _safe_applicant
			else "<unknown>"
		)
		_safe_jd = locals().get("job_description", "Not provided")
		frappe.logger("ai_hiring").error(
			f"[GENERATE QUESTIONS] Applicant: {job_applicant}, Job Title: {_safe_job_title}, Job Description: {_safe_jd}"
		)
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
			email = get_first_field(applicant, EMAIL_FIELD_CANDIDATES) or "candidate"
			frappe.msgprint(
				f"✅ Rejection email sent to {email}", indicator="green", alert=True
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
