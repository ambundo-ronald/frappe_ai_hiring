# Question Generation Enhancement - Implementation Guide

## Overview

This document provides detailed code examples for implementing personalized question generation that leverages candidate resume data.

---

## Part 1: Data Extraction Helper Function

### Location
`frappe_ai_hiring/ai_hiring/services/question_generator.py`

### Function: `get_candidate_context()`

```python
def get_candidate_context(applicant_name: str) -> Optional[Dict[str, Any]]:
    """
    Extract and format candidate's resume data for LLM prompt inclusion.
    
    This function queries the AI Candidate Profile (created by resume parser)
    and structures the data for use in enhanced question generation prompts.
    
    Args:
        applicant_name: Job Applicant name (primary key)
        
    Returns:
        Dict with structured candidate context, or None if profile not found
        
    Structure:
    {
        "experience_years": float,
        "skills": list[str],
        "summary": str,
        "education": list[dict],
        "experience": list[dict],
        "projects": list[dict],
        "education_relevance": str,
        "confidence": float
    }
    
    Returns None if:
    - AI Candidate Profile doesn't exist for applicant
    - Resume parsing hasn't been completed
    - Parsed data is invalid/corrupt
    """
    try:
        # Step 1: Query AI Candidate Profile
        from frappe_ai_hiring.ai_hiring.doctype.ai_candidate_profile.ai_candidate_profile import (
            get_candidate_profile,
        )
        
        profile_data = get_candidate_profile(applicant_name)
        
        # Return None if no profile found (graceful degradation)
        if not profile_data:
            frappe.logger("ai_hiring").warn(
                f"No AI Candidate Profile for {applicant_name}. "
                "Will generate generic questions."
            )
            return None
        
        # Step 2: Load full profile document to access child tables
        profile_doc = frappe.get_doc("AI Candidate Profile", profile_data['name'])
        
        # Step 3: Parse the JSON resume data
        parsed_data = profile_doc.get_parsed_data()
        
        if not parsed_data:
            frappe.logger("ai_hiring").warn(
                f"No parsed data in profile {profile_data['name']}"
            )
            return None
        
        # Step 4: Build context dictionary
        context = {
            # Direct fields
            "experience_years": profile_doc.total_experience_years or 0,
            "skills": profile_doc.get_skills(),
            "summary": parsed_data.get("summary", ""),
            "education_relevance": profile_doc.education_relevance or "Not Specified",
            "confidence": profile_doc.ai_confidence_score or 0.0,
            
            # Complex fields from parsed JSON
            "education": parsed_data.get("education", []),
            "experience": parsed_data.get("experience", []),
            
            # Child table: projects
            "projects": _format_projects_from_table(profile_doc.projects),
        }
        
        return context
        
    except frappe.DoesNotExistError:
        frappe.logger("ai_hiring").warn(
            f"Job Applicant not found: {applicant_name}"
        )
        return None
    except json.JSONDecodeError as e:
        frappe.logger("ai_hiring").error(
            f"Invalid JSON in candidate profile {applicant_name}: {str(e)}"
        )
        return None
    except Exception as e:
        frappe.logger("ai_hiring").error(
            f"Error extracting candidate context for {applicant_name}: {str(e)}"
        )
        return None


def _format_projects_from_table(projects_table) -> list:
    """
    Convert projects child table to list of dicts.
    
    Args:
        projects_table: Child table from AI Candidate Profile
        
    Returns:
        List of project dicts
    """
    if not projects_table:
        return []
    
    formatted_projects = []
    for project in projects_table:
        # Parse skills string if present
        skills = []
        if project.skills:
            skills = [s.strip() for s in project.skills.split(",")]
        
        formatted_projects.append({
            "title": project.title or "",
            "contribution": project.candidate_contribution or "",
            "skills": skills,
        })
    
    return formatted_projects
```

---

## Part 2: Enhanced Prompt Generation

### Location
`frappe_ai_hiring/ai_hiring/services/question_generator.py`

### Function: `get_question_generation_prompt()` [UPDATED]

