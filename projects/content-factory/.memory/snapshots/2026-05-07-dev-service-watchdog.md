Project Path: content-factory

Source Tree:

```txt
content-factory
├── Makefile
├── README.md
├── apps
│   └── worker
│       └── tests
│           └── test_dev_watchdog.py
└── scripts
    └── dev_watchdog.py

```

`Makefile`:

```
BOOTSTRAP_PYTHON ?= python3
PYTHON_BIN ?= .venv/bin/python
PYTHONPATH_VALUE := apps/api/src:apps/worker/src
PYTHON_SOURCES := apps/api/src apps/api/tests apps/worker/src apps/worker/tests scripts
PYTHON_TYPECHECK_SOURCES := apps/api/src apps/worker/src scripts
OPENAPI_OUTPUT := packages/contracts/openapi/content-factory.openapi.json

.PHONY: install install-node install-python lint-web typecheck-web test-web test-web-e2e lint-api typecheck-api test-api migrate-api dev-web dev-api dev-watchdog export-openapi generate-contracts

install: install-node install-python

install-node:
	pnpm install

install-python:
	$(BOOTSTRAP_PYTHON) -m venv .venv
	$(PYTHON_BIN) -m pip install --upgrade pip
	$(PYTHON_BIN) -m pip install -e '.[dev]'

lint-web:
	pnpm --dir apps/web lint

typecheck-web:
	pnpm --dir apps/web typecheck

test-web:
	pnpm --dir apps/web test --run

test-web-e2e:
	pnpm --dir apps/web test:e2e

lint-api:
	PYTHONPATH=$(PYTHONPATH_VALUE) $(PYTHON_BIN) -m ruff check $(PYTHON_SOURCES)

typecheck-api:
	PYTHONPATH=$(PYTHONPATH_VALUE) $(PYTHON_BIN) -m mypy $(PYTHON_TYPECHECK_SOURCES)

test-api:
	PYTHONPATH=$(PYTHONPATH_VALUE) $(PYTHON_BIN) -m pytest

migrate-api:
	PYTHONPATH=$(PYTHONPATH_VALUE) $(PYTHON_BIN) -m alembic upgrade head

dev-web:
	pnpm --dir apps/web dev

dev-api:
	PYTHONPATH=$(PYTHONPATH_VALUE) $(PYTHON_BIN) -m uvicorn content_factory_api.app:create_app --factory --app-dir apps/api/src --host 0.0.0.0 --port 8000 --reload

dev-watchdog:
	$(PYTHON_BIN) scripts/dev_watchdog.py

export-openapi:
	PYTHONPATH=$(PYTHONPATH_VALUE) $(PYTHON_BIN) -m content_factory_api.export_openapi --output $(OPENAPI_OUTPUT)

generate-contracts: export-openapi
	pnpm --dir packages/contracts generate

```

`README.md`:

```md
# Content Factory

AI-сервис контент-завода для цифровых аватаров, коротких видео, human-in-the-loop production pipeline и аналитического цикла улучшения контента.

## Статус

Проект перешел из чистого planning в раннюю реализацию пилота. Recommended stack зафиксирован, а первый технический срез `Phase 1` уже поднял monorepo bootstrap, web/api/worker baseline, local infra и OpenAPI contract generation.

## Быстрый старт для агента

1. Прочитать `AGENTS.md`.
2. Прочитать `.memory/context.md`.
3. Для бизнес-задач прочитать `.business/INDEX.md`, затем только нужные файлы внутри `.business/`.
4. Перед реализацией нетривиальных задач использовать workflow из `shared/skills/bulletproof/SKILL.md`.

## Структура

- `apps/web/` - React 19 + Vite bootstrap для operator cockpit.
- `apps/api/` - FastAPI control-plane API с config validation и health endpoints.
- `apps/worker/` - Dramatiq worker bootstrap для async/render workloads.
- `packages/contracts/` - OpenAPI-derived typed contracts.
- `infra/` - local Docker Compose baseline для Postgres, Redis и MinIO.
- `.business/` - скрытый бизнес-контекст, не коммитится.
- `.memory/` - рабочая память проекта, решения, handoff-и, snapshots.
- `docs/` - документация.
- `scripts/` - служебные скрипты.

## Команды

- Node install: `pnpm install`
- Python install: `make install-python BOOTSTRAP_PYTHON=/path/to/python3.12`
- Web gates: `make lint-web && make typecheck-web && make test-web`
- API/worker gates: `make lint-api && make typecheck-api && make test-api`
- API migrations: `make migrate-api`
- Contracts: `make generate-contracts`
- Dev servers: `make dev-web` и `make dev-api`
- Dev watchdog: `make dev-watchdog` следит за local infra/API/web и поднимает упавшие части; безопасная проверка без запуска процессов: `.venv/bin/python scripts/dev_watchdog.py --once --dry-run`

## Web Dev Notes

- `VITE_API_BASE_URL=/` использует same-origin proxy Vite для `/api` и `/health`, чтобы local cockpit работал без отдельной CORS-настройки API.
- Presigned upload URLs на локальный MinIO автоматически проксируются через dev server path `"/__storage_proxy"` для browser upload flow.

```

`apps/worker/tests/test_dev_watchdog.py`:

```py
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

```

`scripts/dev_watchdog.py`:

```py
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

```