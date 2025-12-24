"""Question Generation Service for AI Hiring"""

import frappe
from typing import Dict, List, Any, Optional
import json
from frappe_ai_hiring.ai_hiring.utils.llm_client import call_llm
from frappe_ai_hiring.ai_hiring.utils.audit_logger import AIAuditLogger

PROMPT_VERSION = "2.0.0"


def get_candidate_context(applicant_name: str) -> Optional[Dict[str, Any]]:
	"""Extract and format candidate's resume data for LLM prompt inclusion."""
	try:
		from frappe_ai_hiring.ai_hiring.doctype.ai_candidate_profile.ai_candidate_profile import get_candidate_profile
		
		profile_data = get_candidate_profile(applicant_name)
		if not profile_data:
			frappe.logger("ai_hiring").warn(f"No AI Candidate Profile for {applicant_name}")
			return None
		
		profile_doc = frappe.get_doc("AI Candidate Profile", profile_data['name'])
		parsed_data = profile_doc.get_parsed_data()
		
		if not parsed_data:
			frappe.logger("ai_hiring").warn(f"No parsed data in profile {profile_data['name']}")
			return None
		
		context = {
			"experience_years": profile_doc.total_experience_years or 0,
			"skills": profile_doc.get_skills(),
			"summary": parsed_data.get("summary", ""),
			"education_relevance": profile_doc.education_relevance or "Not Specified",
			"confidence": profile_doc.ai_confidence_score or 0.0,
			"education": parsed_data.get("education", []),
			"experience": parsed_data.get("experience", []),
			"projects": _format_projects_from_table(profile_doc.projects),
		}
		
		return context
		
	except frappe.DoesNotExistError:
		frappe.logger("ai_hiring").warn(f"Job Applicant not found: {applicant_name}")
		return None
	except json.JSONDecodeError as e:
		frappe.logger("ai_hiring").error(f"Invalid JSON in candidate profile {applicant_name}: {str(e)}")
		return None
	except Exception as e:
		frappe.logger("ai_hiring").error(f"Error extracting candidate context for {applicant_name}: {str(e)}")
		return None


def _format_projects_from_table(projects_table) -> list:
	"""Convert projects child table to list of dicts."""
	if not projects_table:
		return []
	
	formatted_projects = []
	for project in projects_table:
		skills = []
		if project.skills:
			skills = [s.strip() for s in project.skills.split(",")]
		
		formatted_projects.append({
			"title": project.title or "",
			"contribution": project.candidate_contribution or "",
			"skills": skills,
		})
	
	return formatted_projects


def _format_candidate_context_for_prompt(candidate_context: Dict[str, Any], num_questions: int) -> str:
	"""Format candidate context data for inclusion in user prompt."""
	
	total = num_questions
	generic_count = max(2, int(total * 0.40))
	depth_count = max(2, int(total * 0.35))
	gap_count = max(1, int(total * 0.15))
	verify_count = total - generic_count - depth_count - gap_count
	
	experience_str = ""
	if candidate_context.get("experience"):
		experience_str = "\nRECENT EXPERIENCE:\n"
		for i, exp in enumerate(candidate_context["experience"][:3], 1):
			experience_str += f"{i}. {exp.get('title', 'N/A')} @ {exp.get('company', 'N/A')}\n"
	
	projects_str = ""
	if candidate_context.get("projects"):
		projects_str = "\nNOTABLE PROJECTS:\n"
		for i, proj in enumerate(candidate_context["projects"], 1):
			tech_stack = ", ".join(proj.get("skills", []))
			projects_str += f"{i}. {proj.get('title', 'N/A')} - Tech: {tech_stack}\n"
	
	context_section = f"""
CANDIDATE BACKGROUND:
- Years of Experience: {candidate_context.get('experience_years', 0)}
- Skills: {', '.join(candidate_context.get('skills', []))}
- Education Relevance: {candidate_context.get('education_relevance', 'Unknown')}{experience_str}{projects_str}

QUESTION DISTRIBUTION FOR THIS CANDIDATE:
- Generic (Job-Fit): ~{generic_count} questions
- Depth Assessment (Verify claimed skills): ~{depth_count} questions
- Gap Analysis (Missing skills from JD): ~{gap_count} questions
- Verification (Project/experience claims): ~{verify_count} questions

Total: {num_questions} personalized screening questions
"""
	
	return context_section


