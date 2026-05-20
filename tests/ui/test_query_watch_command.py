"""UI tests for recurring query watch commands."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from sqlit.domains.shell.app.main import SSMSTUI
from sqlit.shared.app.runtime import RuntimeConfig

from .mocks import MockConnectionStore, MockSettingsStore, build_test_services, create_test_connection


class _DummyTimer:
    def __init__(self) -> None:
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


def _make_app() -> SSMSTUI:
    runtime = RuntimeConfig(process_worker=False)
    services = build_test_services(
        runtime=runtime,
        connection_store=MockConnectionStore([create_test_connection("demo", "sqlite")]),
        settings_store=MockSettingsStore({"theme": "tokyo-night"}),
    )
    return SSMSTUI(services=services)


class TestWatchCommand:
    @pytest.mark.asyncio
    async def test_watch_command_schedules_recurring_query_execution(self) -> None:
        app = _make_app()

        async with app.run_test(size=(100, 35)) as pilot:
            await pilot.pause()
            app.query_input.text = "select 1"
            app.current_connection = object()
            app.current_provider = MagicMock()
            app.current_config = create_test_connection("demo", "sqlite")
            app._watch_query_timer = None
            app._watch_query_interval_s = 0.0
            app._watch_query_running = False
            app._watch_query_last_sql = None
            app._watch_query_execution_count = 0

            timer = _DummyTimer()
            app.set_interval = MagicMock(return_value=timer)
            app._execute_query_common = MagicMock()

            app._run_command("watch 2s")
            await pilot.pause()

            app.set_interval.assert_called_once()
            interval, callback = app.set_interval.call_args.args[:2]
            assert interval == 2.0
            assert callable(callback)
            assert app._watch_query_timer is timer
            assert app._watch_query_interval_s == 2.0
            assert app._watch_query_last_sql == "select 1"
            assert app._watch_query_execution_count == 0
            assert app._last_notification == "Query watch enabled (2s)"

            callback()
            assert app._execute_query_common.call_count == 1
            assert app._watch_query_execution_count == 1

    @pytest.mark.asyncio
    async def test_watch_off_stops_existing_timer(self) -> None:
        app = _make_app()

        async with app.run_test(size=(100, 35)) as pilot:
            await pilot.pause()
            timer = _DummyTimer()
            app._watch_query_timer = timer
            app._watch_query_interval_s = 5.0
            app._watch_query_last_sql = "select 1"
            app._watch_query_execution_count = 3

            app._run_command("watch off")
            await pilot.pause()

            assert timer.stopped is True
            assert app._watch_query_timer is None
            assert app._watch_query_interval_s == 0.0
            assert app._watch_query_last_sql is None
            assert app._watch_query_execution_count == 0
            assert app._last_notification == "Query watch disabled"

    @pytest.mark.asyncio
    async def test_watch_tick_does_not_overlap_running_query(self) -> None:
        app = _make_app()

        async with app.run_test(size=(100, 35)) as pilot:
            await pilot.pause()
            app.query_input.text = "select 1"
            app.current_connection = object()
            app.current_provider = MagicMock()
            app.current_config = create_test_connection("demo", "sqlite")
            app.query_executing = True
            app._watch_query_running = False
            app._watch_query_execution_count = 0
            app._watch_query_last_sql = "select 1"
            app._execute_query_common = MagicMock()

            app._watch_query_tick()
            await pilot.pause()

            app._execute_query_common.assert_not_called()
            assert app._watch_query_execution_count == 0
            assert app._last_notification == "Watch skipped: query already running"

    @pytest.mark.asyncio
    async def test_watch_command_requires_active_connection_and_query(self) -> None:
        app = _make_app()

        async with app.run_test(size=(100, 35)) as pilot:
            await pilot.pause()
            app.query_input.text = ""
            app.current_connection = None
            app.current_provider = None
            app.current_config = None
            app._watch_query_timer = None

            app._run_command("watch 1s")
            await pilot.pause()

            assert app._watch_query_timer is None
            assert app._last_notification == "Connect to a server to watch queries"
