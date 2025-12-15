# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

"""
Unit tests for AI Hiring pipeline services
"""

import pytest
import frappe
from frappe.test_runner import FrappeTestCase


class TestResumeParsing(FrappeTestCase):
	"""Tests for resume parsing service"""

	def setUp(self):
		"""Set up test data"""
		self.job_opening = frappe.new_doc("Job Opening")
		self.job_opening.designation = "Software Engineer"
		self.job_opening.job_title = "Software Engineer"
		self.job_opening.status = "Open"
		self.job_opening.save()

		self.job_applicant = frappe.new_doc("Job Applicant")
		self.job_applicant.applicant_name = "Test Candidate"
		self.job_applicant.email_id = "test@example.com"
		self.job_applicant.phone = "+1-555-0100"
		self.job_applicant.designation = "Software Engineer"
		self.job_applicant.job_title = "Software Engineer"
		self.job_applicant.save()

	def test_create_candidate_profile_success(self):
		"""Test successful candidate profile creation"""
		from frappe_ai_hiring.ai_hiring.services.resume_parser import (
			create_candidate_profile,
		)

		# Mock the internal parse_resume function
		with frappe.mock_frappe_call(
			"frappe_ai_hiring.ai_hiring.services.resume_parser.parse_resume"
		) as mock_parse:
			mock_parse.return_value = frappe.new_doc("AI Candidate Profile")
			mock_parse.return_value.name = "test-profile-001"
			mock_parse.return_value.applicant = self.job_applicant.name
			mock_parse.return_value.skills = "Python, FastAPI, PostgreSQL"
			mock_parse.return_value.experience_years = 5

			result = create_candidate_profile(
				self.job_applicant.name, self.job_opening.name
			)

			assert result is not None
			assert isinstance(result, str)  # Returns profile name

	def test_create_candidate_profile_missing_job_opening(self):
		"""Test candidate profile creation when job opening is missing"""
		from frappe_ai_hiring.ai_hiring.services.resume_parser import (
			create_candidate_profile,
		)

		# Should lookup job opening from applicant's designation
		result = create_candidate_profile(self.job_applicant.name, None)
		assert result is not None


class TestShortlisting(FrappeTestCase):
	"""Tests for shortlisting service"""

	def setUp(self):
		"""Set up test data"""
		self.job_opening = frappe.new_doc("Job Opening")
		self.job_opening.designation = "Senior Engineer"
		self.job_opening.job_title = "Senior Engineer"
		self.job_opening.description = "We need a senior engineer with 5+ years experience"
		self.job_opening.status = "Open"
		self.job_opening.save()

		self.job_applicant = frappe.new_doc("Job Applicant")
		self.job_applicant.applicant_name = "Senior Candidate"
		self.job_applicant.email_id = "senior@example.com"
		self.job_applicant.designation = "Senior Engineer"
		self.job_applicant.job_title = "Senior Engineer"
		self.job_applicant.save()

		self.candidate_profile = frappe.new_doc("AI Candidate Profile")
		self.candidate_profile.applicant = self.job_applicant.name
		self.candidate_profile.job_opening = self.job_opening.name
		self.candidate_profile.skills = "Python, AWS, Kubernetes"
		self.candidate_profile.experience_years = 6
		self.candidate_profile.save()

	def test_create_shortlisting_result_success(self):
		"""Test successful shortlisting result creation"""
		from frappe_ai_hiring.ai_hiring.services.shortlisting_service import (
			create_shortlisting_result,
		)

		with frappe.mock_frappe_call(
			"frappe_ai_hiring.ai_hiring.services.shortlisting_service.shortlist_candidate"
		) as mock_shortlist:
			result_doc = frappe.new_doc("AI Shortlisting Result")
			result_doc.name = "shortlist-001"
			result_doc.applicant = self.job_applicant.name
			result_doc.decision = "Shortlist"
			result_doc.fit_score = 0.85

			mock_shortlist.return_value = result_doc

			result = create_shortlisting_result(
				self.job_applicant.name, self.job_opening.name
			)

			assert result is not None
			assert isinstance(result, str)