```python
def get_question_generation_prompt(
    job_role: str,
    job_description: str,
    difficulty_level: str,
    num_questions: int = 15,
    topics: Optional[List[str]] = None,
    candidate_context: Optional[Dict[str, Any]] = None  # NEW PARAMETER
) -> tuple[str, str]:
    """
    Generate system and user prompts for question generation.
    
    If candidate_context is provided, generates personalized prompts that
    include depth assessment, gap analysis, and verification questions.
    If not provided, falls back to generic job-description-based questions.
    
    Args:
        job_role: The job role title
        job_description: Full job description text
        difficulty_level: Easy, Medium, or Hard
        num_questions: Number of questions to generate (default 15)
        topics: Optional list of specific topics to cover
        candidate_context: Optional candidate resume data for personalization
        
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    
    # SYSTEM PROMPT (Enhanced)
    system_prompt = """You are an expert technical recruiter and interviewer who creates effective screening questions.

Your task is to generate binary (Yes/No) technical screening questions that can be used to quickly assess a candidate's qualifications.

CRITICAL REQUIREMENTS:
1. Each question must be answerable with a simple Yes or No
2. Questions should be direct and unambiguous
3. Focus on practical skills, experience, and knowledge
4. Questions should be fair and non-discriminatory
5. Avoid questions that are too easy or too obscure
6. Cover a range of topics relevant to the role
7. Each question should have a clear "expected_answer" (Yes or No)

QUESTION TYPES TO INCLUDE:
- Technology/tool experience: "Have you worked with [technology] in production?"
- Skill proficiency: "Can you explain/implement [concept] without references?"
- Project experience: "Have you completed projects involving [requirement]?"
- Problem-solving: "Can you design/architect [type of system]?"
- Best practices: "Are you familiar with [best practice/methodology]?"
- Domain knowledge: "Do you understand [domain concept]?"

"""
    
    # Add enhanced section if candidate data provided
    if candidate_context:
        system_prompt += """CANDIDATE-SPECIFIC QUESTION APPROACH:
Since candidate data is provided, generate questions in these categories:

1. GENERIC (Job-Description based) - ~40% of questions
   Questions on core requirements from the job description
   Should assess role fit regardless of background
   
2. DEPTH ASSESSMENT (Candidate's claimed skills) - ~35%
   Questions on technologies/skills they explicitly list in resume
   Verify they have practical hands-on experience
   Assess depth beyond just knowing the tool
   Example: "You list Django. Have you implemented custom middleware?"
   
3. GAP ANALYSIS (Missing from resume, required by JD) - ~15%
   Questions on important skills NOT listed in their resume but required by JD
   Assess ability and willingness to learn
   Example: "The role requires Kubernetes. Do you have container orchestration experience?"
   
4. VERIFICATION (Project/experience claims) - ~10%
   Questions about their specific projects, roles, or achievements listed
   Verify authenticity of claims on resume
   Assess their actual contribution vs claimed role
   Example: "You mention leading the E-commerce Platform. What was your exact role?"

Each question in output JSON must include:
{
    "topic": "...",
    "question_text": "...",
    "expected_answer": "Yes|No",
    "weight": 1-10,
    "type": "generic|depth|gap|verification",  # NEW
    "category": "...",  # NEW - which category this belongs to
    "rationale": "Why this question matters for this candidate"  # NEW
}

RATIONALE EXAMPLES:
- type=depth: "Candidate lists this skill, verify practical depth"
- type=gap: "Critical skill from JD not listed in resume"
- type=verification: "Verify contribution claims in specific project"
- type=generic: "Core requirement for the role"
"""
    
    system_prompt += """
OUTPUT FORMAT:
Return a JSON object with this exact structure:
{
    "questions": [
        {
            "topic": "Category/Area (e.g., Backend Development, Data Structures)",
            "question_text": "The actual question - must be Yes/No",
            "expected_answer": "Yes" or "No",
            "weight": 5-10 (importance of this question),
            "type": "generic|depth|gap|verification",
            "category": "Job Description|Claimed Skills|Missing Skills|Project Experience",
            "rationale": "Why this question matters for the role/candidate"
        }
    ],
    "metadata": {
        "difficulty_level": "The difficulty level used",
        "total_questions": "Number of questions generated",
        "topics_covered": ["List of topics covered"],
        "personalization": {
            "applicant_context": true/false,
            "question_distribution": {
                "generic": <count>,
                "depth": <count>,
                "gap": <count>,
                "verification": <count>
            }
        }
    }
}

DIFFICULTY GUIDELINES:
- Easy: Entry-level questions, basic concepts, common tools
- Medium: Intermediate experience, practical application, some depth
- Hard: Advanced concepts, architectural decisions, deep expertise"""

    # BUILD USER PROMPT
    
    # Topics instruction
    topics_instruction = ""
    if topics:
        topics_instruction = f"\n\nFOCUS ON THESE SPECIFIC TOPICS: {', '.join(topics)}"
    
    # Base user prompt
    user_prompt = f"""Generate {num_questions} binary (Yes/No) screening questions for the following role:

JOB ROLE: {job_role}

JOB DESCRIPTION:
{job_description}{topics_instruction}
"""
    
    # Add candidate context section if provided
    if candidate_context:
        user_prompt += _format_candidate_context_for_prompt(
            candidate_context,
            num_questions
        )
    
    # Add generation guidelines
    user_prompt += f"""
GENERATION GUIDELINES:
Generate questions that will effectively screen candidates for this role. Ensure questions are:
1. Directly relevant to the job requirements
2. Answerable with Yes or No
3. Fair and unbiased
4. Varied across different topics
5. Appropriate for the {difficulty_level} difficulty level
"""
    
    if candidate_context:
        user_prompt += """
PERSONALIZATION NOTES:
- Use the candidate background information to create relevant depth assessment questions
- Include verification questions about their specific projects
- Create gap analysis questions for important missing skills
- Distribute questions across all 4 types as specified in system prompt

Make questions specific and meaningful, not generic."""
    
    user_prompt += """
Return the questions in the exact JSON format specified."""

    return system_prompt, user_prompt


def _format_candidate_context_for_prompt(
    candidate_context: Dict[str, Any],
    num_questions: int
) -> str:
    """
    Format candidate context data for inclusion in user prompt.
    
    Structures resume data in a readable format for the LLM.
    """
    
    # Calculate question distribution
    total = num_questions
    generic_count = max(2, int(total * 0.40))  # ~40%
    depth_count = max(2, int(total * 0.35))    # ~35%
    gap_count = max(1, int(total * 0.15))      # ~15%
    verify_count = total - generic_count - depth_count - gap_count  # Rest
    
    # Format experience
    experience_str = ""
    if candidate_context.get("experience"):
        experience_str = "\nRECENT EXPERIENCE:\n"
        for i, exp in enumerate(candidate_context["experience"][:3], 1):  # Top 3
            experience_str += f"""
{i}. {exp.get('title', 'N/A')} @ {exp.get('company', 'N/A')}
   Duration: {exp.get('duration', 'N/A')}
   Responsibilities: {', '.join(exp.get('responsibilities', [])[:2])}
"""
    
    # Format projects
    projects_str = ""
    if candidate_context.get("projects"):
        projects_str = "\nNOTABLE PROJECTS:\n"
        for i, proj in enumerate(candidate_context["projects"], 1):
            tech_stack = ", ".join(proj.get("skills", []))
            projects_str += f"""
{i}. {proj.get('title', 'N/A')}
   Contribution: {proj.get('contribution', 'N/A')}
   Tech Stack: {tech_stack}
"""
    
    # Build the section
    context_section = f"""
CANDIDATE BACKGROUND:
- Years of Experience: {candidate_context.get('experience_years', 0)}
- Skills: {', '.join(candidate_context.get('skills', []))}
- Education Relevance: {candidate_context.get('education_relevance', 'Unknown')}
- Professional Summary: {candidate_context.get('summary', 'N/A')}{experience_str}{projects_str}

QUESTION DISTRIBUTION FOR THIS CANDIDATE:
- Generic (Job-Fit): ~{generic_count} questions
- Depth Assessment (Verify claimed skills): ~{depth_count} questions
- Gap Analysis (Missing skills from JD): ~{gap_count} questions
- Verification (Project/experience claims): ~{verify_count} questions

Total: {num_questions} personalized screening questions
"""
    
    return context_section
```

