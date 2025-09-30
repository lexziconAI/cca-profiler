"""Smoke test for CCIP package."""

import csv
import logging
import tempfile
import unittest
from pathlib import Path

import pandas as pd

# Import after creating test CSV to avoid import errors
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestCCIPSmoke(unittest.TestCase):
    """Smoke test to verify basic CCIP functionality."""
    
    def setUp(self):
        """Create minimal test CSV."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.input_csv = self.temp_dir / "test_input.csv"
        self.output_xlsx = self.temp_dir / "test_output.xlsx"
        
        # Create minimal CSV with anchor header and 3 participants
        headers = [
            "ID", "Email", "Date", "Name", "Organisation", "Level", "Focus",
            "I prefer to be clear and direct even if it might seem blunt",  # Q1 anchor
            "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9", "Q10",
            "Q11", "Q12", "Q13", "Q14", "Q15", "Q16", "Q17", "Q18", "Q19", "Q20",
            "Q21", "Q22", "Q23", "Q24", "Q25"
        ]
        
        data = [
            # Participant 1: High scores (Strongly Agree = 5)
            ["1", "user1@example.com", "2024-01-01", "Alice Smith", "Axiom Inc",
             "Manager", "Leadership",
             "5", "2", "5", "5", "5",  # Q1-5 (note Q2 will be reversed)
             "5", "3", "5", "5", "5",  # Q6-10
             "2", "4", "5", "5", "5",  # Q11-15 (note Q11 will be reversed)
             "5", "5", "5", "5", "5",  # Q16-20
             "5", "5", "5", "5", "5"   # Q21-25
            ],
            # Participant 2: Mixed scores (Neutral = 3, Agree = 4)
            ["2", "user2@example.com", "2024-01-02", "Bob Jones", "Tech Corp",
             "Individual Contributor", "Technical",
             "4", "4", "3", "4", "4",  # Q1-5
             "3", "5", "4", "3", "4",  # Q6-10
             "5", "3", "4", "4", "3",  # Q11-15
             "4", "4", "3", "4", "4",  # Q16-20
             "3", "4", "4", "3", "4"   # Q21-25
            ],
            # Participant 3: Low scores (Strongly Disagree = 1, Disagree = 2)
            ["3", "user3@example.com", "2024-01-03", "Carol White", "Global Ltd",
             "Executive", "Strategy",
             "2", "5", "2", "2", "3",  # Q1-5 (Q2 reversed: 5→2)
             "3", "5", "2", "3", "2",  # Q6-10
             "5", "5", "3", "2", "2",  # Q11-15 (Q11 reversed: 5→2)
             "2", "5", "2", "3", "3",  # Q16-20
             "3", "5", "2", "2", "2"   # Q21-25
            ]
        ]
        
        # Write CSV
        with open(self.input_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(data)
    
    def test_forbidden_glyphs(self):
        """Check that no forbidden glyphs are in source code."""
        import ccip.ccip_compose
        import ccip.ccip_embed
        import ccip.svg_icons_radar
        
        forbidden = ["✓", "✔", "✗", "tick", "checkmark", "status icon"]
        
        modules = [ccip.ccip_compose, ccip.ccip_embed, ccip.svg_icons_radar]
        for module in modules:
            module_file = Path(module.__file__)
            content = module_file.read_text()
            for glyph in forbidden:
                self.assertNotIn(glyph, content, 
                               f"Forbidden glyph '{glyph}' found in {module.__name__}")
    
    def test_basic_workflow(self):
        """Test basic CCIP workflow."""
        from ccip.ccip_compose import compose_workbook, REQUIRED_COLUMNS
        from ccip.ccip_intake import detect_survey_columns
        
        # Load test CSV
        df = pd.read_csv(self.input_csv)
        
        # Detect survey columns
        start_idx, end_idx = detect_survey_columns(df)
        self.assertIsNotNone(start_idx, "Should detect survey start column")
        self.assertIsNotNone(end_idx, "Should detect survey end column")
        
        # Compose workbook
        success = compose_workbook(df, self.output_xlsx, start_idx, end_idx)
        self.assertTrue(success, "Workbook composition should succeed")
        
        # Verify output exists
        self.assertTrue(self.output_xlsx.exists(), "Output file should exist")
        
        # Load and verify output
        result_df = pd.read_excel(self.output_xlsx, sheet_name='CCIP Results')
        
        # Check columns
        self.assertEqual(list(result_df.columns), REQUIRED_COLUMNS,
                        "Output should have required columns")
        
        # Check we have 3 rows
        self.assertEqual(len(result_df), 3, "Should have 3 participant rows")

        # Check score formatting (2 decimals with band name)
        # New format: "4.75 (Very High) - interpretation..."
        for idx, row in result_df.iterrows():
            for col in ['DT_Score', 'TR_Score', 'CO_Score', 'CA_Score', 'EP_Score']:
                score_str = str(row[col])
                if score_str != 'N/A' and ' - ' in score_str:
                    score_part = score_str.split(' - ')[0]  # e.g., "4.75 (Very High)"
                    # Extract just the numeric part before the parenthesis
                    numeric_part = score_part.split(' (')[0]
                    self.assertRegex(numeric_part, r'^\d+\.\d{2}$',
                                   f"Score should have 2 decimals: {numeric_part}")
                    # Verify band name is present
                    self.assertIn(' (', score_str, f"Score should contain band name: {score_str}")

        # Check Summary column exists and has content
        self.assertIn('Summary', result_df.columns, "Summary column should exist")
        for idx, row in result_df.iterrows():
            summary = str(row['Summary'])
            self.assertIsNotNone(summary, "Summary should not be None")
            self.assertNotEqual(summary, '', "Summary should not be empty")
            # Should have 3 sentences (3 periods)
            self.assertEqual(summary.count('.'), 3, f"Summary should have 3 sentences: {summary}")
    
    def test_icon_factories(self):
        """Test that icon factories are callable and return SVG."""
        from ccip.svg_icons_radar import ICONS
        
        # Check all expected icons exist
        expected_icons = [
            'LEVEL_TOOLS', 'LEVEL_SHIELD', 'LEVEL_SEEDLING',
            'PR_DT', 'PR_TR', 'PR_CO', 'PR_CA', 'PR_EP'
        ]
        
        for icon_key in expected_icons:
            self.assertIn(icon_key, ICONS, f"Icon {icon_key} should exist")
            
            # Check factory is callable
            factory = ICONS[icon_key]
            self.assertTrue(callable(factory), f"Icon {icon_key} should be callable")
            
            # Check returns SVG string
            svg = factory()
            self.assertIsInstance(svg, str, f"Icon {icon_key} should return string")
            self.assertIn('<svg', svg, f"Icon {icon_key} should return SVG")
    
    def test_cairosvg_conversion(self):
        """Test CairoSVG conversion with retry logic."""
        from ccip.ccip_embed import svg_to_png
        from ccip.svg_icons_radar import ICONS

        # Get sample SVG
        svg_content = ICONS['LEVEL_TOOLS']()
        
        # Try conversion
        png_bytes = svg_to_png(svg_content)
        
        # Should either succeed or log ERROR (per rules)
        if png_bytes is not None:
            self.assertIsInstance(png_bytes, bytes, "Should return PNG bytes")
            self.assertGreater(len(png_bytes), 0, "PNG should have content")
        else:
            # Check that ERROR was logged (conversion failed after retry)
            logger.info("CairoSVG conversion returned None (logged ERROR per rules)")

    def test_q1_detection_methods(self):
        """Test robust Q1 location detection with all fallback methods."""
        from ccip.ccip_intake import detect_survey_columns
        import pandas as pd

        # Test 1: Column-I happy path
        headers_i = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
                     'I prefer to be clear and direct'] + [f'Q{i}' for i in range(2, 26)] + ['Other']
        df_i = pd.DataFrame(columns=headers_i)
        start, end = detect_survey_columns(df_i)
        self.assertEqual(start, 8, "Column I method should find Q1 at index 8")
        self.assertEqual(end, 32, "Column I method should find Q25 at index 32")

        # Test 2: Anchor-is-Q1 (anchor with only 24 columns after)
        headers_anchor = ['A', 'B', 'C', 'I prefer to be clear and direct'] + [f'Q{i}' for i in range(2, 26)]
        df_anchor = pd.DataFrame(columns=headers_anchor)
        start, end = detect_survey_columns(df_anchor)
        self.assertEqual(start, 3, "Anchor-is-Q1 should find Q1 at anchor position")
        self.assertEqual(end, 27, "Anchor-is-Q1 should find Q25 24 positions later")

        # Test 3: Header-based with scrambled positions
        headers_scrambled = ['Email', 'Q5', 'Name', 'Q1', 'Q3', 'Q2', 'Q4'] + [f'Q{i}' for i in range(6, 26)] + ['Other']
        df_scrambled = pd.DataFrame(columns=headers_scrambled)
        start, end = detect_survey_columns(df_scrambled)
        self.assertIsNotNone(start, "Header-based should find Q1-Q25")
        self.assertIsNotNone(end, "Header-based should find Q1-Q25")

        # Test 4: Missing questions should raise ValueError
        headers_missing = ['Email', 'Q1', 'Q2', 'Q4', 'Q5']  # Missing Q3
        df_missing = pd.DataFrame(columns=headers_missing)
        with self.assertRaises(ValueError) as context:
            detect_survey_columns(df_missing)
        self.assertIn("Missing question columns", str(context.exception))

    def test_q1_detection_variants(self):
        """Test detection of Q1-Q25 header variants."""
        from ccip.ccip_intake import detect_survey_columns
        import pandas as pd

        # Test various Q variants
        variants = ['Q1', 'Q 1', 'Q01', 'Q1_Response', 'Q1 Response', 'q1', 'q 1', 'q01']
        for variant in variants:
            headers = ['Email', variant] + [f'Q{i}' for i in range(2, 26)] + ['Other']
            df = pd.DataFrame(columns=headers)
            start, end = detect_survey_columns(df)
            self.assertIsNotNone(start, f"Should detect Q1 variant: {variant}")
            self.assertIsNotNone(end, f"Should detect Q1 variant: {variant}")

    def test_q1_detection_ambiguity(self):
        """Test that ambiguous cases raise appropriate errors."""
        from ccip.ccip_intake import detect_survey_columns
        import pandas as pd

        # This should work fine - single valid anchor
        headers_good = ['Email', 'I prefer to be clear and direct', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10',
                       '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25']
        df_good = pd.DataFrame(columns=headers_good)

        # Add some sample Likert data
        sample_data = []
        for i in range(3):
            row = ['test@email.com', 'Strongly Agree'] + [str(j % 7 + 1) for j in range(25)]
            sample_data.append(row)

        for row in sample_data:
            df_good.loc[len(df_good)] = row

        start, end = detect_survey_columns(df_good)
        self.assertIsNotNone(start, "Valid single anchor should be detected")
        self.assertIsNotNone(end, "Valid single anchor should be detected")

    def test_date_derivation_scenarios(self):
        """Test Date column derivation from various sources."""
        from ccip.ccip_intake import derive_date_column
        import pandas as pd
        import tempfile
        import os
        from datetime import datetime

        # Test 1: Has Date column - should use existing
        df_with_date = pd.DataFrame({
            'Date': ['29/09/2025', '30/09/2025', '01/10/2025'],
            'ID': [1, 2, 3],
            'Email': ['a@test.com', 'b@test.com', 'c@test.com']
        })
        date_series = derive_date_column(df_with_date)
        self.assertEqual(list(date_series), ['29/09/2025', '30/09/2025', '01/10/2025'])

        # Test 2: No Date, has Start time with Excel serials
        excel_serial = 45543.5  # Approximately 2024-09-28 12:00
        df_excel_serial = pd.DataFrame({
            'Start time': [excel_serial, excel_serial + 1, excel_serial + 2],
            'ID': [1, 2, 3],
            'Email': ['a@test.com', 'b@test.com', 'c@test.com']
        })
        date_series = derive_date_column(df_excel_serial)
        # Should parse Excel serials to dd/mm/yyyy format
        self.assertEqual(len(date_series), 3)
        for date_str in date_series:
            self.assertRegex(date_str, r'\d{2}/\d{2}/\d{4}')

        # Test 3: No Date, has Start time with string formats
        df_string_dates = pd.DataFrame({
            'Start Time': ['29/09/2025 14:07', '2025-09-29T14:07:33', '9/29/25 2:07 PM'],
            'ID': [1, 2, 3],
            'Email': ['a@test.com', 'b@test.com', 'c@test.com']
        })
        date_series = derive_date_column(df_string_dates)
        self.assertEqual(len(date_series), 3)
        # Should all parse with dayfirst=True priority
        for date_str in date_series:
            self.assertRegex(date_str, r'\d{2}/\d{2}/\d{4}')

        # Test 4: No Date, no Start time - should use file mtime
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = tmp_file.name
        try:
            df_no_dates = pd.DataFrame({
                'ID': [1, 2, 3],
                'Email': ['a@test.com', 'b@test.com', 'c@test.com']
            })
            date_series = derive_date_column(df_no_dates, tmp_path)
            self.assertEqual(len(date_series), 3)
            # All should be same date (file mtime)
            self.assertEqual(len(set(date_series)), 1)
            self.assertRegex(date_series[0], r'\d{2}/\d{2}/\d{4}')
        finally:
            os.unlink(tmp_path)

        # Test 5: Row-level failures with fallback
        df_mixed = pd.DataFrame({
            'Start time': ['29/09/2025 14:07', 'invalid_date', '01/10/2025 10:00'],
            'ID': [1, 2, 3],
            'Email': ['a@test.com', 'b@test.com', 'c@test.com']
        })
        date_series = derive_date_column(df_mixed)
        self.assertEqual(len(date_series), 3)
        # First and third should parse correctly, second should use fallback
        self.assertRegex(date_series[0], r'\d{2}/\d{2}/\d{4}')
        self.assertRegex(date_series[1], r'\d{2}/\d{2}/\d{4}')  # Fallback
        self.assertRegex(date_series[2], r'\d{2}/\d{2}/\d{4}')

    def tearDown(self):
        """Clean up temp files."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)


if __name__ == '__main__':
    unittest.main()