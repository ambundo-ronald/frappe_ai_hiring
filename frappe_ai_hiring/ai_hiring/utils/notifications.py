"""
Notification System
Handles email notifications and in-app alerts for the AI hiring pipeline
"""

import frappe
from typing import Dict, List, Any, Optional


class NotificationManager:
	"""Manages notifications for hiring pipeline events"""
	
	@staticmethod
	def send_candidate_notification(
		job_applicant: str,
		notification_type: str,
		additional_data: Optional[Dict[str, Any]] = None
	) -> bool:
		"""
		Send notification to candidate.
		
		Args:
			job_applicant: Job Applicant name
			notification_type: Type of notification
			additional_data: Additional data for template
			
		Returns:
			True if sent successfully
		"""
		
		try:
			applicant = frappe.get_doc("Job Applicant", job_applicant)
			
			if not applicant.email_id:
				frappe.logger("ai_hiring").warning(
					f"Cannot send notification to {job_applicant}: No email address"
				)
				return False
			
			templates = NotificationManager._get_candidate_templates()
			
			if notification_type not in templates:
				frappe.throw(f"Unknown notification type: {notification_type}")
			
			template = templates[notification_type]
			
			# Prepare context
			context = {
				"applicant_name": applicant.applicant_name,
				"job_title": applicant.job_title,
				"company": frappe.defaults.get_global_default("company") or "Our Company"
			}
			
			if additional_data:
				context.update(additional_data)
			
			# Format subject and message
			subject = template["subject"].format(**context)
			message = template["message"].format(**context)
			
			# Send email
			frappe.sendmail(
				recipients=[applicant.email_id],
				subject=subject,
				message=message,
				reference_doctype="Job Applicant",
				reference_name=job_applicant
			)
			
			frappe.logger("ai_hiring").info(
				f"Sent {notification_type} notification to {applicant.email_id}"
			)
			
			return True
			
		except Exception as e:
			frappe.logger("ai_hiring").error(
				f"Failed to send notification: {str(e)}"
			)
			return False
	
	@staticmethod
	def send_hr_notification(
		job_applicant: str,
		notification_type: str,
		recipients: Optional[List[str]] = None,
		additional_data: Optional[Dict[str, Any]] = None
	) -> bool:
		"""
		Send notification to HR team.
		
		Args:
			job_applicant: Job Applicant name
			notification_type: Type of notification
			recipients: List of recipient emails (defaults to HR Managers)
			additional_data: Additional template data
			
		Returns:
			True if sent successfully
		"""
		
		try:
			applicant = frappe.get_doc("Job Applicant", job_applicant)
			
			# Get HR Manager emails if not specified
			if not recipients:
				recipients = NotificationManager._get_hr_managers()
			
			if not recipients:
				frappe.logger("ai_hiring").warning("No HR managers found for notification")
				return False
			
			templates = NotificationManager._get_hr_templates()
			
			if notification_type not in templates:
				frappe.throw(f"Unknown notification type: {notification_type}")
			
			template = templates[notification_type]
			
			# Prepare context
			context = {
				"applicant_name": applicant.applicant_name,
				"job_title": applicant.job_title,
				"applicant_link": frappe.utils.get_url_to_form("Job Applicant", job_applicant)
			}
			
			if additional_data:
				context.update(additional_data)
			
			# Format subject and message
			subject = template["subject"].format(**context)
			message = template["message"].format(**context)
			
			# Send email
			frappe.sendmail(
				recipients=recipients,
				subject=subject,
				message=message,
				reference_doctype="Job Applicant",
				reference_name=job_applicant
			)
			
			frappe.logger("ai_hiring").info(
				f"Sent {notification_type} notification to HR team"
			)
			
			return True
			
		except Exception as e:
			frappe.logger("ai_hiring").error(
				f"Failed to send HR notification: {str(e)}"
			)
			return False
	
	@staticmethod
	def create_in_app_notification(
		users: List[str],
		subject: str,
		message: str,
		doctype: str = "Job Applicant",
		docname: Optional[str] = None
	) -> bool:
		"""
		Create in-app notification for users.
		
		Args:
			users: List of usernames
			subject: Notification subject
			message: Notification message
			doctype: Reference DocType
			docname: Reference document name
			
		Returns:
			True if created successfully
		"""
		
		try:
			for user in users:
				notification = frappe.new_doc("Notification Log")
				notification.subject = subject
				notification.email_content = message
				notification.for_user = user
				notification.document_type = doctype
				notification.document_name = docname
				notification.type = "Alert"
				notification.insert(ignore_permissions=True)
			
			frappe.db.commit()
			
			return True
			
		except Exception as e:
			frappe.logger("ai_hiring").error(
				f"Failed to create in-app notification: {str(e)}"
			)
			return False
	
	@staticmethod
	def _get_candidate_templates() -> Dict[str, Dict[str, str]]:
		"""Get email templates for candidate notifications"""
		
		return {
			"application_received": {
				"subject": "Application Received - {job_title}",
				"message": """Dear {applicant_name},

Thank you for applying for the {job_title} position at {company}.

We have received your application and our AI-powered system is currently reviewing your resume. You will receive an update within 24-48 hours.

Best regards,
{company} Hiring Team"""
			},
			"questionnaire_invitation": {
				"subject": "Next Step: Technical Screening - {job_title}",
				"message": """Dear {applicant_name},

Congratulations! Your application for {job_title} has been shortlisted.

The next step is to complete a brief technical screening questionnaire. Please click the link below to get started:

{questionnaire_link}

This should take approximately 15-20 minutes to complete.

Best regards,
{company} Hiring Team"""
			},
			"interview_invitation": {
				"subject": "Interview Invitation - {job_title}",
				"message": """Dear {applicant_name},

We are pleased to invite you for an interview for the {job_title} position.

Interview Details:
- Date: {interview_date}
- Time: {interview_time}
- Duration: {interview_duration}
- Location/Link: {interview_location}

Please confirm your availability by replying to this email.

Best regards,
{company} Hiring Team"""
			},
			"offer_letter": {
				"subject": "Job Offer - {job_title}",
				"message": """Dear {applicant_name},

We are delighted to extend an offer for the {job_title} position at {company}.

Please find the detailed offer letter attached. We look forward to welcoming you to our team!

Best regards,
{company} Hiring Team"""
			},
			"rejection_notice": {
				"subject": "Application Status - {job_title}",
				"message": """Dear {applicant_name},

Thank you for your interest in the {job_title} position at {company}.

After careful consideration, we have decided to move forward with other candidates whose qualifications more closely match our current needs.

We appreciate the time you invested in the application process and encourage you to apply for future opportunities with us.

Best regards,
{company} Hiring Team"""
			}
		}
	
	@staticmethod
	def _get_hr_templates() -> Dict[str, Dict[str, str]]:
		"""Get email templates for HR notifications"""
		
		return {
			"candidate_shortlisted": {
				"subject": "Candidate Shortlisted: {applicant_name}",
				"message": """A candidate has been automatically shortlisted by the AI system.

Candidate: {applicant_name}
Position: {job_title}
Fit Score: {fit_score}%

View Details: {applicant_link}

Please review and proceed with the next steps."""
			},
			"interview_brief_ready": {
				"subject": "Interview Brief Ready: {applicant_name}",
				"message": """An AI-generated interview brief is now available.

Candidate: {applicant_name}
Position: {job_title}
Recommendation: {recommendation}

View Brief: {applicant_link}

The brief includes suggested questions, verification points, and candidate analysis."""
			},
			"questionnaire_completed": {
				"subject": "Questionnaire Completed: {applicant_name}",
				"message": """Candidate has completed the technical screening questionnaire.

Candidate: {applicant_name}
Position: {job_title}
Score: {score}%
Result: {result}

View Results: {applicant_link}"""
			},
			"high_priority_candidate": {
				"subject": "High Priority Candidate: {applicant_name}",
				"message": """A high-priority candidate has been identified.

Candidate: {applicant_name}
Position: {job_title}
Fit Score: {fit_score}%

This candidate scored {fit_score}% fit and should be fast-tracked for interview.

View Profile: {applicant_link}"""
			}
		}
	
	@staticmethod
	def _get_hr_managers() -> List[str]:
		"""Get list of HR Manager email addresses"""
		
		hr_managers = frappe.get_all(
			"Has Role",
			filters={"role": "HR Manager", "parenttype": "User"},
			fields=["parent"]
		)
		
		emails = []
		for manager in hr_managers:
			user = frappe.get_doc("User", manager.parent)
			if user.enabled and user.email:
				emails.append(user.email)
		
		return emails


