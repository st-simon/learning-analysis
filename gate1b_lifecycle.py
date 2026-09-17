from __future__ import annotations

import argparse
import json
import os
import plistlib
import re
import shlex
import signal
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


LABEL = "com.junxia.learning-analysis.gate1b"


class LifecycleError(RuntimeError):
    pass


@dataclass(frozen=True)
class InstallationPaths:
    plist: Path
    runtime_dir: Path
    log_dir: Path
    stdout_log: Path
    stderr_log: Path


def installation_paths(project_root: Path, home: Path) -> InstallationPaths:
    project_root = project_root.resolve()
    home = home.resolve()
    log_dir = project_root / "logs" / "gate1b"
    return InstallationPaths(
        plist=home / "Library" / "LaunchAgents" / f"{LABEL}.plist",
        runtime_dir=project_root / "runtime" / "gate1b",
        log_dir=log_dir,
        stdout_log=log_dir / "launchd.out.log",
        stderr_log=log_dir / "launchd.err.log",
    )


def build_plist(project_root: Path) -> bytes:
    project_root = project_root.resolve()
    log_dir = project_root / "logs" / "gate1b"
    return plistlib.dumps(
        {
            "Label": LABEL,
            "ProgramArguments": [
                str(project_root / ".venv" / "bin" / "python"),
                str(project_root / "gate1b_lifecycle.py"),
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
    runtime_dir = project_root / "runtime" / "gate1b"
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
    paths.plist.parent.mkdir(parents=True, exist_ok=True)
    for directory in (paths.runtime_dir, paths.log_dir):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory.chmod(0o700)
    for log_file in (paths.stdout_log, paths.stderr_log):
        log_file.touch(mode=0o600, exist_ok=True)
        log_file.chmod(0o600)
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
        paths.stdout_log,
        paths.stderr_log,
    )
    for owned_file in owned_files:
        owned_file.unlink(missing_ok=True)
    for owned_dir in (paths.runtime_dir, paths.log_dir):
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
    except (OSError, subprocess.CalledProcessError) as exc:
        cleanup_installation(project_root, home)
        raise LifecycleError("INSTALL_FAILED") from exc
    return target


def status_agent(project_root: Path) -> dict:
    launchctl = _run_checked(["/bin/launchctl", "print", _service_target()])
    pid = parse_launchctl_pid(launchctl.stdout)
    paths = installation_paths(project_root, Path.home())
    try:
        pid_file = int(
            (paths.runtime_dir / "tunnel-client.pid")
            .read_text(encoding="utf-8")
            .strip()
        )
    except (OSError, ValueError) as exc:
        raise LifecycleError("INVALID_PID_FILE") from exc
    if pid != pid_file:
        raise LifecycleError("PID_MISMATCH")
    health = _run_checked(
        [
            str(project_root / "runtime" / "bin" / "tunnel-client"),
            "health",
            "--url-file",
            str(paths.runtime_dir / "tunnel-health.url"),
            "--pid-file",
            str(paths.runtime_dir / "tunnel-client.pid"),
            "--require-control-plane-poll",
            "--json",
        ]
    )
    health_payload = json.loads(health.stdout)
    if health_payload.get("result") != "ok":
        raise LifecycleError("TUNNEL_NOT_READY")
    return {"status": "ok", "label": LABEL, "pid": pid, "ready": True}


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
    cleanup_installation(project_root, home)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gate 1B disposable lifecycle spike")
    parser.add_argument(
        "action", choices=("render", "run", "install", "status", "kill-once", "uninstall")
    )
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
            print(json.dumps(status_agent(root), sort_keys=True))
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
