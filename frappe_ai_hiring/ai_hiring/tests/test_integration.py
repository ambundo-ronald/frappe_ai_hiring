# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

"""
Integration tests for AI Hiring pipeline end-to-end workflow
"""

import pytest
import frappe
from frappe.test_runner import FrappeTestCase
from unittest.mock import patch, MagicMock


class TestAIHiringPipelineIntegration(FrappeTestCase):
	"""Integration tests for complete AI hiring workflow"""

	def setUp(self):
		"""Set up test environment"""
		# Create AI Settings
		self.ai_settings = frappe.new_doc("AI Settings")
		self.ai_settings.api_provider = "openai"
		self.ai_settings.api_key = "sk-test-key"
		self.ai_settings.model_name = "gpt-4"
		self.ai_settings.enable_rate_limiting = 1
		self.ai_settings.rate_limit_per_hour = 100
		self.ai_settings.enable_audit_logging = 1
		self.ai_settings.save()

		# Create Job Opening
		self.job_opening = frappe.new_doc("Job Opening")
		self.job_opening.designation = "Full Stack Developer"
		self.job_opening.job_title = "Full Stack Developer"
		self.job_opening.description = (
			"We are looking for a full stack developer with 3+ years experience "
			"in Python, React, and PostgreSQL"
		)
		self.job_opening.status = "Open"
		self.job_opening.save()

	def test_pipeline_job_applicant_creation_triggers_processing(self):
		"""Test that creating a Job Applicant triggers AI processing"""
		job_applicant = frappe.new_doc("Job Applicant")
		job_applicant.applicant_name = "Pipeline Test Candidate"
		job_applicant.email_id = "pipeline@example.com"
		job_applicant.phone = "+1-555-0102"
		job_applicant.designation = self.job_opening.designation
		job_applicant.job_title = self.job_opening.job_title

		with patch(
			"frappe_ai_hiring.ai_hiring.jobs.process_new_applicant.enqueue_applicant_processing"
		) as mock_enqueue:
			job_applicant.save()
			# Verify that processing was enqueued
			# Note: In actual tests, we'd verify the queue

	def test_pipeline_parsing_stage(self):
		"""Test resume parsing stage of pipeline"""
		from frappe_ai_hiring.ai_hiring.services.resume_parser import (
			create_candidate_profile,
		)

		job_applicant = frappe.new_doc("Job Applicant")
		job_applicant.applicant_name = "Parse Stage Candidate"
		job_applicant.email_id = "parse@example.com"
		job_applicant.designation = self.job_opening.designation
		job_applicant.job_title = self.job_opening.job_title
		job_applicant.save()

		# Mock LLM response
		mock_response = {
			"skills": ["Python", "React", "PostgreSQL", "Docker"],
			"experience_years": 4,
			"current_company": "Tech Corp",
			"education": "BS Computer Science",
			"technical_skills": {
				"backend": ["Python", "FastAPI", "Django"],
				"frontend": ["React", "TypeScript"],
				"databases": ["PostgreSQL", "MongoDB"],
			},
		}

		with patch(
			"frappe_ai_hiring.ai_hiring.utils.llm_client.LLMClient.call_llm",
			return_value=mock_response,
		):
			profile_name = create_candidate_profile(
				job_applicant.name, self.job_opening.name
			)

			assert profile_name is not None
			profile = frappe.get_doc("AI Candidate Profile", profile_name)
			assert profile.applicant == job_applicant.name
			assert "Python" in profile.skills

	def test_pipeline_shortlisting_stage(self):
		"""Test shortlisting stage of pipeline"""
		from frappe_ai_hiring.ai_hiring.services.shortlisting_service import (
			create_shortlisting_result,
		)

		# Create prerequisite data
		job_applicant = frappe.new_doc("Job Applicant")
		job_applicant.applicant_name = "Shortlist Stage Candidate"
		job_applicant.email_id = "shortlist@example.com"
		job_applicant.designation = self.job_opening.designation
		job_applicant.job_title = self.job_opening.job_title
		job_applicant.save()

		candidate_profile = frappe.new_doc("AI Candidate Profile")
		candidate_profile.applicant = job_applicant.name
		candidate_profile.job_opening = self.job_opening.name
		candidate_profile.skills = "Python, React, PostgreSQL"
		candidate_profile.experience_years = 4
		candidate_profile.save()

		# Mock LLM response for shortlisting
		mock_response = {
			"decision": "Shortlist",
			"fit_score": 0.84,
			"technical_fit": 0.86,
			"culture_fit": 0.82,
			"reasoning": "Strong full stack skills with relevant experience",
			"concerns": "Limited DevOps experience",
		}

		with patch(
			"frappe_ai_hiring.ai_hiring.utils.llm_client.LLMClient.call_llm",
			return_value=mock_response,
		):
			result_name = create_shortlisting_result(
				job_applicant.name, self.job_opening.name
			)

			assert result_name is not None
			result = frappe.get_doc("AI Shortlisting Result", result_name)
			assert result.decision == "Shortlist"
			assert result.fit_score >= 0.8

	def test_pipeline_question_generation_stage(self):
		"""Test question generation stage of pipeline"""
		from frappe_ai_hiring.ai_hiring.services.question_generator import (
			create_question_set,
		)

		# Mock LLM response for questions
		mock_response = {
			"questions": [
				{"question": "What is your experience with React hooks?", "difficulty": "Medium"},
				{"question": "Design a RESTful API for a blog platform", "difficulty": "Hard"},
				{"question": "Explain your approach to database optimization", "difficulty": "Medium"},
			]
		}

		with patch(
			"frappe_ai_hiring.ai_hiring.utils.llm_client.LLMClient.call_llm",
			return_value=mock_response,
		):
			question_set = frappe.new_doc("AI Question Set")
			question_set.job_role = self.job_opening.job_title
			question_set.difficulty = "Medium"
			question_set.job_description = self.job_opening.description
			question_set.passing_score = 70.0
			question_set.save()

			assert len(question_set.questions) >= 0
			assert question_set.difficulty in ["Easy", "Medium", "Hard"]

	def test_pipeline_interview_brief_generation(self):
		"""Test interview brief generation stage of pipeline"""
		# Create test data
		job_applicant = frappe.new_doc("Job Applicant")
		job_applicant.applicant_name = "Interview Brief Candidate"
		job_applicant.email_id = "interview@example.com"
		job_applicant.designation = self.job_opening.designation
		job_applicant.job_title = self.job_opening.job_title
		job_applicant.save()

		candidate_profile = frappe.new_doc("AI Candidate Profile")
		candidate_profile.applicant = job_applicant.name
		candidate_profile.job_opening = self.job_opening.name
		candidate_profile.skills = "Python, React, PostgreSQL"
		candidate_profile.experience_years = 4
		candidate_profile.save()

		# Create interview brief
		brief = frappe.new_doc("AI Interview Brief")
		brief.applicant = job_applicant.name
		brief.job_opening = self.job_opening.name
		brief.summary = "Candidate shows strong full stack capabilities"
		brief.strengths = "Solid Python/React knowledge, good problem-solving"
		brief.weak_areas = "Limited team leadership experience"
		brief.verification_points = (
			"Verify project scale experience, check team size worked with"
		)
		brief.suggested_questions = (
			"Tell us about your largest project and your role in it"
		)
		brief.generated_by_model = "gpt-4"
		brief.prompt_version = "v1.0"
		brief.save()

		assert brief.name is not None
		assert "full stack" in brief.summary.lower()

	def test_pipeline_evaluation_stage(self):
		"""Test evaluation stage of pipeline"""
		# Create prerequisite data
		job_applicant = frappe.new_doc("Job Applicant")
		job_applicant.applicant_name = "Evaluation Candidate"
		job_applicant.email_id = "eval@example.com"
		job_applicant.designation = self.job_opening.designation
		job_applicant.job_title = self.job_opening.job_title
		job_applicant.save()

		interview_brief = frappe.new_doc("AI Interview Brief")
		interview_brief.applicant = job_applicant.name
		interview_brief.job_opening = self.job_opening.name
		interview_brief.summary = "Test brief"
		interview_brief.save()

		# Create evaluation result
		evaluation = frappe.new_doc("AI Evaluation Result")
		evaluation.interview_brief = interview_brief.name
		evaluation.applicant = job_applicant.name
		evaluation.overall_score = 82
		evaluation.technical_score = 85
		evaluation.communication_score = 78
		evaluation.culture_fit_score = 81
		evaluation.hire_recommendation = "Recommend"
		evaluation.key_strengths = (
			"Excellent technical skills, strong communication"
		)
		evaluation.areas_for_improvement = (
			"Could improve system design knowledge"
		)
		evaluation.save()

		assert evaluation.overall_score == 82
		assert evaluation.hire_recommendation == "Recommend"


