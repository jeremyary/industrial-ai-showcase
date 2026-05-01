# OpenUSD — Universal Scene Description

## What problem USD solves

If you have worked with Kubernetes manifests, you understand the value
of a declarative description format: you describe the desired state,
and the system reconciles reality to match. USD (Universal Scene
Description) serves the same role for 3D worlds.

Before USD, every 3D tool — Maya, Blender, 3ds Max, Houdini, CAD
applications — used its own file format. Moving data between tools
required lossy conversions. A lighting artist's work could not easily
compose with a layout artist's work without manual merge processes.
Scale, materials, coordinate systems, and animation data all needed
translation.

USD provides a single, interoperable scene description that multiple
tools can read and write. It supports non-destructive layered
composition, meaning different contributors (layout, lighting,
animation, physics) can work on the same scene simultaneously without
overwriting each other's work. For physical AI, USD is the format that
describes the digital twin — the 3D world where robots train, test, and
operate.

## Origin

USD was created at Pixar Animation Studios to manage the complexity of
feature film production pipelines where hundreds of artists contribute
to a single scene. Pixar open-sourced USD in 2016, and it has since
become the de facto standard for 3D interchange.

In 2023, Pixar, Adobe, Apple, Autodesk, and NVIDIA founded the
**Alliance for OpenUSD (AOUSD)** under the Linux Foundation to govern
the standard's development. General members now include Cesium, Epic
Games, IKEA, Meta, Unity, and others.

