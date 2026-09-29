from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from decision_lab.data import generate_demo
from decision_lab.engine import compare_policies
from decision_lab.models import Invoice, Obligation, Scenario


app = FastAPI(
    title="MSME Receivables Decision Lab",
    version="0.1.0",
    description="Research prototype for comparing MSME receivables actions under cash-flow constraints.",
)


class CompareRequest(BaseModel):
    invoices: list[Invoice]
    obligations: list[Obligation]
    scenario: Scenario
    policies: list[str] = Field(default_factory=list)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "msme-receivables-decision-lab"}


@app.get("/generate-demo")
def generate_demo_endpoint() -> dict:
    invoices, obligations, scenario = generate_demo(seed=42)
    return {
        "invoices": [item.model_dump(mode="json") for item in invoices],
        "obligations": [item.model_dump(mode="json") for item in obligations],
        "scenario": scenario.model_dump(mode="json"),
    }


@app.post("/compare")
def compare(request: CompareRequest) -> dict:
    try:
        results = compare_policies(
            request.invoices,
            request.obligations,
            request.scenario,
            request.policies or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "results": [result.model_dump(mode="json") for result in results]
    }
