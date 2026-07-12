"""
Security Utilities
Additional security features for the AI Hiring system
"""

import frappe
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import hashlib
import time
from frappe_ai_hiring.ai_hiring.utils.hrms_compat import (
	EMAIL_FIELD_CANDIDATES,
	PHONE_FIELD_CANDIDATES,
)


class RateLimiter:
	"""
	Rate limiter for AI operations to prevent abuse and control costs.
	"""
	
	@staticmethod
	def check_rate_limit(
		operation_type: str,
		user: Optional[str] = None,
		limit: int = 100,
		window_seconds: int = 3600
	) -> bool:
		"""
		Check if operation is within rate limits.
		
		Args:
			operation_type: Type of operation (resume_parsing, shortlisting, etc.)
			user: User performing the operation (defaults to current user)
			limit: Maximum operations allowed in window
			window_seconds: Time window in seconds
			
		Returns:
			True if within limits, False otherwise
		"""
		
		user = user or frappe.session.user
		cache_key = f"rate_limit:{operation_type}:{user}"
		
		# Get current count from cache
		current = frappe.cache().get_value(cache_key)
		
		if current is None:
			# First operation in this window
			frappe.cache().set_value(cache_key, 1, expires_in_sec=window_seconds)
			return True
		
		if int(current) >= limit:
			# Rate limit exceeded
			frappe.logger("ai_hiring").warning(
				f"Rate limit exceeded for {user}: {operation_type} ({current}/{limit})"
			)
			return False
		
		# Increment counter
		frappe.cache().incr(cache_key)
		return True
	
	@staticmethod
	def get_rate_limit_status(
		operation_type: str,
		user: Optional[str] = None
	) -> Dict[str, Any]:
		"""
		Get current rate limit status.
		
		Args:
			operation_type: Type of operation
			user: User to check (defaults to current user)
			
		Returns:
			Dict with current count and limit info
		"""
		
		user = user or frappe.session.user
		cache_key = f"rate_limit:{operation_type}:{user}"
		
		current = frappe.cache().get_value(cache_key) or 0
		
		# Get limits from settings
		settings = frappe.get_cached_value(
			"AI Settings",
			"AI Settings",
			["rate_limit_per_hour", "rate_limit_per_day"],
			as_dict=True
		)
		
		return {
			"operation_type": operation_type,
			"user": user,
			"current_count": int(current),
			"hourly_limit": settings.get("rate_limit_per_hour", 100),
			"daily_limit": settings.get("rate_limit_per_day", 500)
		}
	
	@staticmethod
	def reset_rate_limit(operation_type: str, user: Optional[str] = None) -> None:
		"""
		Reset rate limit for a user (admin only).
		
		Args:
			operation_type: Type of operation
			user: User to reset
		"""
		
		if not frappe.has_permission("AI Settings", "write"):
			frappe.throw("Insufficient permissions to reset rate limits")
		
		user = user or frappe.session.user
		cache_key = f"rate_limit:{operation_type}:{user}"
		frappe.cache().delete_value(cache_key)
		
		frappe.logger("ai_hiring").info(
			f"Rate limit reset for {user}: {operation_type}"
		)


