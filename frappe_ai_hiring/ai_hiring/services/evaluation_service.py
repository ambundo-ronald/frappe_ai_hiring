"""
Evaluation Service
Evaluates candidate answers to screening questions using AI.
"""

import frappe
from typing import Dict, List, Any, Optional
import json
from frappe_ai_hiring.ai_hiring.utils.llm_client import call_llm
from frappe_ai_hiring.ai_hiring.utils.audit_logger import AIAuditLogger


PROMPT_VERSION = "1.0.0"


def get_evaluation_prompt(
    questions_and_answers: List[Dict[str, Any]],
    candidate_context: Optional[Dict[str, Any]] = None
) -> tuple[str, str]:
    """
    Generate the system and user prompts for answer evaluation.
    
    Args:
        questions_and_answers: List of dicts with question_text, candidate_answer, expected_answer, weight
        candidate_context: Optional context about the candidate (resume summary, experience)
        
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    
    system_prompt = """You are an expert technical evaluator who assesses candidate responses to screening questions.

Your task is to evaluate a candidate's Yes/No answers to technical screening questions and provide:
1. Whether each answer matches the expected answer
2. Overall scoring and assessment
3. Analysis of strengths and weaknesses

EVALUATION CRITERIA:
- Direct match: Does the candidate's answer match the expected answer?
- Context consideration: Consider the weight/importance of each question
- Leniency: Be fair - if a candidate shows strong skills in most areas, minor gaps are acceptable
- Pattern recognition: Identify topic areas where the candidate is strong or weak

OUTPUT FORMAT:
Return a JSON object with this exact structure:
{
    "question_results": [
        {
            "question_text": "The question text",
            "candidate_answer": "Yes" or "No",
            "expected_answer": "Yes" or "No",
            "is_correct": true or false,
            "points_earned": <calculated based on weight>,
            "points_possible": <weight value>,
            "topic": "The topic/category"
        }
    ],
    "summary": {
        "total_questions": <number>,
        "correct_answers": <number>,
        "percentage_score": <0-100>,
        "points_earned": <sum of points earned>,
        "points_possible": <sum of all weights>,
        "pass_fail": "Pass" or "Fail"
    },
    "topic_analysis": {
        "strong_topics": ["Topics where candidate scored well"],
        "weak_topics": ["Topics where candidate struggled"],
        "topic_scores": {
            "Topic Name": {
                "score": <percentage>,
                "questions_count": <number>
            }
        }
    },
    "feedback": {
        "strengths": ["List of candidate strengths based on answers"],
        "areas_for_improvement": ["Areas where candidate could improve"],
        "overall_assessment": "Brief overall assessment (2-3 sentences)",
        "recommendation": "Proceed" or "Reject" or "Further Review"
    }
}

SCORING LOGIC:
- Each question has a weight (1-10)
- If answer is correct: points_earned = weight
- If answer is incorrect: points_earned = 0
- Percentage score = (total points earned / total points possible) * 100
- Pass/Fail is determined by comparing to passing threshold (typically 70%)"""

    context_text = ""
    if candidate_context:
        context_text = f"""

CANDIDATE CONTEXT:
{json.dumps(candidate_context, indent=2)}

Consider this context when evaluating answers, but still prioritize direct question responses."""
    
    # Format questions for prompt
    qa_text = ""
    for idx, qa in enumerate(questions_and_answers, 1):
        qa_text += f"""
Question {idx}:
- Topic: {qa.get('topic', 'General')}
- Question: {qa['question_text']}
- Expected Answer: {qa['expected_answer']}
- Candidate Answer: {qa['candidate_answer']}
- Weight: {qa.get('weight', 5)}
"""
    
    user_prompt = f"""Evaluate the following candidate responses to screening questions:{context_text}

QUESTIONS AND ANSWERS:
{qa_text}

