# -*- coding: utf-8 -*-
# Copyright (c) 2024, Your Company and contributors
# For license information, please see license.txt

"""
Unit tests for Question Generator and Evaluation services.
"""

from __future__ import unicode_literals

import pytest
from unittest.mock import patch
from ai_hiring.services.question_generator import QuestionGenerator
from ai_hiring.services.question_evaluation import QuestionEvaluator


class TestQuestionGenerator:
    """Test cases for QuestionGenerator class."""
    
    def test_generate_questions_success(self, mock_llm_client, mock_parsed_resume, 
                                       mock_job_opening, mock_questions):
        """Test successful question generation."""
        mock_llm_client.generate_structured_output.return_value = {
            "success": True,
            "data": {"questions": mock_questions},
            "error": None
        }
        
        with patch('ai_hiring.services.question_generator.LLMClient', return_value=mock_llm_client):
            generator = QuestionGenerator()
            result = generator.generate_questions(
                resume_data=mock_parsed_resume,
                job_description=mock_job_opening["description"],
                num_questions=5
            )
        
        assert result["success"] is True
        assert len(result["data"]["questions"]) == 5
        assert all("question" in q for q in result["data"]["questions"])
        assert all("topic" in q for q in result["data"]["questions"])
        assert all("weight" in q for q in result["data"]["questions"])
    
    def test_generate_questions_custom_count(self, mock_llm_client, mock_parsed_resume, 
                                            mock_job_opening):
        """Test generating custom number of questions."""
        questions = [{"question": f"Question {i}", "topic": "Test", "weight": 5} 
                    for i in range(10)]
        
        mock_llm_client.generate_structured_output.return_value = {
            "success": True,
            "data": {"questions": questions},
            "error": None
        }
        
        with patch('ai_hiring.services.question_generator.LLMClient', return_value=mock_llm_client):
            generator = QuestionGenerator()
            result = generator.generate_questions(
                resume_data=mock_parsed_resume,
                job_description=mock_job_opening["description"],
                num_questions=10
            )
        
        assert len(result["data"]["questions"]) == 10
    
    def test_generate_questions_with_focus_areas(self, mock_llm_client, mock_parsed_resume, 
                                                 mock_job_opening):
        """Test question generation with specific focus areas."""
        focus_areas = ["Python", "Django", "REST APIs"]
        
        mock_llm_client.generate_structured_output.return_value = {
            "success": True,
            "data": {"questions": [
                {"question": "Do you have Python experience?", "topic": "Python", "weight": 10},
                {"question": "Have you worked with Django?", "topic": "Django", "weight": 9},
                {"question": "Do you know REST APIs?", "topic": "REST APIs", "weight": 8}
            ]},
            "error": None
        }
        
        with patch('ai_hiring.services.question_generator.LLMClient', return_value=mock_llm_client):
            generator = QuestionGenerator()
            result = generator.generate_questions(
                resume_data=mock_parsed_resume,
                job_description=mock_job_opening["description"],
                num_questions=3,
                focus_areas=focus_areas
            )
        
        assert result["success"] is True
        topics = [q["topic"] for q in result["data"]["questions"]]
        assert any(area in str(topics) for area in focus_areas)
    
    def test_validate_question_format(self):
        """Test question format validation."""
        generator = QuestionGenerator()
        
        # Valid question
        valid_q = {
            "question": "Do you have Python experience?",
            "topic": "Programming",
            "weight": 8
        }
        assert generator._validate_question(valid_q) is True
        
        # Invalid - missing field
        invalid_q1 = {
            "question": "Test question",
            "topic": "Test"
            # Missing weight
        }
        assert generator._validate_question(invalid_q1) is False
        
        # Invalid - wrong type
        invalid_q2 = {
            "question": "Test question",
            "topic": "Test",
            "weight": "high"  # Should be number
        }
        assert generator._validate_question(invalid_q2) is False
    
    def test_deduplicate_questions(self):
        """Test removal of duplicate questions."""
        generator = QuestionGenerator()
        
        questions = [
            {"question": "Do you have Python experience?", "topic": "Python", "weight": 8},
            {"question": "Do you have Python experience?", "topic": "Python", "weight": 8},  # Duplicate
            {"question": "Have you worked with Django?", "topic": "Django", "weight": 7}
        ]
        
        deduplicated = generator._deduplicate_questions(questions)
        
        assert len(deduplicated) == 2
        question_texts = [q["question"] for q in deduplicated]
        assert len(question_texts) == len(set(question_texts))
    
    def test_generate_questions_llm_error(self, mock_llm_client, mock_parsed_resume, 
                                         mock_job_opening):
        """Test handling of LLM errors."""
        mock_llm_client.generate_structured_output.return_value = {
            "success": False,
            "data": None,
            "error": "API error"
        }
        
        with patch('ai_hiring.services.question_generator.LLMClient', return_value=mock_llm_client):
            generator = QuestionGenerator()
            result = generator.generate_questions(
                resume_data=mock_parsed_resume,
                job_description=mock_job_opening["description"]
            )
        
        assert result["success"] is False


