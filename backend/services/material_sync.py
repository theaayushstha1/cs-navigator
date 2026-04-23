"""Sync Canvas course materials to GCS and Vertex AI Search datastores.

Uses the student's authenticated Canvas session (from LDAP login) to download
files, upload to GCS, and create per-course Vertex AI Search datastores.
"""

import asyncio
import logging
import os
import re

import httpx
from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine
from google.cloud import storage

logger = logging.getLogger(__name__)

# Production defaults preserved so Cloud Run deploys that only set
# GOOGLE_CLOUD_PROJECT continue to work. Override via env in dev or other envs.
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "csnavigator-vertex-ai")
GCS_BUCKET = os.getenv("GCS_BUCKET", "ai-agent-csdept-1")
LOCATION = os.getenv("DISCOVERY_ENGINE_LOCATION", "us")
SUPPORTED_TYPES = {"pdf", "docx", "pptx", "txt", "html"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
CANVAS_API = "https://morganstate.instructure.com/api/v1"

# Allowed characters for path segments derived from user/course input.
_SAFE_SEGMENT_RE = re.compile(r"[^A-Za-z0-9._\-]")


def _extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _safe_segment(value) -> str:
    """Sanitize a value for use inside a GCS object path or datastore ID."""
    s = str(value) if value is not None else ""
    # Strip directory traversal and any path separators.
    s = s.replace("\\", "/").split("/")[-1]
    s = _SAFE_SEGMENT_RE.sub("_", s)
    # Disallow leading dots so we cannot produce "." or "..".
    s = s.lstrip(".")
    return s or "unknown"


def _require_config() -> None:
    # Defaults above are non-empty, so these will only ever trip if an operator
    # explicitly sets the env var to an empty string.
    if not PROJECT_ID:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT env var is empty")
    if not GCS_BUCKET:
        raise RuntimeError("GCS_BUCKET env var is empty")


async def sync_course_files(
    canvas_client: httpx.AsyncClient,
    course_id: int,
    course_name: str,
) -> dict:
    """Download files from a Canvas course and upload to GCS.

    Args:
        canvas_client: Authenticated httpx client with Canvas session cookies.
        course_id: Canvas course ID.
        course_name: Clean course name for labeling.

    Returns:
        Dict with course_id, course_name, files_uploaded, files_skipped, skip_reasons.
    """
    _require_config()
    safe_course_id = _safe_segment(course_id)

    files = []
    url = f"{CANVAS_API}/courses/{int(course_id)}/files?per_page=100"
    try:
        while url:
            resp = await canvas_client.get(url)
            resp.raise_for_status()
            files.extend(resp.json())
            url = None
            for part in resp.headers.get("Link", "").split(","):
                if 'rel="next"' in part:
                    url = part.split("<")[1].split(">")[0]
    except httpx.HTTPError:
        logger.exception("sync_course_files: Canvas listing failed for course %s", safe_course_id)
        return {
            "course_id": course_id,
            "course_name": course_name,
            "files_uploaded": 0,
            "files_skipped": 0,
            "skip_reasons": ["Canvas listing failed"],
        }

    try:
        gcs_client = await asyncio.to_thread(storage.Client)
        bucket = gcs_client.bucket(GCS_BUCKET)
    except Exception:
        logger.exception("sync_course_files: GCS client init failed")
        return {
            "course_id": course_id,
            "course_name": course_name,
            "files_uploaded": 0,
            "files_skipped": 0,
            "skip_reasons": ["GCS init failed"],
        }

    uploaded = 0
    skipped = []

    for f in files:
        name = f.get("display_name", "") or ""
        ext = _extension(name)
        size = f.get("size", 0)

        if ext not in SUPPORTED_TYPES:
            skipped.append(f"Unsupported type: {name}")
            continue
        if size > MAX_FILE_SIZE:
            skipped.append(f"Too large: {name}")
            continue

        try:
            dl_resp = await canvas_client.get(f["url"], follow_redirects=True)
        except httpx.HTTPError:
            logger.exception("sync_course_files: download error for %s", name)
            skipped.append(f"Download error: {name}")
            continue

        if dl_resp.status_code != 200:
            skipped.append(f"Download failed: {name}")
            continue
        if len(dl_resp.content) > MAX_FILE_SIZE:
            skipped.append(f"Too large after download: {name}")
            continue

        safe_name = _safe_segment(name)
        blob_path = f"course_files/{safe_course_id}/{safe_name}"
        try:
            blob = bucket.blob(blob_path)
            await asyncio.to_thread(blob.upload_from_string, dl_resp.content)
            uploaded += 1
        except Exception:
            logger.exception("sync_course_files: upload failed for %s", blob_path)
            skipped.append(f"Upload failed: {name}")

    return {
        "course_id": course_id,
        "course_name": course_name,
        "files_uploaded": uploaded,
        "files_skipped": len(skipped),
        "skip_reasons": skipped[:10],
    }


def get_or_create_datastore(course_id: str, course_name: str) -> str:
    """Create a Vertex AI Search datastore for a course if it doesn't exist.

    Returns the datastore ID string.
    """
    _require_config()
    safe_course_id = _safe_segment(course_id)

    client_options = ClientOptions(api_endpoint=f"{LOCATION}-discoveryengine.googleapis.com")
    client = discoveryengine.DataStoreServiceClient(client_options=client_options)
    parent = f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection"
    ds_id = f"canvas-course-{safe_course_id}"
    full_name = f"{parent}/dataStores/{ds_id}"

    try:
        client.get_data_store(name=full_name)
        return ds_id
    except Exception as e:
        # Only swallow "not found" style errors; re-raise anything else.
        msg = str(e).lower()
        if "not found" not in msg and "notfound" not in msg and "404" not in msg:
            logger.exception("get_or_create_datastore: unexpected get_data_store error")
            raise

    ds = discoveryengine.DataStore(
        display_name=f"Canvas: {course_name}",
        industry_vertical=discoveryengine.IndustryVertical.GENERIC,
        solution_types=[discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH],
        content_config=discoveryengine.DataStore.ContentConfig.CONTENT_REQUIRED,
    )

    try:
        op = client.create_data_store(
            parent=parent,
            data_store=ds,
            data_store_id=ds_id,
        )
        op.result(timeout=120)
    except Exception:
        logger.exception("get_or_create_datastore: create_data_store failed for %s", ds_id)
        raise
    return ds_id


def import_documents(course_id: str) -> str:
    """Import documents from GCS into a course's datastore.

    Returns the operation name for status checking.
    """
    _require_config()
    safe_course_id = _safe_segment(course_id)

    client_options = ClientOptions(api_endpoint=f"{LOCATION}-discoveryengine.googleapis.com")
    client = discoveryengine.DocumentServiceClient(client_options=client_options)
    ds_id = f"canvas-course-{safe_course_id}"
    parent = (
        f"projects/{PROJECT_ID}/locations/{LOCATION}"
        f"/collections/default_collection/dataStores/{ds_id}/branches/default_branch"
    )

    gcs_source = discoveryengine.GcsSource(
        input_uris=[f"gs://{GCS_BUCKET}/course_files/{safe_course_id}/*"],
        data_schema="content",
    )

    try:
        op = client.import_documents(
            request=discoveryengine.ImportDocumentsRequest(
                parent=parent,
                gcs_source=gcs_source,
                reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
            )
        )
    except Exception:
        logger.exception("import_documents: import_documents call failed for %s", ds_id)
        raise
    return op.operation.name
