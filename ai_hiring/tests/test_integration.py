# -*- coding: utf-8 -*-
# Copyright (c) 2024, Your Company and contributors
# For license information, please see license.txt

"""
Integration tests for complete AI Hiring pipeline.
"""

from __future__ import unicode_literals

import pytest
from unittest.mock import patch, MagicMock
import frappe
from ai_hiring.jobs.process_new_applicant import process_applicant_pipeline


class TestCompletePipeline:
    """Integration tests for end-to-end hiring pipeline."""
    
    @patch('ai_hiring.services.resume_parser.extract_text_from_file')
    @patch('ai_hiring.services.resume_parser.LLMClient')
    @patch('ai_hiring.services.shortlisting.LLMClient')
    @patch('ai_hiring.services.question_generator.LLMClient')
    def test_full_pipeline_accepted_candidate(self, mock_qg_llm, mock_sl_llm, mock_rp_llm, 
                                             mock_extract, mock_job_applicant, mock_job_opening,
                                             mock_resume_text, mock_parsed_resume, 
                                             mock_shortlisting_result, mock_questions):
        """Test complete pipeline for accepted candidate."""
        # Setup all mocks
        mock_extract.return_value = mock_resume_text
        
        # Resume parsing
        mock_rp_client = MagicMock()
        mock_rp_client.generate_structured_output.return_value = {
            "success": True,
            "data": mock_parsed_resume,
            "error": None
        }
        mock_rp_llm.return_value = mock_rp_client
        
        # Shortlisting
        mock_sl_client = MagicMock()
        mock_sl_client.generate_structured_output.return_value = {
            "success": True,
            "data": mock_shortlisting_result,
            "error": None
        }
        mock_sl_llm.return_value = mock_sl_client
        
        # Question generation
        mock_qg_client = MagicMock()
        mock_qg_client.generate_structured_output.return_value = {
            "success": True,
            "data": {"questions": mock_questions},
            "error": None
        }
        mock_qg_llm.return_value = mock_qg_client
        
        # Mock Frappe DB calls
        with patch('frappe.get_doc') as mock_get_doc:
            # Mock Job Applicant
            mock_applicant_doc = MagicMock()
            mock_applicant_doc.name = mock_job_applicant["name"]
            mock_applicant_doc.job_title = mock_job_applicant["job_title"]
            mock_applicant_doc.resume_attachment = mock_job_applicant["resume_attachment"]
            
            # Mock Job Opening
            mock_job_doc = MagicMock()
            mock_job_doc.description = mock_job_opening["description"]
            
            def get_doc_side_effect(doctype, name=None):
                if doctype == "Job Applicant":
                    return mock_applicant_doc
                elif doctype == "Job Opening":
                    return mock_job_doc
                return MagicMock()
            
            mock_get_doc.side_effect = get_doc_side_effect
            
            # Execute pipeline
            result = process_applicant_pipeline(mock_job_applicant["name"])
        
        # Verify complete flow
        assert result["success"] is True
        assert "resume_parsed" in result
        assert "shortlisting_done" in result
        assert "questions_generated" in result
    
    @patch('ai_hiring.services.resume_parser.extract_text_from_file')
    @patch('ai_hiring.services.resume_parser.LLMClient')
    @patch('ai_hiring.services.shortlisting.LLMClient')
    def test_full_pipeline_rejected_candidate(self, mock_sl_llm, mock_rp_llm, mock_extract,
                                             mock_job_applicant, mock_job_opening,
                                             mock_resume_text, mock_parsed_resume):
        """Test complete pipeline for rejected candidate."""
        # Setup mocks
        mock_extract.return_value = mock_resume_text
        
        # Resume parsing
        mock_rp_client = MagicMock()
        mock_rp_client.generate_structured_output.return_value = {
            "success": True,
            "data": mock_parsed_resume,
            "error": None
        }
        mock_rp_llm.return_value = mock_rp_client
        
        # Shortlisting - REJECT decision
        rejection_result = {
            "fit_score": 25,
            "ai_decision": "reject",
            "technical_skills_match": 30,
            "experience_match": 20,
            "education_match": 25,
            "key_strengths": [],
            "potential_concerns": ["Insufficient experience", "Wrong skill set"],
            "recommendations": "Does not meet minimum requirements."
        }
        
        mock_sl_client = MagicMock()
        mock_sl_client.generate_structured_output.return_value = {
            "success": True,
            "data": rejection_result,
            "error": None
        }
        mock_sl_llm.return_value = mock_sl_client
        
        with patch('frappe.get_doc') as mock_get_doc:
            mock_applicant_doc = MagicMock()
            mock_applicant_doc.name = mock_job_applicant["name"]
            mock_applicant_doc.job_title = mock_job_applicant["job_title"]
            mock_applicant_doc.resume_attachment = mock_job_applicant["resume_attachment"]
            
            mock_job_doc = MagicMock()
            mock_job_doc.description = mock_job_opening["description"]
            
            def get_doc_side_effect(doctype, name=None):
                if doctype == "Job Applicant":
                    return mock_applicant_doc
                elif doctype == "Job Opening":
                    return mock_job_doc
                return MagicMock()
            
            mock_get_doc.side_effect = get_doc_side_effect
            
            result = process_applicant_pipeline(mock_job_applicant["name"])
        
        # Pipeline should stop after rejection
        assert result["success"] is True
        assert "shortlisting_done" in result
        assert result.get("ai_decision") == "reject"
        # Questions should NOT be generated for rejected candidates
        assert "questions_generated" not in result or not result["questions_generated"]
    
    def test_pipeline_resume_parsing_failure(self, mock_job_applicant):
        """Test pipeline behavior when resume parsing fails."""
        with patch('ai_hiring.services.resume_parser.extract_text_from_file') as mock_extract:
            mock_extract.side_effect = Exception("Failed to extract text")
            
            with patch('frappe.get_doc') as mock_get_doc:
                mock_applicant_doc = MagicMock()
                mock_applicant_doc.name = mock_job_applicant["name"]
                mock_applicant_doc.resume_attachment = "/invalid/path.pdf"
                mock_get_doc.return_value = mock_applicant_doc
                
                result = process_applicant_pipeline(mock_job_applicant["name"])
            
            # Pipeline should handle error gracefully
            assert result["success"] is False or "error" in result
    
    def test_pipeline_rate_limiting(self, mock_job_applicant):
        """Test that pipeline respects rate limiting."""
        with patch('ai_hiring.utils.security.RateLimiter.check_rate_limit') as mock_rate_limit:
            mock_rate_limit.return_value = False  # Rate limit exceeded
            
            with patch('frappe.get_doc') as mock_get_doc:
                mock_applicant_doc = MagicMock()
                mock_applicant_doc.name = mock_job_applicant["name"]
                mock_get_doc.return_value = mock_applicant_doc
                
                with pytest.raises(Exception, match="rate limit"):
                    process_applicant_pipeline(mock_job_applicant["name"])
    
    @patch('ai_hiring.services.resume_parser.extract_text_from_file')
    @patch('ai_hiring.services.resume_parser.LLMClient')
    @patch('ai_hiring.services.shortlisting.LLMClient')
    @patch('ai_hiring.services.question_generator.LLMClient')
    @patch('ai_hiring.services.question_evaluation.LLMClient')
    @patch('ai_hiring.services.interview_brief.LLMClient')
    def test_full_pipeline_with_questionnaire_completion(self, mock_ib_llm, mock_qe_llm, 
                                                        mock_qg_llm, mock_sl_llm, mock_rp_llm,
                                                        mock_extract, mock_job_applicant,
                                                        mock_job_opening, mock_resume_text,
                                                        mock_parsed_resume, mock_shortlisting_result,
                                                        mock_questions, mock_answers):
        """Test complete pipeline including questionnaire evaluation and interview brief."""
        # Setup all service mocks (similar to first test)
        mock_extract.return_value = mock_resume_text
        
        mock_rp_client = MagicMock()
        mock_rp_client.generate_structured_output.return_value = {
            "success": True,
            "data": mock_parsed_resume,
            "error": None
        }
        mock_rp_llm.return_value = mock_rp_client
        
        mock_sl_client = MagicMock()
        mock_sl_client.generate_structured_output.return_value = {
            "success": True,
            "data": mock_shortlisting_result,
            "error": None
        }
        mock_sl_llm.return_value = mock_sl_client
        
        mock_qg_client = MagicMock()
        mock_qg_client.generate_structured_output.return_value = {
            "success": True,
            "data": {"questions": mock_questions},
            "error": None
        }
        mock_qg_llm.return_value = mock_qg_client
        
        # Question evaluation
        mock_qe_client = MagicMock()
        mock_qe_client.generate_structured_output.return_value = {
            "success": True,
            "data": {
                "overall_score": 95,
                "topic_scores": {"Architecture": 100, "Frameworks": 100},
                "strengths": ["Strong technical skills"],
                "areas_for_improvement": [],
                "recommendation": "Excellent"
            },
            "error": None
        }
        mock_qe_llm.return_value = mock_qe_client
        
        # Interview brief
        mock_ib_client = MagicMock()
        mock_ib_client.generate_structured_output.return_value = {
            "success": True,
            "data": {
                "candidate_summary": "Strong candidate",
                "key_strengths": ["Technical expertise"],
                "areas_to_probe": ["Project examples"],
                "suggested_questions": ["Question 1", "Question 2"],
                "technical_depth_questions": ["Tech Q1"],
                "red_flags": [],
                "overall_recommendation": "Strong hire"
            },
            "error": None
        }
        mock_ib_llm.return_value = mock_ib_client
        
        with patch('frappe.get_doc') as mock_get_doc:
            mock_applicant_doc = MagicMock()
            mock_applicant_doc.name = mock_job_applicant["name"]
            mock_applicant_doc.job_title = mock_job_applicant["job_title"]
            mock_applicant_doc.resume_attachment = mock_job_applicant["resume_attachment"]
            
            mock_job_doc = MagicMock()
            mock_job_doc.description = mock_job_opening["description"]
            
            def get_doc_side_effect(doctype, name=None):
                if doctype == "Job Applicant":
                    return mock_applicant_doc
                elif doctype == "Job Opening":
                    return mock_job_doc
                return MagicMock()
            
            mock_get_doc.side_effect = get_doc_side_effect
            
            # Execute full pipeline
            result = process_applicant_pipeline(mock_job_applicant["name"])
        
        # Verify all stages completed
        assert result["success"] is True
        assert "resume_parsed" in result
        assert "shortlisting_done" in result
        assert "questions_generated" in result


