"""Structured logs preserve request identity and exception causes."""

import json
import logging
import unittest

from system1_ops.logging_config import JSONFormatter


class StructuredLogging(unittest.TestCase):
    def test_json_preserves_exception_and_correlation(self):
        try:
            raise ValueError("测试原因")
        except ValueError:
            import sys

            record = logging.LogRecord(
                "system1", logging.ERROR, __file__, 1, "inference_failed request_id=abc", (), sys.exc_info()
            )
        value = json.loads(JSONFormatter().format(record))
        self.assertEqual(value["request_id"], "abc")
        self.assertEqual(value["level"], "ERROR")
        self.assertIn("ValueError: 测试原因", value["exception"])
        self.assertNotIn("\n", JSONFormatter().format(record))
