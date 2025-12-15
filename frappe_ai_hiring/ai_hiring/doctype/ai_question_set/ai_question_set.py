# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document
from typing import Dict, Any, List


class AIQuestionSet(Document):
	"""AI Question Set DocType"""

	def validate(self):
		"""Validate question set"""
		self.update_total_questions()
		self.validate_passing_score()

	def update_total_questions(self):
		"""Update total questions count"""
		self.total_questions = len(self.questions) if self.questions else 0

	def validate_passing_score(self):
		"""Validate passing score"""
		if self.passing_score and not (0 <= self.passing_score <= 100):
			frappe.throw("Passing score must be between 0 and 100")

	def get_questions_by_topic(self, topic: str) -> List[Dict[str, Any]]:
		"""
		Get questions filtered by topic

		Args:
			topic: Topic name

		Returns:
			List of questions
		"""
		return [q.as_dict() for q in self.questions if q.topic == topic]

	def calculate_score(self, answers: Dict[str, str]) -> Dict[str, Any]:
		"""
		Calculate score for given answers

		Args:
			answers: Dict mapping question index to answer (Yes/No)

		Returns:
			Score calculation result
		"""
		if not self.questions:
			return {"total_score": 0, "percentage": 0, "passed": False}

		total_weight = sum(q.weight or 1 for q in self.questions)
		earned_weight = 0

		results = []
		for idx, question in enumerate(self.questions):
			question_id = str(idx)
			given_answer = answers.get(question_id, "")
			is_correct = given_answer == question.expected_answer
			weight = question.weight or 1

			if is_correct:
				earned_weight += weight

			results.append({
				"question": question.question_text,
				"topic": question.topic,
				"given_answer": given_answer,
				"expected_answer": question.expected_answer,
				"is_correct": is_correct,
				"weight": weight,
			})

		percentage = (earned_weight / total_weight * 100) if total_weight > 0 else 0
		passed = percentage >= (self.passing_score or 70)

		return {
			"total_questions": len(self.questions),
			"correct_answers": sum(1 for r in results if r["is_correct"]),
			"total_weight": total_weight,
			"earned_weight": earned_weight,
			"percentage": round(percentage, 2),
			"passed": passed,
			"results": results,
		}


@frappe.whitelist()
def get_question_set(job_role: str, difficulty: str = "Basic") -> Dict[str, Any]:
	"""
	Get question set for a job role

	Args:
		job_role: Job role name
		difficulty: Difficulty level

	Returns:
		Question set data or None
	"""
	question_set = frappe.db.get_value(
		"AI Question Set",
		{"job_role": job_role, "difficulty": difficulty},
		["name", "job_role", "difficulty", "total_questions", "passing_score"],
		as_dict=True,
		order_by="creation desc",
	)

	if question_set:
		# Get questions
		doc = frappe.get_doc("AI Question Set", question_set.name)
		question_set["questions"] = [
			{
				"idx": idx,
				"topic": q.topic,
				"question_text": q.question_text,
				"weight": q.weight,
			}
			for idx, q in enumerate(doc.questions)
		]

	return question_set if question_set else None


@frappe.whitelist()
def submit_answers(question_set: str, answers: str) -> Dict[str, Any]:
	"""
	Submit answers and get score

	Args:
		question_set: Question set name
		answers: JSON string of answers

	Returns:
		Score result
	"""
	try:
		answers_dict = json.loads(answers) if isinstance(answers, str) else answers
		doc = frappe.get_doc("AI Question Set", question_set)
		result = doc.calculate_score(answers_dict)
		return result
	except Exception as e:
		frappe.throw(f"Failed to submit answers: {str(e)}")
