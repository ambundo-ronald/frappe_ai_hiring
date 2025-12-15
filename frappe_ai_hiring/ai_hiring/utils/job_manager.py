"""
Job Management Utilities
Helper functions for managing background jobs and queue operations
"""

import frappe
from typing import Dict, List, Any, Optional
from datetime import datetime


def enqueue_with_retry(
	method: str,
	queue: str = "default",
	timeout: int = 300,
	max_retries: int = 3,
	retry_delay: int = 60,
	**kwargs
) -> str:
	"""
	Enqueue a job with retry configuration.
	
	Args:
		method: The method to enqueue
		queue: Queue name (default, short, long)
		timeout: Job timeout in seconds
		max_retries: Maximum number of retries
		retry_delay: Delay between retries in seconds
		**kwargs: Arguments to pass to the method
		
	Returns:
		Job ID
	"""
	
	job = frappe.enqueue(
		method=method,
		queue=queue,
		timeout=timeout,
		is_async=True,
		**kwargs
	)
	
	# Store job metadata for tracking
	job_id = str(job.id) if hasattr(job, 'id') else None
	
	if job_id:
		_store_job_metadata(
			job_id=job_id,
			method=method,
			queue=queue,
			max_retries=max_retries,
			retry_delay=retry_delay,
			kwargs=kwargs
		)
	
	return job_id


def _store_job_metadata(
	job_id: str,
	method: str,
	queue: str,
	max_retries: int,
	retry_delay: int,
	kwargs: Dict[str, Any]
) -> None:
	"""
	Store job metadata in cache for tracking.
	
	Args:
		job_id: Unique job ID
		method: Method being executed
		queue: Queue name
		max_retries: Maximum retries
		retry_delay: Delay between retries
		kwargs: Job arguments
	"""
	
	cache_key = f"job_metadata:{job_id}"
	metadata = {
		"job_id": job_id,
		"method": method,
		"queue": queue,
		"max_retries": max_retries,
		"retry_delay": retry_delay,
		"kwargs": kwargs,
		"created_at": datetime.now().isoformat(),
		"status": "queued",
		"retry_count": 0
	}
	
	frappe.cache().set_value(cache_key, metadata, expires_in_sec=86400)  # 24 hours


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
	"""
	Get status of a background job.
	
	Args:
		job_id: Job ID
		
	Returns:
		Job metadata dict or None
	"""
	
	cache_key = f"job_metadata:{job_id}"
	return frappe.cache().get_value(cache_key)


def update_job_status(
	job_id: str,
	status: str,
	error_message: Optional[str] = None
) -> None:
	"""
	Update job status in cache.
	
	Args:
		job_id: Job ID
		status: New status (queued, running, completed, failed, retrying)
		error_message: Optional error message
	"""
	
	cache_key = f"job_metadata:{job_id}"
	metadata = frappe.cache().get_value(cache_key)
	
	if metadata:
		metadata["status"] = status
		metadata["updated_at"] = datetime.now().isoformat()
		
		if error_message:
			metadata["error_message"] = error_message
		
		if status == "retrying":
			metadata["retry_count"] = metadata.get("retry_count", 0) + 1
		
		frappe.cache().set_value(cache_key, metadata, expires_in_sec=86400)


def retry_failed_job(job_id: str) -> bool:
	"""
	Retry a failed job.
	
	Args:
		job_id: Job ID to retry
		
	Returns:
		True if retry was queued, False otherwise
	"""
	
	metadata = get_job_status(job_id)
	
	if not metadata:
		frappe.throw(f"Job {job_id} not found")
	
	if metadata["status"] not in ["failed", "error"]:
		frappe.throw(f"Job {job_id} is not in failed state")
	
	retry_count = metadata.get("retry_count", 0)
	max_retries = metadata.get("max_retries", 3)
	
	if retry_count >= max_retries:
		frappe.throw(f"Job {job_id} has exceeded maximum retries ({max_retries})")
	
	# Re-enqueue the job
	method = metadata["method"]
	queue = metadata.get("queue", "default")
	kwargs = metadata.get("kwargs", {})
	
	new_job_id = enqueue_with_retry(
		method=method,
		queue=queue,
		max_retries=max_retries - retry_count,
		**kwargs
	)
	
	frappe.logger("ai_hiring").info(
		f"Retrying job {job_id} as new job {new_job_id}"
	)
	
	return True


def get_queue_stats() -> Dict[str, Any]:
	"""
	Get statistics about job queues.
	
	Returns:
		Dict with queue statistics
	"""
	
	try:
		import redis
		from rq import Queue
		from frappe.utils.background_jobs import get_redis_conn
		
		conn = get_redis_conn()
		
		stats = {}
		for queue_name in ["default", "short", "long"]:
			queue = Queue(queue_name, connection=conn)
			stats[queue_name] = {
				"count": len(queue),
				"started_jobs": queue.started_job_registry.count,
				"finished_jobs": queue.finished_job_registry.count,
				"failed_jobs": queue.failed_job_registry.count,
				"deferred_jobs": queue.deferred_job_registry.count
			}
		
		return stats
		
	except Exception as e:
		frappe.logger("ai_hiring").error(f"Failed to get queue stats: {str(e)}")
		return {}