- [OpenUSD](https://openusd.org/)
- [Alliance for OpenUSD](https://aousd.org/)

## Core concepts

### Stage

A `UsdStage` is the composed view of a scene — the fully assembled
scenegraph that applications work with. You open a root layer file, and
USD's composition engine assembles the full stage from all referenced
layers.

Think of the stage as what `kubectl get` returns — the reconciled state
after all sources have been composed.

### Layer

A layer is a file (or in-memory buffer) containing scene description.
Layers stack like Photoshop layers: stronger layers override weaker
ones. A layer is the unit of persistence — what you save to disk.

Different teams contribute different layers: the layout team provides
object placement, the lighting team provides light configurations, the
physics team provides simulation properties. These layers compose
non-destructively.

### Prim (Primitive)

Prims are the fundamental elements of scene description. They live in a
namespace hierarchy, addressed by paths:

```
/World
/World/Warehouse
/World/Warehouse/Floor
/World/Warehouse/Racking
/World/Warehouse/Forklift
/World/Warehouse/Forklift/Body
/World/Warehouse/Forklift/ForkAssembly
```

A prim can represent geometry (mesh, sphere, cube), a camera, a light,
a transform group, a physics body, or an abstract organizational node.
Prims are classified by schemas that define their properties.

### Properties

Properties live on prims and come in two types:

- **Attributes**: Typed, time-varying data. Position, color, radius,
  joint angle — any value that describes the prim's state.
- **Relationships**: Pointers to other prims or properties. A material
  binding is a relationship from a mesh prim to a material prim.

### Schemas

Schemas define the interface of a prim — what properties it should
have and what they mean. Two types:

- **IsA schemas**: Define what a prim IS. `UsdGeomMesh` makes a prim
  a mesh with vertices, face indices, and normals. `UsdGeomCamera`
  makes it a camera with focal length and aperture.
- **API schemas**: Define capabilities a prim HAS. `PhysicsCollisionAPI`
  adds collision properties. `PhysicsMassAPI` adds mass. Multiple API
  schemas can be applied to one prim.

For Kubernetes engineers: schemas are like CRD definitions. An IsA
schema is like declaring `kind: Deployment`. An API schema is like
adding annotations or labels that enable specific controllers to act
on the resource.

## Composition arcs

Composition arcs are the operators that assemble complex scenes from
multiple files. This is USD's most powerful feature and the one that
takes the most effort to understand. The arcs are evaluated in a
defined strength order: **LIVRPS** (Local, Inherits, VariantSets,
References, Payloads, SubLayers).

### SubLayers

Stacks layers together, composing them top-to-bottom. The primary
mechanism for departmental overrides — a lighting layer on top of a
layout layer on top of base geometry. Opinions in stronger (earlier)
sublayers win.

```
root.usda
├── sublayer: lighting.usda     (strongest)
├── sublayer: animation.usda
└── sublayer: layout.usda       (weakest)
```

### References

The primary assembly mechanism. A prim in one layer points to a prim
in another layer, composing the target's subtree into the referencer.
This is how individual assets (a forklift, a pallet, a robot) are
assembled into a scene.

```usda
def Xform "Forklift" (
    references = @./assets/forklift.usd@</ForkliftRoot>
)
{
    # Local overrides compose on top of the referenced asset
    double3 xformOp:translate = (10.0, 5.0, 0.0)
}
```

### VariantSets

Bundle multiple variations of an asset in one package with a switchable
selector. A forklift asset might have variants for different load
capacities, colors, or attachment configurations. Downstream consumers
switch variants non-destructively.

```usda
def Xform "Forklift" (
    variants = {
        string loadCapacity = "2ton"
    }
    variantSets = "loadCapacity"
)
{
    variantSet "loadCapacity" = {
        "1ton" { ... }
        "2ton" { ... }
        "5ton" { ... }
    }
}
```

### Payloads

A "deferred reference" that can be selectively loaded or unloaded after
the stage is opened. This enables working with massive scenes — you
open a factory-scale digital twin but only load the section you are
currently working with. Payloads are the mechanism for managing memory
and load time in large environments.

### Inherits

Establishes a persistent base/derived relationship. All opinions applied
to the base propagate to the derived prim everywhere in the
composition. Used for class-based sharing — all lights of a type inherit
from a base configuration.

### Local opinions

Direct opinions on a prim in the current layer. These are the strongest
opinions and always win.

## File formats

| Extension | Format | Use case |
|-----------|--------|----------|
| `.usda` | ASCII text (UTF-8) | Human-readable, debugging, diffs, small files |
| `.usdc` | Binary "crate" | Production: faster loading, smaller files, memory-mapped |
| `.usd` | Generic (auto-detects content) | Used when the format may change |
| `.usdz` | Uncompressed zip archive | Single-file distribution (AR, web) |

The `usda` format is valuable for the same reason YAML is valuable in
Kubernetes — you can read it, diff it, and version-control it. The
`usdc` format is what you use in production for performance.

## USD for digital twins and physical AI

USD is the scene description layer that makes digital twins composable,
versionable, and interoperable:

- **Single source of truth**: The factory's 3D representation lives in
  USD. Isaac Sim loads it for simulation. Omniverse renders it for
  visualization. Analytics tools query it for spatial analysis.
- **Layered composition**: The base factory geometry comes from CAD
  conversion. Robot placements come from a separate layer. Physics
  properties come from another. Sensor configurations from another.
  Each can be updated independently.
- **Collaboration**: Multiple engineers work on the same scene
  simultaneously through Nucleus, each contributing to different layers.
- **Versioning**: USD files can be version-controlled in Git (especially
  `.usda` format). Scene history is commit history.

## Key terminology reference

| Term | Definition |
|------|-----------|
| **Stage** | The composed scenegraph — the final assembled scene |
| **Layer** | A file containing scene description; layers stack and compose |
| **Prim** | A node in the scene hierarchy; the fundamental element |
| **Schema** | A typed interface defining a prim's properties |
| **Composition arc** | An operator that assembles scenes from multiple sources |
| **LIVRPS** | The strength order: Local, Inherits, VariantSets, References, Payloads, SubLayers |
| **Payload** | A deferred reference; can be loaded/unloaded to manage memory |
| **Variant** | A switchable alternative within an asset |

## Further reading

- [OpenUSD Introduction](https://openusd.org/release/intro.html) —
  Pixar's official introduction to USD concepts.
- [OpenUSD Glossary](https://openusd.org/release/glossary.html) —
  Definitive terminology reference.
- [OpenUSD FAQ](https://openusd.org/release/usdfaq.html) — Answers
  to common questions about USD capabilities and limitations.
- [USD Tutorials](https://openusd.org/release/tut_usd_tutorials.html) —
  Hands-on tutorials for working with USD programmatically.
- [NVIDIA USD Documentation](https://docs.omniverse.nvidia.com/usd/latest/index.html) —
  USD documentation specific to the Omniverse ecosystem.
- [Alliance for OpenUSD](https://aousd.org/) — The governance body
  for the OpenUSD standard.
