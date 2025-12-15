# AI Hiring Pipeline - Testing Guide

This guide explains how to run unit and integration tests for the frappe_ai_hiring application.

## Prerequisites

Ensure your local ERPNext instance is running:

```bash
cd ~/frappe-bench
bench start
```

In a separate terminal, install test dependencies:

```bash
cd ~/frappe-bench
pip install -r apps/frappe_ai_hiring/requirements-test.txt
```

## Test Structure

### Unit Tests (`test_services.py`)
Test individual service functions in isolation with mocked LLM responses:
- `TestResumeParsing` - Resume parsing and candidate profile creation
- `TestShortlisting` - Shortlisting decision making
- `TestQuestionGeneration` - Question set generation with difficulty levels
- `TestEvaluation` - Interview evaluation scoring
- `TestInterviewBrief` - Interview brief generation

### Integration Tests (`test_integration.py`)
Test end-to-end workflows with mocked LLM:
- `TestAIHiringPipelineIntegration` - Complete pipeline from applicant to evaluation
- `TestPipelineReporting` - Report query execution and output
- `TestUIActions` - UI button actions (Reprocess, Send Questionnaire, Schedule)

### Fixtures (`conftest.py`)
Reusable test data and mocks:
- `ai_settings` - AI Settings configuration
- `job_opening` - Test job opening
- `job_applicant` - Test job applicant
- `mock_llm_client` - Mocked LLM responses
- `mock_audit_logger` - Mocked audit logging
- `mock_notification_manager` - Mocked notifications

## Running Tests

### Option 1: Using Pytest (Recommended)

Run all tests:
```bash
cd ~/frappe-bench
python -m pytest apps/frappe_ai_hiring/frappe_ai_hiring/ai_hiring/tests -v
```

Run only unit tests:
```bash
python -m pytest apps/frappe_ai_hiring/frappe_ai_hiring/ai_hiring/tests/test_services.py -v
```

Run only integration tests:
```bash
python -m pytest apps/frappe_ai_hiring/frappe_ai_hiring/ai_hiring/tests/test_integration.py -v
```

Run with coverage report:
```bash
python -m pytest apps/frappe_ai_hiring/frappe_ai_hiring/ai_hiring/tests \
  --cov=frappe_ai_hiring \
  --cov-report=html \
  --cov-report=term-missing
```

### Option 2: Using Test Runner Script

```bash
cd ~/frappe-bench/apps/frappe_ai_hiring
python run_tests.py --type all --verbose --coverage
```

Available options:
- `--type [unit|integration|all]` - Type of tests to run
- `--verbose` - Show detailed output
- `--coverage` - Generate coverage report
- `--frappe` - Use Frappe's built-in test runner
- `--markers` - Filter tests by pytest markers

### Option 3: Using Frappe's Built-in Test Runner

```bash
cd ~/frappe-bench
bench test --app frappe_ai_hiring --verbose
```

## Test Scenarios

### 1. Resume Parsing Pipeline
Tests that job applicant resume is parsed and candidate profile is created:
```python
def test_pipeline_parsing_stage():
    # Create job applicant
    # Mock LLM parse response
    # Call create_candidate_profile()
    # Verify profile created with correct skills
```

### 2. Shortlisting Decision
Tests that candidate is evaluated against job opening:
```python
def test_pipeline_shortlisting_stage():
    # Create candidate profile
    # Mock LLM shortlist response
    # Call create_shortlisting_result()
    # Verify decision and fit score
```

### 3. Question Generation
Tests that screening questions are generated with correct difficulty:
```python
def test_create_question_set_difficulty_enum():
    # Create question set
    # Verify difficulty in [Easy, Medium, Hard]
    # Verify question count persisted
```

### 4. Interview Evaluation
Tests that interview scores are calculated:
```python
def test_create_evaluation_result():
    # Create evaluation result
    # Verify overall_score, technical_score, etc.
    # Verify hire_recommendation
```