def clear_stuck_jobs(queue_name: str = "default", timeout: int = 3600) -> int:
	"""
	Clear jobs that have been stuck for longer than timeout.
	
	Args:
		queue_name: Name of the queue
		timeout: Timeout in seconds (default 1 hour)
		
	Returns:
		Number of jobs cleared
	"""
	
	try:
		from rq import Queue
		from frappe.utils.background_jobs import get_redis_conn
		
		conn = get_redis_conn()
		queue = Queue(queue_name, connection=conn)
		
		# Get started jobs that are older than timeout
		registry = queue.started_job_registry
		job_ids = registry.get_job_ids()
		
		cleared = 0
		now = datetime.now()
		
		for job_id in job_ids:
			try:
				job = queue.fetch_job(job_id)
				if job and job.started_at:
					age = (now - job.started_at).total_seconds()
					if age > timeout:
						job.cancel()
						registry.remove(job)
						cleared += 1
			except:
				continue
		
		frappe.logger("ai_hiring").info(
			f"Cleared {cleared} stuck jobs from {queue_name} queue"
		)
		
		return cleared
		
	except Exception as e:
		frappe.logger("ai_hiring").error(f"Failed to clear stuck jobs: {str(e)}")
		return 0


@frappe.whitelist()
def get_applicant_processing_status(job_applicant: str) -> Dict[str, Any]:
	"""
	Get processing status for a job applicant.
	
	Args:
		job_applicant: Job Applicant name
		
	Returns:
		Status information
	"""
	
	status = {
		"applicant": job_applicant,
		"stages_completed": [],
		"current_stage": None,
		"overall_status": "Not Started"
	}
	
	# Check for candidate profile
	if frappe.db.exists("AI Candidate Profile", {"job_applicant": job_applicant}):
		status["stages_completed"].append("Resume Parsing")
	
	# Check for shortlisting result
	if frappe.db.exists("AI Shortlisting Result", {"job_applicant": job_applicant}):
		status["stages_completed"].append("Shortlisting")
		result = frappe.get_doc("AI Shortlisting Result", {"job_applicant": job_applicant})
		status["decision"] = result.decision
		status["fit_score"] = result.fit_score
	
	# Check for questionnaire
	if frappe.db.exists("AI Evaluation Result", {"job_applicant": job_applicant}):
		status["stages_completed"].append("Questionnaire Evaluation")
	
	# Check for interview brief
	if frappe.db.exists("AI Interview Brief", {"job_applicant": job_applicant}):
		status["stages_completed"].append("Interview Brief")
	
	# Determine overall status
	if len(status["stages_completed"]) == 0:
		status["overall_status"] = "Not Started"
	elif len(status["stages_completed"]) >= 4:
		status["overall_status"] = "Complete"
	else:
		status["overall_status"] = "In Progress"
		status["current_stage"] = status["stages_completed"][-1]
	
	return status


@frappe.whitelist()
def reprocess_applicant(job_applicant: str, stages: Optional[List[str]] = None) -> Dict[str, Any]:
	"""
	Reprocess an applicant through selected stages.
	
	Args:
		job_applicant: Job Applicant name
		stages: List of stages to reprocess (default: all)
		
	Returns:
		Result dict
	"""
	
	if not frappe.has_permission("Job Applicant", "write"):
		frappe.throw("Insufficient permissions")
	
	applicant = frappe.get_doc("Job Applicant", job_applicant)
	
	if not stages:
		stages = ["parsing", "shortlisting", "interview_brief"]
	
	results = {"applicant": job_applicant, "reprocessed": []}
	
	# Reprocess resume parsing
	if "parsing" in stages:
		try:
			from frappe_ai_hiring.ai_hiring.services.resume_parser import create_candidate_profile
			
			profile_name = create_candidate_profile(
				job_applicant=job_applicant,
				job_opening=applicant.job_title
			)
			results["reprocessed"].append({"stage": "parsing", "status": "success", "doc": profile_name})
		except Exception as e:
			results["reprocessed"].append({"stage": "parsing", "status": "failed", "error": str(e)})
	
	# Reprocess shortlisting
	if "shortlisting" in stages:
		try:
			from frappe_ai_hiring.ai_hiring.services.shortlisting_service import reshortlist_candidate
			
			result_name = reshortlist_candidate(
				job_applicant=job_applicant,
				job_opening=applicant.job_title
			)
			results["reprocessed"].append({"stage": "shortlisting", "status": "success", "doc": result_name})
		except Exception as e:
			results["reprocessed"].append({"stage": "shortlisting", "status": "failed", "error": str(e)})
	
	# Regenerate interview brief
	if "interview_brief" in stages:
		try:
			if frappe.db.exists("AI Interview Brief", {"job_applicant": job_applicant}):
				from frappe_ai_hiring.ai_hiring.services.interview_brief_service import regenerate_interview_brief
				
				brief_name = frappe.db.get_value("AI Interview Brief", {"job_applicant": job_applicant}, "name")
				regenerate_interview_brief(brief_name)
				results["reprocessed"].append({"stage": "interview_brief", "status": "success", "doc": brief_name})
			else:
				from frappe_ai_hiring.ai_hiring.services.interview_brief_service import create_interview_brief
				
				brief_name = create_interview_brief(job_applicant=job_applicant)
				results["reprocessed"].append({"stage": "interview_brief", "status": "success", "doc": brief_name})
		except Exception as e:
			results["reprocessed"].append({"stage": "interview_brief", "status": "failed", "error": str(e)})
	
	return results
