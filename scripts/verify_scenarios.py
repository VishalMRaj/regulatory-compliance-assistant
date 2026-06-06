import sys
import os
import logging

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.api_services import query_regulatory_knowledge, analyze_change_impact, generate_compliance_report
from datetime import date, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_scenario_1():
    print("\n" + "="*60)
    print("SCENARIO 1: Regulatory Q&A (FAST_RAG Path)")
    print("="*60)
    question = "What are the capital adequacy requirements for Tier 1 under Basel III as amended in 2023?"
    print(f"Q: {question}")
    result = query_regulatory_knowledge(question)
    print(f"\nAnswer: {result.get('answer', 'N/A')}")
    citations = result.get("citations", [])
    if citations:
        print(f"\nCitations ({len(citations)}):")
        for c in citations:
            print(f"  - [{c.get('doc_id')} v{c.get('version')} | {c.get('jurisdiction')}]")


def test_scenario_3():
    print("\n" + "="*60)
    print("SCENARIO 3: Regulatory Change Impact Analysis")
    print("="*60)
    new_circular = (
        "RBI Circular RBI/2026-27/45 dated June 2026: With immediate effect, "
        "all outbound remittances from Indian entities exceeding USD 100,000 to "
        "jurisdictions not on the FATF white-list require prior RBI approval and "
        "submission of form A2 with supporting documentation. This supersedes the "
        "previous threshold of USD 300,000 under LRS."
    )
    print("New Circular: RBI/2026-27/45 (lowering LRS threshold to USD 100k)")
    result = analyze_change_impact(new_circular, "IN")
    print(f"\nUrgency: {result.get('urgency', 'N/A')}")
    print(f"Summary: {result.get('summary', 'N/A')}")
    print(f"Affected Types: {result.get('affected_transaction_types', [])}")
    print(f"Policy Changes: {result.get('policy_changes_required', [])}")


def test_scenario_4():
    print("\n" + "="*60)
    print("SCENARIO 4: Compliance Report Generation")
    print("="*60)
    end_date = str(date.today())
    start_date = str(date.today() - timedelta(days=30))
    print(f"Period: {start_date} to {end_date}")
    report = generate_compliance_report(start_date, end_date)
    print(f"\nReport Preview (first 500 chars):\n{report[:500]}...")


if __name__ == "__main__":
    test_scenario_1()
    test_scenario_3()
    test_scenario_4()
    print("\n\nAll scenario tests completed.")
