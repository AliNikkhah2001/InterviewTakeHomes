import argparse, asyncio, json
from typing import List, Dict, Any
from fastapi import FastAPI
from pydantic import BaseModel
from .processing import process_notes

app = FastAPI(title="BizzyCar Applied AI Service", version="0.1.0")

class AnalyzeIn(BaseModel):
    messages: List[str]

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.post("/analyze")
async def analyze(payload: AnalyzeIn):
    out = await process_notes(payload.messages)
    return {"items": out}

def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to JSON with {'messages': [..]}")
    parser.add_argument("--output", required=True, help="Path to write JSON results")
    args = parser.parse_args()
    with open(args.input, "r") as f:
        data = json.load(f)
    msgs = data.get("messages", [])
    out = asyncio.run(process_notes(msgs))
    with open(args.output, "w") as f:
        json.dump({"items": out}, f, indent=2)
    print(f"Wrote {args.output}")

if __name__ == "__main__":
    cli()
