"""Pure model rules: repository identity, names, and session ids."""

import unittest
from pathlib import Path

from x_env.model import (
    GitHubRepo,
    GitUrl,
    LocalRepo,
    SessionId,
    SessionName,
    TaskName,
    UsageError,
    repo_identity,
)


class ModelTest(unittest.TestCase):
    def test_repository_identity_matches_github_transports(self):
        for repository in (
            GitHubRepo("owner", "repo"), GitHubRepo("owner", "repo.git"),
            GitUrl("https://github.com/owner/repo.git"), GitUrl("git@github.com:owner/repo.git"),
            GitUrl("ssh://git@github.com/owner/repo.git"), "https://github.com/owner/repo/",
        ):
            with self.subTest(repository=repository):
                self.assertEqual(repo_identity(repository), "owner/repo")

    def test_local_repository_identity_is_its_path(self):
        self.assertEqual(repo_identity(LocalRepo(Path("/src/shop"))), repo_identity("/src/shop"))
        self.assertNotEqual(repo_identity(LocalRepo(Path("/src/shop"))), repo_identity("/src/other"))

    def test_session_id_round_trip(self):
        session = SessionId.of(TaskName("fix-login"), 7, SessionName("code-review"))
        self.assertEqual(session, "fix-login/007-code-review")
        self.assertEqual(session.parse(), ("fix-login", 7, "code-review"))

    def test_malformed_session_ids_are_usage_errors(self):
        for raw in ("fix", "fix/007", "fix/x-review", "../007-x", "fix/007-a/b"):
            with self.subTest(raw=raw):
                with self.assertRaises(UsageError):
                    SessionId(raw).parse()


if __name__ == "__main__":
    unittest.main()
