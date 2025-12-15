# -*- coding: utf-8 -*-
# Copyright (c) 2024, Your Company and contributors
# For license information, please see license.txt

"""
Unit tests for Interview Brief Generator service.
"""

from __future__ import unicode_literals

import pytest
from unittest.mock import patch
from ai_hiring.services.interview_brief import InterviewBriefGenerator


class TestInterviewBriefGenerator:
    """Test cases for InterviewBriefGenerator class."""
    
    def test_generate_brief_success(self, mock_llm_client, mock_parsed_resume, 
                                   mock_shortlisting_result, mock_answers):
        """Test successful interview brief generation."""
        brief_result = {
            "candidate_summary": "Strong Python developer with 7+ years of experience",
            "key_strengths": [
                "Excellent technical skills in Python and Django",
                "Proven leadership experience",
                "Strong problem-solving abilities"
            ],
            "areas_to_probe": [
                "Specific experience with microservices architecture",
                "Team collaboration approach",
                "Handling of technical challenges"
            ],
            "suggested_questions": [
                "Can you describe a complex microservices project you've led?",
                "How do you approach code reviews with junior developers?",
                "Tell me about a time you had to optimize a slow API endpoint."
            ],
            "technical_depth_questions": [
                "Explain your approach to database optimization",
                "How do you ensure API security?",
                "What's your experience with CI/CD pipelines?"
            ],
            "red_flags": [],
            "overall_recommendation": "Strong hire - proceed with technical interview"
        }
        
        mock_llm_client.generate_structured_output.return_value = {
            "success": True,
            "data": brief_result,
            "error": None
        }
        
        with patch('ai_hiring.services.interview_brief.LLMClient', return_value=mock_llm_client):
            generator = InterviewBriefGenerator()
            result = generator.generate_brief(
                resume_data=mock_parsed_resume,
                shortlisting_result=mock_shortlisting_result,
                questionnaire_results={"answers": mock_answers, "score": 95}
            )
        
        assert result["success"] is True
        assert "candidate_summary" in result["data"]
        assert len(result["data"]["key_strengths"]) > 0
        assert len(result["data"]["suggested_questions"]) > 0
    
    def test_generate_brief_without_questionnaire(self, mock_llm_client, mock_parsed_resume, 
                                                  mock_shortlisting_result):
        """Test brief generation without questionnaire data."""
        brief_result = {
            "candidate_summary": "Python developer",
            "key_strengths": ["Technical skills"],
            "areas_to_probe": ["General experience"],
            "suggested_questions": ["Tell me about your experience"],
            "technical_depth_questions": [],
            "red_flags": ["No questionnaire completed"],
            "overall_recommendation": "Proceed with caution"
        }
        
        mock_llm_client.generate_structured_output.return_value = {
            "success": True,
            "data": brief_result,
            "error": None
        }
        
        with patch('ai_hiring.services.interview_brief.LLMClient', return_value=mock_llm_client):
            generator = InterviewBriefGenerator()
            result = generator.generate_brief(
                resume_data=mock_parsed_resume,
                shortlisting_result=mock_shortlisting_result,
                questionnaire_results=None
            )
        
        assert result["success"] is True
        assert "No questionnaire" in str(result["data"]["red_flags"])
    
    def test_generate_brief_with_red_flags(self, mock_llm_client, mock_parsed_resume):
        """Test brief generation with identified red flags."""
        shortlisting_with_concerns = {
            "fit_score": 70,
            "ai_decision": "review",
            "key_strengths": ["Some Python experience"],
            "potential_concerns": [
                "Limited experience with required frameworks",
                "Job hopping - 3 jobs in 2 years",
                "No leadership experience"
            ]
        }
        
        brief_result = {
            "candidate_summary": "Mid-level Python developer",
            "key_strengths": ["Some relevant experience"],
            "areas_to_probe": ["Career stability", "Framework knowledge"],
            "suggested_questions": [
                "Why have you changed jobs frequently?",
                "How do you plan to close the framework knowledge gap?"
            ],
            "technical_depth_questions": [],
            "red_flags": [
                "Frequent job changes",
                "Limited framework experience"
            ],
            "overall_recommendation": "Conditional proceed - address concerns"
        }
        
        mock_llm_client.generate_structured_output.return_value = {
            "success": True,
            "data": brief_result,
            "error": None
        }
        
        with patch('ai_hiring.services.interview_brief.LLMClient', return_value=mock_llm_client):
            generator = InterviewBriefGenerator()
            result = generator.generate_brief(
                resume_data=mock_parsed_resume,
                shortlisting_result=shortlisting_with_concerns,
                questionnaire_results=None
            )
        
        assert result["success"] is True
        assert len(result["data"]["red_flags"]) > 0
        assert len(result["data"]["areas_to_probe"]) > 0
    
    def test_generate_technical_questions(self, mock_parsed_resume):
        """Test generation of technical depth questions."""
        generator = InterviewBriefGenerator()
        
        questions = generator._generate_technical_questions(
            skills=mock_parsed_resume["skills"],
            experience=mock_parsed_resume["experience"]
        )
        
        assert isinstance(questions, list)
        assert len(questions) > 0
    
    def test_identify_red_flags(self, mock_parsed_resume, mock_shortlisting_result):
        """Test red flag identification logic."""
        generator = InterviewBriefGenerator()
        
        # Test with good candidate - should have minimal red flags
        red_flags = generator._identify_red_flags(
            resume_data=mock_parsed_resume,
            shortlisting_result=mock_shortlisting_result
        )
        
        assert isinstance(red_flags, list)
        # Strong candidate should have few or no red flags
        assert len(red_flags) <= 1
    
    def test_generate_probing_areas(self, mock_shortlisting_result):
        """Test generation of areas to probe during interview."""
        generator = InterviewBriefGenerator()
        
        probing_areas = generator._generate_probing_areas(
            shortlisting_result=mock_shortlisting_result
        )
        
        assert isinstance(probing_areas, list)
        assert len(probing_areas) > 0
    
    def test_create_candidate_summary(self, mock_parsed_resume, mock_shortlisting_result):
        """Test candidate summary creation."""
        generator = InterviewBriefGenerator()
        
        summary = generator._create_summary(
            resume_data=mock_parsed_resume,
            shortlisting_result=mock_shortlisting_result
        )
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert mock_parsed_resume["name"] in summary or "experience" in summary.lower()
    
    def test_generate_brief_llm_error(self, mock_llm_client, mock_parsed_resume, 
                                     mock_shortlisting_result):
        """Test handling of LLM errors."""
        mock_llm_client.generate_structured_output.return_value = {
            "success": False,
            "data": None,
            "error": "API error"
        }
        
        with patch('ai_hiring.services.interview_brief.LLMClient', return_value=mock_llm_client):
            generator = InterviewBriefGenerator()
            result = generator.generate_brief(
                resume_data=mock_parsed_resume,
                shortlisting_result=mock_shortlisting_result
            )
        
        assert result["success"] is False
    
    def test_format_brief_for_display(self, mock_llm_client, mock_parsed_resume, 
                                     mock_shortlisting_result):
        """Test formatting of brief for display."""
        brief_result = {
            "candidate_summary": "Test summary",
            "key_strengths": ["Strength 1", "Strength 2"],
            "areas_to_probe": ["Area 1"],
            "suggested_questions": ["Question 1", "Question 2"],
            "technical_depth_questions": ["Tech Q1"],
            "red_flags": [],
            "overall_recommendation": "Proceed"
        }
        
        mock_llm_client.generate_structured_output.return_value = {
            "success": True,
            "data": brief_result,
            "error": None
        }
        
        with patch('ai_hiring.services.interview_brief.LLMClient', return_value=mock_llm_client):
            generator = InterviewBriefGenerator()
            result = generator.generate_brief(
                resume_data=mock_parsed_resume,
                shortlisting_result=mock_shortlisting_result
            )
        
        # Check that all expected sections are present
        assert "candidate_summary" in result["data"]
        assert "key_strengths" in result["data"]
        assert "suggested_questions" in result["data"]


