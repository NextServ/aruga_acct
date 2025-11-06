app_name = "aruga_acct"
app_title = "Aruga Accounting"
app_publisher = "N/A"
app_description = "N/A"
app_email = "carl@servio.ph"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "aruga_acct",
# 		"logo": "/assets/aruga_acct/logo.png",
# 		"title": "Aruga Accounting",
# 		"route": "/aruga_acct",
# 		"has_permission": "aruga_acct.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/aruga_acct/css/aruga_acct.css"
# app_include_js = "/assets/aruga_acct/js/aruga_acct.js"

# include js, css files in header of web template
# web_include_css = "/assets/aruga_acct/css/aruga_acct.css"
# web_include_js = "/assets/aruga_acct/js/aruga_acct.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "aruga_acct/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
doctype_js = {
    "Purchase Invoice" : "public/js/purchase_invoice.js",
    "Sales Invoice" : "public/js/sales_invoice.js",
    "Payment Entry" : "public/js/payment_entry.js",
    "Expense Claim" : "public/js/expense_claim.js"
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "aruga_acct/public/icons.svg"

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
# 	"methods": "aruga_acct.utils.jinja_methods",
# 	"filters": "aruga_acct.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "aruga_acct.install.before_install"
# after_install = "aruga_acct.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "aruga_acct.uninstall.before_uninstall"
# after_uninstall = "aruga_acct.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "aruga_acct.utils.before_app_install"
# after_app_install = "aruga_acct.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "aruga_acct.utils.before_app_uninstall"
# after_app_uninstall = "aruga_acct.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "aruga_acct.notifications.get_notification_config"

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
    "Sales Invoice": {
        "validate": "aruga_acct.aruga_accounting.doc_events.sales_invoice_validate",
    },
    "Purchase Invoice": {
        "validate": "aruga_acct.aruga_accounting.doc_events.purchase_invoice_validate",
    },
    "Payment Entry": {
        "validate": "aruga_acct.aruga_accounting.doc_events.payment_entry_validate",
    },
}


jenv = {
	"methods": [
		"is_local_dev:aruga_acct.aruga_accounting.utils.is_local_dev",
		"preformat_tin:aruga_acct.aruga_accounting.utils.preformat_tin",
		"preformat_tin_with_dash:aruga_acct.aruga_accounting.utils.preformat_tin_with_dash"
	]
}

#v14
jinja = {
	"methods": [
		"aruga_acct.aruga_accounting.utils.is_local_dev",
		"aruga_acct.aruga_accounting.utils.preformat_tin",
		"aruga_acct.aruga_accounting.utils.preformat_tin_with_dash"
	]
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"aruga_acct.tasks.all"
# 	],
# 	"daily": [
# 		"aruga_acct.tasks.daily"
# 	],
# 	"hourly": [
# 		"aruga_acct.tasks.hourly"
# 	],
# 	"weekly": [
# 		"aruga_acct.tasks.weekly"
# 	],
# 	"monthly": [
# 		"aruga_acct.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "aruga_acct.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "aruga_acct.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "aruga_acct.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["aruga_acct.utils.before_request"]
# after_request = ["aruga_acct.utils.after_request"]

# Job Events
# ----------
# before_job = ["aruga_acct.utils.before_job"]
# after_job = ["aruga_acct.utils.after_job"]

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
# 	"aruga_acct.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

fixtures = [
    {
        "dt": "Letter Head", "filters": [
            [
                "name", "in", [
                    "BOA Letterhead"
                ]
            ]
        ]
    },
    {
        "dt": "PH Tax Type Code"
    },
    {
        "dt": "ATC"
    },
    {
        "dt": "VAT Industry"
    }
]
