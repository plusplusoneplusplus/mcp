#!/usr/bin/env python3
"""
Integration test to demonstrate MSBuild output working correctly with the YAML tools security filtering.

This test simulates how the MSBuild output would be processed by the YAML tools system
and verifies that no legitimate build information is incorrectly redacted.
"""

import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import pytest

from utils.secret_scanner import check_secrets, redact_secrets
from mcp_tools.yaml_tools import YamlToolBase


class MockCommandExecutor:
    """Mock command executor that returns our MSBuild output."""

    def __init__(self, msbuild_output: str):
        self.msbuild_output = msbuild_output

    async def execute_async(self, command: str, timeout=None):
        return {"token": "test-token", "status": "running", "pid": 12345}

    async def query_process(self, token: str, wait=False, timeout=None):
        return {
            "status": "completed",
            "success": True,
            "output": self.msbuild_output,
            "error": "",
            "return_code": 0
        }


async def test_msbuild_with_yaml_tools():
    """Test MSBuild output processing through the YAML tools system."""
    
    print("=" * 80)
    print("TESTING MSBUILD OUTPUT WITH YAML TOOLS SECURITY FILTERING")
    print("=" * 80)
    
    # Get the path to the MSBuild fixture file
    test_dir = Path(__file__).parent
    msbuild_file = test_dir / "fixtures" / "msbuild_vcx_example.txt"
    
    if not msbuild_file.exists():
        print(f"Error: {msbuild_file} not found!")
        return False
    
    with open(msbuild_file, 'r', encoding='utf-8') as f:
        msbuild_output = f.read()
    
    print(f"Loaded MSBuild output: {len(msbuild_output)} characters, {len(msbuild_output.splitlines())} lines")
    
    # Create a mock command executor with our MSBuild output
    mock_executor = MockCommandExecutor(msbuild_output)
    
    # Create a YAML tool configuration for MSBuild
    tool_data = {
        "type": "script",
        "scripts": {"darwin": "msbuild MyApp.sln /p:Configuration=Release /p:Platform=x64"},
        "post_processing": {
            "security_filtering": {
                "enabled": True,
                "apply_to": ["stdout", "stderr"],
                "log_findings": True
            }
        },
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    }
    
    # Create the YAML tool
    tool = YamlToolBase(
        tool_name="msbuild_tool",
        tool_data=tool_data,
        command_executor=mock_executor
    )
    
    print("\nTesting YAML tool execution with security filtering...")
    
    # Execute the tool and check the results
    with patch('mcp_tools.yaml_tools.logger') as mock_logger:
        result = await tool._query_status({"token": "test-token"})
    
    # Verify the results
    if not result or len(result) == 0:
        print("❌ ERROR: No result returned from tool execution!")
        return False
    
    result_text = result[0]["text"]
    
    # Check that the output contains expected MSBuild content
    expected_content = [
        "Microsoft (R) Build Engine",
        "Build succeeded",
        "MyApp.vcxproj",
        "ClCompile:",
        "Link:",
        "Time Elapsed"
    ]
    
    missing_content = []
    for content in expected_content:
        if content not in result_text:
            missing_content.append(content)
    
    if missing_content:
        print(f"❌ ERROR: Missing expected content: {missing_content}")
        print(f"Result text preview: {result_text[:500]}...")
        return False
    
    # Check that no content was redacted (should be no [REDACTED] markers)
    if "[REDACTED]" in result_text:
        print("❌ ERROR: Content was incorrectly redacted!")
        print("Redacted content found in result:")
        for i, line in enumerate(result_text.splitlines(), 1):
            if "[REDACTED]" in line:
                print(f"  Line {i}: {line}")
        return False
    
    # Verify that no security warnings were logged
    security_warnings = [call for call in mock_logger.warning.call_args_list 
                        if "SECURITY ALERT" in str(call)]
    
    if security_warnings:
        print("❌ ERROR: Security warnings were logged for clean MSBuild output!")
        for warning in security_warnings:
            print(f"  Warning: {warning}")
        return False
    
    print("✅ SUCCESS: MSBuild output processed correctly through YAML tools!")
    print("✅ SUCCESS: No content was incorrectly redacted!")
    print("✅ SUCCESS: No false positive security alerts!")
    
    return True


