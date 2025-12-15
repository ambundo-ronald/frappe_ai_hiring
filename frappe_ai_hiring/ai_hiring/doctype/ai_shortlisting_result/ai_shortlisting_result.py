# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document
from typing import Dict, Any


class AIShortlistingResult(Document):
	"""AI Shortlisting Result DocType"""

	def validate(self):
		"""Validate shortlisting result"""
		self.check_threshold()
		self.validate_fit_score()

	def check_threshold(self):
		"""Check if fit score meets threshold"""
		settings = frappe.get_cached_value(
			"AI Settings", "AI Settings", "shortlisting_threshold"
		)

		if settings and self.fit_score:
			self.threshold_met = 1 if self.fit_score >= settings else 0

	def validate_fit_score(self):
		"""Validate fit score is in valid range"""
		if self.fit_score and not (0 <= self.fit_score <= 100):
			frappe.throw("Fit score must be between 0 and 100")

	def set_result(
		self,
		decision: str,
		fit_score: float,
		reasons: list,
		missing_skills: list,
		strengths: list,
		confidence: float,
		model: str,
		prompt_version: str,
		raw_response: Dict[str, Any],
	):
		"""
		Set shortlisting result data

		Args:
			decision: Shortlist/Reject/Review
			fit_score: Fit score (0-100)
			reasons: List of reasons
			missing_skills: List of missing skills
			strengths: List of strengths
			confidence: Confidence score (0-1)
			model: Model name
			prompt_version: Prompt version
			raw_response: Raw LLM response
		"""
		self.decision = decision
		self.fit_score = fit_score
		self.reasons = "\n".join(reasons) if isinstance(reasons, list) else reasons
		self.missing_skills = ", ".join(missing_skills) if isinstance(missing_skills, list) else missing_skills
		self.strengths = ", ".join(strengths) if isinstance(strengths, list) else strengths
		self.confidence_score = confidence
		self.model_name = model
		self.prompt_version = prompt_version
		self.raw_llm_response = json.dumps(raw_response, indent=2)


@frappe.whitelist()
def get_shortlisting_result(applicant: str, job_opening: str = None) -> Dict[str, Any]:
	"""
	Get shortlisting result for an applicant

	Args:
		applicant: Job Applicant name
		job_opening: Optional job opening filter

	Returns:
		Shortlisting result data or None
	"""
	filters = {"applicant": applicant}
	if job_opening:
		filters["job_opening"] = job_opening

	result = frappe.db.get_value(
		"AI Shortlisting Result",
		filters,
		["name", "decision", "fit_score", "reasons", "missing_skills", "strengths"],
		as_dict=True,
		order_by="creation desc",
	)

	return result if result else None


@frappe.whitelist()
def get_shortlisting_stats(job_opening: str = None) -> Dict[str, Any]:
	"""
	Get shortlisting statistics

	Args:
		job_opening: Optional job opening filter

	Returns:
		Statistics dictionary
	"""
	filters = {}
	if job_opening:
		filters["job_opening"] = job_opening

	total = frappe.db.count("AI Shortlisting Result", filters)

	shortlisted = frappe.db.count("AI Shortlisting Result", {**filters, "decision": "Shortlist"})
	rejected = frappe.db.count("AI Shortlisting Result", {**filters, "decision": "Reject"})
	review = frappe.db.count("AI Shortlisting Result", {**filters, "decision": "Review"})

	avg_fit_score = frappe.db.get_value(
		"AI Shortlisting Result", filters, "avg(fit_score)"
	) or 0

	return {
		"total": total,
		"shortlisted": shortlisted,
		"rejected": rejected,
		"review": review,
		"avg_fit_score": round(avg_fit_score, 2),
	}
