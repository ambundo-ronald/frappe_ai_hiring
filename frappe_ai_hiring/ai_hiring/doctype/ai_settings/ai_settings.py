# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AISettings(Document):
	"""AI Settings DocType for managing LLM configuration"""

	def validate(self):
		"""Validate settings before save"""
		self.validate_provider_config()
		self.validate_thresholds()
		self.validate_governance()

	def validate_provider_config(self):
		"""Validate provider-specific configuration"""
		if self.provider in ["OpenAI", "Azure OpenAI", "Custom"]:
			if not self.api_key:
				frappe.throw("API Key is required for {0}".format(self.provider))
			if not self.api_base_url and self.provider in ["Azure OpenAI", "Custom"]:
				frappe.throw("API Base URL is required for {0}".format(self.provider))

		if self.provider == "Ollama":
			if not self.api_base_url:
				frappe.throw("API Base URL is required for Ollama")

	def validate_thresholds(self):
		"""Validate threshold values"""
		if not (0 <= self.shortlisting_threshold <= 100):
			frappe.throw("Shortlisting threshold must be between 0 and 100")

		if not (0 <= self.questionnaire_pass_threshold <= 100):
			frappe.throw("Questionnaire pass threshold must be between 0 and 100")

	def validate_governance(self):
		"""Validate rate limits and retention settings"""
		if self.enable_rate_limiting:
			if self.rate_limit_per_hour and self.rate_limit_per_hour < 1:
				frappe.throw("Hourly limit must be positive when rate limiting is enabled")
			if self.rate_limit_per_day and self.rate_limit_per_day < self.rate_limit_per_hour:
				frappe.throw("Daily limit should be greater than or equal to hourly limit")

		if self.enable_data_retention:
			if self.audit_log_retention_days and self.audit_log_retention_days < 1:
				frappe.throw("Audit log retention days must be positive")
			if self.rejected_candidate_retention_days and self.rejected_candidate_retention_days < 1:
				frappe.throw("Rejected candidate retention days must be positive")

	def get_api_config(self):
		"""Get API configuration for LLM calls"""
		config = {
			"provider": self.provider,
			"model": self.default_model,
			"temperature": self.temperature,
			"max_tokens": self.max_tokens,
			"timeout": self.timeout,
		}

		if self.api_key:
			config["api_key"] = self.get_password("api_key")

		if self.api_base_url:
			config["api_base_url"] = self.api_base_url

		return config


@frappe.whitelist()
def get_ai_settings():
	"""Get AI Settings (cached)"""
	if not frappe.db.exists("AI Settings", "AI Settings"):
		return None

	settings = frappe.get_cached_doc("AI Settings", "AI Settings")
	return settings


@frappe.whitelist()
def test_connection():
	"""Test API connection"""
	try:
		settings = get_ai_settings()
		if not settings:
			frappe.throw("AI Settings not configured")

		# Import here to avoid circular dependency
		from frappe_ai_hiring.ai_hiring.utils.llm_client import LLMClient

		client = LLMClient()
		result = client.test_connection()

		frappe.msgprint("✅ Connection successful", indicator="green", alert=True)
		return {"success": True, "message": "Connection successful", "result": result}

	except Exception as e:
		frappe.log_error(f"Connection test failed: {str(e)}", "AI Settings Connection Test")
		frappe.throw(f"Connection test failed: {str(e)}")
