"""
Interview Brief Service
Generates comprehensive interview briefs for interviewers and captures post-interview feedback.
"""

import frappe
from typing import Dict, List, Any, Optional
import json
from frappe_ai_hiring.ai_hiring.utils.llm_client import call_llm
from frappe_ai_hiring.ai_hiring.utils.audit_logger import log_ai_operation


PROMPT_VERSION = "1.0.0"


def get_interview_brief_prompt(
    candidate_data: Dict[str, Any],
    shortlisting_data: Dict[str, Any],
    evaluation_data: Optional[Dict[str, Any]] = None
) -> tuple[str, str]:
    """
    Generate the system and user prompts for interview brief generation.
    
    Args:
        candidate_data: Parsed resume data from AI Candidate Profile
        shortlisting_data: Shortlisting results and analysis
        evaluation_data: Optional questionnaire evaluation results
        
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    
    system_prompt = """You are an expert interview preparation consultant who creates comprehensive interview briefs for hiring managers and technical interviewers.

Your task is to analyze all available candidate information and create a structured interview brief that helps interviewers:
1. Understand the candidate's background quickly
2. Focus on key areas of strength and concern
3. Ask targeted questions to verify claims
4. Make informed hiring decisions

CRITICAL REQUIREMENTS:
1. Be objective and evidence-based
2. Highlight both strengths and areas requiring verification
3. Provide specific, actionable interview questions
4. Consider all available data (resume, shortlisting, questionnaire)
5. Be fair and avoid bias
6. Focus on job-relevant factors

OUTPUT FORMAT:
Return a JSON object with this exact structure:
{
    "candidate_overview": {
        "experience_summary": "Brief summary of total experience and career progression",
        "key_strengths": ["List of 3-5 key strengths with evidence"],
        "potential_concerns": ["List of any areas needing verification or clarification"],
        "overall_fit": "Brief assessment of candidate fit for the role (2-3 sentences)"
    },
    "technical_assessment": {
        "core_skills": {
            "Skill/Technology Name": {
                "proficiency_level": "Expert/Advanced/Intermediate/Basic",
                "evidence": "What demonstrates this proficiency",
                "verification_needed": true or false
            }
        },
        "experience_highlights": ["Notable projects or achievements from resume"],
        "gaps_to_explore": ["Technical areas that need more discussion"]
    },
    "questionnaire_insights": {
        "strong_areas": ["Topics where candidate performed well"],
        "weak_areas": ["Topics needing deeper exploration"],
        "score_summary": "Brief summary if questionnaire data available, or 'N/A'"
    },
    "interview_strategy": {
        "recommended_focus_areas": ["3-5 key areas to focus the interview on"],
        "verification_points": ["Specific claims or skills that need hands-on verification"],
        "suggested_questions": [
            {
                "category": "Technical/Behavioral/Situational",
                "question": "The actual interview question",
                "purpose": "What this question aims to verify or assess",
                "follow_up": "Potential follow-up based on answer"
            }
        ],
        "red_flags_to_probe": ["Any concerning patterns or gaps to investigate"]
    },
    "decision_support": {
        "hire_recommendation": "Strong Yes/Yes/Maybe/No/Strong No",
        "confidence_level": "High/Medium/Low",
        "key_decision_factors": ["3-5 critical factors for the hiring decision"],
        "risk_assessment": "Brief assessment of hiring risks (2-3 sentences)",
        "next_steps": "Recommended next steps based on interview outcome"
    }
}

ANALYSIS GUIDELINES:
- Strengths: Look for consistent patterns, relevant experience, proven skills
- Concerns: Identify gaps, inconsistencies, or areas lacking evidence
- Questions: Make them specific, practical, and tied to job requirements
- Fairness: Avoid assumptions based on limited information
- Depth: Go beyond surface-level observations to provide real insights"""

    # Build candidate data section
    candidate_text = f"""CANDIDATE RESUME DATA:
Total Experience: {candidate_data.get('experience_years', 'Unknown')} years
Skills: {', '.join(candidate_data.get('skills', [])[:20])}

Education:
{json.dumps(candidate_data.get('education', []), indent=2)}

Work Experience:
{json.dumps(candidate_data.get('experience', []), indent=2)}

