from argparse import ArgumentParser
import logging
import threading
from pathlib import Path
import re
from urllib.parse import urlsplit

from huggingface_hub import snapshot_download


MODEL_REPOSITORY = "rizzoaiacademy/rizzo-pii-0.3B"
DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[3] / "ai_models" / "rizzo-pii-0.3B"
REDACTION_POLICY = {
	"entity_labels": {
		"EMAIL_ADDRESS": "EMAIL",
		"PHONE_NUMBER": "PHONE",
		"TELEPHONE": "PHONE",
		"TEL": "PHONE",
		"CITY": "LOCATION",
		"REGION": "LOCATION",
		"STATE": "LOCATION",
		"LOC": "LOCATION",
		"GPE": "LOCATION",
		"GEO": "LOCATION",
		"ORGANIZATION": "COMPANY",
		"ORG": "COMPANY",
		"COMPANY_NAME": "COMPANY",
		"SCORE": "GRADE",
		"MARK": "GRADE",
		"GPA": "GRADE",
	},
	"text_patterns": (
		(
			"EMAIL",
			re.compile(r"(?i)(?<![\w.+-])[\w.%+-]+@[\w.-]+\.[a-z]{2,}(?![\w.-])"),
			1,
		),
		(
			"PHONE",
			re.compile(
				r"(?i)\b(?:tel(?:efono)?|phone|mobile|cellulare)\s*[:.-]?\s*"
				r"(?P<number>\+?\d[\d\s().-]{5,}\d)"
			),
			7,
		),
		("PHONE", re.compile(r"(?<!\w)\+?\d[\d\s().-]{7,}\d(?!\w)"), 9),
		(
			"GRADE",
			re.compile(
				r"(?i)\b(?:vot[oi]|grades?|gpa|media\s+voti)\b\s*[:=-]?\s*"
				r"(?:\d{1,3}(?:[.,]\d{1,2})?(?:\s*/\s*\d{1,3})?|[a-f](?:[+-])?)"
				r"(?:\s*(?:e\s+lode|with\s+honors))?"
			),
			1,
		),
		(
			"GRADE",
			re.compile(
				r"(?i)(?<!\d)(?:\d{1,2}\s*/\s*30|\d{1,3}\s*/\s*(?:100|110)|"
				r"\d\s*/\s*10|110\s+e\s+lode)(?!\d)"
			),
			1,
		),
	),
	"social_domains": frozenset(
		{
			"linkedin.com",
			"instagram.com",
			"facebook.com",
			"fb.com",
			"twitter.com",
			"x.com",
			"tiktok.com",
			"threads.net",
			"youtube.com",
			"youtu.be",
			"mastodon.social",
		}
	),
}
URL_PATTERN = re.compile(
	r"(?i)(?:https?://)?(?:www\.)?[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
	r"(?:\.[a-z0-9-]+)+(?:/[^\s<>\"'`()\[\]{}]*)?"
)
YEAR_PATTERN = re.compile(r"\s*(?:19\d{2}|20(?:[0-2]\d|30))(?:\s*[-–—/]\s*(?:19\d{2}|20(?:[0-2]\d|30)))*\s*")
IGNORED_ENTITY_LABELS = frozenset(
	{"ZIP", "ZIP_CODE", "ZIPCODE", "POSTAL_CODE", "POSTALCODE", "POSTCODE"}
)


