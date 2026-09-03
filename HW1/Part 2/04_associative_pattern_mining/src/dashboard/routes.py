"""
Flask Application Factory & REST API Suite (Features F12, F13).

Serves the single-page admin dashboard plus the JSON API it runs on:

    GET  /                     Single-page dashboard shell
    GET  /health               Liveness probe with per-artifact availability
    GET  /api/summary          Headline KPIs across pipeline and optimization
    GET  /api/crisp-dm         Six-phase CRISP-DM metadata
    GET  /api/eda              Basket distributions and item frequencies
    GET  /api/rules            Filtered, sorted, paginated rule list
    GET  /api/rules/network    Vis.js node/edge graph of the rule set
    GET  /api/rules/scatter    Support/confidence/lift points for the 3D plot
    GET  /api/rules/export     Rule export as CSV or JSON
    GET  /api/itemsets         Discovered frequent itemsets
    GET  /api/optimization     Target paper, trajectory and convergence
    POST /api/sandbox/mine     Interactive on-demand mining
    GET  /api/recommend        Next-basket recommendations for a cart

Every endpoint degrades gracefully: with no artifacts on disk the API returns
well-formed empty structures and flags them as unavailable, so the dashboard can
tell the analyst what to run rather than rendering misleading zeros.
"""

import io
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from flask import Flask, Response, jsonify, render_template, request

from config import ARTIFACTS_DIR, METRIC_DEFINITIONS, PROJECT_ROOT
from src.dashboard.artifact_loader import ArtifactLoader
from src.dashboard.live_miner import (
    SandboxValidationError,
    TransactionCorpus,
    run_live_mining,
    validate_parameters,
)
from src.evaluation.filter import generate_recommendations
from src.optimization.papers import PAPER_CATALOG
from src.utils.logger import get_logger

logger = get_logger("crisp_dm.dashboard")

VERSION = "1.0.0"

#: Ordered CRISP-DM phases, paired with the summary key each one reads from.
CRISP_DM_PHASES = [
    ("business_understanding", "Business Understanding",
     "Frame the commercial question: which product affinities are worth acting on?"),
    ("data_understanding", "Data Understanding",
     "Profile basket sizes, item frequencies, sparsity and data quality anomalies."),
    ("data_preparation", "Data Preparation",
     "Clean cancellations and administrative codes, then encode baskets as a boolean matrix."),
    ("modeling", "Modeling",
     "Discover frequent itemsets with FP-Growth or Apriori and extract candidate rules."),
    ("evaluation", "Evaluation",
     "Score rules on nine interest metrics, prune redundant sub-rules, categorise by action."),
    ("deployment", "Deployment",
     "Publish summary, rules and report artifacts for the dashboard and downstream use."),
]


def _float_arg(name: str, default: Optional[float] = None) -> Optional[float]:
    """Read a float query parameter, ignoring blanks and malformed values."""
    raw = request.args.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _int_arg(name: str, default: int) -> int:
    """Read an integer query parameter, falling back to `default`."""
    raw = request.args.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return default