---

## Part 3: Enhanced Main Function

### Location
`frappe_ai_hiring/ai_hiring/services/question_generator.py`

### Function: `generate_questions()` [UPDATED]

```python
def generate_questions(
    job_role: str,
    job_description: str,
    difficulty_level: str = "Medium",
    num_questions: int = 15,
    topics: Optional[List[str]] = None,
    applicant_name: Optional[str] = None  # NEW PARAMETER
) -> Dict[str, Any]:
    """
    Generate screening questions for a job role using AI.
    
    Optionally personalizes questions based on candidate's resume.
    
    Args:
        job_role: The job role title
        job_description: Full job description text
        difficulty_level: Easy, Medium, or Hard (default: Medium)
        num_questions: Number of questions to generate (default: 15)
        topics: Optional list of specific topics to cover
        applicant_name: Optional applicant name for resume-based personalization
        
    Returns:
        Dict with questions and metadata
        
    Raises:
        ValueError: If inputs are invalid
        Exception: If generation fails
        
    Behavior:
    - If applicant_name provided and profile exists: generates personalized questions
    - If applicant_name provided but no profile: logs warning, generates generic questions
    - If applicant_name not provided: generates generic questions
    """
    
    # Validate inputs
    if not job_role or not job_role.strip():
        raise ValueError("Job role is required")
    
    if not job_description or not job_description.strip():
        raise ValueError("Job description is required")
    
    valid_difficulties = ["Easy", "Medium", "Hard"]
    if difficulty_level not in valid_difficulties:
        raise ValueError(f"Difficulty must be one of: {', '.join(valid_difficulties)}")
    
    if num_questions < 5 or num_questions > 50:
        raise ValueError("Number of questions must be between 5 and 50")
    
    # NEW: Get candidate context if applicant provided
    candidate_context = None
    candidate_info_str = ""
    
    if applicant_name:
        candidate_context = get_candidate_context(applicant_name)
        if candidate_context:
            candidate_info_str = f" for applicant {applicant_name}"
            frappe.logger("ai_hiring").info(
                f"Generating personalized questions{candidate_info_str} "
                f"(experience: {candidate_context.get('experience_years')} years, "
                f"skills: {len(candidate_context.get('skills', []))})"
            )
        else:
            frappe.logger("ai_hiring").warn(
                f"No candidate profile found for {applicant_name}, "
                "generating generic questions instead"
            )
    
    # Get prompts (enhanced to include candidate context)
    system_prompt, user_prompt = get_question_generation_prompt(
        job_role=job_role,
        job_description=job_description,
        difficulty_level=difficulty_level,
        num_questions=num_questions,
        topics=topics,
        candidate_context=candidate_context  # NEW
    )
    
    # Log the operation (pre-call)
    AIAuditLogger.log_llm_call(
        operation="Question Generation",
        prompt=f"[Generated prompts v{PROMPT_VERSION}]",
        response="",
        model="",
        metadata={
            "job_role": job_role,
            "difficulty_level": difficulty_level,
            "num_questions": num_questions,
            "topics": topics or [],
            "prompt_version": PROMPT_VERSION,
            "personalized": bool(candidate_context),  # NEW
            "applicant": applicant_name or None,  # NEW
        },
        success=True,
    )
    
    try:
        # Call LLM
        response = call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            reference_doctype="AI Question Set",
            operation_type="Question Generation"
        )
        
        # Validate schema (enhanced)
        validate_questions_schema(response, has_candidate_data=bool(candidate_context))
        
        # Log success
        AIAuditLogger.log_llm_call(
            operation="Question Generation",
            prompt="[Redacted]",
            response=f"Generated {len(response.get('questions', []))} questions",
            model="",
            metadata={
                "job_role": job_role,
                "topics_covered": response.get("metadata", {}).get("topics_covered", []),
                "count": len(response.get("questions", [])),
                "personalized": bool(candidate_context),  # NEW
                "question_types": response.get("metadata", {})
                    .get("personalization", {})
                    .get("question_distribution", {}),  # NEW
            },
            success=True,
        )
        
        return response
        
    except Exception as e:
        # Log failure
        AIAuditLogger.log_error(
            operation="Question Generation",
            error_message=str(e),
            metadata={
                "job_role": job_role,
                "personalized": bool(candidate_context),
                "applicant": applicant_name,
            },
        )
        raise
```

