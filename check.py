# /// script
# requires-python = "==3.12.*"
# dependencies = ["trimesh", "manifold3d", "numpy"]
# ///
"""Sanity checks for the exported meshes."""

from pathlib import Path

import numpy as np
import trimesh

OUT = Path(__file__).parent / "out"
LENSES = ["red", "yellow", "green"]

body = trimesh.load_mesh(OUT / "body.stl")
lenses = {c: trimesh.load_mesh(OUT / f"lens_{c}.stl") for c in LENSES}

for name, m in {"body": body, **lenses}.items():
    assert m.is_watertight, f"{name} is not watertight"

size = trimesh.util.concatenate([body, *lenses.values()]).extents
assert np.allclose(size, [24.0, 72.1, 7.3], atol=0.02), f"bad overall size {size}"

DOME = 1.5
dome_r = (9**2 + DOME**2) / (2 * DOME)
lens_volume = np.pi * 9**2 * 2 + np.pi * DOME**2 * (3 * dome_r - DOME) / 3
for c, lens in lenses.items():
    assert np.isclose(lens.volume, lens_volume, rtol=0.01), (
        f"{c} lens volume {lens.volume}"
    )
    overlap = trimesh.boolean.intersection([body, lens], engine="manifold")
    assert overlap.volume < 0.01, f"{c} lens overlaps body by {overlap.volume} mm3"

ys = [lenses[c].centroid[1] for c in LENSES]
assert ys == sorted(ys, reverse=True), "lenses must go red, yellow, green top to bottom"
assert (OUT / "traffic_light.3mf").stat().st_size > 0
print("OK")
