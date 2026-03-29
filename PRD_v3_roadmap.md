# CS Navigator v3.0 - Product Requirements Document

**Author:** Aayush Shrestha
**Date:** March 27, 2026
**Status:** Planning
**Current Version:** v2.2 (Multi-tier caching, Vertex AI Search, ADK Agent)

---

## Executive Summary

Upgrade CS Navigator from unstructured text files with workaround versioning to a structured Vertex AI Search datastore with instant document updates, migrate user auth from AWS RDS to Firebase, and ingest new department data provided by Dr. Guo.

---

## 1. Structured Datastore Migration

### Problem
The current system uses **unstructured plain text files** in GCS. Vertex AI Search's INCREMENTAL mode won't re-crawl files with unchanged URIs, forcing a workaround where we create versioned copies (`faculty_v{timestamp}.txt`) on every edit. This creates redundancy, cleanup complexity, and ~13 second indexing delays.

### Goal
Migrate all 45 KB files to **structured JSON documents** in Vertex AI Search. Structured datastores support `UpdateDocumentRequest` with inline content, meaning edits are indexed instantly with no versioning workaround needed.

### Current State
- 45 text/JSON files in `gs://csnavigator-unified-kb/v4_split/`
- Unstructured datastore: `csnavigator-unified-kb-v4`
- Search via Discovery Engine API (full-text + semantic)
- Versioned file workaround for updates (~13s delay)

### Target State
- Structured JSON documents in Vertex AI Search
- Each document has defined fields (title, content, category, metadata)
- `UpdateDocumentRequest` with `struct_data` for instant updates
- No versioned files, no GCS intermediary for index updates
- Admin dashboard reads/writes directly to the structured datastore

### Schema Design

```json
{
  "doc_id": "academic_faculty",
  "title": "Computer Science Faculty Directory",
  "category": "academic|career|financial|general",
  "subcategory": "faculty|courses|advising|etc",
  "content": "Full text content of the document...",
  "last_updated": "2026-03-27T00:00:00Z",
  "updated_by": "admin@morgan.edu",
  "tags": ["faculty", "research", "contact"],
  "version": 1
}
```

### Implementation Steps

1. **Design the JSON schema** for all document categories
   - Academic (faculty, courses, degrees, advising, tracks)
   - Career (internships, resources, organizations)
   - Financial (aid, scholarships, tuition, housing)
   - General (department info, leadership, calendar, forms)

2. **Create a migration script** (`migrate_to_structured.py`)
   - Read all 45 current text files from GCS
   - Parse each into the structured JSON schema
   - Create a NEW structured datastore in Vertex AI Search
   - Import all documents via `ImportDocumentsRequest`
   - Validate search results match current behavior

3. **Update `datastore_manager.py`**
   - Replace `update_document()` with `struct_data` based updates
   - Remove all versioned file logic
   - Remove GCS upload/download for index operations
   - Keep GCS only as a backup/export mechanism

4. **Update ADK agent** (`cs_navigator_unified/agent.py`)
   - Point `VertexAiSearchTool` to the new structured datastore
   - Test that grounding results still include all relevant fields

5. **Update admin dashboard**
   - Remove versioned file filtering
   - Add structured field editing (category, tags, metadata)
   - Show last_updated and updated_by info

### Risks
- Structured search may behave differently than unstructured (relevance ranking)
- Need to test that semantic search quality is preserved
- Migration must be atomic (switch over, not gradual)

### Success Criteria
- Admin saves a doc, chatbot reflects the change in < 5 seconds
- No versioned files in GCS
- Zero duplicate entries in the datastore
- Search quality is equal or better than current

---

## 2. Firebase Auth Migration

### Problem
User authentication currently uses AWS RDS MySQL with bcrypt password hashing and JWT tokens. This works but adds AWS dependency and doesn't support social login, email verification, password reset, or MFA out of the box.

### Goal
Migrate user authentication to **Firebase Authentication** while keeping the existing RDS database for non-auth data (chat history, DegreeWorks, Banner, support tickets).

### Current State
- **Database:** AWS RDS MySQL (`cs-navigator-db.cbh3ertrslsi.us-east-1.rds.amazonaws.com`)
- **Tables:** `users` (email, password_hash, role, profile fields)
- **Auth flow:** Register -> bcrypt hash -> JWT token (HS256, 4hr expiry)
- **No:** Email verification, password reset, social login, MFA

