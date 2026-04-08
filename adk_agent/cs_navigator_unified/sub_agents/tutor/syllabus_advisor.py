"""Syllabus Advisor sub-agent -- answers questions about course syllabi."""

import os
from google.adk.agents import LlmAgent
from google.adk.tools import VertexAiSearchTool
from google.adk.tools.agent_tool import AgentTool

MODEL = os.getenv("AGENT_MODEL", "gemini-2.5-flash")
SYLLABI_DATASTORE_ID = os.getenv("SYLLABI_DATASTORE_ID", "")
syllabi_tools = [VertexAiSearchTool(data_store_id=SYLLABI_DATASTORE_ID)] if SYLLABI_DATASTORE_ID else []

_syllabi_search_agent = LlmAgent(
    name="Syllabi_Search",
    model=MODEL,
    description="Searches the CS department syllabi datastore.",
    tools=syllabi_tools,
    instruction="Use the VertexAiSearchTool to find information from the CS course syllabi.",
)

syllabus_advisor = LlmAgent(
    name="Syllabus_Advisor",
    model=MODEL,
    tools=[AgentTool(agent=_syllabi_search_agent)],
    instruction="""You are a Syllabus Advisor for the Computer Science department.

You help with:
- Course overviews and learning objectives
- Grading breakdowns (exams, assignments, projects, participation)
- Required and recommended textbooks
- Weekly/monthly topic schedules
- Assignment and project deadlines
- Attendance, late work, and academic integrity policies
- Office hours and instructor contact info
- Exam dates and formats

When answering:
1. Always cite which syllabus (e.g., "According to the COSC 111 syllabus...")
2. Focus only on the requested course
3. If info isn't in the syllabi, say so clearly
4. For deadlines/dates, remind to confirm with professor

Keep responses concise and direct.
""",
)
