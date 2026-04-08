"""Sync Canvas course materials to GCS and Vertex AI Search datastores.

Uses the student's authenticated Canvas session (from LDAP login) to download
files, upload to GCS, and create per-course Vertex AI Search datastores.
"""

import os
from datetime import datetime, timezone

import httpx
from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine
from google.cloud import storage

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "csnavigator-vertex-ai")
GCS_BUCKET = os.getenv("GCS_BUCKET", "ai-agent-csdept-1")
LOCATION = "us"
SUPPORTED_TYPES = {"pdf", "docx", "pptx", "txt", "html"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
CANVAS_API = "https://morganstate.instructure.com/api/v1"


def _extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


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
    files = []
    url = f"{CANVAS_API}/courses/{course_id}/files?per_page=100"
    while url:
        resp = await canvas_client.get(url)
        resp.raise_for_status()
        files.extend(resp.json())
        url = None
        for part in resp.headers.get("Link", "").split(","):
            if 'rel="next"' in part:
                url = part.split("<")[1].split(">")[0]

    gcs_client = storage.Client()
    bucket = gcs_client.bucket(GCS_BUCKET)

    uploaded = 0
    skipped = []

    for f in files:
        name = f.get("display_name", "")
        ext = _extension(name)
        size = f.get("size", 0)

        if ext not in SUPPORTED_TYPES:
            skipped.append(f"Unsupported type: {name}")
            continue
        if size > MAX_FILE_SIZE:
            skipped.append(f"Too large: {name}")
            continue

        dl_resp = await canvas_client.get(f["url"], follow_redirects=True)
        if dl_resp.status_code != 200:
            skipped.append(f"Download failed: {name}")
            continue
        if len(dl_resp.content) > MAX_FILE_SIZE:
            skipped.append(f"Too large after download: {name}")
            continue

        blob_path = f"course_files/{course_id}/{name}"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(dl_resp.content)
        uploaded += 1

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
    client_options = ClientOptions(api_endpoint=f"{LOCATION}-discoveryengine.googleapis.com")
    client = discoveryengine.DataStoreServiceClient(client_options=client_options)
    parent = f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection"
    ds_id = f"canvas-course-{course_id}"
    full_name = f"{parent}/dataStores/{ds_id}"

    try:
        client.get_data_store(name=full_name)
        return ds_id
    except Exception:
        pass

    ds = discoveryengine.DataStore(
        display_name=f"Canvas: {course_name}",
        industry_vertical=discoveryengine.IndustryVertical.GENERIC,
        solution_types=[discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH],
        content_config=discoveryengine.DataStore.ContentConfig.CONTENT_REQUIRED,
    )

    op = client.create_data_store(
        parent=parent,
        data_store=ds,
        data_store_id=ds_id,
    )
    op.result(timeout=120)
    return ds_id


def import_documents(course_id: str) -> str:
    """Import documents from GCS into a course's datastore.

    Returns the operation name for status checking.
    """
    client_options = ClientOptions(api_endpoint=f"{LOCATION}-discoveryengine.googleapis.com")
    client = discoveryengine.DocumentServiceClient(client_options=client_options)
    ds_id = f"canvas-course-{course_id}"
    parent = (
        f"projects/{PROJECT_ID}/locations/{LOCATION}"
        f"/collections/default_collection/dataStores/{ds_id}/branches/default_branch"
    )

    gcs_source = discoveryengine.GcsSource(
        input_uris=[f"gs://{GCS_BUCKET}/course_files/{course_id}/*"],
        data_schema="content",
    )

    op = client.import_documents(
        request=discoveryengine.ImportDocumentsRequest(
            parent=parent,
            gcs_source=gcs_source,
            reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
        )
    )
    return op.operation.name
