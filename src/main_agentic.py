"""Main entry point for Agentic MongoDB DBA Agent"""

import argparse
import logging
import sys
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table
from rich import box

from utils.config_loader import load_config, ClusterConfig
from utils.mongodb_client import MongoDBManager
from agent.intelligent_agentic_agent import IntelligentAgenticDBAAgent
from models.health_check_report import HealthCheckReport, HealthSeverity

# Setup rich console
console = Console()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)

logger = logging.getLogger(__name__)

# Keywords that route to the health check pipeline instead of the agentic loop
_HEALTH_CHECK_KEYWORDS = {
    "health check", "healthcheck", "health-check",
    "cluster health", "cluster check", "check cluster",
    "full check", "run health", "health report",
}


def _is_health_check_query(query: str) -> bool:
    q = query.lower().strip()
    return any(kw in q for kw in _HEALTH_CHECK_KEYWORDS)


def print_health_report(report: HealthCheckReport) -> None:
    """Render a HealthCheckReport to the Rich console."""

    _SEVERITY_STYLE = {
        HealthSeverity.OK:       ("✓ OK",       "bold green"),
        HealthSeverity.WARNING:  ("⚠ WARNING",  "bold yellow"),
        HealthSeverity.CRITICAL: ("✗ CRITICAL", "bold red"),
    }

    overall_label, overall_style = _SEVERITY_STYLE[report.overall_severity]

    # ── Header ────────────────────────────────────────────────────────────────
    console.print()
    cluster_label = f"{report.cluster_name}  ({report.cluster_uri})" if report.cluster_name else report.cluster_uri
    console.print(Panel(
        f"[bold]MongoDB Cluster Health Check[/bold]\n"
        f"Run ID:   {report.run_id}\n"
        f"Time:     {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        f"Cluster:  {cluster_label}",
        box=box.DOUBLE,
        style="cyan",
        expand=False,
    ))

    console.print(f"\n  Overall Health:  [{overall_style}]{overall_label}[/{overall_style}]\n")

    # ── Sections ──────────────────────────────────────────────────────────────
    for i, section in enumerate(report.sections, 1):
        label, style = _SEVERITY_STYLE[section.severity]
        console.print(
            f"[bold]SECTION {i}[/bold]  {section.name:<40} [{style}]{label}[/{style}]"
        )
        console.rule(style="dim")

        # Signals table
        tbl = Table(box=None, show_header=False, padding=(0, 2))
        tbl.add_column(style="dim", width=30)
        tbl.add_column()
        for sig in section.signals:
            val = f"{sig.value} {sig.unit}".strip()
            if sig.threshold is not None:
                val += f"  [dim](threshold: {sig.threshold} {sig.unit})[/dim]"
            tbl.add_row(sig.name.replace("_", " "), val)
        console.print(tbl)

        console.print()
        for finding in section.findings:
            console.print(f"  {finding}")
        console.print()

    # ── Recommendations ───────────────────────────────────────────────────────
    if report.recommendations:
        console.print(f"[bold]RECOMMENDATIONS[/bold]  ({len(report.recommendations)} item(s))")
        console.rule(style="dim")
        for rec in report.recommendations:
            priority_style = "bold red" if rec.priority == "high" else "bold yellow"
            confidence_style = "green" if rec.confidence == "high" else "yellow"
            console.print(
                f"  [[{priority_style}]{rec.priority.upper()}[/{priority_style}]]  "
                f"[bold]{rec.collection}[/bold]"
            )
            console.print(f"  Action:     [cyan]{rec.action}[/cyan]")
            console.print(f"  Evidence:   {rec.evidence}")
            console.print(
                f"  Confidence: [{confidence_style}]{rec.confidence.upper()}[/{confidence_style}]"
            )
            console.print()
    else:
        console.print("[bold]RECOMMENDATIONS[/bold]  No actions required.")
        console.rule(style="dim")
        console.print()

    # ── Footer ────────────────────────────────────────────────────────────────
    html_path = report.report_path.replace(".json", ".html")
    console.print(Panel(
        f"[bold green]Report saved[/bold green]\n\n"
        f"  HTML  →  {html_path}\n"
        f"  JSON  →  {report.report_path}",
        expand=False,
    ))
    console.print()


