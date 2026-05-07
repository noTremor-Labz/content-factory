from __future__ import annotations

from io import StringIO
from pathlib import Path

from scripts.dev_watchdog import DevWatchdog, HealthCheck, ManagedProcess, ServiceSpec


class FakeProcess(ManagedProcess):
    def __init__(self, pid: int = 1001) -> None:
        self.pid = pid
        self.returncode: int | None = None
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        _ = timeout
        self.returncode = 0 if self.returncode is None else self.returncode
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = 0

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9


def test_healthy_services_do_nothing(tmp_path: Path) -> None:
    commands: list[tuple[str, ...]] = []
    processes: list[tuple[str, ...]] = []
    service = _service("api", "process", ("make", "dev-api"))
    output = StringIO()
    watchdog = DevWatchdog(
        services=(service,),
        project_root=tmp_path,
        dry_run=False,
        health_probe=lambda _check: True,
        command_runner=lambda command: commands.append(command) or 0,
        process_starter=lambda spec: processes.append(spec.command) or FakeProcess(),
        output=output,
    )

    watchdog.run_once()

    assert commands == []
    assert processes == []
    assert "healthy" in output.getvalue()


def test_dry_run_reports_recovery_without_starting_process(tmp_path: Path) -> None:
    processes: list[tuple[str, ...]] = []
    service = _service("api", "process", ("make", "dev-api"))
    output = StringIO()
    watchdog = DevWatchdog(
        services=(service,),
        project_root=tmp_path,
        dry_run=True,
        health_probe=lambda _check: False,
        process_starter=lambda spec: processes.append(spec.command) or FakeProcess(),
        output=output,
    )

    watchdog.run_once()

    assert processes == []
    assert "[dry-run] would start api: make dev-api" in output.getvalue()


def test_unhealthy_command_service_runs_recovery(tmp_path: Path) -> None:
    commands: list[tuple[str, ...]] = []
    service = _service(
        "infra",
        "command",
        ("docker", "compose", "-f", "infra/docker-compose.yml", "up", "-d"),
    )
    watchdog = DevWatchdog(
        services=(service,),
        project_root=tmp_path,
        health_probe=lambda _check: False,
        command_runner=lambda command: commands.append(command) or 0,
    )

    watchdog.run_once()

    assert commands == [("docker", "compose", "-f", "infra/docker-compose.yml", "up", "-d")]


def test_unhealthy_process_service_starts_managed_process(tmp_path: Path) -> None:
    started: list[tuple[str, ...]] = []
    service = _service("web", "process", ("make", "dev-web"))
    watchdog = DevWatchdog(
        services=(service,),
        project_root=tmp_path,
        health_probe=lambda _check: False,
        process_starter=lambda spec: started.append(spec.command) or FakeProcess(),
    )

    watchdog.run_once()

    assert started == [("make", "dev-web")]


def test_exited_managed_process_restarts_when_unhealthy(tmp_path: Path) -> None:
    started_processes: list[FakeProcess] = []
    service = _service("api", "process", ("make", "dev-api"))

    def start_process(_spec: ServiceSpec) -> FakeProcess:
        process = FakeProcess(pid=1000 + len(started_processes))
        started_processes.append(process)
        return process

    watchdog = DevWatchdog(
        services=(service,),
        project_root=tmp_path,
        health_probe=lambda _check: False,
        process_starter=start_process,
    )
    watchdog.run_once()
    started_processes[0].returncode = 1

    watchdog.run_once()

    assert len(started_processes) == 2
    assert started_processes[0].terminated is False


def _service(
    name: str,
    kind: str,
    command: tuple[str, ...],
) -> ServiceSpec:
    return ServiceSpec(
        name=name,
        kind=kind,
        checks=(HealthCheck(name=f"{name}-check", kind="http", target="http://localhost"),),
        command=command,
        startup_grace_seconds=0.0,
    )
