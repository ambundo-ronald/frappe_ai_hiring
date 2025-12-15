# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document
from typing import Dict, Any


class AIEvaluationResult(Document):
	"""AI Evaluation Result DocType"""

	def validate(self):
		"""Validate evaluation result"""
		self.determine_pass_fail()

	def determine_pass_fail(self):
		"""Determine pass/fail status based on score"""
		if self.percentage_score and self.passing_score_threshold:
			self.threshold_met = 1 if self.percentage_score >= self.passing_score_threshold else 0
			self.pass_fail = "Pass" if self.threshold_met else "Fail"

	def set_results(
		self,
		score_data: Dict[str, Any],
		weak_topics: list,
		strong_topics: list,
		inconsistencies: str,
		recommendation: str,
		model: str,
	):
		"""
		Set evaluation results

		Args:
			score_data: Score calculation result from question set
			weak_topics: List of weak topics
			strong_topics: List of strong topics
			inconsistencies: Inconsistencies found
			recommendation: AI recommendation
			model: Model name
		"""
		self.total_questions = score_data.get("total_questions", 0)
		self.correct_answers = score_data.get("correct_answers", 0)
		self.total_score = score_data.get("earned_weight", 0)
		self.percentage_score = score_data.get("percentage", 0)

		self.weak_topics = ", ".join(weak_topics) if isinstance(weak_topics, list) else weak_topics
		self.strong_topics = ", ".join(strong_topics) if isinstance(strong_topics, list) else strong_topics
		self.inconsistencies = inconsistencies
		self.recommendation = recommendation
		self.evaluated_by_model = model

		# Store detailed results
		self.detailed_results = json.dumps(score_data, indent=2)

	def get_topic_performance(self) -> Dict[str, Any]:
		"""
		Get performance breakdown by topic

		Returns:
			Topic performance statistics
		"""
		if not self.detailed_results:
			return {}

		try:
			data = json.loads(self.detailed_results)
			results = data.get("results", [])

			topic_stats = {}
			for result in results:
				topic = result.get("topic")
				if topic not in topic_stats:
					topic_stats[topic] = {"total": 0, "correct": 0}

				topic_stats[topic]["total"] += 1
				if result.get("is_correct"):
					topic_stats[topic]["correct"] += 1

			# Calculate percentages
			for topic in topic_stats:
				total = topic_stats[topic]["total"]
				correct = topic_stats[topic]["correct"]
				topic_stats[topic]["percentage"] = round((correct / total * 100), 2) if total > 0 else 0

			return topic_stats

		except (json.JSONDecodeError, KeyError):
			return {}


@frappe.whitelist()
def get_evaluation_result(applicant: str, question_set: str = None) -> Dict[str, Any]:
	"""
	Get evaluation result for an applicant

	Args:
		applicant: Job Applicant name
		question_set: Optional question set filter

	Returns:
		Evaluation result data or None
	"""
	filters = {"applicant": applicant}
	if question_set:
		filters["question_set"] = question_set

	result = frappe.db.get_value(
		"AI Evaluation Result",
		filters,
		[
			"name",
			"pass_fail",
			"percentage_score",
			"correct_answers",
			"total_questions",
			"recommendation",
		],
		as_dict=True,
		order_by="creation desc",
	)

	return result if result else None


@frappe.whitelist()
def get_evaluation_stats(job_opening: str = None) -> Dict[str, Any]:
	"""
	Get evaluation statistics

	Args:
		job_opening: Optional job opening filter

	Returns:
		Statistics dictionary
	"""
	filters = {}
	if job_opening:
		filters["job_opening"] = job_opening

	total = frappe.db.count("AI Evaluation Result", filters)
	passed = frappe.db.count("AI Evaluation Result", {**filters, "pass_fail": "Pass"})
	failed = frappe.db.count("AI Evaluation Result", {**filters, "pass_fail": "Fail"})

	avg_score = frappe.db.get_value("AI Evaluation Result", filters, "avg(percentage_score)") or 0

	return {
		"total": total,
		"passed": passed,
		"failed": failed,
		"pass_rate": round((passed / total * 100), 2) if total > 0 else 0,
		"avg_score": round(avg_score, 2),
	}
