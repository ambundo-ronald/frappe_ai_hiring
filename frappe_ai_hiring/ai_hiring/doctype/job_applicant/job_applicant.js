// Copyright (c) 2025, Your Company and contributors
// For license information, please see license.txt

frappe.ui.form.on("Job Applicant", {
	refresh(frm) {
		// Add actions into the Form Menu instead of showing custom buttons

		// Process Candidate (requires resume attached)
		if (frm.doc.resume_attachment) {
			frm.page.add_menu_item(__("Process Candidate"), () => {
				frappe.call({
					method: "frappe_ai_hiring.ai_hiring.doctype.job_applicant.job_applicant.process_candidate",
					args: { job_applicant: frm.doc.name },
					callback: () => {
						frappe.show_alert({ message: __("Candidate processing queued"), indicator: "green" });
					},
				});
			});
		}

		// Reprocess Candidate (always available)
		frm.page.add_menu_item(__("Reprocess Candidate"), () => {
			frappe.call({
				method: "frappe_ai_hiring.ai_hiring.doctype.job_applicant.job_applicant.reprocess_candidate",
				args: { job_applicant: frm.doc.name, stages: ["parsing", "shortlisting"] },
				callback: () => {
					frappe.show_alert({ message: __("Candidate reprocessing queued"), indicator: "green" });
					setTimeout(() => frm.reload_doc(), 1200);
				},
			});
		});

		// Generate Questions (available when not Rejected and job title present)
		if (frm.doc.status !== "Rejected" && frm.doc.job_title) {
			frm.page.add_menu_item(__("Generate Questions"), () => {
				frappe.call({
					method: "frappe_ai_hiring.ai_hiring.doctype.job_applicant.job_applicant.generate_questions",
					args: { job_applicant: frm.doc.name, difficulty: "Medium", num_questions: 15 },
					callback: (r) => {
						if (r.message && r.message.question_set) {
							frappe.msgprint({ message: __("Question set generated: ") + r.message.question_set, title: __("Success") });
						} else {
							frappe.show_alert({ message: __("Question generation completed"), indicator: "green" });
						}
					},
				});
			});
		}

		// Send Questionnaire (only if shortlisted)
		frappe.db.count("AI Shortlisting Result", {
			filters: { applicant: frm.doc.name, decision: "Shortlist" },
		}).then((count) => {
			if (count > 0) {
				frm.page.add_menu_item(__("Send Questionnaire"), () => {
					frappe.call({
						method: "frappe_ai_hiring.ai_hiring.doctype.job_applicant.job_applicant.send_questionnaire",
						args: { job_applicant: frm.doc.name },
						callback: (r) => {
							if (r.message) {
								frappe.show_alert({ message: __("Questionnaire sent"), indicator: "green" });
								frm.reload_doc();
							}
						},
					});
				});
			}
		});

		// Send Rejected Mail (only if Rejected)
		if (frm.doc.status === "Rejected") {
			frm.page.add_menu_item(__("Send Rejected Mail"), () => {
				frappe.call({
					method: "frappe_ai_hiring.ai_hiring.doctype.job_applicant.job_applicant.send_rejection_email",
					args: { job_applicant: frm.doc.name },
					callback: (r) => {
						if (r.message && r.message.success) {
							frappe.show_alert({ message: __("Rejection email sent"), indicator: "green" });
						}
					},
				});
			});
		}
	}
});

