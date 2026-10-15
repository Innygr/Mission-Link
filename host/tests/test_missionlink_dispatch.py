import unittest

from host.missionlink_dispatch import DispatchError, ServiceDispatcher
from host.missionlink_envelopes import ServiceEnvelope
from host.missionlink_services import ServiceRecord, ServiceRegistry


NOW = 10_000


def request(**overrides):
    values = dict(
        kind="request", request_id="req-1", service_id="weather.local",
        operation="weather.current", created_at_ms=NOW - 1_000,
        expires_at_ms=NOW + 10_000, payload={"units": "metric"},
    )
    values.update(overrides)
    return ServiceEnvelope(**values).to_bytes()


def make_dispatcher(*, acl=None, healthy=True, replay_limit=10):
    registry = ServiceRegistry()
    registry.register(ServiceRecord(
        service_id="weather.local", host_id="weather.node",
        display_name="Weather", capabilities=("weather.current",),
        transports=("lan",), healthy=healthy, max_inline_request_bytes=96,
    ))
    dispatcher = ServiceDispatcher(
        registry, acl if acl is not None else {"client-1": frozenset({"weather.local"})},
        max_replay_entries=replay_limit,
    )
    dispatcher.register_handler(
        "weather.local", "weather.current",
        lambda principal, payload: {"temperatureC": 18},
    )
    return dispatcher


class ServiceDispatcherTests(unittest.TestCase):
    def test_authorized_request_returns_correlated_response(self):
        dispatcher = make_dispatcher()
        response = dispatcher.dispatch(request(), principal_id="client-1", now_ms=NOW)
        self.assertEqual(response.kind, "response")
        self.assertEqual(response.request_id, "req-1")
        self.assertEqual(response.payload, {"temperatureC": 18})
        self.assertEqual(ServiceEnvelope.from_bytes(response.to_bytes()), response)

    def test_unknown_or_unauthorized_principal_fails_closed(self):
        dispatcher = make_dispatcher()
        for principal in ("stranger", "", None):
            with self.subTest(principal=principal), self.assertRaises(DispatchError):
                dispatcher.dispatch(request(), principal_id=principal, now_ms=NOW)

    def test_replay_is_rejected_before_second_handler_call(self):
        calls = []
        dispatcher = make_dispatcher()
        dispatcher.register_handler("weather.local", "weather.current",
                                    lambda principal, payload: calls.append(principal) or {})
        dispatcher.dispatch(request(), principal_id="client-1", now_ms=NOW)
        with self.assertRaises(DispatchError) as caught:
            dispatcher.dispatch(request(), principal_id="client-1", now_ms=NOW)
        self.assertEqual(caught.exception.code, "replay")
        self.assertEqual(calls, ["client-1"])

    def test_replay_ids_are_scoped_to_principal(self):
        dispatcher = make_dispatcher(acl={
            "client-1": frozenset({"weather.local"}),
            "client-2": frozenset({"weather.local"}),
        })
        dispatcher.dispatch(request(), principal_id="client-1", now_ms=NOW)
        response = dispatcher.dispatch(request(), principal_id="client-2", now_ms=NOW)
        self.assertEqual(response.request_id, "req-1")

    def test_expired_future_and_non_request_messages_are_rejected(self):
        dispatcher = make_dispatcher()
        for raw in (
            request(expires_at_ms=NOW),
            request(created_at_ms=NOW + 60_000, expires_at_ms=NOW + 70_000),
            ServiceEnvelope(
                kind="response", request_id="req-2", service_id="weather.local",
                operation="weather.current", created_at_ms=NOW - 1,
                expires_at_ms=NOW + 1_000, payload={},
            ).to_bytes(),
        ):
            with self.subTest(raw=raw), self.assertRaises(DispatchError):
                dispatcher.dispatch(raw, principal_id="client-1", now_ms=NOW)

    def test_unknown_operation_and_unhealthy_service_are_rejected(self):
        dispatcher = make_dispatcher()
        with self.assertRaises(DispatchError) as caught:
            dispatcher.dispatch(request(operation="weather.admin"), principal_id="client-1", now_ms=NOW)
        self.assertEqual(caught.exception.code, "operation_not_found")
        dispatcher = make_dispatcher(healthy=False)
        with self.assertRaises(DispatchError) as caught:
            dispatcher.dispatch(request(), principal_id="client-1", now_ms=NOW)
        self.assertEqual(caught.exception.code, "unavailable")

    def test_payload_and_response_size_are_bounded(self):
        dispatcher = make_dispatcher()
        with self.assertRaises(DispatchError) as caught:
            dispatcher.dispatch(request(payload={"x": "a" * 100}), principal_id="client-1", now_ms=NOW)
        self.assertEqual(caught.exception.code, "too_large")
        dispatcher.register_handler("weather.local", "weather.current",
                                    lambda principal, payload: {"data": "x" * 200})
        with self.assertRaises(DispatchError) as caught:
            dispatcher.dispatch(request(request_id="req-2"), principal_id="client-1", now_ms=NOW)
        self.assertEqual(caught.exception.code, "response_too_large")

    def test_replay_cache_has_a_hard_bound_and_prunes_expired_entries(self):
        dispatcher = make_dispatcher(replay_limit=1)
        dispatcher.dispatch(request(), principal_id="client-1", now_ms=NOW)
        with self.assertRaises(DispatchError) as caught:
            dispatcher.dispatch(request(request_id="req-2"), principal_id="client-1", now_ms=NOW)
        self.assertEqual(caught.exception.code, "replay_cache_full")
        dispatcher.dispatch(request(request_id="req-2"), principal_id="client-1", now_ms=NOW + 300_000)
        self.assertEqual(len(dispatcher._seen), 1)

    def test_handler_failures_do_not_leak_exception_details(self):
        dispatcher = make_dispatcher()
        dispatcher.register_handler("weather.local", "weather.current",
                                    lambda principal, payload: 1 / 0)
        with self.assertRaises(DispatchError) as caught:
            dispatcher.dispatch(request(), principal_id="client-1", now_ms=NOW)
        self.assertEqual(caught.exception.code, "handler_failed")
        self.assertNotIn("division", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
