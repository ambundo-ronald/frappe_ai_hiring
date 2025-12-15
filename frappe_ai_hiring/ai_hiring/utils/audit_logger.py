# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

"""
AI Audit Logger
Logs all AI decisions, prompts, and responses for auditability
"""

import frappe
import json
from datetime import datetime
from typing import Dict, Any, Optional


class AIAuditLogger:
	"""Logger for AI operations with audit trail"""

	@staticmethod
	def log_llm_call(
		operation: str,
		prompt: str,
		response: str,
		model: str,
		metadata: Optional[Dict[str, Any]] = None,
		success: bool = True,
		error_message: Optional[str] = None,
	):
		"""
		Log an LLM API call with all relevant details

		Args:
			operation: Type of operation (e.g., 'resume_parsing', 'shortlisting')
			prompt: The prompt sent to LLM
			response: The response from LLM
			model: Model name used
			metadata: Additional metadata (applicant_id, job_opening, etc.)
			success: Whether the call was successful
			error_message: Error message if failed
		"""
		try:
			log_entry = {
				"operation": operation,
				"model": model,
				"success": success,
				"timestamp": datetime.now().isoformat(),
				"user": frappe.session.user,
				"metadata": metadata or {},
			}

			if error_message:
				log_entry["error_message"] = error_message

			# Store in Error Log for visibility
			frappe.log_error(
				title=f"AI Operation: {operation}",
				message=json.dumps(log_entry, indent=2),
				reference_doctype=metadata.get("doctype") if metadata else None,
				reference_name=metadata.get("docname") if metadata else None,
			)

			# Also log to file for debugging
			frappe.logger("ai_hiring").info(
				f"AI Operation: {operation} | Model: {model} | Success: {success}"
			)

		except Exception as e:
			frappe.logger("ai_hiring").error(f"Failed to log AI operation: {str(e)}")

	@staticmethod
	def log_shortlisting_decision(
		applicant: str,
		job_opening: str,
		decision: str,
		fit_score: float,
		reasons: list,
		model: str,
	):
		"""Log a shortlisting decision"""
		AIAuditLogger.log_llm_call(
			operation="shortlisting",
			prompt="[Redacted for brevity]",
			response=json.dumps(
				{"decision": decision, "fit_score": fit_score, "reasons": reasons}
			),
			model=model,
			metadata={
				"doctype": "Job Applicant",
				"docname": applicant,
				"job_opening": job_opening,
			},
			success=True,
		)

	@staticmethod
	def log_question_generation(
		job_role: str, skills: list, questions_generated: int, model: str
	):
		"""Log question generation"""
		AIAuditLogger.log_llm_call(
			operation="question_generation",
			prompt="[Redacted for brevity]",
			response=f"Generated {questions_generated} questions",
			model=model,
			metadata={"job_role": job_role, "skills": skills, "count": questions_generated},
			success=True,
		)

	@staticmethod
	def log_interview_brief(applicant: str, brief_sections: dict, model: str):
		"""Log interview brief generation"""
		AIAuditLogger.log_llm_call(
			operation="interview_brief_generation",
			prompt="[Redacted for brevity]",
			response=json.dumps(brief_sections),
			model=model,
			metadata={"doctype": "Job Applicant", "docname": applicant},
			success=True,
		)

	@staticmethod
	def log_error(operation: str, error_message: str, metadata: Optional[Dict] = None):
		"""Log an error in AI operations"""
		AIAuditLogger.log_llm_call(
			operation=operation,
			prompt="",
			response="",
			model="",
			metadata=metadata,
			success=False,
			error_message=error_message,
		)
