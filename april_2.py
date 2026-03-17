#!/usr/bin/env python3
"""
AprilTag GPS Prototype -4-Tag Cube Version
=============================================
Generates 4 AprilTags (N/E/S/W) for the base station cube,
then opens webcam to compute your laptop's GPS position.

Setup:
  pip install opencv-python numpy pupil-apriltags moms-apriltag Pillow

Usage:
  python apriltag_gps_4tags.py
"""

import os
import sys
import math
import platform
import subprocess

import cv2
import numpy as np
from PIL import Image

try:
    from pupil_apriltags import Detector
except ImportError:
    print("ERROR: pip install pupil-apriltags")
    sys.exit(1)

try:
    from moms_apriltag import TagGenerator2
except ImportError:
    print("ERROR: pip install moms-apriltag")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

BASE_LATITUDE  = 44.811762669944315    # bills house    44.811762669944315, -93.30598577393306
BASE_LONGITUDE = -93.30598577393306   # Your house
BASE_HEADING_DEG = 0.0

TAG_FAMILY = "tag36h11"
TAG_PX = 800
BORDER_PX = 80

# 4 tags -one per face
TAGS = {
    0: "NORTH",
    1: "EAST",
    2: "SOUTH",
    3: "WEST",
}

CAM_W, CAM_H = 1280, 720
FX = FY = 920.0
CX, CY = CAM_W / 2, CAM_H / 2
EARTH_RADIUS = 6371000.0


# ═══════════════════════════════════════════════════════════════
# STEP 1: Generate ALL 4 tags
# ═══════════════════════════════════════════════════════════════

