# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from typing import Dict, Any
from frappe_ai_hiring.ai_hiring.utils.hrms_compat import EMAIL_FIELD_CANDIDATES, get_first_field


class AIInterviewBrief(Document):
	"""AI Interview Brief DocType"""

	def validate(self):
		"""Validate interview brief"""
		self.update_last_updated()

	def update_last_updated(self):
		"""Update last updated timestamp"""
		if self.has_value_changed("interviewer_notes") or self.has_value_changed(
			"hire_recommendation"
		):
			self.last_updated = frappe.utils.now_datetime()

	def set_brief_data(
		self,
		strengths: str,
		weak_areas: str,
		verification_points: str,
		suggested_questions: str,
		model: str,
		prompt_version: str,
	):
		"""
		Set interview brief data

		Args:
			strengths: Candidate strengths
			weak_areas: Areas of concern
			verification_points: Points to verify
			suggested_questions: Suggested questions
			model: Model name
			prompt_version: Prompt version
		"""
		self.strengths = strengths
		self.weak_areas = weak_areas
		self.verification_points = verification_points
		self.suggested_questions = suggested_questions
		self.generated_by_model = model
		self.prompt_version = prompt_version

	def generate_final_summary(self) -> str:
		"""
		Generate final summary combining all interview data

		Returns:
			Final summary text
		"""
		summary_parts = []

		# Candidate overview
		if self.strengths:
			summary_parts.append(f"**Strengths:**\n{self.strengths}")

		if self.weak_areas:
			summary_parts.append(f"**Areas of Concern:**\n{self.weak_areas}")

		# Interview feedback
		if self.interviewer_notes:
			summary_parts.append(f"**Interview Notes:**\n{self.interviewer_notes}")

		if self.interviewer_rating:
			summary_parts.append(f"**Interviewer Rating:** {self.interviewer_rating}")

		if self.hire_recommendation:
			summary_parts.append(f"**Recommendation:** {self.hire_recommendation}")

		if self.final_comments:
			summary_parts.append(f"**Final Comments:**\n{self.final_comments}")

		return "\n\n".join(summary_parts)


@frappe.whitelist()
def get_interview_brief(applicant: str) -> Dict[str, Any]:
	"""
	Get interview brief for an applicant

	Args:
		applicant: Job Applicant name

	Returns:
		Interview brief data or None
	"""
	brief = frappe.db.get_value(
		"AI Interview Brief",
		{"applicant": applicant},
		[
			"name",
			"strengths",
			"weak_areas",
			"verification_points",
			"suggested_questions",
			"hire_recommendation",
		],
		as_dict=True,
		order_by="creation desc",
	)

	return brief if brief else None


@frappe.whitelist()
def update_interview_feedback(
	brief_name: str, interviewer_notes: str, rating: str, recommendation: str, comments: str
):
	"""
	Update interview feedback

	Args:
		brief_name: Interview brief name
		interviewer_notes: Interview notes
		rating: Interviewer rating
		recommendation: Hire recommendation
		comments: Final comments
	"""
	try:
		doc = frappe.get_doc("AI Interview Brief", brief_name)
		doc.interviewer_notes = interviewer_notes
		doc.interviewer_rating = rating
		doc.hire_recommendation = recommendation
		doc.final_comments = comments

		# Generate final summary
		doc.final_summary = doc.generate_final_summary()

		doc.save(ignore_permissions=True)
		frappe.db.commit()

		return {"success": True, "message": "Interview feedback updated successfully"}

	except Exception as e:
		frappe.log_error(f"Failed to update interview feedback: {str(e)}", "Update Interview Feedback")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_interview_stats(job_opening: str = None) -> Dict[str, Any]:
	"""
	Get interview statistics

	Args:
		job_opening: Optional job opening filter

	Returns:
		Statistics dictionary
	"""
	filters = {}
	if job_opening:
		filters["job_opening"] = job_opening

	total = frappe.db.count("AI Interview Brief", filters)

	# Count by recommendation
	strongly_recommend = frappe.db.count(
		"AI Interview Brief", {**filters, "hire_recommendation": "Strongly Recommend"}
	)
	recommend = frappe.db.count(
		"AI Interview Brief", {**filters, "hire_recommendation": "Recommend"}
	)
	maybe = frappe.db.count("AI Interview Brief", {**filters, "hire_recommendation": "Maybe"})
	not_recommend = frappe.db.count(
		"AI Interview Brief", {**filters, "hire_recommendation": "Do Not Recommend"}
	)

	return {
		"total": total,
		"strongly_recommend": strongly_recommend,
		"recommend": recommend,
		"maybe": maybe,
		"not_recommend": not_recommend,
	}


