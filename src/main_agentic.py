"""Main entry point for Agentic MongoDB DBA Agent"""

import argparse
import logging
import sys
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table
from rich import box

from utils.config_loader import load_config
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
    console.print(Panel(
        f"[bold]MongoDB Cluster Health Check[/bold]\n"
        f"Run ID:   {report.run_id}\n"
        f"Time:     {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        f"Cluster:  {report.cluster_uri}",
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
    console.print(f"  [dim]Report saved → {report.report_path}[/dim]")
    console.print()


def test_prerequisites(config, mongo_manager):
    """Test that all prerequisites are met"""
    console.print("🔍 Checking prerequisites...", style="blue")

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
        with MCPClient(config.mongodb.monitored_cluster) as mcp:
            if not mcp.ping():
                raise RuntimeError("MCP server returned no tools")
        logger.info("Connected to monitored cluster via MCP: %s", config.mongodb.monitored_cluster)
        console.print("✅ MongoDB MCP Server: OK", style="green")
    except Exception as e:
        console.print("❌ Cannot connect to monitored cluster via MCP", style="red")
        console.print(f"   Connection string: {config.mongodb.monitored_cluster}", style="red")
        console.print(f"   Error: {e}", style="red")
        return False

    try:
        from langchain_ollama import OllamaLLM
        llm = OllamaLLM(base_url=config.ollama.base_url, model=config.ollama.model)
        llm.invoke("test")
        console.print("✅ Ollama connection: OK", style="green")
    except Exception as e:
        console.print(f"❌ Cannot connect to Ollama", style="red")
        console.print(f"   URL: {config.ollama.base_url}  Model: {config.ollama.model}", style="red")
        console.print(f"   Error: {e}", style="red")
        return False

    console.print("✅ All prerequisites met", style="green")
    return True


def run_health_check(config) -> None:
    """Run the deterministic health check pipeline and print the report."""
    from agent.health_check_runner import HealthCheckRunner

    console.print("\n🏥 Running cluster health check...", style="bold blue")
    runner = HealthCheckRunner(config)
    report = runner.run()
    print_health_report(report)


def run_investigation(config, mongo_manager, query: str) -> None:
    """Run the agentic investigation loop for a natural language query."""
    console.print("\n🤖 Starting Agentic MongoDB DBA Agent Investigation...", style="bold blue")
    console.print("\n" + "─" * 80)
    console.print(f"📝 USER REQUEST: {query}", style="bold cyan", justify="center")
    console.print("─" * 80)
    console.print("\n🧠 Agent is planning investigation strategy...", style="yellow")

    agent = IntelligentAgenticDBAAgent(config, mongo_manager)
    result = agent.investigate(query)

    console.print("\n" + "=" * 80, style="green")
    console.print(result)
    console.print("=" * 80, style="green")


def main():
    parser = argparse.ArgumentParser(description="Agentic MongoDB DBA Agent")
    parser.add_argument("query", nargs="?", help="Natural language query or 'health check'")
    parser.add_argument("--health-check", action="store_true", help="Run cluster health check")
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
        mongo_manager = MongoDBManager(
            config.mongodb.agent_store,
            config.mongodb.monitored_cluster,
        )

        if not test_prerequisites(config, mongo_manager):
            console.print("\n❌ Prerequisites not met. Please fix the issues above.", style="red")
            sys.exit(1)

        # Route: explicit flag OR keyword detection in the query
        if args.health_check or (args.query and _is_health_check_query(args.query)):
            run_health_check(config)
        else:
            run_investigation(config, mongo_manager, args.query)

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