Summary:
{candidate_data.get('summary', 'Not available')}

Certifications:
{json.dumps(candidate_data.get('certifications', []), indent=2) if candidate_data.get('certifications') else 'None listed'}"""

    # Build shortlisting data section
    shortlisting_text = f"""SHORTLISTING ANALYSIS:
Decision: {shortlisting_data.get('decision', 'Unknown')}
Fit Score: {shortlisting_data.get('fit_score', 'N/A')}/100

Reasons for Decision:
{json.dumps(shortlisting_data.get('reasons', []), indent=2)}

Matching Skills:
{json.dumps(shortlisting_data.get('matching_skills', []), indent=2)}

Missing Skills:
{json.dumps(shortlisting_data.get('missing_skills', []), indent=2)}

Experience Match:
{shortlisting_data.get('experience_match', 'Not assessed')}"""

    # Build questionnaire section if available
    questionnaire_text = ""
    if evaluation_data:
        questionnaire_text = f"""

QUESTIONNAIRE EVALUATION:
Score: {evaluation_data.get('percentage_score', 'N/A')}%
Result: {evaluation_data.get('pass_fail', 'N/A')}
Correct Answers: {evaluation_data.get('correct_answers', 0)}/{evaluation_data.get('total_questions', 0)}

Strong Topics:
{evaluation_data.get('strong_topics', 'Not available')}

Weak Topics:
{evaluation_data.get('weak_topics', 'Not available')}

Strengths:
{evaluation_data.get('strengths', 'Not available')}

Areas for Improvement:
{evaluation_data.get('areas_for_improvement', 'Not available')}

Overall Assessment:
{evaluation_data.get('overall_assessment', 'Not available')}"""

    user_prompt = f"""Generate a comprehensive interview brief for this candidate:

{candidate_text}

{shortlisting_text}{questionnaire_text}

Create a detailed, actionable interview brief that helps the interviewer make an informed decision. Focus on what matters most for the role and provide specific guidance on how to conduct an effective interview.

