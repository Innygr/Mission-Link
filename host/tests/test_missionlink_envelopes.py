import json
import unittest

from host.missionlink_envelopes import MAX_ENVELOPE_BYTES, EnvelopeError, ServiceEnvelope, is_expired


def envelope(**overrides):
    values = dict(
        kind="request", request_id="req_01", service_id="weather.local",
        operation="weather.current", created_at_ms=1_000, expires_at_ms=31_000,
        payload={"units": "metric"},
    )
    values.update(overrides)
    return ServiceEnvelope(**values)


class ServiceEnvelopeTests(unittest.TestCase):
    def test_round_trip(self):
        original = envelope()
        wire = original.to_bytes()
        self.assertLessEqual(len(wire), MAX_ENVELOPE_BYTES)
        self.assertEqual(ServiceEnvelope.from_bytes(wire), original)

    def test_error_requires_known_code(self):
        good = envelope(kind="error", error_code="unavailable")
        self.assertEqual(ServiceEnvelope.from_bytes(good.to_bytes()), good)
        with self.assertRaises(EnvelopeError):
            envelope(kind="error").to_bytes()
        with self.assertRaises(EnvelopeError):
            envelope(error_code="unavailable").to_bytes()

    def test_rejects_bad_ids_times_and_lifetime(self):
        for bad in (
            envelope(request_id="contains spaces"), envelope(service_id="../private"),
            envelope(operation=""), envelope(created_at_ms=True), envelope(expires_at_ms=1_000),
            envelope(expires_at_ms=301_001),
        ):
            with self.subTest(bad=bad), self.assertRaises(EnvelopeError):
                bad.to_bytes()

    def test_rejects_unbounded_or_non_json_payloads(self):
        for payload in ([], "string", {"bad": float("nan")}, {"nested": [[[[[[[[[[0]]]]]]]]]]}):
            with self.subTest(payload=payload), self.assertRaises(EnvelopeError):
                envelope(payload=payload).to_bytes()

    def test_rejects_oversized_envelope(self):
        with self.assertRaises(EnvelopeError):
            envelope(payload={"text": "x" * 200}).to_bytes()

    def test_decoder_rejects_unknown_fields_versions_and_malformed_data(self):
        base = json.loads(envelope().to_bytes())
        for mutate in (
            lambda obj: obj.update(extra=True), lambda obj: obj.update(v=2),
            lambda obj: obj.update(expiresAtMs="later"),
        ):
            obj = dict(base)
            mutate(obj)
            with self.subTest(obj=obj), self.assertRaises(EnvelopeError):
                ServiceEnvelope.from_bytes(json.dumps(obj, separators=(",", ":")).encode())
        for raw in (b"", b"not json", b"[]", b'{"v":NaN}'):
            with self.subTest(raw=raw), self.assertRaises(EnvelopeError):
                ServiceEnvelope.from_bytes(raw)

    def test_expiry_boundary(self):
        item = envelope()
        self.assertFalse(is_expired(item, 30_999))
        self.assertTrue(is_expired(item, 31_000))
        with self.assertRaises(EnvelopeError):
            is_expired(item, True)


if __name__ == "__main__":
    unittest.main()
