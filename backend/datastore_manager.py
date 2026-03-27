"""
Vertex AI Search Datastore Manager
====================================
Manages documents in the Google Cloud Vertex AI Search datastore.
Supports listing, uploading, deleting, and previewing documents.
Uses GCS as staging for uploads, then triggers datastore import.
"""

import os
import io
import time
import threading
from typing import Optional
from google.cloud import storage
from google.cloud import discoveryengine_v1 as discoveryengine
from google.api_core.client_options import ClientOptions

# Configuration from environment
GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "csnavigator-vertex-ai")
GCS_BUCKET_NAME = os.getenv("GCS_KB_BUCKET", "csnavigator-unified-kb")
DATASTORE_ID = os.getenv(
    "VERTEX_AI_DATASTORE_ID",
    "projects/csnavigator-vertex-ai/locations/us/collections/default_collection/dataStores/csnavigator-unified-kb-v4"
)

# Extract location from datastore ID (e.g., "us" from ".../locations/us/...")
_ds_parts = DATASTORE_ID.split("/")
LOCATION = _ds_parts[_ds_parts.index("locations") + 1] if "locations" in _ds_parts else "us"

# Regional endpoint for Discovery Engine
API_ENDPOINT = f"{LOCATION}-discoveryengine.googleapis.com"

BRANCH = f"{DATASTORE_ID}/branches/default_branch"
GCS_PREFIX = "v4_split/"

# In-memory content cache for fast search (avoids re-downloading from GCS)
_content_cache = {}  # {blob_name: (content_text, timestamp)}
_content_cache_lock = threading.Lock()
_CONTENT_CACHE_TTL = 300  # 5 minutes


def _get_cached_contents() -> dict:
    """Get all KB document contents, using in-memory cache when fresh."""
    now = time.time()
    with _content_cache_lock:
        # Check if cache is still fresh
        if _content_cache and all(now - ts < _CONTENT_CACHE_TTL for _, ts in _content_cache.values()):
            return {k: v[0] for k, v in _content_cache.items()}

    # Cache miss or stale: re-download all docs
    storage_client = _get_storage_client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blobs = list(bucket.list_blobs(prefix=GCS_PREFIX))

    new_cache = {}
    for blob in blobs:
        if not blob.name.endswith(('.txt', '.json', '.csv', '.html')):
            continue
        try:
            content = blob.download_as_text(encoding="utf-8")
            new_cache[blob.name] = (content, now)
        except Exception:
            continue

    with _content_cache_lock:
        _content_cache.clear()
        _content_cache.update(new_cache)

    return {k: v[0] for k, v in new_cache.items()}


def invalidate_content_cache():
    """Clear the content cache (call after uploads/edits/deletes)."""
    with _content_cache_lock:
        _content_cache.clear()


def _get_doc_client():
    options = ClientOptions(api_endpoint=API_ENDPOINT)
    return discoveryengine.DocumentServiceClient(client_options=options)


def _get_storage_client():
    return storage.Client(project=GCP_PROJECT)


def list_datastore_documents() -> list[dict]:
    """List all documents in the Vertex AI datastore with GCS metadata.
    Runs GCS and Discovery Engine API calls in parallel for speed."""
    import time
    from concurrent.futures import ThreadPoolExecutor

    start = time.time()
    client = _get_doc_client()
    storage_client = _get_storage_client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)

    # Run both API calls in parallel
    def fetch_gcs_metadata():
        meta = {}
        try:
            for blob in bucket.list_blobs():
                meta[blob.name] = {
                    "size": blob.size or 0,
                    "modified": blob.updated.isoformat() if blob.updated else "",
                }
        except Exception:
            pass
        return meta

    def fetch_datastore_docs():
        request = discoveryengine.ListDocumentsRequest(parent=BRANCH, page_size=100)
        return list(client.list_documents(request=request))

    with ThreadPoolExecutor(max_workers=2) as executor:
        gcs_future = executor.submit(fetch_gcs_metadata)
        docs_future = executor.submit(fetch_datastore_docs)
        gcs_metadata = gcs_future.result()
        raw_docs = docs_future.result()

    docs = []
    for doc in raw_docs:
        doc_id = doc.name.split("/")[-1]
        uri = doc.content.uri if doc.content and doc.content.uri else ""
        filename = uri.split("/")[-1] if uri else doc_id

        size = 0
        modified = ""
        if uri and uri.startswith("gs://"):
            blob_path = uri.replace(f"gs://{GCS_BUCKET_NAME}/", "")
            meta = gcs_metadata.get(blob_path, {})
            size = meta.get("size", 0)
            modified = meta.get("modified", "")

        docs.append({
            "id": doc_id,
            "filename": filename,
            "uri": uri,
            "size": size,
            "modified": modified,
        })

    result = sorted(docs, key=lambda d: d["filename"])
    print(f"[PERF] list_datastore_documents: {time.time()-start:.1f}s ({len(result)} docs)")
    return result