def get_question_generation_prompt(
    job_role: str,
    job_description: str,
    difficulty_level: str,
    num_questions: int = 15,
	topics: Optional[List[str]] = None,
	candidate_context: Optional[Dict[str, Any]] = None
) -> tuple[str, str]:
	"""Generate system and user prompts for question generation."""
	
	system_prompt = """You are an expert technical recruiter who creates effective screening questions.

Your task is to generate binary (Yes/No) technical screening questions to assess candidate qualifications.

CRITICAL REQUIREMENTS:
1. Each question must be answerable with a simple Yes or No
2. Questions should be direct and unambiguous
3. Focus on practical skills, experience, and knowledge
4. Questions should be fair and non-discriminatory
5. Cover a range of topics relevant to the role

QUESTION TYPES TO INCLUDE:
- Technology/tool experience
- Skill proficiency
- Project experience
- Problem-solving
- Best practices
- Domain knowledge
"""

	if candidate_context:
		system_prompt += """
CANDIDATE-SPECIFIC QUESTION APPROACH:
Generate questions in these 4 categories:

1. GENERIC (~40%): Questions on core job description requirements
2. DEPTH ASSESSMENT (~35%): Questions on technologies they explicitly list
3. GAP ANALYSIS (~15%): Questions on important skills required but not in resume
4. VERIFICATION (~10%): Questions about their specific projects or achievements

Each question must include type, category, and rationale fields.
"""

	system_prompt += """
OUTPUT FORMAT: Return JSON with questions array and metadata.
Each question must have: topic, question_text, expected_answer (Yes/No), weight (1-10)"""
	
	if candidate_context:
		system_prompt += ", type, category, rationale"
	
	system_prompt += """

DIFFICULTY GUIDELINES:
- Easy: Entry-level questions, basic concepts
- Medium: Intermediate experience, practical application
- Hard: Advanced concepts, architectural decisions"""

	topics_instruction = ""
	if topics:
		topics_instruction = f"\n\nFOCUS ON THESE TOPICS: {', '.join(topics)}"
	
	user_prompt = f"""Generate {num_questions} binary (Yes/No) screening questions for:

JOB ROLE: {job_role}

JOB DESCRIPTION:
{job_description}{topics_instruction}
"""
	
	if candidate_context:
		user_prompt += _format_candidate_context_for_prompt(candidate_context, num_questions)
	
	user_prompt += f"""
GENERATION GUIDELINES:
Generate questions that are:
1. Directly relevant to job requirements
2. Answerable with Yes or No
3. Fair and unbiased
4. Varied across different topics
5. Appropriate for {difficulty_level} difficulty level
"""
	
	if candidate_context:
		user_prompt += """
PERSONALIZATION NOTES:
- Create depth assessment questions on their listed technologies
- Include verification questions about their specific projects
- Create gap analysis questions for important missing skills
- Distribute across all 4 types

Make questions specific and meaningful."""
	
	user_prompt += "\n\nReturn valid JSON format."
	
	return (system_prompt, user_prompt)


def validate_questions_schema(data: Dict[str, Any], has_candidate_data: bool = False) -> bool:
	"""Validate the generated questions data structure."""
	
	if not isinstance(data, dict):
		raise ValueError("Response must be a JSON object")
	
	if "questions" not in data:
		raise ValueError("Missing 'questions' field")
	
	if not isinstance(data["questions"], list) or len(data["questions"]) == 0:
		raise ValueError("'questions' must be a non-empty array")
	
	required_fields = ["topic", "question_text", "expected_answer", "weight"]
	valid_answers = ["Yes", "No"]
	valid_types = ["generic", "depth", "gap", "verification"]
	valid_categories = ["Job Description", "Claimed Skills", "Missing Skills", "Project Experience"]
	
	for idx, question in enumerate(data["questions"]):
		if not isinstance(question, dict):
			raise ValueError(f"Question {idx + 1} must be an object")
		
		for field in required_fields:
			if field not in question:
				raise ValueError(f"Question {idx + 1} missing '{field}'")
		
		if question["expected_answer"] not in valid_answers:
			raise ValueError(f"Question {idx + 1} has invalid expected_answer")
		
		weight = question["weight"]
		if not isinstance(weight, (int, float)) or weight < 1 or weight > 10:
			raise ValueError(f"Question {idx + 1} weight must be 1-10")
		
		if not question["question_text"].strip():
			raise ValueError(f"Question {idx + 1} has empty question_text")
		
		if has_candidate_data:
			for field in ["type", "category", "rationale"]:
				if field not in question:
					raise ValueError(f"Question {idx + 1} missing '{field}'")
			
			if question["type"] not in valid_types:
				raise ValueError(f"Question {idx + 1} has invalid type")
			
			if question["category"] not in valid_categories:
				raise ValueError(f"Question {idx + 1} has invalid category")
			
			if not str(question.get("rationale", "")).strip():
				raise ValueError(f"Question {idx + 1} has empty rationale")
	
	return True


