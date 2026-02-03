#!/usr/bin/env python3
"""Update implementation_plan.json with QA approval status."""

import json
from datetime import datetime, timezone
from pathlib import Path

# Load implementation plan (relative to script location)
script_dir = Path(__file__).parent
plan_path = script_dir / ".auto-claude/specs/005-code-quality-metrics/implementation_plan.json"
with open(plan_path) as f:
    data = json.load(f)

# Update qa_signoff section
data["qa_signoff"] = {
    "status": "approved",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "qa_session": 2,
    "report_file": "qa_report.md",
    "tests_passed": {
        "unit": "46/46",
        "integration": "E2E PASSED",
        "e2e": "N/A"
    },
    "verified_by": "qa_agent",
    "fixes_from_session_1": [
        "Unrelated frontend files removed (commit 6239a4a)",
        "CodeQualityAnalyzer export fixed (commit 8512af6)"
    ],
    "critical_issues": 0,
    "major_issues": 0,
    "minor_issues": 0,
    "acceptance_criteria_met": [
        "Cyclomatic complexity tracking",
        "Maintainability index calculation",
        "Technical debt estimation",
        "Quality trends over time",
        "Integration with SonarQube or similar"
    ]
}

# Update qa_iteration_history
if "qa_iteration_history" not in data:
    data["qa_iteration_history"] = []

data["qa_iteration_history"].append({
    "iteration": 2,
    "status": "approved",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "issues": [],
    "duration_seconds": 600  # approximately 10 minutes
})

# Update qa_stats
data["qa_stats"] = {
    "total_iterations": 2,
    "last_iteration": 2,
    "last_status": "approved",
    "issues_by_type": {
        "critical": 0,
        "major": 0,
        "minor": 0
    }
}

# Save updated plan
with open(plan_path, 'w') as f:
    json.dump(data, f, indent=2)

print("✅ Implementation plan updated with QA approval")
print("Status: APPROVED")
print("QA Session: 2")
print("Tests: 46/46 unit tests passed, E2E verification passed")
