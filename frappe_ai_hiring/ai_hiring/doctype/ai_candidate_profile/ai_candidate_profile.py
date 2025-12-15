# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document
from typing import Dict, Any


class AICandidateProfile(Document):
	"""AI Candidate Profile DocType"""

	def validate(self):
		"""Validate candidate profile data"""
		self.validate_json_fields()

	def validate_json_fields(self):
		"""Validate JSON fields are valid JSON"""
		if self.parsed_resume_json:
			try:
				json.loads(self.parsed_resume_json)
			except json.JSONDecodeError:
				frappe.throw("Parsed Resume JSON is not valid JSON")

		if self.skill_vector:
			try:
				json.loads(self.skill_vector)
			except json.JSONDecodeError:
				frappe.throw("Skill Vector is not valid JSON")

	def get_parsed_data(self) -> Dict[str, Any]:
		"""Get parsed resume as dictionary"""
		if not self.parsed_resume_json:
			return {}
		try:
			return json.loads(self.parsed_resume_json)
		except json.JSONDecodeError:
			return {}

	def get_skills(self) -> list:
		"""Get list of skills from skill vector"""
		if not self.skill_vector:
			return []
		try:
			data = json.loads(self.skill_vector)
			return data.get("skills", [])
		except json.JSONDecodeError:
			return []

	def set_parsed_data(self, data: Dict[str, Any], model: str, confidence: float):
		"""
		Set parsed resume data

		Args:
			data: Parsed resume dictionary
			model: Model name used
			confidence: Confidence score
		"""
		self.parsed_resume_json = json.dumps(data, indent=2, ensure_ascii=False)
		self.parsing_model = model
		self.ai_confidence_score = confidence

		# Extract key fields
		if "experience_years" in data:
			self.total_experience_years = data["experience_years"]

		if "skills" in data:
			self.skill_vector = json.dumps({"skills": data["skills"]}, indent=2)
			self.primary_skills = ", ".join(data["skills"][:10])  # Top 10 skills

		if "education_relevance" in data:
			self.education_relevance = data["education_relevance"]


@frappe.whitelist()
def get_candidate_profile(applicant: str) -> Dict[str, Any]:
	"""
	Get candidate profile for an applicant

	Args:
		applicant: Job Applicant name

	Returns:
		Candidate profile data or None
	"""
	profile = frappe.db.get_value(
		"AI Candidate Profile",
		{"applicant": applicant},
		["name", "parsed_resume_json", "total_experience_years", "primary_skills"],
		as_dict=True,
	)

	return profile if profile else None