### Target State
- **Firebase Auth** handles: registration, login, password reset, email verification
- **RDS** keeps: chat_history, degreeworks_data, banner_student_data, feedback, support_tickets
- **User link:** Firebase UID stored in RDS `users.firebase_uid` column
- **Frontend:** Firebase SDK for auth UI, token refresh
- **Backend:** Verify Firebase ID tokens instead of custom JWT

### Implementation Steps

1. **Set up Firebase project**
   - Enable Email/Password provider
   - Enable Google Sign-In (optional, Morgan State Google accounts)
   - Configure authorized domains

2. **Backend changes**
   - Add `firebase-admin` to requirements
   - Create `firebase_auth.py` middleware
   - Replace `get_current_user()` dependency to verify Firebase ID tokens
   - Add migration endpoint to link existing users to Firebase accounts
   - Add `firebase_uid` column to `users` table

3. **Frontend changes**
   - Install `firebase` SDK
   - Replace custom login/register forms with Firebase Auth
   - Use `onAuthStateChanged` for session management
   - Send Firebase ID token in `Authorization` header

4. **Data migration**
   - Export existing users from RDS
   - Bulk import into Firebase Auth (email + generated password)
   - Send password reset emails to all existing users
   - Map Firebase UIDs back to RDS user records

5. **Rollback plan**
   - Keep JWT auth as fallback for 2 weeks
   - Backend accepts both Firebase tokens and legacy JWTs during transition
   - Feature flag to switch auth provider

### Risks
- Existing users need to reset passwords (Firebase can't import bcrypt hashes directly without custom claims)
- Morgan State may have SSO/SAML requirements for institutional login
- Firebase free tier: 50K monthly active users (sufficient for CS department)

### Success Criteria
- All existing users can log in via Firebase
- Password reset and email verification work
- No disruption to chat history or DegreeWorks data
- Guest trial flow still works without auth

---

## 3. New Data Ingestion (Dr. Guo's Data)

### Problem
Dr. Guo has provided new department data that needs to be added to the knowledge base. This data needs to be processed, formatted, and ingested into the datastore.

### Goal
Ingest all new data files into the knowledge base, ensuring proper formatting and searchability.

### Implementation Steps

1. **Receive and catalog files from Dr. Guo**
   - Document what files were provided (format, content type)
   - Categorize each file (academic, career, financial, general)
   - Identify what existing KB files need updating vs. new files

2. **Process and format**
   - Convert any PDFs/DOCXs to structured text
   - Split large files into logical sections (one topic per file)
   - Follow existing naming convention: `{category}_{topic}.txt`
   - Ensure natural language format (not raw data tables)

3. **Ingest into datastore**
   - If structured migration (item 1) is done first: import as JSON docs
   - If still unstructured: upload to GCS and trigger import
   - Verify all new content is searchable

4. **Validate**
   - Test queries that should hit the new data
   - Verify no conflicts with existing KB content
   - Check that the agent doesn't hallucinate from partial data

### Data Categories Expected
- [ ] Updated faculty directory (new hires, updated research interests)
- [ ] New course offerings or curriculum changes
- [ ] Updated advising assignments
- [ ] New program tracks or concentrations
- [ ] Department event calendar updates
- [ ] Lab/facility information
- [ ] *Other (TBD based on files received)*

### Dependencies
- Files must be received from Dr. Guo
- Ideally done AFTER structured migration (item 1) for easier ingestion
- Admin review of content accuracy before going live

---

## Priority Order

| # | Task | Effort | Impact | Dependencies |
|---|------|--------|--------|--------------|
| 1 | Structured Datastore Migration | High (1-2 weeks) | High (instant updates, no workarounds) | None |
| 2 | Dr. Guo's Data Ingestion | Medium (2-3 days) | High (fresh, accurate KB) | Better after #1 |
| 3 | Firebase Auth Migration | High (1-2 weeks) | Medium (better UX, social login) | None, can parallel #1 |

---

## Current Architecture Reference

```
Frontend (React 19 + Vite) ──HTTPS──> FastAPI Backend
                                           |
                        ┌──────────────────┼──────────────────┐
                        |                  |                  |
                   AWS RDS MySQL    Google ADK Agent    Redis Cloud
                   (users, chat,    (gemini-2.0-flash   (L2 cache,
                    DegreeWorks,     + VertexAiSearch)    24hr TTL)
                    tickets)              |
                                    Vertex AI Search
                                    (45 unstructured
                                     text files in GCS)
```

---

## Notes

- RDS connection is currently working and stable for auth
- The versioned file approach for updates works but is a workaround
- Structured migration eliminates the need for versioned files entirely
- Firebase migration is independent and can happen in parallel
- Dr. Guo's data should ideally wait for structured migration but can be done anytime