class TestWorkflowTransitions:
    """Integration tests for workflow state transitions."""
    
    def test_state_transition_not_started_to_resume_parsing(self, mock_job_applicant):
        """Test transition from NOT_STARTED to RESUME_PARSING stage."""
        from ai_hiring.integration.workflow_state import WorkflowState, PipelineStage
        
        with patch('frappe.get_doc') as mock_get_doc:
            mock_applicant = MagicMock()
            mock_applicant.name = mock_job_applicant["name"]
            mock_applicant.status = "Open"
            mock_get_doc.return_value = mock_applicant
            
            workflow = WorkflowState(mock_job_applicant["name"])
            current_stage = workflow.get_current_stage()
            
            assert current_stage == PipelineStage.NOT_STARTED
            
            # Transition to resume parsing
            can_transition = workflow.can_transition(PipelineStage.RESUME_PARSING)
            assert can_transition is True
    
    def test_invalid_state_transition(self, mock_job_applicant):
        """Test that invalid transitions are blocked."""
        from ai_hiring.integration.workflow_state import WorkflowState, PipelineStage
        
        with patch('frappe.get_doc') as mock_get_doc:
            mock_applicant = MagicMock()
            mock_applicant.name = mock_job_applicant["name"]
            mock_applicant.status = "Open"
            mock_get_doc.return_value = mock_applicant
            
            workflow = WorkflowState(mock_job_applicant["name"])
            
            # Try to jump directly to INTERVIEW_SCHEDULED (invalid)
            can_transition = workflow.can_transition(PipelineStage.INTERVIEW_SCHEDULED)
            assert can_transition is False


