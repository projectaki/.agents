import http.client
import io
import json
import os
from pathlib import Path
import sys
import unittest
import urllib.error
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import openrouter_api


class OpenRouterTest(unittest.TestCase):
    def test_missing_key_has_a_clear_error(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}), self.assertRaisesRegex(ValueError, "Set OPENROUTER_API_KEY"):
            openrouter_api.api_key()

    def test_post_uses_bearer_auth_json_and_timeout(self):
        with patch.object(openrouter_api.urllib.request, "urlopen", return_value=io.BytesIO(b'{"id":"result"}')) as request:
            result = openrouter_api.request_json("/chat/completions", {"model": "google/image"}, key="secret", timeout=300)
        call, = request.call_args.args
        self.assertEqual(call.full_url, "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(call.get_header("Authorization"), "Bearer secret")
        self.assertEqual(json.loads(call.data), {"model": "google/image"})
        self.assertEqual(request.call_args.kwargs["timeout"], 300)
        self.assertEqual(result, {"id": "result"})

    def test_network_http_and_response_errors_do_not_retry_or_expose_body(self):
        errors = [urllib.error.HTTPError("url", 429, "Limited", {"x-request-id": "request-1"}, io.BytesIO(b"secret body")),
                  urllib.error.URLError("Disconnected"), TimeoutError("Timed out"),
                  http.client.IncompleteRead(b"partial")]
        for error in errors:
            with self.subTest(error=error), patch.object(openrouter_api.urllib.request, "urlopen", side_effect=error) as request:
                with self.assertRaises(ValueError) as raised:
                    openrouter_api.request_json("/chat/completions", {}, key="secret")
                self.assertNotIn("secret", str(raised.exception))
                request.assert_called_once()
        for body in (b"[]", b'{"error":{"message":"sensitive details"}}', b"invalid"):
            with self.subTest(body=body), patch.object(openrouter_api.urllib.request, "urlopen", return_value=io.BytesIO(body)):
                with self.assertRaises(ValueError):
                    openrouter_api.request_json("/models")

    def test_catalog_requires_exact_model_and_capabilities(self):
        model = {"id": "minimax/minimax-m3.1-flash", "supported_parameters": ["tools", "reasoning"],
                 "architecture": {"output_modalities": ["text"]}}
        with patch.object(openrouter_api, "request_json", return_value={"data": [model]}):
            self.assertEqual(openrouter_api.verify_model(model["id"], parameters=("tools", "reasoning")), model)
            for supplied, options in ((model["id"] + ":free", {}),
                                      (model["id"], {"output": "image"}),
                                      (model["id"], {"parameters": ("missing",)})):
                with self.subTest(supplied=supplied, options=options), self.assertRaises(ValueError):
                    openrouter_api.verify_model(supplied, **options)
        with patch.object(openrouter_api, "request_json", return_value={"data": {}}), self.assertRaises(ValueError):
            openrouter_api.verify_model("model")


if __name__ == "__main__":
    unittest.main()
