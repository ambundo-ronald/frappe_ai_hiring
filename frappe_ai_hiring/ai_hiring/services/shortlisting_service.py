# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

"""
Shortlisting Service
AI-powered candidate shortlisting against job descriptions
"""

import frappe
import json
from typing import Dict, Any, Optional
from frappe_ai_hiring.ai_hiring.utils.llm_client import LLMClient
from frappe_ai_hiring.ai_hiring.utils.audit_logger import AIAuditLogger
from frappe_ai_hiring.ai_hiring.utils.common import get_job_description
from frappe_ai_hiring.ai_hiring.utils.hrms_compat import get_job_opening_from_applicant


# Prompt version for tracking
SHORTLISTING_PROMPT_VERSION = "1.0.0"


def get_shortlisting_threshold() -> float:
	"""Return the HR-configured score threshold for automatic shortlisting."""
	threshold = frappe.db.get_single_value("AI Settings", "shortlisting_threshold")
	return float(threshold if threshold is not None else 70.0)


def normalize_fit_score(fit_score: Any) -> float:
	"""Normalize model fit scores to the 0-100 scale used by HR settings."""
	score = float(fit_score)
	if 0 <= score <= 1:
		score = score * 100
	return round(score, 2)


def get_threshold_decision(fit_score: float, threshold: Optional[float] = None) -> str:
	"""Apply the HR-configured score rule as the source of truth."""
	if threshold is None:
		threshold = get_shortlisting_threshold()
	return "Shortlist" if normalize_fit_score(fit_score) >= float(threshold) else "Reject"


def get_shortlisting_prompt(
	resume_data: Dict[str, Any], job_description: str, shortlisting_threshold: float
) -> tuple[str, str]:
	"""
	Get system and user prompts for candidate shortlisting

	Args:
		resume_data: Parsed resume data
		job_description: Job description text

	Returns:
		Tuple of (system_prompt, user_prompt)
	"""
	system_prompt = """You are a senior technical recruiter AI with expertise in candidate evaluation.

Your task is to evaluate candidates against job descriptions objectively and fairly.

CRITICAL RULES:
- Evaluate ONLY technical and professional fit
- Do NOT infer or consider: age, gender, religion, ethnicity, nationality
- Base decisions on: skills, experience, education, project relevance
- Be honest about skill gaps
- Provide specific, actionable reasons for decisions
- Respond ONLY with valid JSON matching the schema"""

	# Extract key info from resume
	skills = resume_data.get("skills", [])
	experience_years = resume_data.get("experience_years", 0)
	summary = resume_data.get("summary", "")

	user_prompt = f"""Evaluate this candidate for the job position.

JOB DESCRIPTION:
{job_description}

CANDIDATE PROFILE:
- Years of Experience: {experience_years}
- Skills: {', '.join(skills[:20])}
- Summary: {summary}

OUTPUT SCHEMA (respond with valid JSON only):
{{
  "fit_score": <0-100 integer>,
  "decision": "Shortlist|Reject|Review",
  "reasons": ["reason1", "reason2", "reason3"],
  "missing_skills": ["skill1", "skill2"],
  "strengths": ["strength1", "strength2"],
  "confidence_score": <0.0-1.0>
}}

SCORING RULE:
- Return fit_score on a 0-100 scale.
- The HR-configured automatic shortlisting threshold is {shortlisting_threshold}%.
- Shortlist means fit_score >= {shortlisting_threshold}.
- Reject means fit_score < {shortlisting_threshold}.
- Use Review only if the profile cannot be reliably scored from the available resume data.

Evaluate the candidate now:"""

	return system_prompt, user_prompt


