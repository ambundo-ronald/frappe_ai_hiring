"""
Dashboard Widgets
Provides data for dashboard widgets and analytics
"""

import frappe
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


class DashboardAnalytics:
	"""Analytics and dashboard data provider"""
	
	@staticmethod
	def get_pipeline_overview() -> Dict[str, Any]:
		"""
		Get high-level pipeline overview.
		
		Returns:
			Pipeline statistics
		"""
		
		# Get all active applicants
		active_applicants = frappe.db.count(
			"Job Applicant",
			filters={"status": ["not in", ["Rejected", "Accepted"]]}
		)
		
		# Get hired count (last 30 days)
		hired_count = frappe.db.count(
			"Job Applicant",
			filters={
				"status": "Accepted",
				"modified": [">=", frappe.utils.add_days(frappe.utils.nowdate(), -30)]
			}
		)
		
		# Get rejected count (last 30 days)
		rejected_count = frappe.db.count(
			"Job Applicant",
			filters={
				"status": "Rejected",
				"modified": [">=", frappe.utils.add_days(frappe.utils.nowdate(), -30)]
			}
		)
		
		# Get AI processing stats
		ai_profiles = frappe.db.count("AI Candidate Profile")
		ai_shortlisted = frappe.db.count(
			"AI Shortlisting Result",
			filters={"decision": "Shortlist"}
		)
		
		# Get pending actions
		pending_questionnaires = frappe.db.count(
			"AI Evaluation Result",
			filters={"pass_fail": ["is", "not set"]}
		)
		
		pending_interviews = frappe.db.count(
			"AI Interview Brief",
			filters={"interview_completed": 0}
		)
		
		return {
			"active_candidates": active_applicants,
			"hired_last_30_days": hired_count,
			"rejected_last_30_days": rejected_count,
			"ai_profiles_created": ai_profiles,
			"ai_shortlisted": ai_shortlisted,
			"pending_questionnaires": pending_questionnaires,
			"pending_interviews": pending_interviews,
			"timestamp": frappe.utils.now()
		}
	
	@staticmethod
	def get_ai_performance_metrics() -> Dict[str, Any]:
		"""
		Get AI system performance metrics.
		
		Returns:
			Performance statistics
		"""
		
		# Shortlisting accuracy (based on final hire decisions)
		shortlisting_results = frappe.db.sql("""
			SELECT 
				sr.decision as ai_decision,
				ja.status as final_status,
				COUNT(*) as count
			FROM `tabAI Shortlisting Result` sr
			JOIN `tabJob Applicant` ja ON sr.job_applicant = ja.name
			GROUP BY sr.decision, ja.status
		""", as_dict=True)
		
		# Calculate accuracy
		ai_shortlisted_and_hired = 0
		ai_rejected_and_rejected = 0
		total_decided = 0
		
		for result in shortlisting_results:
			if result.ai_decision == "Shortlist" and result.final_status == "Accepted":
				ai_shortlisted_and_hired += result.count
				total_decided += result.count
			elif result.ai_decision == "Reject" and result.final_status == "Rejected":
				ai_rejected_and_rejected += result.count
				total_decided += result.count
			elif result.final_status in ["Accepted", "Rejected"]:
				total_decided += result.count
		
		accuracy = (
			((ai_shortlisted_and_hired + ai_rejected_and_rejected) / total_decided * 100)
			if total_decided > 0 else 0
		)
		
		# Average processing time
		avg_processing_time = frappe.db.sql("""
			SELECT 
				AVG(TIMESTAMPDIFF(SECOND, ja.creation, acp.creation)) as avg_seconds
			FROM `tabJob Applicant` ja
			JOIN `tabAI Candidate Profile` acp ON ja.name = acp.job_applicant
			WHERE ja.creation >= DATE_SUB(NOW(), INTERVAL 30 DAY)
		""", as_dict=True)
		
		avg_time = avg_processing_time[0].avg_seconds if avg_processing_time else 0
		
		# Get average fit scores
		avg_fit_score = frappe.db.sql("""
			SELECT AVG(fit_score) as avg_score
			FROM `tabAI Shortlisting Result`
			WHERE decision = 'Shortlist'
		""", as_dict=True)
		
		return {
			"ai_accuracy_percentage": round(accuracy, 2),
			"avg_processing_time_seconds": int(avg_time) if avg_time else 0,
			"avg_fit_score": round(avg_fit_score[0].avg_score, 2) if avg_fit_score else 0,
			"total_evaluations": total_decided,
			"timestamp": frappe.utils.now()
		}
	
	@staticmethod
	def get_funnel_stats() -> List[Dict[str, Any]]:
		"""
		Get hiring funnel statistics.
		
		Returns:
			List of funnel stage stats
		"""
		
		# Get counts at each stage
		total_applications = frappe.db.count("Job Applicant")
		
		parsed = frappe.db.count("AI Candidate Profile")
		
		shortlisted = frappe.db.count(
			"AI Shortlisting Result",
			filters={"decision": "Shortlist"}
		)
		
		evaluated = frappe.db.count("AI Evaluation Result")
		
		interviewed = frappe.db.count(
			"AI Interview Brief",
			filters={"interview_completed": 1}
		)
		
		hired = frappe.db.count(
			"Job Applicant",
			filters={"status": "Accepted"}
		)
		
		funnel = [
			{
				"stage": "Applications Received",
				"count": total_applications,
				"percentage": 100
			},
			{
				"stage": "Resume Parsed",
				"count": parsed,
				"percentage": round((parsed / total_applications * 100), 2) if total_applications > 0 else 0
			},
			{
				"stage": "AI Shortlisted",
				"count": shortlisted,
				"percentage": round((shortlisted / total_applications * 100), 2) if total_applications > 0 else 0
			},
			{
				"stage": "Questionnaire Completed",
				"count": evaluated,
				"percentage": round((evaluated / total_applications * 100), 2) if total_applications > 0 else 0
			},
			{
				"stage": "Interviewed",
				"count": interviewed,
				"percentage": round((interviewed / total_applications * 100), 2) if total_applications > 0 else 0
			},
			{
				"stage": "Hired",
				"count": hired,
				"percentage": round((hired / total_applications * 100), 2) if total_applications > 0 else 0
			}
		]
		
		return funnel
	
	@staticmethod
	def get_time_to_hire_stats() -> Dict[str, Any]:
		"""
		Calculate time-to-hire statistics.
		
		Returns:
			Time-to-hire metrics
		"""
		
		# Get hired candidates in last 90 days
		hired_stats = frappe.db.sql("""
			SELECT 
				ja.name,
				ja.creation as application_date,
				ja.modified as hire_date,
				TIMESTAMPDIFF(DAY, ja.creation, ja.modified) as days_to_hire
			FROM `tabJob Applicant` ja
			WHERE ja.status = 'Accepted'
			AND ja.modified >= DATE_SUB(NOW(), INTERVAL 90 DAY)
		""", as_dict=True)
		
		if not hired_stats:
			return {
				"avg_days_to_hire": 0,
				"min_days": 0,
				"max_days": 0,
				"total_hired": 0
			}
		
		days_list = [s.days_to_hire for s in hired_stats]
		
		return {
			"avg_days_to_hire": round(sum(days_list) / len(days_list), 1),
			"min_days": min(days_list),
			"max_days": max(days_list),
			"total_hired": len(hired_stats),
			"timestamp": frappe.utils.now()
		}
	
	@staticmethod
	def get_top_skills_demand() -> List[Dict[str, Any]]:
		"""
		Get most in-demand skills from job openings.
		
		Returns:
			List of skills with demand count
		"""
		
		# This would ideally parse job descriptions
		# For now, get from AI Candidate Profiles
		
		skills_data = frappe.db.sql("""
			SELECT primary_skills
			FROM `tabAI Candidate Profile`
			WHERE primary_skills IS NOT NULL
			AND primary_skills != ''
		""", as_dict=True)
		
		# Count skill occurrences
		skill_counts = {}
		for record in skills_data:
			if record.primary_skills:
				skills = [s.strip() for s in record.primary_skills.split(',')]
				for skill in skills:
					if skill:
						skill_counts[skill] = skill_counts.get(skill, 0) + 1
		
		# Sort and return top 10
		sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:10]
		
		return [
			{"skill": skill, "count": count}
			for skill, count in sorted_skills
		]
	
	@staticmethod
	def get_rejection_reasons() -> List[Dict[str, Any]]:
		"""
		Get top rejection reasons from AI shortlisting.
		
		Returns:
			List of rejection reasons with counts
		"""
		
		rejected_results = frappe.db.sql("""
			SELECT reasons
			FROM `tabAI Shortlisting Result`
			WHERE decision = 'Reject'
			AND reasons IS NOT NULL
		""", as_dict=True)
		
		# Parse and count reasons
		reason_counts = {}
		for record in rejected_results:
			if record.reasons:
				import json
				try:
					reasons = json.loads(record.reasons)
					if isinstance(reasons, list):
						for reason in reasons:
							reason_counts[reason] = reason_counts.get(reason, 0) + 1
				except:
					pass
		
		# Sort and return top 5
		sorted_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)[:5]
		
		return [
			{"reason": reason, "count": count}
			for reason, count in sorted_reasons
		]