Analyze the responses and return a complete evaluation in the JSON format specified. Be thorough but fair in your assessment."""

    return system_prompt, user_prompt


def validate_evaluation_schema(data: Dict[str, Any]) -> bool:
    """
    Validate the evaluation result data structure.
    
    Args:
        data: The parsed JSON data from LLM
        
    Returns:
        True if valid, raises exception if invalid
    """
    if not isinstance(data, dict):
        raise ValueError("Response must be a JSON object")
    
    # Validate required top-level fields
    required_fields = ["question_results", "summary", "topic_analysis", "feedback"]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate summary
    summary = data["summary"]
    summary_fields = ["total_questions", "correct_answers", "percentage_score", "pass_fail"]
    for field in summary_fields:
        if field not in summary:
            raise ValueError(f"Summary missing field: {field}")
    
    # Validate pass_fail value
    if summary["pass_fail"] not in ["Pass", "Fail"]:
        raise ValueError("pass_fail must be 'Pass' or 'Fail'")
    
    # Validate percentage_score range
    score = summary["percentage_score"]
    if not isinstance(score, (int, float)) or score < 0 or score > 100:
        raise ValueError("percentage_score must be between 0 and 100")
    
    # Validate question_results is a list
    if not isinstance(data["question_results"], list):
        raise ValueError("question_results must be an array")
    
    # Validate topic_analysis
    if "strong_topics" not in data["topic_analysis"]:
        raise ValueError("topic_analysis missing strong_topics")
    
    if "weak_topics" not in data["topic_analysis"]:
        raise ValueError("topic_analysis missing weak_topics")
    
    # Validate feedback
    feedback = data["feedback"]
    feedback_fields = ["strengths", "areas_for_improvement", "overall_assessment", "recommendation"]
    for field in feedback_fields:
        if field not in feedback:
            raise ValueError(f"Feedback missing field: {field}")
    
    return True


def evaluate_questionnaire(
    job_applicant: str,
    question_set: str,
    answers: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Evaluate a candidate's answers to a questionnaire.
    
    Args:
        job_applicant: Name of the Job Applicant document
        question_set: Name of the AI Question Set document
        answers: List of dicts with question_text and candidate_answer
        
    Returns:
        Evaluation results
        
    Raises:
        Exception: If evaluation fails
    """
    
    # Get question set
    qs_doc = frappe.get_doc("AI Question Set", question_set)
    
    # Build questions_and_answers list
    questions_and_answers = []
    answer_map = {ans["question_text"]: ans["candidate_answer"] for ans in answers}
    
    for question in qs_doc.questions:
        candidate_answer = answer_map.get(question.question_text, "No")
        
        questions_and_answers.append({
            "question_text": question.question_text,
            "expected_answer": question.expected_answer,
            "candidate_answer": candidate_answer,
            "weight": question.weight or 5,
            "topic": question.topic
        })
    
    # Get candidate context if available
    candidate_context = None
    if frappe.db.exists("AI Candidate Profile", {"job_applicant": job_applicant}):
        profile = frappe.get_doc("AI Candidate Profile", {"job_applicant": job_applicant})
        parsed_data = profile.get_parsed_data()
        if parsed_data:
            candidate_context = {
                "total_experience_years": parsed_data.get("experience_years", 0),
                "key_skills": parsed_data.get("skills", [])[:10],  # Top 10 skills
                "summary": parsed_data.get("summary", "")[:500]  # First 500 chars
            }
    
    # Get prompts
    system_prompt, user_prompt = get_evaluation_prompt(
        questions_and_answers=questions_and_answers,
        candidate_context=candidate_context
    )
    
    # Log the operation (pre-call)
    AIAuditLogger.log_llm_call(
        operation="Evaluation",
        prompt=f"[Generated prompts v{PROMPT_VERSION}]",
        response="",
        model="",
        metadata={
            "doctype": "Job Applicant",
            "docname": job_applicant,
            "question_set": question_set,
            "total_questions": len(questions_and_answers),
            "prompt_version": PROMPT_VERSION,
        },
        success=True,
    )
    
    try:
        # Call LLM
        response = call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            reference_doctype="AI Evaluation Result",
            operation_type="Evaluation"
        )
        
        # Validate schema
        validate_evaluation_schema(response)
        
        # Log success
        AIAuditLogger.log_llm_call(
            operation="Evaluation",
            prompt=user_prompt,
            response=json.dumps({
                "percentage_score": response["summary"]["percentage_score"],
                "pass_fail": response["summary"]["pass_fail"],
            }),
            model="",
            metadata={"doctype": "Job Applicant", "docname": job_applicant, "question_set": question_set},
            success=True,
        )
        
        return response
        
    except Exception as e:
        # Log failure
        AIAuditLogger.log_error(
            operation="Evaluation",
            error_message=str(e),
            metadata={"doctype": "Job Applicant", "docname": job_applicant, "question_set": question_set},
        )
        raise