---

## Part 4: Enhanced Validation

### Location
`frappe_ai_hiring/ai_hiring/services/question_generator.py`

### Function: `validate_questions_schema()` [UPDATED]

```python
def validate_questions_schema(
    data: Dict[str, Any],
    has_candidate_data: bool = False  # NEW PARAMETER
) -> bool:
    """
    Validate the generated questions data structure.
    
    Args:
        data: The parsed JSON data from LLM
        has_candidate_data: If True, validate enhanced schema with type/category
        
    Returns:
        True if valid, raises exception if invalid
    """
    
    if not isinstance(data, dict):
        raise ValueError("Response must be a JSON object")
    
    if "questions" not in data:
        raise ValueError("Missing 'questions' field")
    
    if not isinstance(data["questions"], list):
        raise ValueError("'questions' must be an array")
    
    if len(data["questions"]) == 0:
        raise ValueError("At least one question is required")
    
    # Validate each question
    required_fields = ["topic", "question_text", "expected_answer", "weight"]
    valid_answers = ["Yes", "No"]
    
    # NEW: Fields required when has_candidate_data
    enhanced_fields = ["type", "category", "rationale"] if has_candidate_data else []
    valid_types = ["generic", "depth", "gap", "verification"]
    valid_categories = [
        "Job Description",
        "Claimed Skills",
        "Missing Skills", 
        "Project Experience"
    ]
    
    for idx, question in enumerate(data["questions"]):
        if not isinstance(question, dict):
            raise ValueError(f"Question {idx + 1} must be an object")
        
        # Check required base fields
        for field in required_fields:
            if field not in question:
                raise ValueError(f"Question {idx + 1} missing '{field}' field")
        
        # Validate expected_answer
        if question["expected_answer"] not in valid_answers:
            raise ValueError(
                f"Question {idx + 1} expected_answer must be 'Yes' or 'No', "
                f"got: {question['expected_answer']}"
            )
        
        # Validate weight
        weight = question["weight"]
        if not isinstance(weight, (int, float)) or weight < 1 or weight > 10:
            raise ValueError(f"Question {idx + 1} weight must be between 1 and 10")
        
        # Validate question_text
        question_text = question["question_text"].strip()
        if not question_text:
            raise ValueError(f"Question {idx + 1} has empty question_text")
        
        # NEW: Validate enhanced fields if candidate data was used
        if has_candidate_data:
            # Check enhanced required fields
            for field in enhanced_fields:
                if field not in question:
                    raise ValueError(
                        f"Question {idx + 1} missing '{field}' field "
                        "(required for personalized questions)"
                    )
            
            # Validate type
            if question["type"] not in valid_types:
                raise ValueError(
                    f"Question {idx + 1} has invalid type: {question['type']}. "
                    f"Must be one of: {', '.join(valid_types)}"
                )
            
            # Validate category
            if question["category"] not in valid_categories:
                raise ValueError(
                    f"Question {idx + 1} has invalid category: {question['category']}. "
                    f"Must be one of: {', '.join(valid_categories)}"
                )
            
            # Validate rationale is not empty
            if not isinstance(question.get("rationale"), str) or not question["rationale"].strip():
                raise ValueError(f"Question {idx + 1} has empty or invalid rationale")
    
    # NEW: Validate question distribution if metadata present
    if has_candidate_data and "metadata" in data:
        personalization = data.get("metadata", {}).get("personalization", {})
        distribution = personalization.get("question_distribution", {})
        
        if distribution:
            total_distributed = sum(distribution.values())
            if total_distributed != len(data["questions"]):
                frappe.logger("ai_hiring").warn(
                    f"Question distribution mismatch: "
                    f"distributed={total_distributed}, total={len(data['questions'])}"
                )
    
    return True
```