@frappe.whitelist()
def get_dashboard_data() -> Dict[str, Any]:
	"""
	Get comprehensive dashboard data.
	
	Returns:
		Complete dashboard data
	"""
	
	if not frappe.has_permission("Job Applicant", "read"):
		frappe.throw("Insufficient permissions")
	
	return {
		"overview": DashboardAnalytics.get_pipeline_overview(),
		"ai_performance": DashboardAnalytics.get_ai_performance_metrics(),
		"funnel": DashboardAnalytics.get_funnel_stats(),
		"time_to_hire": DashboardAnalytics.get_time_to_hire_stats(),
		"top_skills": DashboardAnalytics.get_top_skills_demand(),
		"rejection_reasons": DashboardAnalytics.get_rejection_reasons()
	}


@frappe.whitelist()
def get_applicant_timeline(job_applicant: str) -> List[Dict[str, Any]]:
	"""
	Get complete timeline for a job applicant.
	
	Args:
		job_applicant: Job Applicant name
		
	Returns:
		List of timeline events
	"""
	
	if not frappe.has_permission("Job Applicant", "read"):
		frappe.throw("Insufficient permissions")
	
	timeline = []
	
	# Get Job Applicant creation
	applicant = frappe.get_doc("Job Applicant", job_applicant)
	timeline.append({
		"date": applicant.creation,
		"event": "Application Received",
		"description": f"Applied for {applicant.job_title}",
		"type": "info"
	})
	
	# Get AI Candidate Profile
	if frappe.db.exists("AI Candidate Profile", {"job_applicant": job_applicant}):
		profile = frappe.get_doc("AI Candidate Profile", {"job_applicant": job_applicant})
		timeline.append({
			"date": profile.creation,
			"event": "Resume Parsed",
			"description": f"AI parsed resume. Experience: {profile.total_experience_years} years",
			"type": "success"
		})
	
	# Get Shortlisting Result
	if frappe.db.exists("AI Shortlisting Result", {"job_applicant": job_applicant}):
		result = frappe.get_doc("AI Shortlisting Result", {"job_applicant": job_applicant})
		timeline.append({
			"date": result.creation,
			"event": f"AI Decision: {result.decision}",
			"description": f"Fit score: {result.fit_score}%",
			"type": "success" if result.decision == "Shortlist" else "danger"
		})
	
	# Get Evaluation Result
	if frappe.db.exists("AI Evaluation Result", {"job_applicant": job_applicant}):
		evaluation = frappe.get_doc("AI Evaluation Result", {"job_applicant": job_applicant})
		timeline.append({
			"date": evaluation.creation,
			"event": "Questionnaire Completed",
			"description": f"Score: {evaluation.percentage_score}% - {evaluation.pass_fail}",
			"type": "success" if evaluation.pass_fail == "Pass" else "warning"
		})
	
	# Get Interview Brief
	if frappe.db.exists("AI Interview Brief", {"job_applicant": job_applicant}):
		brief = frappe.get_doc("AI Interview Brief", {"job_applicant": job_applicant})
		timeline.append({
			"date": brief.creation,
			"event": "Interview Brief Generated",
			"description": f"AI Recommendation: {brief.ai_hire_recommendation}",
			"type": "info"
		})
		
		if brief.interview_completed:
			timeline.append({
				"date": brief.modified,
				"event": "Interview Completed",
				"description": f"Interviewer Recommendation: {brief.interviewer_recommendation}",
				"type": "success" if brief.interviewer_recommendation in ["Hire", "Strong Hire"] else "warning"
			})
	
	# Sort by date
	timeline.sort(key=lambda x: x["date"])
	
	return timeline
