// Copyright (c) 2025, Your Company and contributors
// For license information, please see license.txt

frappe.ui.form.on("AI Interview Brief", {
	refresh(frm) {
		// Show schedule interview button if not scheduled
		if (!frm.doc.interview_scheduled) {
			frm.add_custom_button(__("Schedule Interview"), function() {
				let dialog = new frappe.ui.Dialog({
					title: __("Schedule Interview"),
					fields: [
						{
							label: __("Interview Date"),
							fieldname: "interview_date",
							fieldtype: "Date",
							reqd: 1,
						},
						{
							label: __("Interviewer Email"),
							fieldname: "interviewer_email",
							fieldtype: "Data",
							fieldtype: "Link",
							options: "User",
							reqd: 1,
						},
					],
					primary_action_label: __("Schedule"),
					primary_action(values) {
						frappe.call({
							method: "frappe_ai_hiring.ai_hiring.doctype.ai_interview_brief.ai_interview_brief.schedule_interview",
							args: {
								interview_brief: frm.doc.name,
								interview_date: values.interview_date,
								interviewer_email: values.interviewer_email,
							},
							callback: function(r) {
								if (r.message) {
									frappe.msgprint(
										__("Interview scheduled successfully"),
										__("Success")
									);
									dialog.hide();
									frm.reload_doc();
								}
							},
						});
					},
				});
				dialog.show();
			}).addClass("btn-primary");
		} else {
			frm.add_custom_button(__("Interview Scheduled ✓"), function() {
				frappe.msgprint(
					__(`Interview scheduled for ${frm.doc.interview_date}`)
				);
			}).addClass("btn-info").prop("disabled", true);
		}

		// Show interview feedback button if evaluation exists
		if (frm.doc.name) {
			frappe.call({
				method: "frappe_ai_hiring.ai_hiring.doctype.ai_interview_brief.ai_interview_brief.get_interview_feedback",
				args: {
					interview_brief: frm.doc.name,
				},
				callback: function(r) {
					if (
						r.message &&
						r.message.evaluation &&
						r.message.evaluation.overall_score
					) {
						frm.add_custom_button(__("View Feedback"), function() {
							frappe.msgprint(
								frappe.render_template(
									`<div>
                                <h5>Interview Evaluation</h5>
                                <div class="row">
                                    <div class="col-md-3 text-center">
                                        <h6>Overall Score</h6>
                                        <strong>${r.message.evaluation.overall_score}%</strong>
                                    </div>
                                    <div class="col-md-3 text-center">
                                        <h6>Technical</h6>
                                        <strong>${r.message.evaluation.technical_score}%</strong>
                                    </div>
                                    <div class="col-md-3 text-center">
                                        <h6>Communication</h6>
                                        <strong>${r.message.evaluation.communication_score}%</strong>
                                    </div>
                                    <div class="col-md-3 text-center">
                                        <h6>Culture Fit</h6>
                                        <strong>${r.message.evaluation.culture_fit_score}%</strong>
                                    </div>
                                </div>
                                <hr/>
                                <h6>Strengths</h6>
                                <p>${r.message.evaluation.key_strengths}</p>
                                <h6>Areas for Improvement</h6>
                                <p>${r.message.evaluation.areas_for_improvement}</p>
                                <h6>Recommendation</h6>
                                <p><strong>${r.message.evaluation.hire_recommendation}</strong></p>
                            </div>`
								)
							);
						});
					}
				},
			});
		}
	},
});
