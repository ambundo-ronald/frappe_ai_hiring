# -*- coding: utf-8 -*-
# Copyright (c) 2024, Your Company and contributors
# For license information, please see license.txt

"""
Unit tests for Resume Parser service.
"""

from __future__ import unicode_literals

import pytest
from unittest.mock import patch, MagicMock
from ai_hiring.services.resume_parser import ResumeParser, extract_text_from_file


class TestResumeParser:
    """Test cases for ResumeParser class."""
    
    def test_parse_resume_success(self, mock_llm_client, mock_resume_text, mock_parsed_resume):
        """Test successful resume parsing."""
        # Setup mock
        mock_llm_client.generate_structured_output.return_value = {
            "success": True,
            "data": mock_parsed_resume,
            "error": None
        }
        
        # Execute
        with patch('ai_hiring.services.resume_parser.LLMClient', return_value=mock_llm_client):
            parser = ResumeParser()
            result = parser.parse_resume(mock_resume_text)
        
        # Verify
        assert result["success"] is True
        assert result["data"]["name"] == "John Doe"
        assert result["data"]["email"] == "john.doe@example.com"
        assert len(result["data"]["skills"]) > 0
        assert result["data"]["total_experience_years"] == 7
    
    def test_parse_resume_with_empty_text(self, mock_llm_client):
        """Test parsing with empty resume text."""
        with patch('ai_hiring.services.resume_parser.LLMClient', return_value=mock_llm_client):
            parser = ResumeParser()
            result = parser.parse_resume("")
        
        assert result["success"] is False
        assert "empty" in result["error"].lower()
    
    def test_parse_resume_llm_error(self, mock_llm_client, mock_resume_text):
        """Test handling of LLM API errors."""
        # Setup mock to return error
        mock_llm_client.generate_structured_output.return_value = {
            "success": False,
            "data": None,
            "error": "API rate limit exceeded"
        }
        
        with patch('ai_hiring.services.resume_parser.LLMClient', return_value=mock_llm_client):
            parser = ResumeParser()
            result = parser.parse_resume(mock_resume_text)
        
        assert result["success"] is False
        assert "API rate limit" in result["error"]
    
    def test_parse_resume_invalid_json(self, mock_llm_client, mock_resume_text):
        """Test handling of invalid JSON from LLM."""
        # Setup mock to return invalid data
        mock_llm_client.generate_structured_output.return_value = {
            "success": True,
            "data": {"invalid": "structure"},
            "error": None
        }
        
        with patch('ai_hiring.services.resume_parser.LLMClient', return_value=mock_llm_client):
            parser = ResumeParser()
            result = parser.parse_resume(mock_resume_text)
        
        # Should still succeed but with defaults
        assert result["success"] is True
    
    def test_validate_parsed_data(self, mock_parsed_resume):
        """Test validation of parsed resume data."""
        parser = ResumeParser()
        
        # Valid data should pass
        validated = parser._validate_parsed_data(mock_parsed_resume)
        assert validated is not None
        assert "name" in validated
        assert "email" in validated
    
    def test_validate_parsed_data_missing_fields(self):
        """Test validation with missing required fields."""
        parser = ResumeParser()
        
        # Missing email
        invalid_data = {
            "name": "John Doe",
            "skills": ["Python"]
        }
        
        validated = parser._validate_parsed_data(invalid_data)
        assert validated is not None
        assert validated.get("email") == ""  # Should have default
    
    def test_extract_skills(self, mock_parsed_resume):
        """Test skill extraction and deduplication."""
        parser = ResumeParser()
        
        skills = parser._extract_skills(mock_parsed_resume)
        
        assert isinstance(skills, list)
        assert len(skills) > 0
        assert "Python" in skills
        # Check deduplication
        assert len(skills) == len(set(skills))