def create_app(config: Optional[Dict[str, Any]] = None) -> Flask:
    """
    Build the dashboard Flask application.

    Parameters
    ----------
    config : Optional[Dict[str, Any]]
        Overrides merged into `app.config`. `ARTIFACTS_DIR` redirects the loader
        at a different artifacts directory, which is how the test suite points
        the app at a temporary fixture directory.
    """
    app = Flask(
        __name__,
        template_folder=str(Path(PROJECT_ROOT) / "templates"),
        static_folder=str(Path(PROJECT_ROOT) / "static"),
    )

    app.config["ARTIFACTS_DIR"] = str(ARTIFACTS_DIR)
    app.config["DATASET"] = "synthetic"
    if config:
        app.config.update(config)

    loader = ArtifactLoader(artifacts_dir=app.config["ARTIFACTS_DIR"])
    corpus = TransactionCorpus(dataset_name=app.config.get("DATASET", "synthetic"))

    app.extensions["artifact_loader"] = loader
    app.extensions["transaction_corpus"] = corpus

    # ------------------------------------------------------------------
    # Shell & health
    # ------------------------------------------------------------------

    @app.route("/")
    def index() -> Response:
        """Render the single-page dashboard shell."""
        return render_template(
            "index.html",
            version=VERSION,
            metric_definitions=METRIC_DEFINITIONS,
            papers=PAPER_CATALOG,
        )

    @app.route("/health")
    def health():
        """Liveness probe reporting which artifacts the dashboard can serve."""
        return jsonify(
            {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": VERSION,
                "artifacts": loader.availability(),
                "artifacts_dir": str(loader.artifacts_dir),
            }
        ), 200

    # ------------------------------------------------------------------
    # Pipeline views
    # ------------------------------------------------------------------

    @app.route("/api/summary")
    def api_summary():
        """Headline KPIs spanning the pipeline run and the optimization search."""
        return jsonify(loader.summary_kpis())

    @app.route("/api/crisp-dm")
    def api_crisp_dm():
        """Six-phase CRISP-DM metadata, one entry per phase, in canonical order."""
        summary = loader.get_pipeline_summary()
        stages = summary.get("crisp_dm_stages") or {}

        phases = []
        for index, (key, title, description) in enumerate(CRISP_DM_PHASES, start=1):
            details = stages.get(key) or {}
            phases.append(
                {
                    "index": index,
                    "key": key,
                    "title": title,
                    "description": description,
                    "completed": bool(details),
                    "details": details,
                }
            )

        return jsonify(
            {
                "available": bool(stages),
                "framework": "CRISP-DM",
                "metadata": summary.get("pipeline_metadata", {}),
                "phases": phases,
                "top_rules": summary.get("top_rules", []),
                "report_markdown": loader.get_pipeline_report(),
            }
        )

    @app.route("/api/eda")
    def api_eda():
        """Basket-size distribution, item frequencies and sparsity diagnostics."""
        return jsonify(loader.get_eda())

    @app.route("/api/itemsets")
    def api_itemsets():
        """Discovered frequent itemsets, optionally filtered by cardinality."""
        itemsets = loader.get_frequent_itemsets()
        length = _int_arg("length", 0)
        if length > 0:
            itemsets = [item for item in itemsets if item.get("length") == length]

        limit = max(1, _int_arg("limit", 200))
        by_length: Dict[str, int] = {}
        for item in loader.get_frequent_itemsets():
            key = f"k={item.get('length', 0)}"
            by_length[key] = by_length.get(key, 0) + 1

        return jsonify(
            {
                "total": len(itemsets),
                "by_length": by_length,
                "itemsets": itemsets[:limit],
            }
        )

    # ------------------------------------------------------------------
    # Rules
    # ------------------------------------------------------------------

    def _filtered_rules() -> List[Dict[str, Any]]:
        """Apply the shared query-parameter filters to the loaded rule set."""
        rules = loader.get_rules()

        min_support = _float_arg("min_support")
        min_confidence = _float_arg("min_confidence")
        min_lift = _float_arg("min_lift")
        search = (request.args.get("search") or "").strip().lower()
        category = (request.args.get("category") or "").strip()

        def _keep(rule: Dict[str, Any]) -> bool:
            if min_support is not None and float(rule.get("support", 0.0)) < min_support:
                return False
            if min_confidence is not None and float(rule.get("confidence", 0.0)) < min_confidence:
                return False
            if min_lift is not None and float(rule.get("lift", 0.0)) < min_lift:
                return False
            if category and str(rule.get("rule_category", "")) != category:
                return False
            if search:
                items = " ".join(rule.get("antecedents", []) + rule.get("consequents", [])).lower()
                if search not in items:
                    return False
            return True

        filtered = [rule for rule in rules if _keep(rule)]

        sort_by = (request.args.get("sort_by") or "lift").strip()
        descending = (request.args.get("order") or "desc").lower() != "asc"
        if filtered and sort_by in filtered[0]:
            filtered.sort(key=lambda r: float(r.get(sort_by, 0.0) or 0.0), reverse=descending)

        return filtered

    @app.route("/api/rules")
    def api_rules():
        """Filtered, sorted and paginated association rules."""
        filtered = _filtered_rules()

        limit = max(1, _int_arg("limit", 100))
        offset = max(0, _int_arg("offset", 0))
        page = filtered[offset: offset + limit]

        return jsonify(
            {
                "total": len(loader.get_rules()),
                "filtered": len(filtered),
                "limit": limit,
                "offset": offset,
                "returned": len(page),
                "rules": page,
                "categories": sorted(
                    {str(r["rule_category"]) for r in filtered if r.get("rule_category")}
                ),
                "metric_definitions": METRIC_DEFINITIONS,
            }
        )

    @app.route("/api/rules/network")
    def api_rules_network():
        """
        Rule set as a Vis.js force-directed graph.

        Items become nodes sized by how often they participate in rules; each
        rule becomes a directed edge from its antecedent items to its consequent
        items, weighted by lift. Multi-item antecedents fan in from every member,
        which keeps the graph readable without inventing synthetic hub nodes.
        """
        limit = max(1, _int_arg("limit", 120))
        rules = _filtered_rules()[:limit]

        degree: Dict[str, int] = {}
        edges: List[Dict[str, Any]] = []

        for rule in rules:
            antecedents = rule.get("antecedents", [])
            consequents = rule.get("consequents", [])
            lift = float(rule.get("lift", 0.0) or 0.0)
            confidence = float(rule.get("confidence", 0.0) or 0.0)

            for item in antecedents + consequents:
                degree[item] = degree.get(item, 0) + 1

            for source in antecedents:
                for target in consequents:
                    edges.append(
                        {
                            "id": f"e{len(edges)}",
                            "from": source,
                            "to": target,
                            "value": round(lift, 4),
                            "title": (
                                f"{{{', '.join(antecedents)}}} -> {{{', '.join(consequents)}}}<br>"
                                f"confidence {confidence:.3f} | lift {lift:.3f}"
                            ),
                            "confidence": round(confidence, 6),
                            "lift": round(lift, 6),
                            "support": round(float(rule.get("support", 0.0) or 0.0), 6),
                            "rule_id": rule.get("id"),
                        }
                    )

        nodes = [
            {
                "id": item,
                "label": item if len(item) <= 28 else item[:25] + "...",
                "title": f"{item} ({count} rule participations)",
                "value": count,
            }
            for item, count in sorted(degree.items(), key=lambda kv: kv[1], reverse=True)
        ]

        return jsonify({"nodes": nodes, "edges": edges, "rule_count": len(rules)})

    @app.route("/api/rules/scatter")
    def api_rules_scatter():
        """Support / confidence / lift coordinates for the 3D scatter plot."""
        rules = _filtered_rules()[: max(1, _int_arg("limit", 500))]
        return jsonify(
            {
                "points": [
                    {
                        "id": rule.get("id"),
                        "support": float(rule.get("support", 0.0) or 0.0),
                        "confidence": float(rule.get("confidence", 0.0) or 0.0),
                        "lift": float(rule.get("lift", 0.0) or 0.0),
                        "leverage": float(rule.get("leverage", 0.0) or 0.0),
                        "label": (
                            f"{{{', '.join(rule.get('antecedents', []))}}} -> "
                            f"{{{', '.join(rule.get('consequents', []))}}}"
                        ),
                        "category": rule.get("rule_category", "General Association"),
                    }
                    for rule in rules
                ],
                "count": len(rules),
            }
        )

    @app.route("/api/rules/export")
    def api_rules_export():
        """Export the current filtered rule selection as CSV or JSON."""
        fmt = (request.args.get("format") or "json").lower().strip()
        rules = _filtered_rules()

        if fmt == "csv":
            frame = pd.DataFrame(rules)
            for column in ("antecedents", "consequents"):
                if column in frame.columns:
                    frame[column] = frame[column].apply(
                        lambda items: ", ".join(items) if isinstance(items, list) else str(items)
                    )
            buffer = io.StringIO()
            frame.to_csv(buffer, index=False)
            return Response(
                buffer.getvalue(),
                mimetype="text/csv",
                headers={"Content-Disposition": "attachment; filename=association_rules.csv"},
            )

        if fmt not in ("json", "csv"):
            return jsonify({"status": "error", "message": f"Unsupported format '{fmt}'."}), 400

        return Response(
            json.dumps({"count": len(rules), "rules": rules}, indent=2),
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=association_rules.json"},
        )

    # ------------------------------------------------------------------
    # Optimization
    # ------------------------------------------------------------------

    @app.route("/api/optimization")
    def api_optimization():
        """Target paper, hyperparameter trajectory and convergence history."""
        log = loader.get_optimization_log()
        history = loader.get_optimization_history()

        return jsonify(
            {
                "available": bool(log.get("iteration_trail")) or bool(history),
                "metadata": log.get("metadata", {}),
                "target_paper": log.get("target_paper", {}),
                "config": log.get("config", {}),
                "summary": log.get("summary", {}),
                "target_vs_achieved": log.get("target_vs_achieved", {}),
                "best_hyperparameters": log.get("best_hyperparameters", {}),
                "best_metrics": log.get("best_metrics", {}),
                "history": history,
                "optimized_rules": loader.get_optimized_rules()[: max(1, _int_arg("limit", 100))],
                "paper_catalog": PAPER_CATALOG,
            }
        )

    # ------------------------------------------------------------------
    # Interactive sandbox & recommendations
    # ------------------------------------------------------------------

    @app.route("/api/sandbox/mine", methods=["POST"])
    def api_sandbox_mine():
        """Mine the corpus on demand with analyst-supplied parameters."""
        payload = request.get_json(silent=True)
        if payload is None:
            return jsonify(
                {"status": "error", "message": "Request body must be valid JSON."}
            ), 400

        try:
            params = validate_parameters(payload)
        except SandboxValidationError as exc:
            return jsonify({"status": "error", "message": str(exc)}), 400

        try:
            onehot, metadata = corpus.load()
        except Exception as exc:  # pragma: no cover - corpus load failure is environmental
            logger.error(f"Sandbox corpus could not be loaded: {exc}")
            return jsonify(
                {"status": "error", "message": f"Transaction corpus unavailable: {exc}"}
            ), 503

        result = run_live_mining(
            df_onehot=onehot,
            min_support=params["min_support"],
            min_confidence=params["min_confidence"],
            min_lift=params["min_lift"],
            max_len=params["max_len"],
            algorithm=params["algorithm"],
            top_n=params["top_n"],
            sort_by=params["sort_by"],
        )
        result["dataset"] = metadata
        return jsonify(result)

    @app.route("/api/sandbox/corpus")
    def api_sandbox_corpus():
        """Describe the corpus the sandbox mines, without running a search."""
        try:
            _, metadata = corpus.load()
        except Exception as exc:  # pragma: no cover - environmental
            return jsonify({"status": "error", "message": str(exc)}), 503
        return jsonify({"status": "success", "dataset": metadata})

    @app.route("/api/recommend")
    def api_recommend():
        """Recommend next-basket items for a comma-separated cart."""
        raw_cart = request.args.get("cart", "")
        cart = [item.strip() for item in raw_cart.split(",") if item.strip()]

        if not cart:
            return jsonify(
                {
                    "cart": [],
                    "recommendations": [],
                    "message": "Supply a comma-separated 'cart' parameter to get recommendations.",
                }
            )

        rules_df = loader.get_rules_df()
        recommendations = generate_recommendations(
            cart=cart,
            rules_df=rules_df,
            top_n=max(1, _int_arg("limit", 10)),
            min_confidence=_float_arg("min_confidence", 0.0) or 0.0,
            min_lift=_float_arg("min_lift", 1.0) or 1.0,
        )

        return jsonify(
            {
                "cart": cart,
                "recommendations": recommendations,
                "rules_considered": int(len(rules_df)),
            }
        )

    @app.route("/api/catalog/items")
    def api_catalog_items():
        """Distinct item labels appearing in the rule set, for cart autocomplete."""
        items = sorted(
            {
                item
                for rule in loader.get_rules()
                for item in rule.get("antecedents", []) + rule.get("consequents", [])
            }
        )
        return jsonify({"count": len(items), "items": items})

    # ------------------------------------------------------------------

    @app.errorhandler(404)
    def not_found(error):
        """JSON 404 for API paths, so the front end never parses an HTML error page."""
        if request.path.startswith("/api/"):
            return jsonify({"status": "error", "message": f"No such endpoint: {request.path}"}), 404
        return render_template("index.html", version=VERSION,
                               metric_definitions=METRIC_DEFINITIONS,
                               papers=PAPER_CATALOG), 404

    @app.errorhandler(500)
    def server_error(error):  # pragma: no cover - defensive
        logger.error(f"Unhandled dashboard error: {error}")
        return jsonify({"status": "error", "message": "Internal server error."}), 500

    return app