def create_evaluation_result(
    job_applicant: str,
    question_set: str,
    answers: List[Dict[str, str]]
) -> str:
    """
    Evaluate questionnaire and create AI Evaluation Result document.
    
    Args:
        job_applicant: Name of the Job Applicant document
        question_set: Name of the AI Question Set document
        answers: List of dicts with question_text and candidate_answer
        
    Returns:
        Name of the created AI Evaluation Result document
        
    Raises:
        Exception: If creation fails
    """
    
    # Evaluate
    result = evaluate_questionnaire(
        job_applicant=job_applicant,
        question_set=question_set,
        answers=answers
    )
    
    # Create AI Evaluation Result document
    eval_doc = frappe.new_doc("AI Evaluation Result")
    eval_doc.job_applicant = job_applicant
    eval_doc.question_set = question_set
    
    # Set summary fields
    summary = result["summary"]
    eval_doc.total_questions = summary["total_questions"]
    eval_doc.correct_answers = summary["correct_answers"]
    eval_doc.percentage_score = summary["percentage_score"]
    eval_doc.pass_fail = summary["pass_fail"]
    
    # Set topic analysis
    topic_analysis = result["topic_analysis"]
    eval_doc.strong_topics = ", ".join(topic_analysis.get("strong_topics", []))
    eval_doc.weak_topics = ", ".join(topic_analysis.get("weak_topics", []))
    
    # Set feedback
    feedback = result["feedback"]
    eval_doc.strengths = "\n".join(f"• {s}" for s in feedback.get("strengths", []))
    eval_doc.areas_for_improvement = "\n".join(f"• {a}" for a in feedback.get("areas_for_improvement", []))
    eval_doc.overall_assessment = feedback.get("overall_assessment", "")
    eval_doc.recommendation = feedback.get("recommendation", "Further Review")
    
    # Store detailed results as JSON
    eval_doc.set_results(result)
    
    # Save
    eval_doc.insert()
    frappe.db.commit()
    
    frappe.logger("ai_hiring").info(
        f"Created AI Evaluation Result: {eval_doc.name} for {job_applicant}"
    )
    
    return eval_doc.name


