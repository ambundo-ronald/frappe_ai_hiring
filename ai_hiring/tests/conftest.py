# -*- coding: utf-8 -*-
# Copyright (c) 2024, Your Company and contributors
# For license information, please see license.txt

"""
Pytest fixtures and test configuration for AI Hiring tests.
"""

from __future__ import unicode_literals

import pytest
import frappe
from unittest.mock import MagicMock, patch
from datetime import datetime


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing without making real API calls."""
    with patch('ai_hiring.utils.llm_client.LLMClient') as mock:
        client_instance = MagicMock()
        
        # Mock successful response
        client_instance.generate_structured_output.return_value = {
            "success": True,
            "data": {
                "name": "Test Candidate",
                "email": "test@example.com"
            },
            "error": None,
            "raw_response": "Mocked response"
        }
        
        mock.return_value = client_instance
        yield client_instance


@pytest.fixture
def mock_job_applicant():
    """Create a mock Job Applicant document."""
    return {
        "name": "JOB-APP-2024-00001",
        "applicant_name": "John Doe",
        "email_id": "john.doe@example.com",
        "job_title": "Senior Python Developer",
        "status": "Open",
        "resume_attachment": "/files/resume.pdf",
        "creation": datetime.now(),
        "modified": datetime.now()
    }


@pytest.fixture
def mock_job_opening():
    """Create a mock Job Opening document."""
    return {
        "name": "JOB-OPEN-2024-00001",
        "job_title": "Senior Python Developer",
        "description": """
We are seeking an experienced Python developer with:
- 5+ years of Python experience
- Strong Django/Flask expertise
- Experience with REST APIs
- Knowledge of PostgreSQL
- Familiarity with Docker and AWS

Responsibilities:
- Design and implement backend services
- Write clean, maintainable code
- Collaborate with frontend team
- Mentor junior developers
        """,
        "status": "Open",
        "creation": datetime.now(),
        "modified": datetime.now()
    }


@pytest.fixture
def mock_resume_text():
    """Sample resume text for testing."""
    return """
John Doe
Senior Python Developer
Email: john.doe@example.com
Phone: +1-555-0123

SUMMARY
Experienced Python developer with 7+ years building scalable web applications.
Expert in Django, Flask, and FastAPI. Strong knowledge of databases and cloud platforms.

EXPERIENCE

Senior Python Developer | Tech Corp | 2020 - Present
- Designed and implemented microservices architecture using FastAPI
- Led team of 4 developers on e-commerce platform rebuild
- Improved API response time by 40% through optimization
- Implemented CI/CD pipelines with GitHub Actions and AWS

Python Developer | StartupXYZ | 2017 - 2020
- Built REST APIs using Django REST Framework
- Developed data processing pipelines with Celery
- Integrated third-party payment systems
- Wrote comprehensive unit tests with pytest

SKILLS
Languages: Python, JavaScript, SQL
Frameworks: Django, Flask, FastAPI, React
Databases: PostgreSQL, MySQL, Redis, MongoDB
Tools: Docker, Kubernetes, AWS, Git, Jenkins

EDUCATION
B.S. Computer Science | State University | 2017
    """


@pytest.fixture
def mock_parsed_resume():
    """Sample parsed resume data."""
    return {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "phone": "+1-555-0123",
        "summary": "Experienced Python developer with 7+ years building scalable web applications.",
        "experience": [
            {
                "company": "Tech Corp",
                "title": "Senior Python Developer",
                "duration": "2020 - Present",
                "description": "Designed and implemented microservices architecture"
            },
            {
                "company": "StartupXYZ",
                "title": "Python Developer",
                "duration": "2017 - 2020",
                "description": "Built REST APIs using Django REST Framework"
            }
        ],
        "education": [
            {
                "degree": "B.S. Computer Science",
                "institution": "State University",
                "year": "2017"
            }
        ],
        "skills": [
            "Python", "JavaScript", "SQL", "Django", "Flask", 
            "FastAPI", "React", "PostgreSQL", "Docker", "AWS"
        ],
        "total_experience_years": 7
    }


@pytest.fixture
def mock_shortlisting_result():
    """Sample AI shortlisting result."""
    return {
        "fit_score": 85,
        "ai_decision": "shortlist",
        "technical_skills_match": 90,
        "experience_match": 85,
        "education_match": 80,
        "key_strengths": [
            "7+ years of Python experience",
            "Strong expertise in Django and Flask",
            "Proven experience with REST APIs",
            "Good knowledge of PostgreSQL and AWS"
        ],
        "potential_concerns": [
            "No specific mention of Docker expertise level"
        ],
        "recommendations": "Strong candidate with excellent technical match. Schedule technical interview."
    }


@pytest.fixture
def mock_questions():
    """Sample AI-generated questions."""
    return [
        {
            "question": "Do you have experience with microservices architecture?",
            "topic": "Architecture",
            "weight": 10
        },
        {
            "question": "Have you worked with FastAPI framework?",
            "topic": "Frameworks",
            "weight": 8
        },
        {
            "question": "Do you have experience with Docker containerization?",
            "topic": "DevOps",
            "weight": 7
        },
        {
            "question": "Have you led a development team before?",
            "topic": "Leadership",
            "weight": 6
        },
        {
            "question": "Do you have AWS cloud platform experience?",
            "topic": "Cloud",
            "weight": 8
        }
    ]


@pytest.fixture
def mock_answers():
    """Sample candidate answers to questionnaire."""
    return [
        {
            "question": "Do you have experience with microservices architecture?",
            "answer": "yes",
            "topic": "Architecture"
        },
        {
            "question": "Have you worked with FastAPI framework?",
            "answer": "yes",
            "topic": "Frameworks"
        },
        {
            "question": "Do you have experience with Docker containerization?",
            "answer": "yes",
            "topic": "DevOps"
        },
        {
            "question": "Have you led a development team before?",
            "answer": "yes",
            "topic": "Leadership"
        },
        {
            "question": "Do you have AWS cloud platform experience?",
            "answer": "yes",
            "topic": "Cloud"
        }
    ]


@pytest.fixture(autouse=True)
def frappe_session():
    """Setup Frappe test session."""
    frappe.set_user("Administrator")
    yield
    frappe.db.rollback()


@pytest.fixture
def disable_rate_limiting():
    """Disable rate limiting for tests."""
    with patch('ai_hiring.utils.security.RateLimiter.check_rate_limit') as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def mock_file_content():
    """Mock file reading for resume extraction."""
    def _mock_file(file_path: str) -> bytes:
        if file_path.endswith('.pdf'):
            return b"Mocked PDF content"
        elif file_path.endswith('.docx'):
            return b"Mocked DOCX content"
        elif file_path.endswith('.txt'):
            return b"Mocked TXT content"
        return b""
    
    return _mock_file
