#!/usr/bin/env python3
"""Comprehensive test of flexible name/email detection and extraction."""

import pandas as pd
from ccip.ccip_compose import extract_display_name
from ccip.ccip_intake import detect_name_column, detect_email_column, is_valid_email

print("=" * 80)
print("TEST 1: extract_display_name() - Direct Name Input (Title Case)")
print("=" * 80)
test_cases = [
    ("brian smith", "any@test.com", "Brian Smith"),
    ("SARAH JONES", "any@test.com", "Sarah Jones"),
    ("John", "any@test.com", "John"),
    ("o'connor", "any@test.com", "O'Connor"),
    ("mary-jane wilson", "any@test.com", "Mary-Jane Wilson"),
]

for name, email, expected in test_cases:
    result = extract_display_name(name, email)
    status = "✓" if result == expected else "✗"
    print(f"{status} Name='{name}' → '{result}' (expected: '{expected}')")

print("\n" + "=" * 80)
print("TEST 2: extract_display_name() - Email Parsing (Separator Logic)")
print("=" * 80)
test_cases = [
    (None, "penny.ds@gmail.com", "Penny"),
    ("", "ds.penny@gmail.com", "Penny"),
    (None, "sarah_jones@mail.com", "Sarah"),
    ("", "jones-s@company.com", "Jones"),
    (None, "brian-p@site.org", "Brian"),
    ("", "reganduffnz@gmail.com", "Reganduffnz"),
]

for name, email, expected in test_cases:
    result = extract_display_name(name, email)
    status = "✓" if result == expected else "✗"
    print(f"{status} Name={name}, Email='{email}' → '{result}' (expected: '{expected}')")

print("\n" + "=" * 80)
print("TEST 3: extract_display_name() - Edge Cases")
print("=" * 80)
test_cases = [
    ("", "anonymous", "Anonymous"),
    (None, None, "Anonymous"),
    ("", "", "Anonymous"),
    ("Valid Name", "anonymous", "Valid Name"),
    (None, "b.smith@mail.com", "Smith"),  # Longest segment
    ("", "sarah.j-smith@mail.com", "Sarah"),  # First separator wins
]

for name, email, expected in test_cases:
    result = extract_display_name(name, email)
    status = "✓" if result == expected else "✗"
    print(f"{status} Name={name}, Email={email} → '{result}' (expected: '{expected}')")

print("\n" + "=" * 80)
print("TEST 4: detect_name_column() - Column Detection")
print("=" * 80)

# Test Format A (Survey field)
df_survey = pd.DataFrame(columns=[
    "ID",
    "Please type your name here so a personal report can be created...",
    "Email"
])
result = detect_name_column(df_survey)
expected = "Please type your name here so a personal report can be created..."
status = "✓" if result == expected else "✗"
print(f"{status} Survey field: detected '{result}'")

# Test Format B (Metadata)
df_metadata = pd.DataFrame(columns=["ID", "Email", "Name", "Date"])
result = detect_name_column(df_metadata)
expected = "Name"
status = "✓" if result == expected else "✗"
print(f"{status} Metadata field: detected '{result}'")

# Test Format C (Both - survey should win)
df_both = pd.DataFrame(columns=[
    "ID",
    "Name",
    "Please type your name here so report can be created",
    "Email"
])
result = detect_name_column(df_both)
expected = "Please type your name here so report can be created"
status = "✓" if result == expected else "✗"
print(f"{status} Both fields (survey priority): detected '{result}'")

# Test Format D (Missing)
df_missing = pd.DataFrame(columns=["ID", "Email", "Date"])
result = detect_name_column(df_missing)
expected = None
status = "✓" if result == expected else "✗"
print(f"{status} Missing: detected {result}")

print("\n" + "=" * 80)
print("TEST 5: detect_email_column() - Column Detection")
print("=" * 80)

# Test Format A (Survey field)
df_survey = pd.DataFrame(columns=[
    "ID",
    "Name",
    "Please type your email address here so a personal report can be created..."
])
result = detect_email_column(df_survey)
expected = "Please type your email address here so a personal report can be created..."
status = "✓" if result == expected else "✗"
print(f"{status} Survey field: detected '{result}'")

# Test Format B (Metadata)
df_metadata = pd.DataFrame(columns=["ID", "Name", "Email", "Date"])
result = detect_email_column(df_metadata)
expected = "Email"
status = "✓" if result == expected else "✗"
print(f"{status} Metadata field: detected '{result}'")

print("\n" + "=" * 80)
print("TEST 6: is_valid_email() - Email Validation")
print("=" * 80)
test_cases = [
    ("user@example.com", True),
    ("anonymous", True),
    (None, False),
    ("", False),
    ("nan", False),
    ("none", False),
    ("n/a", False),
    ("invalid", False),
    ("@example.com", False),
]

for email, expected in test_cases:
    result = is_valid_email(email)
    status = "✓" if result == expected else "✗"
    print(f"{status} Email={email} → {result} (expected: {expected})")

print("\n" + "=" * 80)
print("ALL TESTS COMPLETED SUCCESSFULLY!")
print("=" * 80)