def generate_all_tags():
    """Generate 4 AprilTag images for the cube faces."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tag_dir = os.path.join(script_dir, "april_tags")
    os.makedirs(tag_dir, exist_ok=True)

    tg = TagGenerator2(TAG_FAMILY)

    print("\n" + "=" * 60)
    print("  AprilTag GPS Prototype -4-Tag Cube")
    print("=" * 60)
    print(f"\n  Base station: {BASE_LATITUDE:.8f}, {BASE_LONGITUDE:.8f}")
    print(f"\n  Generating 4 tags for cube faces...\n")

    filepaths = {}

    for tag_id, face in TAGS.items():
        # Generate tag
        tag_raw = tg.generate(tag_id)
        inner = TAG_PX - 2 * BORDER_PX
        tag_scaled = cv2.resize(tag_raw, (inner, inner), interpolation=cv2.INTER_NEAREST)

        # Add white border
        img = np.ones((TAG_PX, TAG_PX), dtype=np.uint8) * 255
        img[BORDER_PX:BORDER_PX + inner, BORDER_PX:BORDER_PX + inner] = tag_scaled

        # Add face label at the top
        img_color = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        label = f"ID:{tag_id} -{face} FACE"
        cv2.putText(img_color, label, (TAG_PX // 2 - 150, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)

        # Save
        filename = f"{TAG_FAMILY}_id{tag_id}_{face}.png"
        filepath = os.path.join(tag_dir, filename)
        cv2.imwrite(filepath, img_color)
        filepaths[tag_id] = filepath
        print(f"  ✅ Tag ID {tag_id} ({face}) → {filepath}")

    # Also create a single combined image with all 4 tags
    print(f"\n  Creating combined image with all 4 tags...")
    combined_w = TAG_PX * 2 + 40
    combined_h = TAG_PX * 2 + 120
    combined = np.ones((combined_h, combined_w, 3), dtype=np.uint8) * 255

    # Title
    cv2.putText(combined, "AprilTag Base Station -Print All 4 Faces",
                (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    cv2.putText(combined, f"Family: {TAG_FAMILY} | Location: {BASE_LATITUDE:.6f}, {BASE_LONGITUDE:.6f}",
                (40, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)

    # Place 4 tags in 2x2 grid
    positions = [
        (0, "NORTH", 10, 100),           # top-left
        (1, "EAST", TAG_PX + 30, 100),   # top-right
        (2, "SOUTH", 10, TAG_PX + 110),  # bottom-left
        (3, "WEST", TAG_PX + 30, TAG_PX + 110),  # bottom-right
    ]

    for tag_id, face, x, y in positions:
        tag_img = cv2.imread(filepaths[tag_id])
        h, w = tag_img.shape[:2]
        # Make sure it fits
        if y + h <= combined_h and x + w <= combined_w:
            combined[y:y+h, x:x+w] = tag_img

    combined_path = os.path.join(tag_dir, "ALL_4_TAGS_COMBINED.png")
    cv2.imwrite(combined_path, combined)
    print(f"  ✅ Combined → {combined_path}")

    # Open the combined image
    if platform.system() == "Darwin":
        subprocess.Popen(["open", combined_path])
    elif platform.system() == "Linux":
        subprocess.Popen(["xdg-open", combined_path])
    elif platform.system() == "Windows":
        os.startfile(combined_path)

    print(f"\n  All tags saved in: {tag_dir}")
    print(f"  Print each tag and attach to the cube face.")
    print(f"    Tag ID 0 → NORTH face")
    print(f"    Tag ID 1 → EAST face")
    print(f"    Tag ID 2 → SOUTH face")
    print(f"    Tag ID 3 → WEST face")

    return tag_dir


# ═══════════════════════════════════════════════════════════════
# STEP 2: GPS math
# ═══════════════════════════════════════════════════════════════

def offset_to_gps(base_lat, base_lon, east_m, north_m):
    d_lat = north_m / EARTH_RADIUS
    d_lon = east_m / (EARTH_RADIUS * math.cos(math.radians(base_lat)))
    return base_lat + math.degrees(d_lat), base_lon + math.degrees(d_lon)


# ═══════════════════════════════════════════════════════════════
# STEP 3: Live webcam -detects ANY of the 4 tags
# ═══════════════════════════════════════════════════════════════

def run_camera(tag_size_cm):
    """Open webcam, detect any of the 4 tags, show live GPS."""
    tag_size_m = tag_size_cm / 100.0
    heading_rad = math.radians(BASE_HEADING_DEG)
    box_half = 0.5  # half the box size in meters (adjust to your cube)

    K = np.array([[FX, 0, CX], [0, FY, CY], [0, 0, 1]], dtype=np.float64)
    D = np.zeros((5, 1), dtype=np.float64)

    detector = Detector(
        families=TAG_FAMILY,
        nthreads=4,
        quad_decimate=1.5,
        quad_sigma=0.0,
        refine_edges=1,
        decode_sharpening=0.25,
    )

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)

    if not cap.isOpened():
        print("ERROR: Could not open camera.")
        sys.exit(1)

    # Tag face configs: offset from box center + face normal direction
    tag_config = {
        0: {"face": "NORTH", "normal_yaw": 0.0,
            "offset": np.array([0.0, box_half, 0.0])},
        1: {"face": "EAST",  "normal_yaw": -math.pi / 2,
            "offset": np.array([box_half, 0.0, 0.0])},
        2: {"face": "SOUTH", "normal_yaw": math.pi,
            "offset": np.array([0.0, -box_half, 0.0])},
        3: {"face": "WEST",  "normal_yaw": math.pi / 2,
            "offset": np.array([-box_half, 0.0, 0.0])},
    }

    print(f"\n  Camera open!")
    print(f"  Show ANY of the 4 tags (ID 0-3) to the camera.")
    print(f"  The detected face name will appear on screen.")
    print(f"  Press Q to quit.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        detections = detector.detect(
            gray,
            estimate_tag_pose=True,
            camera_params=(FX, FY, CX, CY),
            tag_size=tag_size_m,
        )

        found = False
        for det in detections:
            tag_id = det.tag_id
            if tag_id not in tag_config:
                continue
            found = True

            cfg = tag_config[tag_id]
            face_name = cfg["face"]
            face_yaw = cfg["normal_yaw"]
            tag_offset = cfg["offset"]

            tx, ty, tz = det.pose_t.flatten()
            dist_m = math.sqrt(tx ** 2 + ty ** 2 + tz ** 2)

            # Camera position relative to tag in ENU
            cam_east = -tx
            cam_north = -tz

            # Rotate tag offset by heading
            cos_h = math.cos(heading_rad)
            sin_h = math.sin(heading_rad)
            tag_east = tag_offset[0] * cos_h - tag_offset[1] * sin_h
            tag_north = tag_offset[0] * sin_h + tag_offset[1] * cos_h

            # Rotate camera offset by face normal + heading
            total_yaw = face_yaw + heading_rad
            cos_t = math.cos(total_yaw)
            sin_t = math.sin(total_yaw)
            east_rotated = cam_east * cos_t - cam_north * sin_t + tag_east
            north_rotated = cam_east * sin_t + cam_north * cos_t + tag_north

            my_lat, my_lon = offset_to_gps(
                BASE_LATITUDE, BASE_LONGITUDE,
                east_rotated, north_rotated)

            # Draw tag outline
            corners = det.corners.astype(int)
            cv2.polylines(frame, [corners], True, (0, 255, 0), 3)
            cx_tag, cy_tag = int(det.center[0]), int(det.center[1])
            cv2.circle(frame, (cx_tag, cy_tag), 8, (0, 255, 0), -1)

            # Draw 3D axes
            rvec, _ = cv2.Rodrigues(det.pose_R)
            axis_len = tag_size_m / 2
            pts = np.float32([[0,0,0],[axis_len,0,0],[0,axis_len,0],[0,0,-axis_len]])
            imgpts, _ = cv2.projectPoints(pts, rvec, det.pose_t, K, D)
            origin = tuple(imgpts[0].ravel().astype(int))
            cv2.line(frame, origin, tuple(imgpts[1].ravel().astype(int)), (0,0,255), 3)
            cv2.line(frame, origin, tuple(imgpts[2].ravel().astype(int)), (0,255,0), 3)
            cv2.line(frame, origin, tuple(imgpts[3].ravel().astype(int)), (255,0,0), 3)

            # HUD
            cv2.rectangle(frame, (8, 8), (540, 250), (0, 0, 0), -1)
            cv2.rectangle(frame, (8, 8), (540, 250), (0, 255, 0), 2)

            hud = [
                f"DETECTED: Tag ID {tag_id} -{face_name} FACE",
                f"Family: {TAG_FAMILY}",
                f"",
                f"Base station (tag location):",
                f"  Lat: {BASE_LATITUDE:.8f}",
                f"  Lon: {BASE_LONGITUDE:.8f}",
                f"",
                f"MY LOCATION (laptop/segway):",
                f"  Lat: {my_lat:.8f}",
                f"  Lon: {my_lon:.8f}",
                f"",
                f"Distance: {dist_m:.3f} m ({dist_m*100:.1f} cm)",
                f"Offset: E={east_rotated:+.3f}m  N={north_rotated:+.3f}m",
            ]

            colors = [
                (0, 255, 0), (150, 150, 150), (150, 150, 150),
                (180, 180, 180), (180, 180, 180), (180, 180, 180), (180, 180, 180),
                (0, 255, 255), (0, 255, 255), (0, 255, 255), (0, 255, 255),
                (255, 200, 0), (200, 200, 200),
            ]

            for i, line in enumerate(hud):
                color = colors[i] if i < len(colors) else (200, 200, 200)
                weight = 2 if i == 0 or line.startswith("MY") else 1
                cv2.putText(frame, line, (18, 30 + i * 17),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, weight)

            # Console
            print(
                f"\r  [{face_name}] ID:{tag_id} | "
                f"Lat: {my_lat:.8f}  Lon: {my_lon:.8f} | "
                f"dist={dist_m:.3f}m   ",
                end="", flush=True)

        if not found:
            cv2.rectangle(frame, (8, 8), (500, 50), (0, 0, 0), -1)
            cv2.putText(frame, "No tag detected -show any face (ID 0-3) to camera",
                        (18, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 200), 2)

        cv2.imshow("AprilTag 4-Face Cube Prototype  [Q = quit]", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("\n\n  Done!")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    # Generate all 4 tags
    tag_dir = generate_all_tags()

    print("\n  Print or display the tags on your cube.")
    print("  Measure the black square side length in cm.")

    while True:
        raw = input("\n  Tag side length in cm (e.g. 7.5): ").strip().replace(",", ".")
        try:
            tag_cm = float(raw)
            if tag_cm > 0:
                break
        except ValueError:
            pass
        print("  Enter a positive number")

    input(f"\n  Tag size = {tag_cm} cm. Press ENTER to start camera ...")
    run_camera(tag_cm)


if __name__ == "__main__":
    main()