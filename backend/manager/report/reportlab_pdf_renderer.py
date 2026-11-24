from io import BytesIO
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from backend.domain.models.report_model import InterviewReportResponse


_FONT_NAME = "HireReadyVera"
_BOLD_FONT_NAME = "HireReadyVera-Bold"


class ReportPdfRendererUnavailable(RuntimeError):
	pass


class ReportLabPdfRenderer:
	def render(self, report: InterviewReportResponse | dict[str, Any]) -> bytes:
		try:
			import reportlab
			from reportlab.lib import colors
			from reportlab.lib.enums import TA_CENTER, TA_LEFT
			from reportlab.lib.pagesizes import A4
			from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
			from reportlab.lib.units import mm
			from reportlab.pdfbase import pdfmetrics
			from reportlab.pdfbase.ttfonts import TTFont
			from reportlab.platypus import (
				HRFlowable,
				Paragraph,
				SimpleDocTemplate,
				Spacer,
			)
		except ModuleNotFoundError as error:
			if error.name and error.name.startswith("reportlab"):
				raise ReportPdfRendererUnavailable(
					"ReportLab non è installato nell'ambiente Python del backend. "
					"Installa le dipendenze del progetto e riavvia il backend."
				) from error
			raise ReportPdfRendererUnavailable(
				f"ReportLab non può essere caricato: {error.name or error}."
			) from error

		report_data = (
			report.model_dump(mode="json")
			if isinstance(report, InterviewReportResponse)
			else report
		)
		_font_directory = Path(reportlab.__file__).resolve().parent / "fonts"
		registered_fonts = pdfmetrics.getRegisteredFontNames()
		if _FONT_NAME not in registered_fonts:
			pdfmetrics.registerFont(TTFont(_FONT_NAME, str(_font_directory / "Vera.ttf")))
		if _BOLD_FONT_NAME not in registered_fonts:
			pdfmetrics.registerFont(
				TTFont(_BOLD_FONT_NAME, str(_font_directory / "VeraBd.ttf"))
			)
		navy = colors.HexColor("#1f3a5f")
		blue = colors.HexColor("#4a7fb5")
		muted = colors.HexColor("#4a6078")
		border = colors.HexColor("#dce3eb")
		styles = getSampleStyleSheet()
		title_style = ParagraphStyle(
			"ReportTitle",
			parent=styles["Title"],
			fontName=_BOLD_FONT_NAME,
			fontSize=21,
			leading=26,
			textColor=navy,
			alignment=TA_LEFT,
			spaceAfter=8,
		)
		score_style = ParagraphStyle(
			"OverallScore",
			parent=styles["Normal"],
			fontName=_BOLD_FONT_NAME,
			fontSize=12,
			textColor=navy,
			spaceAfter=12,
		)
		section_style = ParagraphStyle(
			"SectionHeading",
			parent=styles["Heading2"],
			fontName=_BOLD_FONT_NAME,
			fontSize=15,
			leading=19,
			textColor=navy,
			spaceBefore=15,
			spaceAfter=8,
			keepWithNext=True,
		)
		card_heading_style = ParagraphStyle(
			"CardHeading",
			parent=styles["Heading3"],
			fontName=_BOLD_FONT_NAME,
			fontSize=12,
			leading=15,
			textColor=navy,
			spaceBefore=8,
			spaceAfter=5,
			keepWithNext=True,
		)
		body_style = ParagraphStyle(
			"ReportBody",
			parent=styles["BodyText"],
			fontName=_FONT_NAME,
			fontSize=10,
			leading=15,
			textColor=colors.HexColor("#243447"),
			spaceAfter=8,
		)
		label_style = ParagraphStyle(
			"ReportLabel",
			parent=body_style,
			fontName=_BOLD_FONT_NAME,
			textColor=muted,
			spaceAfter=3,
			keepWithNext=True,
		)
		badge_style = ParagraphStyle(
			"AnswerScore",
			parent=body_style,
			fontName=_BOLD_FONT_NAME,
			fontSize=9,
			textColor=navy,
			backColor=colors.HexColor("#e8f1fb"),
			borderColor=border,
			borderWidth=0.6,
			borderPadding=5,
			spaceAfter=6,
		)
		empty_style = ParagraphStyle(
			"EmptyReport",
			parent=body_style,
			textColor=muted,
			alignment=TA_CENTER,
			spaceBefore=5,
			spaceAfter=10,
		)
		story = [
			Paragraph("Report del colloquio", title_style),
			HRFlowable(width="100%", thickness=1.5, color=blue, spaceAfter=12),
		]

		if report_data.get("score") is not None:
			story.append(
				Paragraph(
					f"Media complessiva: {report_data['score']:.2f}/10",
					score_style,
				)
			)

		story.extend(
			[
				Paragraph("In sintesi", section_style),
				_report_paragraph(report_data.get("summary", ""), body_style, Paragraph),
				Paragraph("Punti di intervento", section_style),
			]
		)

		intervention_points = report_data.get("intervention_points", [])
		if not intervention_points:
			story.append(
				Paragraph(
					"Non sono emersi punti di intervento specifici dalle risposte.",
					empty_style,
				)
			)
		for point in intervention_points:
			story.append(
				Paragraph(
					_report_text(point.get("area", "")),
					card_heading_style,
				)
			)
			for label, key in (
				("Evidenza nel colloquio", "evidence"),
				("Intervento consigliato", "recommendation"),
			):
				story.extend(
					_report_labeled_paragraph(
						label,
						point.get(key, ""),
						label_style,
						body_style,
						Paragraph,
					)
				)

		story.append(Paragraph("Valutazione delle risposte", section_style))
		answers = report_data.get("answers", [])
		if not answers:
			story.append(
				Paragraph(
					"Non sono presenti risposte valutabili nel report.",
					empty_style,
				)
			)
		for index, answer in enumerate(answers, start=1):
			story.append(
				Paragraph(f"Risposta {index}", card_heading_style)
			)
			story.append(
				Paragraph(_answer_score_label(answer.get("score")), badge_style)
			)
			for label, key in (
				("Domanda", "question"),
				("Risposta del candidato", "answer"),
				("Motivazione / criticità", "motivation"),
			):
				story.extend(
					_report_labeled_paragraph(
						label,
						answer.get(key, ""),
						label_style,
						body_style,
						Paragraph,
					)
				)
			story.append(Spacer(1, 4 * mm))

		buffer = BytesIO()
		document = SimpleDocTemplate(
			buffer,
			pagesize=A4,
			rightMargin=18 * mm,
			leftMargin=18 * mm,
			topMargin=18 * mm,
			bottomMargin=18 * mm,
			title="Report del colloquio",
			author="HireReady",
		)
		document.build(story)
		return buffer.getvalue()


def _report_text(value: Any) -> str:
	return escape(str(value)).replace("\n", "<br/>")


def _report_paragraph(value: Any, style: Any, paragraph_type: Any) -> Any:
	return paragraph_type(_report_text(value), style)


def _report_labeled_paragraph(
	label: str,
	value: Any,
	label_style: Any,
	body_style: Any,
	paragraph_type: Any,
) -> list[Any]:
	return [
		paragraph_type(escape(label), label_style),
		_report_paragraph(value, body_style, paragraph_type),
	]


def _answer_score_label(score: Any) -> str:
	if score is None:
		return "Voto non disponibile"
	if score <= 4:
		return f"{score}/10 · Risposta da approfondire"
	if score <= 7:
		return f"{score}/10 · Risposta parzialmente efficace"
	return f"{score}/10 · Risposta solida"