class DataRetentionPolicy:
	"""
	Manage data retention and cleanup for AI-generated data.
	"""
	
	@staticmethod
	def cleanup_old_audit_logs(days: int = 90) -> int:
		"""
		Delete audit logs older than specified days.
		
		Args:
			days: Number of days to retain
			
		Returns:
			Number of records deleted
		"""
		
		cutoff_date = frappe.utils.add_days(frappe.utils.nowdate(), -days)
		
		# Delete old audit logs
		deleted = frappe.db.sql("""
			DELETE FROM `tabAI Audit Log`
			WHERE creation < %s
		""", (cutoff_date,))
		
		frappe.db.commit()
		
		count = deleted[0][0] if deleted else 0
		frappe.logger("ai_hiring").info(
			f"Cleaned up {count} audit logs older than {days} days"
		)
		
		return count
	
	@staticmethod
	def cleanup_rejected_candidates(days: int = 180) -> int:
		"""
		Archive or delete data for rejected candidates after retention period.
		
		Args:
			days: Number of days to retain rejected candidate data
			
		Returns:
			Number of records cleaned up
		"""
		
		cutoff_date = frappe.utils.add_days(frappe.utils.nowdate(), -days)
		
		# Find rejected candidates older than retention period
		rejected_applicants = frappe.db.sql("""
			SELECT name FROM `tabJob Applicant`
			WHERE status = 'Rejected'
			AND modified < %s
		""", (cutoff_date,), as_dict=True)
		
		count = 0
		for applicant in rejected_applicants:
			try:
				# Delete associated AI documents
				for doctype in [
					"AI Candidate Profile",
					"AI Shortlisting Result",
					"AI Evaluation Result",
					"AI Interview Brief"
				]:
					docs = frappe.get_all(
						doctype,
						filters={"job_applicant": applicant.name}
					)
					
					for doc in docs:
						frappe.delete_doc(doctype, doc.name, force=True)
				
				count += 1
				
			except Exception as e:
				frappe.logger("ai_hiring").error(
					f"Failed to cleanup data for {applicant.name}: {str(e)}"
				)
		
		frappe.db.commit()
		
		frappe.logger("ai_hiring").info(
			f"Cleaned up data for {count} rejected candidates older than {days} days"
		)
		
		return count
	
	@staticmethod
	def anonymize_candidate_data(job_applicant: str) -> bool:
		"""
		Anonymize PII in candidate records while retaining analytics data.
		
		Args:
			job_applicant: Job Applicant name
			
		Returns:
			True if successful
		"""
		
		try:
			# Anonymize Job Applicant
			applicant = frappe.get_doc("Job Applicant", job_applicant)
			applicant.applicant_name = f"Anonymized-{hashlib.md5(job_applicant.encode()).hexdigest()[:8]}"
			for fieldname in EMAIL_FIELD_CANDIDATES + PHONE_FIELD_CANDIDATES:
				if applicant.meta.has_field(fieldname):
					setattr(applicant, fieldname, None)
			applicant.save(ignore_permissions=True)
			
			# Anonymize AI Candidate Profile
			if frappe.db.exists("AI Candidate Profile", {"job_applicant": job_applicant}):
				profile = frappe.get_doc("AI Candidate Profile", {"job_applicant": job_applicant})
				
				# Remove PII from parsed data
				parsed_data = profile.get_parsed_data()
				if parsed_data:
					# Remove sensitive fields
					parsed_data.pop("contact_info", None)
					parsed_data.pop("email", None)
					parsed_data.pop("phone", None)
					parsed_data["summary"] = "[Anonymized]"
					
					profile.set_parsed_data(parsed_data)
					profile.save(ignore_permissions=True)
			
			frappe.db.commit()
			
			frappe.logger("ai_hiring").info(
				f"Anonymized candidate data: {job_applicant}"
			)
			
			return True
			
		except Exception as e:
			frappe.logger("ai_hiring").error(
				f"Failed to anonymize {job_applicant}: {str(e)}"
			)
			return False