def reevaluate_questionnaire(evaluation_result_name: str) -> None:
    """
    Re-evaluate an existing evaluation result.
    
    Args:
        evaluation_result_name: Name of the AI Evaluation Result document
        
    Raises:
        Exception: If re-evaluation fails
    """
    
    eval_doc = frappe.get_doc("AI Evaluation Result", evaluation_result_name)
    
    # Get stored results to extract original answers
    stored_results = eval_doc.get_results()
    if not stored_results or "question_results" not in stored_results:
        frappe.throw("Cannot re-evaluate: original answers not found")
    
    # Reconstruct answers list
    answers = []
    for qr in stored_results["question_results"]:
        answers.append({
            "question_text": qr["question_text"],
            "candidate_answer": qr["candidate_answer"]
        })
    
    # Re-evaluate
    result = evaluate_questionnaire(
        job_applicant=eval_doc.job_applicant,
        question_set=eval_doc.question_set,
        answers=answers
    )
    
    # Update document with new results
    summary = result["summary"]
    eval_doc.total_questions = summary["total_questions"]
    eval_doc.correct_answers = summary["correct_answers"]
    eval_doc.percentage_score = summary["percentage_score"]
    eval_doc.pass_fail = summary["pass_fail"]
    
    topic_analysis = result["topic_analysis"]
    eval_doc.strong_topics = ", ".join(topic_analysis.get("strong_topics", []))
    eval_doc.weak_topics = ", ".join(topic_analysis.get("weak_topics", []))
    
    feedback = result["feedback"]
    eval_doc.strengths = "\n".join(f"• {s}" for s in feedback.get("strengths", []))
    eval_doc.areas_for_improvement = "\n".join(f"• {a}" for a in feedback.get("areas_for_improvement", []))
    eval_doc.overall_assessment = feedback.get("overall_assessment", "")
    eval_doc.recommendation = feedback.get("recommendation", "Further Review")
    
    eval_doc.set_results(result)
    
    # Save
    eval_doc.save()
    frappe.db.commit()
    
    frappe.logger("ai_hiring").info(
        f"Re-evaluated AI Evaluation Result: {evaluation_result_name}"
    )


@frappe.whitelist()
def test_evaluation() -> Dict[str, Any]:
    """
    Test function for questionnaire evaluation.
    
    Returns:
        Evaluation results
    """
    
    # Sample questions and answers
    questions_and_answers = [
        {
            "question_text": "Do you have at least 5 years of Python development experience?",
            "expected_answer": "Yes",
            "candidate_answer": "Yes",
            "weight": 8,
            "topic": "Experience"
        },
        {
            "question_text": "Have you worked with Django or Flask in production applications?",
            "expected_answer": "Yes",
            "candidate_answer": "Yes",
            "weight": 9,
            "topic": "Backend Frameworks"
        },
        {
            "question_text": "Can you design and implement RESTful APIs?",
            "expected_answer": "Yes",
            "candidate_answer": "Yes",
            "weight": 10,
            "topic": "API Development"
        },
        {
            "question_text": "Do you have experience with PostgreSQL or MySQL?",
            "expected_answer": "Yes",
            "candidate_answer": "No",
            "weight": 7,
            "topic": "Databases"
        },
        {
            "question_text": "Have you used Docker and Kubernetes in production?",
            "expected_answer": "Yes",
            "candidate_answer": "Yes",
            "weight": 8,
            "topic": "DevOps"
        },
        {
            "question_text": "Can you write unit tests and integration tests?",
            "expected_answer": "Yes",
            "candidate_answer": "Yes",
            "weight": 7,
            "topic": "Testing"
        },
        {
            "question_text": "Do you have experience with cloud platforms (AWS/Azure)?",
            "expected_answer": "Yes",
            "candidate_answer": "No",
            "weight": 6,
            "topic": "Cloud"
        },
        {
            "question_text": "Have you led or mentored other developers?",
            "expected_answer": "Yes",
            "candidate_answer": "Yes",
            "weight": 5,
            "topic": "Leadership"
        }
    ]
    
    candidate_context = {
        "total_experience_years": 6,
        "key_skills": ["Python", "Django", "REST API", "Docker", "Git"],
        "summary": "Experienced Python developer with strong backend skills"
    }
    
    system_prompt, user_prompt = get_evaluation_prompt(
        questions_and_answers=questions_and_answers,
        candidate_context=candidate_context
    )
    
    response = call_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        reference_doctype="AI Evaluation Result",
        operation_type="questionnaire_evaluation"
    )
    
    validate_evaluation_schema(response)
    
    return {
        "status": "Success",
        "percentage_score": response["summary"]["percentage_score"],
        "pass_fail": response["summary"]["pass_fail"],
        "data": response
    }
