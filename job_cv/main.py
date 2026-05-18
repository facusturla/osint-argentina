#!/usr/bin/env python3
"""
Job CV Customizer — tailor your CV and cover letter to every application.

Usage:
  python job_cv/main.py apply -c "Acme Corp" -t "Backend Engineer" -f job.txt
  python job_cv/main.py apply -c "Acme Corp" -t "Backend Engineer" --cover-letter
  python job_cv/main.py list
  python job_cv/main.py status 0001 interview
"""

import argparse
import sys
from pathlib import Path

# Allow running as `python job_cv/main.py` from repo root
sys.path.insert(0, str(Path(__file__).parent))


def cmd_apply(args: argparse.Namespace) -> None:
    from customizer import customize_cv, generate_cover_letter, load_base_cv
    from pdf_gen import save_outputs
    from tracker import ApplicationTracker

    # Read job description
    if args.job_file:
        job_path = Path(args.job_file)
        if not job_path.exists():
            print(f"Error: job file not found: {args.job_file}")
            sys.exit(1)
        job_desc = job_path.read_text().strip()
    elif not sys.stdin.isatty():
        job_desc = sys.stdin.read().strip()
    else:
        print("Paste the job description below, then press Ctrl+D (or Ctrl+Z on Windows):\n")
        try:
            job_desc = sys.stdin.read().strip()
        except KeyboardInterrupt:
            print("\nCancelled.")
            sys.exit(0)

    if not job_desc:
        print("Error: job description is empty.")
        sys.exit(1)

    print(f"\n→ Customizing CV for [{args.title}] at [{args.company}]...")
    base_cv = load_base_cv()
    customized_cv = customize_cv(base_cv, job_desc, args.company, args.title)
    print("  CV customized.")

    cover_letter = None
    if args.cover_letter:
        print("→ Generating cover letter...")
        cover_letter = generate_cover_letter(base_cv, job_desc, args.company, args.title)
        print("  Cover letter generated.")

    files = save_outputs(args.company, args.title, customized_cv, cover_letter)

    tracker = ApplicationTracker()
    app_id = tracker.add(args.company, args.title, files)

    print(f"\n✓ Application #{app_id} saved:")
    for label, path in files.items():
        rel = Path(path).relative_to(Path.cwd()) if Path(path).is_absolute() else Path(path)
        print(f"  {label:<20} {rel}")


def cmd_list(args: argparse.Namespace) -> None:
    from tracker import ApplicationTracker

    ApplicationTracker().display()


def cmd_status(args: argparse.Namespace) -> None:
    from tracker import ApplicationTracker

    ApplicationTracker().update_status(args.id, args.status)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="job_cv",
        description="Customize your CV and cover letter for every job application.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── apply ──────────────────────────────────────────────────────────────
    apply_p = sub.add_parser("apply", help="Customize CV (and optionally cover letter) for a job")
    apply_p.add_argument("-c", "--company", required=True, help="Company name")
    apply_p.add_argument("-t", "--title", required=True, help="Job title")
    apply_p.add_argument(
        "-f",
        "--job-file",
        metavar="FILE",
        help="Path to a text file containing the job description (omit to paste via stdin)",
    )
    apply_p.add_argument(
        "--cover-letter",
        action="store_true",
        help="Also generate a tailored cover letter",
    )
    apply_p.set_defaults(func=cmd_apply)

    # ── list ───────────────────────────────────────────────────────────────
    list_p = sub.add_parser("list", help="Show all tracked applications")
    list_p.set_defaults(func=cmd_list)

    # ── status ─────────────────────────────────────────────────────────────
    status_p = sub.add_parser("status", help="Update the status of an application")
    status_p.add_argument("id", help="Application ID (e.g. 0001)")
    status_p.add_argument(
        "status",
        choices=["applied", "interview", "offer", "rejected", "withdrawn"],
    )
    status_p.set_defaults(func=cmd_status)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