---

## Part 5: Updated Question Set Creation

### Location
`frappe_ai_hiring/ai_hiring/services/question_generator.py`

### Function: `create_question_set()` [UPDATED]

```python
def create_question_set(
    job_role: str,
    job_description: str,
    difficulty_level: str = "Medium",
    num_questions: int = 15,
    topics: Optional[List[str]] = None,
    passing_score: float = 70.0,
    applicant_name: Optional[str] = None  # NEW PARAMETER
) -> str:
    """
    Generate questions and create an AI Question Set document.
    
    Args:
        job_role: The job role title
        job_description: Full job description text
        difficulty_level: Easy, Medium, or Hard
        num_questions: Number of questions to generate
        topics: Optional list of specific topics
        passing_score: Minimum percentage to pass (default: 70.0)
        applicant_name: Optional applicant for personalized generation
        
    Returns:
        Name of the created AI Question Set document
        
    Raises:
        Exception: If creation fails
    """
    
    # Generate questions (enhanced with applicant_name)
    result = generate_questions(
        job_role=job_role,
        job_description=job_description,
        difficulty_level=difficulty_level,
        num_questions=num_questions,
        topics=topics,
        applicant_name=applicant_name  # NEW
    )
    
    # Create AI Question Set document
    question_set = frappe.new_doc("AI Question Set")
    question_set.job_role = job_role
    question_set.difficulty = difficulty_level
    question_set.passing_score = passing_score
    question_set.job_description = job_description
    question_set.total_questions = len(result["questions"])
    
    # NEW: Set applicant if personalized
    if applicant_name:
        question_set.based_on_applicant = applicant_name
        question_set.include_resume_based_questions = 1
    
    # Add questions
    for q_data in result["questions"]:
        # NEW: Include type and category in child rows
        question_set.append("questions", {
            "topic": q_data["topic"],
            "question_text": q_data["question_text"],
            "expected_answer": q_data["expected_answer"],
            "weight": q_data["weight"],
            # NEW fields - optional but stored if present
            "type": q_data.get("type", "generic"),  # Fallback to generic
            "category": q_data.get("category", "Job Description"),  # Fallback
        })
    
    # Save
    question_set.insert()
    frappe.db.commit()
    
    frappe.logger("ai_hiring").info(
        f"Created AI Question Set: {question_set.name} "
        f"with {len(result['questions'])} questions "
        f"{'(personalized for ' + applicant_name + ')' if applicant_name else '(generic)'}"
    )
    
    return question_set.name
```