class TestTextExtraction:
    """Test cases for text extraction from different file formats."""
    
    @patch('ai_hiring.services.resume_parser.frappe.get_doc')
    def test_extract_text_from_pdf(self, mock_get_doc, mock_file_content):
        """Test PDF text extraction."""
        # Setup mock file
        mock_file_doc = MagicMock()
        mock_file_doc.get_content.return_value = mock_file_content('/files/resume.pdf')
        mock_get_doc.return_value = mock_file_doc
        
        with patch('PyPDF2.PdfReader') as mock_pdf:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Extracted text from PDF"
            mock_pdf.return_value.pages = [mock_page]
            
            result = extract_text_from_file('/files/resume.pdf')
            
            assert "Extracted text" in result
    
    @patch('ai_hiring.services.resume_parser.frappe.get_doc')
    def test_extract_text_from_docx(self, mock_get_doc, mock_file_content):
        """Test DOCX text extraction."""
        mock_file_doc = MagicMock()
        mock_file_doc.get_content.return_value = mock_file_content('/files/resume.docx')
        mock_get_doc.return_value = mock_file_doc
        
        with patch('docx.Document') as mock_docx:
            mock_paragraph = MagicMock()
            mock_paragraph.text = "Extracted text from DOCX"
            mock_docx.return_value.paragraphs = [mock_paragraph]
            
            result = extract_text_from_file('/files/resume.docx')
            
            assert "Extracted text" in result
    
    @patch('ai_hiring.services.resume_parser.frappe.get_doc')
    def test_extract_text_from_txt(self, mock_get_doc, mock_file_content):
        """Test TXT text extraction."""
        mock_file_doc = MagicMock()
        mock_file_doc.get_content.return_value = b"Plain text content"
        mock_get_doc.return_value = mock_file_doc
        
        result = extract_text_from_file('/files/resume.txt')
        
        assert "Plain text content" in result
    
    def test_extract_text_unsupported_format(self):
        """Test handling of unsupported file formats."""
        with pytest.raises(ValueError, match="Unsupported file format"):
            extract_text_from_file('/files/resume.xyz')
    
    @patch('ai_hiring.services.resume_parser.frappe.get_doc')
    def test_extract_text_file_not_found(self, mock_get_doc):
        """Test handling of missing files."""
        mock_get_doc.side_effect = Exception("File not found")
        
        with pytest.raises(Exception):
            extract_text_from_file('/files/missing.pdf')


class TestResumeParserIntegration:
    """Integration tests for complete resume parsing flow."""
    
    @patch('ai_hiring.services.resume_parser.extract_text_from_file')
    def test_parse_resume_from_file(self, mock_extract, mock_llm_client, 
                                    mock_resume_text, mock_parsed_resume):
        """Test end-to-end parsing from file to structured data."""
        # Setup mocks
        mock_extract.return_value = mock_resume_text
        mock_llm_client.generate_structured_output.return_value = {
            "success": True,
            "data": mock_parsed_resume,
            "error": None
        }
        
        with patch('ai_hiring.services.resume_parser.LLMClient', return_value=mock_llm_client):
            parser = ResumeParser()
            
            # Extract and parse
            text = mock_extract('/files/resume.pdf')
            result = parser.parse_resume(text)
        
        # Verify complete flow
        assert result["success"] is True
        assert result["data"]["name"] == "John Doe"
        assert len(result["data"]["experience"]) == 2
        assert len(result["data"]["skills"]) == 10
    
    def test_parse_resume_with_special_characters(self, mock_llm_client, mock_parsed_resume):
        """Test parsing resume with special characters and encoding."""
        resume_text = """
        Candidate Name: José María González
        Email: jose.maria@example.com
        Skills: Python, C++, C#, .NET
        """
        
        mock_llm_client.generate_structured_output.return_value = {
            "success": True,
            "data": mock_parsed_resume,
            "error": None
        }
        
        with patch('ai_hiring.services.resume_parser.LLMClient', return_value=mock_llm_client):
            parser = ResumeParser()
            result = parser.parse_resume(resume_text)
        
        assert result["success"] is True
    
    def test_parse_resume_performance(self, mock_llm_client, mock_resume_text, mock_parsed_resume):
        """Test parsing performance with large resume."""
        # Create large resume text
        large_resume = mock_resume_text * 10  # Simulate large resume
        
        mock_llm_client.generate_structured_output.return_value = {
            "success": True,
            "data": mock_parsed_resume,
            "error": None
        }
        
        with patch('ai_hiring.services.resume_parser.LLMClient', return_value=mock_llm_client):
            parser = ResumeParser()
            
            import time
            start_time = time.time()
            result = parser.parse_resume(large_resume)
            duration = time.time() - start_time
        
        assert result["success"] is True
        assert duration < 30  # Should complete within 30 seconds
