// Copyright (c) 2025, Your Company and contributors
// For license information, please see license.txt

// Client-side script to wire the Test Configuration button
frappe.ui.form.on("AI Settings", {
	refresh(frm) {
		// Add explicit button to call server-side test_connection
		frm.add_custom_button(
			__("Test Configuration"),
			() => {
				frappe.call({
					method: "frappe_ai_hiring.ai_hiring.doctype.ai_settings.ai_settings.test_connection",
					freeze: true,
					freeze_message: __("Testing AI configuration..."),
					success: (r) => {
						if (r && r.message && r.message.success) {
							frappe.show_alert({
								message: __("Connection successful"),
								indicator: "green",
							});
						}
					},
					error: (err) => {
						// frappe.call will already show the error; keep handler for clarity
						console.error("Test configuration failed", err);
					},
				});
			}
		).addClass("btn-primary");
	},
});
