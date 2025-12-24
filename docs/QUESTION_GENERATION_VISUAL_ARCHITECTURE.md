# Question Generation Pipeline - Visual Architecture

## Current State (Job-Description Only)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Question Generation Pipeline                  │
│                      (Current - Generic)                         │
└─────────────────────────────────────────────────────────────────┘

Job Applicant Form (UI)
         │
         ▼
┌──────────────────────────────┐
│ generate_questions()         │  ◄── job_applicant.py
│ (job_applicant, difficulty) │
└──────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────┐
│ create_question_set()                                │
│ - Fetch job description from Job Opening             │
│ - Call generate_questions(job_role, jd)             │
└──────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────┐
│ LLM Service                                          │
│ ┌────────────────────────────────────────────────┐  │
│ │ System Prompt (Generic)                        │  │
│ │ "Generate binary tech screening questions"    │  │
│ └────────────────────────────────────────────────┘  │
│ ┌────────────────────────────────────────────────┐  │
│ │ User Prompt (JD Only)                          │  │
│ │ "JOB ROLE: [role]                              │  │
│ │  JOB DESCRIPTION: [description]                │  │
│ │  DIFFICULTY: [level]"                          │  │
│ └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────┐
│ AI Question Set Created                              │
│ - All questions based on JD only                     │
│ - Same questions for all candidates in same role     │
│ - No personalization or verification                 │
└──────────────────────────────────────────────────────┘

❌ ISSUE: No candidate-specific assessment
```

---

## Enhanced State (Job Description + Candidate Resume)

```
┌─────────────────────────────────────────────────────────────────┐
│            Enhanced Question Generation Pipeline                 │
│          (Proposed - Personalized + Generic)                    │
└─────────────────────────────────────────────────────────────────┘

Job Applicant Form (UI)
         │
         ├─ generate_questions(job_applicant, personalized=True)
         │
         ▼
┌──────────────────────────────────────────────────────┐
│ create_question_set()                                │
│ - Fetch job description                              │
│ - applicant_name parameter passed (NEW)              │
└──────────────────────────────────────────────────────┘
         │
         ├──────────────────────────────────────┐
         │                                      │
         ▼                                      ▼
    Get Job Data                    Get Candidate Data
    ┌─────────────────┐             ┌──────────────────────────┐
    │ Job Opening     │             │ AI Candidate Profile     │
    ├─────────────────┤             ├──────────────────────────┤
    │ • Role Title    │             │ • Experience Years       │
    │ • Description   │             │ • Skills List            │
    │ • Requirements  │             │ • Education Level        │
    │ • Tech Stack    │             │ • Projects (table)       │
    │ • Experience    │             │ • Parsed Resume JSON     │
    │   Level         │             │ • Confidence Score       │
    └─────────────────┘             └──────────────────────────┘
         │
         └──────────────┬───────────────────────┘
                        │
                        ▼
         ┌──────────────────────────────────────┐
         │ Candidate Context Extraction         │
         │ (NEW Helper Function)                │
         ├──────────────────────────────────────┤
         │ • Parse resume_json                  │
         │ • Extract projects[]                 │
         │ • List claimed skills                │
         │ • Get experience_years               │
         │ • Get education_relevance            │
         └──────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────┐
