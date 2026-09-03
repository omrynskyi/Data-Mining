#!/usr/bin/env python3
"""
Data Science Admin Dashboard Entrypoint (Requirement 3).

Starts the Associative Pattern Mining Studio: a single-page admin console over
the CRISP-DM pipeline, the discovered association rules, the hill climbing search
against the target research paper, and a live mining sandbox.

Usage
-----
    python app.py
    PORT=8080 python app.py
    python app.py --port 8080 --debug

The server reads HOST and PORT from the environment (overridable by flags) so it
drops into a container or a test harness without editing code.
"""

import argparse
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import ARTIFACTS_DIR
from src.dashboard.routes import create_app
from src.utils.logger import setup_logger

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 5000


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the dashboard server."""
    parser = argparse.ArgumentParser(
        description="Associative Pattern Mining Studio - Data Science Admin Dashboard",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.environ.get("HOST", DEFAULT_HOST),
        help="Interface to bind (env: HOST).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", DEFAULT_PORT)),
        help="TCP port to serve on (env: PORT).",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=str,
        default=os.environ.get("ARTIFACTS_DIR", str(ARTIFACTS_DIR)),
        help="Directory to read pipeline and optimization artifacts from.",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=os.environ.get("DATASET", "synthetic"),
        help="Dataset the live mining sandbox operates on.",
    )
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")

    return parser.parse_args()


def main() -> int:
    """Create and serve the dashboard application."""
    args = parse_args()
    logger = setup_logger(verbose=args.verbose)

    app = create_app(
        {
            "ARTIFACTS_DIR": args.artifacts_dir,
            "DATASET": args.dataset,
        }
    )

    banner_width = 70
    logger.info("=" * banner_width)
    logger.info("  ASSOCIATIVE PATTERN MINING STUDIO - ADMIN DASHBOARD")
    logger.info("=" * banner_width)
    logger.info(f"  Artifacts : {args.artifacts_dir}")
    logger.info(f"  Sandbox   : {args.dataset}")
    logger.info(f"  Serving   : http://{args.host}:{args.port}")
    logger.info(f"  Health    : http://{args.host}:{args.port}/health")
    logger.info("=" * banner_width)

    # The reloader forks a second process, which breaks subprocess lifecycle
    # management in the acceptance tests; keep it off unless debugging.
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        use_reloader=False,
        threaded=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
