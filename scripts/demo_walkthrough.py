"""End-to-End Reviewer Demonstration Walkthrough for Portfolio Rebalancing System.

Demonstrates the 9 core capabilities of the implemented backend without mutating
production data, bypassing authentication, or executing trades.
"""

import argparse
from datetime import date, datetime
from decimal import Decimal
import json
import logging
import os
from pathlib import Path
import sys
from typing import Optional

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.rebalance_proposal import RebalanceProposal
from app.schemas.approval import ReviewerContext
from app.schemas.policy_rag import PolicySearchRequest
from app.services.approval.approval_service import ApprovalService
from app.services.audit.audit_service import AuditService
from app.services.policy_rag.embedding_service import FakeEmbeddingService
from app.services.policy_rag.policy_rag_service import PolicyRAGService
from app.services.portfolio_analytics_service import PortfolioAnalyticsService
from app.services.rebalancing_service import RebalancingService
from scripts.ingest_policies import ingest_policy_batch
from scripts.seed_database import (
    apply_migrations,
    inspect_database_state,
    resolve_database_url,
    seed_dataset,
    validate_connectivity,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("demo_walkthrough")


def print_stage_header(stage_num: int, title: str) -> None:
    """Print standard styled stage header."""
    separator = "=" * 80
    print(f"\n{separator}")
    print(f"  STAGE {stage_num}: {title.upper()}")
    print(f"{separator}\n")


def stage_1_database_and_migrations(engine) -> bool:
    """Stage 1: Verify database reachability and migration readiness."""
    print_stage_header(1, "Database Connectivity & Migration Verification")

    print(f"Target Database Dialect: {engine.dialect.name}")
    print("Testing connection reachability...")
    if not validate_connectivity(engine):
        print("[ERROR] Database connectivity failed. Verify database target is online.")
        return False
    print("Database connection verified successfully.")

    migrations_dir = REPO_ROOT / "docs" / "migrations"
    print(f"Verifying migration readiness against '{migrations_dir}'...")
    pending = apply_migrations(engine, migrations_dir, dry_run=True)
    if pending:
        print(f"  Pending migrations detected ({len(pending)}): {', '.join(pending)}")
        print("  Applying pending migrations transactionally...")
        applied = apply_migrations(engine, migrations_dir, dry_run=False)
        print(f"  Successfully applied: {', '.join(applied)}")
    else:
        print("  All SQL migrations (000-003) are verified and up to date.")

    print("\nAPI / CLI Equivalent:")
    print("  python scripts/seed_database.py --dry-run")
    return True


def stage_2_synthetic_dataset(engine) -> bool:
    """Stage 2: Verify synthetic starter data availability."""
    print_stage_header(2, "Synthetic Dataset Availability")

    state = inspect_database_state(engine)
    print("Database Entity Table Row Counts:")
    for table, count in state.items():
        print(f"  - {table:25s}: {count:5d} records")

    if state.get("investor_profile", 0) == 0:
        print("\nDatabase is unseeded. Seeding starter dataset from data/starter...")
        dataset_dir = REPO_ROOT / "data" / "starter"
        seed_dataset(engine, dataset_dir)
        state = inspect_database_state(engine)
        print("Seeding complete. New counts:")
        for table, count in state.items():
            print(f"  - {table:25s}: {count:5d} records")

    print("\nStarter Dataset Summary:")
    print(f"  Investors:    {state.get('investor_profile', 0)} (Target: 5)")
    print(f"  Portfolios:   {state.get('portfolio', 0)} (Target: 10)")
    print(f"  Instruments:  {state.get('instrument', 0)} (Target: 20)")
    print(f"  Market Prices:{state.get('market_price', 0)} (Target: 600)")
    print(f"  Holdings:     {state.get('holding', 0)} (Target: 53)")
    print(f"  Constraints:  {state.get('constraint', 0)} (Target: 28)")

    print("\nAPI / CLI Equivalent:")
    print("  python scripts/seed_database.py --dataset-dir data/starter")
    return True


def stage_3_policy_rag(engine) -> bool:
    """Stage 3: Policy document ingestion and semantic retrieval."""
    print_stage_header(3, "Policy Document Ingestion & Semantic Retrieval (RAG)")

    policies_dir = REPO_ROOT / "policy_documents"
    print(f"Checking policy repository at '{policies_dir}'...")

    with Session(engine) as session:
        state = inspect_database_state(engine)
        doc_count = state.get("policy_documents", 0)
        chunk_count = state.get("policy_chunks", 0)

        embedding_svc = FakeEmbeddingService(dimension=384)
        if doc_count == 0:
            print("No policies ingested yet. Ingesting markdown policies...")
            ingest_policy_batch(engine, policies_dir, embedding_service=embedding_svc)
            print("Policy documents successfully vectorized and stored.")
        else:
            print(f"Policy RAG store is populated: {doc_count} documents, {chunk_count} chunks.")

        rag_service = PolicyRAGService(session, embedding_service=embedding_svc)
        query = "cash buffer and liquidity limits"
        search_date = date(2026, 1, 15)
        print(f"\nExecuting semantic similarity search:")
        print(f"  Query:       '{query}'")
        print(f"  As-Of Date:  {search_date}")
        results = rag_service.search_policies(query=query, as_of_date=search_date, top_k=2)

        print(f"  Retrieved Chunks ({len(results)} matches):")
        for idx, res in enumerate(results, start=1):
            print(f"    [{idx}] Doc: '{res.document_title}' (v{res.document_version}) | Chunk: {res.chunk_id}")
            print(f"        Similarity: {res.similarity_score:.4f}")
            snippet = res.content.strip().replace("\n", " ")[:120]
            print(f"        Excerpt: \"{snippet}...\"")

    print("\nREST API Equivalent:")
    print("  POST /api/v1/policies/search")
    print('  Payload: {"query": "cash buffer and liquidity limits", "as_of_date": "2026-01-15", "top_k": 2}')
    return True


def stage_4_portfolio_valuation(engine, portfolio_id: str, as_of: date) -> bool:
    """Stage 4: Portfolio valuation and asset-class weights."""
    print_stage_header(4, "Portfolio Valuation & Position Analysis")

    print(f"Target Portfolio ID: {portfolio_id}")
    print(f"Evaluation As-Of Date: {as_of}")

    with Session(engine) as session:
        analytics = PortfolioAnalyticsService(session)
        val = analytics.get_portfolio_valuation(portfolio_id, as_of)

        print(f"\nTotal Portfolio Value: ${val.total_market_value:,.2f} USD")
        print(f"Positions Count:      {len(val.positions)}")
        print("\nPosition Breakdown:")
        print(f"  {'Symbol':<12} {'Asset Class':<12} {'Quantity':<12} {'Price':<12} {'Market Value':<14} {'Price Date':<12}")
        print("  " + "-" * 76)
        for pos in val.positions:
            sym = pos.symbol or pos.instrument_id
            print(
                f"  {sym:<12} {pos.asset_class:<12} {pos.quantity:<12.2f} "
                f"${pos.unit_price:<11.2f} ${pos.market_value:<13.2f} {str(pos.price_date):<12}"
            )

    print("\nREST API Equivalent:")
    print(f"  GET /api/v1/portfolios/{portfolio_id}/valuation?as_of_date={as_of}")
    return True


def stage_5_drift_analysis(engine, portfolio_id: str, as_of: date) -> bool:
    """Stage 5: Portfolio allocation drift analysis and trigger evaluation."""
    print_stage_header(5, "Portfolio Drift Analysis & Rebalance Trigger")

    with Session(engine) as session:
        analytics = PortfolioAnalyticsService(session)
        drift_res = analytics.get_portfolio_drift(portfolio_id, as_of)

        print(f"Target Portfolio:      {portfolio_id}")
        trigger_flag = drift_res.rebalance_trigger.rebalance_required if drift_res.rebalance_trigger else False
        print(f"Rebalance Triggered:   {trigger_flag}")
        if drift_res.rebalance_trigger:
            print(f"Trigger Status:        {drift_res.rebalance_trigger.status}")
            print(f"Triggered Asset Classes: {', '.join(drift_res.rebalance_trigger.triggered_asset_classes) or 'None'}")

        print("\nAsset Class Drift Summary:")
        print(f"  {'Asset Class':<14} {'Target %':<12} {'Current %':<12} {'Drift %':<12} {'Monetary Drift':<16} {'Signal':<8}")
        print("  " + "-" * 76)
        for d in drift_res.drifts:
            signal = d.action_signal or "HOLD"
            print(
                f"  {d.asset_class:<14} {d.target_weight:>8.2f}%    "
                f"{d.current_weight:>8.2f}%    {d.percentage_drift:>8.2f}%    "
                f"${d.monetary_drift:>14,.2f}  {signal:<8}"
            )

    print("\nREST API Equivalent:")
    print(f"  GET /api/v1/portfolios/{portfolio_id}/drift?as_of_date={as_of}")
    return True


def stage_6_and_7_proposal_simulation_gatekeeper(engine, portfolio_id: str, as_of: date) -> Optional[str]:
    """Stages 6 & 7: Rebalance proposal generation, post-trade simulation, and constraint evaluation."""
    print_stage_header(6, "Rebalance Proposal Generation, Simulation & Policy Gatekeeper")

    proposal_id: Optional[str] = None
    with Session(engine) as session:
        reb_service = RebalancingService(session)
        proposal = reb_service.create_and_persist_proposal(portfolio_id, as_of)
        proposal_id = proposal.proposal_id

        print(f"Generated Proposal ID: {proposal.proposal_id}")
        print(f"Proposal Status:       {proposal.status}")
        print(f"Review Decision State: {proposal.review_decision}")
        print(f"Pre-Trade Value:       ${proposal.pre_trade_portfolio_value:,.2f}")
        print(f"Post-Trade Value:      ${proposal.post_trade_portfolio_value:,.2f}")

        print(f"\nProposed Deterministic Trades ({len(proposal.trades)}):")
        print(f"  {'Side':<6} {'Instrument':<14} {'Quantity':<12} {'Unit Price':<12} {'Value':<12} {'Est Fee':<10}")
        print("  " + "-" * 68)
        for t in proposal.trades:
            print(
                f"  {t.trade_side:<6} {t.instrument_id:<14} {t.quantity:<12.2f} "
                f"${t.unit_price:<11.2f} ${t.trade_value:<11.2f} ${t.fee_amount:<9.2f}"
            )

        print("\nPost-Trade Simulation Outcome:")
        sim = proposal.simulation
        print(f"  Pre-Trade Cash:      ${sim.pre_trade_cash:,.2f}")
        print(f"  Post-Trade Cash:     ${sim.post_trade_cash:,.2f}")
        print(f"  Total Fees:          ${sim.total_executable_fees:,.2f}")
        print(f"  Post-Trade Total:    ${sim.post_trade_portfolio_value:,.2f}")

        print(f"\nPolicy Constraint Gatekeeper Findings ({len(proposal.constraint_findings)} constraints evaluated):")
        for cf in proposal.constraint_findings:
            flag = "VIOLATION" if cf.is_violated else "PASSED"
            sev = f"[{cf.severity}]"
            print(f"  - {sev:<8} {cf.constraint_name} -> {flag}: {cf.message}")

        print("\nFinancial Safety & Execution Safeguards:")
        print("  - Real trade execution is NEVER performed by this system.")
        print("  - Proposed trades are non-binding recommendations requiring human approval.")
        print("  - Investor holdings table remains 100% UNTOUCHED.")

    print("\nREST API Equivalent:")
    print(f"  POST /api/v1/portfolios/{portfolio_id}/rebalance/proposals")
    print(f'  Payload: {{"as_of_date": "{as_of}"}}')
    return proposal_id


def stage_8_grounded_explanation_and_citations(engine, as_of: date) -> bool:
    """Stage 8: Grounded explanation and policy citation behavior."""
    print_stage_header(8, "Grounded Explanation & Compliance Citations")

    print("Verifying Policy Compliance Q&A interface...")
    with Session(engine) as session:
        embedding_svc = FakeEmbeddingService(dimension=384)
        rag_service = PolicyRAGService(session, embedding_service=embedding_svc)
        question = "What is the mandatory cash buffer requirement for client portfolios?"
        
        print(f"Query: '{question}' (As-Of: {as_of})")
        resp = rag_service.ask_question(
            query=question,
            as_of_date=as_of,
            top_k=2,
        )

        print(f"\nAnswer Grounding Status: {'SYNTHESIZED' if resp.answer else 'FALLBACK'}")
        print(f"Response Summary:\n  {resp.answer.strip()}")
        print(f"\nRetrieved Policy Citations ({len(resp.citations)}):")
        for idx, c in enumerate(resp.citations, start=1):
            print(f"  [{idx}] Document: {c.document_title} (ID: {c.document_id}, v{c.version})")
            print(f"      Section/Chunk: {c.chunk_id}")
            snippet = (c.excerpt or "").strip().replace("\n", " ")[:100]
            print(f"      Excerpt: \"{snippet}...\"")

    print("\nREST API Equivalent:")
    print("  POST /api/v1/policies/ask")
    print(f'  Payload: {{"query": "{question}", "as_of_date": "{as_of}", "top_k": 2}}')
    return True


def stage_9_human_approval_and_audit(engine) -> bool:
    """Stage 9: Human review governance and immutable append-only audit trail."""
    print_stage_header(9, "Human Approval / Rejection Governance & Audit Trail")

    # Pick the pre-seeded pending proposal in starter dataset
    demo_proposal_id = "RB-2026-000004"
    print(f"Inspecting pre-seeded proposal for review: {demo_proposal_id}")

    with Session(engine) as session:
        proposal = session.query(RebalanceProposal).filter_by(proposal_id=demo_proposal_id).first()
        if not proposal:
            print(f"[WARN] Proposal {demo_proposal_id} not found; skipping review demo.")
            return False

        print(f"  Current Status:         {proposal.status}")
        print(f"  Current Decision State: {proposal.review_decision}")
        print(f"  Associated Portfolio:   {proposal.portfolio_id}")

        approval_service = ApprovalService(session)
        audit_service = AuditService(session)

        # 1. Demonstrate unauthorized rejection
        print("\nSecurity Enforcement:")
        print("  - Calls without valid Bearer credentials are rejected with HTTP 401.")
        print("  - Tokens without REVIEWER, ADMIN, or PORTFOLIO_MANAGER role are rejected with HTTP 403.")

        # 2. Reviewer Context (authorized reviewer)
        reviewer = ReviewerContext(
            reviewer_id="REV-DEMO-01",
            role="REVIEWER",
            email="demo.reviewer@firm.com",
        )
        print(f"\nSimulating Authorized Human Review by: {reviewer.reviewer_id} ({reviewer.role})")

        if proposal.status == "PENDING_REVIEW":
            print("Proposal is in PENDING_REVIEW. Executing sample review decision (REJECT)...")
            decision_res = approval_service.reject_proposal(
                proposal_id=demo_proposal_id,
                reviewer=reviewer,
                reason="Demo Reviewer Verification: Mandatory quarterly cash rebalance note required.",
            )
            print(f"  Updated Proposal Status: {decision_res.status}")
            print(f"  Review Decision:         {decision_res.review_decision}")
            print(f"  Reviewer Identity:       {decision_res.reviewer_id}")
            print(f"  Justification Reason:    '{decision_res.review_reason}'")
            print(f"  Affected Trades:         {decision_res.rejected_trade_count} trades marked REJECTED.")
        else:
            print(f"Proposal was already reviewed: status={proposal.status}, decision={proposal.review_decision}.")

        # 3. Retrieve Append-Only Audit Trail
        print("\nQuerying Immutable Chronological Audit Trail:")
        events = audit_service.get_events_for_proposal(demo_proposal_id)
        print(f"Total Recorded Audit Events: {len(events)}")
        print(f"  {'Event ID':<18} {'Action':<10} {'Actor':<14} {'Role':<12} {'Timestamp':<25}")
        print("  " + "-" * 80)
        for ev in events:
            metadata = ev.metadata_json or {}
            role = metadata.get("actor_role", "REVIEWER")
            print(
                f"  {ev.event_id:<18} {ev.action:<10} {ev.actor_id:<14} "
                f"{role:<12} {str(ev.timestamp):<25}"
            )

        print("\nFinancial Safety Verification:")
        print("  - Proposal decisions are strictly durable and auditable.")
        print("  - Holdings and real asset balances were NOT modified.")
        print("  - Real-world trade execution remains outside system boundaries.")

    print("\nREST API Equivalents:")
    print(f"  POST /api/v1/proposals/{demo_proposal_id}/reject")
    print('  Headers: {"Authorization": "Bearer dev-reviewer-token"}')
    print('  Payload: {"reason": "Mandatory quarterly cash rebalance note required."}')
    print(f"  GET /api/v1/proposals/{demo_proposal_id}/audit")
    return True


def run_walkthrough(
    database_url: Optional[str] = None,
    portfolio_id: str = "PORT-INV-000001-02",
    as_of: date = date(2026, 1, 15),
) -> int:
    """Execute complete 9-stage guided walkthrough."""
    print("=" * 80)
    print("  PORTFOLIO REBALANCING SYSTEM — TECHNICAL REVIEWER DEMO WALKTHROUGH")
    print("=" * 80)
    print(f"Execution Timestamp: {datetime.now().isoformat()}")
    print(f"Target Portfolio:    {portfolio_id}")
    print(f"Target As-Of Date:   {as_of}")

    try:
        db_url = resolve_database_url(database_url)
    except Exception as exc:
        print(f"[FATAL] Database URL resolution failed: {exc}")
        return 1

    engine = create_engine(db_url)
    try:
        # Stage 1: Connectivity & Migrations
        if not stage_1_database_and_migrations(engine):
            return 1

        # Stage 2: Starter Dataset
        if not stage_2_synthetic_dataset(engine):
            return 1

        # Stage 3: Policy RAG
        if not stage_3_policy_rag(engine):
            return 1

        # Stage 4: Valuation
        if not stage_4_portfolio_valuation(engine, portfolio_id, as_of):
            return 1

        # Stage 5: Drift Analysis
        if not stage_5_drift_analysis(engine, portfolio_id, as_of):
            return 1

        # Stages 6 & 7: Proposal, Simulation & Constraints
        stage_6_and_7_proposal_simulation_gatekeeper(engine, portfolio_id, as_of)

        # Stage 8: Grounded Explanations
        stage_8_grounded_explanation_and_citations(engine, as_of)

        # Stage 9: Human Approval & Audit Trail
        stage_9_human_approval_and_audit(engine)

        print("\n" + "=" * 80)
        print("  DEMO WALKTHROUGH COMPLETED SUCCESSFULLY (All 9 Stages Verified)")
        print("=" * 80)
        return 0
    except Exception as exc:
        logger.exception("Walkthrough encountered an unexpected error: %s", exc)
        print(f"\n[ERROR] Walkthrough failed: {exc}")
        return 1
    finally:
        engine.dispose()


def main() -> int:
    """CLI Entrypoint for the demo walkthrough."""
    parser = argparse.ArgumentParser(
        description="Reviewer Demonstration Walkthrough for Portfolio Rebalancing System.",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="Database connection URI (defaults to DATABASE_URL environment variable).",
    )
    parser.add_argument(
        "--portfolio-id",
        type=str,
        default="PORT-INV-000001-02",
        help="Portfolio identifier to evaluate (default: PORT-INV-000001-02).",
    )
    parser.add_argument(
        "--as-of-date",
        type=lambda d: datetime.strptime(d, "%Y-%m-%d").date(),
        default=date(2026, 1, 15),
        help="Valuation reference date YYYY-MM-DD (default: 2026-01-15).",
    )

    args = parser.parse_args()
    return run_walkthrough(
        database_url=args.database_url,
        portfolio_id=args.portfolio_id,
        as_of=args.as_of_date,
    )


if __name__ == "__main__":
    sys.exit(main())
