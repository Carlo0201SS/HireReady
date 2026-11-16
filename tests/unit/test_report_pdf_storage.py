import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.controller import save_report_pdf


class ReportPdfStorageTests(unittest.TestCase):
	def test_creates_report_directory_and_numbers_saved_reports(self):
		with tempfile.TemporaryDirectory() as temporary_directory:
			report_directory = os.path.join(temporary_directory, "report")
			with patch("backend.controller._REPORT_DIRECTORY", report_directory):
				first_filename = save_report_pdf(b"%PDF-first")
				second_filename = save_report_pdf(b"%PDF-second")

			self.assertEqual(first_filename, "report_colloquio_1.pdf")
			self.assertEqual(second_filename, "report_colloquio_2.pdf")
			self.assertEqual(
				Path(report_directory, first_filename).read_bytes(),
				b"%PDF-first",
			)
			self.assertEqual(
				Path(report_directory, second_filename).read_bytes(),
				b"%PDF-second",
			)


if __name__ == "__main__":
	unittest.main()