class SecurityValidator:
	"""
	Validate security configuration and settings.
	"""
	
	@staticmethod
	def validate_ai_settings() -> Dict[str, Any]:
		"""
		Validate AI Settings configuration for security issues.
		
		Returns:
			Dict with validation results
		"""
		
		results = {
			"valid": True,
			"warnings": [],
			"errors": [],
			"recommendations": []
		}
		
		try:
			settings = frappe.get_doc("AI Settings", "AI Settings")
			
			# Check API key configuration
			if not settings.api_key:
				results["errors"].append("API key is not configured")
				results["valid"] = False
			
			# Check provider configuration
			if not settings.provider:
				results["errors"].append("LLM provider is not configured")
				results["valid"] = False
			
			# Check model configuration
			if not settings.default_model:
				results["warnings"].append("Default model is not set")
			
			# Check temperature settings
			if settings.temperature and (settings.temperature < 0 or settings.temperature > 1):
				results["warnings"].append("Temperature should be between 0 and 1")
			
			# Check PII redaction
			if not settings.enable_pii_redaction:
				results["warnings"].append(
					"PII redaction is disabled - candidate privacy may be at risk"
				)
				results["recommendations"].append("Enable PII redaction in production")
			
			# Check audit logging
			if not settings.enable_audit_logging:
				results["warnings"].append("Audit logging is disabled")
				results["recommendations"].append("Enable audit logging for compliance")
			
			# Check rate limiting
			rate_limit_per_hour = settings.get("rate_limit_per_hour", 0)
			if not rate_limit_per_hour or rate_limit_per_hour > 500:
				results["warnings"].append("Rate limiting may be too permissive")
				results["recommendations"].append("Set reasonable rate limits to control costs")
			
			# Check timeout settings
			timeout = settings.get("timeout_seconds", 0)
			if not timeout or timeout > 300:
				results["warnings"].append("Timeout is not configured or too high")
				results["recommendations"].append("Set timeout to 60-120 seconds")
			
		except Exception as e:
			results["errors"].append(f"Validation failed: {str(e)}")
			results["valid"] = False
		
		return results
	
	@staticmethod
	def validate_permissions() -> Dict[str, Any]:
		"""
		Validate that DocType permissions are properly configured.
		
		Returns:
			Dict with permission validation results
		"""
		
		results = {
			"valid": True,
			"issues": []
		}
		
		doctypes_to_check = [
			"AI Settings",
			"AI Candidate Profile",
			"AI Shortlisting Result",
			"AI Question Set",
			"AI Evaluation Result",
			"AI Interview Brief"
		]
		
		for doctype in doctypes_to_check:
			try:
				# Check if HR Manager has appropriate permissions
				permissions = frappe.get_all(
					"Custom DocPerm",
					filters={"parent": doctype, "role": "HR Manager"},
					fields=["read", "write", "create", "delete"]
				)
				
				if not permissions:
					results["issues"].append(
						f"{doctype}: No permissions found for HR Manager role"
					)
					results["valid"] = False
				
			except Exception as e:
				results["issues"].append(f"{doctype}: Error checking permissions - {str(e)}")
		
		return results
	
	@staticmethod
	def audit_security_configuration() -> Dict[str, Any]:
		"""
		Perform comprehensive security audit.
		
		Returns:
			Complete audit report
		"""
		
		audit_report = {
			"timestamp": frappe.utils.now(),
			"ai_settings": SecurityValidator.validate_ai_settings(),
			"permissions": SecurityValidator.validate_permissions(),
			"recommendations": []
		}
		
		# Overall recommendations
		if not audit_report["ai_settings"]["valid"] or not audit_report["permissions"]["valid"]:
			audit_report["recommendations"].append(
				"Critical security issues found - review configuration before production use"
			)
		
		audit_report["recommendations"].extend([
			"Regularly review and rotate API keys",
			"Monitor rate limits and adjust as needed",
			"Review audit logs for suspicious activity",
			"Implement data retention policies",
			"Train users on security best practices"
		])
		
		return audit_report


@frappe.whitelist()
def check_operation_rate_limit(operation_type: str) -> Dict[str, Any]:
	"""
	Check rate limit status for current user.
	
	Args:
		operation_type: Type of operation to check
		
	Returns:
		Rate limit status
	"""
	
	return RateLimiter.get_rate_limit_status(operation_type)


@frappe.whitelist()
def run_security_audit() -> Dict[str, Any]:
	"""
	Run security configuration audit (admin only).
	
	Returns:
		Audit report
	"""
	
	if not frappe.has_permission("AI Settings", "write"):
		frappe.throw("Insufficient permissions to run security audit")
	
	return SecurityValidator.audit_security_configuration()


@frappe.whitelist()
def cleanup_old_data(
	audit_log_days: int = 90,
	rejected_candidates_days: int = 180
) -> Dict[str, Any]:
	"""
	Run data cleanup tasks (admin only).
	
	Args:
		audit_log_days: Days to retain audit logs
		rejected_candidates_days: Days to retain rejected candidate data
		
	Returns:
		Cleanup results
	"""
	
	if not frappe.has_permission("AI Settings", "write"):
		frappe.throw("Insufficient permissions to run cleanup")
	
	results = {
		"audit_logs_deleted": DataRetentionPolicy.cleanup_old_audit_logs(audit_log_days),
		"rejected_candidates_cleaned": DataRetentionPolicy.cleanup_rejected_candidates(
			rejected_candidates_days
		)
	}
	
	return results