│ Enhanced LLM Service                                 │
│ ┌────────────────────────────────────────────────┐  │
│ │ System Prompt (Enhanced)                       │  │
│ │ [Original] +                                   │  │
│ │ "CANDIDATE-SPECIFIC QUESTION TYPES:            │  │
│ │ - Depth Assessment (claimed skills)            │  │
│ │ - Project Verification (specific projects)     │  │
│ │ - Gap Analysis (missing skills)                │  │
│ │ - Experience Validation (work history)"        │  │
│ └────────────────────────────────────────────────┘  │
│ ┌────────────────────────────────────────────────┐  │
│ │ User Prompt (Enhanced)                         │  │
│ │ "JOB REQUIREMENTS:                             │  │
│ │  [job_description]                             │  │
│ │                                                │  │
│ │  CANDIDATE BACKGROUND:                         │  │
│ │  - Experience: 5 years                         │  │
│ │  - Skills: [Python, Django, PostgreSQL, ...]  │  │
│ │  - Summary: [professional summary]             │  │
│ │                                                │  │
│ │  CANDIDATE'S EXPERIENCE:                       │  │
│ │  [Recent roles from resume]                    │  │
│ │                                                │  │
│ │  CANDIDATE'S PROJECTS:                         │  │
│ │  [Notable projects with contributions]         │  │
│ │                                                │  │
│ │  GENERATE:                                     │  │
│ │  - 6 generic role-fit questions                │  │
│ │  - 5 depth assessment questions                │  │
│ │  - 2 gap analysis questions                    │  │
│ │  - 2 verification questions"                   │  │
│ └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────┐
│ Enhanced Validation                                  │
│ ├─ Validate existing schema                         │
│ ├─ Validate new fields:                             │
│ │  • type (generic|depth|gap|verification)          │
│ │  • category (field-mapped)                        │
│ │  • rationale (why this question)                  │
│ └─ Check question distribution                      │
└──────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────┐
│ AI Question Set Created (Enhanced)                   │
│ ├─ 40% Generic: Job role fit                        │
│ ├─ 35% Depth: Verify claimed skills                 │
│ ├─ 15% Gap: Assess missing requirements             │
│ ├─ 10% Verification: Project/experience claims      │
│ │                                                    │
│ ├─ New fields:                                      │
│ │  • based_on_applicant: JOB-APP-2024-00001         │
│ │  • include_resume_based_questions: checked        │
│ │  • Each question has type & category              │
│ │                                                    │
│ └─ Different for each candidate! ✓                  │
└──────────────────────────────────────────────────────┘

✅ BENEFIT: Personalized assessment + verification + gap analysis
```

---

## Data Flow Comparison

### Current Flow
```
Job Description
       │
       ▼
    [LLM]
       │
       ▼
    Questions (generic)
```

### Enhanced Flow
```
Job Description ──┐
                  ├──→ Format Context ──→ [LLM] ──→ Questions
Resume Data ──────┤                  (Enhanced)    (Personalized)
Candidate Skills ─┘
```

---

## Candidate Context Extraction

```
┌─────────────────────────────────────────────────────────┐
│ get_candidate_context(applicant_name) [NEW]            │
│                                                         │
│ Input: Job Applicant Name (string)                     │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ STEP 1: Query AI Candidate Profile                     │
│  SELECT parsed_resume_json, total_experience_years     │
│         primary_skills, education_relevance            │
│  WHERE applicant = applicant_name                       │
├─────────────────────────────────────────────────────────┤
│ STEP 2: Parse JSON                                      │
│  - parsed_resume_json → dict                           │
│  - Extract:                                            │
│    • experience[]                                      │
│    • projects[]                                        │
│    • education[]                                       │
│    • summary                                           │
├─────────────────────────────────────────────────────────┤
│ STEP 3: Build Context Dict                            │
│ {                                                       │
│   "experience_years": 5,                               │
│   "skills": ["Python", "Django", ...],                │
│   "summary": "...",                                    │
│   "education": [...],                                  │
│   "experience": [                                      │
│     {                                                  │
│       "title": "Senior Developer",                     │
│       "company": "Tech Corp",                          │
│       "duration": "2020-Present"                       │
│     }                                                  │
│   ],                                                   │
│   "projects": [                                        │
│     {                                                  │
│       "title": "E-commerce Platform",                  │
│       "contribution": "Led backend development",       │
│       "skills": ["Python", "Django", "PostgreSQL"]     │
│     }                                                  │
│   ],                                                   │
│   "education_relevance": "Highly Relevant",            │
│   "confidence": 0.95                                   │
│ }                                                       │
├─────────────────────────────────────────────────────────┤
│ Output: Context Dict (or None if no profile)          │
└─────────────────────────────────────────────────────────┘
```

---

## Question Generation Distribution

### Without Candidate Data (Current)
```
All 15 Questions
┌──────────────────────────┐
│   Generic Questions      │  100%
│   (Job Description)      │
└──────────────────────────┘
```

### With Candidate Data (Enhanced)
```
15 Questions Distributed
┌────────────────┬─────────────────┐
│ Generic (6)    │ Job Description │  40%
│ - Role fit     │                 │
│ - Core skills  │                 │
├────────────────┼─────────────────┤
│ Depth (5)      │ Claimed Skills  │  35%
│ - Verify facts │ Verification    │
│ - Skill depth  │                 │
├────────────────┼─────────────────┤
│ Gap (2)        │ Missing Skills  │  15%
│ - Can learn?   │ Assessment      │
│ - Interest?    │                 │
├────────────────┼─────────────────┤
│ Verify (2)     │ Project/Work    │  10%
│ - Project q's  │ Experience      │
└────────────────┴─────────────────┘

