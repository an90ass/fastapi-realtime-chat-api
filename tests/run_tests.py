"""
Self-contained test runner script.
Can be run directly via: python tests/run_tests.py
Executes all unit tests, integration tests, and websocket tests without requiring pytest.
In CI/CD (GitHub Actions), pytest will run automatically via pytest.ini.
"""

import inspect
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from tests.conftest import test_client
import tests.integration.test_auth_api as test_auth_api
import tests.integration.test_chat_api as test_chat_api
import tests.integration.test_rooms_api as test_rooms_api
import tests.websocket.test_websocket_chat as test_websocket_chat


def run_standalone_test_functions():
    """Runs functional test cases that accept test_client fixture."""
    modules = [test_auth_api, test_rooms_api, test_chat_api, test_websocket_chat]
    total_passed = 0
    total_failed = 0

    print("\n--- Running Integration & WebSocket Test Cases ---")
    for mod in modules:
        for name, obj in inspect.getmembers(mod):
            if name.startswith("test_") and inspect.isfunction(obj):
                sys.stdout.write(f"Running {mod.__name__}.{name} ... ")
                sys.stdout.flush()
                try:
                    # Provide fresh test_client
                    for client in test_client():
                        obj(client)
                    print("PASSED")
                    total_passed += 1
                except Exception as exc:
                    print(f"FAILED: {exc}")
                    total_failed += 1

    return total_passed, total_failed


def main():
    # 1. Run unittest test cases (Architecture and Service Unit Tests)
    print("--- Running Unit Tests ---")
    loader = unittest.TestLoader()
    suite = loader.discover("tests/unit", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 2. Run standalone functional test cases
    passed, failed = run_standalone_test_functions()

    print("\n==========================================")
    print(f"Unit Tests: {result.testsRun} run, {len(result.failures)} failures, {len(result.errors)} errors")
    print(f"Integration & WS Tests: {passed + failed} run, {passed} passed, {failed} failed")
    print("==========================================")

    if not result.wasSuccessful() or failed > 0:
        sys.exit(1)
    else:
        print("ALL TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)


if __name__ == "__main__":
    main()
