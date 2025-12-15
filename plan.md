# 📄 AI-Driven Hiring Automation System

### Technical & Implementation Specification

**Target Platform:** Frappe Framework + Frappe HRMS
**App Name:** `frappe_ai_hiring`
**Audience:** LLM (for code generation), Senior Engineers
**Purpose:** End-to-End AI-Assisted Candidate Shortlisting & Interview Support

---

## 1. SYSTEM GOAL

Build an **AI-assisted hiring automation system** that integrates with **Frappe HRMS** to:

1. Parse and understand resumes
2. Shortlist candidates against Job Descriptions
3. Generate and evaluate **binary technical questionnaires**
4. Maintain candidate progression state
5. Generate **interviewer-ready summaries**
6. Preserve auditability, explainability, and human control

The system **must not auto-hire** candidates.

---

## 2. NON-FUNCTIONAL REQUIREMENTS

* Must be installed as a **separate Frappe app**
* Must be **OpenAI-compatible** (OpenAI / Azure / Ollama)
* Must be **async & scalable**
* Must log **every AI decision**
* Must redact **PII before LLM calls**
* Must be **multi-tenant safe**

---

## 3. HIGH-LEVEL ARCHITECTURE

```
Frappe HRMS
 └── Job Opening
 └── Job Applicant
        ↓ (Doc Event Hook)
AI Hiring App
 ├── Resume Parser
 ├── JD Matcher
 ├── Shortlisting Engine
 ├── Question Generator
 ├── Questionnaire Evaluator
 ├── Interview Summary Generator
 └── Analytics
        ↓
Back to HRMS (Status Updates + Notes)
```

---

## 4. DATA FLOW (END-TO-END)

### 4.1 Trigger

* A `Job Applicant` is created or updated with a resume

### 4.2 Resume Parsing

* Resume → Structured JSON
* Skills normalized
* Experience inferred

### 4.3 AI Shortlisting

* Resume JSON + Job Description
* AI returns:

  * Fit Score
  * Decision
  * Explanation
  * Missing Skills

### 4.4 Questionnaire Stage

* AI generates **binary questions**
* Candidate answers
* Auto-scoring
* Threshold-based progression

### 4.5 Interview Support

* AI generates interviewer brief
* Interviewer adds notes
* AI summarizes feedback

---

## 5. DOCTYPE DEFINITIONS (STRICT)

### 5.1 AI Candidate Profile

**Purpose:** Canonical AI-understood representation of candidate

```yaml
DocType: AI Candidate Profile
Fields:
  - applicant (Link → Job Applicant)
  - job_opening (Link → Job Opening)
  - parsed_resume_json (Long Text, JSON)
  - skill_vector (Long Text, JSON)
  - total_experience_years (Float)
  - education_relevance (Select)
  - ai_confidence_score (Float)
  - pii_redacted (Check)
Indexes:
  - applicant
  - job_opening
```

---

### 5.2 AI Shortlisting Result

```yaml
DocType: AI Shortlisting Result
Fields:
  - applicant (Link → Job Applicant)
  - job_opening (Link → Job Opening)
  - fit_score (Float)
  - decision (Select: Shortlist, Reject, Review)
  - reasons (Long Text)
  - missing_skills (Long Text)
  - model_name (Data)
  - prompt_version (Data)
  - raw_llm_response (Long Text)
  - created_on (Datetime)
Permissions:
  - Read: HR Manager
```

---

### 5.3 AI Question Set

```yaml
DocType: AI Question Set
Fields:
  - job_role (Data)
  - difficulty (Select: Basic, Intermediate)
  - total_questions (Int)
  - questions (Child Table → AI Question)
```

#### Child: AI Question

```yaml
Fields:
  - topic (Select: OS, DBMS, OOP, SDLC, Language)
  - question_text (Text)
  - expected_answer (Select: Yes, No)
  - weight (Int)
```

---

### 5.4 AI Evaluation Result

```yaml
DocType: AI Evaluation Result
Fields:
  - applicant (Link)
  - question_set (Link)
  - total_score (Float)
  - pass_fail (Select)
  - inconsistencies (Long Text)
  - recommendation (Text)
```

---

### 5.5 AI Interview Brief

```yaml
DocType: AI Interview Brief
Fields:
  - applicant (Link)
  - strengths (Text)
  - weak_areas (Text)
  - verification_points (Text)
  - suggested_questions (Long Text)
  - final_summary (Long Text)
```

---

## 6. LLM INTEGRATION SPECIFICATION

### 6.1 LLM Configuration

```yaml
Settings:
  provider: openai_compatible
  api_base_url: string
  api_key: encrypted
  default_model: gpt-4.1-mini
  temperature: 0.2
  timeout: 60s
```

---

### 6.2 Prompt Versioning

All prompts must:

* Be stored in code
* Have explicit version numbers
* Produce **STRICT JSON**

---

## 7. PROMPT TEMPLATES (CANONICAL)

### 7.1 Resume Shortlisting Prompt

```text
SYSTEM:
You are a senior technical recruiter AI.

USER:
Job Description:
{{job_description}}

Candidate Resume (Structured JSON):
{{resume_json}}

RULES:
- Do not infer age, gender, religion
- Evaluate only technical and professional fit

OUTPUT STRICT JSON:
{
  "fit_score": 0-100,
  "decision": "Shortlist | Reject | Review",
  "reasons": [string],
  "missing_skills": [string],
  "confidence_score": 0-1
}
```

---

### 7.2 Question Generation Prompt

```text
SYSTEM:
You generate basic technical screening questions.

USER:
Job Role: {{role}}
Primary Skills: {{skills}}

RULES:
- Questions must be binary
- Cover OS, OOP, SDLC, Core Language

OUTPUT JSON:
{
  "questions": [
    {
      "topic": "OS",
      "question": "Do you understand process vs thread?",
      "expected_answer": "Yes"
    }
  ]
}
```

---

### 7.3 Interview Summary Prompt

```text
SYSTEM:
You assist interviewers.

USER:
Candidate Data:
{{candidate_profile}}

Interview Notes:
{{interviewer_notes}}

OUTPUT JSON:
{
  "strengths": [],
  "risks": [],
  "verification_points": [],
  "hire_recommendation": "Yes | No | Maybe"
}
```

---

## 8. BACKGROUND JOBS (MANDATORY)

All LLM calls must be async.

```python
frappe.enqueue(
  method="ai_hiring.jobs.shortlist_candidate",
  queue="long",
  timeout=300
)
```

---

## 9. SECURITY & COMPLIANCE

* Remove:

  * Name
  * Phone
  * Email
* Replace with tokens before LLM calls
* Store original resume encrypted
* Log:

  * Prompt
  * Model
  * Response

---

## 10. PIPELINE STATES

```text
Applied
→ AI Parsed
→ AI Shortlisted
→ Questionnaire Sent
→ Questionnaire Passed
→ Interview Scheduled
→ Interview Completed
→ Offer / Rejected
```

---

## 11. EXTENSIBILITY RULES

* New job roles must not require code changes
* Question sets are regeneratable
* Model upgrades must not break stored data

---

## 12. SUCCESS CRITERIA

* Reduce resume screening time by ≥70%
* Interviewer prep time ≤5 minutes per candidate
* Explainable rejection reasons for every candidate

---

## 13. INSTRUCTION TO LLM (IMPORTANT)

> **You must strictly follow this document.
> Do not invent fields, flows, or logic not defined here.
> Generate production-ready Frappe app code.**
