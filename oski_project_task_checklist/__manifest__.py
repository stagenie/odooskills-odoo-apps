# -*- coding: utf-8 -*-
{
    "name": "Task Checklist",
    "version": "18.0.1.0.0",
    "category": "Services/Project",
    "summary": "Never let anything slip: every task gets a checkable checklist with a progress bar and per-step assignment.",
    "description": """
Step Checklist on Project Tasks
===============================

The micro-steps of a task often end up in comments or
emails — a source of oversights. This module adds a "Checklist" tab to every
project task to list, check and assign each sub-step.

- "Checklist" tab with an inline-editable list (reorderable by drag and drop).
- Automatically computed progress bar (% of steps completed).
- Each step can be assigned to a different user.
- Optional progress column in the task list view.

No configuration required: works right after installation.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_01_checklist_tab.png",
        "static/description/screenshot_02_list_progress.png",
    ],
    "depends": ["project"],
    "data": [
        "security/ir.model.access.csv",
        "views/project_task_views.xml",
    ],
    "installable": True,
    "application": False,
}