---

## Part 6: API Layer Update

### Location
`frappe_ai_hiring/ai_hiring/doctype/job_applicant/job_applicant.py`

### Function: `generate_questions()` [UPDATED]

```python
@frappe.whitelist()
def generate_questions(
    job_applicant: str,
    difficulty: str = "Medium",
    num_questions: int = 15,
    personalized: bool = True  # NEW PARAMETER
):
    """
    Manually generate screening questions for the applicant's job role.
    
    Supports both personalized (based on resume) and generic generation.
    
    Args:
        job_applicant: Job Applicant name
        difficulty: Difficulty level (Easy/Medium/Hard)
        num_questions: Number of questions to generate
        personalized: If True, generate based on candidate's resume.
                      If False, generate generic questions. Default: True
        
    Returns:
        Dict with created question_set name
        
    Raises:
        Exception: If generation fails
    """
    
    if not frappe.has_permission("Job Applicant", "write", job_applicant):
        frappe.throw("Insufficient permissions")
    
    try:
        applicant = frappe.get_doc("Job Applicant", job_applicant)
        
        if not applicant.job_title:
            frappe.throw("Job title is required to generate questions")
        
        # Fetch job opening description if available
        job_description = ""
        if applicant.job_title:
            job_opening_name = frappe.db.get_value(
                "Job Opening",
                {"job_title": applicant.job_title},
                "name",
                order_by="creation desc"
            )
            if job_opening_name:
                job_opening = frappe.get_doc("Job Opening", job_opening_name)
                job_description = job_opening.description or ""
        
        if not job_description:
            frappe.throw("Job description is required")
        
        from frappe_ai_hiring.ai_hiring.services.question_generator import create_question_set
        
        # NEW: Pass applicant_name only if personalized=True
        applicant_to_use = job_applicant if personalized else None
        
        question_set_name = create_question_set(
            job_role=applicant.job_title,
            job_description=job_description,
            difficulty_level=difficulty,
            num_questions=num_questions,
            applicant_name=applicant_to_use  # NEW
        )
        
        # Inform via comment on applicant
        mode = "personalized" if personalized else "generic"
        applicant.add_comment(
            "Comment",
            f"Question set generated ({mode} mode): {question_set_name}"
        )
        
        frappe.msgprint(
            f"✅ Question set generated: {question_set_name}",
            indicator="green",
            alert=True
        )
        
        return {
            "success": True,
            "question_set": question_set_name,
            "personalized": personalized
        }
    
    except Exception as e:
        frappe.logger("ai_hiring").error(
            f"[GENERATE QUESTIONS] Applicant: {job_applicant}, "
            f"Job Title: {applicant.job_title if 'applicant' in locals() else 'N/A'}, "
            f"Error: {str(e)}"
        )
        frappe.throw(f"Failed to generate questions: {str(e)}")
```

---

## Part 7: Database Schema Updates

### File: `ai_question_set.json`

Add new fields to store personalization metadata:

```json
{
  "field_order": [
    // ... existing fields ...
    "personalization_section",
    "based_on_applicant",
    "include_resume_based_questions"
    // ... rest of fields ...
  ],
  "fields": [
    // ... existing fields ...
    {
      "fieldname": "personalization_section",
      "fieldtype": "Section Break",
      "label": "Personalization",
      "collapsible": 1
    },
    {
      "fieldname": "based_on_applicant",
      "fieldtype": "Link",
      "label": "Based on Applicant",
      "options": "Job Applicant",
      "description": "If set, questions are personalized to this applicant's resume"
    },
    {
      "fieldname": "include_resume_based_questions",
      "fieldtype": "Check",
      "label": "Include Resume-Based Questions",
      "default": 1,
      "description": "Whether this question set includes depth, gap, and verification questions"
    }
  ]
}
```

### File: `ai_question.json` (Child Table)

Add fields to store question metadata:

```json
{
  "fields": [
    // ... existing fields ...
    {
      "fieldname": "type",
      "fieldtype": "Select",
      "label": "Question Type",
      "options": "generic\ndepth\ngap\nverification",
      "description": "Type of screening question",
      "in_list_view": 1
    },
    {
      "fieldname": "category",
      "fieldtype": "Data",
      "label": "Category",
      "description": "Question category (Job Description, Claimed Skills, Missing Skills, Project Experience)"
    }
  ]
}
```

---

## Part 8: Unit Tests

### File: `frappe_ai_hiring/ai_hiring/tests/test_questions.py`

