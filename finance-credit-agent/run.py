"""
run.py
───────
Main CLI entry point for the Finance Credit Follow-Up Email Agent.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent))


def generate_sample_excel():
    """Generate sample_invoices.xlsx from the CSV."""
    import pandas as pd
    csv_path = Path("data/sample_invoices.csv")
    xlsx_path = Path("data/sample_invoices.xlsx")
    if not csv_path.exists():
        print("ERROR: data/sample_invoices.csv not found.")
        return
    df = pd.read_csv(csv_path)
    df.to_excel(xlsx_path, index=False)
    print(f"Generated: {xlsx_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Finance Credit Follow-Up Email Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                              # Run with sample data (dry-run)
  python run.py --file data/invoices.csv    # Run with custom file
  python run.py --live                      # Live email mode (SMTP required)
  python run.py --generate-samples          # Generate sample Excel file
  python run.py --reset-db                  # Reset database
        """,
    )
    parser.add_argument("--file", "-f", default="data/sample_invoices.csv", help="Invoice CSV or Excel file")
    parser.add_argument("--live", action="store_true", help="Send real emails (SMTP required)")
    parser.add_argument("--generate-samples", action="store_true", help="Generate sample Excel from CSV")
    parser.add_argument("--reset-db", action="store_true", help="Reset the database (WARNING: destructive)")
    parser.add_argument("--scheduler", action="store_true", help="Start the scheduler daemon")
    args = parser.parse_args()

    if args.generate_samples:
        generate_sample_excel()
        return

    if args.reset_db:
        confirm = input("⚠️  This will DELETE all data. Type 'yes' to confirm: ")
        if confirm.strip().lower() == "yes":
            from app.database.db_setup import reset_db
            reset_db()
            print("Database reset complete.")
        else:
            print("Aborted.")
        return

    if args.scheduler:
        from app.services.scheduler import start_scheduler
        import time
        print("Starting scheduler daemon... Press Ctrl+C to stop.")
        sched = start_scheduler()
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            sched.shutdown()
            print("Scheduler stopped.")
        return

    # Default: run the agent
    from app.utils.logger import setup_logging
    setup_logging("INFO")

    from app.agents.email_agent import run_agent
    dry_run = not args.live

    print(f"\n{'='*60}")
    print(f"  Finance Credit Follow-Up Email Agent")
    print(f"  Mode: {'DRY RUN (mock)' if dry_run else '⚡ LIVE (real emails)'}")
    print(f"  File: {args.file}")
    print(f"{'='*60}\n")

    result = run_agent(source_file=args.file, dry_run=dry_run)
    stats = result.get("run_stats", {})

    print(f"\n{'='*60}")
    print("  RUN COMPLETE")
    print(f"{'='*60}")
    for k, v in (stats or {}).items():
        print(f"  {k:25s}: {v}")
    print(f"{'='*60}\n")

    if stats.get("emails_sent", 0) > 0:
        print(f"[EMAIL] Check outputs/ directory for generated emails.")
    if stats.get("escalated_cases", 0) > 0:
        print(f"[ESCALATED] {stats['escalated_cases']} accounts flagged for legal review.")
    print("\n[OK] Run: streamlit run app/ui/dashboard.py to view the dashboard.\n")


if __name__ == "__main__":
    main()