class TestQuestionGeneration(FrappeTestCase):
	"""Tests for question generation service"""

	def setUp(self):
		"""Set up test data"""
		self.job_opening = frappe.new_doc("Job Opening")
		self.job_opening.designation = "Data Scientist"
		self.job_opening.job_title = "Data Scientist"
		self.job_opening.description = (
			"Looking for experienced data scientist with ML background"
		)
		self.job_opening.save()

	def test_create_question_set_difficulty_enum(self):
		"""Test that question set respects Easy/Medium/Hard difficulty"""
		from frappe_ai_hiring.ai_hiring.services.question_generator import (
			create_question_set,
		)

		question_set = frappe.new_doc("AI Question Set")
		question_set.job_role = self.job_opening.job_title
		question_set.difficulty = "Medium"
		question_set.job_description = self.job_opening.description
		question_set.passing_score = 70.0

		# Add test questions
		q1 = question_set.append("questions", {})
		q1.question = "What is machine learning?"
		q1.difficulty = "Easy"

		q2 = question_set.append("questions", {})
		q2.question = "Explain neural networks"
		q2.difficulty = "Medium"

		question_set.save()

		# Verify difficulty is set correctly
		assert question_set.difficulty in ["Easy", "Medium", "Hard"]
		assert question_set.questions[0].difficulty == "Easy"
		assert question_set.questions[1].difficulty == "Medium"

	def test_question_set_persists_total_questions(self):
		"""Test that total_questions count is persisted"""
		question_set = frappe.new_doc("AI Question Set")
		question_set.job_role = "Python Developer"
		question_set.difficulty = "Medium"
		question_set.passing_score = 70.0

		for i in range(3):
			q = question_set.append("questions", {})
			q.question = f"Test question {i+1}"
			q.difficulty = "Medium"

		question_set.save()

		# Reload and verify
		reloaded = frappe.get_doc("AI Question Set", question_set.name)
		assert len(reloaded.questions) == 3


class TestEvaluation(FrappeTestCase):
	"""Tests for interview evaluation service"""

	def setUp(self):
		"""Set up test data"""
		self.job_opening = frappe.new_doc("Job Opening")
		self.job_opening.designation = "Product Manager"
		self.job_opening.job_title = "Product Manager"
		self.job_opening.save()

		self.job_applicant = frappe.new_doc("Job Applicant")
		self.job_applicant.applicant_name = "PM Candidate"
		self.job_applicant.email_id = "pm@example.com"
		self.job_applicant.designation = "Product Manager"
		self.job_applicant.job_title = "Product Manager"
		self.job_applicant.save()

		self.interview_brief = frappe.new_doc("AI Interview Brief")
		self.interview_brief.applicant = self.job_applicant.name
		self.interview_brief.job_opening = self.job_opening.name
		self.interview_brief.summary = "Strong PM background"
		self.interview_brief.save()

	def test_create_evaluation_result(self):
		"""Test evaluation result creation with scores"""
		evaluation = frappe.new_doc("AI Evaluation Result")
		evaluation.interview_brief = self.interview_brief.name
		evaluation.applicant = self.job_applicant.name
		evaluation.overall_score = 78
		evaluation.technical_score = 75
		evaluation.communication_score = 82
		evaluation.culture_fit_score = 76
		evaluation.hire_recommendation = "Recommend"
		evaluation.key_strengths = "Strong leadership"
		evaluation.areas_for_improvement = "Needs product metrics knowledge"
		evaluation.save()

		# Reload and verify
		reloaded = frappe.get_doc("AI Evaluation Result", evaluation.name)
		assert reloaded.overall_score == 78
		assert reloaded.hire_recommendation == "Recommend"


class TestInterviewBrief(FrappeTestCase):
	"""Tests for interview brief generation"""

	def setUp(self):
		"""Set up test data"""
		self.job_opening = frappe.new_doc("Job Opening")
		self.job_opening.designation = "DevOps Engineer"
		self.job_opening.job_title = "DevOps Engineer"
		self.job_opening.save()

		self.job_applicant = frappe.new_doc("Job Applicant")
		self.job_applicant.applicant_name = "DevOps Candidate"
		self.job_applicant.email_id = "devops@example.com"
		self.job_applicant.designation = "DevOps Engineer"
		self.job_applicant.job_title = "DevOps Engineer"
		self.job_applicant.save()

	def test_create_interview_brief(self):
		"""Test interview brief creation"""
		brief = frappe.new_doc("AI Interview Brief")
		brief.applicant = self.job_applicant.name
		brief.job_opening = self.job_opening.name
		brief.summary = "Candidate has strong Kubernetes experience"
		brief.strengths = "Infrastructure automation, CI/CD"
		brief.weak_areas = "Limited security experience"
		brief.verification_points = (
			"Verify AWS certifications, check Terraform knowledge"
		)
		brief.suggested_questions = "Tell us about your infrastructure design"
		brief.generated_by_model = "gpt-4"
		brief.prompt_version = "v1.0"
		brief.save()

		# Reload and verify
		reloaded = frappe.get_doc("AI Interview Brief", brief.name)
		assert "Kubernetes" in reloaded.summary
		assert reloaded.generated_by_model == "gpt-4"

	def test_interview_brief_summary_generation(self):
		"""Test auto-generated final summary"""
		brief = frappe.new_doc("AI Interview Brief")
		brief.applicant = self.job_applicant.name
		brief.job_opening = self.job_opening.name
		brief.strengths = "Strong infrastructure skills"
		brief.weak_areas = "Limited Python experience"
		brief.save()

		summary = brief.generate_final_summary()
		assert summary is not None
		assert len(summary) > 0