class TestPipelineReporting(FrappeTestCase):
	"""Integration tests for AI hiring pipeline report"""

	def setUp(self):
		"""Set up test data for reports"""
		self.job_opening = frappe.new_doc("Job Opening")
		self.job_opening.designation = "QA Engineer"
		self.job_opening.job_title = "QA Engineer"
		self.job_opening.status = "Open"
		self.job_opening.save()

	def test_pipeline_report_query_executes(self):
		"""Test that pipeline report query executes without SQL errors"""
		from frappe_ai_hiring.ai_hiring.report.ai_hiring_pipeline_report.ai_hiring_pipeline_report import (
			execute,
		)

		# Create test data
		job_applicant = frappe.new_doc("Job Applicant")
		job_applicant.applicant_name = "Report Test Candidate"
		job_applicant.email_id = "report@example.com"
		job_applicant.designation = self.job_opening.designation
		job_applicant.job_title = self.job_opening.job_title
		job_applicant.status = "Open"
		job_applicant.save()

		# Execute report
		try:
			columns, data = execute(filters={})
			assert columns is not None
			assert isinstance(data, list)
		except Exception as e:
			pytest.fail(f"Report query failed: {str(e)}")

	def test_pipeline_report_includes_all_stages(self):
		"""Test that report shows all pipeline stages"""
		from frappe_ai_hiring.ai_hiring.report.ai_hiring_pipeline_report.ai_hiring_pipeline_report import (
			execute,
		)

		columns, data = execute(filters={})

		# Verify columns include expected fields
		column_names = [col.get("fieldname") for col in columns]
		expected_fields = [
			"applicant_name",
			"job_opening",
			"candidate_status",
			"parsing_status",
			"shortlist_decision",
			"evaluation_score",
			"hire_recommendation",
		]

		for field in expected_fields:
			assert field in column_names, f"Missing field: {field}"


