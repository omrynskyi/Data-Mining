#!/usr/bin/env python3
"""
Regenerates `dashboard/src/data/defaultData.ts` from the current pipeline artifacts.

The dashboard fetches `public/data/*.json` at runtime; this bundled snapshot is the
offline fallback that keeps `npm run build` and the Vitest render suite deterministic
even when the Python pipeline has not been executed yet.

Usage:
    python scripts/generate_default_data.py
"""

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = PROJECT_ROOT / "artifacts"
TARGET = PROJECT_ROOT / "dashboard" / "src" / "data" / "defaultData.ts"

HEADER = """/**
 * Bundled offline snapshot of the CRISP-DM pipeline and autoresearch artifacts.
 *
 * GENERATED FILE - do not edit by hand.
 * Regenerate with:  python scripts/generate_default_data.py
 *
 * The dashboard always prefers the live artifacts served from `public/data/`;
 * this snapshot is the fallback used when those files are unavailable
 * (fresh clone, offline preview, JSDOM test environment).
 */

import type { AutoresearchOutput, PipelineOutput } from '../types';

"""


def main() -> int:
    pipeline_path = ARTIFACTS / "pipeline_output.json"
    autoresearch_path = ARTIFACTS / "autoresearch_output.json"

    if not pipeline_path.exists():
        print(f"error: {pipeline_path} not found - run `python run_pipeline.py` first", file=sys.stderr)
        return 1

    pipeline = json.loads(pipeline_path.read_text(encoding="utf-8"))
    autoresearch = (
        json.loads(autoresearch_path.read_text(encoding="utf-8"))
        if autoresearch_path.exists()
        else None
    )

    body = HEADER
    body += "export const defaultPipelineOutput: PipelineOutput = "
    body += json.dumps(pipeline, indent=2)
    body += " as unknown as PipelineOutput;\n\n"

    if autoresearch is not None:
        body += "export const defaultAutoresearchOutput: AutoresearchOutput = "
        body += json.dumps(autoresearch, indent=2)
        body += " as unknown as AutoresearchOutput;\n"
    else:
        body += "export const defaultAutoresearchOutput: AutoresearchOutput | null = null;\n"

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(body, encoding="utf-8")
    print(f"Wrote {TARGET} ({TARGET.stat().st_size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
