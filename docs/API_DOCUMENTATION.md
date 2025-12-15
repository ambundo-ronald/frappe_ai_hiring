# AI Hiring Automation - API Documentation

## 📡 API Reference

Complete documentation for all public API endpoints in the AI Hiring Automation system.

---

## Table of Contents

1. [Authentication](#authentication)
2. [Resume Parsing API](#resume-parsing-api)
3. [Candidate Shortlisting API](#candidate-shortlisting-api)
4. [Question Generation API](#question-generation-api)
5. [Questionnaire Evaluation API](#questionnaire-evaluation-api)
6. [Interview Brief API](#interview-brief-api)
7. [Dashboard & Analytics API](#dashboard--analytics-api)
8. [Workflow Management API](#workflow-management-api)
9. [Error Handling](#error-handling)
10. [Rate Limiting](#rate-limiting)
11. [Code Examples](#code-examples)

---

## Authentication

All API endpoints require authentication using Frappe's standard authentication mechanisms.

### API Key Authentication

```http
GET /api/method/ai_hiring.api.parse_resume
Authorization: token <api_key>:<api_secret>
```

### Session Authentication

For browser-based requests, use Frappe's session cookies.

### Generate API Keys

```python
# In Frappe console
from frappe.core.doctype.user.user import generate_keys
keys = generate_keys("user@example.com")
print(f"API Key: {keys['api_key']}")
print(f"API Secret: {keys['api_secret']}")
```

---

## Resume Parsing API

### Parse Resume from File

Extract and parse resume data from uploaded files.

**Endpoint**: `/api/method/ai_hiring.api.parse_resume`

**Method**: `POST`

**Parameters**:
- `applicant_id` (string, required): Job Applicant ID
- `file_url` (string, optional): Resume file URL (if not attached to applicant)

**Request Example**:
```python
import requests

url = "https://yoursite.com/api/method/ai_hiring.api.parse_resume"
headers = {
    "Authorization": "token api_key:api_secret",
    "Content-Type": "application/json"
}
data = {
    "applicant_id": "JOB-APP-2024-00001"
}

response = requests.post(url, json=data, headers=headers)
print(response.json())
```

**Response**:
```json
{
  "message": {
    "success": true,
    "data": {
      "name": "John Doe",
      "email": "john.doe@example.com",
      "phone": "+1-555-0123",
      "summary": "Experienced Python developer...",
      "experience": [
        {
          "company": "Tech Corp",
          "title": "Senior Python Developer",
          "duration": "2020 - Present",
          "description": "Led team of 4 developers..."
        }
      ],
      "education": [
        {
          "degree": "B.S. Computer Science",
          "institution": "State University",
          "year": "2017"
        }
      ],
      "skills": ["Python", "Django", "PostgreSQL", "Docker", "AWS"],
      "total_experience_years": 7
    },
    "parsing_id": "AI-RP-2024-00001"
  }
}
```

### Get Parsed Resume

Retrieve previously parsed resume data.

**Endpoint**: `/api/method/ai_hiring.api.get_parsed_resume`

**Method**: `GET`

**Parameters**:
- `applicant_id` (string, required): Job Applicant ID

**Response**:
```json
{
  "message": {
    "name": "AI-RP-2024-00001",
    "job_applicant": "JOB-APP-2024-00001",
    "parsed_data": { /* same as parse_resume response */ },
    "raw_text": "Resume text content...",
    "parsing_status": "Success",
    "creation": "2024-12-15 10:30:00"
  }
}
```

---

## Candidate Shortlisting API

### Evaluate Candidate

Evaluate a candidate against job requirements.

**Endpoint**: `/api/method/ai_hiring.api.evaluate_candidate`

**Method**: `POST`

**Parameters**:
- `applicant_id` (string, required): Job Applicant ID
- `job_opening_id` (string, optional): Job Opening ID (auto-detected if linked)

**Request Example**:
```python
data = {
    "applicant_id": "JOB-APP-2024-00001",
    "job_opening_id": "JOB-OPEN-2024-00001"
}
response = requests.post(url, json=data, headers=headers)
```

**Response**:
```json
{
  "message": {
    "success": true,
    "data": {
      "fit_score": 85,
      "ai_decision": "shortlist",
      "technical_skills_match": 90,
      "experience_match": 85,
      "education_match": 80,
      "key_strengths": [
        "7+ years of Python experience",
        "Strong expertise in Django and Flask",
        "Proven experience with REST APIs"
      ],
      "potential_concerns": [
        "No specific mention of Docker expertise level"
      ],
      "recommendations": "Strong candidate with excellent technical match. Schedule technical interview."
    },
    "shortlisting_id": "AI-SL-2024-00001"
  }
}
```

### Get Shortlisting Result

Retrieve existing shortlisting results.

**Endpoint**: `/api/method/ai_hiring.api.get_shortlisting_result`

**Method**: `GET`

**Parameters**:
- `applicant_id` (string, required): Job Applicant ID

**Response**:
```json
{
  "message": {
    "name": "AI-SL-2024-00001",
    "job_applicant": "JOB-APP-2024-00001",
    "ai_decision": "shortlist",
    "fit_score": 85,
    /* additional fields */
  }
}
```

---

## Question Generation API

### Generate Questions

Generate customized questionnaire for a candidate.

**Endpoint**: `/api/method/ai_hiring.api.generate_questions`

**Method**: `POST`

**Parameters**:
- `applicant_id` (string, required): Job Applicant ID
- `num_questions` (int, optional): Number of questions (default: 10)
- `focus_areas` (list, optional): Specific topics to focus on

**Request Example**:
```python
data = {
    "applicant_id": "JOB-APP-2024-00001",
    "num_questions": 15,
    "focus_areas": ["Python", "Django", "Team Leadership"]
}
response = requests.post(url, json=data, headers=headers)
```

**Response**:
```json
{
  "message": {
    "success": true,
    "data": {
      "questions": [
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
          "question": "Do you have AWS cloud platform experience?",
          "topic": "Cloud",
          "weight": 8
        }
      ]
    },
    "questionnaire_id": "AI-QN-2024-00001"
  }
}
```

### Send Questionnaire

Send questionnaire link to candidate via email.

**Endpoint**: `/api/method/ai_hiring.api.send_questionnaire`

**Method**: `POST`

**Parameters**:
- `questionnaire_id` (string, required): AI Questionnaire ID
- `applicant_email` (string, optional): Override email (uses applicant's email if not provided)

**Response**:
```json
{
  "message": {
    "success": true,
    "email_sent": true,
    "questionnaire_link": "https://yoursite.com/questionnaire/xyz123"
  }
}
```

### Get Questionnaire

Retrieve questionnaire details.

**Endpoint**: `/api/method/ai_hiring.api.get_questionnaire`

**Method**: `GET`

**Parameters**:
- `questionnaire_id` (string, required): AI Questionnaire ID

**Response**:
```json
{
  "message": {
    "name": "AI-QN-2024-00001",
    "job_applicant": "JOB-APP-2024-00001",
    "questions": [ /* array of questions */ ],
    "status": "Sent",
    "sent_at": "2024-12-15 11:00:00"
  }
}
```

---

## Questionnaire Evaluation API

### Evaluate Answers

Evaluate candidate's questionnaire responses.

**Endpoint**: `/api/method/ai_hiring.api.evaluate_answers`

**Method**: `POST`

**Parameters**:
- `questionnaire_id` (string, required): AI Questionnaire ID
- `answers` (list, required): Array of {question, answer, topic}

**Request Example**:
```python
data = {
    "questionnaire_id": "AI-QN-2024-00001",
    "answers": [
        {
            "question": "Do you have experience with microservices?",
            "answer": "yes",
            "topic": "Architecture"
        },
        {
            "question": "Have you worked with FastAPI?",
            "answer": "yes",
            "topic": "Frameworks"
        }
    ]
}
response = requests.post(url, json=data, headers=headers)
```

**Response**:
```json
{
  "message": {
    "success": true,
    "data": {
      "overall_score": 95,
      "topic_scores": {
        "Architecture": 100,
        "Frameworks": 100,
        "DevOps": 90
      },
      "strengths": [
        "Strong technical expertise across all areas",
        "Excellent cloud platform knowledge"
      ],
      "areas_for_improvement": [
        "Could strengthen Docker knowledge"
      ],
      "recommendation": "Highly qualified candidate. Proceed to interview."
    },
    "evaluation_id": "AI-QE-2024-00001"
  }
}
```

### Get Evaluation Result

Retrieve existing evaluation.

**Endpoint**: `/api/method/ai_hiring.api.get_evaluation_result`

**Method**: `GET`

**Parameters**:
- `applicant_id` (string, required): Job Applicant ID

**Response**:
```json
{
  "message": {
    "name": "AI-QE-2024-00001",
    "job_applicant": "JOB-APP-2024-00001",
    "overall_score": 95,
    /* evaluation details */
  }
}
```

---

## Interview Brief API

### Generate Interview Brief

Create comprehensive interview preparation document.

**Endpoint**: `/api/method/ai_hiring.api.generate_interview_brief`

**Method**: `POST`

**Parameters**:
- `applicant_id` (string, required): Job Applicant ID

**Request Example**:
```python
data = {
    "applicant_id": "JOB-APP-2024-00001"
}
response = requests.post(url, json=data, headers=headers)
```

**Response**:
```json
{
  "message": {
    "success": true,
    "data": {
      "candidate_summary": "Strong Python developer with 7+ years of experience in web application development...",
      "key_strengths": [
        "Excellent technical skills in Python ecosystem",
        "Proven leadership experience",
        "Strong problem-solving abilities"
      ],
      "areas_to_probe": [
        "Specific microservices architecture experience",
        "Team collaboration style",
        "Approach to technical challenges"
      ],
      "suggested_questions": [
        "Can you describe a complex microservices project you've led?",
        "How do you approach code reviews with junior developers?",
        "Tell me about a time you optimized a slow API endpoint."
      ],
      "technical_depth_questions": [
        "Explain your database optimization approach",
        "How do you ensure API security?",
        "What's your CI/CD pipeline experience?"
      ],
      "red_flags": [],
      "overall_recommendation": "Strong hire - proceed with technical interview"
    },
    "brief_id": "AI-IB-2024-00001"
  }
}
```

### Get Interview Brief

Retrieve existing brief.

**Endpoint**: `/api/method/ai_hiring.api.get_interview_brief`

**Method**: `GET`

**Parameters**:
- `applicant_id` (string, required): Job Applicant ID

**Response**:
```json
{
  "message": {
    "name": "AI-IB-2024-00001",
    "job_applicant": "JOB-APP-2024-00001",
    /* brief details */
  }
}
```

---

## Dashboard & Analytics API

### Get Pipeline Overview

Get high-level pipeline statistics.

**Endpoint**: `/api/method/ai_hiring.api.get_pipeline_overview`

**Method**: `GET`

**Parameters**: None

**Response**:
```json
{
  "message": {
    "active_candidates": 25,
    "hired_count": 3,
    "rejected_count": 12,
    "pending_review": 5,
    "avg_processing_time": 2.5,
    "avg_fit_score": 72.3,
    "stages_breakdown": {
      "resume_parsing": 10,
      "shortlisting": 8,
      "questionnaire": 4,
      "interview": 3
    }
  }
}
```

### Get AI Performance Metrics

Get AI accuracy and performance data.

**Endpoint**: `/api/method/ai_hiring.api.get_ai_performance`

**Method**: `GET`

**Parameters**:
- `from_date` (string, optional): Start date (YYYY-MM-DD)
- `to_date` (string, optional): End date (YYYY-MM-DD)

**Response**:
```json
{
  "message": {
    "total_evaluations": 100,
    "correct_predictions": 87,
    "accuracy_rate": 87.0,
    "avg_fit_score_shortlisted": 82.5,
    "avg_fit_score_rejected": 35.2,
    "avg_processing_time": 3.2,
    "by_decision": {
      "shortlist": {"count": 45, "hired": 28, "accuracy": 88.9},
      "reject": {"count": 40, "hired": 2, "accuracy": 90.0},
      "review": {"count": 15, "hired": 7, "accuracy": 73.3}
    }
  }
}
```

### Get Funnel Statistics

Get conversion rates through hiring pipeline.

**Endpoint**: `/api/method/ai_hiring.api.get_funnel_stats`

**Method**: `GET`

**Parameters**:
- `from_date` (string, optional): Start date
- `to_date` (string, optional): End date

**Response**:
```json
{
  "message": [
    {"stage": "Applied", "count": 100, "conversion_rate": 100.0},
    {"stage": "Resume Parsed", "count": 95, "conversion_rate": 95.0},
    {"stage": "Shortlisted", "count": 45, "conversion_rate": 47.4},
    {"stage": "Questionnaire Completed", "count": 38, "conversion_rate": 84.4},
    {"stage": "Interviewed", "count": 25, "conversion_rate": 65.8},
    {"stage": "Offered", "count": 12, "conversion_rate": 48.0},
    {"stage": "Hired", "count": 10, "conversion_rate": 83.3}
  ]
}
```

---

## Workflow Management API

### Get Current Stage

Get candidate's current pipeline stage.

**Endpoint**: `/api/method/ai_hiring.api.get_current_stage`

**Method**: `GET`

**Parameters**:
- `applicant_id` (string, required): Job Applicant ID

**Response**:
```json
{
  "message": {
    "applicant_id": "JOB-APP-2024-00001",
    "current_stage": "QUESTIONNAIRE_SENT",
    "stage_number": 5,
    "progress_percentage": 38,
    "next_stage": "QUESTIONNAIRE_COMPLETED",
    "can_proceed": true
  }
}
```

### Transition Stage

Move candidate to next pipeline stage.

**Endpoint**: `/api/method/ai_hiring.api.transition_stage`

**Method**: `POST`

**Parameters**:
- `applicant_id` (string, required): Job Applicant ID
- `target_stage` (string, required): Target pipeline stage

**Request Example**:
```python
data = {
    "applicant_id": "JOB-APP-2024-00001",
    "target_stage": "INTERVIEW_SCHEDULED"
}
response = requests.post(url, json=data, headers=headers)
```

**Response**:
```json
{
  "message": {
    "success": true,
    "previous_stage": "QUESTIONNAIRE_COMPLETED",
    "current_stage": "INTERVIEW_SCHEDULED",
    "transition_valid": true
  }
}
```

### Reprocess Candidate

Reprocess specific pipeline stages for a candidate.

**Endpoint**: `/api/method/ai_hiring.api.reprocess_candidate`

**Method**: `POST`

**Parameters**:
- `applicant_id` (string, required): Job Applicant ID
- `stages` (list, optional): Specific stages to reprocess (default: all)

**Request Example**:
```python
data = {
    "applicant_id": "JOB-APP-2024-00001",
    "stages": ["shortlisting", "questions"]
}
response = requests.post(url, json=data, headers=headers)
```

**Response**:
```json
{
  "message": {
    "success": true,
    "reprocessed_stages": ["shortlisting", "questions"],
    "job_id": "background-job-xyz123"
  }
}
```

### Get Processing Status

Check status of background processing.

**Endpoint**: `/api/method/ai_hiring.api.get_processing_status`

**Method**: `GET`

**Parameters**:
- `applicant_id` (string, required): Job Applicant ID

**Response**:
```json
{
  "message": {
    "applicant_id": "JOB-APP-2024-00001",
    "status": "processing",
    "current_operation": "resume_parsing",
    "progress": 25,
    "estimated_completion": "2024-12-15 10:35:00",
    "stages": {
      "resume_parsing": {"status": "in_progress", "started_at": "10:30:00"},
      "shortlisting": {"status": "pending"},
      "questions": {"status": "pending"}
    }
  }
}
```

---

## Error Handling

All API endpoints follow a consistent error response format.

### Error Response Structure

```json
{
  "exc_type": "ValidationError",
  "exception": "Applicant not found: JOB-APP-INVALID",
  "_server_messages": "[{\"message\": \"Applicant not found\"}]"
}
```

### Common Error Codes

| HTTP Code | Error Type | Description |
|-----------|------------|-------------|
| 400 | ValidationError | Invalid input parameters |
| 401 | AuthenticationError | Invalid or missing credentials |
| 403 | PermissionError | Insufficient permissions |
| 404 | DoesNotExistError | Resource not found |
| 429 | RateLimitError | Rate limit exceeded |
| 500 | InternalServerError | System error |
| 503 | ServiceUnavailable | AI service unavailable |

### Error Handling Example

```python
try:
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    result = response.json()
    
    if "message" in result:
        # Success
        return result["message"]
    else:
        # Error response
        error = result.get("exception", "Unknown error")
        print(f"Error: {error}")
        
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 429:
        print("Rate limit exceeded. Retry after some time.")
    elif e.response.status_code == 401:
        print("Authentication failed. Check API credentials.")
    else:
        print(f"HTTP error: {e}")
        
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
```

---

## Rate Limiting

API requests are subject to rate limiting to ensure fair usage.

### Rate Limit Headers

Response headers include rate limit information:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1702645200
```

### Rate Limit Response

When limit exceeded:

```json
{
  "exc_type": "RateLimitError",
  "exception": "Rate limit exceeded. Try again in 3600 seconds.",
  "_server_messages": "[{\"message\": \"Rate limit exceeded\"}]"
}
```

### Best Practices

1. **Check remaining quota** before making bulk requests
2. **Implement exponential backoff** for retries
3. **Cache responses** when appropriate
4. **Batch operations** during off-peak hours
5. **Monitor usage** through analytics

---

## Code Examples

### Python Client

Complete Python client example:

```python
import requests
import json
from typing import Dict, Any, Optional

class AIHiringClient:
    """Client for AI Hiring Automation API"""
    
    def __init__(self, base_url: str, api_key: str, api_secret: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.api_secret = api_secret
        self.headers = {
            "Authorization": f"token {api_key}:{api_secret}",
            "Content-Type": "application/json"
        }
    
    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make API request"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, params=data, headers=self.headers)
            else:
                response = requests.post(url, json=data, headers=self.headers)
            
            response.raise_for_status()
            return response.json().get("message", {})
            
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            raise
    
    def parse_resume(self, applicant_id: str) -> Dict[str, Any]:
        """Parse candidate resume"""
        return self._request("POST", "/api/method/ai_hiring.api.parse_resume", 
                           {"applicant_id": applicant_id})
    
    def evaluate_candidate(self, applicant_id: str, job_opening_id: Optional[str] = None) -> Dict[str, Any]:
        """Evaluate candidate against job requirements"""
        data = {"applicant_id": applicant_id}
        if job_opening_id:
            data["job_opening_id"] = job_opening_id
        return self._request("POST", "/api/method/ai_hiring.api.evaluate_candidate", data)
    
    def generate_questions(self, applicant_id: str, num_questions: int = 10, 
                          focus_areas: Optional[list] = None) -> Dict[str, Any]:
        """Generate questionnaire"""
        data = {
            "applicant_id": applicant_id,
            "num_questions": num_questions
        }
        if focus_areas:
            data["focus_areas"] = focus_areas
        return self._request("POST", "/api/method/ai_hiring.api.generate_questions", data)
    
    def evaluate_answers(self, questionnaire_id: str, answers: list) -> Dict[str, Any]:
        """Evaluate questionnaire answers"""
        return self._request("POST", "/api/method/ai_hiring.api.evaluate_answers",
                           {"questionnaire_id": questionnaire_id, "answers": answers})
    
    def generate_interview_brief(self, applicant_id: str) -> Dict[str, Any]:
        """Generate interview brief"""
        return self._request("POST", "/api/method/ai_hiring.api.generate_interview_brief",
                           {"applicant_id": applicant_id})
    
    def get_pipeline_overview(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        return self._request("GET", "/api/method/ai_hiring.api.get_pipeline_overview")


# Usage example
if __name__ == "__main__":
    client = AIHiringClient(
        base_url="https://yoursite.com",
        api_key="your-api-key",
        api_secret="your-api-secret"
    )
    
    # Parse resume
    result = client.parse_resume("JOB-APP-2024-00001")
    print("Resume parsed:", result)
    
    # Evaluate candidate
    evaluation = client.evaluate_candidate("JOB-APP-2024-00001")
    print(f"Fit Score: {evaluation['data']['fit_score']}")
    print(f"Decision: {evaluation['data']['ai_decision']}")
    
    # Generate questions
    questions = client.generate_questions("JOB-APP-2024-00001", num_questions=15)
    print(f"Generated {len(questions['data']['questions'])} questions")
    
    # Get pipeline overview
    overview = client.get_pipeline_overview()
    print(f"Active candidates: {overview['active_candidates']}")
```

### JavaScript/Node.js Client

```javascript
const axios = require('axios');

class AIHiringClient {
    constructor(baseUrl, apiKey, apiSecret) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.headers = {
            'Authorization': `token ${apiKey}:${apiSecret}`,
            'Content-Type': 'application/json'
        };
    }
    
    async request(method, endpoint, data = null) {
        const url = `${this.baseUrl}${endpoint}`;
        
        try {
            const config = {
                method: method,
                url: url,
                headers: this.headers
            };
            
            if (method === 'GET' && data) {
                config.params = data;
            } else if (data) {
                config.data = data;
            }
            
            const response = await axios(config);
            return response.data.message;
            
        } catch (error) {
            console.error('API request failed:', error.message);
            throw error;
        }
    }
    
    async parseResume(applicantId) {
        return await this.request('POST', '/api/method/ai_hiring.api.parse_resume', 
                                 { applicant_id: applicantId });
    }
    
    async evaluateCandidate(applicantId, jobOpeningId = null) {
        const data = { applicant_id: applicantId };
        if (jobOpeningId) data.job_opening_id = jobOpeningId;
        return await this.request('POST', '/api/method/ai_hiring.api.evaluate_candidate', data);
    }
    
    async generateQuestions(applicantId, numQuestions = 10, focusAreas = null) {
        const data = {
            applicant_id: applicantId,
            num_questions: numQuestions
        };
        if (focusAreas) data.focus_areas = focusAreas;
        return await this.request('POST', '/api/method/ai_hiring.api.generate_questions', data);
    }
    
    async getPipelineOverview() {
        return await this.request('GET', '/api/method/ai_hiring.api.get_pipeline_overview');
    }
}

// Usage
(async () => {
    const client = new AIHiringClient(
        'https://yoursite.com',
        'your-api-key',
        'your-api-secret'
    );
    
    const result = await client.parseResume('JOB-APP-2024-00001');
    console.log('Resume parsed:', result);
    
    const overview = await client.getPipelineOverview();
    console.log('Pipeline overview:', overview);
})();
```

### cURL Examples

```bash
# Parse resume
curl -X POST https://yoursite.com/api/method/ai_hiring.api.parse_resume \
  -H "Authorization: token api_key:api_secret" \
  -H "Content-Type: application/json" \
  -d '{"applicant_id": "JOB-APP-2024-00001"}'

# Evaluate candidate
curl -X POST https://yoursite.com/api/method/ai_hiring.api.evaluate_candidate \
  -H "Authorization: token api_key:api_secret" \
  -H "Content-Type: application/json" \
  -d '{"applicant_id": "JOB-APP-2024-00001"}'

# Get pipeline overview
curl -X GET https://yoursite.com/api/method/ai_hiring.api.get_pipeline_overview \
  -H "Authorization: token api_key:api_secret"
```

---

## Webhooks

### Configure Webhooks

Set up webhooks to receive real-time notifications of pipeline events.

**Setup**: Navigate to AI Settings > Webhooks

**Supported Events**:
- `candidate.applied`
- `resume.parsed`
- `candidate.shortlisted`
- `candidate.rejected`
- `questionnaire.sent`
- `questionnaire.completed`
- `interview.scheduled`
- `candidate.hired`

**Webhook Payload Example**:
```json
{
  "event": "candidate.shortlisted",
  "timestamp": "2024-12-15T10:30:00Z",
  "data": {
    "applicant_id": "JOB-APP-2024-00001",
    "applicant_name": "John Doe",
    "job_title": "Senior Python Developer",
    "fit_score": 85,
    "ai_decision": "shortlist"
  }
}
```

---

## API Versioning

Current API version: **v1**

All endpoints are prefixed with version:
- Current: `/api/method/ai_hiring.api.*`
- Future: `/api/v2/method/ai_hiring.api.*`

Breaking changes will be introduced in new versions only.

---

## Support

For API support:
- **Documentation**: This file
- **GitHub Issues**: Report bugs
- **Email**: api-support@yourcompany.com

---

**API Version**: 1.0  
**Last Updated**: 2024-12-15  
**Compatibility**: Frappe v14+
