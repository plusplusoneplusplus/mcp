"""
Test helpers for azrepo plugin tests.
"""

from unittest.mock import patch


def patch_azure_utils_env_manager(func=None):
    """
    Helper decorator to patch both workitem_tool.env_manager and azure_rest_utils.env_manager.

    This decorator can be used to simplify the nested patching in tests after the refactoring
    that moved common utilities to azure_rest_utils.py.

    Usage:
        @patch_azure_utils_env_manager
        def test_something(self, mock_env_manager, mock_rest_env_manager):
            # Configure both mock managers
            mock_env_manager.get_azrepo_parameters.return_value = {...}
            mock_rest_env_manager.get_azrepo_parameters.return_value = {...}

    Or with an existing patch:
        @patch("something.else")
        @patch_azure_utils_env_manager
        def test_something(self, mock_env_manager, mock_rest_env_manager, mock_something_else):
            ...
    """
    if func is None:
        # Being used as a decorator factory
        return patch_azure_utils_env_manager

    # Apply both patches
    patched = patch("plugins.azrepo.workitem_tool.env_manager")(func)
    return patch("plugins.azrepo.azure_rest_utils.env_manager")(patched)
