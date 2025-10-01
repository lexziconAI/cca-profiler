"""Unit tests for robust name/email detection and extraction."""

import pandas as pd
import pytest
from ccip.ccip_intake import (
    detect_name_and_email_robust,
    extract_name_and_email_robust,
    _looks_like_email,
    _looks_like_name,
    _email_to_name
)


class TestRobustDetection:
    """Test robust name/email detection."""
    
    def test_normal_aligned_columns(self):
        """Test case where Name/Email columns are correctly aligned."""
        df = pd.DataFrame({
            'Name': ['John Smith', 'Jane Doe'],
            'Email': ['john@example.com', 'jane@example.com'],
            'Q1': [3, 4]
        })
        
        _, _, name_col, email_col = detect_name_and_email_robust(df)
        assert name_col == 'Name'
        assert email_col == 'Email'
        
        # Test extraction
        row = df.iloc[0]
        name, email = extract_name_and_email_robust(row, name_col, email_col)
        assert name == 'John Smith'
        assert email == 'john@example.com'
    
    def test_swapped_columns(self):
        """Test case where Name contains emails and Email contains names."""
        df = pd.DataFrame({
            'Name': ['john@example.com', 'jane@example.com'],
            'Email': ['John Smith', 'Jane Doe'],
            'Q1': [3, 4]
        })
        
        _, _, name_col, email_col = detect_name_and_email_robust(df)
        # Should detect swap and correct it
        assert name_col == 'Email'  # Should use Email column for names
        assert email_col == 'Name'  # Should use Name column for emails
        
        # Test extraction
        row = df.iloc[0]
        name, email = extract_name_and_email_robust(row, name_col, email_col)
        assert name == 'John Smith'
        assert email == 'john@example.com'
    
    def test_empty_survey_fields_fallback(self):
        """Test fallback to simple columns when survey fields are empty."""
        df = pd.DataFrame({
            'Please type your name here so a personal report can be created - your results will not be shared with anyone': [None, None],
            'Please type your email address here so a personal report can be created - your results will not be shared with anyone': [None, None],
            'Name': ['Alice Johnson', 'Bob Wilson'],
            'Email': ['alice@example.com', 'bob@example.com'],
            'Q1': [3, 4]
        })
        
        _, _, name_col, email_col = detect_name_and_email_robust(df)
        assert name_col == 'Name'
        assert email_col == 'Email'
        
        # Test extraction
        row = df.iloc[0]
        name, email = extract_name_and_email_robust(row, name_col, email_col)
        assert name == 'Alice Johnson'
        assert email == 'alice@example.com'
    
    def test_all_blank_defaults(self):
        """Test defaults when all fields are blank."""
        df = pd.DataFrame({
            'Name': [None, ''],
            'Email': [None, ''],
            'Q1': [3, 4]
        })
        
        _, _, name_col, email_col = detect_name_and_email_robust(df)
        
        # Test extraction with defaults
        row = df.iloc[0]
        name, email = extract_name_and_email_robust(row, name_col, email_col)
        assert name == 'Anonymous'
        assert email == ''  # Blank per specification


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_looks_like_email(self):
        """Test email detection."""
        assert _looks_like_email('john@example.com') == True
        assert _looks_like_email('john.doe@company.co.uk') == True
        assert _looks_like_email('John Smith') == False
        assert _looks_like_email('') == False
        assert _looks_like_email(None) == False
    
    def test_looks_like_name(self):
        """Test name detection."""
        assert _looks_like_name('John Smith') == True
        assert _looks_like_name('Alice') == True
        assert _looks_like_name('john@example.com') == False
        assert _looks_like_name('') == False
        assert _looks_like_name(None) == False
    
    def test_email_to_name(self):
        """Test email to name conversion."""
        assert _email_to_name('john.smith@example.com') == 'John Smith'
        assert _email_to_name('alice_johnson@company.co.uk') == 'Alice Johnson'
        assert _email_to_name('bob-wilson@test.org') == 'Bob Wilson'
        assert _email_to_name('simple@example.com') == 'Simple'


