import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether

from backend.app.models import Analysis, Patient, Visit
from backend.app.services.storage import resolve_key


def build_report(patient: Patient, analysis: Analysis, visits: list[Visit], overlay: Path | None) -> dict:
    if analysis.output_mode == "anatomy":
        from backend.app.services.anatomy_report import build_anatomy_report
        return build_anatomy_report(patient, analysis, visits)
    report_id = uuid4().hex
    path = resolve_key(f"reports/{report_id}.pdf")
    path.parent.mkdir(parents=True, exist_ok=True)
    result = analysis.result_json
    prediction = result.get("prediction")
    trained = analysis.output_mode == "trained"
    if trained and not prediction:
        raise ValueError("Trained report requires a sequence prediction")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("Kicker", fontSize=9, textColor=colors.HexColor("#117b8a"), spaceAfter=12))
    styles.add(
        ParagraphStyle(
            "Warning",
            parent=styles["BodyText"],
            textColor=colors.HexColor("#922b21"),
            backColor=colors.HexColor("#fff0ed"),
            borderPadding=8,
            spaceAfter=12,
        )
    )
    doc = SimpleDocTemplate(
        str(path), pagesize=(595, 842), rightMargin=42, leftMargin=42, topMargin=40, bottomMargin=45
    )
    story = [
        Paragraph("NEUROPREDICT AI / RESEARCH REPORT", styles["Kicker"]),
        Paragraph(escape(patient.code), styles["Title"]),
        Paragraph("Research Prototype | Not a medical diagnosis", styles["Heading2"]),
        Paragraph(
            f"Output mode: {escape(analysis.output_mode.title())} | Model: {escape(analysis.model_version)}",
            styles["Normal"],
        ),
        Paragraph(f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}", styles["Normal"]),
        Spacer(1, 16),
    ]
    if trained:
        classification = (
            "Observed CDR increase" if prediction["predicted_increase"] else "No observed CDR increase"
        )
        story.extend(
            [
                Paragraph("Experimental trained sequence classification", styles["Heading2"]),
                Paragraph(
                    "POOR HELD-OUT PERFORMANCE / RESEARCH ONLY. This checkpoint failed to generalize. "
                    "It recognizes observed first-to-last CDR change retrospectively using all included visits; "
                    "it does not forecast future Alzheimer's disease. Training-cohort predictions are in-sample "
                    "demonstrations, not accuracy evidence. Not clinically validated.",
                    styles["Warning"],
                ),
                Paragraph(
                    f"One uncalibrated sequence score: {prediction['score']:.6f}. "
                    f"Validation-selected threshold: {prediction['decision_threshold']:.6f}. "
                    f"Classification: {classification}. This score is not a disease probability.",
                    styles["BodyText"],
                ),
                Paragraph(
                    f"Cohort role: {escape(prediction['cohort_role'])}. "
                    f"Training: {prediction['training_subjects']} subjects / {prediction['training_visits']} visits. "
                    f"Reused test holdout: {prediction['test_subjects']} subjects; "
                    f"accuracy {prediction['test_accuracy'] * 100:.1f}%, "
                    f"balanced accuracy {prediction['test_balanced_accuracy'] * 100:.1f}%, "
                    f"ROC-AUC {prediction['test_roc_auc']:.4f}; "
                    f"majority-class baseline accuracy {prediction['majority_baseline_accuracy'] * 100:.1f}%.",
                    styles["BodyText"],
                ),
                Paragraph(
                    f"Checkpoint SHA-256: {escape(prediction['checkpoint_sha256'])}", styles["BodyText"]
                ),
                Spacer(1, 14),
                Paragraph("Per-visit image-proxy metrics (not neural predictions)", styles["Heading2"]),
                Paragraph(
                    "Foreground fraction and feature change are intensity-derived proxies, not segmented anatomy, "
                    "measured atrophy or model attribution. No per-visit trained scores are generated.",
                    styles["BodyText"],
                ),
                Spacer(1, 10),
            ]
        )
    else:
        story.extend(
            [
                Paragraph("Longitudinal progression-risk estimates", styles["Heading2"]),
                Paragraph(
                    "Uncalibrated structural-change index shown as a percentage; not a probability of disease. "
                    "All changes refer to the earliest included visit.",
                    styles["BodyText"],
                ),
                Spacer(1, 10),
            ]
        )
    lookup = {v.id: v for v in visits}
    rows = [["Visit", "Day", *([] if trained else ["Estimate"]), "Foreground proxy", "Feature change"]]
    for i, vid in enumerate(result["visit_ids"]):
        visit = lookup[vid]
        rows.append(
            [
                Paragraph(escape(visit.label), styles["Normal"]),
                str(visit.days_from_baseline),
                *([] if trained else [f"{result['risk_scores'][i] * 100:.1f}%"]),
                f"{result['biomarkers']['foreground_fraction'][i] * 100:.1f}%",
                f"{result['biomarkers']['feature_change'][i]:.4f}",
            ]
        )
    table = Table(
        rows,
        colWidths=[180, 55, 150, 120] if trained else [145, 45, 75, 135, 105],
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5f3f5")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#dce4e9")),
            ]
        )
    )
    story.extend([table, Spacer(1, 18), Paragraph("Research interpretation", styles["Heading2"])])
    if trained:
        story.append(
            Paragraph(
                "The classification applies to this entire observed sequence only. A train cohort role means "
                "the subject contributed to fitting the model; validation/test roles refer to the frozen research "
                "split, and the test holdout was reused. This analysis does not establish future progression "
                "or improved prediction accuracy.",
                styles["BodyText"],
            )
        )
    else:
        story.append(
            Paragraph(
                f"The index changed by {(result['risk_scores'][-1] - result['risk_scores'][0]) * 100:+.1f} "
                "percentage points relative to baseline. This describes the pipeline output and does not establish disease progression.",
                styles["BodyText"],
            )
        )
    observed = [v for v in visits if v.id in result["visit_ids"] and v.metadata_json.get("nWBV") is not None]
    if observed:
        story.extend([Spacer(1, 10), Paragraph("Observed OASIS metadata", styles["Heading2"])])
        for visit in observed:
            etiv = visit.metadata_json.get("eTIV")
            etiv_label = f"{etiv:.1f} mL" if isinstance(etiv, (int, float)) else "unavailable"
            story.append(
                Paragraph(
                    f"{escape(visit.label)}: nWBV {visit.metadata_json['nWBV']:.4f}; "
                    f"eTIV {etiv_label}. Source: supplied OASIS demographics; not inferred by this app.",
                    styles["BodyText"],
                )
            )
    if overlay and overlay.is_file():
        story.append(
            KeepTogether(
                [
                    Spacer(1, 14),
                    Paragraph("Intensity-difference research visualization", styles["Heading2"]),
                    Image(str(overlay), width=2.2 * inch, height=2.2 * inch),
                    Paragraph(
                        "Selected scan versus baseline. Not anatomically registered; not Grad-CAM.",
                        styles["BodyText"],
                    ),
                ]
            )
        )
    story.extend([Spacer(1, 14), Paragraph("Methods and limitations", styles["Heading2"])])
    story.extend(Paragraph(escape(caveat), styles["BodyText"]) for caveat in result["caveats"])

    def footer(canvas, document):
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#526477"))
        canvas.drawString(42, 24, "Alzhio | Research Prototype | Not a medical diagnosis")
        canvas.drawRightString(553, 24, f"Page {document.page}")

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    metadata = {
        "id": report_id,
        "patientId": patient.id,
        "patientCode": patient.code,
        "ownerId": patient.owner_id,
        "analysisId": analysis.id,
        "outputMode": analysis.output_mode,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "downloadUrl": f"/api/reports/{report_id}/download",
    }
    resolve_key(f"reports/{report_id}.json").write_text(json.dumps(metadata), encoding="utf-8")
    return {k: v for k, v in metadata.items() if k != "ownerId"}
