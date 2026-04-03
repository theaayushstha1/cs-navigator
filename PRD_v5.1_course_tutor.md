# CS Navigator v5.1 - Course AI Tutor

**Author:** Aayush Shrestha
**Date:** March 31, 2026
**Status:** Planning
**Current Version:** v5.0-canvas (Model selector, Canvas integration, structured datastore)
**Target Branch:** `version-5.1-course-tutor`

---

## Executive Summary

Build a per-course AI tutor that downloads all course materials (PDFs, slides, lecture notes, syllabus) from Canvas LMS and creates searchable knowledge bases. Students click a course in My Classes and get a dedicated chat that understands their specific course content.

---

## Problem

Students currently use CS Navigator for department-level questions (faculty, requirements, advising). But their most frequent academic needs are course-specific:
- "What did the professor cover in lecture 5?"
- "Help me understand the sorting algorithm from the slides"
- "What are the requirements for homework 3?"
- "What topics will be on the midterm?"

The chatbot can't answer these because it has no access to course materials. Students must manually search through Canvas, download PDFs, and read through them.

---

## Goal

When a student syncs their Canvas account, automatically download all course materials and create per-course searchable knowledge bases. Each course gets a dedicated chat page where the student can ask course-specific questions grounded in the actual lecture notes, slides, assignments, and announcements.

---

## Architecture

### Data Flow

```
Student syncs Canvas (LDAP auth)
        |
        v
Canvas REST API
  |-- /courses/{id}/modules        (course structure)
  |-- /courses/{id}/modules/{}/items (module items)
  |-- /courses/{id}/files           (all files: PDFs, slides, docs)
  |-- /courses/{id}/pages           (wiki pages: syllabus, notes)
  |-- /courses/{id}/announcements   (course announcements)
        |
        v
Download files during sync (LDAP cookies alive)
        |
        v
Google Cloud Storage (shared per-course)
  gs://csnavigator-course-content/courses/{course_id}/
  |-- files/         (raw PDFs, PPTX, DOCX)
  |-- pages/         (HTML pages converted to text)
  |-- manifest.json  (file versions for incremental sync)
        |
        v
Text Extraction Pipeline
  (PDF -> text, DOCX -> text, PPTX -> text, HTML -> text)
  Uses existing backend/text_extractor.py
        |
        v
Per-course Vertex AI Search Datastore
  csnavigator-course-{course_id}
  Documents: extracted text with module/chapter metadata
        |
        v
ADK Agent (search_course_kb function tool)
  Dynamically queries the right per-course datastore
        |
        v
Frontend: /course-chat/{course_id}
  Dedicated chat page scoped to one course
```

### Storage: GCS (Shared Per-Course)

Course files are identical for all enrolled students. No per-student duplication.

```
gs://csnavigator-course-content/
  courses/
    49380/                          # COSC 320 - Algorithms
      files/
        lecture5_sorting.pdf
        homework3.pdf
        midterm_study_guide.docx
      pages/
        syllabus.txt
        grading_policy.txt
      announcements/
        2026-03-15_midterm_reminder.txt
      manifest.json                 # {filename: {updated_at, hash, size}}
    48445/                          # COSC 458 - Software Engineering
      ...
```

**Cost:** ~$0.02/GB/month. A typical course has 50-200MB of materials. 6 courses = ~1GB = $0.02/month.

### Knowledge Base: Per-Course Vertex AI Search

Each course gets its own datastore for clean isolation:

```
Datastore: csnavigator-course-49380
Documents:
  - doc_id: "lecture5_sorting"
    title: "Lecture 5 - Sorting Algorithms"
    content: [extracted text]
    metadata: {module: "Module 3", type: "lecture", file_type: "pdf"}

  - doc_id: "homework3"
    title: "Homework 3 - Graph Algorithms"
    content: [extracted text]
    metadata: {module: "Module 4", type: "assignment", file_type: "pdf"}
```

**Benefits:**
- Clean isolation: no cross-course contamination in search results
- Easy cleanup: delete datastore at semester end
- Existing Discovery Engine API (already used for main KB)

**Cost:** ~$2-5/month per active datastore (search queries). 6 courses = ~$12-30/month.

### Agent: Same Agent + FunctionTool

No new agent or Cloud Run service. Add a Python function tool to the existing agent:

