# AI Hiring Automation for Frappe/ERPNext

> **AI-powered recruitment automation that streamlines the entire hiring pipeline from resume screening to interview preparation.**

[![Frappe](https://img.shields.io/badge/Frappe-v14%2B-blue)](https://frappeframework.com/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-success)]()

## 🚀 Overview

AI Hiring Automation is a comprehensive Frappe application that leverages artificial intelligence to automate and optimize the recruitment process. Built on the Frappe Framework with seamless ERPNext HRMS integration, it reduces time-to-hire while improving candidate quality through intelligent screening and evaluation.

### ✨ Key Features

- **📄 Intelligent Resume Parsing**: Automatically extract structured data from PDF, DOCX, and TXT resumes
- **🎯 AI-Powered Candidate Shortlisting**: Evaluate candidates against job requirements with detailed scoring
- **❓ Dynamic Questionnaire Generation**: Create customized yes/no questionnaires tailored to each candidate
- **📊 Automated Answer Evaluation**: Analyze responses with weighted scoring and topic-wise assessment
- **📝 Interview Brief Generation**: Prepare comprehensive interview guides with suggested questions
- **🔄 Complete Workflow Management**: Track candidates through 13 pipeline stages with state validation
- **📧 Automated Notifications**: Send email notifications to candidates and HR at key milestones
- **📈 Analytics & Reporting**: Track AI performance, pipeline metrics, and hiring funnel statistics
- **🔒 Enterprise Security**: Rate limiting, audit logging, GDPR compliance, and role-based access control
- **🔌 REST API**: Full-featured API for integrations and custom workflows

## Requirements

- Frappe Framework v14 or higher
- Frappe HRMS
- OpenAI-compatible API endpoint (OpenAI, Azure OpenAI, or Ollama)
- Redis (for background jobs)
- Python 3.10+

## Installation

1. Get the app:
```bash
bench get-app https://github.com/yourcompany/frappe_ai_hiring.git
```

2. Install on your site:
```bash
bench --site your-site.local install-app frappe_ai_hiring
```

3. Configure AI Settings:
   - Navigate to **AI Settings** in your site
   - Add your OpenAI-compatible API credentials
   - Configure model preferences and temperature

## Usage

### For HR Managers

1. **Job Applicant Processing**: When a new candidate applies with a resume, the system automatically:
   - Parses the resume
   - Evaluates against the job description
   - Provides shortlisting recommendations

2. **Review AI Decisions**: Navigate to **AI Shortlisting Result** to see:
   - Fit scores
   - Detailed reasoning
   - Missing skills analysis

3. **Send Questionnaires**: For shortlisted candidates:
   - System generates role-specific binary questions
   - Candidates receive questionnaire links
   - Auto-scoring with pass/fail thresholds

4. **Interview Preparation**: Before interviews, view **AI Interview Brief** for:
   - Candidate strengths and risks
   - Verification points
   - Suggested questions

### For Developers

See [DEVELOPER.md](DEVELOPER.md) for:
- Architecture overview
- API documentation
- Custom prompt templates
- Extension guidelines

## Configuration

### AI Settings

- **Provider**: OpenAI-compatible endpoint
- **API Base URL**: Your API endpoint
- **API Key**: Encrypted credentials
- **Default Model**: e.g., `gpt-4-turbo-preview`
- **Temperature**: 0.2 (recommended for consistency)
- **Timeout**: 60 seconds

### Queue Configuration

Background jobs use Frappe's queue system:
- **Queue**: `long` (for LLM calls)
- **Timeout**: 300 seconds
- **Retry Logic**: 3 attempts with exponential backoff

## Security & Compliance

- **PII Redaction**: Names, emails, phone numbers are redacted before LLM calls
- **Data Encryption**: Sensitive fields encrypted at rest
- **Audit Logs**: Every AI decision logged with prompt and response
- **No Auto-Hire**: System provides recommendations only; humans make final decisions

## Pipeline States

```
Applied → AI Parsed → AI Shortlisted → Questionnaire Sent →
Questionnaire Passed → Interview Scheduled → Interview Completed →
Offer / Rejected
```

## Support

For issues and questions:
- GitHub Issues: [Link to repo]
- Documentation: [Link to docs]
- Email: support@yourcompany.com

## License

MIT License - see LICENSE file for details

## Credits

Built with ❤️ using [Frappe Framework](https://frappeframework.com)