async def test_msbuild_with_secrets():
    """Test that secrets are still detected when mixed with MSBuild output."""
    
    print("\n" + "=" * 80)
    print("TESTING MSBUILD OUTPUT WITH ACTUAL SECRETS")
    print("=" * 80)
    
    # Create MSBuild output with actual secrets
    msbuild_with_secrets = """
Microsoft (R) Build Engine version 17.8.3+195e7f5a3 for .NET Framework
Build started 1/15/2024 2:30:45 PM.
ClCompile:
  C:\\Program Files\\Microsoft Visual Studio\\2022\\Professional\\VC\\Tools\\MSVC\\14.38.33130\\bin\\HostX64\\x64\\cl.exe
  main.cpp
  utils.cpp
  Generating Code...
Link:
  C:\\Program Files\\Microsoft Visual Studio\\2022\\Professional\\VC\\Tools\\MSVC\\14.38.33130\\bin\\HostX64\\x64\\link.exe
  MyApp.vcxproj -> C:\\Projects\\MyApp\\x64\\Release\\MyApp.exe
Build succeeded.
    0 Warning(s)
    0 Error(s)

# This is where secrets might accidentally be included:
Database connection: Server=localhost;Database=MyDB;User=admin;Password=SuperSecret123!@#;
API_KEY=sk-1234567890abcdef1234567890abcdef1234567890abcdef
SECRET_TOKEN=ghp_1234567890abcdef1234567890abcdef123456

Time Elapsed 00:00:12.34
"""
    
    # Create mock executor
    mock_executor = MockCommandExecutor(msbuild_with_secrets)
    
    # Create tool with security filtering
    tool_data = {
        "type": "script",
        "scripts": {"darwin": "msbuild MyApp.sln"},
        "post_processing": {
            "security_filtering": {
                "enabled": True,
                "apply_to": ["stdout", "stderr"],
                "log_findings": True
            }
        },
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    }
    
    tool = YamlToolBase(
        tool_name="msbuild_with_secrets",
        tool_data=tool_data,
        command_executor=mock_executor
    )
    
    print("Testing YAML tool execution with secrets in MSBuild output...")
    
    # Execute the tool
    with patch('mcp_tools.yaml_tools.logger') as mock_logger:
        result = await tool._query_status({"token": "test-token"})
    
    result_text = result[0]["text"]
    
    # Check that secrets were redacted
    if "[REDACTED]" not in result_text:
        print("❌ ERROR: Secrets were not redacted!")
        return False
    
    # Check that legitimate MSBuild content is still present
    if "Microsoft (R) Build Engine" not in result_text or "Build succeeded" not in result_text:
        print("❌ ERROR: Legitimate MSBuild content was incorrectly removed!")
        return False
    
    # Check that security warnings were logged
    security_warnings = [call for call in mock_logger.warning.call_args_list 
                        if "SECURITY ALERT" in str(call)]
    
    if not security_warnings:
        print("❌ ERROR: No security warnings were logged for content with secrets!")
        return False
    
    print("✅ SUCCESS: Secrets were properly detected and redacted!")
    print("✅ SUCCESS: Legitimate MSBuild content was preserved!")
    print("✅ SUCCESS: Security alerts were properly logged!")
    
    # Show what was redacted
    print("\nRedacted content preview:")
    for i, line in enumerate(result_text.splitlines(), 1):
        if "[REDACTED]" in line:
            print(f"  Line {i}: {line}")
    
    return True


@pytest.mark.asyncio
async def test_msbuild_integration():
    """Main integration test function for pytest compatibility."""
    print("MSBuild Integration Test with YAML Tools Security Filtering")
    print("This test demonstrates that MSBuild output works correctly with the security filtering system.")
    print()
    
    # Test 1: Clean MSBuild output should not be redacted
    test1_passed = await test_msbuild_with_yaml_tools()
    
    # Test 2: MSBuild output with secrets should have secrets redacted but build info preserved
    test2_passed = await test_msbuild_with_secrets()
    
    print("\n" + "=" * 80)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 80)
    print(f"Test 1 (Clean MSBuild): {'PASSED' if test1_passed else 'FAILED'}")
    print(f"Test 2 (MSBuild with Secrets): {'PASSED' if test2_passed else 'FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("The MSBuild output works correctly with the YAML tools security filtering system.")
        print("✅ No false positives on legitimate build output")
        print("✅ Real secrets are still detected and redacted")
        print("✅ Security logging works as expected")
        assert True
    else:
        print("\n❌ SOME INTEGRATION TESTS FAILED!")
        assert False, "MSBuild integration tests failed"


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_msbuild_integration()) 