Each question category serves different purpose!
```

---

## Example: Question Generation for Candidate

### Scenario
```
Job Opening: Senior Python Developer
Job Description: 
  "We need experienced Python developer with 5+ years, 
   Django/FastAPI, PostgreSQL, Redis, Docker, Kubernetes, 
   AWS experience"

Candidate Resume:
  Experience: 5 years
  Skills: Python, JavaScript, Django, PostgreSQL, 
          Redis, Docker, Git, HTML/CSS
  Current: Senior Developer at Tech Corp (2020-Present)
  Projects: E-commerce Platform (led backend, Python/Django/PostgreSQL),
            Analytics Dashboard (data pipeline, Python/Redis)
  Missing: Kubernetes, AWS, FastAPI, Microservices
```

### Generated Questions (15 total)

**GENERIC (6 questions)** - 40%
```
1. Have you used Django for building production web applications?
   Expected: Yes
   Type: generic
   Category: Job Description
   Weight: 8

2. Do you have experience with PostgreSQL database design and optimization?
   Expected: Yes
   Type: generic
   Category: Job Description
   Weight: 8

3. Can you explain Docker containerization and how you'd containerize a Python app?
   Expected: Yes
   Type: generic
   Category: Job Description
   Weight: 7

4. Have you worked with caching solutions like Redis in production?
   Expected: Yes
   Type: generic
   Category: Job Description
   Weight: 7

5. Do you understand REST API design principles and HTTP methods?
   Expected: Yes
   Type: generic
   Category: Job Description
   Weight: 6

6. Have you worked with Git version control in team environments?
   Expected: Yes
   Type: generic
   Category: Job Description
   Weight: 6
```

**DEPTH ASSESSMENT (5 questions)** - 35%
```
7. In your E-commerce Platform project, you mentioned using Django. 
   Did you implement custom middleware or signal handlers?
   Expected: Yes
   Type: depth
   Category: Claimed Skills
   Weight: 8
   Rationale: Assesses depth of Django expertise claimed

8. You list Redis as a skill. Have you implemented caching strategies, 
   pub/sub messaging, or sessions with Redis?
   Expected: Yes
   Type: depth
   Category: Claimed Skills
   Weight: 7
   Rationale: Verify practical Redis experience beyond listing

9. PostgreSQL appears in your projects. Have you written complex queries, 
   indexes, or done query optimization?
   Expected: Yes
   Type: depth
   Category: Claimed Skills
   Weight: 8
   Rationale: Assess database depth beyond CRUD operations

10. In your Analytics Dashboard project, you handled data pipelines. 
    Did you design the schema or write ETL logic?
    Expected: Yes
    Type: depth
    Category: Claimed Skills
    Weight: 7
    Rationale: Verify contribution claims in project

11. Your experience is 5 years as claimed. Have you led 
    architectural decisions or mentored junior developers?
    Expected: Yes
    Type: depth
    Category: Claimed Skills
    Weight: 6
    Rationale: Validate "senior" level experience
```

**GAP ANALYSIS (2 questions)** - 15%
```
12. Kubernetes is an important requirement. Do you have experience 
    with container orchestration platforms?
    Expected: No (likely, given resume), but willing to learn
    Type: gap
    Category: Missing Skills
    Weight: 9
    Rationale: Critical skill missing, assess openness to learning

13. AWS cloud platform is required. Do you have hands-on experience 
    deploying and managing applications on AWS?
    Expected: No (likely, given resume), but willing to learn
    Type: gap
    Category: Missing Skills
    Weight: 8
    Rationale: Key requirement gap, assess cloud readiness
```

**VERIFICATION (2 questions)** - 10%
```
14. In your E-commerce Platform, what was your exact role? 
    Did you lead the entire backend or specific components?
    Expected: Specific detailed answer showing leadership
    Type: verification
    Category: Project Experience
    Weight: 9
    Rationale: Verify leadership claims in project

15. You've worked with both Django and Python for 5 years. 
    Can you tell us about the most complex architectural decision 
    you made and why?
    Expected: Thoughtful answer showing judgment
    Type: verification
    Category: Project Experience
    Weight: 8
    Rationale: Verify depth and decision-making capability
```

---

## Key Insights from Enhanced Approach

```
CANDIDATE: John (Senior Python Dev, 5 years)