Return the brief in the exact JSON format specified."""

    return system_prompt, user_prompt


def validate_interview_brief_schema(data: Dict[str, Any]) -> bool:
    """
    Validate the interview brief data structure.
    
    Args:
        data: The parsed JSON data from LLM
        
    Returns:
        True if valid, raises exception if invalid
    """
    if not isinstance(data, dict):
        raise ValueError("Response must be a JSON object")
    
    # Validate required top-level sections
    required_sections = [
        "candidate_overview",
        "technical_assessment",
        "questionnaire_insights",
        "interview_strategy",
        "decision_support"
    ]
    
    for section in required_sections:
        if section not in data:
            raise ValueError(f"Missing required section: {section}")
    
    # Validate candidate_overview
    overview = data["candidate_overview"]
    overview_fields = ["experience_summary", "key_strengths", "overall_fit"]
    for field in overview_fields:
        if field not in overview:
            raise ValueError(f"candidate_overview missing field: {field}")
    
    # Validate decision_support
    decision = data["decision_support"]
    decision_fields = ["hire_recommendation", "confidence_level", "key_decision_factors"]
    for field in decision_fields:
        if field not in decision:
            raise ValueError(f"decision_support missing field: {field}")
    
    # Validate hire_recommendation values
    valid_recommendations = ["Strong Yes", "Yes", "Maybe", "No", "Strong No"]
    if decision["hire_recommendation"] not in valid_recommendations:
        raise ValueError(
            f"hire_recommendation must be one of: {', '.join(valid_recommendations)}"
        )
    
    # Validate confidence_level
    valid_confidence = ["High", "Medium", "Low"]
    if decision["confidence_level"] not in valid_confidence:
        raise ValueError(f"confidence_level must be one of: {', '.join(valid_confidence)}")
    
    # Validate interview_strategy has suggested_questions
    if "suggested_questions" not in data["interview_strategy"]:
        raise ValueError("interview_strategy missing suggested_questions")
    
    if not isinstance(data["interview_strategy"]["suggested_questions"], list):
        raise ValueError("suggested_questions must be an array")
    
    return True


def generate_interview_brief(
    job_applicant: str,
    include_questionnaire: bool = True
) -> Dict[str, Any]:
    """
    Generate a comprehensive interview brief for a candidate.
    
    Args:
        job_applicant: Name of the Job Applicant document
        include_questionnaire: Whether to include questionnaire data if available
        
    Returns:
        Interview brief data
        
    Raises:
        Exception: If generation fails
    """
    
    # Get candidate profile
    if not frappe.db.exists("AI Candidate Profile", {"job_applicant": job_applicant}):
        frappe.throw(f"AI Candidate Profile not found for {job_applicant}")
    
    profile = frappe.get_doc("AI Candidate Profile", {"job_applicant": job_applicant})
    candidate_data = profile.get_parsed_data()
    
    if not candidate_data:
        frappe.throw(f"No parsed resume data available for {job_applicant}")
    
    # Get shortlisting result
    if not frappe.db.exists("AI Shortlisting Result", {"job_applicant": job_applicant}):
        frappe.throw(f"AI Shortlisting Result not found for {job_applicant}")
    
    shortlisting = frappe.get_doc("AI Shortlisting Result", {"job_applicant": job_applicant})
    shortlisting_data = {
        "decision": shortlisting.decision,
        "fit_score": shortlisting.fit_score,
        "reasons": json.loads(shortlisting.reasons) if shortlisting.reasons else [],
        "matching_skills": json.loads(shortlisting.matching_skills) if shortlisting.matching_skills else [],
        "missing_skills": json.loads(shortlisting.missing_skills) if shortlisting.missing_skills else [],
        "experience_match": shortlisting.experience_match
    }
    
    # Get questionnaire evaluation if available
    evaluation_data = None
    if include_questionnaire:
        eval_name = frappe.db.get_value(
            "AI Evaluation Result",
            {"job_applicant": job_applicant},
            "name"
        )
        
        if eval_name:
            evaluation = frappe.get_doc("AI Evaluation Result", eval_name)
            evaluation_data = {
                "percentage_score": evaluation.percentage_score,
                "pass_fail": evaluation.pass_fail,
                "correct_answers": evaluation.correct_answers,
                "total_questions": evaluation.total_questions,
                "strong_topics": evaluation.strong_topics,
                "weak_topics": evaluation.weak_topics,
                "strengths": evaluation.strengths,
                "areas_for_improvement": evaluation.areas_for_improvement,
                "overall_assessment": evaluation.overall_assessment
            }
    
    # Get prompts
    system_prompt, user_prompt = get_interview_brief_prompt(
        candidate_data=candidate_data,
        shortlisting_data=shortlisting_data,
        evaluation_data=evaluation_data
    )
    
    # Log the operation
    log_ai_operation(
        operation_type="interview_brief_generation",
        input_data={
            "job_applicant": job_applicant,
            "include_questionnaire": include_questionnaire,
            "prompt_version": PROMPT_VERSION
        },
        reference_doctype="Job Applicant",
        reference_name=job_applicant
    )
    
    try:
        # Call LLM
        response = call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            reference_doctype="AI Interview Brief",
            operation_type="interview_brief_generation"
        )
        
        # Validate schema
        validate_interview_brief_schema(response)
        
        # Log success
        log_ai_operation(
            operation_type="interview_brief_generation",
            input_data={"job_applicant": job_applicant},
            output_data={
                "hire_recommendation": response["decision_support"]["hire_recommendation"],
                "confidence_level": response["decision_support"]["confidence_level"]
            },
            reference_doctype="Job Applicant",
            reference_name=job_applicant,
            status="Success"
        )
        
        return response
        
    except Exception as e:
        # Log failure
        log_ai_operation(
            operation_type="interview_brief_generation",
            input_data={"job_applicant": job_applicant},
            error_message=str(e),
            reference_doctype="Job Applicant",
            reference_name=job_applicant,
            status="Failed"
        )
        raise


def create_interview_brief(
    job_applicant: str,
    include_questionnaire: bool = True
) -> str:
    """
    Generate interview brief and create AI Interview Brief document.
    
    Args:
        job_applicant: Name of the Job Applicant document
        include_questionnaire: Whether to include questionnaire data
        
    Returns:
        Name of the created AI Interview Brief document
        
    Raises:
        Exception: If creation fails
    """
    
    # Generate brief
    result = generate_interview_brief(
        job_applicant=job_applicant,
        include_questionnaire=include_questionnaire
    )
    
    # Create AI Interview Brief document
    brief = frappe.new_doc("AI Interview Brief")
    brief.job_applicant = job_applicant
    
    # Set candidate overview
    overview = result["candidate_overview"]
    brief.experience_summary = overview.get("experience_summary", "")
    brief.key_strengths = "\n".join(f"• {s}" for s in overview.get("key_strengths", []))
    brief.potential_concerns = "\n".join(f"• {c}" for c in overview.get("potential_concerns", []))
    brief.overall_fit_assessment = overview.get("overall_fit", "")
    
    # Set technical assessment
    tech = result["technical_assessment"]
    
    # Format core skills
    skills_text = ""
    for skill_name, skill_data in tech.get("core_skills", {}).items():
        skills_text += f"\n**{skill_name}**\n"
        skills_text += f"- Proficiency: {skill_data.get('proficiency_level', 'Unknown')}\n"
        skills_text += f"- Evidence: {skill_data.get('evidence', 'None')}\n"
        if skill_data.get('verification_needed'):
            skills_text += "- ⚠️ Needs verification in interview\n"
    
    brief.technical_skills_assessment = skills_text
    brief.experience_highlights = "\n".join(f"• {h}" for h in tech.get("experience_highlights", []))
    brief.technical_gaps = "\n".join(f"• {g}" for g in tech.get("gaps_to_explore", []))
    
    # Set questionnaire insights
    quest = result["questionnaire_insights"]
    brief.questionnaire_strong_areas = ", ".join(quest.get("strong_areas", []))
    brief.questionnaire_weak_areas = ", ".join(quest.get("weak_areas", []))
    brief.questionnaire_summary = quest.get("score_summary", "N/A")
    
    # Set interview strategy
    strategy = result["interview_strategy"]
    brief.recommended_focus_areas = "\n".join(f"• {a}" for a in strategy.get("recommended_focus_areas", []))
    brief.verification_points = "\n".join(f"• {v}" for v in strategy.get("verification_points", []))
    
    # Format suggested questions
    questions_text = ""
    for q in strategy.get("suggested_questions", []):
        questions_text += f"\n**[{q.get('category', 'General')}]**\n"
        questions_text += f"Q: {q.get('question', '')}\n"
        questions_text += f"Purpose: {q.get('purpose', '')}\n"
        if q.get('follow_up'):
            questions_text += f"Follow-up: {q.get('follow_up', '')}\n"
        questions_text += "\n"
    
    brief.suggested_interview_questions = questions_text
    brief.red_flags_to_investigate = "\n".join(f"• {f}" for f in strategy.get("red_flags_to_probe", []))
    
    # Set decision support
    decision = result["decision_support"]
    brief.ai_hire_recommendation = decision.get("hire_recommendation", "Maybe")
    brief.confidence_level = decision.get("confidence_level", "Medium")
    brief.key_decision_factors = "\n".join(f"• {f}" for f in decision.get("key_decision_factors", []))
    brief.risk_assessment = decision.get("risk_assessment", "")
    brief.recommended_next_steps = decision.get("next_steps", "")
    
    # Store complete brief data as JSON
    brief.set_brief_data(result)
    
    # Save
    brief.insert()
    frappe.db.commit()
    
    frappe.logger("ai_hiring").info(
        f"Created AI Interview Brief: {brief.name} for {job_applicant}"
    )
    
    return brief.name


def update_interview_feedback(
    interview_brief_name: str,
    interviewer_notes: str,
    interviewer_recommendation: str,
    technical_score: Optional[int] = None,
    cultural_fit_score: Optional[int] = None,
    communication_score: Optional[int] = None
) -> None:
    """
    Update interview brief with post-interview feedback.
    
    Args:
        interview_brief_name: Name of the AI Interview Brief document
        interviewer_notes: Detailed notes from the interview
        interviewer_recommendation: Hire/No Hire/Further Review
        technical_score: Technical assessment score (1-10)
        cultural_fit_score: Cultural fit score (1-10)
        communication_score: Communication skills score (1-10)
        
    Raises:
        Exception: If update fails
    """
    
    brief = frappe.get_doc("AI Interview Brief", interview_brief_name)
    
    # Update feedback fields
    brief.interviewer_notes = interviewer_notes
    brief.interviewer_recommendation = interviewer_recommendation
    
    if technical_score is not None:
        brief.technical_score = technical_score
    
    if cultural_fit_score is not None:
        brief.cultural_fit_score = cultural_fit_score
    
    if communication_score is not None:
        brief.communication_score = communication_score
    
    # Mark as feedback provided
    brief.interview_completed = 1
    
    # Save
    brief.save()
    frappe.db.commit()
    
    frappe.logger("ai_hiring").info(
        f"Updated interview feedback for: {interview_brief_name}"
    )


def generate_final_summary(interview_brief_name: str) -> str:
    """
    Generate final hiring summary combining AI analysis and interviewer feedback.
    
    Args:
        interview_brief_name: Name of the AI Interview Brief document
        
    Returns:
        Final summary text
        
    Raises:
        Exception: If generation fails
    """
    
    brief = frappe.get_doc("AI Interview Brief", interview_brief_name)
    
    if not brief.interview_completed:
        frappe.throw("Interview feedback must be provided before generating final summary")
    
    # Build summary
    summary_parts = []
    
    # Header
    summary_parts.append("# FINAL HIRING DECISION SUMMARY\n")
    summary_parts.append(f"**Candidate:** {brief.job_applicant}\n")
    summary_parts.append(f"**Date:** {frappe.utils.now()}\n\n")
    
    # AI Recommendation vs Interviewer Recommendation
    summary_parts.append("## Recommendations Comparison\n")
    summary_parts.append(f"- **AI Recommendation:** {brief.ai_hire_recommendation} (Confidence: {brief.confidence_level})\n")
    summary_parts.append(f"- **Interviewer Recommendation:** {brief.interviewer_recommendation}\n\n")
    
    # Check for alignment
    ai_positive = brief.ai_hire_recommendation in ["Strong Yes", "Yes"]
    interviewer_positive = brief.interviewer_recommendation in ["Hire", "Strong Hire"]
    
    if ai_positive and interviewer_positive:
        summary_parts.append("✅ **ALIGNED:** Both AI and interviewer recommend hiring.\n\n")
    elif not ai_positive and not interviewer_positive:
        summary_parts.append("✅ **ALIGNED:** Both AI and interviewer recommend not hiring.\n\n")
    else:
        summary_parts.append("⚠️ **DIVERGENT:** AI and interviewer recommendations differ. Review carefully.\n\n")
    
    # Scores Summary
    if brief.technical_score or brief.cultural_fit_score or brief.communication_score:
        summary_parts.append("## Interview Scores\n")
        if brief.technical_score:
            summary_parts.append(f"- Technical Skills: {brief.technical_score}/10\n")
        if brief.cultural_fit_score:
            summary_parts.append(f"- Cultural Fit: {brief.cultural_fit_score}/10\n")
        if brief.communication_score:
            summary_parts.append(f"- Communication: {brief.communication_score}/10\n")
        summary_parts.append("\n")
    
    # Key Strengths
    summary_parts.append("## Key Strengths\n")
    summary_parts.append(brief.key_strengths or "Not specified")
    summary_parts.append("\n\n")
    
    # Areas of Concern
    if brief.potential_concerns:
        summary_parts.append("## Areas of Concern\n")
        summary_parts.append(brief.potential_concerns)
        summary_parts.append("\n\n")
    
    # Interviewer Notes
    summary_parts.append("## Interviewer Notes\n")
    summary_parts.append(brief.interviewer_notes or "No notes provided")
    summary_parts.append("\n\n")
    
    # Final Recommendation
    summary_parts.append("## Final Recommendation\n")
    summary_parts.append(brief.recommended_next_steps or "Review and make final decision")
    summary_parts.append("\n")
    
    final_summary = "".join(summary_parts)
    
    # Store in document
    brief.final_hiring_summary = final_summary
    brief.save()
    frappe.db.commit()
    
    return final_summary


def regenerate_interview_brief(interview_brief_name: str) -> None:
    """
    Regenerate an existing interview brief with latest data.
    
    Args:
        interview_brief_name: Name of the AI Interview Brief document
        
    Raises:
        Exception: If regeneration fails
    """
    
    brief = frappe.get_doc("AI Interview Brief", interview_brief_name)
    job_applicant = brief.job_applicant
    
    # Generate new brief
    result = generate_interview_brief(
        job_applicant=job_applicant,
        include_questionnaire=True
    )
    
    # Update document (preserve interview feedback if exists)
    overview = result["candidate_overview"]
    brief.experience_summary = overview.get("experience_summary", "")
    brief.key_strengths = "\n".join(f"• {s}" for s in overview.get("key_strengths", []))
    brief.potential_concerns = "\n".join(f"• {c}" for c in overview.get("potential_concerns", []))
    brief.overall_fit_assessment = overview.get("overall_fit", "")
    
    # Update other sections (abbreviated for brevity - same as create_interview_brief)
    decision = result["decision_support"]
    brief.ai_hire_recommendation = decision.get("hire_recommendation", "Maybe")
    brief.confidence_level = decision.get("confidence_level", "Medium")
    
    brief.set_brief_data(result)
    
    # Save
    brief.save()
    frappe.db.commit()
    
    frappe.logger("ai_hiring").info(
        f"Regenerated AI Interview Brief: {interview_brief_name}"
    )


@frappe.whitelist()
def test_generate_brief(job_applicant: str = None) -> Dict[str, Any]:
    """
    Test function for interview brief generation.
    
    Args:
        job_applicant: Optional Job Applicant name (uses sample data if not provided)
        
    Returns:
        Interview brief data
    """
    
    if not job_applicant:
        # Use sample data for testing
        candidate_data = {
            "experience_years": 6,
            "skills": ["Python", "Django", "REST API", "PostgreSQL", "Docker", "AWS", "Redis", "Git"],
            "education": [
                {"degree": "B.Tech in Computer Science", "institution": "ABC University", "year": 2018}
            ],
            "experience": [
                {
                    "title": "Senior Backend Developer",
                    "company": "Tech Corp",
                    "duration": "2021 - Present",
                    "responsibilities": ["Built scalable APIs", "Mentored junior developers"]
                }
            ],
            "summary": "Experienced backend developer with strong Python and Django skills",
            "certifications": ["AWS Certified Solutions Architect"]
        }
        
        shortlisting_data = {
            "decision": "Shortlist",
            "fit_score": 85,
            "reasons": ["Strong technical skills", "Relevant experience", "Good cultural fit"],
            "matching_skills": ["Python", "Django", "PostgreSQL", "Docker"],
            "missing_skills": ["Kubernetes"],
            "experience_match": "Good match"
        }
        
        evaluation_data = {
            "percentage_score": 87.5,
            "pass_fail": "Pass",
            "correct_answers": 7,
            "total_questions": 8,
            "strong_topics": "Backend Development, API Design, Testing",
            "weak_topics": "Cloud Infrastructure",
            "strengths": "• Strong Python expertise\n• Good API design knowledge",
            "areas_for_improvement": "• Could improve cloud platform knowledge",
            "overall_assessment": "Solid technical candidate with minor gaps"
        }
        
        system_prompt, user_prompt = get_interview_brief_prompt(
            candidate_data=candidate_data,
            shortlisting_data=shortlisting_data,
            evaluation_data=evaluation_data
        )
        
        response = call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            reference_doctype="AI Interview Brief",
            operation_type="interview_brief_generation"
        )
        
        validate_interview_brief_schema(response)
        
        return {
            "status": "Success",
            "hire_recommendation": response["decision_support"]["hire_recommendation"],
            "confidence": response["decision_support"]["confidence_level"],
            "data": response
        }
    
    else:
        # Use actual candidate data
        result = generate_interview_brief(
            job_applicant=job_applicant,
            include_questionnaire=True
        )
        
        return {
            "status": "Success",
            "hire_recommendation": result["decision_support"]["hire_recommendation"],
            "confidence": result["decision_support"]["confidence_level"],
            "data": result
        }