```python
def search_course_kb(course_id: str, query: str) -> str:
    """Search a specific course's knowledge base for relevant content."""
    datastore_id = f"csnavigator-course-{course_id}"
    # Use Discovery Engine API to search
    client = discoveryengine.SearchServiceClient(...)
    request = discoveryengine.SearchRequest(
        serving_config=f".../{datastore_id}/servingConfigs/default_search",
        query=query,
        page_size=5,
    )
    results = client.search(request)
    # Format results as text for the agent
    ...
```

The agent's instruction tells it: "When the user is in a course-specific chat (course_id in session state), use search_course_kb to find answers in that course's materials."

---

## New Canvas API Methods

Add to `backend/canvas_client.py`:

### 1. fetch_course_modules(client, course_id)
```
GET /api/v1/courses/{id}/modules?include[]=items&per_page=50
```
Returns: Module structure with items (pages, files, assignments, quizzes)

### 2. fetch_course_files(client, course_id)
```
GET /api/v1/courses/{id}/files?per_page=100&sort=updated_at
```
Returns: File metadata including download URL, size, content_type, updated_at

### 3. download_file(client, file_url)
```
GET {file_url}  (with Canvas session cookies)
```
Returns: Raw file bytes

### 4. fetch_course_pages(client, course_id)
```
GET /api/v1/courses/{id}/pages?per_page=50
GET /api/v1/courses/{id}/pages/{page_url}  (full content)
```
Returns: Wiki pages with HTML body (syllabus, lecture notes)

### 5. fetch_announcements(client, course_id)
```
GET /api/v1/courses/{id}/discussion_topics?only_announcements=true&per_page=20
```
Returns: Course announcements with message body

---

## Database Model

```python
class CourseKnowledgeBase(Base):
    __tablename__ = "course_knowledge_bases"

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, nullable=False)       # Canvas course ID
    course_name = Column(String(255))                  # "COSC 320 - Algorithms"
    course_code = Column(String(50))                   # "COSC320"
    datastore_id = Column(String(255))                 # Vertex AI Search datastore name
    gcs_path = Column(String(500))                     # gs://bucket/courses/{id}/
    file_count = Column(Integer, default=0)            # Number of files indexed
    total_size_bytes = Column(BigInteger, default=0)   # Total content size
    last_synced = Column(DateTime)
    created_by = Column(Integer, ForeignKey("users.id"))  # First student who synced
    semester = Column(String(20))                      # "Spring 2026"

    # Unique per course (shared across students)
    __table_args__ = (UniqueConstraint('course_id', 'semester'),)
```

---

## Sync Pipeline

### Trigger
Extended Canvas sync flow. When student clicks "Sync Canvas":
1. Existing flow: fetch courses, grades, assignments, missing (current behavior)
2. NEW: for each enrolled course, check if course KB exists
3. If not, or if stale (>24hr), run course content sync

### Per-Course Content Sync
```
1. Fetch file list from Canvas API
2. Compare against GCS manifest.json
3. Download only new/updated files (incremental)
4. Upload to GCS
5. Extract text (text_extractor.py)
6. Create/update Vertex AI Search datastore
7. Update manifest.json
8. Update CourseKnowledgeBase DB record
```

### Progress Streaming
Extend existing SSE progress to include course sync:
```
{"step": "canvas_auth", "message": "Authenticating with Canvas..."}
{"step": "courses", "message": "Fetching 6 courses..."}
{"step": "grades", "message": "Loading grades..."}
{"step": "course_sync", "message": "Syncing COSC 320 materials (12 files)..."}
{"step": "course_sync", "message": "Syncing COSC 458 materials (8 files)..."}
{"step": "indexing", "message": "Indexing course content..."}
{"step": "done", "message": "Canvas sync complete!"}
```

---

## Frontend: Course Chat Page

### Route: `/course-chat/:courseId`

