"""Pytest configuration: register custom markers."""

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "network: tests that require live network access to Crossref, arXiv, etc."
    )