def shortlist_candidate(applicant_name: str, job_opening: str) -> Optional[str]:
	"""
	Shortlist candidate and create AI Shortlisting Result

	Args:
		applicant_name: Job Applicant name
		job_opening: Job Opening name

	Returns:
		AI Shortlisting Result name or None
	"""
	try:
		frappe.logger("ai_hiring").info(f"Shortlisting candidate: {applicant_name}")

		# Step 1: Get candidate profile
		candidate_profile = frappe.db.get_value(
			"AI Candidate Profile",
			{"applicant": applicant_name, "job_opening": job_opening},
			["name", "parsed_resume_json"],
			as_dict=True,
		)

		if not candidate_profile:
			frappe.throw("AI Candidate Profile not found. Please parse resume first.")

		resume_data = json.loads(candidate_profile.parsed_resume_json)

		# Step 2: Get job description
		job_description = get_job_description(job_opening)

		if not job_description:
			frappe.throw("Job description not found")

		# Step 3: Call LLM for shortlisting
		threshold = get_shortlisting_threshold()
		client = LLMClient()
		system_prompt, user_prompt = get_shortlisting_prompt(resume_data, job_description, threshold)

		shortlisting_data = client.call_llm(
			prompt=user_prompt,
			system_prompt=system_prompt,
			operation="Shortlisting",
			metadata={"doctype": "Job Applicant", "docname": applicant_name, "job_opening": job_opening},
		)

		# Step 4: Validate shortlisting data
		required_fields = ["fit_score", "decision", "reasons", "missing_skills", "strengths"]
		for field in required_fields:
			if field not in shortlisting_data:
				frappe.throw(f"Missing required field in shortlisting data: {field}")

		fit_score = normalize_fit_score(shortlisting_data["fit_score"])
		decision = get_threshold_decision(fit_score, threshold)

		# Step 5: Create AI Shortlisting Result
		settings = frappe.get_cached_doc("AI Settings", "AI Settings")
		config = settings.get_api_config()

		result = frappe.get_doc(
			{
				"doctype": "AI Shortlisting Result",
				"applicant": applicant_name,
				"job_opening": job_opening,
			}
		)

		result.set_result(
			decision=decision,
			fit_score=fit_score,
			reasons=shortlisting_data["reasons"],
			missing_skills=shortlisting_data["missing_skills"],
			strengths=shortlisting_data.get("strengths", []),
			confidence=shortlisting_data.get("confidence_score", 0.0),
			model=config.get("model"),
			prompt_version=SHORTLISTING_PROMPT_VERSION,
			raw_response=shortlisting_data,
		)

		result.insert(ignore_permissions=True)
		frappe.db.commit()

		# Log the decision
		AIAuditLogger.log_shortlisting_decision(
			applicant=applicant_name,
			job_opening=job_opening,
			decision=decision,
			fit_score=fit_score,
			reasons=shortlisting_data["reasons"],
			model=config.get("model"),
		)

		frappe.logger("ai_hiring").info(
			f"Created AI Shortlisting Result: {result.name} - Decision: {result.decision}"
		)

		return result.name

	except Exception as e:
		error_msg = f"Shortlisting failed for {applicant_name}: {str(e)}"
		frappe.logger("ai_hiring").error(error_msg)
		AIAuditLogger.log_error(
			operation="Shortlisting",
			error_message=error_msg,
			metadata={"doctype": "Job Applicant", "docname": applicant_name, "job_opening": job_opening},
		)
		raise


def create_shortlisting_result(job_applicant: str, job_opening: Optional[str] = None) -> Optional[str]:
	"""Public wrapper to run shortlisting and persist result."""
	if not job_opening:
		job_opening = get_job_opening_from_applicant(job_applicant)
		if not job_opening:
			frappe.throw(f"Job Opening not found for applicant {job_applicant}")

	return shortlist_candidate(job_applicant, job_opening)


@frappe.whitelist()
def reshortlist_candidate(applicant_name: str, job_opening: str):
	"""
	Re-shortlist a candidate

	Args:
		applicant_name: Job Applicant name
		job_opening: Job Opening name

	Returns:
		Result dictionary
	"""
	try:
		# Delete existing result if any
		existing = frappe.db.get_value(
			"AI Shortlisting Result",
			{"applicant": applicant_name, "job_opening": job_opening},
		)
		if existing:
			frappe.delete_doc("AI Shortlisting Result", existing, ignore_permissions=True)

		# Shortlist candidate
		result_name = shortlist_candidate(applicant_name, job_opening)

		return {
			"success": True,
			"message": "Candidate re-shortlisted successfully",
			"result": result_name,
		}

	except Exception as e:
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def bulk_shortlist(job_opening: str):
	"""
	Shortlist all applicants for a job opening

	Args:
		job_opening: Job Opening name

	Returns:
		Result summary
	"""
	try:
		# Get all applicants for job opening
		applicants = frappe.get_all(
			"Job Applicant",
			filters={"status": ["!=", "Rejected"]},
			fields=["name", "applicant_name"],
		)
		applicants = [
			applicant
			for applicant in applicants
			if get_job_opening_from_applicant(applicant.name) == job_opening
		]

		if not applicants:
			return {"success": False, "message": "No applicants found"}

		results = {"total": len(applicants), "success": 0, "failed": 0, "errors": []}

		for applicant in applicants:
			try:
				# Check if already shortlisted
				existing = frappe.db.exists(
					"AI Shortlisting Result",
					{"applicant": applicant.name, "job_opening": job_opening},
				)

				if existing:
					continue

				# Shortlist
				shortlist_candidate(applicant.name, job_opening)
				results["success"] += 1

			except Exception as e:
				results["failed"] += 1
				results["errors"].append(
					{"applicant": applicant.applicant_name, "error": str(e)}
				)

		return {"success": True, "results": results}

	except Exception as e:
		return {"success": False, "message": str(e)}