JOB REQUIREMENTS          │ CANDIDATE HAS           │ QUESTION TYPE
──────────────────────────┼────────────────────────┼──────────────────
Python 5+ years          │ ✓ Python 5 years       │ DEPTH - verify depth
Django/FastAPI           │ ✓ Django                │ DEPTH - assess depth
                         │ ✗ FastAPI              │ GAP - can learn?
PostgreSQL               │ ✓ PostgreSQL            │ DEPTH - implementation?
Redis                    │ ✓ Redis                 │ DEPTH - patterns?
Docker                   │ ✓ Docker                │ GENERIC - confirm
Kubernetes               │ ✗ NOT listed            │ GAP - openness?
AWS                      │ ✗ NOT listed            │ GAP - cloud knowledge?

Generic: 6 questions on core role requirements
Depth: 5 questions to verify their actual skill depth  
Gap: 2 questions to assess missing-but-learnable skills
Verify: 2 questions on their specific projects/claims

TOTAL: 15 personalized questions for JOHN specifically
```

---

## Benefits Illustrated

```
BEFORE (Generic)
Q: Have you used Python?
Q: Do you know Django?
Q: Can you design databases?
   ↓
   Questions could be for ANY role
   No assessment of actual background
   No verification of claims
   No gap analysis

AFTER (Personalized)
Q1: Have you used Django? (GENERIC)
    → For any Python dev role

Q7: In your E-commerce Platform with Django, did you implement 
    custom middleware? (DEPTH)
    → Verify HIS specific experience

Q12: Kubernetes - do you have orchestration experience? (GAP)
    → Assess learning potential

Q14: In your E-commerce Platform, what was your exact role? (VERIFY)
    → Confirm claims in resume

   ↓
   Questions tailored to JOHN
   Assesses actual background + claims
   Verifies skill depth
   Identifies gaps to develop
   Better hiring signal!
```

---

## File Structure After Enhancement

```
frappe_ai_hiring/
├── ai_hiring/
│   ├── services/
│   │   ├── question_generator.py [MODIFIED]
│   │   │   ├── get_candidate_context() [NEW]
│   │   │   ├── get_question_generation_prompt() [ENHANCED]
│   │   │   ├── generate_questions() [ENHANCED]
│   │   │   ├── create_question_set() [ENHANCED]
│   │   │   └── validate_questions_schema() [ENHANCED]
│   │   │
│   │   ├── resume_parser.py [NO CHANGE]
│   │   ├── shortlisting_service.py [NO CHANGE - reference pattern]
│   │   └── interview_brief_service.py [NO CHANGE - reference pattern]
│   │
│   ├── doctype/
│   │   ├── job_applicant/
│   │   │   └── job_applicant.py [MODIFIED]
│   │   │       └── generate_questions() [ENHANCED with personalized param]
│   │   │
│   │   ├── ai_question_set/
│   │   │   ├── ai_question_set.json [MODIFIED - new fields]
│   │   │   ├── ai_question_set.py [MODIFIED - new calculations]
│   │   │   └── test_ai_question_set.py [TESTS]
│   │   │
│   │   └── ai_candidate_profile/
│   │       └── ai_candidate_profile.py [NO CHANGE]
│   │
│   └── tests/
│       ├── test_questions.py [ENHANCED - new test cases]
│       └── conftest.py [NO CHANGE]
```

---

## Summary Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                   DATA SOURCES TO LEVERAGE                      │
└─────────────────────────────────────────────────────────────────┘

AI Candidate Profile (Created by Resume Parser)
    │
    ├─ parsed_resume_json ◄─── Full structured resume
    │   ├─ skills: []
    │   ├─ experience: []
    │   ├─ projects: []
    │   ├─ education: []
    │   └─ summary: ""
    │
    ├─ total_experience_years ◄─ Quick access
    ├─ primary_skills ◄─ Top skills
    ├─ skill_vector ◄─ Skills as JSON
    ├─ projects[] ◄─ Child table
    ├─ education_relevance ◄─ Qualification assessment
    └─ ai_confidence_score ◄─ Parse confidence

Job Opening (Existing)
    │
    ├─ job_title
    ├─ job_description
    ├─ required_skills
    └─ experience_level

        BOTH ──────────────→ Enhanced LLM Prompt
                            ↓
                    Personalized Questions
                    ✓ Generic (40%)
                    ✓ Depth (35%)
                    ✓ Gap (15%)
                    ✓ Verification (10%)
```

