"""
Camera Simulator — Generates synthetic camera frames for testing.

Creates a mock RTSP-like video source that generates frames with
moving colored rectangles (simulating people) for pipeline testing
without requiring a real camera.

Usage:
    python scripts/camera_simulator.py [--output data/test_video.mp4] [--duration 60] [--fps 15]
"""

import argparse
import sys
import time
import math
from pathlib import Path

import cv2
import numpy as np


def generate_test_video(
    output_path: str = "data/test_video.mp4",
    duration: int = 60,
    fps: int = 15,
    width: int = 640,
    height: int = 480,
) -> None:
    """Generate a test video with simulated people movement."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output), fourcc, fps, (width, height))

    if not writer.isOpened():
        print(f"Failed to create video writer at {output}")
        sys.exit(1)

    total_frames = duration * fps
    print(f"Generating test video: {output}")
    print(f"   Resolution: {width}x{height} @ {fps} FPS")
    print(f"   Duration: {duration}s ({total_frames} frames)")

    # Simulated "people" — moving rectangles
    people = [
        {"x": 100, "y": 200, "vx": 2.0, "vy": 0.5, "w": 50, "h": 120, "color": (0, 180, 255)},
        {"x": 400, "y": 300, "vx": -1.5, "vy": 0.8, "w": 45, "h": 110, "color": (255, 100, 0)},
        {"x": 300, "y": 150, "vx": 1.0, "vy": -0.3, "w": 55, "h": 130, "color": (0, 255, 100)},
    ]

    # Zone overlays
    zones = {
        "entrance_line": {"points": [(100, 400), (540, 400)], "color": (0, 255, 255)},
        "lobby": {
            "points": [(50, 200), (590, 200), (590, 450), (50, 450)],
            "color": (255, 255, 0),
        },
        "checkout": {
            "points": [(400, 100), (600, 100), (600, 300), (400, 300)],
            "color": (0, 255, 0),
        },
        "restricted_area": {
            "points": [(10, 10), (200, 10), (200, 150), (10, 150)],
            "color": (0, 0, 255),
        },
    }

    for frame_idx in range(total_frames):
        # Dark background with subtle gradient
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:] = (25, 20, 15)

        # Add subtle grid pattern
        for gx in range(0, width, 40):
            cv2.line(frame, (gx, 0), (gx, height), (35, 30, 25), 1)
        for gy in range(0, height, 40):
            cv2.line(frame, (0, gy), (width, gy), (35, 30, 25), 1)

        # Draw zones
        for name, zone in zones.items():
            pts = np.array(zone["points"], dtype=np.int32)
            if len(pts) == 2:
                # Line zone
                cv2.line(frame, tuple(pts[0]), tuple(pts[1]), zone["color"], 2)
            else:
                # Polygon zone
                overlay = frame.copy()
                cv2.fillPoly(overlay, [pts], (*zone["color"][:3],))
                cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
                cv2.polylines(frame, [pts], True, zone["color"], 1)

            # Zone label
            label_pos = (pts[0][0] + 5, pts[0][1] + 15)
            cv2.putText(
                frame, name, label_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.4, zone["color"], 1
            )

        # Update and draw people
        t = frame_idx / fps
        for i, p in enumerate(people):
            # Add sinusoidal variation to movement
            dx = p["vx"] + math.sin(t * 0.5 + i) * 0.5
            dy = p["vy"] + math.cos(t * 0.3 + i) * 0.3

            p["x"] += dx
            p["y"] += dy

            # Bounce off walls
            if p["x"] < 0 or p["x"] + p["w"] > width:
                p["vx"] *= -1
                p["x"] = max(0, min(p["x"], width - p["w"]))
            if p["y"] < 0 or p["y"] + p["h"] > height:
                p["vy"] *= -1
                p["y"] = max(0, min(p["y"], height - p["h"]))

            # Draw person rectangle
            x1, y1 = int(p["x"]), int(p["y"])
            x2, y2 = x1 + p["w"], y1 + p["h"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), p["color"], 2)
            cv2.rectangle(frame, (x1 + 2, y1 + 2), (x2 - 2, y2 - 2), p["color"], -1)

            # Label
            cv2.putText(
                frame,
                f"P{i + 1}",
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                p["color"],
                1,
            )

        # Timestamp overlay
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(
            frame,
            f"CAM-01 | {ts} | Frame {frame_idx + 1}/{total_frames}",
            (10, height - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (150, 150, 150),
            1,
        )

        writer.write(frame)

        # Progress
        if (frame_idx + 1) % (fps * 10) == 0 or frame_idx == total_frames - 1:
            pct = ((frame_idx + 1) / total_frames) * 100
            print(f"   Progress: {pct:.0f}% ({frame_idx + 1}/{total_frames} frames)")

    writer.release()
    size_mb = output.stat().st_size / (1024 * 1024)
    print(f"Video saved: {output} ({size_mb:.1f} MB)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate test video for Edge AI CCTV")
    parser.add_argument("--output", default="data/test_video.mp4", help="Output path")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds")
    parser.add_argument("--fps", type=int, default=15, help="Frames per second")
    parser.add_argument("--width", type=int, default=640, help="Frame width")
    parser.add_argument("--height", type=int, default=480, help="Frame height")
    args = parser.parse_args()

    generate_test_video(args.output, args.duration, args.fps, args.width, args.height)


if __name__ == "__main__":
    main()
