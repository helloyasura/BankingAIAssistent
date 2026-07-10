import importlib
import unittest


class AppImportTest(unittest.TestCase):
    def test_app_main_imports(self) -> None:
        module = importlib.import_module("app.main")
        self.assertTrue(hasattr(module, "app"))


if __name__ == "__main__":
    unittest.main()
