#!/usr/bin/env python3
"""Send completion email via browser"""
import webbrowser
import urllib.parse

recipient = "ahmedd.eldarawi@gmail.com"
subject = "PHCA Experiment Results Ready"
body = """Congrats! The full 34-run experiment suite completed successfully.

Results Summary:
- All 34 runs completed (100% success rate)
- Duration: 8.2 hours
- Proactive violation rate: 19.3%
- Reactive violation rate: 26.1%
- Violation reduction: 6.8 percentage points
- Latency improvement: 79.3%
- Resource savings: 54.0%

Results and analysis have been pushed to GitHub.

Check EXPERIMENT_RESULTS_SUMMARY.md for full details.
"""

# Create mailto URL
mailto_url = f"mailto:{recipient}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"

print(f"Opening email client to send completion notification to {recipient}...")
print(f"Subject: {subject}")
print()
print("If your default email client doesn't open, please manually send an email with:")
print(f"To: {recipient}")
print(f"Subject: {subject}")
print(f"Body: {body}")

webbrowser.open(mailto_url)
print("\nEmail client opened. Please send the email.")