def get_document_content(doc_uri: str, max_chars: int = 50000) -> str:
    """Read the content of a document from GCS."""
    if not doc_uri.startswith("gs://"):
        return "Cannot read: not a GCS URI"

    storage_client = _get_storage_client()
    blob_path = doc_uri.replace(f"gs://{GCS_BUCKET_NAME}/", "")
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(blob_path)

    try:
        content = blob.download_as_text(encoding="utf-8")
        return content[:max_chars]
    except Exception as e:
        return f"Error reading file: {e}"


def search_documents(query: str) -> list[dict]:
    """Fast word-boundary search across KB documents using in-memory cache.
    Uses regex word boundaries so 'office' won't match 'officer' or 'unofficial'.
    First search downloads from GCS (~3s), subsequent searches are instant (<50ms)."""
    import re
    cached_contents = _get_cached_contents()

    results = []
    query_lower = query.lower().strip()
    if not query_lower:
        return results

    # Build word-boundary regex for accurate matching
    escaped = re.escape(query_lower)
    pattern = re.compile(r'\b' + escaped + r'\b', re.IGNORECASE)

    for blob_name, content in cached_contents.items():
        matches = pattern.findall(content)
        match_count = len(matches)

        if match_count == 0:
            continue

        # Get context snippet around first match
        m = pattern.search(content)
        snippet = ""
        if m:
            idx = m.start()
            start = max(0, idx - 80)
            end = min(len(content), idx + len(query) + 80)
            snippet = content[start:end].strip()
            if start > 0:
                snippet = "..." + snippet
            if end < len(content):
                snippet = snippet + "..."

        results.append({
            "filename": blob_name.split("/")[-1],
            "blob_path": blob_name,
            "uri": f"gs://{GCS_BUCKET_NAME}/{blob_name}",
            "match_count": match_count,
            "snippet": snippet,
            "size": len(content),
        })

    return sorted(results, key=lambda r: r["match_count"], reverse=True)


def upload_document(filename: str, content: bytes, content_type: str = "text/plain") -> dict:
    """
    Upload a document to GCS and import it into the datastore.
    Returns status dict with success/error info.
    """
    storage_client = _get_storage_client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)

    # Upload to GCS
    blob_path = f"{GCS_PREFIX}{filename}"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(content, content_type=content_type)
    gcs_uri = f"gs://{GCS_BUCKET_NAME}/{blob_path}"

    # Import into datastore
    invalidate_content_cache()
    try:
        _import_gcs_documents([gcs_uri])
        return {"success": True, "uri": gcs_uri, "message": f"Uploaded and imported: {filename}"}
    except Exception as e:
        return {"success": False, "uri": gcs_uri, "message": f"Uploaded to GCS but import failed: {e}"}


def delete_document(doc_id: str, doc_uri: str = "") -> dict:
    """Delete a document from the datastore and optionally from GCS."""
    client = _get_doc_client()
    doc_name = f"{BRANCH}/documents/{doc_id}"

    try:
        client.delete_document(name=doc_name)
    except Exception as e:
        return {"success": False, "message": f"Failed to delete from datastore: {e}"}

    # Also delete from GCS if URI provided
    if doc_uri and doc_uri.startswith("gs://"):
        try:
            storage_client = _get_storage_client()
            blob_path = doc_uri.replace(f"gs://{GCS_BUCKET_NAME}/", "")
            bucket = storage_client.bucket(GCS_BUCKET_NAME)
            blob = bucket.blob(blob_path)
            blob.delete()
        except Exception:
            pass  # GCS delete is best-effort

    invalidate_content_cache()
    return {"success": True, "message": f"Document {doc_id} deleted"}