@frappe.whitelist()
def notify_candidate(
	job_applicant: str,
	notification_type: str,
	**kwargs
) -> Dict[str, Any]:
	"""
	Send notification to candidate (whitelisted for API access).
	
	Args:
		job_applicant: Job Applicant name
		notification_type: Type of notification
		**kwargs: Additional template data
		
	Returns:
		Result dict
	"""
	
	if not frappe.has_permission("Job Applicant", "write"):
		frappe.throw("Insufficient permissions")
	
	success = NotificationManager.send_candidate_notification(
		job_applicant=job_applicant,
		notification_type=notification_type,
		additional_data=kwargs
	)
	
	return {
		"success": success,
		"message": "Notification sent" if success else "Notification failed"
	}


@frappe.whitelist()
def notify_hr_team(
	job_applicant: str,
	notification_type: str,
	**kwargs
) -> Dict[str, Any]:
	"""
	Send notification to HR team (whitelisted for API access).
	
	Args:
		job_applicant: Job Applicant name
		notification_type: Type of notification
		**kwargs: Additional template data
		
	Returns:
		Result dict
	"""
	
	if not frappe.has_permission("Job Applicant", "read"):
		frappe.throw("Insufficient permissions")
	
	success = NotificationManager.send_hr_notification(
		job_applicant=job_applicant,
		notification_type=notification_type,
		additional_data=kwargs
	)
	
	return {
		"success": success,
		"message": "Notification sent" if success else "Notification failed"
	}