class TestQuestionEvaluator:
    """Test cases for QuestionEvaluator class."""
    
    def test_evaluate_answers_success(self, mock_llm_client, mock_questions, mock_answers):
        """Test successful answer evaluation."""
        evaluation_result = {
            "overall_score": 95,
            "topic_scores": {
                "Architecture": 100,
                "Frameworks": 100,
                "DevOps": 100,
                "Leadership": 100,
                "Cloud": 100
            },
            "strengths": [
                "Strong technical expertise across all areas",
                "Good leadership experience"
            ],
            "areas_for_improvement": [],
            "recommendation": "Highly qualified candidate. Proceed to interview."
        }
        
        mock_llm_client.generate_structured_output.return_value = {
            "success": True,
            "data": evaluation_result,
            "error": None
        }
        
        with patch('ai_hiring.services.question_evaluation.LLMClient', return_value=mock_llm_client):
            evaluator = QuestionEvaluator()
            result = evaluator.evaluate_answers(
                questions=mock_questions,
                answers=mock_answers
            )
        
        assert result["success"] is True
        assert result["data"]["overall_score"] == 95
        assert len(result["data"]["topic_scores"]) > 0
        assert "strengths" in result["data"]
    
    def test_evaluate_answers_with_no_answers(self, mock_llm_client, mock_questions):
        """Test evaluation when candidate provided no answers."""
        evaluation_result = {
            "overall_score": 0,
            "topic_scores": {},
            "strengths": [],
            "areas_for_improvement": ["No answers provided"],
            "recommendation": "Cannot evaluate - no responses."
        }
        
        mock_llm_client.generate_structured_output.return_value = {
            "success": True,
            "data": evaluation_result,
            "error": None
        }
        
        with patch('ai_hiring.services.question_evaluation.LLMClient', return_value=mock_llm_client):
            evaluator = QuestionEvaluator()
            result = evaluator.evaluate_answers(
                questions=mock_questions,
                answers=[]
            )
        
        assert result["data"]["overall_score"] == 0
    
    def test_calculate_score_by_topic(self, mock_questions, mock_answers):
        """Test topic-wise score calculation."""
        evaluator = QuestionEvaluator()
        
        topic_scores = evaluator._calculate_topic_scores(
            questions=mock_questions,
            answers=mock_answers
        )
        
        assert isinstance(topic_scores, dict)
        assert len(topic_scores) > 0
        assert all(0 <= score <= 100 for score in topic_scores.values())
    
    def test_calculate_weighted_score(self, mock_questions, mock_answers):
        """Test weighted score calculation."""
        evaluator = QuestionEvaluator()
        
        overall_score = evaluator._calculate_weighted_score(
            questions=mock_questions,
            answers=mock_answers
        )
        
        assert 0 <= overall_score <= 100
    
    def test_evaluate_partial_answers(self, mock_llm_client, mock_questions):
        """Test evaluation with partial answers."""
        partial_answers = [
            {"question": "Do you have experience with microservices architecture?", 
             "answer": "yes", "topic": "Architecture"},
            {"question": "Have you worked with FastAPI framework?", 
             "answer": "no", "topic": "Frameworks"}
            # Only 2 out of 5 questions answered
        ]
        
        evaluation_result = {
            "overall_score": 40,
            "topic_scores": {"Architecture": 100, "Frameworks": 0},
            "strengths": ["Good architecture knowledge"],
            "areas_for_improvement": ["Limited framework experience", "Incomplete questionnaire"],
            "recommendation": "Needs more information."
        }
        
        mock_llm_client.generate_structured_output.return_value = {
            "success": True,
            "data": evaluation_result,
            "error": None
        }
        
        with patch('ai_hiring.services.question_evaluation.LLMClient', return_value=mock_llm_client):
            evaluator = QuestionEvaluator()
            result = evaluator.evaluate_answers(
                questions=mock_questions,
                answers=partial_answers
            )
        
        assert result["data"]["overall_score"] < 50
    
    def test_identify_strengths_and_weaknesses(self, mock_answers):
        """Test identification of candidate strengths and weaknesses."""
        evaluator = QuestionEvaluator()
        
        # All yes answers should show strengths
        strengths = evaluator._identify_strengths(mock_answers)
        assert len(strengths) > 0
        
        # Create answers with some 'no' responses
        mixed_answers = mock_answers.copy()
        mixed_answers[2]["answer"] = "no"
        mixed_answers[3]["answer"] = "no"
        
        weaknesses = evaluator._identify_weaknesses(mixed_answers)
        assert len(weaknesses) > 0
    
    def test_evaluate_answers_llm_error(self, mock_llm_client, mock_questions, mock_answers):
        """Test handling of LLM errors during evaluation."""
        mock_llm_client.generate_structured_output.return_value = {
            "success": False,
            "data": None,
            "error": "API timeout"
        }
        
        with patch('ai_hiring.services.question_evaluation.LLMClient', return_value=mock_llm_client):
            evaluator = QuestionEvaluator()
            result = evaluator.evaluate_answers(
                questions=mock_questions,
                answers=mock_answers
            )
        
        assert result["success"] is False


