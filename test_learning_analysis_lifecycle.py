import plistlib
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from learning_analysis_lifecycle import (
    LABEL,
    LifecycleError,
    build_plist,
    build_tunnel_command,
    cleanup_installation,
    doctor_agent,
    installation_paths,
    load_control_plane_key,
    parse_launchctl_pid,
    prepare_installation,
    status_agent,
    validate_kill_target,
    wait_for_service_absent,
    wait_until_ready,
)


def make_project(root: Path) -> Path:
    project_root = root / "project"
    source = project_root / "extension" / "learning-analysis-capture"
    source.mkdir(parents=True)
    (source / "manifest.json").write_text("{}\n", encoding="utf-8")
    (source / "capture_flow.js").write_text("// flow\n", encoding="utf-8")
    (source / "service_worker.js").write_text("// worker\n", encoding="utf-8")
    return project_root


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
                str(resolved_root / "learning_analysis_lifecycle.py"),
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
        self.assertIn(str(resolved_root / "runtime/learning-analysis/tunnel-health.url"), command)
        self.assertIn(str(resolved_root / "runtime/learning-analysis/tunnel-client.pid"), command)
        self.assertNotIn("secret-value", " ".join(command))


class InstallationFileTests(unittest.TestCase):
    def test_prepares_only_owned_files_with_private_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project_root = make_project(base)
            home = base / "home"
            paths = installation_paths(project_root, home)

            target = prepare_installation(project_root, home)

            self.assertEqual(target, paths.plist)
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertEqual(paths.runtime_dir.stat().st_mode & 0o777, 0o700)
            self.assertEqual(paths.log_dir.stat().st_mode & 0o777, 0o700)
            self.assertEqual(paths.stdout_log.stat().st_mode & 0o777, 0o600)
            self.assertEqual(paths.stderr_log.stat().st_mode & 0o777, 0o600)
            self.assertEqual(paths.token_file.stat().st_mode & 0o777, 0o600)
            self.assertEqual(paths.extension_dir.stat().st_mode & 0o777, 0o700)
            self.assertTrue((paths.extension_dir / "manifest.json").is_file())
            self.assertTrue((paths.extension_dir / "capture_flow.js").is_file())
            self.assertTrue((paths.extension_dir / "service_worker.js").is_file())
            install_config = paths.extension_dir / "install_config.js"
            self.assertEqual(install_config.stat().st_mode & 0o777, 0o600)
            self.assertIn(
                "LEARNING_ANALYSIS_INSTALL_TOKEN",
                install_config.read_text(encoding="utf-8"),
            )
            self.assertEqual(plistlib.loads(target.read_bytes())["Label"], LABEL)

    def test_refuses_to_overwrite_existing_agent(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project_root = make_project(base)
            home = base / "home"
            prepare_installation(project_root, home)

            with self.assertRaisesRegex(LifecycleError, "AGENT_ALREADY_EXISTS"):
                prepare_installation(project_root, home)

    def test_cleanup_removes_only_formal_runtime_owned_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project_root = make_project(base)
            home = base / "home"
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


class ReadyWaitTests(unittest.TestCase):
    def test_retries_named_transient_stages_until_ready(self):
        outcomes = iter(
            (
                LifecycleError("STARTING"),
                LifecycleError("MCP_UNREADY"),
                LifecycleError("CONTROL_PLANE_UNREADY"),
                LifecycleError("CAPTURE_UNREADY"),
                {"status": "ok", "ready": True},
            )
        )

        def probe():
            outcome = next(outcomes)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        result = wait_until_ready(probe, timeout_seconds=1, interval_seconds=0)

        self.assertTrue(result["ready"])

    def test_fails_immediately_for_non_transient_configuration_error(self):
        called = 0

        def probe():
            nonlocal called
            called += 1
            raise LifecycleError("CONFIG_INVALID")

        with self.assertRaisesRegex(LifecycleError, "CONFIG_INVALID"):
            wait_until_ready(probe, timeout_seconds=45, interval_seconds=0)

        self.assertEqual(called, 1)

    def test_preserves_last_transient_error_at_deadline(self):
        started = time.monotonic()

        def probe():
            raise LifecycleError("CAPTURE_UNREADY")

        with self.assertRaisesRegex(LifecycleError, "CAPTURE_UNREADY"):
            wait_until_ready(
                probe,
                timeout_seconds=0.01,
                interval_seconds=0,
            )

        self.assertLess(time.monotonic() - started, 0.5)

    def test_waits_for_launchd_to_finish_bootout(self):
        return_codes = iter((0, 0, 113))

        def run(_command, **_kwargs):
            return subprocess.CompletedProcess([], next(return_codes), "", "")

        wait_for_service_absent(
            timeout_seconds=1,
            interval_seconds=0,
            run=run,
        )

    def test_reports_service_stop_timeout(self):
        def run(_command, **_kwargs):
            return subprocess.CompletedProcess([], 0, "loaded", "")

        with self.assertRaisesRegex(LifecycleError, "SERVICE_STOP_TIMEOUT"):
            wait_for_service_absent(
                timeout_seconds=0.01,
                interval_seconds=0,
                run=run,
            )


class FormalStatusTests(unittest.TestCase):
    def test_status_distinguishes_absent_service(self):
        def run(_command, **_kwargs):
            return subprocess.CompletedProcess([], 113, "", "not found")

        with self.assertRaisesRegex(LifecycleError, "SERVICE_ABSENT"):
            status_agent(Path("/tmp/learning-analysis"), run=run)

    def test_doctor_reports_only_safe_checks_and_ready_state(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project_root = make_project(base)
            home = base / "home"
            prepare_installation(project_root, home)

            result = doctor_agent(
                project_root,
                home,
                status_probe=lambda: {
                    "status": "ok",
                    "label": LABEL,
                    "pid": 123,
                    "ready": True,
                },
            )

        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["ready"])
        self.assertEqual(
            result["checks"],
            {
                "agent": "ok",
                "capture_token": "ok",
                "extension": "ok",
            },
        )
        self.assertNotIn("token", str(result).lower().replace("capture_token", ""))

    def test_doctor_rejects_extension_config_that_does_not_match_token(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project_root = make_project(base)
            home = base / "home"
            prepare_installation(project_root, home)
            paths = installation_paths(project_root, home)
            (paths.extension_dir / "install_config.js").write_text(
                'globalThis.LEARNING_ANALYSIS_INSTALL_TOKEN = "stale";\n',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(LifecycleError, "CONFIG_INVALID"):
                doctor_agent(
                    project_root,
                    home,
                    status_probe=lambda: {
                        "status": "ok",
                        "label": LABEL,
                        "pid": 123,
                        "ready": True,
                    },
                )

    def test_cleanup_and_prepare_rotates_install_token(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project_root = make_project(base)
            home = base / "home"
            prepare_installation(project_root, home)
            paths = installation_paths(project_root, home)
            first_token = paths.token_file.read_text(encoding="utf-8")

            cleanup_installation(project_root, home)
            prepare_installation(project_root, home)
            second_token = paths.token_file.read_text(encoding="utf-8")

        self.assertNotEqual(first_token, second_token)


if __name__ == "__main__":
    unittest.main()
