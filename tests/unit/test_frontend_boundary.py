"""Il frontend deve comunicare solo con il backend HireReady (FastAPI).

Nessun modulo sotto frontend/ può importare backend/, interops/, ai_models/
o client LLM, né chiamare direttamente LM Studio.
"""
import ast
import unittest
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
FORBIDDEN_IMPORT_PREFIXES = ("backend", "interops", "ai_models", "openai", "lmstudio")
FORBIDDEN_SNIPPETS = (":1234", "LM_STUDIO_", "chat/completions")


class FrontendBoundaryTest(unittest.TestCase):
	def _python_files(self):
		return sorted(FRONTEND_DIR.rglob("*.py"))

	def test_frontend_does_not_import_backend_or_llm_clients(self):
		for path in self._python_files():
			tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
			type_checking_lines = {
				statement.lineno
				for guard in ast.walk(tree)
				if isinstance(guard, ast.If)
				and isinstance(guard.test, ast.Name)
				and guard.test.id == "TYPE_CHECKING"
				for statement in ast.walk(guard)
				if isinstance(statement, (ast.Import, ast.ImportFrom))
			}
			for node in ast.walk(tree):
				if isinstance(node, ast.Import):
					names = [alias.name for alias in node.names]
				elif isinstance(node, ast.ImportFrom):
					names = [node.module or ""]
				else:
					continue
				if node.lineno in type_checking_lines:
					continue
				for name in names:
					with self.subTest(file=path.name, module=name):
						self.assertFalse(
							name.split(".")[0] in FORBIDDEN_IMPORT_PREFIXES,
							f"{path} importa {name}: il frontend deve passare da api_client.",
						)

	def test_frontend_does_not_call_lm_studio_directly(self):
		for path in self._python_files():
			source = path.read_text(encoding="utf-8")
			for snippet in FORBIDDEN_SNIPPETS:
				with self.subTest(file=path.name, snippet=snippet):
					self.assertNotIn(snippet, source, f"{path} contiene '{snippet}'.")


class BackendOutboundBoundaryTest(unittest.TestCase):
	"""Le chiamate che escono dal backend verso LM Studio passano solo da interops/."""

	def test_backend_does_not_call_lm_studio_directly(self):
		backend_dir = FRONTEND_DIR.parent / "backend"
		for path in sorted(backend_dir.rglob("*.py")):
			source = path.read_text(encoding="utf-8")
			for snippet in ("import requests", "chat/completions", "/api/v1/"):
				with self.subTest(file=str(path.relative_to(backend_dir)), snippet=snippet):
					self.assertNotIn(snippet, source, f"{path} deve usare interops.LMStudioAPI.")


if __name__ == "__main__":
	unittest.main()
