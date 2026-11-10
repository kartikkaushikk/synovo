import json
from fastapi import APIRouter, Depends, Path, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.postgres import get_db
from app.db.redis import get_redis
from app.models.transcript import Transcript
from app.services.job_service import get_job

router = APIRouter(prefix="/reports", tags=["reports"])

_REPORT_TTL = 60 * 60 * 24 * 7  # 7 days


def _report_key(job_id: str) -> str:
    return f"report:{job_id}"


@router.post("/{job_id}/generate")
async def generate_report(
    job_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """Generate an AI executive report for the job."""
    await get_job(db, job_id)

    result = await db.execute(
        select(Transcript).where(Transcript.job_id == job_id).order_by(Transcript.chunk_index)
    )
    chunks = result.scalars().all()
    if not chunks:
        raise HTTPException(status_code=400, detail="Transcript is empty — process a job first.")

    # Build transcript text for the LLM prompt
    full_text = "\n".join([f"{c.speaker_id or 'SPEAKER'}: {c.text}" for c in chunks])

    # ─── LLM call (mock — swap in real OpenAI/Gemini call here) ──────────────
    # from openai import AsyncOpenAI
    # client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    # response = await client.chat.completions.create(
    #     model="gpt-4o-mini",
    #     messages=[
    #         {"role": "system", "content": "You are an expert meeting analyst. …"},
    #         {"role": "user", "content": full_text},
    #     ]
    # )
    # parsed = json.loads(response.choices[0].message.content)
    # ─────────────────────────────────────────────────────────────────────────

    report = {
        "job_id": job_id,
        "summary": (
            "The conversation focused on aligning technical requirements for the "
            "upcoming platform release. Participants discussed scalability, deployment "
            "strategy, and timeline expectations."
        ),
        "decisions": [
            "Adopt semantic caching for the search layer",
            "Deploy Celery workers to a dedicated GPU instance",
        ],
        "action_items": [
            "Write integration tests for the embedding pipeline",
            "Set up monitoring dashboards in Grafana",
            "Schedule a follow-up call to review staging results",
        ],
    }

    # Persist to Redis (survives restarts; shared across API replicas)
    await redis.setex(_report_key(job_id), _REPORT_TTL, json.dumps(report))
    return report


@router.get("/{job_id}")
async def get_report(
    job_id: str = Path(...),
    redis=Depends(get_redis),
):
    """Fetch the previously generated report."""
    raw = await redis.get(_report_key(job_id))
    if not raw:
        raise HTTPException(status_code=404, detail="Report not found. Generate it first.")
    return json.loads(raw)


@router.get("/{job_id}/pdf")
async def download_pdf_report(
    job_id: str = Path(...),
    redis=Depends(get_redis),
):
    """Download the report as a PDF."""
    raw = await redis.get(_report_key(job_id))
    if not raw:
        raise HTTPException(status_code=404, detail="Report not found. Generate it first.")

    report = json.loads(raw)

    try:
        from fpdf import FPDF
    except ImportError:
        raise HTTPException(status_code=500, detail="fpdf2 is not installed. Run `pip install fpdf2`.")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, f"AI Executive Report: {job_id[:8]}", ln=True, align="C")
    pdf.ln(4)

    pdf.set_font("helvetica", "B", 13)
    pdf.cell(0, 9, "Summary", ln=True)
    pdf.set_font("helvetica", "", 11)
    pdf.multi_cell(0, 7, report["summary"])
    pdf.ln(3)

    pdf.set_font("helvetica", "B", 13)
    pdf.cell(0, 9, "Key Decisions", ln=True)
    pdf.set_font("helvetica", "", 11)
    for d in report["decisions"]:
        pdf.cell(0, 7, f"  \u2022  {d}", ln=True)
    pdf.ln(3)

    pdf.set_font("helvetica", "B", 13)
    pdf.cell(0, 9, "Action Items", ln=True)
    pdf.set_font("helvetica", "", 11)
    for a in report["action_items"]:
        pdf.cell(0, 7, f"  \u2022  {a}", ln=True)

    pdf_output = pdf.output(dest="S")
    pdf_bytes = bytes(pdf_output) if not isinstance(pdf_output, bytes) else pdf_output

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=report_{job_id[:8]}.pdf"},
    )