def test_prerequisites(config, mongo_manager, cluster_uri: str = None, check_llm: bool = True):
    """Test that all prerequisites are met.

    check_llm=False skips the LLM connectivity test — appropriate for --health-check
    where LLM enrichment is optional and must never block startup.
    """
    console.print("🔍 Checking prerequisites...", style="blue")
    target_uri = cluster_uri or config.mongodb.monitored_cluster

    try:
        mongo_manager.test_agent_store_connection()
        logger.info("Connected to agent store: %s", config.mongodb.agent_store)
        logger.info("Agent store connection: OK")
    except Exception as e:
        console.print(f"❌ Cannot connect to agent store", style="red")
        console.print(f"   Connection string: {config.mongodb.agent_store}", style="red")
        console.print(f"   Error: {e}", style="red")
        return False

    try:
        from utils.mcp_client import MCPClient
        with MCPClient(target_uri) as mcp:
            if not mcp.ping():
                raise RuntimeError("MCP server returned no tools")
        logger.info("Connected to monitored cluster via MCP: %s", target_uri)
        console.print("✅ MongoDB MCP Server: OK", style="green")
    except Exception as e:
        console.print("❌ Cannot connect to monitored cluster via MCP", style="red")
        console.print(f"   Connection string: {target_uri}", style="red")
        console.print(f"   Error: {e}", style="red")
        return False

    if check_llm:
        try:
            from utils.llm_factory import build_llm
            llm = build_llm(config)
            llm.invoke("test")
            console.print(f"✅ LLM ({config.llm.provider}): OK", style="green")
        except Exception as e:
            console.print(f"❌ LLM provider '{config.llm.provider}' failed", style="red")
            console.print(f"   Error: {e}", style="red")
            return False
    else:
        console.print(f"  LLM ({config.llm.provider}): skipped for health check (enrichment is best-effort)", style="dim")

    console.print("✅ All prerequisites met", style="green")
    return True


def run_health_check(config, cluster: "ClusterConfig" = None) -> None:
    """Run the deterministic health check pipeline and print the report."""
    from agent.health_check_runner import HealthCheckRunner

    cluster_uri = cluster.uri if cluster else config.mongodb.monitored_cluster
    cluster_name = cluster.name if cluster else ""
    console.print(
        f"\n🏥 Running cluster health check"
        + (f" [{cluster_name}]" if cluster_name else "")
        + "...",
        style="bold blue",
    )
    runner = HealthCheckRunner(config, cluster_uri=cluster_uri, cluster_name=cluster_name)
    report = runner.run()
    print_health_report(report)


def print_multi_report_summary(report) -> None:
    """Print a fleet-level summary to the Rich console."""
    from models.health_check_report import HealthSeverity

    _SEVERITY_STYLE = {
        HealthSeverity.OK:       ("✓ OK",       "bold green"),
        HealthSeverity.WARNING:  ("⚠ WARNING",  "bold yellow"),
        HealthSeverity.CRITICAL: ("✗ CRITICAL", "bold red"),
    }

    overall_label, overall_style = _SEVERITY_STYLE[report.overall_severity]
    ts = report.timestamp.strftime("%Y-%m-%d %H:%M:%S")

    console.print()
    console.print(Panel(
        f"[bold]MongoDB Fleet Health Check[/bold]\n"
        f"Run ID:   {report.run_id}\n"
        f"Time:     {ts} UTC\n"
        f"Clusters: {report.cluster_count}",
        box=box.DOUBLE,
        style="cyan",
        expand=False,
    ))
    console.print(f"\n  Overall Health:  [{overall_style}]{overall_label}[/{overall_style}]\n")

    tbl = Table(box=None, show_header=True, padding=(0, 2))
    tbl.add_column("Cluster", style="bold")
    tbl.add_column("Severity")
    tbl.add_column("Critical", justify="right")
    tbl.add_column("Warning", justify="right")
    tbl.add_column("Recommendations", justify="right")
    for cr in report.clusters:
        label = cr.cluster_name or cr.cluster_uri
        sev_label, sev_style = _SEVERITY_STYLE[cr.overall_severity]
        n_crit = sum(1 for s in cr.sections if s.severity == HealthSeverity.CRITICAL)
        n_warn = sum(1 for s in cr.sections if s.severity == HealthSeverity.WARNING)
        n_recs = len(cr.recommendations)
        tbl.add_row(
            label,
            f"[{sev_style}]{sev_label}[/{sev_style}]",
            str(n_crit) if n_crit else "—",
            str(n_warn) if n_warn else "—",
            str(n_recs) if n_recs else "—",
        )
    console.print(tbl)
    console.print()

    html_path = report.report_path.replace(".json", ".html")
    console.print(Panel(
        f"[bold green]Fleet report saved[/bold green]\n\n"
        f"  HTML  →  {html_path}\n"
        f"  JSON  →  {report.report_path}",
        expand=False,
    ))
    console.print()


