"""
Frappe AI Hiring App Hooks
"""

from . import __version__ as app_version

app_name = "frappe_ai_hiring"
app_title = "Frappe AI Hiring"
app_publisher = "Your Company"
app_description = "AI-Driven Hiring Automation System for Frappe HRMS"
app_email = "info@yourcompany.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/frappe_ai_hiring/css/frappe_ai_hiring.css"
# app_include_js = "/assets/frappe_ai_hiring/js/frappe_ai_hiring.js"

# include js, css files in header of web template
# web_include_css = "/assets/frappe_ai_hiring/css/frappe_ai_hiring.css"
# web_include_js = "/assets/frappe_ai_hiring/js/frappe_ai_hiring.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "frappe_ai_hiring/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Job Applicant": "frappe_ai_hiring/ai_hiring/doctype/job_applicant/job_applicant.js",
	"AI Interview Brief": "frappe_ai_hiring/ai_hiring/doctype/ai_interview_brief/ai_interview_brief.js",
	"AI Settings": "frappe_ai_hiring/ai_hiring/doctype/ai_settings/ai_settings.js",
}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "frappe_ai_hiring.utils.jinja_methods",
# 	"filters": "frappe_ai_hiring.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "frappe_ai_hiring.install.before_install"
# after_install = "frappe_ai_hiring.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "frappe_ai_hiring.uninstall.before_uninstall"
# after_uninstall = "frappe_ai_hiring.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "frappe_ai_hiring.utils.before_app_install"
# after_app_install = "frappe_ai_hiring.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "frappe_ai_hiring.utils.before_app_uninstall"
# after_app_uninstall = "frappe_ai_hiring.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "frappe_ai_hiring.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Job Applicant": {
		"after_insert": "frappe_ai_hiring.ai_hiring.jobs.process_new_applicant.enqueue_applicant_processing",
		"on_update": "frappe_ai_hiring.ai_hiring.jobs.process_new_applicant.on_applicant_update",
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"frappe_ai_hiring.tasks.all"
# 	],
# 	"daily": [
# 		"frappe_ai_hiring.tasks.daily"
# 	],
# 	"hourly": [
# 		"frappe_ai_hiring.tasks.hourly"
# 	],
# 	"weekly": [
# 		"frappe_ai_hiring.tasks.weekly"
# 	],
# 	"monthly": [
# 		"frappe_ai_hiring.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "frappe_ai_hiring.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "frappe_ai_hiring.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "frappe_ai_hiring.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["frappe_ai_hiring.utils.before_request"]
# after_request = ["frappe_ai_hiring.utils.after_request"]

# Job Events
# ----------
# before_job = ["frappe_ai_hiring.utils.before_job"]
# after_job = ["frappe_ai_hiring.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"frappe_ai_hiring.auth.validate"
# ]

# Translation
# --------------------------------

# Make link fields search translated document names for these DocTypes
# Recommended only for DocTypes which have limited documents with untranslated names
# For example: Role, Gender, etc.
# translated_search_doctypes = []