### UI Layout
```
+--------------------------------------------------+
| CS NAVIGATOR  |  COSC 320 - Algorithm Design     |
+--------------------------------------------------+
| [Course Materials]  |  [Chat Area]               |
|                     |                             |
| Module 1            |  Q: Explain merge sort from |
|   lecture1.pdf      |     lecture 5               |
|   notes.txt         |                             |
| Module 2            |  A: Based on the lecture 5  |
|   slides.pptx       |     slides, merge sort...   |
|   homework1.pdf     |                             |
| Module 3            |  Q: What's due this week?   |
|   lecture5.pdf *     |                             |
|   quiz3.pdf         |  A: You have Homework 3 due |
|                     |     Friday Mar 28...        |
+--------------------------------------------------+
| [Type your question about COSC 320...]    [Send] |
+--------------------------------------------------+
```

### Features
- Left sidebar: course materials organized by module
- Click a file to view/download
- Chat grounded in course content + Canvas assignment data
- Course name and instructor shown in header
- Back button to My Classes

---

## API Endpoints

### New Endpoints
```
POST /api/canvas/sync-course/{course_id}   # Sync single course's materials
GET  /api/courses/{course_id}/materials     # List course materials (modules, files)
GET  /api/courses/{course_id}/kb-status     # Check if course KB is ready
POST /api/courses/{course_id}/chat          # Course-specific chat
POST /api/courses/{course_id}/chat/stream   # Course-specific streaming chat
```

### Modified Endpoints
```
POST /api/canvas/sync                       # Extended: also syncs course content
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Cloud Run 5min timeout | Large courses timeout during sync | Stream progress, process async, batch files |
| Canvas cookie expiry mid-download | Sync fails partway | Download smallest files first, checkpoint progress, retry on 401 |
| Vertex AI Search datastore quota | Can't create per-course datastores | Share datastores across students in same course (already planned) |
| Large PDFs (>50MB) | Memory issues, slow extraction | Skip files >50MB, chunk text into sections |
| Professor doesn't use Canvas files | Empty course KB | Show "No course materials available yet" gracefully |
| Text extraction quality | Scanned PDFs, complex slides | Use digital parsing first, fall back to OCR, skip images |
| Cost scaling | Many students × many courses | Shared per-course (not per-student), semester cleanup |

---

## Implementation Phases

### Phase 1: Canvas API Methods (Day 1 morning)
- Add 5 new methods to canvas_client.py
- Test with real Canvas auth against morganstate.instructure.com
- Handle pagination, error codes, file size limits

### Phase 2: GCS Storage Layer (Day 1 afternoon)
- Create GCS bucket and folder structure
- Implement manifest-based incremental sync
- Upload/download helpers

### Phase 3: Content Processing Pipeline (Day 2 morning)
- Text extraction for PDF, DOCX, PPTX, HTML
- Leverage existing text_extractor.py
- Chunk large documents into sections with metadata

### Phase 4: Per-Course Datastore Management (Day 2 afternoon)
- Create/delete Vertex AI Search datastores dynamically
- Document ingestion with module/chapter metadata
- Search function for agent tool

### Phase 5: Extended Canvas Sync (Day 3 morning)
- Integrate course content sync into existing Canvas sync flow
- Database model and migrations
- SSE progress streaming for course sync

### Phase 6: ADK Agent Tool (Day 3 afternoon)
- Add search_course_kb FunctionTool
- Update agent instruction for course-specific context
- Session state with course_id for routing

### Phase 7: Frontend Course Chat (Day 4 morning)
- New CourseChat component
- Course materials sidebar
- Route setup and navigation from My Classes

### Phase 8: Testing & Polish (Day 4 afternoon)
- End-to-end test with real Canvas data
- Performance tuning (lazy-load materials sidebar)
- Error handling and edge cases

---

## Success Criteria

- [ ] Student syncs Canvas and course materials download automatically
- [ ] Each course has a searchable KB with lecture notes, slides, assignments
- [ ] Student can ask course-specific questions and get grounded answers
- [ ] Incremental sync: only new/changed files re-downloaded
- [ ] Course chat loads in <3s
- [ ] Query response time <5s for course-specific questions
- [ ] No cross-course contamination in search results
- [ ] Graceful handling of courses with no materials

---

## Notes

- This builds on v5.0-canvas which already has Canvas LMS integration (courses, grades, assignments)
- The existing `text_extractor.py` handles PDF and DOCX extraction
- Vertex AI Search datastore creation uses the same SDK already in requirements.txt
- GCS bucket `csnavigator-course-content` needs to be created in the `csnavigator-vertex-ai` project
- Consider adding a "Sync Course Materials" button per-course in My Classes for manual trigger