class TestInterviewBriefIntegration:
    """Integration tests for interview brief generation."""
    
    def test_complete_interview_preparation_flow(self, mock_llm_client, mock_parsed_resume, 
                                                 mock_shortlisting_result, mock_answers):
        """Test complete flow from resume to interview brief."""
        # Generate brief with all available data
        brief_result = {
            "candidate_summary": "Excellent candidate with comprehensive experience",
            "key_strengths": [
                "Strong technical background",
                "Leadership experience",
                "Excellent questionnaire performance"
            ],
            "areas_to_probe": ["Specific project examples"],
            "suggested_questions": [
                "Describe your most challenging project",
                "How do you mentor junior developers?"
            ],
            "technical_depth_questions": [
                "Explain your approach to system design",
                "How do you handle technical debt?"
            ],
            "red_flags": [],
            "overall_recommendation": "Strong hire - highly recommended"
        }
        
        mock_llm_client.generate_structured_output.return_value = {
            "success": True,
            "data": brief_result,
            "error": None
        }
        
        with patch('ai_hiring.services.interview_brief.LLMClient', return_value=mock_llm_client):
            generator = InterviewBriefGenerator()
            result = generator.generate_brief(
                resume_data=mock_parsed_resume,
                shortlisting_result=mock_shortlisting_result,
                questionnaire_results={"answers": mock_answers, "score": 95}
            )
        
        assert result["success"] is True
        assert "Strong" in result["data"]["overall_recommendation"] or \
               "highly" in result["data"]["overall_recommendation"].lower()
        assert len(result["data"]["suggested_questions"]) >= 2
    
    def test_brief_generation_for_rejected_candidate(self, mock_llm_client, mock_parsed_resume):
        """Test brief generation for a rejected candidate."""
        rejection_result = {
            "fit_score": 30,
            "ai_decision": "reject",
            "key_strengths": [],
            "potential_concerns": [
                "Insufficient technical skills",
                "No relevant experience"
            ]
        }
        
        brief_result = {
            "candidate_summary": "Does not meet minimum requirements",
            "key_strengths": [],
            "areas_to_probe": [],
            "suggested_questions": [],
            "technical_depth_questions": [],
            "red_flags": ["Insufficient qualifications"],
            "overall_recommendation": "Do not proceed with interview"
        }
        
        mock_llm_client.generate_structured_output.return_value = {
            "success": True,
            "data": brief_result,
            "error": None
        }
        
        with patch('ai_hiring.services.interview_brief.LLMClient', return_value=mock_llm_client):
            generator = InterviewBriefGenerator()
            result = generator.generate_brief(
                resume_data=mock_parsed_resume,
                shortlisting_result=rejection_result
            )
        
        assert result["success"] is True
        assert "not proceed" in result["data"]["overall_recommendation"].lower() or \
               len(result["data"]["red_flags"]) > 0
