"""
Question Generation Service
Generates role-specific binary (Yes/No) technical screening questions using AI.
"""

import frappe
from typing import Dict, List, Any, Optional
import json
from frappe_ai_hiring.ai_hiring.utils.llm_client import call_llm
from frappe_ai_hiring.ai_hiring.utils.audit_logger import log_ai_operation


PROMPT_VERSION = "1.0.0"


def get_question_generation_prompt(
    job_role: str,
    job_description: str,
    difficulty_level: str,
    num_questions: int = 15,
    topics: Optional[List[str]] = None
) -> tuple[str, str]:
    """
    Generate the system and user prompts for question generation.
    
    Args:
        job_role: The job role title
        job_description: Full job description text
        difficulty_level: Easy, Medium, or Hard
        num_questions: Number of questions to generate (default 15)
        topics: Optional list of specific topics to cover
        
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    
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

OUTPUT FORMAT:
Return a JSON object with this exact structure:
{
    "questions": [
        {
            "topic": "Category/Area (e.g., Backend Development, Data Structures)",
            "question_text": "The actual question - must be Yes/No",
            "expected_answer": "Yes" or "No",
            "weight": 5-10 (importance of this question),
            "rationale": "Why this question matters for the role"
        }
    ],
    "metadata": {
        "difficulty_level": "The difficulty level used",
        "total_questions": "Number of questions generated",
        "topics_covered": ["List of topics covered"]
    }
}

DIFFICULTY GUIDELINES:
- Easy: Entry-level questions, basic concepts, common tools
- Medium: Intermediate experience, practical application, some depth
- Hard: Advanced concepts, architectural decisions, deep expertise"""

    topics_instruction = ""
    if topics:
        topics_instruction = f"\n\nFOCUS ON THESE SPECIFIC TOPICS: {', '.join(topics)}"
    
    user_prompt = f"""Generate {num_questions} binary (Yes/No) screening questions for the following role:

JOB ROLE: {job_role}

JOB DESCRIPTION:
{job_description}

DIFFICULTY LEVEL: {difficulty_level}{topics_instruction}

Generate questions that will effectively screen candidates for this role. Ensure questions are:
1. Directly relevant to the job requirements
2. Answerable with Yes or No
3. Fair and unbiased
4. Varied across different topics
5. Appropriate for the {difficulty_level} difficulty level

Return the questions in the exact JSON format specified."""

    return system_prompt, user_prompt


