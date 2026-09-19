from __future__ import annotations

import argparse
import http.client
import json
import os
import plistlib
import re
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from browser_capture_server import load_or_create_token


LABEL = "com.junxia.learning-analysis"
RUNTIME_NAME = "learning-analysis"
EXTENSION_SOURCE_FILES = (
    "manifest.json",
    "capture_flow.js",
    "service_worker.js",
)
TRANSIENT_READY_ERRORS = {
    "STARTING",
    "MCP_UNREADY",
    "CONTROL_PLANE_UNREADY",
    "CAPTURE_UNREADY",
}


class LifecycleError(RuntimeError):
    pass


def wait_until_ready(
    probe,
    *,
    timeout_seconds: float = 45,
    interval_seconds: float = 1,
) -> dict:
    if timeout_seconds < 0 or interval_seconds < 0:
        raise LifecycleError("CONFIG_INVALID")
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            return probe()
        except LifecycleError as exc:
            if str(exc) not in TRANSIENT_READY_ERRORS:
                raise
            if time.monotonic() >= deadline:
                raise
            time.sleep(min(interval_seconds, max(0, deadline - time.monotonic())))


@dataclass(frozen=True)
class InstallationPaths:
    plist: Path
    runtime_dir: Path
    log_dir: Path
    stdout_log: Path
    stderr_log: Path
    token_file: Path
    extension_dir: Path


def installation_paths(project_root: Path, home: Path) -> InstallationPaths:
    project_root = project_root.resolve()
    home = home.resolve()
    runtime_dir = project_root / "runtime" / RUNTIME_NAME
    log_dir = project_root / "logs" / RUNTIME_NAME
    return InstallationPaths(
        plist=home / "Library" / "LaunchAgents" / f"{LABEL}.plist",
        runtime_dir=runtime_dir,
        log_dir=log_dir,
        stdout_log=log_dir / "launchd.out.log",
        stderr_log=log_dir / "launchd.err.log",
        token_file=runtime_dir / "browser-capture.token",
        extension_dir=runtime_dir / "extension",
    )


def build_plist(project_root: Path) -> bytes:
    project_root = project_root.resolve()
    log_dir = project_root / "logs" / RUNTIME_NAME
    return plistlib.dumps(
        {
            "Label": LABEL,
            "ProgramArguments": [
                str(project_root / ".venv" / "bin" / "python"),
                str(project_root / "learning_analysis_lifecycle.py"),
                "run",
            ],
            "WorkingDirectory": str(project_root),
            "RunAtLoad": True,
            "KeepAlive": True,
            "ThrottleInterval": 10,
            "ProcessType": "Background",
            "StandardOutPath": str(log_dir / "launchd.out.log"),
            "StandardErrorPath": str(log_dir / "launchd.err.log"),
        },
        fmt=plistlib.FMT_XML,
        sort_keys=False,
    )


def load_control_plane_key(env_file: Path) -> str:
    file_stat = env_file.stat()
    if not stat.S_ISREG(file_stat.st_mode) or stat.S_IMODE(file_stat.st_mode) & 0o077:
        raise LifecycleError("INSECURE_ENV_FILE")
    matches: list[str] = []
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, separator, raw_value = line.partition("=")
        if separator and name.strip() == "CONTROL_PLANE_API_KEY":
            values = shlex.split(raw_value, posix=True)
            if len(values) != 1 or not values[0]:
                raise LifecycleError("INVALID_CONTROL_PLANE_KEY")
            matches.append(values[0])
    if len(matches) != 1:
        raise LifecycleError("INVALID_CONTROL_PLANE_KEY")
    return matches[0]


def build_tunnel_command(project_root: Path) -> list[str]:
    project_root = project_root.resolve()
    runtime_dir = project_root / "runtime" / RUNTIME_NAME
    return [
        str(project_root / "runtime" / "bin" / "tunnel-client"),
        "run",
        "--config",
        str(project_root / "runtime" / "learning-analysis.yaml"),
        "--health.listen-addr",
        "127.0.0.1:0",
        "--health.url-file",
        str(runtime_dir / "tunnel-health.url"),
        "--pid.file",
        str(runtime_dir / "tunnel-client.pid"),
        "--log.format",
        "json",
        "--log.level",
        "info",
    ]