class TestExtractionEdgeCases:
    """Test edge cases in name/email extraction."""
    
    def test_name_has_email_no_email_column(self):
        """Test when name column has email but no email column."""
        df = pd.DataFrame({
            'Name': ['john@example.com'],
            'Q1': [3]
        })
        
        _, _, name_col, email_col = detect_name_and_email_robust(df)
        row = df.iloc[0]
        name, email = extract_name_and_email_robust(row, name_col, email_col)
        
        assert name == 'John'  # Converted from email
        assert email == 'john@example.com'  # Used from name column
    
    def test_email_has_name_no_name_column(self):
        """Test when email column has name but no name column."""
        df = pd.DataFrame({
            'Email': ['John Smith'],
            'Q1': [3]
        })
        
        _, _, name_col, email_col = detect_name_and_email_robust(df)
        row = df.iloc[0]
        name, email = extract_name_and_email_robust(row, name_col, email_col)
        
        assert name == 'John Smith'
        assert email == ''  # Blank per specification
    
    def test_mixed_valid_invalid_data(self):
        """Test handling of mixed valid/invalid data."""
        df = pd.DataFrame({
            'Name': ['John Smith', 'jane@example.com', None, ''],
            'Email': ['john@example.com', 'Jane Doe', 'bob@example.com', None],
            'Q1': [3, 4, 5, 2]
        })
        
        _, _, name_col, email_col = detect_name_and_email_robust(df)
        
        # Test each row - updated expectations based on improved logic
        test_cases = [
            (0, 'John Smith', 'john@example.com'),    # Normal - name from name col, email from email col
            (1, 'Jane Doe', 'jane@example.com'),      # Swapped - name from email col, email from name col  
            (2, 'Bob', 'bob@example.com'),            # Name from email conversion, email from email col
            (3, 'Anonymous', '')                      # All blank - defaults per spec
        ]
        
        for row_idx, expected_name, expected_email in test_cases:
            row = df.iloc[row_idx]
            name, email = extract_name_and_email_robust(row, name_col, email_col)
            assert name == expected_name, f"Row {row_idx}: expected name '{expected_name}', got '{name}'"
            assert email == expected_email, f"Row {row_idx}: expected email '{expected_email}', got '{email}'"


class TestSpecificationCompliance:
    """Test compliance with exact specification requirements."""
    
    def test_case_1_normal(self):
        """Test case 1: Normal case - Name="Dan", Email="d.simms@pdtraining.com.au" """
        df = pd.DataFrame({
            'Name': ['Dan'],
            'Email': ['d.simms@pdtraining.com.au'],
            'Q1': [3]
        })
        
        _, _, name_col, email_col = detect_name_and_email_robust(df)
        row = df.iloc[0]
        name, email = extract_name_and_email_robust(row, name_col, email_col)
        
        assert name == 'Dan'
        assert email == 'd.simms@pdtraining.com.au'
    
    def test_case_2_swapped(self):
        """Test case 2: Swapped case - Name="d.simms@...", Email="Dan" """
        df = pd.DataFrame({
            'Name': ['d.simms@pdtraining.com.au'],
            'Email': ['Dan'],
            'Q1': [3]
        })
        
        _, _, name_col, email_col = detect_name_and_email_robust(df)
        row = df.iloc[0]
        name, email = extract_name_and_email_robust(row, name_col, email_col)
        
        assert name == 'Dan'  # From email column due to swap detection
        assert email == 'd.simms@pdtraining.com.au'  # From name column due to swap detection
    
    def test_case_3_empty_survey_fields(self):
        """Test case 3: Empty survey fields, fallback to simple columns"""
        df = pd.DataFrame({
            'Please type your name here so a personal report can be created - your results will not be shared with anyone': [''],
            'Please type your email address here so a personal report can be created - your results will not be shared with anyone': [''],
            'Name': ['Sarah Wilson'],
            'Email': ['sarah.wilson@company.com'],
            'Q1': [4]
        })
        
        _, _, name_col, email_col = detect_name_and_email_robust(df)
        row = df.iloc[0]
        name, email = extract_name_and_email_robust(row, name_col, email_col)
        
        assert name == 'Sarah Wilson'
        assert email == 'sarah.wilson@company.com'
    
    def test_case_4_only_email_present(self):
        """Test case 4: Only email present, name extracted from local-part"""
        df = pd.DataFrame({
            'Name': [''],
            'Email': ['bob.anderson@example.org'],
            'Q1': [2]
        })
        
        _, _, name_col, email_col = detect_name_and_email_robust(df)
        row = df.iloc[0]
        name, email = extract_name_and_email_robust(row, name_col, email_col)
        
        assert name == 'Bob Anderson'  # Extracted from email local-part
        assert email == 'bob.anderson@example.org'
    
    def test_case_5_both_missing(self):
        """Test case 5: Both missing, name set to "Anonymous", email blank"""
        df = pd.DataFrame({
            'Name': [''],
            'Email': [''],
            'Q1': [5]
        })
        
        _, _, name_col, email_col = detect_name_and_email_robust(df)
        row = df.iloc[0]
        name, email = extract_name_and_email_robust(row, name_col, email_col)
        
        assert name == 'Anonymous'
        assert email == ''  # Blank per specification


if __name__ == '__main__':
    pytest.main([__file__])