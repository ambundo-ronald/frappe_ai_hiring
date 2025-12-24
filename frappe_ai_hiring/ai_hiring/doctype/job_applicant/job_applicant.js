// Copyright (c) 2025, Your Company and contributors
// For license information, please see license.txt

frappe.ui.form.on("Job Applicant", {
	refresh(frm) {
		// Hide standard apply/rejected actions
		if (frm.doc.status === "Pending") {
			// Add Process Candidate button (manual trigger)
			if (frm.doc.resume_attachment) {
				frm.add_custom_button(__("Process Candidate"), function() {
					frappe.call({
						method: "frappe_ai_hiring.ai_hiring.jobs.process_new_applicant.enqueue_applicant_processing",
						args: {
							doc: frm.doc,
						},
						callback: function(r) {
							frappe.msgprint(
								__("Candidate processing queued"),
								__("Success")
							);
						},
					});
				}).addClass("btn-success");
			}

			// Add custom AI actions
			frm.add_custom_button(__("Reprocess Candidate"), function() {
				frappe.call({
					method: "frappe_ai_hiring.ai_hiring.doctype.job_applicant.job_applicant.reprocess_candidate",
					args: {
						job_applicant: frm.doc.name,
						stages: ["parsing", "shortlisting", "interview_brief"],
					},
					callback: function(r) {
						frappe.msgprint(
							__("Candidate reprocessing queued"),
							__("Success")
						);
						setTimeout(() => frm.reload_doc(), 2000);
					},
				});
			}).addClass("btn-primary");

			// Manual: Generate Questions (no automatic generation)
			if (frm.doc.status !== "Rejected" && frm.doc.job_title) {
				frm.add_custom_button(__("Generate Questions"), function() {
					frappe.call({
						method: "frappe_ai_hiring.ai_hiring.doctype.job_applicant.job_applicant.generate_questions",
						args: {
							job_applicant: frm.doc.name,
							difficulty: "Medium",
							num_questions: 15,
						},
						callback: function(r) {
							if (r.message && r.message.question_set) {
								frappe.msgprint(
									__("Question set generated: ") + r.message.question_set,
									__("Success")
								);
							} else {
								frappe.msgprint(__("Question generation completed"));
							}
						},
					});
				}).addClass("btn-warning");
			}

			// Show only if shortlisted
			let show_questionnaire = frappe.db.count("AI Shortlisting Result", {
				filters: {
					applicant: frm.doc.name,
					decision: "Shortlist",
				},
			}).then((count) => {
				if (count > 0) {
					frm.add_custom_button(
						__("Send Questionnaire"),
						function() {
							frappe.call({
								method: "frappe_ai_hiring.ai_hiring.doctype.job_applicant.job_applicant.send_questionnaire",
								args: {
									job_applicant: frm.doc.name,
								},
								callback: function(r) {
									if (r.message) {
										frappe.msgprint(
											__("Questionnaire sent successfully"),
											__("Success")
										);
										frm.reload_doc();
									}
								},
							});
						}
					).addClass("btn-info");
				}
			});
		}

		// Manual: Send Rejected Mail
		if (frm.doc.status === "Rejected") {
			frm.add_custom_button(__("Send Rejected Mail"), function() {
				frappe.call({
					method: "frappe_ai_hiring.ai_hiring.doctype.job_applicant.job_applicant.send_rejection_email",
					args: { job_applicant: frm.doc.name },
					callback: function(r) {
						frappe.msgprint(__("Rejection email sent"));
					}
				});
			}).addClass("btn-danger");
		}

		// Show processing status
		if (frm.doc.name) {
			frappe.call({
				method: "frappe_ai_hiring.ai_hiring.doctype.job_applicant.job_applicant.get_processing_status",
				args: {
					job_applicant: frm.doc.name,
				},
				callback: function(r) {
					if (r.message) {
						const status = r.message;
						let status_html = `<div class="alert alert-info">
                            <strong>AI Processing Status:</strong><br/>
                            Parsed: ${status.parsed ? "✅" : "⏳"}<br/>
                            Shortlisted: ${status.shortlisted ? "✅" : "⏳"}<br/>
                            Interview Brief: ${status.interview_brief ? "✅" : "⏳"}
                        </div>`;
						frm.set_df_property("section_break_0", "description", status_html);
					}
				},
			});
		}
	},
});
