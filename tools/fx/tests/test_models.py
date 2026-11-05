import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agents"))
import codex_launch
import codex_batch
from fx_models import model_slug, session_agent, session_model, validate_model
import test_fx


class ModelTest(unittest.TestCase):
    def test_model_names_and_safe_directory_names(self):
        for model, slug in (("z-ai/glm-5.3", "z-ai-glm-5.3"),
                            ("minimax/minimax-m3.1-flash:free", "minimax-minimax-m3.1-flash-free"),
                            ("~google/gemini-flash-latest", "google-gemini-flash-latest"),
                            ("gpt-6.1-sol", "gpt-6.1-sol")):
            with self.subTest(model=model):
                self.assertEqual(validate_model(model), model)
                self.assertEqual(model_slug(model), slug)
        for model in ("", "-model", "model name", "model\n", 'model"', "$(command)", None):
            with self.subTest(model=model), self.assertRaises(ValueError):
                validate_model(model)

    def test_session_selection_and_legacy_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            self.assertEqual(session_model(session, "default"), "default")
            self.assertEqual(session_agent(session), "codex")
            (session / "model.txt").write_text("z-ai/glm-5.3\n")
            (session / "launch.txt").write_text("agent=glm\nreasoning=high\n")
            self.assertEqual(session_model(session, "default"), "z-ai/glm-5.3")
            self.assertEqual(session_agent(session), "glm")
            (session / "model.txt").unlink()
            (session / "model.txt").symlink_to(session / "launch.txt")
            with self.assertRaises(ValueError):
                session_model(session, "default")

    def test_registered_defaults_and_overrides_without_network(self):
        root = Path(__file__).resolve().parents[1]
        for agent, default in (("glm", "z-ai/glm-5.3"),
                               ("deepseek", "deepseek/deepseek-v4.1-flash"),
                               ("gemini", "google/gemini-3.8-flash"),
                               ("minimax", "minimax/minimax-m3.1-flash")):
            adapter = root / "agents" / agent
            result = subprocess.run([str(adapter), "model"], text=True, capture_output=True, check=True)
            self.assertEqual(result.stdout.strip(), default)
            result = subprocess.run([str(adapter), "model", "other/model:variant"], text=True, capture_output=True, check=True)
            self.assertEqual(result.stdout.strip(), "other/model:variant")
            self.assertTrue(os.access(adapter.with_name(agent + ".batch"), os.X_OK))
            self.assertTrue(os.access(adapter.with_name(agent + ".process"), os.X_OK))

    def test_subscription_provider_is_not_overridden(self):
        self.assertEqual(codex_launch.provider_arguments(""), [])
        arguments = codex_launch.provider_arguments("openrouter")
        self.assertIn('model_provider="fx_openrouter"', arguments)
        self.assertIn('wire_api="responses"', arguments[-1])
        self.assertIn("OPENROUTER_API_KEY", arguments[-1])
        self.assertNotIn("sk-or-", arguments[-1])
        with self.assertRaises(ValueError):
            codex_launch.provider_arguments("unknown")

    def test_openrouter_preflight_uses_selected_model_and_blocks_failed_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            (session / "model.txt").write_text("z-ai/glm-5.3-flash")
            argv = ["codex_launch.py", "z-ai/glm-5.3", "openrouter", "launch",
                    directory, directory, directory, "high", "Implement"]
            with patch.object(sys, "argv", argv), patch.object(codex_launch.shutil, "which", return_value="codex"), \
                 patch.object(codex_launch, "api_key", return_value="test-key"), \
                 patch.object(codex_launch, "verify_model") as verify, patch.object(codex_launch, "launch") as launch:
                self.assertEqual(codex_launch.main(), 0)
                verify.assert_called_once_with("z-ai/glm-5.3-flash", parameters=("tools", "reasoning"))
                self.assertEqual(launch.call_args.args[-2:], ("z-ai/glm-5.3-flash", "openrouter"))
                launch.reset_mock()
                verify.side_effect = ValueError("Model unavailable")
                self.assertEqual(codex_launch.main(), 1)
                launch.assert_not_called()

    def test_launch_preserves_capture_and_passes_provider_per_process(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            (session / "instructions.md").write_text('Instructions with "quotes"\nand lines\n\n')
            (session / "launch.txt").write_text("agent=glm\nreasoning=high\n")
            with patch.object(codex_launch.subprocess, "run"), \
                 patch.object(codex_launch.subprocess, "check_output", side_effect=['notify=[]', 'hooks.Stop=[]\n']), \
                 patch.object(codex_launch.os, "execvpe") as execute:
                codex_launch.launch(directory, directory, session, "high", ["Prompt with $()"], "z-ai/glm-5.3", "openrouter")
            _, command, environment = execute.call_args.args
            self.assertEqual(command[command.index("--model") + 1], "z-ai/glm-5.3")
            self.assertEqual(command[-2:], ["--", "Prompt with $()"])
            self.assertIn('model_reasoning_effort="high"', command)
            instructions = next(value.split('=', 1)[1] for value in command if value.startswith('developer_instructions='))
            self.assertEqual(json.loads(instructions), 'Instructions with "quotes"\nand lines')
            self.assertIn('model_provider="fx_openrouter"', command)
            self.assertIn('hooks.Stop=[]', command)
            self.assertEqual(environment["FX_SESSION_CONTEXT_DIR"], str(session))
            self.assertTrue((session / "events/codex-session.jsonl").exists())

    def test_batch_saves_selected_model_catalog_prices_before_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            (session / 'model.txt').write_text('example/model')
            pricing = {'prompt': '0.000001', 'completion': '0.000002', 'input_cache_read': '0.0000001'}
            argv = ['codex_launch.py', 'default', 'openrouter', 'batch',
                    directory, directory, directory, 'high', 'Review']
            with patch.object(sys, 'argv', argv), \
                 patch.object(codex_launch.shutil, 'which', return_value='codex'), \
                 patch.object(codex_launch, 'api_key', return_value='test-key'), \
                 patch.object(codex_launch, 'verify_model', return_value={'pricing': pricing}), \
                 patch.object(codex_batch, 'run_batch', return_value=0):
                self.assertEqual(codex_launch.main(), 0)
            snapshot = json.loads((session / 'pricing.json').read_text())
            self.assertEqual(snapshot['model'], 'example/model')
            self.assertEqual(snapshot['pricing'], pricing)
            self.assertIn('captured_at', snapshot)

    def test_batch_retains_model_provider_reasoning_and_response_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            (session / "instructions.md").write_text("Investigate")
            (session / "launch.txt").write_text("agent=glm\nreasoning=high\n")
            commands = []

            def run(command, **kwargs):
                commands.append(command)
                if "exec" in command:
                    for event in ({"type": "thread.started", "thread_id": "conversation"},
                                  {"type": "item.completed", "item": {"type": "agent_message", "text": "Result"}},
                                  {"type": "turn.completed"}):
                        kwargs["stdout"].write(json.dumps(event) + "\n")
                return subprocess.CompletedProcess(command, 0)

            with patch.object(codex_batch.subprocess, "run", side_effect=run), \
                 patch.object(codex_batch.subprocess, "check_output", return_value="notify=[]"):
                self.assertEqual(codex_batch.run_batch(directory, directory, session, "high", "Investigate",
                                                      "z-ai/glm-5.3", codex_launch.provider_arguments("openrouter"), "openrouter"), 0)
            command = commands[-1]
            self.assertIn('model_provider="fx_openrouter"', command)
            self.assertIn('model_reasoning_effort="high"', command)
            self.assertEqual(command[command.index("--model") + 1], "z-ai/glm-5.3")
            metadata = json.loads(next((session / "results").glob("*/metadata.json")).read_text())
            self.assertEqual(metadata["agent"], "glm")
            self.assertEqual((session / "last_turn_results.md").read_text(), "Result")
            self.assertIn("provider=openrouter", (session / "launch.txt").read_text())


class ModelSelectionCommandTest(unittest.TestCase):
    def setUp(self):
        self.fixture = test_fx.FxTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_codex_and_claude_model_overrides_keep_subscription_provider(self):
        fixture = self.fixture
        task = fixture.task()
        for agent, model in (("codex", "gpt-6.1-terra"), ("claude", "claude-sonnet-5-5")):
            result = fixture.fx("agent", agent, "--name", "custom", "--model", model,
                                "-r", "h", "--prompt", "Inspect", cwd=task)
            command = json.loads(result.stdout)["arguments"]
            self.assertEqual(command[command.index("--model") + 1], model)
            self.assertFalse(any("fx_openrouter" in item for item in command))
            session = sorted((task / "context").iterdir())[-1]
            self.assertEqual((session / "model.txt").read_text().strip(), model)
            self.assertIn(f"model={model}\n", (session / "launch.txt").read_text())

    def test_invalid_model_and_resume_override_fail_before_session_creation(self):
        fixture = self.fixture
        task = fixture.task()
        for extra in (("--model", "bad model"), ("--model", ""),
                      ("--model", "a", "--model", "b"),
                      ("--resume", "context/old", "--model", "gpt-6.1-terra")):
            result = fixture.fx("agent", "codex", *extra, cwd=task, check=False)
            self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list((task / "context").iterdir()), [])

    def test_model_override_survives_new_tab(self):
        fixture = self.fixture
        task = fixture.task()
        fixture.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        result = fixture.fx("agent", "codex", "--name", "review", "-m", "gpt-6.1-terra", "--new-tab", cwd=task)
        arguments = json.loads(result.stdout)["arguments"]
        self.assertIn("gpt-6.1-terra", arguments[arguments.index("--name") + 1])
        session = next((task / "context").iterdir())
        self.assertEqual((session / "model.txt").read_text().strip(), "gpt-6.1-terra")

    def test_codex_capture_retains_openrouter_agent_identity(self):
        fixture = self.fixture
        task = fixture.task()
        fixture.fx("agent", "codex", "--name", "review", cwd=task)
        session = next((task / "context").iterdir())
        metadata = session / "launch.txt"
        metadata.write_text(metadata.read_text().replace("agent=codex", "agent=glm"))
        fixture.capture_codex(session, {"hook_event_name": "Stop", "session_id": "conversation",
                                        "turn_id": "turn", "last_assistant_message": "Review result"})
        response = json.loads(next((session / "results").glob("*/metadata.json")).read_text())
        self.assertEqual(response["agent"], "glm")
        self.assertEqual((session / "last_turn_results.md").read_text(), "Review result")


if __name__ == "__main__":
    unittest.main()
