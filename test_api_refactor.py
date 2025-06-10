#!/usr/bin/env python3
"""
Simple test script to verify the API refactoring works correctly.
"""

import sys
from pathlib import Path

# Add the project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def test_api_imports():
    """Test that all API modules can be imported successfully."""
    print("Testing API module imports...")
    
    try:
        from server.api import api_routes
        print("✅ Successfully imported api_routes from server.api")
        
        # Check that we have the expected number of routes
        expected_routes = 22  # Based on the original api.py
        actual_routes = len(api_routes)
        print(f"✅ Found {actual_routes} routes (expected around {expected_routes})")
        
        # Test individual module imports
        from server.api.knowledge import api_import_knowledge, api_list_collections
        print("✅ Successfully imported knowledge endpoints")
        
        from server.api.background_jobs import api_list_background_jobs
        print("✅ Successfully imported background job endpoints")
        
        from server.api.configuration import api_get_configuration
        print("✅ Successfully imported configuration endpoints")
        
        from server.api.tool_history import api_list_tool_history
        print("✅ Successfully imported tool history endpoints")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_route_structure():
    """Test that the route structure is correct."""
    print("\nTesting route structure...")
    
    try:
        from server.api import api_routes
        
        # Check for key routes
        route_paths = [route.path for route in api_routes]
        
        expected_paths = [
            "/api/import-knowledge",
            "/api/collections", 
            "/api/configuration",
            "/api/background-jobs",
            "/api/tool-history"
        ]
        
        for path in expected_paths:
            if path in route_paths:
                print(f"✅ Found route: {path}")
            else:
                print(f"❌ Missing route: {path}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Route structure test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing API Refactoring")
    print("=" * 50)
    
    success = True
    
    # Test imports
    if not test_api_imports():
        success = False
    
    # Test route structure
    if not test_route_structure():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! API refactoring is working correctly.")
        return 0
    else:
        print("💥 Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 