class RizzoAnonymizer:
	def __init__(self, model_dir: str | Path = DEFAULT_MODEL_DIR) -> None:
		self.model_dir = Path(model_dir).expanduser().resolve()
		self._pipeline = None
		self._lock = threading.Lock()
		# idle -> downloading -> loading -> ready  (oppure error)
		self.state = "idle"

	def warm_up(self) -> None:
		"""Scarica il modello se manca e lo carica in memoria. Pensato per l'avvio del backend."""
		try:
			if not self.is_available:
				self.state = "downloading"
				download_model(self.model_dir, force=True)
			self.state = "loading"
			self._get_pipeline()
			self.state = "ready"
		except Exception:
			self.state = "error"
			logging.exception("Preparazione del modello Rizzo PII non riuscita")

	@property
	def is_available(self) -> bool:
		weights = self.model_dir / "model.safetensors"
		if not (self.model_dir / "config.json").is_file() or not weights.is_file():
			return False
		# Un checkout git senza git-lfs lascia un file "puntatore" di pochi byte al posto dei pesi.
		with weights.open("rb") as file:
			return not file.read(64).startswith(b"version https://git-lfs")

	def anonymize(self, text: str) -> str:
		if not text.strip():
			return text

		entities = self._get_pipeline()(text)
		redactions = []
		github_spans = []

		for match in URL_PATTERN.finditer(text):
			url = match.group().rstrip(".,;:!?")
			if not url:
				continue
			domain = self._url_domain(url)
			span = (match.start(), match.start() + len(url))
			if domain == "github.com" or domain.endswith(".github.com"):
				github_spans.append(span)
			elif any(
				domain == social_domain or domain.endswith(f".{social_domain}")
				for social_domain in REDACTION_POLICY["social_domains"]
			):
				redactions.append((span[0], span[1], "SOCIAL_LINK"))

		for entity in entities:
			start = int(entity["start"])
			end = int(entity["end"])
			if start < 0 or end > len(text) or start >= end:
				continue
			if any(start < github_end and end > github_start for github_start, github_end in github_spans):
				continue
			if YEAR_PATTERN.fullmatch(text[start:end]):
				continue

			label = self._normalize_label(
				str(entity.get("entity_group") or entity.get("entity") or "PII")
			)
			if label in IGNORED_ENTITY_LABELS:
				continue
			redactions.append((start, end, label))

		for label, pattern, minimum_digits in REDACTION_POLICY["text_patterns"]:
			for match in pattern.finditer(text):
				start = match.start("number") if "number" in match.groupdict() else match.start()
				end = match.end("number") if "number" in match.groupdict() else match.end()
				if YEAR_PATTERN.fullmatch(text[start:end]):
					continue
				if label == "PHONE":
					digit_count = sum(character.isdigit() for character in text[start:end])
					if digit_count < minimum_digits or digit_count > 15:
						continue
				redactions.append((start, end, label))

		return self._apply_redactions(text, redactions)

	@staticmethod
	def _apply_redactions(text: str, redactions: list[tuple[int, int, str]]) -> str:
		selected_redactions = []
		last_end = -1
		for start, end, label in sorted(
			redactions,
			key=lambda item: (item[0], -(item[1] - item[0]), item[2]),
		):
			if start >= last_end:
				selected_redactions.append((start, end, label))
				last_end = end

		for start, end, label in reversed(selected_redactions):
			text = f"{text[:start]}[{label}]{text[end:]}"
		return text

	@staticmethod
	def _normalize_label(label: str) -> str:
		label = re.sub(r"[^A-Za-z0-9_]+", "_", label.removeprefix("B-").removeprefix("I-")).strip("_")
		label = label.upper() or "PII"
		return REDACTION_POLICY["entity_labels"].get(label, label)

	@staticmethod
	def _url_domain(value: str) -> str:
		url = value if "://" in value else f"//{value}"
		return (urlsplit(url).hostname or "").lower().removeprefix("www.")

	def _get_pipeline(self):
		with self._lock:
			return self._load_pipeline()

	def _load_pipeline(self):
		if self._pipeline is None:
			if not self.is_available:
				raise FileNotFoundError(
					f"Modello Rizzo PII non trovato in {self.model_dir}. "
					"Scaricalo prima con: python -m backend.manager.cv.rizzo_anonymizer"
				)

			from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline

			tokenizer = AutoTokenizer.from_pretrained(self.model_dir, local_files_only=True)
			model = AutoModelForTokenClassification.from_pretrained(
				self.model_dir,
				local_files_only=True,
			)
			self._pipeline = pipeline(
				"token-classification",
				model=model,
				tokenizer=tokenizer,
				aggregation_strategy="simple",
				device=-1,
			)

		return self._pipeline


def download_model(destination: str | Path = DEFAULT_MODEL_DIR, force: bool = False) -> Path:

	model_dir = Path(destination).expanduser().resolve()
	model_dir.mkdir(parents=True, exist_ok=True)

	# metodo i huggingface che vuole il path corretto del modello da scaricare.
	snapshot_download(repo_id=MODEL_REPOSITORY, local_dir=str(model_dir), force_download=force)
	
	return model_dir


def main() -> None:
	parser = ArgumentParser(description="Scarica localmente il modello Rizzo PII.")
	parser.add_argument(
		"--destination",
		type=Path,
		default=DEFAULT_MODEL_DIR,
		help="Cartella locale in cui salvare il modello.",
	)
	parser.add_argument(
		"--force",
		action="store_true",
		help="Riscarica i file anche se risultano già presenti (es. puntatori git-lfs).",
	)
	args = parser.parse_args()

	model_dir = download_model(args.destination, force=args.force)
	print(f"Modello disponibile in: {model_dir}")


if __name__ == "__main__":
	main()