def run_multi_cluster_health_check(config) -> None:
    """Run health checks across all configured clusters and produce a unified fleet report."""
    import json
    import time
    from datetime import datetime
    from pathlib import Path
    from agent.health_check_runner import HealthCheckRunner
    from models.multi_cluster_report import MultiClusterReport
    from models.health_check_report import worst_severity
    from utils.multi_cluster_html_reporter import render_multi_html
    from utils.multi_cluster_markdown_reporter import render_multi_markdown

    clusters = config.mongodb.monitored_clusters
    console.print(
        f"\n🏥 Running fleet health check across {len(clusters)} cluster(s)...",
        style="bold blue",
    )

    _SEVERITY_STYLE = {
        HealthSeverity.OK:       ("✓ OK",       "bold green"),
        HealthSeverity.WARNING:  ("⚠ WARNING",  "bold yellow"),
        HealthSeverity.CRITICAL: ("✗ CRITICAL", "bold red"),
    }

    reports = []
    for cluster in clusters:
        console.print(f"  → [{cluster.name}] {cluster.uri}", style="dim")
        runner = HealthCheckRunner(config, cluster_uri=cluster.uri, cluster_name=cluster.name)
        try:
            report = runner.run()
            reports.append(report)
            sev_label, sev_style = _SEVERITY_STYLE[report.overall_severity]
            console.print(f"    {cluster.name}: [{sev_style}]{sev_label}[/{sev_style}]")
        except Exception as e:
            console.print(f"    [bold red]✗ FAILED[/bold red]: {e}", style="red")
            logger.exception("Health check failed for cluster %s", cluster.name)

    if not reports:
        console.print("❌ All cluster checks failed.", style="red")
        return

    overall = worst_severity([r.overall_severity for r in reports])
    run_id = f"fleet_{int(time.time())}"
    timestamp = datetime.utcnow()

    multi = MultiClusterReport(
        run_id=run_id,
        timestamp=timestamp,
        overall_severity=overall,
        clusters=reports,
    )

    # Save reports
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    stem = f"fleet_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}"

    json_path = reports_dir / f"{stem}.json"
    json_path.write_text(json.dumps(multi.to_dict(), indent=2, default=str))
    logger.info("Fleet JSON report saved: %s", json_path)

    html_path = reports_dir / f"{stem}.html"
    html_path.write_text(render_multi_html(multi), encoding="utf-8")
    logger.info("Fleet HTML report saved: %s", html_path)

    md_path = reports_dir / f"{stem}.md"
    md_path.write_text(render_multi_markdown(multi), encoding="utf-8")
    logger.info("Fleet Markdown report saved: %s", md_path)

    multi.report_path = str(json_path)
    print_multi_report_summary(multi)


def run_investigation(config, mongo_manager, query: str, cluster: "ClusterConfig" = None) -> None:
    """Run the agentic investigation loop for a natural language query."""
    console.print("\n🤖 Starting Agentic MongoDB DBA Agent Investigation...", style="bold blue")
    console.print("\n" + "─" * 80)
    console.print(f"📝 USER REQUEST: {query}", style="bold cyan", justify="center")
    console.print("─" * 80)
    console.print("\n🧠 Agent is planning investigation strategy...", style="yellow")

    agent = IntelligentAgenticDBAAgent(config, mongo_manager, cluster=cluster)
    result = agent.investigate(query)

    console.print("\n" + "=" * 80, style="green")
    console.print(result)
    console.print("=" * 80, style="green")


def main():
    parser = argparse.ArgumentParser(description="Agentic MongoDB DBA Agent")
    parser.add_argument("query", nargs="?", help="Natural language query or 'health check'")
    parser.add_argument("--health-check", action="store_true", help="Run cluster health check")
    parser.add_argument("--cluster", default=None, metavar="NAME",
                        help="Target cluster name (from monitored_clusters config)")
    parser.add_argument("--config", default="config/agent_config.yaml", help="Config file path")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if not args.query and not args.health_check:
        parser.print_help()
        sys.exit(1)

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        config = load_config(args.config)

        # Resolve the target cluster
        clusters = config.mongodb.monitored_clusters
        if args.cluster:
            cluster = config.mongodb.get_cluster(args.cluster)
            if cluster is None:
                available = [c.name for c in clusters]
                console.print(
                    f"❌ Unknown cluster '{args.cluster}'. Available: {available}", style="red"
                )
                sys.exit(1)
        else:
            cluster = clusters[0] if clusters else ClusterConfig(
                name="default", uri=config.mongodb.monitored_cluster
            )

        mongo_manager = MongoDBManager(
            config.mongodb.agent_store,
            cluster.uri,
        )

        # Determine route before prereq check so we can skip LLM test for health checks
        is_hc = args.health_check or (args.query and _is_health_check_query(args.query))

        if not test_prerequisites(config, mongo_manager, cluster_uri=cluster.uri, check_llm=not is_hc):
            console.print("\n❌ Prerequisites not met. Please fix the issues above.", style="red")
            sys.exit(1)
        if is_hc:
            # Multi-cluster fleet check when no specific cluster is requested and N > 1
            if not args.cluster and len(config.mongodb.monitored_clusters) > 1:
                run_multi_cluster_health_check(config)
            else:
                run_health_check(config, cluster=cluster)
        else:
            run_investigation(config, mongo_manager, args.query, cluster=cluster)

    except KeyboardInterrupt:
        console.print("\n🛑 Interrupted by user", style="yellow")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n❌ Error: {e}", style="red")
        if args.debug:
            logger.exception("Detailed error information")
        sys.exit(1)
    finally:
        try:
            if "mongo_manager" in locals():
                mongo_manager.close_all_connections()
                logger.info("All MongoDB connections closed")
        except Exception as e:
            logger.warning("Error during cleanup: %s", e)


if __name__ == "__main__":
    main()
