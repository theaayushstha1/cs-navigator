"""Generate a 10-15 min study audio about CSNavigator using OpenAI TTS"""
import os
import io
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Script broken into chunks (OpenAI TTS limit ~4096 chars each)
# Written as a clear, educational narration
SCRIPT_CHUNKS = [

# CHUNK 1: Intro + Architecture Overview
"""Welcome to this deep dive into CSNavigator, the AI-powered academic advising chatbot built for Morgan State University's Computer Science Department. By the end of this guide, you'll understand exactly how every piece of this system works, from the moment a student types a question, to the moment they see the AI's answer streaming on their screen.

Let's start with the big picture. CSNavigator is built as three separate services that talk to each other. Think of it like a restaurant: the frontend is the dining room where customers sit, the backend is the kitchen manager taking orders and coordinating everything, and the ADK Agent is the actual chef doing the cooking, which in our case means the AI reasoning.

These three services are deployed on Google Cloud Run, which is a serverless platform. Serverless means you don't manage any servers. You give Google a Docker container, and Cloud Run runs it, scales it automatically, and even turns it off when nobody's using it so you don't pay anything. When a student sends a message, Cloud Run spins up your container in milliseconds.

Here's the flow: The user's browser loads the React frontend. When they type a question, the frontend sends it to the FastAPI backend. The backend then forwards the question to the ADK Agent, which uses Google's Gemini 2 Flash AI model to generate an answer. But here's the key part: the agent doesn't just make things up. It's grounded in a knowledge base of 45 documents covering everything about Morgan State's CS department.""",

# CHUNK 2: The ADK Agent Deep Dive
"""Let's go deeper into the ADK Agent, because this is the brain of the whole system. ADK stands for Agent Development Kit. It's Google's framework for building AI agents. Our agent uses a single unified architecture, which was a major evolution from the previous version.

Version 3 had eight separate specialist agents. There was an academic agent, a career agent, a financial aid agent, and so on. When a student asked a question, a root agent had to figure out which specialist to route it to. This meant three separate AI calls per question, taking six to twelve seconds. That's way too slow.

Version 4 collapsed everything into one unified agent. One agent handles all topics. It uses Gemini 2 Flash, which is Google's fastest model with good accuracy. Now every question takes just one AI call, responding in two to four seconds. That's a huge improvement.

Here's how a query actually gets processed, step by step. The student types "What are the prerequisites for COSC 220?" The frontend sends this to the backend's streaming endpoint. The backend first checks if this student has DegreeWorks data linked. DegreeWorks is the university's degree audit system that tracks what courses a student has completed. If they do have it linked, their academic record, including their GPA, completed courses, and remaining requirements, gets injected into the AI session.

Next, the backend checks the cache. We have a two-tier cache. Level 1 is an in-memory Python dictionary, instant lookup in under a millisecond. Level 2 is Redis, about five milliseconds. If we find a cached answer, we return it immediately, saving both time and money on AI API calls.""",

# CHUNK 3: Vertex AI Search + Grounding
"""If there's no cached answer, the backend calls the ADK Agent. The agent receives the question along with a system instruction that's hundreds of lines long. This instruction tells the agent who it is, what it can help with, how to format responses, and critically, it includes the student's DegreeWorks data if available.

Now here's where the magic happens. The agent has a tool called Vertex AI Search Tool. This tool is connected to a datastore in Google's Discovery Engine. The datastore contains 45 text documents stored in Google Cloud Storage. These documents cover academic information like courses, prerequisites, degree requirements, and faculty. They cover career topics like internships and organizations. Financial aid information including scholarships, FAFSA, tuition, and housing. And general campus resources like the library, tutoring services, and the academic calendar.

When the agent needs to answer a question, it automatically searches this knowledge base using semantic search. Semantic search means it understands meaning, not just keywords. So if a student asks "how do I get money for school," it will find documents about financial aid and scholarships even though those exact words aren't in the query.

The agent then generates its response based ONLY on what it found in the knowledge base plus the student's DegreeWorks data. This is called grounding. The agent is grounded in real data, which prevents it from hallucinating or making up fake course codes and requirements. If the knowledge base doesn't have the answer, the agent honestly says so and suggests contacting the CS department.""",

# CHUNK 4: Streaming + Frontend
"""Now let's talk about streaming, because this is what makes the chat feel fast and modern. When the backend gets the AI response, it doesn't wait for the entire answer to be generated. Instead, it streams it back in real time using a protocol called Server-Sent Events, or SSE.

SSE is a standard where the server sends a continuous stream of events to the browser over a regular HTTP connection. Each event is a line of text starting with "data:" followed by JSON. There are four event types: "status" events tell the frontend what the agent is doing, like searching the knowledge base. "Chunk" events contain pieces of the response text as they're generated. A "done" event signals the complete response. And "error" events indicate something went wrong.

On the frontend, the React Chatbox component reads this stream using the Fetch API's ReadableStream interface. As each chunk arrives, it appends the text to the bot's message bubble. This creates the typing effect you see in ChatGPT and Claude, where words appear one by one.

While waiting for the first chunk, the frontend shows an animated status indicator. This cycles through steps: first a lightbulb icon saying "Understanding your question," then a magnifying glass saying "Searching knowledge base," then "Analyzing results," and finally a pen icon saying "Preparing response." Each completed step gets a green checkmark with a pop animation. This gives the student visual feedback that the system is working.""",

# CHUNK 5: Backend Architecture
"""Let's dive into the backend architecture. The backend is a FastAPI application written in Python. FastAPI is a modern web framework that's extremely fast and supports async operations natively. The main file, main.py, is over 3000 lines long and contains all the API routes.

The backend has several critical modules. The vertex_agent module handles all communication with the ADK Agent. It manages sessions intelligently. Instead of creating a new session for every message, it caches sessions per user for 30 minutes. If the same student sends another question and their DegreeWorks data hasn't changed, we reuse the existing session, saving about 100 to 200 milliseconds per request.

The cache module implements the two-tier caching we discussed. The cache key combines the query text with a context hash. The context hash includes the user ID and whether they have DegreeWorks data. This is critical for security: it ensures personalized responses, which include student-specific course recommendations, are never accidentally served to other students.

The datastore manager module handles all operations on the knowledge base. Admins can upload, edit, search, and delete documents through the admin dashboard. When we first built this, loading the document list took over 10 seconds because it made 45 individual API calls to Google Cloud Storage to get each file's metadata. We optimized this by fetching all metadata in a single batch call and running it in parallel with the Discovery Engine query. Then we added a 60-second server-side cache. The result: first load dropped to 2.4 seconds, and subsequent loads are instant at 50 milliseconds.""",

# CHUNK 6: Auth + Database + Frontend Details
"""Authentication uses JWT tokens, which stands for JSON Web Tokens. When a student logs in, the backend verifies their password against a bcrypt hash stored in the MySQL database. If valid, it creates a signed token containing their user ID, email, and role. This token expires after four hours. The frontend stores it in the browser's local storage and includes it in every API request as a Bearer token in the Authorization header.

There are two roles: regular users who can chat, view their profile, and browse the curriculum, and admins who additionally get access to the admin dashboard with seven tabs for managing users, the knowledge base, support tickets, feedback, curriculum, and system health.

The database is MySQL hosted on Amazon's RDS service. It stores user accounts, chat history, DegreeWorks data, support tickets, and Banner student data. Interestingly, the same database is shared between local development and the production Cloud Run deployment.

On the frontend side, one of the most important files is apiBase.js. This tiny file determines where all API calls go. When running on localhost, it returns the local backend URL. When running on any other hostname, like the Cloud Run domain, it returns the production backend URL. This is how the exact same React code works both locally and in production without any configuration changes.""",

# CHUNK 7: Cloud Run + Deployment + Wrap Up
"""Finally, let's talk about deployment. All three services run on Google Cloud Run. Deploying is surprisingly simple. We use the command "gcloud run deploy" with a "--source" flag, which tells Google to build the Docker container in the cloud using Cloud Build. You don't even need Docker installed locally. Cloud Build reads the Dockerfile, builds the image, stores it in Artifact Registry, and deploys a new revision to Cloud Run. The whole process takes about three to five minutes per service.

We also created a Cloud Build YAML configuration file for CI/CD, meaning Continuous Integration and Continuous Deployment. When connected to GitHub, every push to the main branch automatically triggers a full deployment of all three services. The build pipeline runs in parallel where possible: it builds all three Docker images simultaneously, then deploys them in order, ADK first because the backend needs its URL, then backend, then frontend.

The ADK service is private, meaning only the backend can call it. The frontend and backend are public since users need to access them. The ADK gets more resources, 2 gigabytes of RAM and 2 CPUs, because it runs the AI model, while the frontend only needs 512 megabytes since it just serves static files.

To summarize, CSNavigator is a three-service architecture: React frontend, FastAPI backend, and Google ADK agent with Gemini 2 Flash. The agent is grounded in a 45-document knowledge base using Vertex AI Search. Responses stream in real time via Server-Sent Events. A two-tier cache saves money and time. DegreeWorks integration enables personalized academic advice. And everything deploys to Cloud Run with a single command. This is a production-grade AI system that serves real students at Morgan State University."""
]

output_dir = Path(r"C:\Users\Aayush\Desktop\cs-chatbot-v4.2")
output_file = output_dir / "CSNavigator_Study_Audio.mp3"

print(f"Generating {len(SCRIPT_CHUNKS)} audio chunks...")

# Generate each chunk and combine
audio_parts = []
for i, chunk in enumerate(SCRIPT_CHUNKS, 1):
    print(f"  Chunk {i}/{len(SCRIPT_CHUNKS)} ({len(chunk)} chars)...")
    response = client.audio.speech.create(
        model="tts-1-hd",
        voice="onyx",  # deep, clear male voice - good for educational content
        input=chunk,
        speed=0.95,  # slightly slower for study purposes
    )
    audio_parts.append(response.content)
    print(f"  Chunk {i} done ({len(response.content)} bytes)")

# Combine all audio parts into one file
print("Combining audio...")
with open(output_file, "wb") as f:
    for part in audio_parts:
        f.write(part)

size_mb = output_file.stat().st_size / (1024 * 1024)
print(f"\nDone! Audio saved to: {output_file}")
print(f"File size: {size_mb:.1f} MB")
print(f"Estimated duration: ~12-15 minutes")
