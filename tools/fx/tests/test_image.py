import base64
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import image_openrouter

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a4VQAAAAASUVORK5CYII=")


def response(data=PNG, mime="image/png"):
    return {"id": "generation-1", "usage": {"cost": 0.03}, "choices": [{"message": {
        "images": [{"image_url": {"url": f"data:{mime};base64,{base64.b64encode(data).decode()}"}}]}}]}


class ImageTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_input_and_prompt_become_a_multimodal_request(self):
        original = self.root / "original.png"
        original.write_bytes(PNG)
        payload = image_openrouter.image_request("google/gemini-nano-banana-2.1", "Change background", [original])
        self.assertEqual(payload["modalities"], ["image", "text"])
        content = payload["messages"][0]["content"]
        self.assertEqual(content[0], {"type": "text", "text": "Change background"})
        self.assertEqual(base64.b64decode(content[1]["image_url"]["url"].split(",", 1)[1]), PNG)
        for prompt in ("", "   "):
            with self.assertRaises(ValueError):
                image_openrouter.image_request("google/model", prompt, [])
        original.write_bytes(b"not an image")
        with self.assertRaises(ValueError):
            image_openrouter.image_request("google/model", "Prompt", [original])

    def test_response_requires_a_valid_image_data_url(self):
        self.assertEqual(image_openrouter.response_image(response()), (PNG, (".png",)))
        invalid = [{}, {"choices": []}, {"choices": [{"message": {"images": []}}]},
                   {"choices": [{"message": {"images": [{"image_url": {"url": "https://remote/image.png"}}]}}]},
                   response(b"not an image"), response(PNG, "image/jpeg")]
        for body in invalid:
            with self.subTest(body=body), self.assertRaises(ValueError):
                image_openrouter.response_image(body)
        bad = response()
        bad["choices"][0]["message"]["images"][0]["image_url"]["url"] = "data:image/png;base64,!!!"
        with self.assertRaises(ValueError):
            image_openrouter.response_image(bad)

    def test_output_is_complete_and_existing_files_are_preserved(self):
        output = self.root / "output.png"
        image_openrouter.save_image(output, PNG, (".png",))
        self.assertEqual(output.read_bytes(), PNG)
        with self.assertRaises(FileExistsError):
            image_openrouter.save_image(output, b"replacement", (".png",))
        self.assertEqual(output.read_bytes(), PNG)
        with self.assertRaises(ValueError):
            image_openrouter.save_image(self.root / "wrong.jpg", PNG, (".png",))
        self.assertEqual(list(self.root.iterdir()), [output])

    def run_main(self, output, **options):
        argv = ["image_openrouter.py", "--default-model", "google/gemini-nano-banana-2.1",
                "--prompt", "Create an image", "--output", str(output)]
        with patch.object(sys, "argv", argv), patch.object(image_openrouter, "api_key", return_value="test-key"), \
             patch.object(image_openrouter, "verify_model") as verify, \
             patch.object(image_openrouter, "request_json", **options) as request, \
             patch.object(sys, "stdout", new_callable=io.StringIO) as stdout, \
             patch.object(sys, "stderr", new_callable=io.StringIO) as stderr:
            result = image_openrouter.main()
            return result, request, verify, stdout.getvalue(), stderr.getvalue()

    def test_generation_saves_image_and_reports_model_and_usage(self):
        output = self.root / "assets/image.png"
        result, request, verify, stdout, stderr = self.run_main(output, return_value=response())
        self.assertEqual(result, 0)
        self.assertEqual(output.read_bytes(), PNG)
        self.assertEqual(stdout.strip(), str(output))
        metadata = json.loads(stderr)
        self.assertEqual(metadata["model"], "google/gemini-nano-banana-2.1")
        self.assertEqual(metadata["generation_id"], "generation-1")
        self.assertEqual(metadata["usage"], {"cost": 0.03})
        verify.assert_called_once_with("google/gemini-nano-banana-2.1", output="image")
        self.assertEqual(request.call_args.args[0], "/chat/completions")
        self.assertEqual(request.call_args.kwargs, {"key": "test-key", "timeout": 300})

    def test_existing_output_is_rejected_before_billing(self):
        output = self.root / "existing.png"
        output.write_bytes(PNG)
        argv = ["image_openrouter.py", "--default-model", "google/gemini-nano-banana-2.1",
                "--prompt", "Create", "--output", str(output)]
        with patch.object(sys, "argv", argv), patch.object(image_openrouter, "api_key", return_value="test-key"), \
             patch.object(image_openrouter, "request_json") as request, patch.object(sys, "stderr", new_callable=io.StringIO):
            with self.assertRaises(SystemExit):
                image_openrouter.main()
            request.assert_not_called()
        self.assertEqual(output.read_bytes(), PNG)

    def test_request_failure_does_not_write_partial_output(self):
        output = self.root / "image.png"
        with self.assertRaises(SystemExit):
            self.run_main(output, side_effect=ValueError("Request failed"))
        self.assertFalse(output.exists())
        self.assertEqual(list(self.root.iterdir()), [])

    def test_command_dispatch_and_help_work_outside_a_task(self):
        tool = Path(__file__).resolve().parents[1] / "fx"
        for arguments in (("image", "--help"), ("image", "nano", "--help")):
            result = subprocess.run([str(tool), *arguments], cwd=self.root, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--output", result.stdout)
        for backend in ("missing", "../nano", ""):
            result = subprocess.run([str(tool), "image", backend], cwd=self.root, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