def prepare_installation(project_root: Path, home: Path) -> Path:
    paths = installation_paths(project_root, home)
    if paths.plist.exists():
        raise LifecycleError("AGENT_ALREADY_EXISTS")
    source_dir = project_root.resolve() / "extension" / "learning-analysis-capture"
    missing = [name for name in EXTENSION_SOURCE_FILES if not (source_dir / name).is_file()]
    if missing:
        raise LifecycleError("MISSING_EXTENSION_SOURCE")
    paths.plist.parent.mkdir(parents=True, exist_ok=True)
    for directory in (paths.runtime_dir, paths.log_dir):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory.chmod(0o700)
    for log_file in (paths.stdout_log, paths.stderr_log):
        log_file.touch(mode=0o600, exist_ok=True)
        log_file.chmod(0o600)
    paths.extension_dir.mkdir(mode=0o700)
    paths.extension_dir.chmod(0o700)
    for name in EXTENSION_SOURCE_FILES:
        destination = paths.extension_dir / name
        shutil.copyfile(source_dir / name, destination)
        destination.chmod(0o600)
    token = load_or_create_token(paths.token_file)
    config = paths.extension_dir / "install_config.js"
    config.write_text(
        f"globalThis.LEARNING_ANALYSIS_INSTALL_TOKEN = {json.dumps(token)};\n",
        encoding="utf-8",
    )
    config.chmod(0o600)
    payload = build_plist(project_root)
    with tempfile.NamedTemporaryFile(dir=paths.plist.parent, delete=False) as temporary:
        temporary.write(payload)
        temporary.flush()
        temporary_path = Path(temporary.name)
    temporary_path.chmod(0o600)
    temporary_path.replace(paths.plist)
    return paths.plist


def cleanup_installation(project_root: Path, home: Path) -> None:
    paths = installation_paths(project_root, home)
    owned_files = (
        paths.plist,
        paths.runtime_dir / "tunnel-client.pid",
        paths.runtime_dir / "tunnel-health.url",
        paths.runtime_dir / "kill-once.marker",
        paths.token_file,
        paths.extension_dir / "manifest.json",
        paths.extension_dir / "capture_flow.js",
        paths.extension_dir / "service_worker.js",
        paths.extension_dir / "install_config.js",
        paths.stdout_log,
        paths.stderr_log,
    )
    for owned_file in owned_files:
        owned_file.unlink(missing_ok=True)
    for owned_dir in (paths.extension_dir, paths.runtime_dir, paths.log_dir):
        if owned_dir.exists():
            try:
                owned_dir.rmdir()
            except OSError as exc:
                raise LifecycleError("CLEANUP_NOT_EMPTY") from exc


def parse_launchctl_pid(output: str) -> int:
    matches = re.findall(r"^\s*pid = (\d+)\s*$", output, flags=re.MULTILINE)
    if len(matches) != 1:
        raise LifecycleError("INVALID_LAUNCHCTL_PID")
    return int(matches[0])


def validate_kill_target(
    pid_file: Path,
    launchctl_output: str,
    process_command: str,
    project_root: Path,
) -> int:
    try:
        pid_from_file = int(pid_file.read_text(encoding="utf-8").strip())
    except (OSError, ValueError) as exc:
        raise LifecycleError("INVALID_PID_FILE") from exc
    pid_from_launchctl = parse_launchctl_pid(launchctl_output)
    if pid_from_file != pid_from_launchctl:
        raise LifecycleError("PID_MISMATCH")
    expected_executable = str(
        project_root.resolve() / "runtime" / "bin" / "tunnel-client"
    )
    if not (
        process_command == expected_executable
        or process_command.startswith(f"{expected_executable} ")
    ):
        raise LifecycleError("UNEXPECTED_PROCESS")
    return pid_from_file


def _project_root() -> Path:
    return Path(__file__).resolve().parent


def _domain() -> str:
    return f"gui/{os.getuid()}"


def _service_target() -> str:
    return f"{_domain()}/{LABEL}"


