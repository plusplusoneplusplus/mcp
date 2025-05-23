import os
import tempfile
import shutil
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from utils.vector_store.markdown_segmenter import MarkdownSegmenter
from utils.vector_store.vector_store import ChromaVectorStore

async def api_import_knowledge(request: Request):
    form = await request.form()
    files = form.getlist("files")
    collection = form.get("collection") or "default"
    overwrite = form.get("overwrite") == "true"
    if not files:
        return JSONResponse({"success": False, "error": "No files uploaded."}, status_code=400)

    if overwrite:
        # Delete the collection before importing
        try:
            store = ChromaVectorStore(persist_directory=PERSIST_DIR)
            store.client.delete_collection(collection)
        except Exception as e:
            # If collection doesn't exist, ignore
            pass

    temp_dir = tempfile.mkdtemp(prefix="import_know_")
    try:
        filepaths = []
        for upload in files:
            rel_path = getattr(upload, "filename", None) or getattr(upload, "name", None)
            if not rel_path:
                continue
            dest_path = os.path.join(temp_dir, rel_path)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "wb") as f:
                content = await upload.read()
                f.write(content)
            filepaths.append(dest_path)
        md_files = [f for f in filepaths if f.lower().endswith(".md")]
        if not md_files:
            return JSONResponse({"success": False, "error": "No markdown files found in upload."}, status_code=400)
        vector_store = ChromaVectorStore(collection_name=collection, persist_directory=PERSIST_DIR)
        segmenter = MarkdownSegmenter(vector_store)
        total = 0
        for md_path in md_files:
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
            stat = os.stat(md_path)
            file_name = os.path.basename(md_path)
            rel_path = os.path.relpath(md_path, temp_dir)
            file_size = stat.st_size
            import datetime
            file_date = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
            n, _ = segmenter.segment_and_store(content, file_name=file_name, rel_path=rel_path, file_size=file_size, file_date=file_date)
            total += n
        return JSONResponse({
            "success": True,
            "imported_files": len(md_files),
            "total_segments": total
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

from starlette.responses import JSONResponse

PERSIST_DIR = os.path.join(os.path.dirname(__file__), ".vector_store")

async def api_list_collections(request: Request):
    store = ChromaVectorStore(persist_directory=PERSIST_DIR)
    collections = store.list_collections()
    return JSONResponse({"collections": collections})

async def api_list_documents(request: Request):
    collection = request.query_params.get("collection")
    if not collection:
        return JSONResponse({"error": "Missing collection parameter."}, status_code=400)
    store = ChromaVectorStore(collection_name=collection, persist_directory=PERSIST_DIR)
    # ChromaDB does not have a direct 'list all' method, so we use a hack: query all with a dummy vector
    # We'll use a zero-vector of the correct dimension (assume 384 for MiniLM)
    try:
        dummy_vec = [[0.0]*384]
        results = store.collection.query(query_embeddings=dummy_vec, n_results=1000)
        # Return ids, documents, metadatas
        return JSONResponse({
            "ids": results.get("ids", [[]])[0],
            "documents": results.get("documents", [[]])[0],
            "metadatas": results.get("metadatas", [[]])[0],
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

from sentence_transformers import SentenceTransformer
import numpy as np

async def api_query_segments(request: Request):
    collection = request.query_params.get("collection")
    query_text = request.query_params.get("query")
    try:
        limit = int(request.query_params.get("limit", 3))
    except Exception:
        limit = 3
    if not collection or not query_text:
        return JSONResponse({"error": "Missing collection or query parameter."}, status_code=400)
    try:
        embedder = SentenceTransformer("all-MiniLM-L6-v2")
        query_vec = embedder.encode([query_text]).tolist()
        store = ChromaVectorStore(collection_name=collection, persist_directory=PERSIST_DIR)
        results = store.collection.query(query_embeddings=query_vec, n_results=limit)
        # Chroma returns lists of lists for ids, docs, etc.
        return JSONResponse({
            "ids": results.get("ids", [[]])[0],
            "documents": results.get("documents", [[]])[0],
            "metadatas": results.get("metadatas", [[]])[0],
            "distances": results.get("distances", [[]])[0],
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

async def api_delete_collection(request: Request):
    try:
        data = await request.json()
        collection = data.get("collection")
        if not collection:
            return JSONResponse({"success": False, "error": "Missing collection name."}, status_code=400)
        store = ChromaVectorStore(persist_directory=PERSIST_DIR)
        # ChromaDB API: delete_collection
        store.client.delete_collection(collection)
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

api_routes = [
    Route("/api/import-knowledge", endpoint=api_import_knowledge, methods=["POST"]),
    Route("/api/collections", endpoint=api_list_collections, methods=["GET"]),
    Route("/api/collection-documents", endpoint=api_list_documents, methods=["GET"]),
    Route("/api/query-segments", endpoint=api_query_segments, methods=["GET"]),
    Route("/api/delete-collection", endpoint=api_delete_collection, methods=["POST"]),
]
