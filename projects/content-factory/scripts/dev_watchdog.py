#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, TextIO

ServiceKind = Literal["command", "process"]
HealthKind = Literal["http", "tcp"]


class ManagedProcess(Protocol):
    pid: int

    def poll(self) -> int | None: ...

    def wait(self, timeout: float | None = None) -> int: ...

    def terminate(self) -> None: ...

    def kill(self) -> None: ...


@dataclass(frozen=True)
class HealthCheck:
    name: str
    kind: HealthKind
    target: str


@dataclass(frozen=True)
class ServiceSpec:
    name: str
    kind: ServiceKind
    checks: tuple[HealthCheck, ...]
    command: tuple[str, ...]
    failure_threshold: int = 1
    startup_grace_seconds: float = 5.0


@dataclass
class ServiceState:
    process: ManagedProcess | None = None
    failure_count: int = 0
    started_at: float | None = None


HealthProbe = Callable[[HealthCheck], bool]
CommandRunner = Callable[[tuple[str, ...]], int]
ProcessStarter = Callable[[ServiceSpec], ManagedProcess]


class DevWatchdog:
    def __init__(
        self,
        *,
        services: Sequence[ServiceSpec],
        project_root: Path,
        dry_run: bool = False,
        health_probe: HealthProbe | None = None,
        command_runner: CommandRunner | None = None,
        process_starter: ProcessStarter | None = None,
        output: TextIO | None = None,
        log_dir: Path | None = None,
        health_timeout_seconds: float = 2.0,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self._services = tuple(services)
        self._project_root = project_root
        self._dry_run = dry_run
        self._output = output or sys.stdout
        self._log_dir = log_dir or project_root / ".logs" / "watchdog"
        self._health_probe = health_probe or default_health_probe(health_timeout_seconds)
        self._command_runner = command_runner or self._run_command
        self._process_starter = process_starter or self._start_process
        self._now = now
        self._states = {service.name: ServiceState() for service in self._services}

    def run_once(self) -> None:
        for service in self._services:
            state = self._states[service.name]
            healthy = self._is_healthy(service)
            if healthy:
                state.failure_count = 0
                self._write(f"{service.name}: healthy")
                continue

            if self._is_in_startup_grace(service, state):
                self._write(f"{service.name}: waiting for startup grace")
                continue

            state.failure_count += 1
            self._write(
                f"{service.name}: unhealthy "
                f"({state.failure_count}/{service.failure_threshold})",
            )
            if state.failure_count >= service.failure_threshold:
                self._recover(service, state)
                state.failure_count = 0

    def run_forever(self, *, interval_seconds: float) -> None:
        try:
            while True:
                self.run_once()
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            self._write("watchdog: stopping")
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        for service in self._services:
            state = self._states[service.name]
            if service.kind == "process" and state.process is not None:
                if state.process.poll() is None:
                    self._write(f"{service.name}: stopping managed process")
                    terminate_process_tree(state.process)
                state.process = None

    def _is_healthy(self, service: ServiceSpec) -> bool:
        return all(self._health_probe(check) for check in service.checks)

    def _is_in_startup_grace(self, service: ServiceSpec, state: ServiceState) -> bool:
        if service.kind != "process" or state.process is None or state.started_at is None:
            return False
        if state.process.poll() is not None:
            return False
        return self._now() - state.started_at < service.startup_grace_seconds

    def _recover(self, service: ServiceSpec, state: ServiceState) -> None:
        if service.kind == "command":
            self._run_recovery_command(service)
            return

        if state.process is not None and state.process.poll() is None:
            self._write(f"{service.name}: restarting managed process")
            if not self._dry_run:
                terminate_process_tree(state.process)

        if self._dry_run:
            self._write(f"[dry-run] would start {service.name}: {_format_command(service.command)}")
            return

        state.process = self._process_starter(service)
        state.started_at = self._now()
        self._write(f"{service.name}: started pid={state.process.pid}")

    def _run_recovery_command(self, service: ServiceSpec) -> None:
        if self._dry_run:
            self._write(f"[dry-run] would run {service.name}: {_format_command(service.command)}")
            return

        return_code = self._command_runner(service.command)
        if return_code == 0:
            self._write(f"{service.name}: recovery command completed")
        else:
            self._write(f"{service.name}: recovery command failed with exit code {return_code}")

    def _run_command(self, command: tuple[str, ...]) -> int:
        completed = subprocess.run(command, cwd=self._project_root, check=False)
        return completed.returncode

    def _start_process(self, service: ServiceSpec) -> ManagedProcess:
        self._log_dir.mkdir(parents=True, exist_ok=True)
        log_path = self._log_dir / f"{service.name}.log"
        with log_path.open("ab") as log_file:
            return subprocess.Popen(
                service.command,
                cwd=self._project_root,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )

    def _write(self, message: str) -> None:
        print(message, file=self._output)


def default_health_probe(timeout_seconds: float) -> HealthProbe:
    def probe(check: HealthCheck) -> bool:
        try:
            if check.kind == "http":
                request = urllib.request.Request(check.target, method="GET")
                with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                    status = int(response.status)
                    return 200 <= status < 300

            host, port = _parse_tcp_target(check.target)
            with socket.create_connection((host, port), timeout=timeout_seconds):
                return True
        except Exception:
            return False

    return probe


def terminate_process_tree(process: ManagedProcess, *, timeout_seconds: float = 5.0) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except Exception:
        process.terminate()

    try:
        process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except Exception:
            process.kill()
        process.wait(timeout=timeout_seconds)


def default_services() -> tuple[ServiceSpec, ...]:
    return (
        ServiceSpec(
            name="infra",
            kind="command",
            checks=(
                HealthCheck("postgres", "tcp", "127.0.0.1:5432"),
                HealthCheck("redis", "tcp", "127.0.0.1:6379"),
                HealthCheck("minio", "http", "http://127.0.0.1:9000/minio/health/live"),
            ),
            command=("docker", "compose", "-f", "infra/docker-compose.yml", "up", "-d"),
        ),
        ServiceSpec(
            name="api",
            kind="process",
            checks=(HealthCheck("api-ready", "http", "http://127.0.0.1:8000/health/ready"),),
            command=("make", "dev-api"),
            startup_grace_seconds=8.0,
        ),
        ServiceSpec(
            name="web",
            kind="process",
            checks=(HealthCheck("web-root", "http", "http://127.0.0.1:5173/"),),
            command=("make", "dev-web"),
            startup_grace_seconds=8.0,
        ),
    )


def select_services(
    services: Sequence[ServiceSpec],
    requested_names: str | None,
) -> tuple[ServiceSpec, ...]:
    if requested_names is None:
        return tuple(services)

    requested = {name.strip() for name in requested_names.split(",") if name.strip()}
    selected = tuple(service for service in services if service.name in requested)
    missing = requested - {service.name for service in selected}
    if missing:
        names = ", ".join(sorted(missing))
        raise SystemExit(f"Unknown service(s): {names}")
    return selected


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Watch and recover the local Content Factory stack.",
    )
    parser.add_argument("--once", action="store_true", help="Run one check/recovery pass and exit.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print recovery actions without running them.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Seconds between watchdog passes.",
    )
    parser.add_argument("--timeout", type=float, default=2.0, help="Seconds per health check.")
    parser.add_argument(
        "--services",
        help="Comma-separated subset to watch. Available: infra,api,web.",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=None,
        help="Directory for API/web process logs. Default: .logs/watchdog.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    project_root = Path(__file__).resolve().parents[1]
    services = select_services(default_services(), args.services)
    watchdog = DevWatchdog(
        services=services,
        project_root=project_root,
        dry_run=args.dry_run,
        log_dir=args.log_dir,
        health_timeout_seconds=args.timeout,
    )

    if args.once:
        watchdog.run_once()
    else:
        watchdog.run_forever(interval_seconds=args.interval)
    return 0


def _parse_tcp_target(target: str) -> tuple[str, int]:
    host, raw_port = target.rsplit(":", 1)
    return host, int(raw_port)


def _format_command(command: Sequence[str]) -> str:
    return " ".join(command)


if __name__ == "__main__":
    raise SystemExit(main())
