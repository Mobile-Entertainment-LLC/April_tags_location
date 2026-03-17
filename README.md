# AprilTag GPS Prototype

A proof-of-concept that computes a device's GPS coordinates using AprilTag fiducial markers instead of GPS. Place a tag at a known location, point a camera at it, and the system calculates the camera's lat/lon position in real time based on the tag's distance and angle.

Built as Phase 1 of the oTo segway localization system — solving GPS-denied positioning under bridges and covered structures.

## Demo

![4-Face Cube Detection](demo_screenshot.png)

*Live detection of Tag ID 3 (WEST face) on a physical cube. The system computes the camera's GPS coordinates in real time from the tag's known position — no GPS needed.*

## How It Works

1. An AprilTag is placed at a **known GPS location** (manually entered)
2. A camera detects the tag and measures **distance + angle** to it
3. The system computes: `known tag position + measured offset = camera position`
4. Lat/lon updates live as the tag moves closer, farther, or side to side

## Demo Results

Tested with a laptop webcam and tag displayed on a phone screen:

- **Position jitter:** ~7 cm (~3 inches) at 54 cm range
- **Phone GPS error (same session):** 50-60 meters off
- **AprilTag was ~700x more accurate than GPS**

## Scripts

| File | Description |
|------|-------------|
| `apriltag_gps_prototype.py` | Single tag prototype — generates 1 tag, opens webcam, shows live GPS |
| `apriltag_gps_4tags.py` | 4-tag cube version — generates N/E/S/W tags for a base station box |

## Setup

```bash
pip install opencv-python numpy pupil-apriltags moms-apriltag Pillow
```

## Usage

### Single Tag (quick test)

```bash
python apriltag_gps_prototype.py
```

### 4-Tag Cube (full base station)

```bash
python apriltag_gps_4tags.py
```

Both scripts will:
1. Generate the AprilTag image(s) in an `april_tags/` folder
2. Ask you to measure the printed/displayed tag size in cm
3. Open your webcam and show live GPS coordinates on screen
4. Press **Q** to quit

## Configuration

Edit the coordinates at the top of either script to set your base station location:

```python
BASE_LATITUDE  = 45.03244197593199    # Your location
BASE_LONGITUDE = -93.08111888039345   # Your location
```

## Tag Family

Uses **tag36h11** — a 6x6 grid with hamming distance 11. Most robust family with 587 unique IDs. Each tag in the family differs by at least 11 cells, making it nearly impossible to confuse one tag for another even with partial occlusion.

## 4-Tag Cube Layout

```
         Tag ID 0
         (NORTH)
        ┌────────┐
Tag ID 3│        │Tag ID 1
(WEST)  │  Cube  │(EAST)
        └────────┘
         Tag ID 2
         (SOUTH)
```

## Known Warning

```
Error, more than one new minima found.
```

This is harmless. When the camera views a flat tag nearly head-on, two 3D poses can produce the same 2D image. The library finds both solutions and picks the best one. It does not affect accuracy — our test showed stable ~7 cm jitter despite this warning on every frame.

## Requirements

- Python 3.8+
- Webcam
- A phone or printed paper to display the tag

## References

- [AprilTag 3](https://april.eecs.umich.edu/software/apriltag) — Olson, University of Michigan
- [pupil-apriltags](https://github.com/pupil-labs/apriltags) — Python bindings
- [Point-LIO](https://github.com/dfloreaa/point_lio_ros2) — Next phase: LiDAR-inertial odometry
