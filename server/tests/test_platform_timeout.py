"""Test platform-specific timeout functionality for issue #109."""

import platform
import unittest.mock
import pytest

from server.tests.conftest import get_platform_timeout


class TestPlatformTimeout:
    """Test platform-specific timeout handling."""

    def test_windows_timeout_is_longer(self):
        """Test that Windows gets a longer timeout than other platforms."""
        with unittest.mock.patch('platform.system') as mock_system:
            # Test Windows timeout
            mock_system.return_value = 'Windows'
            windows_timeout = get_platform_timeout()

            # Test Unix timeout
            mock_system.return_value = 'Linux'
            linux_timeout = get_platform_timeout()

            # Test macOS timeout
            mock_system.return_value = 'Darwin'
            macos_timeout = get_platform_timeout()

            # Windows should have longer timeout
            assert windows_timeout > linux_timeout
            assert windows_timeout > macos_timeout
            assert windows_timeout == 60
            assert linux_timeout == 30
            assert macos_timeout == 30

    def test_current_platform_timeout(self):
        """Test that current platform returns a reasonable timeout."""
        timeout = get_platform_timeout()

        # Should be either 30 or 60 seconds
        assert timeout in [30, 60]

        # Should match expected value for current platform
        if platform.system().lower() == 'windows':
            assert timeout == 60
        else:
            assert timeout == 30

    def test_case_insensitive_platform_detection(self):
        """Test that platform detection is case insensitive."""
        with unittest.mock.patch('platform.system') as mock_system:
            # Test various case combinations
            for windows_variant in ['Windows', 'WINDOWS', 'windows', 'WiNdOwS']:
                mock_system.return_value = windows_variant
                assert get_platform_timeout() == 60
