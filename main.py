from fastapi import FastAPI, HTTPException
from typing import Any, Dict
import tempfile
import json
import os
from rag_lite import enrich_payload_with_rag

app = FastAPI()

@app.post("/optimize_sql")
async def optimize_sql(payload: Dict[str, Any], max_context_tokens: int = 200000):
    try:
        print("Received payload:", payload)
        
        # Save incoming payload to a temp file
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp_file:
            json.dump(payload, temp_file, indent=2)
            temp_file_path = temp_file.name

        # Enrich payload with RAG-lite (now with max_context_tokens parameter)
        enrich_payload_with_rag(temp_file_path, max_context_tokens=max_context_tokens)

        # Read back the enriched payload
        with open(temp_file_path, 'r') as f:
            enriched_payload = json.load(f)

        # Clean up temp file
        os.unlink(temp_file_path)
        
        print("Enriched payload:", enriched_payload)
        return {"enriched_payload": enriched_payload}
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=str(e))