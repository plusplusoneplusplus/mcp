#!/usr/bin/env python3
"""
Test script to verify that MSBuild output doesn't trigger false positive secret detection.

This script reads the example MSBuild output and runs it through the secret scanner
to ensure that no legitimate build information is incorrectly flagged as secrets.
"""

import os
from pathlib import Path

from utils.secret_scanner import check_secrets, redact_secrets


def test_msbuild_output():
    """Test the MSBuild output for false positive secret detection."""
    
    # Get the path to the MSBuild fixture file
    test_dir = Path(__file__).parent
    msbuild_file = test_dir / "fixtures" / "msbuild_vcx_example.txt"
    
    if not msbuild_file.exists():
        print(f"Error: {msbuild_file} not found!")
        return False
    
    with open(msbuild_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("=" * 80)
    print("TESTING MSBUILD OUTPUT FOR SECRET DETECTION")
    print("=" * 80)
    print(f"File: {msbuild_file}")
    print(f"Content length: {len(content)} characters")
    print(f"Number of lines: {len(content.splitlines())}")
    print()
    
    # Check for secrets
    print("Running secret detection...")
    findings = check_secrets(content)
    
    print(f"Number of potential secrets detected: {len(findings)}")
    print()
    
    if findings:
        print("⚠️  POTENTIAL ISSUES DETECTED:")
        print("-" * 40)
        for i, finding in enumerate(findings, 1):
            print(f"{i}. Line {finding['LineNumber']}: {finding['SecretType']}")
            print(f"   Value: {finding['SecretValue'][:50]}{'...' if len(finding['SecretValue']) > 50 else ''}")
            print(f"   Rule: {finding['RuleID']}")
            print()
        
        # Test redaction
        print("Testing redaction...")
        redacted_content, redaction_findings = redact_secrets(content)
        
        # Show what would be redacted
        original_lines = content.splitlines()
        redacted_lines = redacted_content.splitlines()
        
        print("Lines that would be modified by redaction:")
        for i, (orig, redacted) in enumerate(zip(original_lines, redacted_lines)):
            if orig != redacted:
                print(f"Line {i+1}:")
                print(f"  Original: {orig}")
                print(f"  Redacted: {redacted}")
                print()
        
        return False
    else:
        print("✅ SUCCESS: No secrets detected in MSBuild output!")
        print("The secret detection correctly identified this as legitimate build output.")
        
        # Verify redaction doesn't change anything
        redacted_content, redaction_findings = redact_secrets(content)
        if content == redacted_content:
            print("✅ SUCCESS: Redaction leaves content unchanged (as expected).")
        else:
            print("❌ ERROR: Redaction modified content even though no secrets were detected!")
            return False
        
        return True


def test_with_actual_secrets():
    """Test that the scanner still detects actual secrets when mixed with build output."""
    
    print("\n" + "=" * 80)
    print("TESTING WITH ACTUAL SECRETS MIXED IN")
    print("=" * 80)
    
    # Create content with actual secrets mixed in
    test_content = """
Microsoft (R) Build Engine version 17.8.3+195e7f5a3 for .NET Framework
Build started 1/15/2024 2:30:45 PM.
Connection string: Server=localhost;Database=MyDB;User=admin;Password=SuperSecret123!@#;
ClCompile:
  C:\\Program Files\\Microsoft Visual Studio\\2022\\Professional\\VC\\Tools\\MSVC\\14.38.33130\\bin\\HostX64\\x64\\cl.exe
API_KEY=sk-1234567890abcdef1234567890abcdef1234567890abcdef
Build succeeded.
    0 Warning(s)
    0 Error(s)
"""
    
    print("Testing content with actual secrets mixed in...")
    findings = check_secrets(test_content)
    
    print(f"Number of potential secrets detected: {len(findings)}")
    
    if findings:
        print("✅ SUCCESS: Scanner correctly detected secrets in mixed content:")
        for finding in findings:
            print(f"  - Line {finding['LineNumber']}: {finding['SecretType']}")
        
        # Test redaction
        redacted_content, _ = redact_secrets(test_content)
        if "[REDACTED]" in redacted_content:
            print("✅ SUCCESS: Secrets were properly redacted.")
            
            # Show redacted lines
            print("\nRedacted content preview:")
            for i, line in enumerate(redacted_content.splitlines()[:10], 1):
                if "[REDACTED]" in line:
                    print(f"  Line {i}: {line}")
        else:
            print("❌ ERROR: Secrets were not redacted!")
            return False
        
        return True
    else:
        print("❌ ERROR: Scanner failed to detect actual secrets!")
        return False


def test_msbuild_secret_detection():
    """Main test function for pytest compatibility."""
    print("MSBuild Secret Detection Test")
    print("This test verifies that legitimate MSBuild output doesn't trigger false positives")
    print("while ensuring that actual secrets would still be detected.\n")
    
    # Test 1: Clean MSBuild output should not trigger detection
    test1_passed = test_msbuild_output()
    
    # Test 2: Mixed content with actual secrets should trigger detection
    test2_passed = test_with_actual_secrets()
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Test 1 (Clean MSBuild): {'PASSED' if test1_passed else 'FAILED'}")
    print(f"Test 2 (Mixed Content): {'PASSED' if test2_passed else 'FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("The secret detection is working correctly for MSBuild output.")
        assert True
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("The secret detection may need adjustment for MSBuild output.")
        assert False, "MSBuild secret detection tests failed"


if __name__ == "__main__":
    test_msbuild_secret_detection() 