class TestQuestionWorkflowIntegration:
    """Integration tests for question generation and evaluation workflow."""
    
    def test_complete_questionnaire_workflow(self, mock_llm_client, mock_parsed_resume, 
                                            mock_job_opening, mock_questions, mock_answers):
        """Test complete flow from generation to evaluation."""
        # Step 1: Generate questions
        mock_llm_client.generate_structured_output.return_value = {
            "success": True,
            "data": {"questions": mock_questions},
            "error": None
        }
        
        with patch('ai_hiring.services.question_generator.LLMClient', return_value=mock_llm_client):
            generator = QuestionGenerator()
            gen_result = generator.generate_questions(
                resume_data=mock_parsed_resume,
                job_description=mock_job_opening["description"]
            )
        
        assert gen_result["success"] is True
        questions = gen_result["data"]["questions"]
        
        # Step 2: Evaluate answers
        mock_llm_client.generate_structured_output.return_value = {
            "success": True,
            "data": {
                "overall_score": 95,
                "topic_scores": {"Architecture": 100, "Frameworks": 100},
                "strengths": ["Strong technical skills"],
                "areas_for_improvement": [],
                "recommendation": "Excellent candidate"
            },
            "error": None
        }
        
        with patch('ai_hiring.services.question_evaluation.LLMClient', return_value=mock_llm_client):
            evaluator = QuestionEvaluator()
            eval_result = evaluator.evaluate_answers(
                questions=questions,
                answers=mock_answers
            )
        
        assert eval_result["success"] is True
        assert eval_result["data"]["overall_score"] > 80
