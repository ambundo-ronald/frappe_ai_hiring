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
		execution_time_ms: int = 0,
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
			execution_time_ms: Time taken for execution in milliseconds
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

			# Create AI Audit Log document
			audit_log = frappe.new_doc("AI Audit Log")
			audit_log.operation_type = operation
			audit_log.model_used = model
			audit_log.success = success
			audit_log.timestamp = datetime.now()
			audit_log.user = frappe.session.user
			audit_log.execution_time_ms = execution_time_ms
			
			# Add reference doctype and name if in metadata
			if metadata:
				if metadata.get("doctype"):
					audit_log.reference_doctype = metadata.get("doctype")
				if metadata.get("docname"):
					audit_log.reference_name = metadata.get("docname")
				audit_log.operation_details = metadata.get("details", "")
				audit_log.metadata = json.dumps(metadata, indent=2)
			
			# Add prompt/response previews (first 500 chars)
			if prompt:
				audit_log.prompt_preview = prompt[:500]
			if response:
				audit_log.response_preview = str(response)[:500]
			
			if error_message:
				audit_log.error_message = error_message
				audit_log.status = "Failed"
			else:
				audit_log.status = "Completed"
			
			audit_log.insert(ignore_permissions=True)

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
			operation="Shortlisting",
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
			operation="Question Generation",
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
			operation="Interview Brief",
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
	@staticmethod
	def get_logs_for_reference(reference_doctype: str, reference_name: str, limit: int = 50):
		"""Get all audit logs for a specific document"""
		return frappe.db.get_list(
			"AI Audit Log",
			filters={"reference_doctype": reference_doctype, "reference_name": reference_name},
			fields=["name", "timestamp", "operation_type", "success", "model_used"],
			order_by="timestamp desc",
			limit_page_length=limit,
		)

	@staticmethod
	def get_logs_by_operation(operation: str, limit: int = 50):
		"""Get all audit logs for a specific operation type"""
		return frappe.db.get_list(
			"AI Audit Log",
			filters={"operation_type": operation},
			fields=["name", "timestamp", "reference_doctype", "reference_name", "success", "model_used"],
			order_by="timestamp desc",
			limit_page_length=limit,
		)

	@staticmethod
	def get_failed_operations(limit: int = 50):
		"""Get all failed AI operations"""
		return frappe.db.get_list(
			"AI Audit Log",
			filters={"success": 0},
			fields=["name", "timestamp", "operation_type", "reference_doctype", "reference_name", "error_message"],
			order_by="timestamp desc",
			limit_page_length=limit,
		)