def wait_for_service_absent(
    *,
    timeout_seconds: float = 10,
    interval_seconds: float = 0.1,
    run=subprocess.run,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while True:
        result = run(
            ["/bin/launchctl", "print", _service_target()],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode != 0:
            return
        if time.monotonic() >= deadline:
            raise LifecycleError("SERVICE_STOP_TIMEOUT")
        time.sleep(min(interval_seconds, max(0, deadline - time.monotonic())))


def _run_checked(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )


def run_daemon(project_root: Path) -> None:
    if os.geteuid() == 0:
        raise LifecycleError("ROOT_NOT_ALLOWED")
    os.umask(0o077)
    paths = installation_paths(project_root, Path.home())
    paths.runtime_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    paths.runtime_dir.chmod(0o700)
    key = load_control_plane_key(project_root / ".env")
    command = build_tunnel_command(project_root)
    for required_path in (
        Path(command[0]),
        project_root / "runtime" / "learning-analysis.yaml",
    ):
        if not required_path.is_file():
            raise LifecycleError("MISSING_RUNTIME_DEPENDENCY")
    environment = os.environ.copy()
    environment["CONTROL_PLANE_API_KEY"] = key
    os.execve(command[0], command, environment)


def install_agent(project_root: Path, home: Path) -> Path:
    if os.geteuid() == 0:
        raise LifecycleError("ROOT_NOT_ALLOWED")
    existing = subprocess.run(
        ["/bin/launchctl", "print", _service_target()],
        capture_output=True,
        text=True,
    )
    if existing.returncode == 0:
        raise LifecycleError("AGENT_ALREADY_LOADED")
    target = prepare_installation(project_root, home)
    try:
        _run_checked(["/usr/bin/plutil", "-lint", str(target)])
        _run_checked(["/bin/launchctl", "bootstrap", _domain(), str(target)])
        wait_until_ready(
            lambda: status_agent(project_root, home=home),
            timeout_seconds=45,
        )
    except (LifecycleError, OSError, subprocess.CalledProcessError) as exc:
        subprocess.run(
            ["/bin/launchctl", "bootout", _service_target()],
            capture_output=True,
            text=True,
        )
        wait_for_service_absent()
        cleanup_installation(project_root, home)
        if isinstance(exc, LifecycleError):
            raise
        raise LifecycleError("INSTALL_FAILED") from exc
    return target


def _capture_is_ready() -> bool:
    connection = http.client.HTTPConnection("127.0.0.1", 18431, timeout=1)
    try:
        connection.request("GET", "/healthz")
        response = connection.getresponse()
        response.read()
        return response.status == 200
    except OSError:
        return False
    finally:
        connection.close()


def _health_error(output: str) -> str:
    normalized = output.lower()
    if "control" in normalized:
        return "CONTROL_PLANE_UNREADY"
    if "mcp" in normalized:
        return "MCP_UNREADY"
    return "STARTING"


def status_agent(
    project_root: Path,
    *,
    home: Path | None = None,
    run=subprocess.run,
    capture_probe=_capture_is_ready,
) -> dict:
    launchctl = run(
        ["/bin/launchctl", "print", _service_target()],
        capture_output=True,
        text=True,
        timeout=3,
    )
    if launchctl.returncode != 0:
        raise LifecycleError("SERVICE_ABSENT")
    try:
        pid = parse_launchctl_pid(launchctl.stdout)
    except LifecycleError as exc:
        if str(exc) == "INVALID_LAUNCHCTL_PID" and "pid =" not in launchctl.stdout:
            raise LifecycleError("STARTING") from exc
        raise LifecycleError("CONFIG_INVALID") from exc
    paths = installation_paths(project_root, home or Path.home())
    try:
        pid_file = int(
            (paths.runtime_dir / "tunnel-client.pid")
            .read_text(encoding="utf-8")
            .strip()
        )
    except FileNotFoundError as exc:
        raise LifecycleError("STARTING") from exc
    except (OSError, ValueError) as exc:
        raise LifecycleError("CONFIG_INVALID") from exc
    if pid != pid_file:
        raise LifecycleError("CONFIG_INVALID")
    try:
        health = run(
            [
                str(project_root / "runtime" / "bin" / "tunnel-client"),
                "health",
                "--url-file",
                str(paths.runtime_dir / "tunnel-health.url"),
                "--pid-file",
                str(paths.runtime_dir / "tunnel-client.pid"),
                "--require-control-plane-poll",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired as exc:
        raise LifecycleError("CONTROL_PLANE_UNREADY") from exc
    if health.returncode != 0:
        raise LifecycleError(_health_error(f"{health.stdout}\n{health.stderr}"))
    try:
        health_payload = json.loads(health.stdout)
    except json.JSONDecodeError as exc:
        raise LifecycleError("MCP_UNREADY") from exc
    if health_payload.get("result") != "ok":
        raise LifecycleError(_health_error(health.stdout))
    if not capture_probe():
        raise LifecycleError("CAPTURE_UNREADY")
    return {
        "status": "ok",
        "label": LABEL,
        "pid": pid,
        "ready": True,
        "capture_ready": True,
    }


def doctor_agent(
    project_root: Path,
    home: Path,
    *,
    wait_seconds: float = 0,
    status_probe=None,
) -> dict:
    paths = installation_paths(project_root, home)
    if not paths.plist.is_file():
        raise LifecycleError("SERVICE_ABSENT")
    try:
        token_mode = stat.S_IMODE(paths.token_file.stat().st_mode)
        token = paths.token_file.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise LifecycleError("CONFIG_INVALID") from exc
    if token_mode != 0o600 or not token:
        raise LifecycleError("CONFIG_INVALID")
    required_extension_files = (*EXTENSION_SOURCE_FILES, "install_config.js")
    if (
        stat.S_IMODE(paths.extension_dir.stat().st_mode) != 0o700
        or any(not (paths.extension_dir / name).is_file() for name in required_extension_files)
    ):
        raise LifecycleError("CONFIG_INVALID")
    expected_config = (
        f"globalThis.LEARNING_ANALYSIS_INSTALL_TOKEN = {json.dumps(token)};\n"
    )
    try:
        config_path = paths.extension_dir / "install_config.js"
        if (
            stat.S_IMODE(config_path.stat().st_mode) != 0o600
            or config_path.read_text(encoding="utf-8") != expected_config
        ):
            raise LifecycleError("CONFIG_INVALID")
    except OSError as exc:
        raise LifecycleError("CONFIG_INVALID") from exc
    probe = status_probe or (lambda: status_agent(project_root, home=home))
    status_payload = wait_until_ready(
        probe,
        timeout_seconds=wait_seconds,
    )
    return {
        "status": "ok",
        "label": LABEL,
        "pid": status_payload["pid"],
        "ready": True,
        "checks": {
            "agent": "ok",
            "capture_token": "ok",
            "extension": "ok",
        },
    }


def upgrade_agent(project_root: Path, home: Path) -> Path:
    subprocess.run(
        ["/bin/launchctl", "bootout", _service_target()],
        capture_output=True,
        text=True,
    )
    wait_for_service_absent()
    cleanup_installation(project_root, home)
    return install_agent(project_root, home)


def kill_once(project_root: Path) -> int:
    paths = installation_paths(project_root, Path.home())
    marker = paths.runtime_dir / "kill-once.marker"
    if marker.exists():
        raise LifecycleError("KILL_ALREADY_USED")
    launchctl = _run_checked(["/bin/launchctl", "print", _service_target()])
    pid = parse_launchctl_pid(launchctl.stdout)
    process = _run_checked(["/bin/ps", "-p", str(pid), "-o", "command="])
    validated_pid = validate_kill_target(
        paths.runtime_dir / "tunnel-client.pid",
        launchctl.stdout,
        process.stdout.strip(),
        project_root,
    )
    descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as marker_file:
        marker_file.write("used\n")
    os.kill(validated_pid, signal.SIGTERM)
    return validated_pid


def uninstall_agent(project_root: Path, home: Path) -> None:
    subprocess.run(
        ["/bin/launchctl", "bootout", _service_target()],
        capture_output=True,
        text=True,
    )
    wait_for_service_absent()
    cleanup_installation(project_root, home)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Learning Analysis local lifecycle")
    parser.add_argument(
        "action",
        choices=(
            "render",
            "run",
            "install",
            "status",
            "doctor",
            "upgrade",
            "kill-once",
            "uninstall",
        ),
    )
    parser.add_argument("--wait", type=float, default=0)
    args = parser.parse_args(argv)
    root = _project_root()
    try:
        if args.action == "render":
            sys.stdout.buffer.write(build_plist(root))
        elif args.action == "run":
            run_daemon(root)
        elif args.action == "install":
            target = install_agent(root, Path.home())
            print(json.dumps({"status": "ok", "label": LABEL, "plist": str(target)}))
        elif args.action == "status":
            result = wait_until_ready(
                lambda: status_agent(root),
                timeout_seconds=args.wait,
            )
            print(json.dumps(result, sort_keys=True))
        elif args.action == "doctor":
            print(
                json.dumps(
                    doctor_agent(root, Path.home(), wait_seconds=args.wait),
                    sort_keys=True,
                )
            )
        elif args.action == "upgrade":
            target = upgrade_agent(root, Path.home())
            print(json.dumps({"status": "ok", "label": LABEL, "plist": str(target)}))
        elif args.action == "kill-once":
            pid = kill_once(root)
            print(json.dumps({"status": "ok", "terminated_pid": pid}))
        elif args.action == "uninstall":
            uninstall_agent(root, Path.home())
            print(json.dumps({"status": "ok", "label": LABEL, "removed": True}))
    except (LifecycleError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        code = str(exc) if isinstance(exc, LifecycleError) else "LIFECYCLE_OPERATION_FAILED"
        print(json.dumps({"status": "error", "error_code": code}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