```python
import frappe
import pytest
from frappe.test_runner import FrappeTestCase


class TestQuestionGenerationWithCandidate(FrappeTestCase):
    """Tests for personalized question generation"""
    
    def setUp(self):
        """Setup test data"""
        # Create job applicant
        self.job_applicant = frappe.new_doc("Job Applicant")
        self.job_applicant.applicant_name = "Test Candidate"
        self.job_applicant.email_id = "test@example.com"
        self.job_applicant.job_title = "Senior Python Developer"
        self.job_applicant.save()
        
        # Create AI Candidate Profile with parsed resume
        self.profile = frappe.new_doc("AI Candidate Profile")
        self.profile.applicant = self.job_applicant.name
        self.profile.total_experience_years = 5
        self.profile.primary_skills = "Python, Django, PostgreSQL"
        self.profile.education_relevance = "Highly Relevant"
        self.profile.ai_confidence_score = 0.95
        
        # Set parsed resume JSON
        parsed_data = {
            "skills": ["Python", "Django", "PostgreSQL", "Docker"],
            "experience_years": 5,
            "summary": "Experienced Python developer",
            "education": [
                {
                    "degree": "B.S. Computer Science",
                    "institution": "State University",
                    "year": "2019",
                    "field": "Computer Science"
                }
            ],
            "experience": [
                {
                    "title": "Senior Developer",
                    "company": "Tech Corp",
                    "duration": "2020-Present",
                    "responsibilities": ["Backend development", "Architecture"]
                }
            ],
            "projects": [
                {
                    "title": "E-commerce Platform",
                    "candidate_contribution": "Led backend development",
                    "skills": ["Python", "Django", "PostgreSQL"]
                }
            ],
            "education_relevance": "Highly Relevant"
        }
        
        self.profile.set_parsed_data(parsed_data, "gpt-4", 0.95)
        self.profile.insert()
    
    def test_get_candidate_context_success(self):
        """Test successful candidate context extraction"""
        from frappe_ai_hiring.ai_hiring.services.question_generator import (
            get_candidate_context,
        )
        
        context = get_candidate_context(self.job_applicant.name)
        
        assert context is not None
        assert context["experience_years"] == 5
        assert "Python" in context["skills"]
        assert len(context["projects"]) == 1
        assert context["projects"][0]["title"] == "E-commerce Platform"
    
    def test_get_candidate_context_not_found(self):
        """Test graceful handling when profile doesn't exist"""
        from frappe_ai_hiring.ai_hiring.services.question_generator import (
            get_candidate_context,
        )
        
        context = get_candidate_context("NonExistentApplicant")
        
        assert context is None
    
    def test_generate_questions_personalized(self):
        """Test personalized question generation"""
        from frappe_ai_hiring.ai_hiring.services.question_generator import (
            generate_questions,
        )
        
        job_description = """
        Senior Python Developer
        Required: 5+ years Python, Django, PostgreSQL, Kubernetes, AWS
        """
        
        result = generate_questions(
            job_role="Senior Python Developer",
            job_description=job_description,
            difficulty_level="Medium",
            num_questions=10,
            applicant_name=self.job_applicant.name
        )
        
        # Check basic structure
        assert "questions" in result
        assert len(result["questions"]) == 10
        
        # Check for enhanced fields
        has_enhanced = False
        for q in result["questions"]:
            if "type" in q and "category" in q:
                has_enhanced = True
                assert q["type"] in ["generic", "depth", "gap", "verification"]
                assert q["category"] in [
                    "Job Description",
                    "Claimed Skills",
                    "Missing Skills",
                    "Project Experience"
                ]
        
        # At least some questions should have enhanced fields
        assert has_enhanced, "No enhanced questions found in personalized generation"
    
    def test_generate_questions_generic_fallback(self):
        """Test fallback to generic when profile missing"""
        from frappe_ai_hiring.ai_hiring.services.question_generator import (
            generate_questions,
        )
        
        job_description = "Senior Python Developer needed"
        
        # Generate for non-existent applicant (should not fail)
        result = generate_questions(
            job_role="Senior Python Developer",
            job_description=job_description,
            difficulty_level="Medium",
            num_questions=10,
            applicant_name="NonExistentApplicant"
        )
        
        # Should still generate questions
        assert "questions" in result
        assert len(result["questions"]) == 10
    
    def test_question_validation_enhanced_schema(self):
        """Test validation of enhanced schema"""
        from frappe_ai_hiring.ai_hiring.services.question_generator import (
            validate_questions_schema,
        )
        
        # Valid enhanced data
        valid_data = {
            "questions": [
                {
                    "topic": "Backend",
                    "question_text": "Have you used Django?",
                    "expected_answer": "Yes",
                    "weight": 8,
                    "type": "depth",
                    "category": "Claimed Skills",
                    "rationale": "Candidate lists Django"
                }
            ],
            "metadata": {
                "difficulty_level": "Medium",
                "total_questions": 1,
                "topics_covered": ["Backend"],
                "personalization": {
                    "question_distribution": {
                        "generic": 0,
                        "depth": 1,
                        "gap": 0,
                        "verification": 0
                    }
                }
            }
        }
        
        # Should pass validation
        assert validate_questions_schema(valid_data, has_candidate_data=True)
    
    def test_question_validation_invalid_type(self):
        """Test validation rejects invalid question type"""
        from frappe_ai_hiring.ai_hiring.services.question_generator import (
            validate_questions_schema,
        )
        
        invalid_data = {
            "questions": [
                {
                    "topic": "Backend",
                    "question_text": "Have you used Django?",
                    "expected_answer": "Yes",
                    "weight": 8,
                    "type": "invalid_type",  # Invalid!
                    "category": "Claimed Skills",
                    "rationale": "..."
                }
            ]
        }
        
        with pytest.raises(ValueError, match="invalid type"):
            validate_questions_schema(invalid_data, has_candidate_data=True)
    
    def test_create_question_set_personalized(self):
        """Test creating question set with personalization"""
        from frappe_ai_hiring.ai_hiring.services.question_generator import (
            create_question_set,
        )
        
        # Mock LLM response
        with frappe.mock_frappe_call("frappe_ai_hiring.ai_hiring.utils.llm_client.call_llm") as mock:
            mock.return_value = {
                "questions": [
                    {
                        "topic": "Backend",
                        "question_text": "Have you used Django?",
                        "expected_answer": "Yes",
                        "weight": 8,
                        "type": "depth",
                        "category": "Claimed Skills",
                        "rationale": "Candidate lists Django"
                    }
                ],
                "metadata": {
                    "difficulty_level": "Medium",
                    "total_questions": 1,
                    "topics_covered": ["Backend"]
                }
            }
            
            question_set_name = create_question_set(
                job_role="Senior Python Developer",
                job_description="Need Python dev",
                difficulty_level="Medium",
                num_questions=1,
                applicant_name=self.job_applicant.name
            )
        
        # Verify document created
        assert frappe.db.exists("AI Question Set", question_set_name)
        
        # Check personalization fields
        qs_doc = frappe.get_doc("AI Question Set", question_set_name)
        assert qs_doc.based_on_applicant == self.job_applicant.name
        assert qs_doc.include_resume_based_questions == 1
```