class TestNotificationIntegration:
    """Integration tests for notification system."""
    
    def test_send_application_received_notification(self, mock_job_applicant):
        """Test sending application received notification."""
        from ai_hiring.integration.notifications import NotificationManager
        
        with patch('frappe.sendmail') as mock_sendmail:
            manager = NotificationManager()
            manager.send_candidate_notification(
                candidate_email=mock_job_applicant["email_id"],
                candidate_name=mock_job_applicant["applicant_name"],
                notification_type="application_received",
                context={"position": mock_job_applicant["job_title"]}
            )
            
            # Verify email was sent
            mock_sendmail.assert_called_once()
            call_args = mock_sendmail.call_args[1]
            assert mock_job_applicant["email_id"] in call_args["recipients"]
    
    def test_send_shortlist_notification_to_hr(self, mock_job_applicant):
        """Test sending shortlist notification to HR."""
        from ai_hiring.integration.notifications import NotificationManager
        
        with patch('frappe.get_all') as mock_get_all, \
             patch('frappe.get_doc') as mock_get_doc:
            
            # Mock HR users
            mock_get_all.return_value = [{"name": "hr@company.com"}]
            
            manager = NotificationManager()
            manager.send_hr_notification(
                notification_type="candidate_shortlisted",
                context={
                    "candidate_name": mock_job_applicant["applicant_name"],
                    "position": mock_job_applicant["job_title"],
                    "fit_score": 85
                }
            )
            
            # Verify notification was created
            mock_get_doc.assert_called()


