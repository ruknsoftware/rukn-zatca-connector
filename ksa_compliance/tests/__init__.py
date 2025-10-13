"""
Tests module for KSA Compliance

This module is required for Frappe's parallel test runner to work properly.
It provides a minimal interface that satisfies the parallel test runner's requirements.

The parallel test runner expects this module to exist and be importable.
We don't need to import anything specific since the test discovery
happens through file system scanning, not through this module.
"""

# Ensure the module is properly importable
__version__ = "1.0.0"
__all__ = []

# This is a minimal module that just needs to exist for the parallel test runner
# The actual test discovery happens through file system scanning
