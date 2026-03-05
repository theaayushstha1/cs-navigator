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
from typing import Optional
from google.cloud import storage
from google.cloud import discoveryengine_v1 as discoveryengine
from google.api_core.client_options import ClientOptions

# Configuration from environment
GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "csnavigator-vertex-ai")
GCS_BUCKET_NAME = os.getenv("GCS_KB_BUCKET", "csnavigator-kb-2026")
DATASTORE_ID = os.getenv(
    "VERTEX_AI_DATASTORE_ID",
    "projects/csnavigator-vertex-ai/locations/us/collections/default_collection/dataStores/csnavigator-kb-uscentral_1768951850167"
)

# Extract location from datastore ID (e.g., "us" from ".../locations/us/...")
_ds_parts = DATASTORE_ID.split("/")
LOCATION = _ds_parts[_ds_parts.index("locations") + 1] if "locations" in _ds_parts else "us"

# Regional endpoint for Discovery Engine
API_ENDPOINT = f"{LOCATION}-discoveryengine.googleapis.com"

BRANCH = f"{DATASTORE_ID}/branches/default_branch"
GCS_PREFIX = "MSU_Knowledge_Base/"


def _get_doc_client():
    options = ClientOptions(api_endpoint=API_ENDPOINT)
    return discoveryengine.DocumentServiceClient(client_options=options)


def _get_storage_client():
    return storage.Client(project=GCP_PROJECT)


def list_datastore_documents() -> list[dict]:
    """List all documents in the Vertex AI datastore with their GCS metadata."""
    client = _get_doc_client()
    storage_client = _get_storage_client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)

    request = discoveryengine.ListDocumentsRequest(parent=BRANCH, page_size=100)
    docs = []

    for doc in client.list_documents(request=request):
        doc_id = doc.name.split("/")[-1]
        uri = doc.content.uri if doc.content and doc.content.uri else ""
        filename = uri.split("/")[-1] if uri else doc_id

        # Get file size from GCS
        size = 0
        modified = ""
        if uri and uri.startswith("gs://"):
            blob_path = uri.replace(f"gs://{GCS_BUCKET_NAME}/", "")
            blob = bucket.blob(blob_path)
            try:
                blob.reload()
                size = blob.size or 0
                modified = blob.updated.isoformat() if blob.updated else ""
            except Exception:
                pass

        docs.append({
            "id": doc_id,
            "filename": filename,
            "uri": uri,
            "size": size,
            "modified": modified,
        })

    return sorted(docs, key=lambda d: d["filename"])


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
    """Search across all GCS documents for a query string (case-insensitive)."""
    storage_client = _get_storage_client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blobs = list(bucket.list_blobs())

    results = []
    query_lower = query.lower()

    for blob in blobs:
        try:
            content = blob.download_as_text(encoding="utf-8")
        except Exception:
            continue

        content_lower = content.lower()
        if query_lower not in content_lower:
            continue

        # Count matches
        match_count = content_lower.count(query_lower)

        # Get context snippet around first match
        idx = content_lower.find(query_lower)
        start = max(0, idx - 60)
        end = min(len(content), idx + len(query) + 60)
        snippet = content[start:end]

        results.append({
            "filename": blob.name.split("/")[-1],
            "blob_path": blob.name,
            "uri": f"gs://{GCS_BUCKET_NAME}/{blob.name}",
            "match_count": match_count,
            "snippet": snippet,
            "size": blob.size or 0,
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

    return {"success": True, "message": f"Document {doc_id} deleted"}


def update_document(doc_uri: str, content: bytes, content_type: str = "text/plain") -> dict:
    """Update an existing document's content in GCS and re-import."""
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

    # Re-import to update datastore index
    try:
        _import_gcs_documents([doc_uri])
        return {"success": True, "message": f"Updated and re-imported: {blob_path}"}
    except Exception as e:
        return {"success": True, "message": f"Updated in GCS but re-import failed (will sync eventually): {e}"}


def sync_datastore() -> dict:
    """Re-import all documents from GCS bucket into the datastore."""
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
