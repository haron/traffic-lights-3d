# /// script
# requires-python = "==3.12.*"
# dependencies = ["build123d>=0.9"]
# ///
"""Traffic-light keychain: black body + 3 in-place lenses for a 4-filament print.

X = width, Y = up, Z = thickness (back face on the bed at Z=0). Units: mm.
"""

from math import radians, sin
from pathlib import Path

from build123d import (
    Align,
    Box,
    Circle,
    Color,
    Cylinder,
    Ellipse,
    Mesher,
    Plane,
    Pos,
    Rectangle,
    RectangleRounded,
    Rot,
    Sphere,
    export_stl,
    extrude,
    fillet,
    make_hull,
)

W, H, T, CORNER_R = 24.0, 64.2, 4.0, 1.6
EYE_BASE, EYE_R, EYE_Y, HOLE_D, EYE_FILLET = 9.6, 4.0, H + 3.9, 3.0, 1.5
NICHE_D, FLOOR, LENS_T, LENS_DOME = 18.0, 1.0, 2.0, 1.5
VISOR_RI, VISOR_RO, VISOR_H, TAPER_DEG = 9.2, 10.8, 3.3, 15
LENSES = {"red": H - 12.0, "yellow": H - 33.0, "green": H - 54.0}
COLORS = {
    "body": (0.1, 0.1, 0.1),
    "red": (0.9, 0.2, 0.15),
    "yellow": (0.95, 0.75, 0.1),
    "green": (0.2, 0.75, 0.4),
}
OUT = Path(__file__).parent / "out"
BOTTOM = (Align.CENTER, Align.CENTER, Align.MIN)


def outline():
    body = Pos(0, H / 2) * RectangleRounded(W, H, CORNER_R)
    eye = make_hull(
        (Pos(0, EYE_Y) * Circle(EYE_R)).edges()
        + (Pos(0, H - 0.5) * Rectangle(EYE_BASE, 1)).edges()
    )
    face = body + eye
    joints = [
        v
        for v in face.vertices()
        if abs(v.Y - H) < 1e-6 and abs(abs(v.X) - EYE_BASE / 2) < 1e-6
    ]
    assert len(joints) == 2, joints
    return fillet(joints, EYE_FILLET) - Pos(0, EYE_Y) * Circle(HOLE_D / 2)


def visor(y):
    ring = Pos(0, y, T) * (
        Cylinder(VISOR_RO, VISOR_H, align=BOTTOM)
        - Cylinder(VISOR_RI, VISOR_H, align=BOTTOM)
    )
    upper = Pos(0, y + VISOR_RO, T) * Box(
        2 * VISOR_RO, 2 * VISOR_RO, VISOR_H, align=BOTTOM
    )
    # Ends rise as a quarter ellipse over the last TAPER_DEG: flat-topped box above, ellipse below.
    rise = (VISOR_RI + VISOR_RO) / 2 * sin(radians(TAPER_DEG))
    plane = Plane(origin=(-W, y + rise, T), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
    taper = extrude(plane * Ellipse(rise, VISOR_H), amount=2 * W)
    flat = Pos(0, y + rise + VISOR_RO, T) * Box(
        2 * VISOR_RO, 2 * VISOR_RO, VISOR_H, align=BOTTOM
    )
    return ring & upper & (taper + flat)


def build():
    body = extrude(outline(), amount=T)
    for y in LENSES.values():
        body = (
            body
            - Pos(0, y, FLOOR) * Cylinder(NICHE_D / 2, T - FLOOR, align=BOTTOM)
            + visor(y)
        )
    return {"body": body} | {c: lens(y) for c, y in LENSES.items()}


def lens(y):
    # Disc with a spherical cap LENS_DOME tall. The sphere is turned so its poles sit sideways,
    # away from the crown: a pole on top meshes into a degenerate sliver.
    a, top = NICHE_D / 2, FLOOR + LENS_T
    r = (a**2 + LENS_DOME**2) / (2 * LENS_DOME)
    sphere = Pos(0, y, top + LENS_DOME - r) * Rot(90, 0, 0) * Sphere(r)
    blank = Pos(0, y, FLOOR) * Cylinder(a, LENS_T + LENS_DOME, align=BOTTOM)
    return blank & (sphere + Pos(0, y, FLOOR) * Cylinder(a, LENS_T, align=BOTTOM))


def main():
    OUT.mkdir(exist_ok=True)
    mesher = Mesher()
    for name, part in build().items():
        assert part.is_valid, name
        stem = name if name == "body" else f"lens_{name}"
        part.label, part.color = stem, Color(*COLORS[name])
        export_stl(part, OUT / f"{stem}.stl", tolerance=0.005, angular_tolerance=0.1)
        mesher.add_shape(part, linear_deflection=0.005, angular_deflection=0.1)
    # Mesher adds one build item per shape; regroup them into a single multi-part object so slicers load it as one piece.
    model, identity = mesher.model, mesher.wrapper.GetIdentityTransform()
    items = model.GetBuildItems()
    while items.MoveNext():
        model.RemoveBuildItem(items.GetCurrent())
    assembly = model.AddComponentsObject()
    assembly.SetName("traffic_light")
    for mesh in mesher.meshes:
        assembly.AddComponent(mesh, identity)
    model.AddBuildItem(assembly, identity)
    mesher.write(OUT / "traffic_light.3mf")


if __name__ == "__main__":
    main()
