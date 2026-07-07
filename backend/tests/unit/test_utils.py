"""Unit tests for utility modules."""

import numpy as np
import pytest


class TestGeometryUtils:
    """Tests for app.utils.geometry."""

    def test_bbox_center(self) -> None:
        from app.utils.geometry import bbox_center

        cx, cy = bbox_center(100, 200, 200, 400)
        assert cx == 150.0
        assert cy == 300.0

    def test_bbox_center_zero(self) -> None:
        from app.utils.geometry import bbox_center

        cx, cy = bbox_center(0, 0, 100, 100)
        assert cx == 50.0
        assert cy == 50.0


class TestTimeUtils:
    """Tests for app.utils.time."""

    def test_now_utc_has_timezone(self) -> None:
        from app.utils.time import now_utc

        dt = now_utc()
        assert dt.tzinfo is not None

    def test_iso_roundtrip(self) -> None:
        from app.utils.time import now_utc, to_iso, from_iso

        dt = now_utc()
        iso = to_iso(dt)
        parsed = from_iso(iso)
        assert abs((dt - parsed).total_seconds()) < 1

    def test_elapsed_seconds(self) -> None:
        from datetime import timedelta
        from app.utils.time import now_utc, elapsed_seconds

        start = now_utc()
        end = start + timedelta(seconds=5.5)
        assert elapsed_seconds(start, end) == pytest.approx(5.5)


class TestLetterbox:
    """Tests for app.ai.preprocessing.letterbox."""

    def test_prepare_input_shape(self) -> None:
        from app.ai.preprocessing.letterbox import prepare_input

        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        tensor, info = prepare_input(image, target_size=(640, 640))
        assert tensor.shape == (1, 3, 640, 640)
        assert tensor.dtype == np.float32

    def test_prepare_input_normalized(self) -> None:
        from app.ai.preprocessing.letterbox import prepare_input

        image = np.ones((480, 640, 3), dtype=np.uint8) * 255
        tensor, _ = prepare_input(image, target_size=(640, 640))
        assert tensor.max() <= 1.0
        assert tensor.min() >= 0.0
