"""Sync course materials via the backend API.

The backend handles Canvas auth (student's LDAP session) and GCS upload.
This tool is a thin wrapper that calls the backend endpoint.
"""

import os
import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:5000")


async def sync_course_materials(course_id: int, course_name: str) -> dict:
    """Sync a Canvas course's files to GCS and create a search datastore.

    Downloads the course's files via the backend (which has the student's
    Canvas session), uploads to GCS, and creates a Vertex AI Search datastore.

    Args:
        course_id: The Canvas course ID to sync.
        course_name: The clean course name (e.g., 'COSC 251').
    """
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{BACKEND_URL}/api/canvas/sync-materials",
                json={"course_id": course_id, "course_name": course_name},
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "status": data.get("status", "error"),
                "files_uploaded": data.get("sync_result", {}).get("files_uploaded", 0),
                "datastore_id": data.get("datastore_id", ""),
                "message": (
                    f"Synced {data.get('sync_result', {}).get('files_uploaded', 0)} files "
                    f"for {course_name}. Indexing in progress."
                ),
            }
    except httpx.HTTPStatusError as e:
        return {
            "status": "error",
            "message": f"Sync failed: {e.response.text}",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Sync failed: {str(e)}",
        }
