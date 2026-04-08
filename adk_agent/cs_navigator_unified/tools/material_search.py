"""Course material search using Vertex AI Discovery Engine.

Datastores are created dynamically per-course by the material sync endpoint,
so we query Discovery Engine directly instead of using VertexAiSearchTool.
"""

import os

from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "csnavigator-vertex-ai")
LOCATION = "us"


def search_course_materials(query: str, course_id: str) -> dict:
    """Search a course's synced materials for relevant content.

    Args:
        query: The search query (e.g., "binary search trees").
        course_id: The Canvas course ID whose datastore to search.

    Returns:
        Dict with status, results list, and result_count.
    """
    ds_id = f"canvas-course-{course_id}"
    serving_config = (
        f"projects/{PROJECT_ID}/locations/{LOCATION}"
        f"/collections/default_collection/dataStores/{ds_id}"
        f"/servingConfigs/default_serving_config"
    )

    client_options = ClientOptions(
        api_endpoint=f"{LOCATION}-discoveryengine.googleapis.com"
    )
    client = discoveryengine.SearchServiceClient(client_options=client_options)

    content_spec = discoveryengine.SearchRequest.ContentSearchSpec(
        snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
            return_snippet=True,
        ),
        extractive_content_spec=discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
            max_extractive_answer_count=3,
        ),
    )

    try:
        response = client.search(
            request=discoveryengine.SearchRequest(
                serving_config=serving_config,
                query=query,
                page_size=5,
                content_search_spec=content_spec,
            )
        )
    except Exception as e:
        if "NOT_FOUND" in str(e):
            return {
                "status": "not_synced",
                "message": f"Course {course_id} materials haven't been synced yet.",
                "results": [],
                "result_count": 0,
            }
        raise

    results = []
    for result in response.results:
        doc = result.document
        data = dict(doc.derived_struct_data) if doc.derived_struct_data else {}
        results.append({
            "title": data.get("title", "Unknown"),
            "snippets": [s.get("snippet", "") for s in data.get("snippets", [])],
            "extractive_answers": [
                a.get("content", "") for a in data.get("extractive_answers", [])
            ],
        })

    return {
        "status": "ok",
        "results": results,
        "result_count": len(results),
    }
