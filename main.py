#!/usr/bin/env python3
import json
from pathlib import Path
from agents.diagnoser import Diagnoser
from agents.remediator import RemediationAgent  # <-- Use RemediationAgent as before
from agents.remediation_approver import RemediationApprovalAgent  # <-- Import RemediationApprovalAgent

def main():
    # Step 1: Run Diagnoser
    agent = Diagnoser()
    result = agent.run(
        "Analyze the dividend data from NBIM and Custody, identify discrepancies, classify their severity, and " \
        "provide explanations. Follow the instructions you have received with great accuracy. " \
        "Output the results as a JSON array and remember that all occurrences need to be analyzed and outputted."
    )
    print("Agent result:", result)

    # Step 2: Load diagnosis results
    path = Path("data/severity_results.json")
    with open(path, "r") as f:
        data = json.load(f)

    print(json.dumps(data, indent=2))

    # Step 3: Run RemediationAgent on medium/high discrepancies
    remediator = RemediationAgent("data/knowledge_base.json")  # RemediationAgent is still in use
    remediation_approver = RemediationApprovalAgent("approved_remediations.json")  # remediation_approver now included
    
    for entry in data:
        if entry["severity"] in ["medium", "high"]:
            print(f"\n⚠️ Issue {entry['id']}: {entry['explanation']}")
            suggestion = remediator.remediate(entry)
            print(f"💡 Suggested remediation: {suggestion}")

            user_input = input("Apply this remediation? (y/n): ")
            if user_input.lower() == "y":
                print("✅ User accepted remediation.")
                
                # Step 4: The remediation_approver agent automatically saves the accepted remediation
                remediation_approver.run(f"Take the following suggestion: {suggestion} and save it to approved_remediations.json using the remediation_tool"
                )
            else:
                print("❌ User rejected remediation.")

if __name__ == "__main__":
    main()
