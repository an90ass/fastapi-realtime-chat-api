import ast
import pathlib
import unittest


def _extract_imported_modules(source_code: str) -> set[str]:
    """Parse python source using AST and extract all top-level imported module names."""
    tree = ast.parse(source_code)
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module.split(".")[0])
                # Also track full module path to check internal layer boundaries
                modules.add(node.module)
    return modules


class TestArchitectureLayerIsolation(unittest.TestCase):
    """
    Automated architectural guardrail tests.
    Enforces Clean Architecture layer boundaries via AST inspection.
    """

    def setUp(self):
        self.root_dir = pathlib.Path(__file__).resolve().parent.parent.parent
        self.domain_dir = self.root_dir / "app" / "domain"
        self.app_dir = self.root_dir / "app" / "application"

    def test_domain_layer_has_zero_framework_dependencies(self):
        """Domain layer must not import FastAPI, SQLAlchemy, Redis, Pydantic, or Infrastructure."""
        forbidden = {"fastapi", "sqlalchemy", "redis", "pydantic", "app.infrastructure", "app.presentation"}
        domain_files = [f for f in self.domain_dir.rglob("*.py") if f.name != "__init__.py"]
        self.assertGreater(len(domain_files), 0, "No domain files found to test.")

        for py_file in domain_files:
            source = py_file.read_text(encoding="utf-8")
            imported = _extract_imported_modules(source)
            violations = imported & forbidden
            self.assertEqual(
                violations,
                set(),
                f"Architecture violation in domain file {py_file.name}: imports forbidden modules {violations}",
            )

    def test_application_layer_has_zero_framework_dependencies(self):
        """Application layer must not import FastAPI, SQLAlchemy, Redis, or Infrastructure."""
        forbidden = {"fastapi", "sqlalchemy", "redis", "app.infrastructure", "app.presentation"}
        app_files = [f for f in self.app_dir.rglob("*.py") if f.name != "__init__.py"]
        self.assertGreater(len(app_files), 0, "No application files found to test.")

        for py_file in app_files:
            source = py_file.read_text(encoding="utf-8")
            imported = _extract_imported_modules(source)
            violations = imported & forbidden
            self.assertEqual(
                violations,
                set(),
                f"Architecture violation in application file {py_file.name}: imports forbidden modules {violations}",
            )

    def test_application_services_do_not_import_redis_client(self):
        """Application services must depend on IMessageBroker, never on concrete redis_client."""
        service_files = list((self.app_dir / "services").glob("*.py"))
        for py_file in service_files:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    segment = ast.get_source_segment(py_file.read_text(encoding="utf-8"), node) or ""
                    self.assertNotIn(
                        "redis_client",
                        segment,
                        f"DIP violation: {py_file.name} directly imports redis_client instead of IMessageBroker",
                    )


if __name__ == "__main__":
    unittest.main()
