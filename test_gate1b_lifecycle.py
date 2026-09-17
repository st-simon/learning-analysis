import plistlib
import tempfile
import unittest
from pathlib import Path

from gate1b_lifecycle import (
    LABEL,
    LifecycleError,
    build_plist,
    build_tunnel_command,
    cleanup_installation,
    installation_paths,
    load_control_plane_key,
    parse_launchctl_pid,
    prepare_installation,
    validate_kill_target,
)


class BuildPlistTests(unittest.TestCase):
    def test_builds_secret_free_user_agent_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory) / "learning-analysis"
            project_root.mkdir()
            payload = build_plist(project_root)
            plist = plistlib.loads(payload)
            resolved_root = project_root.resolve()

        self.assertEqual(plist["Label"], LABEL)
        self.assertEqual(
            plist["ProgramArguments"],
            [
                str(resolved_root / ".venv/bin/python"),
                str(resolved_root / "gate1b_lifecycle.py"),
                "run",
            ],
        )
        self.assertEqual(plist["WorkingDirectory"], str(resolved_root))
        self.assertIs(plist["RunAtLoad"], True)
        self.assertIs(plist["KeepAlive"], True)
        self.assertEqual(plist["ThrottleInterval"], 10)
        self.assertEqual(plist["ProcessType"], "Background")
        self.assertNotIn("EnvironmentVariables", plist)
        self.assertNotIn(b"CONTROL_PLANE_API_KEY", payload)


class RuntimeSecretTests(unittest.TestCase):
    def test_reads_only_the_control_plane_key_without_shell_evaluation(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                "DANGER=$(touch should-not-exist)\n"
                "CONTROL_PLANE_API_KEY='secret-value'\n",
                encoding="utf-8",
            )
            env_file.chmod(0o600)

            value = load_control_plane_key(env_file)

            self.assertEqual(value, "secret-value")
            self.assertFalse((Path(directory) / "should-not-exist").exists())

    def test_rejects_group_or_world_readable_env_file(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text("CONTROL_PLANE_API_KEY=secret\n", encoding="utf-8")
            env_file.chmod(0o644)

            with self.assertRaisesRegex(LifecycleError, "INSECURE_ENV_FILE"):
                load_control_plane_key(env_file)

    def test_tunnel_command_contains_no_secret(self):
        root = Path("/tmp/learning-analysis")
        resolved_root = root.resolve()

        command = build_tunnel_command(root)

        self.assertEqual(command[0], str(resolved_root / "runtime/bin/tunnel-client"))
        self.assertIn(str(resolved_root / "runtime/gate1b/tunnel-health.url"), command)
        self.assertIn(str(resolved_root / "runtime/gate1b/tunnel-client.pid"), command)
        self.assertNotIn("secret-value", " ".join(command))


class InstallationFileTests(unittest.TestCase):
    def test_prepares_only_owned_files_with_private_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project_root = base / "project"
            home = base / "home"
            project_root.mkdir()
            paths = installation_paths(project_root, home)

            target = prepare_installation(project_root, home)

            self.assertEqual(target, paths.plist)
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertEqual(paths.runtime_dir.stat().st_mode & 0o777, 0o700)
            self.assertEqual(paths.log_dir.stat().st_mode & 0o777, 0o700)
            self.assertEqual(paths.stdout_log.stat().st_mode & 0o777, 0o600)
            self.assertEqual(paths.stderr_log.stat().st_mode & 0o777, 0o600)
            self.assertEqual(plistlib.loads(target.read_bytes())["Label"], LABEL)

    def test_refuses_to_overwrite_existing_agent(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project_root = base / "project"
            home = base / "home"
            project_root.mkdir()
            prepare_installation(project_root, home)

            with self.assertRaisesRegex(LifecycleError, "AGENT_ALREADY_EXISTS"):
                prepare_installation(project_root, home)

    def test_cleanup_removes_only_gate1b_owned_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project_root = base / "project"
            home = base / "home"
            project_root.mkdir()
            paths = installation_paths(project_root, home)
            prepare_installation(project_root, home)
            (paths.runtime_dir / "tunnel-client.pid").write_text("123", encoding="utf-8")
            unrelated = project_root / "runtime" / "keep.txt"
            unrelated.write_text("keep", encoding="utf-8")
            other_agent = paths.plist.parent / "other.plist"
            other_agent.write_text("keep", encoding="utf-8")

            cleanup_installation(project_root, home)

            self.assertFalse(paths.plist.exists())
            self.assertFalse(paths.runtime_dir.exists())
            self.assertFalse(paths.log_dir.exists())
            self.assertTrue(unrelated.exists())
            self.assertTrue(other_agent.exists())


class KillTargetTests(unittest.TestCase):
    def test_requires_matching_pid_file_launchctl_pid_and_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            pid_file = root / "tunnel-client.pid"
            pid_file.write_text("4321\n", encoding="utf-8")
            launchctl_output = "service = {\n\tpid = 4321\n}\n"
            process_command = f"{root}/runtime/bin/tunnel-client run --config config.yaml"

            pid = validate_kill_target(
                pid_file, launchctl_output, process_command, root
            )

            self.assertEqual(pid, 4321)

    def test_rejects_pid_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            pid_file = root / "tunnel-client.pid"
            pid_file.write_text("4321\n", encoding="utf-8")

            with self.assertRaisesRegex(LifecycleError, "PID_MISMATCH"):
                validate_kill_target(
                    pid_file,
                    "pid = 9999\n",
                    f"{root}/runtime/bin/tunnel-client run",
                    root,
                )

    def test_launchctl_pid_parser_rejects_missing_or_duplicate_pid(self):
        self.assertEqual(parse_launchctl_pid("\n  pid = 12\n"), 12)
        for output in ("state = running\n", "pid = 1\npid = 2\n"):
            with self.subTest(output=output):
                with self.assertRaisesRegex(LifecycleError, "INVALID_LAUNCHCTL_PID"):
                    parse_launchctl_pid(output)


if __name__ == "__main__":
    unittest.main()
