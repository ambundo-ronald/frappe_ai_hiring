# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

"""
Pytest fixtures and configuration for frappe_ai_hiring tests
"""

import json
from unittest.mock import MagicMock, patch
import pytest
import frappe
from frappe.test_runner import make_test_records


@pytest.fixture
def ai_settings(db):
	"""Create and return AI Settings test document"""
	doc = frappe.new_doc("AI Settings")
	doc.api_provider = "openai"
	doc.api_key = "sk-test-key"
	doc.api_url = "https://api.openai.com/v1"
	doc.model_name = "gpt-4"
	doc.enable_rate_limiting = 1
	doc.rate_limit_per_hour = 100
	doc.rate_limit_per_day = 500
	doc.enable_audit_logging = 1
	doc.enable_data_retention = 1
	doc.audit_log_retention_days = 90
	doc.rejected_candidate_retention_days = 30
	doc.timeout_seconds = 60
	doc.save()
	return doc


@pytest.fixture
def job_opening(db):
	"""Create and return test Job Opening"""
	doc = frappe.new_doc("Job Opening")
	doc.designation = "Senior Software Engineer"
	doc.job_title = "Senior Software Engineer"
	doc.status = "Open"
	doc.save()
	return doc


@pytest.fixture
def job_applicant(db, job_opening):
	"""Create and return test Job Applicant"""
	doc = frappe.new_doc("Job Applicant")
	doc.applicant_name = "John Doe"
	doc.email_id = "john@example.com"
	doc.phone = "+1-555-0100"
	doc.designation = job_opening.designation
	doc.job_title = job_opening.job_title
	doc.resume_attachment = None
	doc.save()
	return doc


@pytest.fixture
def job_applicant_with_resume(db, job_opening):
	"""Create test Job Applicant with resume content"""
	doc = frappe.new_doc("Job Applicant")
	doc.applicant_name = "Jane Smith"
	doc.email_id = "jane@example.com"
	doc.phone = "+1-555-0101"
	doc.designation = job_opening.designation
	doc.job_title = job_opening.job_title
	doc.save()

	# Create mock file attachment
	file_doc = frappe.new_doc("File")
	file_doc.file_name = "resume.pdf"
	file_doc.file_url = "/files/resume.pdf"
	file_doc.attached_to_doctype = "Job Applicant"
	file_doc.attached_to_name = doc.name
	file_doc.is_private = 0
	file_doc.save()

	doc.resume_attachment = file_doc.name
	doc.save()
	return doc


@pytest.fixture
def mock_llm_response():
	"""Mock LLM response for candidate parsing"""
	return {
		"skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
		"experience_years": 5,
		"current_company": "Tech Corp",
		"education": "BS Computer Science",
		"certifications": ["AWS Solutions Architect"],
		"previous_roles": [
			{"title": "Software Engineer", "duration": "3 years"},
			{"title": "Junior Developer", "duration": "2 years"},
		],
		"technical_skills": {
			"backend": ["Python", "FastAPI", "Django"],
			"databases": ["PostgreSQL", "Redis"],
			"devops": ["Docker", "Kubernetes"],
		},
		"soft_skills": ["Leadership", "Communication", "Problem Solving"],
	}


@pytest.fixture
def mock_shortlist_response():
	"""Mock LLM response for shortlisting decision"""
	return {
		"decision": "Shortlist",
		"fit_score": 0.82,
		"technical_fit": 0.85,
		"culture_fit": 0.78,
		"reasoning": "Strong technical background with relevant experience. Good communication skills.",
		"concerns": "Limited Kubernetes experience, but willing to learn.",
		"recommended_questions": [
			"Tell us about your Kubernetes experience",
			"How do you approach learning new technologies?",
		],
	}


@pytest.fixture
def mock_question_response():
	"""Mock LLM response for question generation"""
	return {
		"questions": [
			{
				"question": "What is your experience with microservices architecture?",
				"difficulty": "Medium",
				"type": "Technical",
			},
			{
				"question": "Describe a challenging project you led and how you overcame obstacles.",
				"difficulty": "Medium",
				"type": "Behavioral",
			},
			{
				"question": "How do you stay updated with new technologies?",
				"difficulty": "Easy",
				"type": "Open-ended",
			},
		],
		"total_questions": 3,
	}


@pytest.fixture
def mock_evaluation_response():
	"""Mock LLM response for interview evaluation"""
	return {
		"overall_score": 78,
		"technical_score": 82,
		"communication_score": 75,
		"culture_fit_score": 76,
		"key_strengths": "Strong technical knowledge, clear communication, demonstrated leadership.",
		"areas_for_improvement": "Could improve system design knowledge, needs more hands-on deployment experience.",
		"hire_recommendation": "Recommend",
		"confidence": 0.88,
	}


@pytest.fixture
def mock_llm_client():
	"""Mock LLMClient for all services"""
	with patch(
		"frappe_ai_hiring.ai_hiring.utils.llm_client.LLMClient.call_llm"
	) as mock:

		def llm_side_effect(*args, **kwargs):
			"""Return appropriate mock response based on operation"""
			operation = kwargs.get("operation_type", "")
			if "parse" in operation.lower() or "resume" in operation.lower():
				return {
					"skills": ["Python", "FastAPI"],
					"experience_years": 5,
					"education": "BS Computer Science",
				}
			elif "shortlist" in operation.lower():
				return {"decision": "Shortlist", "fit_score": 0.82}
			elif "question" in operation.lower():
				return {
					"questions": [
						{"question": "Test Q1", "difficulty": "Medium"},
						{"question": "Test Q2", "difficulty": "Hard"},
					]
				}
			elif "evaluate" in operation.lower():
				return {
					"overall_score": 78,
					"technical_score": 82,
					"hire_recommendation": "Recommend",
				}
			return {}

		mock.side_effect = llm_side_effect
		yield mock


@pytest.fixture(autouse=True)
def reset_frappe_db(db):
	"""Reset Frappe database between tests"""
	yield
	# Cleanup is handled by pytest-frappe


@pytest.fixture
def mock_audit_logger():
	"""Mock audit logging"""
	with patch(
		"frappe_ai_hiring.ai_hiring.utils.audit_logger.AIAuditLogger.log_action"
	) as mock:
		yield mock


@pytest.fixture
def mock_notification_manager():
	"""Mock notification manager"""
	with patch(
		"frappe_ai_hiring.ai_hiring.utils.notifications.NotificationManager.send_candidate_notification"
	) as mock:
		mock.return_value = True
		yield mock


@pytest.fixture
def mock_pii_redactor():
	"""Mock PII redactor"""
	with patch(
		"frappe_ai_hiring.ai_hiring.utils.pii_redactor.PIIRedactor.redact"
	) as mock:
		mock.side_effect = lambda x: x  # Return text as-is for testing
		yield mock