def generate_questions(
    job_role: str,
    job_description: str,
    difficulty_level: str = "Medium",
    num_questions: int = 15,
	topics: Optional[List[str]] = None,
	applicant_name: Optional[str] = None
) -> Dict[str, Any]:
	"""Generate screening questions, optionally personalized based on candidate resume."""
	
	if not job_role or not job_role.strip():
		raise ValueError("Job role is required")
	
	if not job_description or not job_description.strip():
		raise ValueError("Job description is required")
	
	if difficulty_level not in ["Easy", "Medium", "Hard"]:
		raise ValueError("Difficulty must be Easy, Medium, or Hard")
	
	if num_questions < 5 or num_questions > 50:
		raise ValueError("Number of questions must be between 5 and 50")
	
	candidate_context = None
	
	if applicant_name:
		candidate_context = get_candidate_context(applicant_name)
		if candidate_context:
			frappe.logger("ai_hiring").info(
				f"Generating personalized questions for {applicant_name} "
				f"({candidate_context.get('experience_years')} years experience)"
			)
		else:
			frappe.logger("ai_hiring").warn(
				f"No candidate profile for {applicant_name}, generating generic questions"
			)
	
	system_prompt, user_prompt = get_question_generation_prompt(
		job_role=job_role,
		job_description=job_description,
		difficulty_level=difficulty_level,
		num_questions=num_questions,
		topics=topics,
		candidate_context=candidate_context
	)
	
	try:
		response = call_llm(
			system_prompt=system_prompt,
			user_prompt=user_prompt,
			reference_doctype="AI Question Set",
			operation_type="Question Generation"
		)
		
		validate_questions_schema(response, has_candidate_data=bool(candidate_context))
		
		AIAuditLogger.log_llm_call(
			operation="Question Generation",
			prompt="[Redacted]",
			response=f"Generated {len(response.get('questions', []))} questions",
			model="",
			metadata={
				"job_role": job_role,
				"count": len(response.get("questions", [])),
				"personalized": bool(candidate_context),
			},
			success=True,
		)
		
		return response
		
	except Exception as e:
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


def create_question_set(
    job_role: str,
    job_description: str,
    difficulty_level: str = "Medium",
    num_questions: int = 15,
    topics: Optional[List[str]] = None,
    passing_score: float = 70.0,
	applicant_name: Optional[str] = None
) -> str:
	"""Generate questions and create an AI Question Set document."""
	
	result = generate_questions(
		job_role=job_role,
		job_description=job_description,
		difficulty_level=difficulty_level,
		num_questions=num_questions,
		topics=topics,
		applicant_name=applicant_name
	)
	
	question_set = frappe.new_doc("AI Question Set")
	question_set.job_role = job_role
	question_set.difficulty = difficulty_level
	question_set.passing_score = passing_score
	question_set.job_description = job_description
	question_set.total_questions = len(result["questions"])
	question_set.prompt_version = PROMPT_VERSION
	if applicant_name:
		question_set.based_on_applicant = applicant_name
		question_set.include_resume_based_questions = 1
	
	for q_data in result["questions"]:
		question_set.append("questions", {
			"topic": q_data["topic"],
			"question_text": q_data["question_text"],
			"expected_answer": q_data["expected_answer"],
			"weight": q_data["weight"],
			"type": q_data.get("type", ""),
			"category": q_data.get("category", "")
		})
	
	question_set.insert()
	frappe.db.commit()
	
	frappe.logger("ai_hiring").info(
		f"Created AI Question Set: {question_set.name} with {len(result['questions'])} questions"
	)
	
	return question_set.name


def regenerate_questions(question_set_name: str) -> None:
	"""Regenerate questions for an existing AI Question Set."""
	
	question_set = frappe.get_doc("AI Question Set", question_set_name)
	
	job_role = question_set.job_role
	job_description = question_set.job_description
	difficulty_level = question_set.difficulty
	num_questions = len(question_set.questions) or 15
	applicant_name = question_set.get("based_on_applicant")
	
	result = generate_questions(
		job_role=job_role,
		job_description=job_description or "",
		difficulty_level=difficulty_level,
		num_questions=num_questions,
		applicant_name=applicant_name
	)
	
	question_set.questions = []
	
	for q_data in result["questions"]:
		question_set.append("questions", {
			"topic": q_data["topic"],
			"question_text": q_data["question_text"],
			"expected_answer": q_data["expected_answer"],
			"weight": q_data["weight"],
			"type": q_data.get("type", ""),
			"category": q_data.get("category", "")
		})
	
	question_set.save()
	frappe.db.commit()
	
	frappe.logger("ai_hiring").info(f"Regenerated questions for {question_set_name}")


@frappe.whitelist()
def test_generate_questions(
    job_role: str = "Senior Python Developer",
    difficulty: str = "Medium"
) -> Dict[str, Any]:
	"""Test function for question generation."""
	
	sample_jd = """We are looking for a Senior Python Developer with 5+ years of experience.
Required Skills:
- Python 3.x, Django/Flask
- RESTful API development
- PostgreSQL/MySQL
- Redis, Celery
- Docker, Kubernetes
- Git, CI/CD
- AWS/Azure cloud platforms"""
	
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
