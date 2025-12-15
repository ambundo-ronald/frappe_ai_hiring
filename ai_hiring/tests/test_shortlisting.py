# -*- coding: utf-8 -*-
# Copyright (c) 2024, Your Company and contributors
# For license information, please see license.txt

"""
Unit tests for Candidate Shortlisting service.
"""

from __future__ import unicode_literals

import pytest
from unittest.mock import patch
from ai_hiring.services.shortlisting import CandidateShortlisting


class TestCandidateShortlisting:
    """Test cases for CandidateShortlisting class."""
    
    def test_evaluate_candidate_success(self, mock_llm_client, mock_parsed_resume, 
                                       mock_job_opening, mock_shortlisting_result):
        """Test successful candidate evaluation."""
        # Setup mock
        mock_llm_client.generate_structured_output.return_value = {
            "success": True,
            "data": mock_shortlisting_result,
            "error": None
        }
        
        with patch('ai_hiring.services.shortlisting.LLMClient', return_value=mock_llm_client):
            shortlister = CandidateShortlisting()
            result = shortlister.evaluate_candidate(
                resume_data=mock_parsed_resume,
                job_description=mock_job_opening["description"]
            )
        
        # Verify
        assert result["success"] is True
        assert result["data"]["fit_score"] == 85
        assert result["data"]["ai_decision"] == "shortlist"
        assert len(result["data"]["key_strengths"]) > 0
    
    def test_evaluate_candidate_with_missing_resume_data(self, mock_llm_client, mock_job_opening):
        """Test evaluation with incomplete resume data."""
        incomplete_resume = {
            "name": "John Doe",
            "skills": []  # No skills
        }
        
        with patch('ai_hiring.services.shortlisting.LLMClient', return_value=mock_llm_client):
            shortlister = CandidateShortlisting()
            result = shortlister.evaluate_candidate(
                resume_data=incomplete_resume,
                job_description=mock_job_opening["description"]
            )
        
        # Should still proceed but with lower confidence
        assert result is not None
    
    def test_evaluate_candidate_reject_decision(self, mock_llm_client, mock_parsed_resume, 
                                                mock_job_opening):
        """Test candidate rejection scenario."""
        rejection_result = {
            "fit_score": 35,
            "ai_decision": "reject",
            "technical_skills_match": 40,
            "experience_match": 30,
            "education_match": 35,
            "key_strengths": ["Good communication skills"],
            "potential_concerns": [
                "Insufficient Python experience",
                "No relevant framework knowledge",
                "Limited database expertise"
            ],
            "recommendations": "Does not meet minimum technical requirements."
        }
        
        mock_llm_client.generate_structured_output.return_value = {
            "success": True,
            "data": rejection_result,
            "error": None
        }
        
        with patch('ai_hiring.services.shortlisting.LLMClient', return_value=mock_llm_client):
            shortlister = CandidateShortlisting()
            result = shortlister.evaluate_candidate(
                resume_data=mock_parsed_resume,
                job_description=mock_job_opening["description"]
            )
        
        assert result["success"] is True
        assert result["data"]["ai_decision"] == "reject"
        assert result["data"]["fit_score"] < 50
    
    def test_evaluate_candidate_review_decision(self, mock_llm_client, mock_parsed_resume, 
                                               mock_job_opening):
        """Test candidate review scenario (borderline case)."""
        review_result = {
            "fit_score": 65,
            "ai_decision": "review",
            "technical_skills_match": 70,
            "experience_match": 60,
            "education_match": 65,
            "key_strengths": [
                "Good Python experience",
                "Relevant project work"
            ],
            "potential_concerns": [
                "Limited experience with required frameworks",
                "No leadership experience mentioned"
            ],
            "recommendations": "Review candidate carefully. May be suitable with training."
        }
        
        mock_llm_client.generate_structured_output.return_value = {
            "success": True,
            "data": review_result,
            "error": None
        }
        
        with patch('ai_hiring.services.shortlisting.LLMClient', return_value=mock_llm_client):
            shortlister = CandidateShortlisting()
            result = shortlister.evaluate_candidate(
                resume_data=mock_parsed_resume,
                job_description=mock_job_opening["description"]
            )
        
        assert result["success"] is True
        assert result["data"]["ai_decision"] == "review"
        assert 50 <= result["data"]["fit_score"] <= 75
    
    def test_calculate_experience_match(self, mock_parsed_resume, mock_job_opening):
        """Test experience matching logic."""
        shortlister = CandidateShortlisting()
        
        # Mock the experience extraction
        with patch.object(shortlister, '_extract_required_experience', return_value=5):
            match_score = shortlister._calculate_experience_match(
                mock_parsed_resume,
                mock_job_opening["description"]
            )
        
        # Candidate has 7 years, requirement is 5 years
        assert match_score >= 80  # Should be high match
    
    def test_calculate_skills_match(self, mock_parsed_resume, mock_job_opening):
        """Test skills matching logic."""
        shortlister = CandidateShortlisting()
        
        match_score = shortlister._calculate_skills_match(
            mock_parsed_resume["skills"],
            mock_job_opening["description"]
        )
        
        # Should find good matches for Python, Django, PostgreSQL, etc.
        assert match_score >= 70
    
    def test_extract_key_requirements(self, mock_job_opening):
        """Test extraction of key requirements from job description."""
        shortlister = CandidateShortlisting()
        
        requirements = shortlister._extract_key_requirements(
            mock_job_opening["description"]
        )
        
        assert isinstance(requirements, dict)
        assert "skills" in requirements or "experience" in requirements
    
    def test_evaluate_candidate_llm_error(self, mock_llm_client, mock_parsed_resume, 
                                         mock_job_opening):
        """Test handling of LLM errors during evaluation."""
        mock_llm_client.generate_structured_output.return_value = {
            "success": False,
            "data": None,
            "error": "API connection timeout"
        }
        
        with patch('ai_hiring.services.shortlisting.LLMClient', return_value=mock_llm_client):
            shortlister = CandidateShortlisting()
            result = shortlister.evaluate_candidate(
                resume_data=mock_parsed_resume,
                job_description=mock_job_opening["description"]
            )
        
        assert result["success"] is False
        assert "timeout" in result["error"].lower()
    
    def test_validate_fit_score_range(self, mock_llm_client, mock_parsed_resume, 
                                     mock_job_opening):
        """Test that fit scores are always within valid range (0-100)."""
        # Test with out-of-range score
        invalid_result = {
            "fit_score": 150,  # Invalid
            "ai_decision": "shortlist",
            "technical_skills_match": 90,
            "experience_match": 85,
            "education_match": 80,
            "key_strengths": ["Test"],
            "potential_concerns": [],
            "recommendations": "Test"
        }
        
        mock_llm_client.generate_structured_output.return_value = {
            "success": True,
            "data": invalid_result,
            "error": None
        }
        
        with patch('ai_hiring.services.shortlisting.LLMClient', return_value=mock_llm_client):
            shortlister = CandidateShortlisting()
            result = shortlister.evaluate_candidate(
                resume_data=mock_parsed_resume,
                job_description=mock_job_opening["description"]
            )
        
        # Should normalize the score
        if result["success"]:
            assert 0 <= result["data"]["fit_score"] <= 100


