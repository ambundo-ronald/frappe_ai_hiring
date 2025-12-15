"""
Workflow State Machine
Manages the state transitions and workflow logic for the AI hiring pipeline
"""

import frappe
from typing import Dict, List, Any, Optional
from enum import Enum


class PipelineStage(Enum):
	"""Enumeration of pipeline stages"""
	NOT_STARTED = "Not Started"
	RESUME_PARSING = "Resume Parsing"
	SHORTLISTING = "Shortlisting"
	QUESTIONNAIRE_PENDING = "Questionnaire Pending"
	QUESTIONNAIRE_EVALUATION = "Questionnaire Evaluation"
	INTERVIEW_BRIEF_READY = "Interview Brief Ready"
	INTERVIEW_SCHEDULED = "Interview Scheduled"
	INTERVIEW_COMPLETED = "Interview Completed"
	FINAL_REVIEW = "Final Review"
	OFFER_PENDING = "Offer Pending"
	HIRED = "Hired"
	REJECTED = "Rejected"
	ON_HOLD = "On Hold"


class WorkflowState:
	"""Manages workflow state and transitions for candidates"""
	
	# Valid state transitions
	VALID_TRANSITIONS = {
		PipelineStage.NOT_STARTED: [
			PipelineStage.RESUME_PARSING,
			PipelineStage.REJECTED
		],
		PipelineStage.RESUME_PARSING: [
			PipelineStage.SHORTLISTING,
			PipelineStage.REJECTED
		],
		PipelineStage.SHORTLISTING: [
			PipelineStage.QUESTIONNAIRE_PENDING,
			PipelineStage.INTERVIEW_BRIEF_READY,
			PipelineStage.REJECTED,
			PipelineStage.ON_HOLD
		],
		PipelineStage.QUESTIONNAIRE_PENDING: [
			PipelineStage.QUESTIONNAIRE_EVALUATION,
			PipelineStage.REJECTED,
			PipelineStage.ON_HOLD
		],
		PipelineStage.QUESTIONNAIRE_EVALUATION: [
			PipelineStage.INTERVIEW_BRIEF_READY,
			PipelineStage.REJECTED,
			PipelineStage.ON_HOLD
		],
		PipelineStage.INTERVIEW_BRIEF_READY: [
			PipelineStage.INTERVIEW_SCHEDULED,
			PipelineStage.REJECTED,
			PipelineStage.ON_HOLD
		],
		PipelineStage.INTERVIEW_SCHEDULED: [
			PipelineStage.INTERVIEW_COMPLETED,
			PipelineStage.REJECTED,
			PipelineStage.ON_HOLD
		],
		PipelineStage.INTERVIEW_COMPLETED: [
			PipelineStage.FINAL_REVIEW,
			PipelineStage.REJECTED,
			PipelineStage.ON_HOLD
		],
		PipelineStage.FINAL_REVIEW: [
			PipelineStage.OFFER_PENDING,
			PipelineStage.REJECTED
		],
		PipelineStage.OFFER_PENDING: [
			PipelineStage.HIRED,
			PipelineStage.REJECTED
		],
		PipelineStage.ON_HOLD: [
			PipelineStage.QUESTIONNAIRE_PENDING,
			PipelineStage.INTERVIEW_SCHEDULED,
			PipelineStage.REJECTED
		],
		PipelineStage.HIRED: [],
		PipelineStage.REJECTED: []
	}
	
	@staticmethod
	def get_current_stage(job_applicant: str) -> PipelineStage:
		"""
		Determine current pipeline stage for a candidate.
		
		Args:
			job_applicant: Job Applicant name
			
		Returns:
			Current PipelineStage
		"""
		
		# Check for candidate profile
		has_profile = frappe.db.exists("AI Candidate Profile", {"job_applicant": job_applicant})
		
		# Check for shortlisting result
		shortlisting = None
		if frappe.db.exists("AI Shortlisting Result", {"job_applicant": job_applicant}):
			shortlisting = frappe.get_doc("AI Shortlisting Result", {"job_applicant": job_applicant})
		
		# Check for evaluation result
		has_evaluation = frappe.db.exists("AI Evaluation Result", {"job_applicant": job_applicant})
		
		# Check for interview brief
		interview_brief = None
		if frappe.db.exists("AI Interview Brief", {"job_applicant": job_applicant}):
			interview_brief = frappe.get_doc("AI Interview Brief", {"job_applicant": job_applicant})
		
		# Get Job Applicant status
		applicant = frappe.get_doc("Job Applicant", job_applicant)
		status = applicant.status
		
		# Determine stage based on available data
		if status == "Rejected":
			return PipelineStage.REJECTED
		elif status == "Accepted" or status == "Hired":
			return PipelineStage.HIRED
		elif status == "Hold":
			return PipelineStage.ON_HOLD
		
		# Check interview completion
		if interview_brief and interview_brief.interview_completed:
			if interview_brief.interviewer_recommendation in ["Hire", "Strong Hire"]:
				return PipelineStage.FINAL_REVIEW
			else:
				return PipelineStage.INTERVIEW_COMPLETED
		
		# Check if interview brief exists
		if interview_brief:
			return PipelineStage.INTERVIEW_BRIEF_READY
		
		# Check evaluation
		if has_evaluation:
			evaluation = frappe.get_doc("AI Evaluation Result", {"job_applicant": job_applicant})
			if evaluation.pass_fail == "Pass":
				return PipelineStage.QUESTIONNAIRE_EVALUATION
			else:
				return PipelineStage.REJECTED
		
		# Check for questionnaire
		if frappe.db.exists("AI Question Set", {"job_role": applicant.job_title}):
			return PipelineStage.QUESTIONNAIRE_PENDING
		
		# Check shortlisting
		if shortlisting:
			if shortlisting.decision == "Reject":
				return PipelineStage.REJECTED
			elif shortlisting.decision == "Shortlist":
				return PipelineStage.SHORTLISTING
			else:
				return PipelineStage.SHORTLISTING
		
		# Check parsing
		if has_profile:
			return PipelineStage.RESUME_PARSING
		
		# Default
		return PipelineStage.NOT_STARTED
	
	@staticmethod
	def can_transition(current_stage: PipelineStage, target_stage: PipelineStage) -> bool:
		"""
		Check if transition from current to target stage is valid.
		
		Args:
			current_stage: Current pipeline stage
			target_stage: Desired target stage
			
		Returns:
			True if transition is valid
		"""
		
		valid_targets = WorkflowState.VALID_TRANSITIONS.get(current_stage, [])
		return target_stage in valid_targets
	
	@staticmethod
	def transition_to_stage(
		job_applicant: str,
		target_stage: PipelineStage,
		notes: Optional[str] = None,
		force: bool = False
	) -> bool:
		"""
		Transition candidate to a new stage.
		
		Args:
			job_applicant: Job Applicant name
			target_stage: Target pipeline stage
			notes: Optional transition notes
			force: Force transition even if invalid
			
		Returns:
			True if transition successful
		"""
		
		current_stage = WorkflowState.get_current_stage(job_applicant)
		
		# Check if transition is valid
		if not force and not WorkflowState.can_transition(current_stage, target_stage):
			frappe.throw(
				f"Invalid transition from {current_stage.value} to {target_stage.value}"
			)
		
		# Update Job Applicant status
		applicant = frappe.get_doc("Job Applicant", job_applicant)
		
		# Map pipeline stages to Job Applicant statuses
		stage_to_status = {
			PipelineStage.REJECTED: "Rejected",
			PipelineStage.HIRED: "Accepted",
			PipelineStage.ON_HOLD: "Hold",
			PipelineStage.INTERVIEW_SCHEDULED: "Open",
			PipelineStage.INTERVIEW_COMPLETED: "Open",
			PipelineStage.FINAL_REVIEW: "Open",
			PipelineStage.OFFER_PENDING: "Open"
		}
		
		if target_stage in stage_to_status:
			applicant.status = stage_to_status[target_stage]
		
		# Add comment with transition info
		transition_note = notes or f"Transitioned from {current_stage.value} to {target_stage.value}"
		applicant.add_comment("Comment", transition_note)
		
		applicant.save(ignore_permissions=True)
		frappe.db.commit()
		
		frappe.logger("ai_hiring").info(
			f"Transitioned {job_applicant} from {current_stage.value} to {target_stage.value}"
		)
		
		return True
	
	@staticmethod
	def get_next_stages(job_applicant: str) -> List[PipelineStage]:
		"""
		Get list of valid next stages for a candidate.
		
		Args:
			job_applicant: Job Applicant name
			
		Returns:
			List of valid next stages
		"""
		
		current_stage = WorkflowState.get_current_stage(job_applicant)
		return WorkflowState.VALID_TRANSITIONS.get(current_stage, [])
	
	@staticmethod
	def get_stage_progress(job_applicant: str) -> Dict[str, Any]:
		"""
		Get detailed progress information for a candidate.
		
		Args:
			job_applicant: Job Applicant name
			
		Returns:
			Dict with stage progress details
		"""
		
		current_stage = WorkflowState.get_current_stage(job_applicant)
		next_stages = WorkflowState.get_next_stages(job_applicant)
		
		# Calculate completion percentage
		stage_order = [
			PipelineStage.NOT_STARTED,
			PipelineStage.RESUME_PARSING,
			PipelineStage.SHORTLISTING,
			PipelineStage.QUESTIONNAIRE_PENDING,
			PipelineStage.QUESTIONNAIRE_EVALUATION,
			PipelineStage.INTERVIEW_BRIEF_READY,
			PipelineStage.INTERVIEW_SCHEDULED,
			PipelineStage.INTERVIEW_COMPLETED,
			PipelineStage.FINAL_REVIEW,
			PipelineStage.OFFER_PENDING,
			PipelineStage.HIRED
		]
		
		if current_stage == PipelineStage.REJECTED:
			completion = 0
		elif current_stage == PipelineStage.HIRED:
			completion = 100
		elif current_stage in stage_order:
			stage_index = stage_order.index(current_stage)
			completion = int((stage_index / len(stage_order)) * 100)
		else:
			completion = 0
		
		return {
			"job_applicant": job_applicant,
			"current_stage": current_stage.value,
			"next_stages": [s.value for s in next_stages],
			"completion_percentage": completion,
			"can_proceed": len(next_stages) > 0
		}