def validate_questions_schema(data: Dict[str, Any]) -> bool:
    """
    Validate the generated questions data structure.
    
    Args:
        data: The parsed JSON data from LLM
        
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
    
    for idx, question in enumerate(data["questions"]):
        if not isinstance(question, dict):
            raise ValueError(f"Question {idx + 1} must be an object")
        
        for field in required_fields:
            if field not in question:
                raise ValueError(f"Question {idx + 1} missing '{field}' field")
        
        if question["expected_answer"] not in valid_answers:
            raise ValueError(
                f"Question {idx + 1} expected_answer must be 'Yes' or 'No', "
                f"got: {question['expected_answer']}"
            )
        
        weight = question["weight"]
        if not isinstance(weight, (int, float)) or weight < 1 or weight > 10:
            raise ValueError(f"Question {idx + 1} weight must be between 1 and 10")
        
        # Validate that question ends with ? or is clearly a question
        question_text = question["question_text"].strip()
        if not question_text:
            raise ValueError(f"Question {idx + 1} has empty question_text")
    
    return True


def generate_questions(
    job_role: str,
    job_description: str,
    difficulty_level: str = "Medium",
    num_questions: int = 15,
    topics: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Generate screening questions for a job role using AI.
    
    Args:
        job_role: The job role title
        job_description: Full job description text
        difficulty_level: Easy, Medium, or Hard (default: Medium)
        num_questions: Number of questions to generate (default: 15)
        topics: Optional list of specific topics to cover
        
    Returns:
        Dict with questions and metadata
        
    Raises:
        Exception: If generation fails
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
    
    # Get prompts
    system_prompt, user_prompt = get_question_generation_prompt(
        job_role=job_role,
        job_description=job_description,
        difficulty_level=difficulty_level,
        num_questions=num_questions,
        topics=topics
    )
    
    # Log the operation
    log_ai_operation(
        operation_type="question_generation",
        input_data={
            "job_role": job_role,
            "difficulty_level": difficulty_level,
            "num_questions": num_questions,
            "topics": topics or [],
            "prompt_version": PROMPT_VERSION
        },
        reference_doctype="AI Question Set",
        reference_name=None
    )
    
    try:
        # Call LLM
        response = call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            reference_doctype="AI Question Set",
            operation_type="question_generation"
        )
        
        # Validate schema
        validate_questions_schema(response)
        
        # Log success
        log_ai_operation(
            operation_type="question_generation",
            input_data={"job_role": job_role},
            output_data={
                "questions_generated": len(response.get("questions", [])),
                "topics_covered": response.get("metadata", {}).get("topics_covered", [])
            },
            reference_doctype="AI Question Set",
            reference_name=None,
            status="Success"
        )
        
        return response
        
    except Exception as e:
        # Log failure
        log_ai_operation(
            operation_type="question_generation",
            input_data={"job_role": job_role},
            error_message=str(e),
            reference_doctype="AI Question Set",
            reference_name=None,
            status="Failed"
        )
        raise


def create_question_set(
    job_role: str,
    job_description: str,
    difficulty_level: str = "Medium",
    num_questions: int = 15,
    topics: Optional[List[str]] = None,
    passing_score: float = 70.0
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
        
    Returns:
        Name of the created AI Question Set document
        
    Raises:
        Exception: If creation fails
    """
    
    # Generate questions
    result = generate_questions(
        job_role=job_role,
        job_description=job_description,
        difficulty_level=difficulty_level,
        num_questions=num_questions,
        topics=topics
    )
    
    # Create AI Question Set document
    question_set = frappe.new_doc("AI Question Set")
    question_set.job_role = job_role
    question_set.difficulty = difficulty_level
    question_set.passing_score = passing_score
    question_set.job_description = job_description
    question_set.total_questions = len(result["questions"])
    
    # Add questions
    for q_data in result["questions"]:
        question_set.append("questions", {
            "topic": q_data["topic"],
            "question_text": q_data["question_text"],
            "expected_answer": q_data["expected_answer"],
            "weight": q_data["weight"]
        })
    
    # Save
    question_set.insert()
    frappe.db.commit()
    
    frappe.logger("ai_hiring").info(
        f"Created AI Question Set: {question_set.name} with {len(result['questions'])} questions"
    )
    
    return question_set.name


def regenerate_questions(question_set_name: str) -> None:
    """
    Regenerate questions for an existing AI Question Set.
    
    Args:
        question_set_name: Name of the AI Question Set document
        
    Raises:
        Exception: If regeneration fails
    """
    
    question_set = frappe.get_doc("AI Question Set", question_set_name)
    
    # Get current settings
    job_role = question_set.job_role
    job_description = question_set.job_description
    difficulty_level = question_set.difficulty_level
    num_questions = len(question_set.questions) or 15
    
    # Generate new questions
    result = generate_questions(
        job_role=job_role,
        job_description=job_description or "",
        difficulty_level=difficulty_level,
        num_questions=num_questions
    )
    
    # Clear existing questions
    question_set.questions = []
    
    # Add new questions
    for q_data in result["questions"]:
        question_set.append("questions", {
            "topic": q_data["topic"],
            "question_text": q_data["question_text"],
            "expected_answer": q_data["expected_answer"],
            "weight": q_data["weight"]
        })
    
    # Save
    question_set.save()
    frappe.db.commit()
    
    frappe.logger("ai_hiring").info(
        f"Regenerated questions for AI Question Set: {question_set_name}"
    )


@frappe.whitelist()
def test_generate_questions(
    job_role: str = "Senior Python Developer",
    difficulty: str = "Medium"
) -> Dict[str, Any]:
    """
    Test function for question generation.
    
    Args:
        job_role: Job role to test with
        difficulty: Difficulty level
        
    Returns:
        Generated questions data
    """
    
    sample_jd = """We are looking for a Senior Python Developer with 5+ years of experience.

Required Skills:
- Python 3.x, Django/Flask
- RESTful API development
- PostgreSQL/MySQL
- Redis, Celery
- Docker, Kubernetes
- Git, CI/CD
- AWS/Azure cloud platforms

Responsibilities:
- Design and develop scalable backend services
- Write clean, maintainable code
- Mentor junior developers
- Participate in code reviews
- Optimize application performance"""
    
    result = generate_questions(
        job_role=job_role,
        job_description=sample_jd,
        difficulty_level=difficulty,
        num_questions=10
    )
    
    return {
        "status": "Success",
        "questions_generated": len(result.get("questions", [])),
        "data": result
    }
