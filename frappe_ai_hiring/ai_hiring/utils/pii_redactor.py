# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

"""
PII Redaction Utility
Removes or tokenizes personally identifiable information before AI processing
"""

import re
import frappe
from typing import Dict, Any, Tuple


class PIIRedactor:
	"""Handles PII redaction and restoration"""

	def __init__(self):
		self.token_map = {}
		self.token_counter = 0

	def redact_text(self, text: str) -> Tuple[str, Dict[str, str]]:
		"""
		Redact PII from text and return tokenized version with mapping

		Args:
			text: Original text

		Returns:
			Tuple of (redacted_text, token_map)
		"""
		if not text:
			return text, {}

		redacted = text
		self.token_map = {}

		# Redact email addresses
		redacted = self._redact_emails(redacted)

		# Redact phone numbers
		redacted = self._redact_phones(redacted)

		# Redact potential names (basic heuristic)
		# This is simplified - production would use NER
		redacted = self._redact_names(redacted)

		return redacted, self.token_map

	def _redact_emails(self, text: str) -> str:
		"""Redact email addresses"""
		email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

		def replace_email(match):
			email = match.group(0)
			token = self._generate_token("EMAIL")
			self.token_map[token] = email
			return token

		return re.sub(email_pattern, replace_email, text)

	def _redact_phones(self, text: str) -> str:
		"""Redact phone numbers"""
		# Matches various phone formats
		phone_patterns = [
			r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # US format
			r"\b\(\d{3}\)\s*\d{3}[-.]?\d{4}\b",  # (123) 456-7890
			r"\b\+\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b",  # International
		]

		def replace_phone(match):
			phone = match.group(0)
			token = self._generate_token("PHONE")
			self.token_map[token] = phone
			return token

		result = text
		for pattern in phone_patterns:
			result = re.sub(pattern, replace_phone, result)

		return result

	def _redact_names(self, text: str) -> str:
		"""
		Redact potential names (basic implementation)
		In production, use NER models like spaCy
		"""
		# This is a simplified version
		# Real implementation should use Named Entity Recognition
		return text

	def _generate_token(self, prefix: str) -> str:
		"""Generate a unique token"""
		self.token_counter += 1
		return f"[{prefix}_{self.token_counter}]"

	def restore_text(self, text: str, token_map: Dict[str, str]) -> str:
		"""
		Restore original PII from tokens

		Args:
			text: Tokenized text
			token_map: Mapping of tokens to original values

		Returns:
			Text with restored PII
		"""
		if not text or not token_map:
			return text

		restored = text
		for token, original in token_map.items():
			restored = restored.replace(token, original)

		return restored

	@staticmethod
	def redact_resume_data(resume_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str]]:
		"""
		Redact PII from structured resume data

		Args:
			resume_data: Parsed resume as dictionary

		Returns:
			Tuple of (redacted_data, token_map)
		"""
		redactor = PIIRedactor()
		redacted_data = resume_data.copy()
		all_tokens = {}

		# Redact specific fields
		fields_to_redact = ["email", "phone", "mobile", "contact", "name", "full_name"]

		for field in fields_to_redact:
			if field in redacted_data and redacted_data[field]:
				if isinstance(redacted_data[field], str):
					redacted_text, tokens = redactor.redact_text(redacted_data[field])
					redacted_data[field] = redacted_text
					all_tokens.update(tokens)

		# Redact in nested structures (experience, education)
		for section in ["experience", "education", "certifications"]:
			if section in redacted_data and isinstance(redacted_data[section], list):
				for item in redacted_data[section]:
					if isinstance(item, dict):
						for key, value in item.items():
							if isinstance(value, str) and any(
								term in key.lower() for term in ["email", "phone", "contact"]
							):
								redacted_text, tokens = redactor.redact_text(value)
								item[key] = redacted_text
								all_tokens.update(tokens)

		return redacted_data, all_tokens


@frappe.whitelist()
def test_pii_redaction(text: str):
	"""Test PII redaction (for debugging)"""
	redactor = PIIRedactor()
	redacted, token_map = redactor.redact_text(text)

	return {"original": text, "redacted": redacted, "token_map": token_map}
