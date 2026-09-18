import asyncio
import csv
import os
import sys
import time

# Add apps/api to sys.path so app imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "apps", "api"))

from app.services.verification.engine import verify_batch


async def main():
    input_csv_path = r"C:\RestoOps\input5.csv"
    standalone_csv_path = r"C:\RestoOps\all-bounceblitz-input5.csv"
    output_csv_path = r"C:\RestoOps\restoops_verification_results.csv"
    comparison_csv_path = r"C:\RestoOps\verification_comparison_report.csv"

    print(f"Reading input emails from {input_csv_path}...", flush=True)
    emails = []
    with open(input_csv_path, "r", encoding="utf-8") as f:
        for line in f:
            email = line.strip()
            if email and "@" in email and not email.startswith("email"):
                emails.append(email)

    print(f"Loaded {len(emails)} emails from input5.csv.", flush=True)

    print("Reading standalone BounceBlitz baseline results...", flush=True)
    standalone_map = {}
    with open(standalone_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            standalone_map[row["email"].strip().lower()] = row

    print(f"Loaded {len(standalone_map)} baseline records.", flush=True)

    print("\nStarting RestoOps Email Verification Engine...", flush=True)
    t0 = time.time()

    completed_count = 0
    total_emails = len(emails)

    async def progress_cb(idx, total, result):
        nonlocal completed_count
        completed_count += 1
        if completed_count % 25 == 0 or completed_count == total:
            print(f"Verified {completed_count}/{total} emails ({(completed_count/total)*100:.1f}%)...", flush=True)

    results = await verify_batch(emails, progress_callback=progress_cb)
    elapsed = time.time() - t0
    print(f"\nVerification completed in {elapsed:.2f} seconds ({len(emails)/elapsed:.1f} emails/sec).")

    # Save RestoOps results
    with open(output_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["email", "status", "status_label", "score", "meaning", "what_to_do", "reason", "mx_host", "provider", "latency_ms"])
        for r in results:
            writer.writerow([r.email, r.status, r.status_label, r.score, r.meaning, r.what_to_do, r.reason, r.mx_host, r.provider, r.latency_ms])

    print(f"Saved RestoOps verification results to {output_csv_path}")

    # Comparison logic
    matches = 0
    status_mismatches = 0
    reason_mismatches = 0
    discrepancies = []

    status_counts_restoops = {}
    status_counts_standalone = {}

    for r in results:
        email_key = r.email.lower()
        baseline = standalone_map.get(email_key)

        status_counts_restoops[r.status] = status_counts_restoops.get(r.status, 0) + 1

        if not baseline:
            discrepancies.append({
                "email": r.email,
                "restoops_status": r.status,
                "standalone_status": "N/A",
                "restoops_reason": r.reason,
                "standalone_reason": "N/A",
                "match": False,
                "note": "Missing in standalone baseline"
            })
            continue

        b_status = baseline.get("status", "")
        b_reason = baseline.get("reason", "")
        status_counts_standalone[b_status] = status_counts_standalone.get(b_status, 0) + 1

        status_match = (r.status == b_status)
        reason_match = (r.reason == b_reason)

        if status_match:
            matches += 1
            if not reason_match:
                reason_mismatches += 1
        else:
            status_mismatches += 1
            discrepancies.append({
                "email": r.email,
                "restoops_status": r.status,
                "standalone_status": b_status,
                "restoops_reason": r.reason,
                "standalone_reason": b_reason,
                "match": False,
                "note": f"Status mismatch ({r.status} vs {b_status})"
            })

    # Save comparison report CSV
    with open(comparison_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["email", "restoops_status", "standalone_status", "restoops_reason", "standalone_reason", "status_match", "note"])
        for r in results:
            email_key = r.email.lower()
            baseline = standalone_map.get(email_key, {})
            b_status = baseline.get("status", "N/A")
            b_reason = baseline.get("reason", "N/A")
            s_match = (r.status == b_status)
            note = "EXACT MATCH" if (s_match and r.reason == b_reason) else ("STATUS MATCH" if s_match else "MISMATCH")
            writer.writerow([r.email, r.status, b_status, r.reason, b_reason, s_match, note])

    total_compared = len(results)
    accuracy = (matches / total_compared * 100) if total_compared > 0 else 0

    print("\n" + "="*70)
    print("COMPARISON SUMMARY: RestoOps Engine vs Standalone BounceBlitz")
    print("="*70)
    print(f"Total Emails Compared:      {total_compared}")
    print(f"Exact Status Matches:       {matches} ({accuracy:.2f}%)")
    print(f"Status Mismatches:          {status_mismatches}")
    print(f"Reason Differences:         {reason_mismatches}")
    print("\n--- Status Distribution Comparison ---")
    all_statuses = sorted(list(set(list(status_counts_restoops.keys()) + list(status_counts_standalone.keys()))))
    print(f"{'Status':<15} | {'RestoOps':<10} | {'Standalone':<10}")
    print("-" * 42)
    for st in all_statuses:
        print(f"{st:<15} | {status_counts_restoops.get(st, 0):<10} | {status_counts_standalone.get(st, 0):<10}")

    if discrepancies:
        print(f"\n--- Top Discrepancies (Showing up to 10 of {len(discrepancies)}) ---")
        for d in discrepancies[:10]:
            print(f"Email: {d['email']}")
            print(f"  RestoOps:   status={d['restoops_status']}, reason={d['restoops_reason']}")
            print(f"  Standalone: status={d['standalone_status']}, reason={d['standalone_reason']}")
            print(f"  Note: {d['note']}\n")

    print(f"Detailed comparison report saved to: {comparison_csv_path}")


if __name__ == "__main__":
    asyncio.run(main())