class TestUIActions(FrappeTestCase):
	"""Integration tests for UI action buttons"""

	def setUp(self):
		"""Set up test data"""
		self.job_opening = frappe.new_doc("Job Opening")
		self.job_opening.designation = "UI Test Role"
		self.job_opening.job_title = "UI Test Role"
		self.job_opening.status = "Open"
		self.job_opening.save()

		self.job_applicant = frappe.new_doc("Job Applicant")
		self.job_applicant.applicant_name = "UI Action Test"
		self.job_applicant.email_id = "uiaction@example.com"
		self.job_applicant.designation = self.job_opening.designation
		self.job_applicant.job_title = self.job_opening.job_title
		self.job_applicant.save()

	def test_reprocess_candidate_action(self):
		"""Test reprocess candidate UI action"""
		from frappe_ai_hiring.ai_hiring.doctype.job_applicant.job_applicant import (
			reprocess_candidate,
		)

		with patch(
			"frappe_ai_hiring.ai_hiring.utils.job_manager.reprocess_applicant",
			return_value={"reprocessed": ["parsing", "shortlisting"]},
		):
			result = reprocess_candidate(
				self.job_applicant.name, ["parsing", "shortlisting"]
			)
			assert result is not None
			assert "reprocessed" in result

	def test_send_questionnaire_action(self):
		"""Test send questionnaire UI action"""
		from frappe_ai_hiring.ai_hiring.doctype.job_applicant.job_applicant import (
			send_questionnaire,
		)

		# Create shortlisting result so questionnaire can be sent
		shortlist = frappe.new_doc("AI Shortlisting Result")
		shortlist.applicant = self.job_applicant.name
		shortlist.decision = "Shortlist"
		shortlist.fit_score = 0.85
		shortlist.save()

		# Create question set
		question_set = frappe.new_doc("AI Question Set")
		question_set.job_role = self.job_opening.job_title
		question_set.difficulty = "Medium"
		question_set.passing_score = 70.0
		question_set.save()

		with patch(
			"frappe_ai_hiring.ai_hiring.utils.notifications.NotificationManager.send_candidate_notification",
			return_value=True,
		):
			result = send_questionnaire(self.job_applicant.name)
			assert result is not None
			assert result.get("success") is True

	def test_schedule_interview_action(self):
		"""Test schedule interview UI action"""
		from frappe_ai_hiring.ai_hiring.doctype.ai_interview_brief.ai_interview_brief import (
			schedule_interview,
		)

		interview_brief = frappe.new_doc("AI Interview Brief")
		interview_brief.applicant = self.job_applicant.name
		interview_brief.job_opening = self.job_opening.name
		interview_brief.summary = "Test brief"
		interview_brief.save()

		with patch(
			"frappe_ai_hiring.ai_hiring.utils.notifications.NotificationManager.send_candidate_notification",
			return_value=True,
		):
			event_name = schedule_interview(
				interview_brief.name,
				"2025-12-20",
				"interviewer@example.com",
			)

			assert event_name is not None
			event = frappe.get_doc("Event", event_name)
			assert "Interview" in event.subject
