import tempfile
import unittest
from pathlib import Path

from cleansight.inspector import inspect_csv, write_cleaned_csv


SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample_customers.csv"


class InspectorTest(unittest.TestCase):
    def test_inspection_finds_expected_quality_signals(self):
        result = inspect_csv(SAMPLE)

        self.assertEqual(result.row_count, 13)
        self.assertEqual(result.column_count, 8)
        self.assertEqual(result.duplicate_rows, 1)
        self.assertGreater(result.issue_count, 0)
        self.assertLess(result.quality_score, 100)

    def test_column_profiles_include_format_errors(self):
        result = inspect_csv(SAMPLE)
        profiles = {profile.name: profile for profile in result.column_profiles}

        self.assertGreaterEqual(profiles["email"].invalid_emails, 2)
        self.assertGreaterEqual(profiles["phone"].invalid_phones, 1)
        self.assertGreaterEqual(profiles["signup_date"].invalid_dates, 1)
        self.assertGreaterEqual(profiles["monthly_spend"].outliers, 1)

    def test_cleaned_csv_removes_duplicate_rows(self):
        result = inspect_csv(SAMPLE)
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "cleaned.csv"
            write_cleaned_csv(result, output)

            lines = output.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), result.row_count)


if __name__ == "__main__":
    unittest.main()