---

## Integration Checklist

- [ ] Implement `get_candidate_context()` function
- [ ] Update `get_question_generation_prompt()` with candidate context
- [ ] Update `generate_questions()` to accept applicant_name
- [ ] Update `validate_questions_schema()` for enhanced fields
- [ ] Update `create_question_set()` to pass applicant_name
- [ ] Update `job_applicant.py` `generate_questions()` API
- [ ] Add database schema fields
- [ ] Write and run unit tests
- [ ] Test end-to-end flow
- [ ] Update documentation
- [ ] Deploy and monitor

---

## Error Handling Best Practices

```python
# Always use try-except with specific error logging
try:
    context = get_candidate_context(applicant_name)
except Exception as e:
    frappe.logger("ai_hiring").error(
        f"Failed to get candidate context for {applicant_name}: {str(e)}"
    )
    # Gracefully degrade to generic generation
    context = None

# Validate before using
if context:
    # Use context
    pass
else:
    # Fallback
    pass

# Log decisions for troubleshooting
frappe.logger("ai_hiring").info(
    f"Generating {'personalized' if context else 'generic'} questions "
    f"for {applicant_name}"
)
```

---

## Performance Considerations

1. **Profile Query**: Queries AI Candidate Profile - should be fast (single row)
2. **JSON Parsing**: Parses stored JSON - minimal overhead
3. **LLM Call**: Most expensive operation - same as current, no change
4. **Data Formatting**: Minimal overhead for formatting candidate context

**No significant performance impact expected.**

---

## Monitoring & Logging

Monitor these metrics after deployment:

```python
# Log all question generations
frappe.logger("ai_hiring").info(
    f"Question Generation | "
    f"Applicant: {applicant_name} | "
    f"Personalized: {bool(candidate_context)} | "
    f"Questions: {num_questions} | "
    f"Duration: {elapsed_time}ms"
)

# Track personalization adoption
# Monitor ratio of personalized vs generic generations
# Watch error rates for candidate context extraction
```