@frappe.whitelist()
def get_applicant_workflow_status(job_applicant: str) -> Dict[str, Any]:
	"""
	Get workflow status for a job applicant.
	
	Args:
		job_applicant: Job Applicant name
		
	Returns:
		Workflow status dict
	"""
	
	return WorkflowState.get_stage_progress(job_applicant)


@frappe.whitelist()
def transition_applicant_stage(
	job_applicant: str,
	target_stage: str,
	notes: Optional[str] = None
) -> Dict[str, Any]:
	"""
	Transition applicant to new stage.
	
	Args:
		job_applicant: Job Applicant name
		target_stage: Target stage name
		notes: Optional notes
		
	Returns:
		Result dict
	"""
	
	if not frappe.has_permission("Job Applicant", "write"):
		frappe.throw("Insufficient permissions")
	
	# Convert string to enum
	try:
		target_enum = PipelineStage(target_stage)
	except ValueError:
		frappe.throw(f"Invalid stage: {target_stage}")
	
	success = WorkflowState.transition_to_stage(
		job_applicant=job_applicant,
		target_stage=target_enum,
		notes=notes
	)
	
	return {
		"success": success,
		"new_status": WorkflowState.get_stage_progress(job_applicant)
	}


@frappe.whitelist()
def get_pipeline_statistics() -> Dict[str, Any]:
	"""
	Get overall pipeline statistics.
	
	Returns:
		Statistics by stage
	"""
	
	if not frappe.has_permission("Job Applicant", "read"):
		frappe.throw("Insufficient permissions")
	
	stats = {}
	
	# Get all active job applicants
	applicants = frappe.get_all(
		"Job Applicant",
		filters={"status": ["!=", "Rejected"]},
		fields=["name"]
	)
	
	# Count by stage
	for stage in PipelineStage:
		stats[stage.value] = 0
	
	for applicant in applicants:
		stage = WorkflowState.get_current_stage(applicant.name)
		stats[stage.value] = stats.get(stage.value, 0) + 1
	
	return {
		"total_active": len(applicants),
		"by_stage": stats,
		"timestamp": frappe.utils.now()
	}
