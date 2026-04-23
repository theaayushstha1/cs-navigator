"""Tutor sub-agent package.

Exports the collapsed `tutor_agent`, a single LlmAgent that handles all
tutoring specialties (CS concepts, math, quizzes, debugging, problem
walkthroughs) via prompt personas. Syllabus lookups delegate to the
`syllabus_advisor` sub-agent, which keeps its own VertexAiSearchTool.

The legacy orchestrator + specialist files (orchestrator.py, cs_tutor.py,
math_tutor.py, quiz_master.py, code_debugger.py, problem_solver.py) are
intentionally left in place but orphaned for git history.
"""

from .collapsed_tutor import tutor_agent

__all__ = ["tutor_agent"]
