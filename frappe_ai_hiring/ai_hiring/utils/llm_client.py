# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

"""
LLM Client
Handles communication with OpenAI-compatible APIs
"""

import frappe
import json
import requests
from typing import Dict, Any, Optional
from frappe_ai_hiring.ai_hiring.utils.audit_logger import AIAuditLogger


class LLMClient:
	"""Client for interacting with LLM APIs"""

	def __init__(self):
		"""Initialize LLM client with settings"""
		self.settings = self._get_settings()

	def _get_settings(self):
		"""Get AI settings"""
		from frappe_ai_hiring.ai_hiring.doctype.ai_settings.ai_settings import get_ai_settings

		settings = get_ai_settings()
		if not settings:
			frappe.throw("AI Settings not configured. Please configure AI Settings first.")

		if not settings.enable_ai_processing:
			frappe.throw("AI Processing is disabled in settings")

		return settings

	def call_llm(
		self,
		prompt: str,
		system_prompt: Optional[str] = None,
		operation: str = "generic",
		metadata: Optional[Dict[str, Any]] = None,
		temperature: Optional[float] = None,
		max_tokens: Optional[int] = None,
	) -> Dict[str, Any]:
		"""
		Make an LLM API call

		Args:
			prompt: User prompt
			system_prompt: System prompt (optional)
			operation: Operation type for logging
			metadata: Additional metadata for logging
			temperature: Override default temperature
			max_tokens: Override default max tokens

		Returns:
			Parsed JSON response from LLM
		"""
		try:
			# Prepare request
			config = self.settings.get_api_config()
			headers = self._get_headers(config)
			payload = self._build_payload(
				prompt=prompt,
				system_prompt=system_prompt,
				config=config,
				temperature=temperature,
				max_tokens=max_tokens,
			)

			# Make API call
			url = self._get_endpoint_url(config)
			response = requests.post(
				url, headers=headers, json=payload, timeout=config.get("timeout", 60)
			)

			response.raise_for_status()
			result = response.json()

			# Extract content
			content = self._extract_content(result, config)

			# Parse JSON from content
			parsed_response = self._parse_json_response(content)

			# Log successful call
			AIAuditLogger.log_llm_call(
				operation=operation,
				prompt=prompt[:500],  # Truncate for storage
				response=json.dumps(parsed_response)[:1000],
				model=config.get("model"),
				metadata=metadata,
				success=True,
			)

			return parsed_response

		except requests.exceptions.RequestException as e:
			error_msg = self._format_request_error(e, config)
			AIAuditLogger.log_error(operation, error_msg, metadata)
			frappe.throw(error_msg)

		except json.JSONDecodeError as e:
			error_msg = f"Failed to parse JSON response: {str(e)}"
			AIAuditLogger.log_error(operation, error_msg, metadata)
			frappe.throw(error_msg)

		except Exception as e:
			error_msg = f"LLM call failed: {str(e)}"
			AIAuditLogger.log_error(operation, error_msg, metadata)
			frappe.throw(error_msg)

	def _get_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
		"""Build request headers"""
		headers = {"Content-Type": "application/json"}

		if config.get("api_key") and not self._is_gemini(config):
			headers["Authorization"] = f"Bearer {config['api_key']}"

		if config.get("api_key") and self._is_gemini(config):
			headers["x-goog-api-key"] = config["api_key"]

		return headers

	def _is_gemini(self, config: Dict[str, Any]) -> bool:
		"""Return true when the configured provider is Google's Gemini API."""
		return (config.get("provider") or "").lower() == "gemini"

	def _get_endpoint_url(self, config: Dict[str, Any]) -> str:
		"""Get API endpoint URL"""
		if self._is_gemini(config):
			return self._get_gemini_endpoint_url(config)

		base_url = config.get("api_base_url", "https://api.openai.com/v1")

		# Remove trailing slash
		base_url = base_url.rstrip("/")

		# For OpenAI-compatible APIs
		if "/chat/completions" not in base_url:
			return f"{base_url}/chat/completions"

		return base_url

	def _get_gemini_endpoint_url(self, config: Dict[str, Any]) -> str:
		"""Get Gemini generateContent endpoint URL."""
		base_url = config.get("api_base_url") or "https://generativelanguage.googleapis.com/v1beta"
		base_url = base_url.rstrip("/")

		if ":generateContent" in base_url:
			url = base_url
		else:
			model = config.get("model") or "gemini-2.0-flash"
			if not str(model).startswith("models/"):
				model = f"models/{model}"
			url = f"{base_url}/{model}:generateContent"

		return url

	def _format_request_error(self, error: requests.exceptions.RequestException, config: Dict[str, Any]) -> str:
		"""Return a safe API error message without leaking credentials."""
		status_code = getattr(getattr(error, "response", None), "status_code", None)
		provider = config.get("provider", "AI provider")

		if status_code == 429:
			return (
				f"API request failed: {provider} rate limit or quota exceeded. "
				"Wait a few minutes, reduce bulk processing volume, or check your provider quota/billing."
			)

		message = str(error)
		api_key = config.get("api_key")
		if api_key:
			message = message.replace(api_key, "[redacted]")

		return f"API request failed: {message}"

	def _build_payload(
		self,
		prompt: str,
		system_prompt: Optional[str],
		config: Dict[str, Any],
		temperature: Optional[float] = None,
		max_tokens: Optional[int] = None,
	) -> Dict[str, Any]:
		"""Build API request payload"""
		if self._is_gemini(config):
			return self._build_gemini_payload(
				prompt=prompt,
				system_prompt=system_prompt,
				config=config,
				temperature=temperature,
				max_tokens=max_tokens,
			)

		messages = []

		if system_prompt:
			messages.append({"role": "system", "content": system_prompt})

		messages.append({"role": "user", "content": prompt})

		payload = {
			"model": config.get("model"),
			"messages": messages,
			"temperature": temperature or config.get("temperature", 0.2),
			"max_tokens": max_tokens or config.get("max_tokens", 2000),
		}

		return payload

	def _build_gemini_payload(
		self,
		prompt: str,
		system_prompt: Optional[str],
		config: Dict[str, Any],
		temperature: Optional[float] = None,
		max_tokens: Optional[int] = None,
	) -> Dict[str, Any]:
		"""Build Gemini generateContent request payload."""
		payload = {
			"contents": [
				{
					"role": "user",
					"parts": [{"text": prompt}],
				}
			],
			"generationConfig": {
				"temperature": temperature or config.get("temperature", 0.2),
				"maxOutputTokens": max_tokens or config.get("max_tokens", 2000),
				"responseMimeType": "application/json",
			},
		}

		if system_prompt:
			payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

		return payload

	def _extract_content(self, response: Dict[str, Any], config: Dict[str, Any]) -> str:
		"""Extract content from API response"""
		if self._is_gemini(config):
			return self._extract_gemini_content(response)

		# Standard OpenAI format
		if "choices" in response and len(response["choices"]) > 0:
			return response["choices"][0]["message"]["content"]

		# Fallback
		if "content" in response:
			return response["content"]

		frappe.throw("Unable to extract content from API response")

	def _extract_gemini_content(self, response: Dict[str, Any]) -> str:
		"""Extract text content from Gemini generateContent response."""
		candidates = response.get("candidates") or []
		if candidates:
			parts = candidates[0].get("content", {}).get("parts") or []
			text_parts = [part.get("text", "") for part in parts if part.get("text")]
			if text_parts:
				return "\n".join(text_parts)

		prompt_feedback = response.get("promptFeedback") or {}
		if prompt_feedback.get("blockReason"):
			frappe.throw(f"Gemini blocked the prompt: {prompt_feedback.get('blockReason')}")

		frappe.throw("Unable to extract content from Gemini response")

	def _parse_json_response(self, content: str) -> Dict[str, Any]:
		"""
		Parse JSON from LLM response
		Handles markdown code blocks and other formatting
		"""
		# Try direct parse first
		try:
			return json.loads(content)
		except json.JSONDecodeError:
			pass

		# Try to extract JSON from markdown code block
		import re

		json_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", content, re.DOTALL)
		if json_match:
			try:
				return json.loads(json_match.group(1))
			except json.JSONDecodeError:
				pass

		# Try to find JSON object in text
		json_match = re.search(r"\{.*\}", content, re.DOTALL)
		if json_match:
			try:
				return json.loads(json_match.group(0))
			except json.JSONDecodeError:
				pass

		frappe.throw(f"Unable to parse JSON from response: {content[:200]}")

	def test_connection(self) -> Dict[str, Any]:
		"""Test API connection"""
		try:
			response = self.call_llm(
				prompt="Respond with: {\"status\": \"ok\", \"message\": \"Connection successful\"}",
				system_prompt="You are a test assistant. Respond only with valid JSON.",
				operation="Other",
			)
			return response
		except Exception as e:
			return {"status": "error", "message": str(e)}


# Convenience wrapper used by services that import call_llm directly
def call_llm(
	system_prompt: Optional[str],
	user_prompt: str,
	operation_type: str = "generic",
	reference_doctype: Optional[str] = None,
	metadata: Optional[Dict[str, Any]] = None,
	temperature: Optional[float] = None,
	max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
	"""Invoke the LLM using shared settings."""
	client = LLMClient()
	return client.call_llm(
		prompt=user_prompt,
		system_prompt=system_prompt,
		operation=operation_type,
		metadata=metadata or {"doctype": reference_doctype} if reference_doctype else metadata,
		temperature=temperature,
		max_tokens=max_tokens,
	)


@frappe.whitelist()
def test_llm_client():
	"""Test LLM client (for debugging)"""
	try:
		client = LLMClient()
		result = client.test_connection()
		return {"success": True, "result": result}
	except Exception as e:
		return {"success": False, "error": str(e)}