### 5. Report Queries
Tests that report executes without SQL errors:
```python
def test_pipeline_report_query_executes():
    # Call execute() from report
    # Verify columns and data returned
    # Verify all expected fields present
```

### 6. UI Actions
Tests that UI buttons execute correctly:
```python
def test_reprocess_candidate_action():
    # Mock reprocess_applicant
    # Call reprocess_candidate()
    # Verify result

def test_send_questionnaire_action():
    # Create shortlisting result
    # Call send_questionnaire()
    # Verify notification sent

def test_schedule_interview_action():
    # Create interview brief
    # Call schedule_interview()
    # Verify event created
```

## Mocking LLM Responses

All tests mock the LLMClient to avoid actual API calls. Mock responses are defined in `conftest.py`:

```python
@pytest.fixture
def mock_llm_client():
    """Mock LLMClient for all services"""
    with patch("frappe_ai_hiring.ai_hiring.utils.llm_client.LLMClient.call_llm") as mock:
        def llm_side_effect(*args, **kwargs):
            operation = kwargs.get("operation_type", "")
            if "parse" in operation.lower():
                return {
                    "skills": ["Python", "FastAPI"],
                    "experience_years": 5,
                    "education": "BS Computer Science",
                }
            # ... other operation types
        mock.side_effect = llm_side_effect
        yield mock
```

To customize mock responses for specific tests:

```python
def test_custom_scenario(mock_llm_client):
    custom_response = {
        "decision": "Shortlist",
        "fit_score": 0.95,
    }
    mock_llm_client.return_value = custom_response
    
    # Your test code here
```

## Test Data

Tests create temporary test data using Frappe's document API:

```python
def setUp(self):
    # Create AI Settings
    self.ai_settings = frappe.new_doc("AI Settings")
    self.ai_settings.api_provider = "openai"
    self.ai_settings.save()
    
    # Create Job Opening
    self.job_opening = frappe.new_doc("Job Opening")
    self.job_opening.designation = "Software Engineer"
    self.job_opening.save()
```

Cleanup is automatic after each test via pytest fixtures.

## Common Issues

### Issue: "No module named 'frappe_ai_hiring'"
**Solution**: Ensure you're running tests from the bench directory with correct Python path

```bash
cd ~/frappe-bench
python -m pytest apps/frappe_ai_hiring/...
```

### Issue: "Database connection failed"
**Solution**: Ensure ERPNext is running and database is accessible

```bash
bench start  # In separate terminal
```

### Issue: "Missing fixture 'db'"
**Solution**: Install pytest-frappe plugin

```bash
pip install pytest-frappe>=0.14.0
```

### Issue: LLM responses not mocking correctly
**Solution**: Verify patch path matches import location in your code

```python
# If service imports like this:
from frappe_ai_hiring.ai_hiring.utils.llm_client import LLMClient

# Then patch like this:
patch("frappe_ai_hiring.ai_hiring.utils.llm_client.LLMClient.call_llm")
```

## Coverage Goals

Current test coverage targets:
- **Services**: 80%+ coverage of business logic
- **DocTypes**: Validation and method coverage
- **Utilities**: Core function coverage
- **Reports**: Query execution coverage

Generate coverage report:
```bash
python -m pytest apps/frappe_ai_hiring/frappe_ai_hiring/ai_hiring/tests \
  --cov=frappe_ai_hiring \
  --cov-report=html

# View report
open htmlcov/index.html
```

## Continuous Integration

For CI/CD pipelines, use:

```bash
# GitHub Actions example
python -m pytest apps/frappe_ai_hiring \
  --cov=frappe_ai_hiring \
  --cov-report=xml \
  --junitxml=test-results.xml \
  -v
```

## Next Steps

After confirming tests pass:
1. Deploy to staging environment
2. Run end-to-end manual tests with real candidates
3. Monitor pipeline execution in production
4. Collect metrics on AI recommendation accuracy

For questions or issues, refer to the [User Guide](../docs/USER_GUIDE.md).