def update_document(doc_uri: str, content: bytes, content_type: str = "text/plain") -> dict:
    """Update a document: write new content to GCS, delete old index entry,
    then re-import so Vertex AI Search picks up the new content.
    This is non-disruptive: only the edited doc is briefly unavailable (~30s),
    all other docs remain fully searchable."""
    if not doc_uri.startswith("gs://"):
        return {"success": False, "message": "Not a GCS URI"}

    storage_client = _get_storage_client()
    blob_path = doc_uri.replace(f"gs://{GCS_BUCKET_NAME}/", "")
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(blob_path)

    try:
        blob.upload_from_string(content, content_type=content_type)
    except Exception as e:
        return {"success": False, "message": f"Failed to update in GCS: {e}"}

    invalidate_content_cache()

    # Delete the old doc from the index so INCREMENTAL re-import picks up the new content
    try:
        client = _get_doc_client()
        blob_name = blob_path.split("/")[-1].replace(".", "_")
        doc_name = f"{BRANCH}/documents/{blob_name}"
        try:
            client.delete_document(name=doc_name)
        except Exception:
            pass  # May not exist with this ID, that's fine

        # Re-import just this one doc (creates fresh index entry with new content)
        _import_gcs_documents([doc_uri])
        return {"success": True, "message": f"Updated and re-indexed: {blob_path}"}
    except Exception as e:
        return {"success": True, "message": f"Updated in GCS but re-index delayed: {e}"}


def sync_datastore() -> dict:
    """Re-import all documents from GCS bucket into the datastore."""
    invalidate_content_cache()
    gcs_uri = f"gs://{GCS_BUCKET_NAME}/{GCS_PREFIX}"
    try:
        operation = _import_gcs_documents_bulk(gcs_uri)
        return {"success": True, "message": "Sync started. Documents will be re-indexed shortly.", "operation": str(operation)}
    except Exception as e:
        return {"success": False, "message": f"Sync failed: {e}"}


def _import_gcs_documents(gcs_uris: list[str]):
    """Import specific GCS documents into the datastore."""
    options = ClientOptions(api_endpoint=API_ENDPOINT)
    client = discoveryengine.DocumentServiceClient(client_options=options)

    for uri in gcs_uris:
        blob_name = uri.split("/")[-1].replace(".", "_")
        doc_name = f"{BRANCH}/documents/{blob_name}"

        doc = discoveryengine.Document(
            name=doc_name,
            content=discoveryengine.Document.Content(
                uri=uri,
                mime_type="text/plain",
            ),
        )

        try:
            # Try to update existing document first
            request = discoveryengine.UpdateDocumentRequest(
                document=doc,
                allow_missing=True,  # Creates if doesn't exist
            )
            client.update_document(request=request)
        except Exception as e:
            # Fallback: create new document
            try:
                request = discoveryengine.CreateDocumentRequest(
                    parent=BRANCH,
                    document=doc,
                    document_id=blob_name,
                )
                client.create_document(request=request)
            except Exception as e2:
                raise RuntimeError(f"Failed to import {uri}: {e2}")


def _import_gcs_documents_bulk(gcs_prefix: str):
    """Bulk import all documents from a GCS prefix."""
    options = ClientOptions(api_endpoint=API_ENDPOINT)
    client = discoveryengine.DocumentServiceClient(client_options=options)

    request = discoveryengine.ImportDocumentsRequest(
        parent=BRANCH,
        gcs_source=discoveryengine.GcsSource(
            input_uris=[f"{gcs_prefix}*"],
            data_schema="content",
        ),
        reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
    )

    operation = client.import_documents(request=request)
    return operation