@frappe.whitelist()
def schedule_interview(interview_brief: str, interview_date: str, interviewer_email: str):
	"""
	Schedule an interview event from AI Interview Brief.

	Args:
		interview_brief: AI Interview Brief name
		interview_date: Interview date (YYYY-MM-DD)
		interviewer_email: Interviewer email address

	Returns:
		Event name
	"""
	if not frappe.has_permission("AI Interview Brief", "write", interview_brief):
		frappe.throw("Insufficient permissions")

	try:
		brief = frappe.get_doc("AI Interview Brief", interview_brief)

		# Get applicant details
		applicant = frappe.get_doc("Job Applicant", brief.applicant)
		email = get_first_field(applicant, EMAIL_FIELD_CANDIDATES) or ""

		# Create event
		event = frappe.new_doc("Event")
		event.subject = f"Interview: {applicant.applicant_name} - {brief.job_opening}"
		event.event_category = "Meeting"
		event.starts_on = f"{interview_date} 10:00:00"
		event.ends_on = f"{interview_date} 11:00:00"
		event.description = f"""
        Candidate: {applicant.applicant_name}
        Job: {brief.job_opening}
        Contact: {email}
        
        AI Interview Brief Summary:
        {brief.summary}
        """
		event.save(ignore_permissions=True)

		# Add participants
		if interviewer_email:
			event.add_participant(interviewer_email)
			event.save(ignore_permissions=True)

		# Update interview brief
		brief.interview_scheduled = 1
		brief.interview_date = interview_date
		brief.interviewer_email = interviewer_email
		brief.save(ignore_permissions=True)

		# Send notification
		from frappe_ai_hiring.ai_hiring.utils.notifications import NotificationManager

		NotificationManager.send_candidate_notification(
			job_applicant=brief.applicant,
			notification_type="interview_scheduled",
			additional_data={
				"interview_date": interview_date,
				"interviewer": interviewer_email,
				"event_link": frappe.utils.get_url_to_form("Event", event.name),
			},
		)

		frappe.msgprint(
			f"✅ Interview scheduled for {interview_date}",
			indicator="green",
			alert=True,
		)
		return event.name

	except Exception as e:
		frappe.throw(f"Failed to schedule interview: {str(e)}")


@frappe.whitelist()
def get_interview_feedback(interview_brief: str):
	"""
	Get evaluation feedback for an interview.

	Args:
		interview_brief: AI Interview Brief name

	Returns:
		Feedback dictionary
	"""
	brief = frappe.get_doc("AI Interview Brief", interview_brief)

	# Get evaluation result
	evaluation = frappe.db.get_value(
		"AI Evaluation Result",
		{"interview_brief": interview_brief},
		[
			"overall_score",
			"technical_score",
			"communication_score",
			"culture_fit_score",
			"key_strengths",
			"areas_for_improvement",
			"hire_recommendation",
		],
		as_dict=True,
	)

	return {
		"interview_brief": brief.name,
		"applicant": brief.applicant,
		"job_opening": brief.job_opening,
		"summary": brief.summary,
		"evaluation": evaluation or {},
	}