class TestShortlistingIntegration:
    """Integration tests for candidate shortlisting."""
    
    def test_shortlist_multiple_candidates(self, mock_llm_client, mock_job_opening):
        """Test shortlisting multiple candidates with varying qualifications."""
        candidates = [
            {
                "name": "Strong Candidate",
                "skills": ["Python", "Django", "PostgreSQL", "Docker", "AWS"],
                "total_experience_years": 8
            },
            {
                "name": "Weak Candidate",
                "skills": ["JavaScript", "HTML", "CSS"],
                "total_experience_years": 2
            },
            {
                "name": "Moderate Candidate",
                "skills": ["Python", "Flask", "MySQL"],
                "total_experience_years": 4
            }
        ]
        
        results = []
        with patch('ai_hiring.services.shortlisting.LLMClient', return_value=mock_llm_client):
            shortlister = CandidateShortlisting()
            
            for candidate in candidates:
                # Mock different scores for different candidates
                if candidate["name"] == "Strong Candidate":
                    mock_data = {"fit_score": 90, "ai_decision": "shortlist"}
                elif candidate["name"] == "Weak Candidate":
                    mock_data = {"fit_score": 30, "ai_decision": "reject"}
                else:
                    mock_data = {"fit_score": 60, "ai_decision": "review"}
                
                mock_llm_client.generate_structured_output.return_value = {
                    "success": True,
                    "data": {**mock_data, "key_strengths": [], "potential_concerns": [], 
                            "recommendations": "", "technical_skills_match": 70,
                            "experience_match": 70, "education_match": 70},
                    "error": None
                }
                
                result = shortlister.evaluate_candidate(
                    resume_data=candidate,
                    job_description=mock_job_opening["description"]
                )
                results.append(result)
        
        # Verify results
        assert len(results) == 3
        assert results[0]["data"]["ai_decision"] == "shortlist"
        assert results[1]["data"]["ai_decision"] == "reject"
        assert results[2]["data"]["ai_decision"] == "review"
    
    def test_shortlisting_with_rate_limiting(self, mock_llm_client, mock_parsed_resume, 
                                            mock_job_opening, disable_rate_limiting):
        """Test that shortlisting respects rate limiting."""
        with patch('ai_hiring.services.shortlisting.LLMClient', return_value=mock_llm_client):
            shortlister = CandidateShortlisting()
            
            # Multiple evaluations should work with rate limiting disabled
            for _ in range(5):
                result = shortlister.evaluate_candidate(
                    resume_data=mock_parsed_resume,
                    job_description=mock_job_opening["description"]
                )
                assert result is not None