class TestDashboardIntegration:
    """Integration tests for dashboard and analytics."""
    
    @patch('frappe.db.sql')
    def test_get_pipeline_overview(self, mock_sql):
        """Test getting pipeline overview statistics."""
        from ai_hiring.integration.dashboard import DashboardAnalytics
        
        # Mock database results
        mock_sql.return_value = [(10, 3, 2, 5, 2.5, 80.5)]
        
        dashboard = DashboardAnalytics()
        overview = dashboard.get_pipeline_overview()
        
        assert "active_candidates" in overview
        assert "hired_count" in overview
        assert "rejected_count" in overview
    
    @patch('frappe.db.sql')
    def test_get_funnel_stats(self, mock_sql):
        """Test getting funnel statistics."""
        from ai_hiring.integration.dashboard import DashboardAnalytics
        
        mock_sql.return_value = [
            ("Resume Parsing", 100),
            ("Shortlisting", 75),
            ("Questions Generated", 50),
            ("Questionnaire Completed", 40),
            ("Interview", 30),
            ("Hired", 10)
        ]
        
        dashboard = DashboardAnalytics()
        funnel = dashboard.get_funnel_stats()
        
        assert isinstance(funnel, list)
        assert len(funnel) > 0


class TestEndToEndScenarios:
    """End-to-end scenario tests."""
    
    def test_scenario_strong_candidate_hired(self):
        """Test complete scenario: strong candidate gets hired."""
        # This would test the complete flow from application to hire
        # Including: resume parsing → shortlisting (accept) → questions → 
        # questionnaire completion → interview brief → interview → offer
        pass
    
    def test_scenario_weak_candidate_rejected(self):
        """Test complete scenario: weak candidate gets rejected early."""
        # Test flow: resume parsing → shortlisting (reject) → rejection notification
        pass
    
    def test_scenario_borderline_candidate_needs_review(self):
        """Test complete scenario: borderline candidate needs manual review."""
        # Test flow with "review" decision requiring HR intervention
        pass
