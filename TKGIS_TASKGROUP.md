# tkgis Phase 0–7 — A Python Tkinter GIS Workbench

> **Generated from**: BLACK.md agentic principals, GRDL library analysis (v0.4.0), grdl-runtime execution framework analysis (v0.1.1), QGIS/ArcPro/Orange Data Mining feature survey, Google Earth UX study
> **Baseline**: Empty repository (LICENSE, .gitignore only). 0 tests, 0 LOC. GRDL v0.4.0, grdl-runtime v0.1.1 as upstream dependencies.
> **Execution model**: 8 phases (0–7) with parallel-serial execution. Upstream Extensions → Foundation → Map Engine → Data I/O → Tools & Processing → Visual Workflow Builder → Analysis & Visualization → Integration & Polish.
> **Convention**: Each task group is a self-contained agentic prompt. Feed the group text + `CLAUDE.md` to the agent. Groups within the same phase may execute in parallel.

---

## Execution Topology

```
PHASE 0 (Parallel):     [TG17: grdl Vector Extensions]     [TG18: grdl-runtime Workflow Extensions]
                              │                                      │
                              └──────────────┬───────────────────────┘
                                             ▼
PHASE 1 (Parallel):     [TG1: App Shell]     [TG2: Plugin System]     [TG3: Data Models]
                              │                      │                       │
                              └──────────┬───────────┘───────────────────────┘
                                         ▼
PHASE 2 (Parallel):     [TG4: Map Canvas]    [TG5: Layer Manager]    [TG6: CRS Engine]
                              │                      │                       │
                              └──────────┬───────────┘───────────────────────┘
                                         ▼
PHASE 3 (Parallel):     [TG7: Vector I/O]    [TG8: Raster I/O]     [TG9: Temporal Data]
                              │                      │                       │
                              └──────────┬───────────┘───────────────────────┘
                                         ▼
PHASE 4 (Parallel):     [TG10: Nav Tools]    [TG11: Processing]     [TG12: Spatial Query]
                              │                      │                       │
                              └──────────┬───────────┘───────────────────────┘
                                         ▼
PHASE 5 (Sequential):       [TG19: Visual DAG Workflow Builder]
                                         │
                                         ▼
PHASE 6 (Parallel):     [TG13: Charts]       [TG14: Spatiotemporal]  [TG15: Attribute Table]
                              │                      │                       │
                              └──────────┬───────────┘───────────────────────┘
                                         ▼
PHASE 7 (Sequential):       [TG16: Integration, Testing & Polish]
```

**Phase 0**: Upstream extensions. Before tkgis development begins, GRDL and grdl-runtime must be extended to support generic vector data operations and multi-type DAG workflows. TG17 adds `FeatureSet` (generic vector container), spatial operators, and vector I/O to GRDL. TG18 extends grdl-runtime's workflow engine with data type declarations, vector-aware dispatch, and multi-output step support. These are PRs to the GRDX repositories, not tkgis code.

**Phase 1**: Foundation. Application shell, plugin architecture, and core data models. No file overlap — TG1 owns the GUI shell, TG2 owns the plugin system, TG3 owns domain models. All three are independent.

**Phase 2**: Map engine. The tile-based canvas (TG4), layer management UI and logic (TG5), and coordinate reference system engine (TG6). TG4 consumes data models from TG3. TG5 consumes both TG3 models and TG1's panel system. TG6 is self-contained but consumed by TG4 and TG5.

**Phase 3**: Data ingestion. Vector I/O via geopandas (TG7), raster I/O via GRDL (TG8), and temporal data management (TG9). Each produces layer-compatible data objects consumed by TG5's layer system. TG8 is the heaviest — it integrates GRDL readers, geolocation, and tiled rendering into the map canvas.

**Phase 4**: Interactive tools. Navigation and measurement (TG10), image processing integration with grdl-runtime (TG11), and spatial query/selection (TG12). These consume the map canvas, layer system, and I/O layers.

**Phase 5**: Visual DAG Workflow Builder (TG19). The flagship model-driven development feature — a drag-and-drop node graph editor for composing raster, vector, and mixed-type workflows. Nodes come from the grdl-runtime processor catalog, grdl spatial operators (from Phase 0), geopandas vector operations, and I/O readers/writers. Workflows are saved as grdl-runtime `WorkflowDefinition` YAML for execution on AuraGrid. Sequential — requires all processing infrastructure from Phase 4.

**Phase 6**: Analysis and visualization. Charting widgets (TG13), spatiotemporal analysis (TG14), and the attribute table/data inspector (TG15). These are the "power user" features that differentiate tkgis from a simple viewer. Runs after the workflow builder so charts can integrate as workflow output viewers.

**Phase 7**: Integration testing, cross-cutting polish, plugin examples, and documentation. Sequential — requires all prior phases complete.

---

## Shared File Conflict Map

### tkgis Repository
| File | Modified By | Strategy |
|------|-------------|----------|
| `src/tkgis/__init__.py` | TG1, TG3 | Append-only (TG1 creates, TG3 adds model exports) |
| `src/tkgis/app.py` | TG1, TG5, TG10, TG11, TG13, TG15, TG19 | Delimited sections; TG16 merges |
| `pyproject.toml` | TG1, TG7, TG8, TG13 | Append-only (each adds dependencies to their section) |
| `src/tkgis/models/__init__.py` | TG3, TG9 | Append-only |
| `src/tkgis/panels/__init__.py` | TG5, TG10, TG13, TG15, TG19 | Append-only |
| `tests/conftest.py` | TG3, TG7, TG8 | Append-only (each adds fixtures) |
| `CLAUDE.md` | TG1 only | Direct modification (TG1 creates) |

### GRDL Repository (Phase 0 — upstream PRs)
| File | Modified By | Strategy |
|------|-------------|----------|
| `grdl/image_processing/detection/models.py` | TG17 only | Direct modification (extends existing) |
| `grdl/image_processing/__init__.py` | TG17 only | Append-only (add new exports) |
| `grdl/vocabulary.py` | TG17 only | Append-only (add new enums) |

### grdl-runtime Repository (Phase 0 — upstream PRs)
| File | Modified By | Strategy |
|------|-------------|----------|
| `grdl_rt/execution/dispatch.py` | TG18 only | Direct modification (extend dispatch) |
| `grdl_rt/execution/workflow.py` | TG18 only | Direct modification (extend models) |
| `grdl_rt/execution/dag_executor.py` | TG18 only | Direct modification (extend executor) |
| `grdl_rt/execution/__init__.py` | TG18 only | Append-only (add new exports) |

---

## Task Group 17: GRDL Vector Data Extensions (Upstream — grdx/grdl)

### Agent Profile

You are a **Python geospatial data engineer** specializing in spatial data models, vector operations, and sensor-agnostic feature representations. You are extending **GRDL** (the GEOINT Rapid Development Library) to support generic vector data operations alongside its existing raster and detection capabilities. Read `CLAUDE.md` before starting — it contains all project conventions, constraints, and patterns you must follow.

### Context

GRDL currently has a `DetectionSet` model (in `grdl.image_processing.detection.models`) that represents sparse geo-registered features output by detector algorithms. `DetectionSet` works well for its purpose — it has geometry (shapely), properties, confidence, and GeoJSON export. However, it is tightly scoped to "detection output" and lacks the generality needed for a visual workflow builder where vector data flows between arbitrary nodes (spatial joins, buffers, filters, aggregations).

**The gap**: There is no generic vector feature container in GRDL that can represent:
- Buffered geometries from spatial operations
- Results of spatial joins, intersections, or unions
- Feature collections imported from GIS files (shapefiles, GeoJSON)
- Tabular data with geometry columns from analysis operations
- Vector outputs from non-detection processors

GRDL also lacks spatial operation processors that follow the established `ImageProcessor` pattern with `@processor_version`, `@processor_tags`, and tunable parameters.

Additionally, the `ExecutionPhase.VECTOR_PROCESSING` enum value exists in `grdl.vocabulary` but has no corresponding processors.

**What already exists** (do NOT duplicate):
- `Detection` / `DetectionSet` — keep these as-is for detector outputs
- `ImageProcessor` / `ImageTransform` / `ImageDetector` ABCs in `grdl.image_processing.base`
- `@processor_version`, `@processor_tags`, `Range`, `Options`, `Desc` parameter annotations
- `Fields` / `FieldDefinition` in `grdl.image_processing.detection.fields` — 100+ standardized field names
- `WorkflowOperator` in grdl-runtime for DAG structural operations

**Design principle**: `FeatureSet` should be to vector data what `np.ndarray` is to raster data — the universal container type that flows through workflows. Just as every `ImageTransform.apply()` takes and returns an ndarray, every `VectorProcessor.process()` should take and return a `FeatureSet`.

### Files to Read Before Starting

1. `grdl/image_processing/detection/models.py` — Detection, DetectionSet (pattern to follow)
2. `grdl/image_processing/detection/base.py` — ImageDetector ABC
3. `grdl/image_processing/base.py` — ImageProcessor, ImageTransform ABCs, execute() protocol
4. `grdl/image_processing/detection/fields.py` — Fields, FieldDefinition (reuse for FeatureSet)
5. `grdl/vocabulary.py` — ImageModality, ProcessorCategory, ExecutionPhase enums
6. `grdl/image_processing/versioning.py` — @processor_version, @processor_tags
7. `grdl/image_processing/params.py` — Range, Options, Desc parameter annotations
8. `grdl/IO/base.py` — ImageReader ABC (pattern for VectorReader)
9. `CLAUDE.md` — Project conventions

### Constraints

- Do **NOT** break existing `DetectionSet` API — it is used by CFAR detectors and CSI processor
- Do **NOT** add geopandas as a hard dependency — GRDL uses optional deps; shapely is already required
- `FeatureSet` must be convertible to/from `DetectionSet` (bridge methods)
- `FeatureSet` must be convertible to/from GeoJSON (dict, not file)
- All vector processors must follow the same `@processor_version` / `@processor_tags` pattern as raster processors
- New processors must use `ExecutionPhase.VECTOR_PROCESSING` in their tags
- Maintain GRDL's scalar/array unification pattern where applicable
- All new code must have tests following existing test patterns

### Tasks

#### T17.1: Create the FeatureSet Data Model

```python
# grdl/vector/models.py
from dataclasses import dataclass, field
from typing import Any
import numpy as np
from shapely.geometry.base import BaseGeometry

@dataclass
class Feature:
    """A single geospatial feature with geometry and properties."""
    geometry: BaseGeometry                    # shapely geometry (Point, Polygon, etc.)
    properties: dict[str, Any] = field(default_factory=dict)
    id: str | None = None

    def to_geojson(self) -> dict: ...

    @classmethod
    def from_geojson(cls, geojson: dict) -> 'Feature': ...

@dataclass
class FieldSchema:
    """Schema for a FeatureSet's property fields."""
    name: str
    dtype: str           # "str", "int", "float", "bool", "datetime"
    description: str = ""
    nullable: bool = True

@dataclass
class FeatureSet:
    """Generic container for a collection of geospatial features.

    This is the vector equivalent of np.ndarray — the universal container
    that flows through vector processing workflows.
    """
    features: list[Feature] = field(default_factory=list)
    crs: str = "EPSG:4326"
    schema: list[FieldSchema] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # --- Collection operations ---
    @property
    def count(self) -> int: ...

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """(minx, miny, maxx, maxy)"""
        ...

    @property
    def geometry_types(self) -> set[str]: ...

    def get_geometries(self) -> list[BaseGeometry]: ...

    def get_property_array(self, name: str) -> np.ndarray:
        """Extract a property column as a numpy array."""
        ...

    # --- Filtering ---
    def filter_by_bbox(self, minx, miny, maxx, maxy) -> 'FeatureSet': ...
    def filter_by_property(self, name: str, predicate) -> 'FeatureSet': ...
    def filter_by_geometry(self, geometry: BaseGeometry, predicate: str = "intersects") -> 'FeatureSet': ...

    # --- Serialization ---
    def to_geojson(self) -> dict:
        """Export as GeoJSON FeatureCollection dict."""
        ...

    @classmethod
    def from_geojson(cls, geojson: dict, crs: str = "EPSG:4326") -> 'FeatureSet': ...

    # --- Bridge to DetectionSet ---
    @classmethod
    def from_detection_set(cls, detection_set: 'DetectionSet') -> 'FeatureSet':
        """Convert DetectionSet to FeatureSet (lossless)."""
        ...

    def to_detection_set(self, detector_name: str = "unknown",
                         detector_version: str = "0.0.0") -> 'DetectionSet':
        """Convert FeatureSet to DetectionSet (adds required detector metadata)."""
        ...

    # --- Bridge to geopandas (optional, lazy import) ---
    def to_geodataframe(self) -> 'gpd.GeoDataFrame':
        """Convert to geopandas GeoDataFrame (requires geopandas)."""
        ...

    @classmethod
    def from_geodataframe(cls, gdf: 'gpd.GeoDataFrame') -> 'FeatureSet': ...
```

#### T17.2: Create the VectorProcessor ABC

```python
# grdl/vector/base.py
from grdl.image_processing.base import ImageProcessor

class VectorProcessor(ImageProcessor):
    """Base class for processors that operate on FeatureSet data.

    Follows the same patterns as ImageTransform but for vector data.
    Subclasses implement process() instead of apply().
    """

    @abstractmethod
    def process(self, features: FeatureSet, **kwargs) -> FeatureSet:
        """Process a FeatureSet and return a new FeatureSet."""
        ...

    def execute(self, metadata, source, **kwargs):
        """ImageProcessor protocol: dispatch to process()."""
        if isinstance(source, FeatureSet):
            result = self.process(source, **kwargs)
            return result, metadata
        elif isinstance(source, np.ndarray):
            raise TypeError(
                f"{self.__class__.__name__} is a VectorProcessor and requires "
                f"FeatureSet input, got ndarray. Use a raster-to-vector conversion first."
            )
        else:
            raise TypeError(f"Unsupported source type: {type(source)}")
```

#### T17.3: Implement Core Spatial Operators

```python
# grdl/vector/spatial.py
@processor_version('1.0.0')
@processor_tags(category=PC.ANALYZE, description='Buffer features by distance')
class BufferOperator(VectorProcessor):
    distance: Annotated[float, Range(min=0.0), Desc('Buffer distance')] = 100.0
    resolution: Annotated[int, Range(min=1, max=128), Desc('Circle segments')] = 16

    def process(self, features: FeatureSet, **kwargs) -> FeatureSet: ...

@processor_version('1.0.0')
@processor_tags(category=PC.ANALYZE, description='Spatial intersection of two FeatureSets')
class IntersectionOperator(VectorProcessor):
    def process(self, features: FeatureSet, **kwargs) -> FeatureSet:
        """kwargs['overlay'] contains the second FeatureSet."""
        ...

@processor_version('1.0.0')
@processor_tags(category=PC.ANALYZE, description='Spatial union of two FeatureSets')
class UnionOperator(VectorProcessor):
    def process(self, features: FeatureSet, **kwargs) -> FeatureSet: ...

@processor_version('1.0.0')
@processor_tags(category=PC.ANALYZE, description='Dissolve features by property')
class DissolveOperator(VectorProcessor):
    by: Annotated[str, Desc('Property name to dissolve by')] = ""

    def process(self, features: FeatureSet, **kwargs) -> FeatureSet: ...

@processor_version('1.0.0')
@processor_tags(category=PC.ANALYZE, description='Spatial join between FeatureSets')
class SpatialJoinOperator(VectorProcessor):
    predicate: Annotated[str, Options('intersects', 'contains', 'within'), Desc('Join predicate')] = 'intersects'
    how: Annotated[str, Options('inner', 'left'), Desc('Join type')] = 'inner'

    def process(self, features: FeatureSet, **kwargs) -> FeatureSet: ...

@processor_version('1.0.0')
@processor_tags(category=PC.ANALYZE, description='Clip features by a boundary geometry')
class ClipOperator(VectorProcessor):
    def process(self, features: FeatureSet, **kwargs) -> FeatureSet:
        """kwargs['clip_geometry'] is a shapely geometry or FeatureSet."""
        ...

@processor_version('1.0.0')
@processor_tags(category=PC.ANALYZE, description='Centroid of each feature geometry')
class CentroidOperator(VectorProcessor):
    def process(self, features: FeatureSet, **kwargs) -> FeatureSet: ...

@processor_version('1.0.0')
@processor_tags(category=PC.ANALYZE, description='Convex hull of each feature geometry')
class ConvexHullOperator(VectorProcessor):
    def process(self, features: FeatureSet, **kwargs) -> FeatureSet: ...
```

#### T17.4: Implement Raster-to-Vector Conversion Processors

```python
# grdl/vector/conversion.py
@processor_version('1.0.0')
@processor_tags(category=PC.ANALYZE, description='Convert raster pixels above threshold to point features')
class RasterToPoints(ImageProcessor):
    """Raster → FeatureSet. Extracts pixels matching criteria as Point features."""
    threshold: Annotated[float, Desc('Minimum value to extract')] = 0.0
    band: Annotated[int, Range(min=0), Desc('Band index')] = 0
    sample_step: Annotated[int, Range(min=1), Desc('Subsample every N pixels')] = 1

    def execute(self, metadata, source: np.ndarray, **kwargs):
        """Returns (FeatureSet, metadata) — note: output is FeatureSet, not ndarray."""
        ...

@processor_version('1.0.0')
@processor_tags(category=PC.ANALYZE, description='Rasterize vector features to a pixel mask')
class Rasterize(ImageProcessor):
    """FeatureSet → ndarray. Burns vector geometries into a raster grid."""
    value_field: Annotated[str | None, Desc('Property to burn, or None for binary mask')] = None
    fill_value: Annotated[float, Desc('Background value')] = 0.0
    burn_value: Annotated[float, Desc('Foreground value (if no value_field)')] = 1.0

    def execute(self, metadata, source, **kwargs):
        """source is FeatureSet; returns (ndarray, metadata)."""
        ...
```

#### T17.5: Implement Vector I/O

```python
# grdl/vector/io.py
class VectorReader:
    """Reads vector data files into FeatureSet objects."""

    @staticmethod
    def read(path: str | Path, crs: str | None = None) -> FeatureSet:
        """Read GeoJSON, Shapefile, GeoPackage, KML into FeatureSet.
        Uses geopandas if available, falls back to pure shapely+json for GeoJSON.
        """
        ...

    @staticmethod
    def can_read(path: str | Path) -> bool:
        """Check if path is a supported vector format."""
        ...

class VectorWriter:
    """Writes FeatureSet objects to vector data files."""

    @staticmethod
    def write(features: FeatureSet, path: str | Path,
              driver: str | None = None) -> None:
        """Write to GeoJSON (native) or Shapefile/GPKG (requires geopandas)."""
        ...
```

GeoJSON I/O should work without geopandas (pure json + shapely). Other formats use geopandas as optional dependency.

#### T17.6: Add Vector Vocabulary

```python
# Add to grdl/vocabulary.py

class VectorOperation(str, Enum):
    """Operations available for vector processing workflows."""
    BUFFER = "buffer"
    INTERSECTION = "intersection"
    UNION = "union"
    DIFFERENCE = "difference"
    DISSOLVE = "dissolve"
    SPATIAL_JOIN = "spatial_join"
    CLIP = "clip"
    CENTROID = "centroid"
    CONVEX_HULL = "convex_hull"
    SIMPLIFY = "simplify"
    RASTERIZE = "rasterize"
    VECTORIZE = "vectorize"

class DataType(str, Enum):
    """Data types that flow through workflows."""
    RASTER = "raster"           # np.ndarray
    FEATURE_SET = "feature_set" # FeatureSet
    DETECTION_SET = "detection_set"  # DetectionSet
    METADATA = "metadata"       # dict or ImageMetadata
```

Add `DataType` to `@processor_tags` so processors declare their input/output types:

```python
# Extend @processor_tags signature:
@processor_tags(
    modalities=[IM.SAR],
    category=PC.ANALYZE,
    description='Buffer features',
    input_type=DataType.FEATURE_SET,    # NEW
    output_type=DataType.FEATURE_SET,   # NEW
)
```

#### T17.7: Write Tests

```python
# tests/test_vector_models.py
def test_feature_set_creation(): ...
def test_feature_set_filter_bbox(): ...
def test_feature_set_filter_property(): ...
def test_feature_set_geojson_roundtrip(): ...
def test_feature_set_to_from_detection_set(): ...
def test_feature_set_to_from_geodataframe(): ...

# tests/test_vector_spatial.py
def test_buffer_operator(): ...
def test_intersection_operator(): ...
def test_union_operator(): ...
def test_dissolve_operator(): ...
def test_spatial_join(): ...
def test_clip_operator(): ...

# tests/test_vector_conversion.py
def test_raster_to_points(): ...
def test_rasterize(): ...

# tests/test_vector_io.py
def test_read_geojson(): ...
def test_write_geojson(): ...
def test_vector_reader_can_read(): ...
```

### Success Criteria

- [ ] `FeatureSet` holds heterogeneous geometry features with typed properties
- [ ] `FeatureSet.to_geojson()` / `from_geojson()` round-trips losslessly
- [ ] `FeatureSet.from_detection_set()` / `to_detection_set()` bridges work
- [ ] `FeatureSet.to_geodataframe()` / `from_geodataframe()` works (with geopandas installed)
- [ ] All spatial operators (buffer, intersection, union, dissolve, join, clip) produce correct results
- [ ] `RasterToPoints` converts raster data to point FeatureSet
- [ ] `Rasterize` converts FeatureSet to binary mask ndarray
- [ ] All processors use `@processor_version` / `@processor_tags` with `DataType` annotations
- [ ] VectorReader reads GeoJSON without geopandas
- [ ] Existing DetectionSet tests still pass — no regressions
- [ ] `pytest tests/ -p no:napari -x -q` — 0 failures

### Produces / Consumes

- **Produces**: `FeatureSet`, `VectorProcessor`, spatial operators, `DataType` enum, vector I/O → consumed by TG18 (runtime extensions), TG7 (tkgis vector I/O), TG12 (spatial queries), TG19 (workflow builder)
- **Consumes**: Existing `ImageProcessor` pattern, `DetectionSet`, `@processor_tags` from GRDL

### Dependencies

| Package | Version | Scope | License | Justification |
|---------|---------|-------|---------|---------------|
| shapely | >=2.0.0 | runtime | BSD-3-Clause | Already a GRDL dependency — geometry operations |

**No new dependencies** — shapely is already required. geopandas remains optional.

---

## Task Group 18: grdl-runtime Workflow Extensions (Upstream — grdx/grdl-runtime)

### Agent Profile

You are a **Python systems architect** specializing in workflow engines, type-safe dispatch, and DAG execution. You are extending **grdl-runtime** to support multi-type workflows where steps can consume and produce different data types (raster arrays, FeatureSets, DetectionSets). Read `CLAUDE.md` before starting — it contains all project conventions, constraints, and patterns you must follow.

### Context

grdl-runtime's DAG executor already supports arbitrary data types flowing between steps — `results[step_id]` can hold any object, and `execute_processor()` returns `tuple[Any, ImageMetadata]`. However, there is no **type validation** or **type declaration** in the workflow model. The visual workflow builder (TG19) needs to:

1. Know what data type each processor accepts and produces (to validate drag-and-drop connections)
2. Serialize multi-type workflows to YAML
3. Execute workflows where some steps produce `FeatureSet` and others produce `np.ndarray`
4. Display type-appropriate previews and properties for each node

**What already works**:
- `WorkflowDefinition` with DAG steps and YAML serialization
- `DAGExecutor` with fan-in, topological sort, consumer-count eviction
- `execute_processor()` polymorphic dispatch (GRDL protocol, legacy, callable)
- `WorkflowOperator` for structural DAG operations
- `DetectionAggregator` for detection fan-in
- `ProcessingStep.phase` annotation from `ExecutionPhase` enum

**What needs to be added**:
- Data type declarations on `ProcessingStep` (input_type, output_type)
- Type compatibility validation during DAG construction
- Dispatch awareness for `FeatureSet` inputs (don't try GPU transfer on vectors)
- Workflow graph introspection API for the visual builder
- Multi-output step support (a step that produces both raster and vector)

### Files to Read Before Starting

1. `grdl_rt/execution/workflow.py` — ProcessingStep, WorkflowDefinition
2. `grdl_rt/execution/dag_executor.py` — DAGExecutor, run_dag_ready_dispatch
3. `grdl_rt/execution/dispatch.py` — execute_processor, supports_gpu_transfer
4. `grdl_rt/execution/builder.py` — Workflow fluent builder
5. `grdl_rt/execution/operators.py` — WorkflowOperator, DetectionAggregator
6. `grdl_rt/execution/dsl.py` — DslCompiler, YAML schema
7. `grdl_rt/execution/validation.py` — validate_workflow
8. `grdl_rt/catalog/models.py` — Artifact model
9. `grdl/vector/models.py` — FeatureSet (from TG17)
10. `grdl/vocabulary.py` — DataType enum (from TG17)
11. `CLAUDE.md` — Project conventions

### Constraints

- Do **NOT** break existing linear or DAG workflow execution — all existing tests must pass
- Do **NOT** add geopandas as a dependency — grdl-runtime depends on grdl, not geopandas
- `DataType` annotations must be optional — existing processors without type annotations still work
- GPU dispatch must skip non-array data types (FeatureSet, DetectionSet) — no CuPy transfer
- YAML schema version should bump to 3.0 with backward compatibility for 2.0

### Tasks

#### T18.1: Add Data Type Declarations to ProcessingStep

```python
# Extend grdl_rt/execution/workflow.py

class ProcessingStep:
    # ... existing fields ...
    input_type: str | None = None     # "raster", "feature_set", "detection_set", None (any)
    output_type: str | None = None    # "raster", "feature_set", "detection_set", None (inferred)

    # For multi-output steps:
    output_ports: dict[str, str] | None = None  # {"raster": "raster", "detections": "detection_set"}
```

Update `WorkflowDefinition.to_dict()` / `from_dict()` to serialize these fields. Schema version → 3.0. When loading v2.0 YAML, treat missing type fields as `None` (backward compatible).

#### T18.2: Add Type Validation to DAG Construction

```python
# Extend grdl_rt/execution/validation.py

def validate_type_compatibility(workflow: WorkflowDefinition) -> list[ValidationError]:
    """Check that connected steps have compatible data types.

    Rules:
    - If both producer.output_type and consumer.input_type are declared,
      they must match (or one must be None = "any")
    - DetectionSet is compatible with FeatureSet (via bridge)
    - Raster is NOT compatible with FeatureSet (requires explicit conversion node)
    - Fan-in steps that receive multiple types must declare input_type=None or "any"
    """
    ...
```

Integrate this into `validate_workflow()`.

#### T18.3: Update Dispatch for FeatureSet Awareness

```python
# Extend grdl_rt/execution/dispatch.py

def supports_gpu_transfer(processor) -> bool:
    """Amended: return False for VectorProcessor subclasses."""
    ...

def execute_processor(processor, metadata, source, **kwargs):
    """Amended: handle FeatureSet inputs.

    If source is a FeatureSet and processor is a VectorProcessor,
    dispatch via processor.execute(metadata, source, **kwargs).

    If source is a FeatureSet and processor is an ImageTransform,
    raise TypeError with clear message about needing a conversion node.
    """
    ...
```

#### T18.4: Add Workflow Graph Introspection API

The visual workflow builder needs to query the workflow graph for rendering:

```python
# grdl_rt/execution/graph.py (NEW)

@dataclass
class NodeInfo:
    """Information about a workflow node for visual rendering."""
    step_id: str
    processor_name: str
    processor_version: str | None
    display_name: str
    category: str | None
    input_type: str | None
    output_type: str | None
    output_ports: dict[str, str] | None
    params: dict[str, Any]
    param_specs: dict[str, dict]       # From processor's __param_specs__
    depends_on: list[str]
    phase: str | None
    position: tuple[float, float] | None  # GUI x,y for layout persistence

@dataclass
class EdgeInfo:
    """Information about a connection between nodes."""
    source_id: str
    source_port: str | None     # None = default output, or port name
    target_id: str
    target_port: str | None     # None = default input, or "overlay", "clip_geometry"
    data_type: str | None

class WorkflowGraph:
    """Introspection API for the visual workflow builder."""

    def __init__(self, workflow: WorkflowDefinition, catalog=None):
        ...

    def get_nodes(self) -> list[NodeInfo]: ...
    def get_edges(self) -> list[EdgeInfo]: ...
    def get_node(self, step_id: str) -> NodeInfo | None: ...

    def add_node(self, processor_name: str, params: dict = None,
                 position: tuple[float, float] | None = None) -> str:
        """Add a node. Returns generated step_id."""
        ...

    def remove_node(self, step_id: str) -> None: ...

    def connect(self, source_id: str, target_id: str,
                source_port: str | None = None,
                target_port: str | None = None) -> None:
        """Add an edge. Validates type compatibility."""
        ...

    def disconnect(self, source_id: str, target_id: str) -> None: ...

    def validate(self) -> list[ValidationError]:
        """Full validation: types, cycles, missing dependencies."""
        ...

    def to_workflow_definition(self) -> WorkflowDefinition:
        """Export to serializable WorkflowDefinition."""
        ...

    def topological_levels(self) -> list[list[str]]:
        """Return step IDs grouped by execution level (for visual layout)."""
        ...

    @classmethod
    def from_workflow_definition(cls, workflow: WorkflowDefinition,
                                  catalog=None) -> 'WorkflowGraph': ...
```

#### T18.5: Extend the Artifact Catalog for Type Metadata

```python
# Extend grdl_rt/catalog/models.py

class Artifact:
    # ... existing fields ...
    input_type: str | None = None     # "raster", "feature_set", "detection_set"
    output_type: str | None = None
    output_ports: dict[str, str] | None = None
    kwarg_inputs: dict[str, str] | None = None  # {"overlay": "feature_set", "mask": "raster"}
```

Update `discover_processors()` to populate type metadata from `@processor_tags` `input_type`/`output_type` fields (from TG17).

#### T18.6: Add Generic Aggregator Operator

```python
# Extend grdl_rt/execution/operators.py

class FeatureSetAggregator(WorkflowOperator):
    """Fan-in operator that merges multiple FeatureSets."""

    strategy: Annotated[str, Options('union', 'intersection'), Desc('Merge strategy')] = 'union'

    def operate(self, metadata, source, **kwargs):
        """source is dict[step_id: FeatureSet]. Merge per strategy."""
        ...
```

#### T18.7: Update YAML Schema to v3.0

```yaml
# Schema 3.0 additions:
schema_version: "3.0"
steps:
  - processor: BufferOperator
    version: "1.0.0"
    id: buffer_step
    input_type: feature_set          # NEW
    output_type: feature_set         # NEW
    params:
      distance: 100.0
    depends_on: [read_vector]
    position: [200, 300]             # NEW — GUI layout persistence
  - processor: SomeMultiOutput
    id: multi_step
    output_ports:                    # NEW — multi-output
      raster: raster
      detections: detection_set
    depends_on: [input_step]
```

Ensure `DslCompiler` handles v3.0 YAML and generates it from `WorkflowGraph`.

#### T18.8: Write Tests

```python
# tests/test_type_validation.py
def test_compatible_types_raster_to_raster(): ...
def test_compatible_types_feature_to_feature(): ...
def test_incompatible_raster_to_vector_raises(): ...
def test_detection_compatible_with_feature(): ...
def test_none_type_accepts_anything(): ...
def test_v2_yaml_backward_compatible(): ...

# tests/test_workflow_graph.py
def test_graph_add_remove_nodes(): ...
def test_graph_connect_validates_types(): ...
def test_graph_topological_levels(): ...
def test_graph_to_workflow_definition(): ...
def test_graph_roundtrip_yaml(): ...

# tests/test_feature_set_dispatch.py
def test_dispatch_vector_processor_with_feature_set(): ...
def test_dispatch_image_transform_with_feature_set_raises(): ...
def test_gpu_transfer_skipped_for_feature_set(): ...

# tests/test_feature_set_aggregator.py
def test_union_aggregator(): ...
def test_intersection_aggregator(): ...
```

### Success Criteria

- [ ] `ProcessingStep` serializes `input_type`/`output_type` to YAML v3.0
- [ ] v2.0 YAML files load without errors (backward compatible)
- [ ] Type validation catches incompatible connections (raster → vector processor)
- [ ] `DetectionSet` is accepted where `FeatureSet` is expected (bridge)
- [ ] GPU dispatch correctly skips FeatureSet data
- [ ] `WorkflowGraph` API supports add/remove/connect/disconnect/validate
- [ ] `WorkflowGraph.to_workflow_definition()` produces valid YAML
- [ ] `FeatureSetAggregator` merges multiple FeatureSets
- [ ] Artifact catalog includes type metadata from processor tags
- [ ] All existing grdl-runtime tests pass — 0 regressions
- [ ] `pytest tests/ -x -q` — 0 failures

### Produces / Consumes

- **Produces**: WorkflowGraph API, type-annotated ProcessingStep, FeatureSetAggregator, v3.0 YAML schema → consumed by TG19 (visual builder), TG11 (processing integration)
- **Consumes**: FeatureSet, VectorProcessor, DataType from TG17; existing grdl-runtime infrastructure

### Dependencies

**No new dependencies** — uses existing grdl and grdl-runtime deps.

---

## Task Group 1: Application Shell & Theme (GUI Foundation)

### Agent Profile

You are a **Python GUI developer** specializing in modern tkinter applications with customtkinter and ttkbootstrap. You are building **tkgis**, a desktop GIS application that rivals QGIS and ArcPro in capability while matching Google Earth's simplicity. Read `CLAUDE.md` before starting — it contains all project conventions, constraints, and patterns you must follow.

### Context

tkgis is a greenfield Python GIS application. The repository currently contains only a LICENSE and .gitignore. This task group establishes the application shell — the main window, menu system, toolbar, status bar, dockable panel framework, and theming infrastructure. Every subsequent task group builds into this shell.

The application targets Windows 11 primarily but must remain cross-platform. The UI must feel modern — not the default Tk gray. We use **customtkinter** for the overall theme engine (dark/light mode, rounded widgets, modern color palette) and **ttkbootstrap** for additional themed widgets where customtkinter lacks coverage (treeviews, notebooks, progress bars).

The shell must support a panel/dock layout similar to QGIS: a central map area (placeholder for now) flanked by collapsible side panels (layer tree, properties, toolbox) and a bottom panel (log console, attribute table tabs). Panels are registered by name and toggled via the View menu — this is the extension point for all future UI additions.

### Files to Read Before Starting

1. `LICENSE` — Confirm MIT license
2. `.gitignore` — Confirm Python gitignore patterns

### Constraints

- Do **NOT** implement any map rendering, layer logic, or data I/O — those are TG4/TG5/TG7/TG8's domain
- Do **NOT** add grdl or grdl-runtime as dependencies yet
- All third-party dependencies must be MIT-compatible open-source
- Use **customtkinter** as the primary widget toolkit
- Use **ttkbootstrap** only where customtkinter lacks a widget (e.g., Treeview)
- The panel framework must be extensible — panels register via a `PanelRegistry` without modifying the shell code
- Target Python 3.11+ (match GRDL's minimum)
- Use `src/` layout with `tkgis` as the package name

### Tasks

#### T1.1: Create Project Scaffolding

Set up the project structure, `pyproject.toml`, and entry point.

```
tkgis/
├── CLAUDE.md                  ← Project conventions (create this)
├── pyproject.toml             ← Package metadata and dependencies
├── requirements.txt           ← Pinned dependencies
├── src/
│   └── tkgis/
│       ├── __init__.py        ← Package version, top-level exports
│       ├── __main__.py        ← Entry point: python -m tkgis
│       ├── app.py             ← TkGISApp main application class
│       ├── config.py          ← Application configuration (paths, prefs)
│       ├── constants.py       ← App-wide constants (version, name, defaults)
│       ├── panels/            ← Panel framework
│       │   ├── __init__.py
│       │   ├── base.py        ← BasePanel ABC
│       │   └── registry.py    ← PanelRegistry singleton
│       ├── widgets/           ← Reusable custom widgets
│       │   └── __init__.py
│       └── resources/         ← Icons, themes, assets
│           └── __init__.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── test_app.py
```

`pyproject.toml` dependencies (initial):

```toml
[project]
name = "tkgis"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "customtkinter>=5.2.0",
    "ttkbootstrap>=1.10.0",
    "Pillow>=10.0.0",
]

[project.scripts]
tkgis = "tkgis.__main__:main"

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov"]
```

Write `CLAUDE.md` with project conventions:
- Package name: `tkgis`, import as `tkgis`
- GUI toolkit: customtkinter (primary), ttkbootstrap (supplementary)
- Panel registration pattern (register, don't hardcode)
- Testing: pytest
- Platform: Windows 11 primary, cross-platform secondary

#### T1.2: Implement the Main Application Window

Create `app.py` with the `TkGISApp` class — the root application window.

```python
class TkGISApp(customtkinter.CTk):
    """Main tkgis application window."""

    def __init__(self):
        super().__init__()
        self.title("tkgis")
        self.geometry("1600x900")
        self._setup_menu()
        self._setup_toolbar()
        self._setup_layout()
        self._setup_statusbar()
        self._register_default_panels()

    def _setup_layout(self):
        """Create the dock layout: left panel | center (map) | right panel | bottom panel."""
        # PanedWindow for resizable splits
        ...

    def toggle_panel(self, panel_name: str):
        """Show/hide a registered panel by name."""
        ...
```

Layout structure:
- **Left sidebar** (280px default, collapsible): Layer tree, toolbox
- **Center area** (fills remaining): Map canvas placeholder (dark frame with "Map Canvas" label)
- **Right sidebar** (300px default, collapsible): Properties, metadata inspector
- **Bottom panel** (200px default, collapsible): Log console with scrolling text widget

Use `customtkinter.CTkFrame` for all panel containers. Use ttk `PanedWindow` for resizable splits (customtkinter doesn't have a paned window).

#### T1.3: Implement the Menu System

Create a comprehensive menu bar matching QGIS conventions:

| Menu | Items |
|------|-------|
| **File** | New Project, Open Project, Save Project, Save As, — , Import Layer, Export Layer, — , Recent Projects ▸, — , Exit |
| **Edit** | Undo, Redo, — , Cut, Copy, Paste, — , Preferences |
| **View** | Panels ▸ (dynamic from PanelRegistry), — , Zoom In, Zoom Out, Zoom to Extent, — , Full Screen, — , Theme ▸ (Dark/Light/System) |
| **Layer** | Add Raster Layer, Add Vector Layer, — , Remove Layer, — , Layer Properties, — , Zoom to Layer |
| **Processing** | Toolbox, — , Run Workflow, — , History |
| **Plugins** | Plugin Manager, — , (dynamic plugin entries) |
| **Help** | About, — , Documentation, — , Report Issue |

Use `tkinter.Menu` (customtkinter doesn't override menus). Wire placeholder callbacks that log to the bottom console: `"Menu action: {action_name} (not yet implemented)"`.

#### T1.4: Implement the Toolbar

Create a horizontal toolbar below the menu with icon-sized buttons. Use `customtkinter.CTkButton` with `width=36, height=36` for icon buttons. Initially use text labels (icons added in Phase 6).

Toolbar groups (separated by `CTkFrame` spacers):
1. **File**: New, Open, Save
2. **Navigation**: Pan, Zoom In, Zoom Out, Zoom Extent
3. **Selection**: Select, Deselect
4. **Measurement**: Distance, Area
5. **Processing**: Run Workflow

Each button stores a `tool_name` and emits to a `ToolManager` that tracks the active tool. The active tool button gets a highlighted appearance.

#### T1.5: Implement the Panel Framework

Create the `BasePanel` ABC and `PanelRegistry`.

```python
# panels/base.py
class BasePanel(ABC):
    """Base class for all dockable panels."""

    name: str                    # Unique panel identifier
    title: str                   # Display title
    dock_position: str           # "left", "right", "bottom"
    default_visible: bool = True
    icon: str | None = None

    @abstractmethod
    def create_widget(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        """Build and return the panel's root widget."""
        ...

    def on_show(self): ...
    def on_hide(self): ...
    def on_project_changed(self, project): ...

# panels/registry.py
class PanelRegistry:
    """Singleton registry for panels. Panels register themselves at import time."""

    _panels: dict[str, BasePanel]

    def register(self, panel: BasePanel): ...
    def get(self, name: str) -> BasePanel | None: ...
    def list_panels(self, dock_position: str | None = None) -> list[BasePanel]: ...
    def toggle(self, name: str): ...
```

Create placeholder panels so the layout isn't empty:
- **LogConsolePanel** (bottom): A scrolling `CTkTextbox` that captures log output. Wire Python's `logging` module to append here.
- **PlaceholderPanel** for left ("Layers") and right ("Properties") — these will be replaced by TG5 and TG15.

#### T1.6: Implement the Status Bar

A bottom status bar (`CTkFrame`, height=28) with:
- **Left**: Coordinate display (placeholder: "X: — Y: —")
- **Center**: CRS indicator (placeholder: "EPSG:4326")
- **Right**: Scale indicator, progress bar (hidden until active), memory usage

The status bar exposes `update_coordinates(x, y)`, `update_crs(crs_name)`, `update_scale(scale)`, and `show_progress(value, maximum)` methods for other components to call.

#### T1.7: Implement Theme Management

Wire customtkinter's appearance modes:
- `customtkinter.set_appearance_mode("dark")` / `"light"` / `"system"`
- `customtkinter.set_default_color_theme("blue")` — use blue as the accent
- Store preference in `config.py` and persist to `~/.tkgis/config.json`

The View → Theme submenu toggles between dark/light/system.

#### T1.8: Write Foundation Tests

```python
# tests/test_app.py
def test_app_creates_without_error():
    """App window instantiates without crashing."""

def test_panel_registry():
    """Panels can be registered and retrieved."""

def test_panel_toggle():
    """Panels can be shown and hidden."""

def test_config_persistence():
    """Config saves to and loads from JSON."""
```

Use `pytest`. For tkinter tests, instantiate `tk.Tk()` in fixtures and destroy after. Tests should be fast — no rendering required, just object creation.

### Success Criteria

- [ ] `python -m tkgis` launches a window with menu, toolbar, status bar, and panel layout
- [ ] Panel framework supports register/toggle/list operations
- [ ] Log console panel captures Python logging output
- [ ] Theme switching (dark/light/system) works via View menu
- [ ] Config persists to `~/.tkgis/config.json`
- [ ] `pytest tests/test_app.py` — all tests pass
- [ ] 0 import errors, 0 runtime crashes on launch

### Produces / Consumes

- **Produces**: Application shell, panel framework, toolbar/menu system, status bar API → consumed by TG4, TG5, TG10, TG11, TG13, TG15
- **Produces**: `CLAUDE.md` project conventions → consumed by all subsequent TGs
- **Produces**: `pyproject.toml` with base dependencies → consumed by TG7, TG8 (they add their deps)
- **Consumes**: Nothing from other groups

### Integration Notes for TG16

TG16 must verify that all panels registered by TG5, TG10, TG13, and TG15 appear in the View → Panels submenu and toggle correctly.

---

## Task Group 2: Plugin Architecture & Catalog System

### Agent Profile

You are a **Python systems architect** specializing in plugin architectures, entry points, and catalog systems. You are building the extensibility layer for **tkgis**, a desktop GIS application. Read `CLAUDE.md` before starting — it contains all project conventions, constraints, and patterns you must follow.

### Context

tkgis must support a plugin ecosystem similar to QGIS's plugin manager. Plugins extend tkgis with new tools, panels, data providers, and processing workflows. The plugin system must support three installation vectors:

1. **Built-in plugins**: Shipped with tkgis (e.g., the GRDL raster provider, geopandas vector provider)
2. **Entry-point plugins**: Installed via pip, discovered via `importlib.metadata` entry points
3. **Directory plugins**: Dropped into `~/.tkgis/plugins/` as Python packages

Plugins declare capabilities via a manifest and register components (panels, tools, menu items, data providers) through a typed API. The catalog UI is a panel that lists installed/available plugins with enable/disable/install/remove controls.

### Files to Read Before Starting

1. `src/tkgis/panels/base.py` — Panel ABC (from TG1)
2. `src/tkgis/panels/registry.py` — PanelRegistry pattern (from TG1)
3. `src/tkgis/config.py` — Config system (from TG1)

### Constraints

- Do **NOT** implement any actual plugins — only the framework
- Do **NOT** modify `app.py` — TG16 handles integration
- Plugin discovery must not crash the app if a plugin fails to load — isolate failures with try/except and log errors
- All plugin hooks must be optional — a plugin that only adds a panel needn't implement tool hooks
- Do **NOT** add network/download capabilities yet — plugin installation from remote repos is a future feature

### Tasks

#### T2.1: Define the Plugin Manifest

```python
# src/tkgis/plugins/manifest.py
from dataclasses import dataclass, field

@dataclass(frozen=True)
class PluginManifest:
    """Declares a plugin's identity and capabilities."""
    name: str                          # Unique identifier (e.g., "grdl-raster")
    display_name: str                  # Human-readable name
    version: str                       # Semver string
    description: str
    author: str
    license: str                       # Must be MIT-compatible
    min_tkgis_version: str = "0.1.0"
    capabilities: list[str] = field(default_factory=list)
    # Valid capabilities: "data_provider", "tool", "panel", "processing", "analysis"
    dependencies: list[str] = field(default_factory=list)  # Other plugin names
```

#### T2.2: Define the Plugin ABC

```python
# src/tkgis/plugins/base.py
class TkGISPlugin(ABC):
    """Base class for all tkgis plugins."""

    manifest: PluginManifest

    def activate(self, app_context: 'PluginContext') -> None:
        """Called when plugin is enabled. Register panels, tools, providers."""
        ...

    def deactivate(self) -> None:
        """Called when plugin is disabled. Unregister everything."""
        ...

class PluginContext:
    """Facade providing controlled access to tkgis internals for plugins."""

    panel_registry: PanelRegistry
    tool_manager: 'ToolManager'
    menu_manager: 'MenuManager'
    data_provider_registry: 'DataProviderRegistry'
    config: Config

    def register_panel(self, panel: BasePanel): ...
    def register_tool(self, tool: 'BaseTool'): ...
    def add_menu_item(self, menu_path: str, label: str, callback): ...
    def register_data_provider(self, provider: 'DataProvider'): ...
```

#### T2.3: Implement Plugin Discovery

```python
# src/tkgis/plugins/discovery.py
class PluginDiscovery:
    """Discovers plugins from three sources."""

    def discover_builtin(self) -> list[type[TkGISPlugin]]:
        """Scan tkgis.plugins.builtin package."""
        ...

    def discover_entrypoints(self) -> list[type[TkGISPlugin]]:
        """Scan 'tkgis.plugins' entry point group via importlib.metadata."""
        ...

    def discover_directory(self, path: Path) -> list[type[TkGISPlugin]]:
        """Scan ~/.tkgis/plugins/ for plugin packages with __plugin__.py."""
        ...

    def discover_all(self) -> list[type[TkGISPlugin]]:
        """Merge all sources. Deduplicate by manifest.name. Log failures."""
        ...
```

Each directory plugin must contain a `__plugin__.py` with a `get_plugin() -> type[TkGISPlugin]` factory function.

#### T2.4: Implement the Plugin Manager

```python
# src/tkgis/plugins/manager.py
class PluginManager:
    """Lifecycle management for plugins."""

    def __init__(self, config: Config):
        self._plugins: dict[str, TkGISPlugin] = {}
        self._enabled: set[str] = set()
        self._config = config

    def load_all(self) -> None:
        """Discover and instantiate all plugins. Don't activate yet."""
        ...

    def activate(self, name: str) -> None:
        """Activate a plugin. Resolve dependencies first."""
        ...

    def deactivate(self, name: str) -> None:
        """Deactivate a plugin and any dependents."""
        ...

    def is_enabled(self, name: str) -> bool: ...

    def list_plugins(self) -> list[PluginManifest]: ...
```

Persist enabled/disabled state in `~/.tkgis/plugins.json`.

#### T2.5: Implement the Plugin Manager Panel

A panel (dock_position="right") that lists all discovered plugins with:
- Plugin name, version, author, description
- Enable/Disable toggle (CTkSwitch)
- Status indicator (loaded, error, disabled)
- Error details expandable if load failed

Register this panel as "plugin_manager" in the PanelRegistry. It appears under Plugins → Plugin Manager menu item.

#### T2.6: Implement the Data Provider Registry

```python
# src/tkgis/plugins/providers.py
class DataProvider(ABC):
    """Interface for plugins that provide data reading/writing."""

    name: str
    supported_extensions: list[str]     # e.g., [".shp", ".geojson"]
    supported_modalities: list[str]     # e.g., ["vector", "raster"]

    @abstractmethod
    def can_open(self, path: Path) -> bool: ...

    @abstractmethod
    def open(self, path: Path) -> 'Layer': ...

    @abstractmethod
    def get_file_filter(self) -> str:
        """Return file dialog filter string, e.g., 'Shapefiles (*.shp)'"""
        ...

class DataProviderRegistry:
    """Routes file open requests to the appropriate provider."""

    def register(self, provider: DataProvider): ...
    def open_file(self, path: Path) -> 'Layer': ...
    def get_all_filters(self) -> str: ...
    def find_provider(self, path: Path) -> DataProvider | None: ...
```

#### T2.7: Write Plugin System Tests

```python
def test_plugin_manifest_creation(): ...
def test_plugin_discovery_builtin(): ...
def test_plugin_activate_deactivate(): ...
def test_data_provider_registry(): ...
def test_plugin_failure_isolation(): ...
def test_dependency_resolution(): ...
```

### Success Criteria

- [ ] Plugin manifest dataclass validates required fields
- [ ] Discovery finds builtin plugins, entry-point plugins, and directory plugins
- [ ] Plugin activation/deactivation lifecycle works without crashing
- [ ] Failed plugin loads are isolated — app continues with other plugins
- [ ] Data provider registry routes file opens to correct provider
- [ ] Plugin enabled/disabled state persists across restarts
- [ ] `pytest tests/test_plugins.py` — all tests pass

### Produces / Consumes

- **Produces**: Plugin framework (TkGISPlugin, PluginContext, DataProvider, DataProviderRegistry) → consumed by TG7, TG8, TG9, TG11
- **Produces**: Plugin Manager panel → consumed by TG16 (integration into app shell)
- **Consumes**: PanelRegistry from TG1, Config from TG1

---

## Task Group 3: Core Data Models

### Agent Profile

You are a **Python data engineer** specializing in geospatial data models, coordinate reference systems, and temporal data structures. You are building the domain model layer for **tkgis**, a desktop GIS application. Read `CLAUDE.md` before starting — it contains all project conventions, constraints, and patterns you must follow.

### Context

Every GIS application needs a robust data model for layers, features, projections, and project state. tkgis models must support:

- **Vector layers**: Point, Line, Polygon geometries with attribute tables (backed by geopandas)
- **Raster layers**: Single-band and multi-band imagery including very large images (backed by GRDL readers)
- **Temporal layers**: Layers with a time dimension (e.g., time-series satellite imagery)
- **Projects**: Serializable workspace state (layers, view extent, CRS, tool state)

Models are pure Python dataclasses/Pydantic models with no GUI dependencies. They are the shared vocabulary between all task groups.

### Files to Read Before Starting

1. `src/tkgis/constants.py` — App constants (from TG1)
2. `src/tkgis/config.py` — Config patterns (from TG1)

### Constraints

- Do **NOT** import any GUI libraries (tkinter, customtkinter) in model files
- Do **NOT** add geopandas or grdl as hard dependencies — use `TYPE_CHECKING` guards for type hints and lazy imports for runtime
- Models must be serializable to JSON for project save/load
- Use `dataclasses` for simple models, Pydantic `BaseModel` for models requiring validation
- All coordinate handling must be CRS-aware — never assume EPSG:4326

### Tasks

#### T3.1: Create the Bounds and Geometry Models

```python
# src/tkgis/models/geometry.py
@dataclass(frozen=True)
class BoundingBox:
    """Axis-aligned bounding box in a given CRS."""
    xmin: float
    ymin: float
    xmax: float
    ymax: float
    crs: str = "EPSG:4326"

    @property
    def width(self) -> float: ...
    @property
    def height(self) -> float: ...
    @property
    def center(self) -> tuple[float, float]: ...
    def contains(self, x: float, y: float) -> bool: ...
    def intersects(self, other: 'BoundingBox') -> bool: ...
    def union(self, other: 'BoundingBox') -> 'BoundingBox': ...
    def to_dict(self) -> dict: ...

    @classmethod
    def from_dict(cls, d: dict) -> 'BoundingBox': ...
```

#### T3.2: Create the CRS Model

```python
# src/tkgis/models/crs.py
@dataclass
class CRSDefinition:
    """Coordinate Reference System wrapper."""
    epsg_code: int | None          # e.g., 4326
    proj_string: str | None        # PROJ string fallback
    wkt: str | None                # WKT fallback
    name: str                      # Human-readable (e.g., "WGS 84")
    is_geographic: bool            # True for lat/lon, False for projected
    units: str                     # "degrees" or "meters"

    @classmethod
    def from_epsg(cls, code: int) -> 'CRSDefinition': ...

    @classmethod
    def from_pyproj(cls, crs) -> 'CRSDefinition': ...

    def to_pyproj(self):
        """Convert to pyproj.CRS (lazy import)."""
        ...

    def to_dict(self) -> dict: ...
```

#### T3.3: Create the Layer Model Hierarchy

```python
# src/tkgis/models/layers.py
from enum import Enum, auto
import uuid

class LayerType(Enum):
    VECTOR = auto()
    RASTER = auto()
    TEMPORAL_RASTER = auto()
    TEMPORAL_VECTOR = auto()
    ANNOTATION = auto()

@dataclass
class LayerStyle:
    """Visual styling for a layer."""
    opacity: float = 1.0
    visible: bool = True
    # Vector-specific
    fill_color: str | None = None
    stroke_color: str | None = None
    stroke_width: float = 1.0
    # Raster-specific
    colormap: str | None = None
    band_mapping: list[int] | None = None   # RGB band indices
    contrast_stretch: str = "percentile"     # "minmax", "percentile", "stddev"
    stretch_params: dict | None = None

@dataclass
class Layer:
    """Base layer model."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    layer_type: LayerType = LayerType.RASTER
    source_path: str | None = None
    crs: CRSDefinition | None = None
    bounds: BoundingBox | None = None
    style: LayerStyle = field(default_factory=LayerStyle)
    metadata: dict = field(default_factory=dict)

    # Temporal fields (optional)
    time_start: str | None = None    # ISO 8601
    time_end: str | None = None
    time_steps: list[str] | None = None

    def to_dict(self) -> dict: ...

    @classmethod
    def from_dict(cls, d: dict) -> 'Layer': ...
```

#### T3.4: Create the Project Model

```python
# src/tkgis/models/project.py
@dataclass
class MapView:
    """Current map view state."""
    center_x: float = 0.0
    center_y: float = 0.0
    zoom_level: float = 1.0
    rotation: float = 0.0
    crs: str = "EPSG:4326"

@dataclass
class Project:
    """Serializable project state."""
    name: str = "Untitled Project"
    path: str | None = None
    crs: CRSDefinition = field(default_factory=lambda: CRSDefinition.from_epsg(4326))
    layers: list[Layer] = field(default_factory=list)
    map_view: MapView = field(default_factory=MapView)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())
    plugin_state: dict = field(default_factory=dict)

    def save(self, path: str | Path | None = None) -> None:
        """Serialize to JSON."""
        ...

    @classmethod
    def load(cls, path: str | Path) -> 'Project':
        """Deserialize from JSON."""
        ...

    def add_layer(self, layer: Layer) -> None: ...
    def remove_layer(self, layer_id: str) -> None: ...
    def get_layer(self, layer_id: str) -> Layer | None: ...
    def move_layer(self, layer_id: str, new_index: int) -> None: ...
    def get_full_extent(self) -> BoundingBox | None: ...
```

#### T3.5: Create the Event System

An observer pattern for decoupled communication between models and GUI.

```python
# src/tkgis/models/events.py
from enum import Enum, auto
from typing import Callable, Any

class EventType(Enum):
    LAYER_ADDED = auto()
    LAYER_REMOVED = auto()
    LAYER_VISIBILITY_CHANGED = auto()
    LAYER_STYLE_CHANGED = auto()
    LAYER_ORDER_CHANGED = auto()
    LAYER_SELECTED = auto()
    PROJECT_LOADED = auto()
    PROJECT_SAVED = auto()
    PROJECT_MODIFIED = auto()
    VIEW_CHANGED = auto()
    CRS_CHANGED = auto()
    TOOL_CHANGED = auto()
    PROGRESS_UPDATED = auto()
    TIME_STEP_CHANGED = auto()

class EventBus:
    """Publish-subscribe event bus for decoupled component communication."""

    _listeners: dict[EventType, list[Callable]]

    def subscribe(self, event_type: EventType, callback: Callable) -> None: ...
    def unsubscribe(self, event_type: EventType, callback: Callable) -> None: ...
    def emit(self, event_type: EventType, **kwargs) -> None: ...
```

The EventBus is a singleton shared across the application. All state changes go through events — the GUI subscribes and updates reactively.

#### T3.6: Create the Tool Model

```python
# src/tkgis/models/tools.py
class ToolMode(Enum):
    PAN = auto()
    ZOOM_IN = auto()
    ZOOM_OUT = auto()
    SELECT = auto()
    MEASURE_DISTANCE = auto()
    MEASURE_AREA = auto()
    DRAW_POINT = auto()
    DRAW_LINE = auto()
    DRAW_POLYGON = auto()
    IDENTIFY = auto()

class BaseTool(ABC):
    """Abstract base for map interaction tools."""
    name: str
    mode: ToolMode
    cursor: str = "arrow"

    @abstractmethod
    def on_press(self, x: float, y: float, map_x: float, map_y: float) -> None: ...
    @abstractmethod
    def on_drag(self, x: float, y: float, map_x: float, map_y: float) -> None: ...
    @abstractmethod
    def on_release(self, x: float, y: float, map_x: float, map_y: float) -> None: ...
    def on_move(self, x: float, y: float, map_x: float, map_y: float) -> None: ...
    def on_scroll(self, x: float, y: float, delta: int) -> None: ...
    def on_key(self, key: str) -> None: ...
    def activate(self) -> None: ...
    def deactivate(self) -> None: ...

class ToolManager:
    """Manages the active tool and tool switching."""
    _active_tool: BaseTool | None
    _tools: dict[str, BaseTool]
    _event_bus: EventBus

    def register_tool(self, tool: BaseTool) -> None: ...
    def set_active(self, tool_name: str) -> None: ...
    def get_active(self) -> BaseTool | None: ...
```

#### T3.7: Write Model Tests

```python
def test_bounding_box_operations(): ...
def test_crs_definition_from_epsg(): ...
def test_layer_serialization_roundtrip(): ...
def test_project_save_load(): ...
def test_event_bus_pub_sub(): ...
def test_tool_manager_activation(): ...
def test_project_layer_operations(): ...
```

### Success Criteria

- [ ] All models are importable without GUI dependencies
- [ ] Layer, Project, BoundingBox, CRSDefinition serialize to/from JSON losslessly
- [ ] EventBus delivers events to subscribers and supports unsubscribe
- [ ] ToolManager switches tools and emits TOOL_CHANGED events
- [ ] Project.save/load round-trips all fields
- [ ] `pytest tests/test_models.py` — all tests pass
- [ ] No hard dependency on geopandas, grdl, or pyproj at import time

### Produces / Consumes

- **Produces**: Layer, Project, BoundingBox, CRSDefinition, EventBus, ToolManager, BaseTool → consumed by TG4, TG5, TG6, TG7, TG8, TG9, TG10, TG11, TG12, TG13, TG14, TG15
- **Produces**: DataProvider ABC → consumed by TG7, TG8
- **Consumes**: Constants from TG1

---

## Task Group 4: Tile-Based Map Canvas

### Agent Profile

You are a **Python graphics engineer** specializing in 2D rendering, tile-based map engines, and very large image visualization. You are building the central map canvas for **tkgis**, a desktop GIS application that must handle remotely sensed imagery (10,000+ x 10,000+ pixels) smoothly. Read `CLAUDE.md` before starting — it contains all project conventions, constraints, and patterns you must follow.

### Context

The map canvas is the heart of tkgis. It must render multiple layers (raster and vector) composited together, support smooth pan/zoom with mouse and keyboard, display coordinate grids, and handle images far too large to fit in memory by tiling.

The canvas uses tkinter's `Canvas` widget as the rendering surface. For raster layers, the approach is **tile-based pyramid rendering**: the image is divided into tiles at multiple zoom levels. Only visible tiles are loaded and rendered as `PhotoImage` objects. As the user pans/zooms, tiles are loaded on demand and cached in an LRU cache.

Vector layers are rendered as Canvas items (lines, polygons, ovals) that scale with the view transform.

The view transform converts between three coordinate spaces:
1. **Screen coordinates**: Pixel position on the canvas widget
2. **Map coordinates**: Position in the project CRS (e.g., meters in UTM, degrees in WGS84)
3. **Image coordinates**: Pixel position in a raster layer

### Files to Read Before Starting

1. `src/tkgis/models/geometry.py` — BoundingBox (from TG3)
2. `src/tkgis/models/layers.py` — Layer model (from TG3)
3. `src/tkgis/models/events.py` — EventBus (from TG3)
4. `src/tkgis/models/tools.py` — BaseTool, ToolManager (from TG3)
5. `src/tkgis/models/crs.py` — CRSDefinition (from TG3)

### Constraints

- Do **NOT** implement data loading — use a `TileProvider` ABC that TG8 will implement for raster data
- Do **NOT** add GRDL dependencies — the canvas is provider-agnostic
- Tile cache must be bounded (LRU, configurable max memory)
- Canvas must not freeze during tile loading — use `threading` for background tile fetching and `widget.after()` for UI updates
- All rendering must use tkinter Canvas API (no OpenGL, no pygame)
- Mouse wheel zoom must be smooth (fractional zoom levels)

### Tasks

#### T4.1: Implement the View Transform

```python
# src/tkgis/canvas/transform.py
class ViewTransform:
    """Converts between screen pixels and map coordinates."""

    def __init__(self, center_x: float, center_y: float,
                 scale: float, canvas_width: int, canvas_height: int):
        ...

    def screen_to_map(self, sx: float, sy: float) -> tuple[float, float]: ...
    def map_to_screen(self, mx: float, my: float) -> tuple[float, float]: ...
    def get_visible_extent(self) -> BoundingBox: ...
    def zoom(self, factor: float, anchor_sx: float, anchor_sy: float) -> None:
        """Zoom centered on a screen point (mouse position)."""
        ...
    def pan(self, dx_screen: float, dy_screen: float) -> None: ...
    def fit_extent(self, bbox: BoundingBox) -> None:
        """Adjust scale and center to fit a bounding box."""
        ...
```

The transform must handle both geographic (degrees) and projected (meters) CRS correctly. Y-axis is inverted (screen Y increases downward, map Y increases upward for projected CRS).

#### T4.2: Implement the Tile System

```python
# src/tkgis/canvas/tiles.py
@dataclass(frozen=True)
class TileKey:
    """Identifies a tile in the pyramid."""
    layer_id: str
    zoom_level: int
    tile_row: int
    tile_col: int

class TileProvider(ABC):
    """Interface for tile data sources. Implemented by raster data providers."""

    @abstractmethod
    def get_tile(self, layer: Layer, zoom_level: int,
                 row: int, col: int, tile_size: int) -> np.ndarray | None:
        """Return a tile as an RGB(A) uint8 array, or None if out of bounds."""
        ...

    @abstractmethod
    def get_num_zoom_levels(self, layer: Layer) -> int: ...

    @abstractmethod
    def get_tile_grid(self, layer: Layer, zoom_level: int) -> tuple[int, int]:
        """Return (num_rows, num_cols) at this zoom level."""
        ...

class TileCache:
    """LRU cache for rendered tiles (PhotoImage objects)."""

    def __init__(self, max_tiles: int = 256):
        self._cache: OrderedDict[TileKey, ImageTk.PhotoImage] = OrderedDict()
        self._max_tiles = max_tiles

    def get(self, key: TileKey) -> ImageTk.PhotoImage | None: ...
    def put(self, key: TileKey, image: ImageTk.PhotoImage) -> None: ...
    def invalidate_layer(self, layer_id: str) -> None: ...
    def clear(self) -> None: ...
```

Tile size: 256x256 pixels (standard). Zoom levels are integer powers of 2 downsampling from the native resolution.

#### T4.3: Implement the Map Canvas Widget

```python
# src/tkgis/canvas/map_canvas.py
class MapCanvas(tk.Canvas):
    """The main map display widget. Renders layers via tile compositing."""

    def __init__(self, parent, event_bus: EventBus, tool_manager: ToolManager):
        super().__init__(parent, bg="#1e1e2e", highlightthickness=0)
        self._transform = ViewTransform(...)
        self._tile_cache = TileCache()
        self._layers: list[Layer] = []
        self._tile_providers: dict[str, TileProvider] = {}
        self._event_bus = event_bus
        self._tool_manager = tool_manager
        self._bind_events()

    def set_layers(self, layers: list[Layer]) -> None: ...
    def register_tile_provider(self, layer_id: str, provider: TileProvider) -> None: ...
    def refresh(self) -> None:
        """Recompute visible tiles and redraw."""
        ...

    def _render_frame(self) -> None:
        """Main render loop: determine visible tiles, load missing, composite."""
        ...

    def _load_tile_async(self, key: TileKey) -> None:
        """Load a tile in a background thread, schedule canvas update."""
        ...

    # Mouse event handlers
    def _on_mouse_press(self, event): ...
    def _on_mouse_drag(self, event): ...
    def _on_mouse_release(self, event): ...
    def _on_mouse_move(self, event): ...
    def _on_mouse_wheel(self, event): ...
    def _on_resize(self, event): ...
```

Rendering pipeline:
1. Compute visible extent from transform
2. Determine which tiles at the current zoom level intersect the visible extent
3. For each visible tile: check cache → if miss, start async load → show placeholder (gray tile)
4. Composite tiles onto the canvas using `canvas.create_image()`
5. Render vector layers on top as Canvas items
6. Render overlays (grid, crosshair, selection boxes)

#### T4.4: Implement Pan and Zoom Tools

Wire the built-in pan/zoom into the canvas:

- **Pan**: Click-drag moves the view. Use `ToolMode.PAN`. Cursor changes to grab hand.
- **Zoom In**: Click zooms in at click point. Drag draws a zoom rectangle. `ToolMode.ZOOM_IN`.
- **Zoom Out**: Click zooms out. `ToolMode.ZOOM_OUT`.
- **Mouse wheel**: Always zooms (regardless of active tool). Zoom centers on cursor position. Smooth fractional steps (factor 1.2 per notch).
- **Keyboard**: Arrow keys pan. +/- zoom. Home key fits full extent.

Create concrete `PanTool`, `ZoomInTool`, `ZoomOutTool` extending `BaseTool`. Register them with `ToolManager`.

#### T4.5: Implement the Coordinate Grid Overlay

Render a grid of coordinate lines (graticule) on top of layers:
- Grid spacing auto-adjusts to zoom level (aim for ~5-8 lines visible)
- Labels at grid edges showing coordinate values
- Thin semi-transparent lines
- Toggle via View menu option

```python
# src/tkgis/canvas/overlays.py
class CoordinateGrid:
    def draw(self, canvas: tk.Canvas, transform: ViewTransform, crs: CRSDefinition): ...
```

#### T4.6: Implement the Minimap Widget

A small overview widget (200x150) in the corner of the map canvas showing the full extent with a rectangle indicating the current view. Clicking on the minimap repositions the main view.

```python
# src/tkgis/canvas/minimap.py
class MiniMap(tk.Canvas):
    """Overview widget showing full extent with current view rectangle."""
    def __init__(self, parent, map_canvas: MapCanvas): ...
    def update_view(self): ...
```

#### T4.7: Write Canvas Tests

```python
def test_view_transform_screen_to_map_roundtrip(): ...
def test_view_transform_zoom_anchor(): ...
def test_tile_cache_lru_eviction(): ...
def test_tile_key_visible_computation(): ...
def test_pan_tool_updates_transform(): ...
```

### Success Criteria

- [ ] ViewTransform converts screen↔map coordinates correctly in both geographic and projected CRS
- [ ] TileCache evicts least-recently-used tiles when full
- [ ] MapCanvas renders placeholder tiles (gray grid) when no data is loaded
- [ ] Pan via click-drag updates the view smoothly
- [ ] Mouse wheel zoom centers on cursor position
- [ ] Coordinate grid renders with auto-spacing
- [ ] Minimap shows current view rectangle
- [ ] Background tile loading does not freeze the UI
- [ ] `pytest tests/test_canvas.py` — all tests pass

### Produces / Consumes

- **Produces**: MapCanvas widget, TileProvider ABC, ViewTransform → consumed by TG5, TG8, TG10, TG12
- **Produces**: PanTool, ZoomInTool, ZoomOutTool → consumed by TG10
- **Consumes**: Layer, BoundingBox, CRSDefinition, EventBus, ToolManager, BaseTool from TG3

---

## Task Group 5: Layer Management System

### Agent Profile

You are a **Python GUI developer** specializing in tree-based data management interfaces and layer compositing. You are building the layer management panel for **tkgis**, a desktop GIS application. Read `CLAUDE.md` before starting — it contains all project conventions, constraints, and patterns you must follow.

### Context

The Layer Manager is the primary interface for organizing, styling, and controlling layer visibility. It is a panel docked to the left side of the application that displays a tree view of all layers in the project. Users can:

- Reorder layers by drag-and-drop
- Toggle visibility with checkboxes
- Expand layers to see sub-items (bands for raster, geometry types for vector)
- Right-click for context menu (rename, remove, zoom to, properties, export)
- Double-click to open the Layer Properties dialog

The layer manager listens to EventBus events and updates the tree reactively. It also emits events when the user changes layer order or visibility.

### Files to Read Before Starting

1. `src/tkgis/models/layers.py` — Layer model (from TG3)
2. `src/tkgis/models/events.py` — EventBus (from TG3)
3. `src/tkgis/panels/base.py` — BasePanel ABC (from TG1)
4. `src/tkgis/panels/registry.py` — PanelRegistry (from TG1)
5. `src/tkgis/models/project.py` — Project model (from TG3)

### Constraints

- Do **NOT** implement layer data loading — only manage Layer model objects
- Do **NOT** implement the Layer Properties dialog in detail — create a placeholder that TG16 will complete
- Use `ttkbootstrap.Treeview` for the tree (customtkinter doesn't have Treeview)
- Drag-and-drop must work for reordering (use tkinter DnD or manual selection+move buttons)
- Layer icons: use text symbols initially (🗺 raster, 📍 vector) — icon images added in Phase 6

### Tasks

#### T5.1: Implement the Layer Tree Panel

```python
# src/tkgis/panels/layer_tree.py
class LayerTreePanel(BasePanel):
    name = "layer_tree"
    title = "Layers"
    dock_position = "left"
    default_visible = True

    def __init__(self, project: Project, event_bus: EventBus):
        self._project = project
        self._event_bus = event_bus
        self._tree: ttkbootstrap.Treeview | None = None

    def create_widget(self, parent) -> ctk.CTkFrame:
        """Build the layer tree with toolbar and treeview."""
        ...

    def _build_toolbar(self, parent) -> ctk.CTkFrame:
        """Add/Remove/Move Up/Move Down buttons above the tree."""
        ...

    def _refresh_tree(self) -> None:
        """Rebuild tree items from project.layers."""
        ...

    def _on_layer_added(self, **kwargs) -> None: ...
    def _on_layer_removed(self, **kwargs) -> None: ...
    def _on_visibility_toggled(self, event) -> None: ...
    def _on_context_menu(self, event) -> None: ...
    def _on_double_click(self, event) -> None: ...
```

Tree structure:
```
☑ Layer Name (raster)
  ├── Band 1: Red
  ├── Band 2: Green
  └── Band 3: Blue
☑ Layer Name (vector)
  ├── Points (42 features)
  └── Polygons (15 features)
☐ Layer Name (hidden)
```

#### T5.2: Implement Layer Reordering

Support layer reordering via:
1. **Move Up / Move Down buttons** in the layer toolbar
2. **Keyboard shortcuts**: Alt+Up, Alt+Down
3. **Drag-and-drop** (if feasible with ttkbootstrap Treeview — otherwise defer to buttons + keyboard)

On reorder, emit `EventType.LAYER_ORDER_CHANGED` so the map canvas re-composites.

#### T5.3: Implement the Context Menu

Right-click on a layer item shows:

| Item | Action |
|------|--------|
| Zoom to Layer | Calls `map_canvas.fit_extent(layer.bounds)` |
| Rename | Inline edit in tree |
| Remove Layer | Removes from project, emits event |
| Duplicate Layer | Clones layer with "(copy)" suffix |
| — | separator |
| Properties... | Opens Layer Properties dialog (placeholder) |
| Export Layer... | File save dialog (placeholder) |

#### T5.4: Implement the Layer Style Quick Controls

Below the tree, add a collapsible section with quick style controls for the selected layer:

- **Opacity slider** (0–100%) → updates `layer.style.opacity`
- **Colormap dropdown** (for raster): viridis, gray, terrain, jet, hot → updates `layer.style.colormap`
- **Band mapping** (for multi-band raster): R/G/B dropdowns selecting band indices

Changes emit `EventType.LAYER_STYLE_CHANGED` immediately for live preview.

#### T5.5: Implement the Layer Properties Dialog

A modal dialog (customtkinter `CTkToplevel`) with tabs:

| Tab | Contents |
|-----|----------|
| **General** | Name, type, source path, CRS, extent, feature/pixel count |
| **Style** | Full style controls (expanded version of quick controls) |
| **Metadata** | Key-value table of layer metadata |
| **Temporal** | Time range, time steps, current time (if temporal layer) |

Implement General and Metadata tabs fully. Style and Temporal as placeholders.

#### T5.6: Write Layer Manager Tests

```python
def test_layer_tree_reflects_project(): ...
def test_layer_visibility_toggle(): ...
def test_layer_reorder(): ...
def test_context_menu_actions(): ...
def test_style_change_emits_event(): ...
```

### Success Criteria

- [ ] Layer tree displays all project layers with correct names and types
- [ ] Checkbox toggles update `layer.style.visible` and emit events
- [ ] Layer reordering works via buttons and emits LAYER_ORDER_CHANGED
- [ ] Context menu provides Zoom to, Rename, Remove, Properties actions
- [ ] Opacity slider updates layer style in real-time
- [ ] Layer Properties dialog shows layer metadata
- [ ] `pytest tests/test_layer_manager.py` — all tests pass

### Produces / Consumes

- **Produces**: LayerTreePanel → consumed by TG16 (registration in app shell)
- **Produces**: Layer Properties dialog → consumed by TG8 (raster-specific fields), TG7 (vector-specific fields)
- **Consumes**: Layer, Project, EventBus from TG3; BasePanel, PanelRegistry from TG1

---

## Task Group 6: Coordinate Reference System Engine

### Agent Profile

You are a **Python geospatial developer** specializing in coordinate reference systems, map projections, and spatial transformations. You are building the CRS engine for **tkgis**, a desktop GIS application. Read `CLAUDE.md` before starting — it contains all project conventions, constraints, and patterns you must follow.

### Context

Every layer in tkgis may have a different CRS. The map canvas renders in a single "project CRS." The CRS engine handles on-the-fly reprojection so layers in different CRS display correctly together. It wraps `pyproj` for the heavy lifting but provides a clean API for the rest of tkgis.

The CRS engine also provides:
- A CRS selector dialog (searchable EPSG database)
- Coordinate display formatting (DMS, DD, projected)
- Scale computation for the status bar
- Distance/area measurement in the project CRS

### Files to Read Before Starting

1. `src/tkgis/models/crs.py` — CRSDefinition (from TG3)
2. `src/tkgis/models/geometry.py` — BoundingBox (from TG3)
3. `src/tkgis/canvas/transform.py` — ViewTransform (from TG4)

### Constraints

- `pyproj` is the **only** projection library — do **NOT** use GDAL/OGR directly
- Cache `pyproj.Transformer` instances — they are expensive to create
- Reprojection must handle antimeridian-crossing bounding boxes
- All public methods must accept both `CRSDefinition` objects and EPSG integer codes

### Tasks

#### T6.1: Implement the CRS Transformation Engine

```python
# src/tkgis/crs/engine.py
class CRSEngine:
    """Manages CRS transformations for the application."""

    _transformer_cache: dict[tuple[str, str], pyproj.Transformer]

    def transform_point(self, x: float, y: float,
                        from_crs: CRSDefinition | int,
                        to_crs: CRSDefinition | int) -> tuple[float, float]: ...

    def transform_points(self, xs: np.ndarray, ys: np.ndarray,
                         from_crs, to_crs) -> tuple[np.ndarray, np.ndarray]: ...

    def transform_bbox(self, bbox: BoundingBox,
                       to_crs: CRSDefinition | int) -> BoundingBox: ...

    def get_units(self, crs: CRSDefinition | int) -> str: ...

    def compute_scale(self, transform: ViewTransform,
                      crs: CRSDefinition) -> float:
        """Compute map scale (1:N) at the current view center."""
        ...

    def compute_distance(self, x1, y1, x2, y2, crs) -> float:
        """Geodesic distance in meters."""
        ...

    def compute_area(self, coords: list[tuple[float, float]], crs) -> float:
        """Geodesic area in square meters."""
        ...
```

#### T6.2: Implement Coordinate Formatting

```python
# src/tkgis/crs/formatting.py
class CoordinateFormatter:
    """Formats coordinates for display."""

    def format_dd(self, x: float, y: float) -> str:
        """Decimal degrees: '38.8977° N, 77.0365° W'"""
        ...

    def format_dms(self, x: float, y: float) -> str:
        """Degrees/minutes/seconds: '38° 53' 51.7\" N, 77° 2' 11.4\" W'"""
        ...

    def format_projected(self, x: float, y: float, units: str) -> str:
        """Projected: '500000.0 m E, 4306000.0 m N'"""
        ...

    def auto_format(self, x: float, y: float, crs: CRSDefinition) -> str:
        """Choose format based on CRS type."""
        ...
```

#### T6.3: Implement the CRS Selector Dialog

A searchable dialog for choosing a CRS from the EPSG database.

```python
# src/tkgis/crs/selector.py
class CRSSelectorDialog(ctk.CTkToplevel):
    """Modal dialog for selecting a CRS."""

    def __init__(self, parent, current_crs: CRSDefinition | None = None):
        ...
        # Search entry at top
        # Treeview with columns: EPSG Code, Name, Type, Units
        # Preview of selected CRS (WKT display)
        # OK / Cancel buttons

    def _populate_common(self) -> None:
        """Pre-populate with common CRS: WGS84, UTM zones, Web Mercator, etc."""
        ...

    def _search(self, query: str) -> None:
        """Filter EPSG database by query string."""
        ...

    def get_result(self) -> CRSDefinition | None: ...
```

Use `pyproj.database.get_codes()` to query the EPSG database. Pre-populate with 20-30 common CRS for quick access.

#### T6.4: Write CRS Engine Tests

```python
def test_transform_wgs84_to_utm(): ...
def test_transform_roundtrip(): ...
def test_bbox_reprojection(): ...
def test_geodesic_distance(): ...
def test_coordinate_formatting_dd(): ...
def test_coordinate_formatting_dms(): ...
def test_scale_computation(): ...
```

### Success Criteria

- [ ] CRS transformations are numerically correct (validate against known EPSG test points)
- [ ] Transformer cache avoids redundant `pyproj.Transformer` creation
- [ ] BoundingBox reprojection handles antimeridian correctly
- [ ] Geodesic distance matches pyproj.Geod within 1m
- [ ] CRS selector dialog searches and returns selected CRS
- [ ] Coordinate formatting produces correct DMS strings
- [ ] `pytest tests/test_crs.py` — all tests pass

### Produces / Consumes

- **Produces**: CRSEngine, CoordinateFormatter, CRSSelectorDialog → consumed by TG4 (map canvas), TG7 (vector reprojection), TG8 (raster geolocation), TG10 (measurement tools), TG12 (spatial queries)
- **Consumes**: CRSDefinition, BoundingBox from TG3; ViewTransform from TG4

---

## Task Group 7: Vector Data I/O (GeoPandas Integration)

### Agent Profile

You are a **Python geospatial developer** specializing in vector data formats, geopandas, and spatial databases. You are building the vector data provider for **tkgis**, a desktop GIS application. Read `CLAUDE.md` before starting — it contains all project conventions, constraints, and patterns you must follow.

### Context

tkgis must read and write all common vector geospatial formats. We use **geopandas** as the backend — it handles format diversity through Fiona/pyogrio and provides a rich DataFrame API for attribute operations.

The vector provider is implemented as a **tkgis plugin** (using TG2's plugin framework). It registers a `DataProvider` for vector formats and creates `Layer` objects with geopandas GeoDataFrames as the backing data.

Supported formats: Shapefile (.shp), GeoJSON (.geojson/.json), GeoPackage (.gpkg), KML (.kml/.kmz), CSV with geometry (.csv), GML (.gml), FlatGeobuf (.fgb), Parquet with geometry (.parquet/.geoparquet).

### Files to Read Before Starting

1. `src/tkgis/plugins/base.py` — TkGISPlugin ABC (from TG2)
2. `src/tkgis/plugins/providers.py` — DataProvider ABC (from TG2)
3. `src/tkgis/models/layers.py` — Layer model (from TG3)
4. `src/tkgis/models/crs.py` — CRSDefinition (from TG3)

### Constraints

- Do **NOT** use GDAL/OGR directly — use geopandas which wraps it
- Large vector files (>100k features) must be loaded lazily or with spatial indexing — do NOT load 10M features into memory at once
- Vector rendering on the canvas is TG4's domain via the tile provider pattern — this TG provides the data, not the rendering
- CRS of loaded data must be detected and stored in the Layer.crs field
- Attribute data must be accessible as a pandas DataFrame for the attribute table (TG15)

### Tasks

#### T7.1: Implement the Vector Data Provider Plugin

```python
# src/tkgis/plugins/builtin/vector_provider.py
class VectorDataProvider(DataProvider):
    name = "geopandas-vector"
    supported_extensions = [
        ".shp", ".geojson", ".json", ".gpkg", ".kml", ".kmz",
        ".gml", ".fgb", ".csv", ".parquet", ".geoparquet"
    ]
    supported_modalities = ["vector"]

    def can_open(self, path: Path) -> bool: ...
    def open(self, path: Path) -> Layer: ...
    def get_file_filter(self) -> str: ...

class VectorProviderPlugin(TkGISPlugin):
    manifest = PluginManifest(
        name="vector-provider",
        display_name="Vector Data Provider",
        version="0.1.0",
        description="Reads and writes vector geospatial data via geopandas",
        author="tkgis",
        license="MIT",
        capabilities=["data_provider"],
    )

    def activate(self, ctx: PluginContext) -> None:
        ctx.register_data_provider(VectorDataProvider())

    def deactivate(self) -> None: ...
```

#### T7.2: Implement the Vector Layer Backend

```python
# src/tkgis/io/vector.py
class VectorLayerData:
    """Wraps a geopandas GeoDataFrame for a vector layer."""

    def __init__(self, gdf: gpd.GeoDataFrame, source_path: str | None = None):
        self._gdf = gdf
        self.source_path = source_path

    @property
    def gdf(self) -> gpd.GeoDataFrame: ...

    @property
    def crs(self) -> CRSDefinition: ...

    @property
    def bounds(self) -> BoundingBox: ...

    @property
    def feature_count(self) -> int: ...

    @property
    def geometry_types(self) -> set[str]: ...

    @property
    def columns(self) -> list[str]: ...

    def get_features_in_bbox(self, bbox: BoundingBox) -> gpd.GeoDataFrame:
        """Spatial query: return features intersecting a bounding box."""
        ...

    def get_features_at_point(self, x: float, y: float,
                               tolerance: float) -> gpd.GeoDataFrame:
        """Point query: return features near a point."""
        ...

    def reproject(self, target_crs: CRSDefinition) -> 'VectorLayerData':
        """Return a new VectorLayerData in the target CRS."""
        ...

    @classmethod
    def from_file(cls, path: str | Path) -> 'VectorLayerData':
        """Load from any geopandas-supported format."""
        ...

    def to_file(self, path: str | Path, driver: str | None = None) -> None:
        """Write to file. Auto-detect driver from extension."""
        ...
```

#### T7.3: Implement the Vector Tile Provider

Render vector features as tiles for the map canvas. This converts geometry to rasterized tile images at the requested zoom level.

```python
# src/tkgis/io/vector_tiles.py
class VectorTileProvider(TileProvider):
    """Rasterizes vector features into tiles for the map canvas."""

    def __init__(self, vector_data: VectorLayerData, style: LayerStyle):
        ...

    def get_tile(self, layer, zoom_level, row, col, tile_size) -> np.ndarray | None:
        """Rasterize features intersecting this tile using PIL drawing."""
        ...
```

Use `PIL.ImageDraw` to rasterize geometries onto tile images. Apply the layer style (fill color, stroke color, stroke width). This is simple but functional — advanced styling can be added later.

#### T7.4: Implement Vector Import/Export Dialogs

- **Import dialog**: File open dialog with filters for all supported vector formats. After selection, show a preview of the first few features and detected CRS. Allow CRS override if auto-detection fails.
- **Export dialog**: File save dialog. Format selection based on extension. Option to reproject to a different CRS on export.

Wire these to the File → Import Layer and File → Export Layer menu items.

#### T7.5: Write Vector I/O Tests

```python
def test_load_shapefile(): ...
def test_load_geojson(): ...
def test_load_geopackage(): ...
def test_crs_detection(): ...
def test_spatial_query_bbox(): ...
def test_spatial_query_point(): ...
def test_reproject_vector(): ...
def test_export_roundtrip(): ...
```

Provide small test fixtures: a 10-feature GeoJSON with points, a 5-polygon shapefile.

### Success Criteria

- [ ] All 8 listed vector formats load successfully (with appropriate test files)
- [ ] CRS is correctly detected and stored in Layer.crs
- [ ] BoundingBox is correctly computed
- [ ] Spatial queries (bbox, point) return correct features
- [ ] Reprojection produces correct coordinates
- [ ] VectorTileProvider generates non-empty tile images
- [ ] Export round-trips data without loss
- [ ] `pytest tests/test_vector.py` — all tests pass

### Produces / Consumes

- **Produces**: VectorDataProvider plugin, VectorLayerData, VectorTileProvider → consumed by TG5 (layer tree), TG12 (spatial queries), TG15 (attribute table)
- **Consumes**: DataProvider ABC from TG2; Layer, CRSDefinition, BoundingBox from TG3; TileProvider ABC from TG4

### Dependencies

| Package | Version | Scope | License | Justification |
|---------|---------|-------|---------|---------------|
| geopandas | >=0.14.0 | runtime | BSD-3-Clause | Core vector data I/O and spatial operations |
| pyogrio | >=0.7.0 | runtime | MIT | Fast vector I/O backend for geopandas |
| pyproj | >=3.6.0 | runtime | MIT | CRS detection and reprojection |

---

## Task Group 8: Raster Data I/O (GRDL Integration)

### Agent Profile

You are a **Python image processing engineer** specializing in remotely sensed imagery, tiled rendering of very large images, and geospatial I/O. You are building the raster data provider for **tkgis**, a desktop GIS application that must handle SAR, EO, multispectral, and other sensor modalities. Read `CLAUDE.md` before starting — it contains all project conventions, constraints, and patterns you must follow.

### Context

tkgis uses **GRDL** for all raster image I/O. GRDL provides format-specific readers with lazy loading — it can read spatial subsets (chips) without loading the full image. This is critical for tkgis because remotely sensed imagery can be 30,000×30,000 pixels or larger.

The raster provider is a **tkgis plugin** that:
1. Registers a `DataProvider` for raster formats
2. Implements `TileProvider` to feed the map canvas with tiled image data
3. Uses GRDL's `ChipExtractor` to plan tile reads and GRDL readers for the actual I/O
4. Handles geolocation via GRDL's geolocation module (SICD, affine, GCP)
5. Applies display transforms (dB conversion, percentile stretch) for visualization

GRDL supports: GeoTIFF, NITF (SICD/SIDD), CPHD, HDF5, JPEG2000, Sentinel-1 SLC, TerraSAR-X, BIOMASS, VIIRS, ASTER.

### Files to Read Before Starting

1. `src/tkgis/plugins/base.py` — TkGISPlugin ABC (from TG2)
2. `src/tkgis/plugins/providers.py` — DataProvider ABC (from TG2)
3. `src/tkgis/canvas/tiles.py` — TileProvider ABC, TileKey (from TG4)
4. `src/tkgis/models/layers.py` — Layer, LayerStyle (from TG3)
5. `src/tkgis/models/crs.py` — CRSDefinition (from TG3)
6. GRDL `grdl/IO/__init__.py` — open_image, open_sar, etc.
7. GRDL `grdl/IO/base.py` — ImageReader ABC (read_chip, get_shape, metadata)
8. GRDL `grdl/geolocation/base.py` — Geolocation ABC
9. GRDL `grdl/data_prep/chip_extractor.py` — ChipExtractor
10. GRDL `grdl/image_processing/intensity.py` — ToDecibels, PercentileStretch

### Constraints

- All raster I/O MUST go through GRDL — do **NOT** use rasterio, PIL, or other libraries to read geospatial rasters directly
- Do **NOT** load the full image into memory for large files — always use chip-based reading
- The tile provider must generate pyramid levels by downsampling — GRDL readers provide native resolution only
- Display transforms (dB, stretch) must be applied at tile read time, not stored permanently
- SAR complex data (complex64) must be converted to magnitude before display: `np.abs(complex_data)`
- Multi-band imagery: default RGB mapping for 3+ bands, grayscale for 1 band

### Tasks

#### T8.1: Implement the Raster Data Provider Plugin

```python
# src/tkgis/plugins/builtin/raster_provider.py
class RasterDataProvider(DataProvider):
    name = "grdl-raster"
    supported_extensions = [
        ".tif", ".tiff",     # GeoTIFF
        ".nitf", ".ntf",     # NITF (SICD/SIDD)
        ".h5", ".hdf5",      # HDF5 (CPHD, VIIRS, ASTER)
        ".jp2",              # JPEG2000 (Sentinel-2)
        ".xml",              # TerraSAR-X product descriptor
        ".safe",             # Sentinel-1 SAFE
    ]
    supported_modalities = ["raster"]

    def can_open(self, path: Path) -> bool:
        """Check extension and attempt GRDL open."""
        ...

    def open(self, path: Path) -> Layer:
        """Open with GRDL, extract metadata, create Layer."""
        ...

    def get_file_filter(self) -> str: ...
```

The `open()` method must:
1. Try `grdl.IO.open_sar()` first (for NITF, HDF5, XML), then `grdl.IO.open_image()`, then modality-specific openers
2. Extract metadata: shape, bands, dtype, CRS (from geolocation), bounds
3. Create a `Layer` with the reader stored in `layer.metadata["_reader"]`
4. Create and register a `RasterTileProvider` for this layer

#### T8.2: Implement the Raster Tile Provider

```python
# src/tkgis/io/raster_tiles.py
class RasterTileProvider(TileProvider):
    """Provides tiled access to GRDL raster data for the map canvas."""

    def __init__(self, reader: ImageReader, geolocation: Geolocation | None,
                 layer: Layer):
        self._reader = reader
        self._geolocation = geolocation
        self._layer = layer
        self._pyramid = self._build_pyramid_info()

    def _build_pyramid_info(self) -> list[dict]:
        """Compute tile grid dimensions for each zoom level.

        Level 0 = full resolution (native).
        Level N = 2^N downsampling.
        Max level = smallest level where entire image fits in one tile.
        """
        ...

    def get_tile(self, layer, zoom_level, row, col, tile_size=256) -> np.ndarray | None:
        """Read a chip from the GRDL reader, downsample, apply display transform."""
        # 1. Compute the image-space region for this tile at this zoom level
        # 2. Read chip via reader.read_chip(row_start, row_end, col_start, col_end)
        # 3. Downsample to tile_size x tile_size
        # 4. Apply display transform (complex→magnitude→dB→stretch→uint8 RGB)
        # 5. Return as uint8 RGB array (tile_size, tile_size, 3)
        ...

    def _apply_display_transform(self, data: np.ndarray, style: LayerStyle) -> np.ndarray:
        """Convert raw sensor data to display-ready uint8 RGB."""
        # Complex → magnitude
        # Float → dB (if SAR)
        # Percentile stretch → [0, 255]
        # Band mapping (RGB or colormap)
        ...

    def get_num_zoom_levels(self, layer) -> int: ...
    def get_tile_grid(self, layer, zoom_level) -> tuple[int, int]: ...
```

Key implementation detail: For very large images, the chip read at low zoom levels would span the entire image. Instead, implement **pyramid decimation**: at zoom level N, read a chip at level 0 size but subsample by 2^N using `scipy.ndimage.zoom` or simple striding (`data[::step, ::step]`).

#### T8.3: Implement Geolocation Integration

Extract geolocation from GRDL readers and use it to place rasters in map coordinates.

```python
# src/tkgis/io/raster_geoloc.py
class RasterGeolocationBridge:
    """Bridges GRDL geolocation to tkgis coordinate system."""

    @staticmethod
    def extract_geolocation(reader: ImageReader) -> Geolocation | None:
        """Try to get geolocation from reader metadata.

        Priority:
        1. SICD → SICDGeolocation
        2. GeoTIFF/affine → AffineGeolocation
        3. GCPs → GCPGeolocation
        4. None (no georeferencing)
        """
        ...

    @staticmethod
    def compute_bounds(reader: ImageReader,
                       geolocation: Geolocation) -> BoundingBox:
        """Compute geographic bounds by transforming image corners."""
        ...

    @staticmethod
    def extract_crs(reader: ImageReader,
                    geolocation: Geolocation) -> CRSDefinition:
        """Extract CRS from geolocation/reader metadata."""
        ...
```

#### T8.4: Implement Raster Metadata Extraction

```python
# src/tkgis/io/raster_metadata.py
class RasterMetadataExtractor:
    """Extracts display-friendly metadata from GRDL readers."""

    @staticmethod
    def extract(reader: ImageReader) -> dict:
        """Extract metadata as a flat dict for the Properties dialog."""
        return {
            "rows": ...,
            "cols": ...,
            "bands": ...,
            "dtype": ...,
            "modality": ...,          # SAR, EO, MSI, etc.
            "sensor": ...,            # Sensor name if available
            "acquisition_date": ...,  # If available in metadata
            "pixel_spacing": ...,     # If available
            # SAR-specific
            "polarization": ...,
            "frequency": ...,
            "look_direction": ...,
        }
```

#### T8.5: Implement Band Visualization Controls

For multi-band imagery, provide utilities to create display images:

```python
# src/tkgis/io/raster_display.py
class RasterDisplayEngine:
    """Converts raw raster data to display-ready RGB images."""

    @staticmethod
    def to_display_rgb(data: np.ndarray, style: LayerStyle) -> np.ndarray:
        """Convert N-band data to uint8 RGB for display.

        Strategies:
        - 1 band: grayscale or colormap
        - 3 bands: direct RGB mapping (with stretch)
        - N bands: user-selected band mapping to RGB
        - Complex: magnitude → dB → stretch → grayscale/colormap
        """
        ...

    @staticmethod
    def apply_colormap(data_2d: np.ndarray, colormap_name: str) -> np.ndarray:
        """Apply a matplotlib colormap to single-band data."""
        ...

    @staticmethod
    def percentile_stretch(data: np.ndarray,
                           plow: float = 2.0, phigh: float = 98.0) -> np.ndarray:
        """Stretch data to [0, 255] using percentile clipping."""
        ...
```

#### T8.6: Write Raster I/O Tests

```python
def test_open_geotiff(): ...
def test_open_sicd_nitf(): ...
def test_tile_provider_returns_rgb(): ...
def test_tile_provider_pyramid_levels(): ...
def test_complex_sar_display(): ...
def test_multiband_rgb_mapping(): ...
def test_geolocation_bounds_extraction(): ...
def test_colormap_application(): ...
```

Provide a small test GeoTIFF (100x100, 3-band, with CRS).

### Success Criteria

- [ ] GeoTIFF files load and display correctly
- [ ] NITF/SICD files load via GRDL's SAR readers
- [ ] Tile provider generates correct RGB tiles at multiple zoom levels
- [ ] Complex SAR data displays as magnitude image
- [ ] Multi-band imagery supports configurable RGB band mapping
- [ ] Geolocation correctly places rasters in map coordinates
- [ ] Large images (>10,000 pixels) don't cause memory issues (tiled reading works)
- [ ] `pytest tests/test_raster.py` — all tests pass

### Produces / Consumes

- **Produces**: RasterDataProvider plugin, RasterTileProvider, RasterDisplayEngine → consumed by TG11 (processing), TG5 (layer properties)
- **Consumes**: DataProvider ABC from TG2; TileProvider ABC from TG4; Layer, LayerStyle, CRSDefinition from TG3; GRDL library (external)

### Dependencies

| Package | Version | Scope | License | Justification |
|---------|---------|-------|---------|---------------|
| grdl | >=0.1.0 | runtime | MIT | Core raster I/O for all sensor formats |
| numpy | >=1.20.0 | runtime | BSD-3-Clause | Array operations for tile data |
| scipy | >=1.7.0 | runtime | BSD-3-Clause | Image resampling for pyramid decimation |
| matplotlib | >=3.7.0 | runtime | PSF (MIT-compatible) | Colormap application for raster display |

---

## Task Group 9: Temporal Data Management

### Agent Profile

You are a **Python data engineer** specializing in time-series geospatial data, temporal indexing, and animation frameworks. You are building the temporal data layer for **tkgis**, a desktop GIS application. Read `CLAUDE.md` before starting — it contains all project conventions, constraints, and patterns you must follow.

### Context

Remotely sensed imagery often has a temporal dimension — satellite revisits produce time-series stacks over the same geographic area. tkgis must support:

1. **Temporal raster layers**: A sequence of co-registered raster images indexed by acquisition time
2. **Temporal vector layers**: Feature collections with timestamps (e.g., ship tracks, change detection polygons)
3. **Time slider**: A UI widget that scrubs through time, updating the displayed data
4. **Temporal filtering**: Show only features/imagery within a time window

This task group builds the data model and the time slider widget. It does NOT implement temporal analysis algorithms (that's TG14).

### Files to Read Before Starting

1. `src/tkgis/models/layers.py` — Layer model, time fields (from TG3)
2. `src/tkgis/models/events.py` — EventBus, TIME_STEP_CHANGED (from TG3)
3. `src/tkgis/panels/base.py` — BasePanel ABC (from TG1)

### Constraints

- Use `datetime` and `pandas.Timestamp` for time representation — do NOT invent a custom time type
- Time slider must be performant with 1000+ time steps (e.g., daily imagery over 3 years)
- Temporal layers re-use the same Layer model with populated `time_steps` field — do NOT create separate model classes
- Do **NOT** implement temporal analysis — only data management and the time slider UI

### Tasks

#### T9.1: Implement the Temporal Layer Manager

```python
# src/tkgis/temporal/manager.py
class TemporalLayerManager:
    """Manages temporal indexing for layers with time dimensions."""

    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        self._current_time: datetime | None = None
        self._time_window: timedelta | None = None  # For windowed display

    def get_time_range(self, layer: Layer) -> tuple[datetime, datetime] | None:
        """Return the min/max time for a temporal layer."""
        ...

    def get_time_steps(self, layer: Layer) -> list[datetime]:
        """Return all discrete time steps for a temporal layer."""
        ...

    def get_nearest_step(self, layer: Layer, target: datetime) -> datetime:
        """Find the closest available time step to the target."""
        ...

    def set_current_time(self, t: datetime) -> None:
        """Update current time and emit TIME_STEP_CHANGED event."""
        ...

    def set_time_window(self, window: timedelta | None) -> None:
        """Set a time window for display (e.g., show ±7 days)."""
        ...

    def get_active_data_index(self, layer: Layer) -> int | None:
        """Return the index of the time step closest to current_time."""
        ...
```

#### T9.2: Implement the Time Slider Panel

```python
# src/tkgis/panels/time_slider.py
class TimeSliderPanel(BasePanel):
    name = "time_slider"
    title = "Time"
    dock_position = "bottom"
    default_visible = False  # Only show when temporal layers exist

    def create_widget(self, parent) -> ctk.CTkFrame:
        """Build time slider with:
        - Slider (CTkSlider) spanning the time range
        - Current time label
        - Play/Pause button for animation
        - Speed control
        - Time window selector (instant, ±1 day, ±7 days, ±30 days)
        """
        ...

    def _on_slider_moved(self, value) -> None: ...
    def _play_animation(self) -> None: ...
    def _stop_animation(self) -> None: ...
```

Animation uses `widget.after(interval, callback)` to step through time steps at configurable speed (0.5s to 5s per step).

#### T9.3: Implement Temporal Raster Stack

```python
# src/tkgis/temporal/raster_stack.py
class TemporalRasterStack:
    """Manages a stack of co-registered rasters indexed by time."""

    def __init__(self, layers: list[Layer]):
        """Sort layers by acquisition time, validate co-registration."""
        ...

    @classmethod
    def from_directory(cls, directory: Path,
                       pattern: str = "*.tif") -> 'TemporalRasterStack':
        """Load a time series from a directory of images.
        Extract timestamps from filenames or metadata.
        """
        ...

    def get_frame_at_time(self, t: datetime) -> Layer:
        """Return the layer closest to time t."""
        ...

    def get_time_series_at_pixel(self, row: int, col: int) -> np.ndarray:
        """Extract a time series for a single pixel across all frames."""
        ...
```

#### T9.4: Write Temporal Tests

```python
def test_temporal_manager_time_steps(): ...
def test_temporal_manager_nearest_step(): ...
def test_time_slider_animation(): ...
def test_temporal_raster_stack_from_directory(): ...
def test_temporal_raster_pixel_time_series(): ...
```

### Success Criteria

- [ ] TemporalLayerManager correctly indexes time steps and finds nearest
- [ ] Time slider widget updates current time and emits events
- [ ] Animation plays through time steps at configurable speed
- [ ] TemporalRasterStack loads a directory of images as a time series
- [ ] `pytest tests/test_temporal.py` — all tests pass

### Produces / Consumes

- **Produces**: TemporalLayerManager, TimeSliderPanel, TemporalRasterStack → consumed by TG14 (spatiotemporal analysis), TG8 (temporal raster loading)
- **Consumes**: Layer, EventBus from TG3; BasePanel from TG1

---

## Task Group 10: Navigation & Measurement Tools

### Agent Profile

You are a **Python GUI developer** specializing in interactive map tools, measurement systems, and drawing interactions. You are building the navigation and measurement toolkit for **tkgis**, a desktop GIS application. Read `CLAUDE.md` before starting — it contains all project conventions, constraints, and patterns you must follow.

### Context

Users interact with the map through tools. TG4 created the Pan and Zoom tools. This task group adds the full suite of navigation, measurement, and identification tools. Each tool extends `BaseTool` (from TG3) and interacts with the map canvas (from TG4).

### Files to Read Before Starting

1. `src/tkgis/models/tools.py` — BaseTool, ToolManager, ToolMode (from TG3)
2. `src/tkgis/canvas/map_canvas.py` — MapCanvas (from TG4)
3. `src/tkgis/crs/engine.py` — CRSEngine, geodesic distance/area (from TG6)
4. `src/tkgis/models/events.py` — EventBus (from TG3)

### Constraints

- Do **NOT** modify the map canvas internals — interact through its public API
- All measurement results must be displayed in appropriate units (meters/km for distance, m²/km²/hectares for area)
- Drawing overlays (measurement lines, rubber bands) use canvas temporary items that are cleared when the tool deactivates

### Tasks

#### T10.1: Implement the Distance Measurement Tool

```python
# src/tkgis/tools/measure.py
class DistanceTool(BaseTool):
    name = "measure_distance"
    mode = ToolMode.MEASURE_DISTANCE
    cursor = "crosshair"

    # Click to add vertices, double-click to finish
    # Display running total distance along the polyline
    # Show segment distances as labels on the canvas
    # Geodesic distance via CRSEngine.compute_distance()
```

Render a rubber-band line following the cursor. Display total distance in the status bar. Show per-segment labels on the canvas.

#### T10.2: Implement the Area Measurement Tool

```python
class AreaTool(BaseTool):
    name = "measure_area"
    mode = ToolMode.MEASURE_AREA
    cursor = "crosshair"

    # Click to add polygon vertices, double-click to close
    # Display area in the status bar
    # Geodesic area via CRSEngine.compute_area()
    # Show semi-transparent polygon fill while drawing
```

#### T10.3: Implement the Identify Tool

```python
# src/tkgis/tools/identify.py
class IdentifyTool(BaseTool):
    name = "identify"
    mode = ToolMode.IDENTIFY
    cursor = "question_arrow"

    # Click on map → query all visible layers at that point
    # For vector: return feature attributes
    # For raster: return pixel values at all bands
    # Display results in a popup or the Properties panel
```

Query vector layers via `VectorLayerData.get_features_at_point()`. Query raster layers by converting screen→image coordinates and reading the pixel value.

#### T10.4: Implement the Select Tool

```python
# src/tkgis/tools/select.py
class SelectTool(BaseTool):
    name = "select"
    mode = ToolMode.SELECT
    cursor = "arrow"

    # Click to select feature nearest to cursor
    # Drag to draw selection rectangle
    # Shift+click to add to selection
    # Ctrl+click to toggle selection
    # Selected features highlighted with yellow stroke
```

#### T10.5: Implement Keyboard Navigation

Register keyboard shortcuts in the map canvas:

| Key | Action |
|-----|--------|
| Arrow keys | Pan (50px per press) |
| +/= | Zoom in |
| -/_ | Zoom out |
| Home | Zoom to full extent |
| Space (hold) | Temporary pan tool |
| Escape | Cancel current tool action |
| Delete | Remove selected features |

#### T10.6: Implement the Scale Bar Widget

A scale bar overlay on the map canvas that shows distance at the current zoom level.

```python
# src/tkgis/canvas/overlays.py (add to existing)
class ScaleBar:
    """Draws a scale bar on the map canvas."""
    def draw(self, canvas, transform, crs): ...
```

The scale bar auto-adjusts its length to show round numbers (100m, 500m, 1km, 5km, etc.).

#### T10.7: Write Tool Tests

```python
def test_distance_tool_two_points(): ...
def test_distance_tool_multipoint(): ...
def test_area_tool_triangle(): ...
def test_identify_tool_raster(): ...
def test_identify_tool_vector(): ...
def test_select_tool_rectangle(): ...
def test_keyboard_navigation(): ...
```

### Success Criteria

- [ ] Distance tool shows correct geodesic distance between clicked points
- [ ] Area tool shows correct geodesic area for drawn polygons
- [ ] Identify tool returns pixel values for raster and attributes for vector
- [ ] Select tool highlights selected features
- [ ] Keyboard navigation works (pan, zoom, shortcuts)
- [ ] Scale bar renders with correct distance labels
- [ ] `pytest tests/test_tools.py` — all tests pass

### Produces / Consumes

- **Produces**: DistanceTool, AreaTool, IdentifyTool, SelectTool, ScaleBar → consumed by TG16 (toolbar wiring)
- **Consumes**: BaseTool, ToolManager from TG3; MapCanvas from TG4; CRSEngine from TG6; VectorLayerData from TG7

---

## Task Group 11: Image Processing via grdl-runtime Workflows

### Agent Profile

You are a **Python image processing engineer** specializing in SAR imagery, workflow orchestration, and GPU-accelerated processing. You are building the processing integration for **tkgis**, a desktop GIS application that uses **grdl-runtime** as its workflow execution engine. Read `CLAUDE.md` before starting — it contains all project conventions, constraints, and patterns you must follow.

### Context

tkgis delegates all image processing to **grdl-runtime**. The runtime provides:
- A fluent `Workflow` builder API for defining processing chains
- A processor catalog for discovering available algorithms
- GPU-accelerated execution with CPU fallback
- Progress callbacks for UI updates

tkgis wraps grdl-runtime with:
1. A **Processing Toolbox** panel listing all available processors from the catalog
2. A **Workflow Builder** UI for visually composing processing chains
3. A **Run dialog** for configuring and executing workflows
4. **Live preview** that applies the workflow to the visible map extent in real-time

### Files to Read Before Starting

1. `src/tkgis/io/raster_tiles.py` — RasterTileProvider (from TG8)
2. `src/tkgis/models/layers.py` — Layer (from TG3)
3. `src/tkgis/panels/base.py` — BasePanel (from TG1)
4. `src/tkgis/models/events.py` — EventBus (from TG3)
5. grdl-runtime `grdl_rt/__init__.py` — Public API exports
6. grdl-runtime `grdl_rt/execution/builder.py` — Workflow builder
7. grdl-runtime `grdl_rt/execution/discovery.py` — Processor discovery
8. grdl-runtime `grdl_rt/catalog/models.py` — Artifact model

### Constraints

- All processing MUST go through grdl-runtime's `Workflow` builder — do **NOT** call GRDL processors directly
- Processing must run in a background thread — never block the GUI
- Progress must be reported to the status bar via `EventBus.emit(PROGRESS_UPDATED, ...)`
- Results must be added as new layers — do NOT modify the input layer's data
- The processor catalog is read-only — tkgis does not add processors to the catalog

### Tasks

#### T11.1: Implement the Processing Toolbox Panel

```python
# src/tkgis/panels/toolbox.py
class ProcessingToolboxPanel(BasePanel):
    name = "processing_toolbox"
    title = "Processing"
    dock_position = "right"
    default_visible = False

    def create_widget(self, parent) -> ctk.CTkFrame:
        """Build toolbox with:
        - Search entry (filter by name)
        - Category tree (Filters, Intensity, SAR, Detection, etc.)
        - Processor list (name, version, description)
        - Double-click to open Run Dialog
        """
        ...

    def _populate_catalog(self) -> None:
        """Query grdl-runtime discovery for all available processors."""
        from grdl_rt import discover_processors, filter_processors
        ...

    def _on_processor_selected(self, event) -> None: ...
    def _on_processor_double_click(self, event) -> None: ...
```

Organize processors by `ProcessorCategory` from `grdl.vocabulary` and by `ImageModality` tags.

#### T11.2: Implement the Workflow Builder Panel

```python
# src/tkgis/panels/workflow_builder.py
class WorkflowBuilderPanel(BasePanel):
    name = "workflow_builder"
    title = "Workflow"
    dock_position = "right"
    default_visible = False

    def create_widget(self, parent) -> ctk.CTkFrame:
        """Build workflow composer:
        - Step list (ordered, drag-to-reorder or up/down buttons)
        - Add Step button (opens processor catalog selector)
        - Per-step parameter editors (auto-generated from processor __param_specs__)
        - Remove Step button
        - Run / Preview buttons
        - Save / Load Workflow (YAML)
        """
        ...

    def _add_step(self, processor_class: type) -> None: ...
    def _remove_step(self, index: int) -> None: ...
    def _build_param_editor(self, step_frame, param_specs: dict) -> None:
        """Auto-generate parameter widgets from processor parameter specs.

        Range → CTkSlider with min/max
        Options → CTkComboBox with allowed values
        bool → CTkSwitch
        int/float → CTkEntry with validation
        """
        ...

    def _build_workflow(self) -> 'Workflow':
        """Construct a grdl-runtime Workflow from the current step list."""
        from grdl_rt import Workflow
        ...
```

#### T11.3: Implement the Processing Execution Engine

```python
# src/tkgis/processing/executor.py
class ProcessingExecutor:
    """Runs grdl-runtime workflows with tkgis integration."""

    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        self._thread: threading.Thread | None = None
        self._cancel_flag = threading.Event()

    def execute(self, workflow: 'Workflow',
                input_layer: Layer,
                output_name: str = "Processed") -> None:
        """Run a workflow in a background thread."""
        self._thread = threading.Thread(
            target=self._run,
            args=(workflow, input_layer, output_name),
            daemon=True
        )
        self._thread.start()

    def _run(self, workflow, input_layer, output_name):
        """Background execution with progress reporting."""
        # 1. Get the GRDL reader from the input layer
        # 2. Build workflow with .reader(...).chip("center", size=...)
        # 3. Execute with progress_callback that emits PROGRESS_UPDATED
        # 4. On completion, create a new Layer from the result
        # 5. Emit LAYER_ADDED event
        ...

    def cancel(self) -> None: ...

    def execute_preview(self, workflow, input_layer,
                        visible_extent: BoundingBox) -> np.ndarray:
        """Run workflow on just the visible extent for live preview."""
        ...
```

#### T11.4: Implement the Run Dialog

```python
# src/tkgis/processing/run_dialog.py
class ProcessingRunDialog(ctk.CTkToplevel):
    """Dialog for configuring and running a single processor or workflow."""

    def __init__(self, parent, processor_or_workflow,
                 input_layers: list[Layer]):
        ...
        # Input layer selector (dropdown)
        # Parameter editors (auto-generated from param specs)
        # Output layer name entry
        # Preview checkbox (applies to visible extent)
        # Run / Cancel buttons
        # Progress bar
```

#### T11.5: Implement Workflow Save/Load

```python
# src/tkgis/processing/workflow_io.py
def save_workflow(workflow_steps: list[dict], path: Path) -> None:
    """Save workflow definition as YAML."""
    ...

def load_workflow(path: Path) -> list[dict]:
    """Load workflow definition from YAML."""
    ...
```

Use grdl-runtime's `WorkflowDefinition` serialization format so workflows are interchangeable between tkgis and grdl-runtime CLI.

#### T11.6: Write Processing Tests

```python
def test_catalog_discovery(): ...
def test_param_editor_generation(): ...
def test_workflow_build_from_steps(): ...
def test_processing_executor_background(): ...
def test_workflow_save_load_roundtrip(): ...
```

### Success Criteria

- [ ] Processing Toolbox lists all grdl-runtime catalog processors grouped by category
- [ ] Workflow Builder creates valid grdl-runtime Workflow objects
- [ ] Parameter editors auto-generate from processor specs (sliders, dropdowns, entries)
- [ ] Processing executes in background thread without freezing GUI
- [ ] Progress bar updates during processing
- [ ] Result is added as a new layer in the project
- [ ] Workflow save/load round-trips correctly
- [ ] `pytest tests/test_processing.py` — all tests pass

### Produces / Consumes

- **Produces**: ProcessingToolboxPanel, WorkflowBuilderPanel, ProcessingExecutor → consumed by TG16
- **Consumes**: Layer, EventBus from TG3; BasePanel from TG1; grdl-runtime Workflow API (external); RasterTileProvider from TG8

### Dependencies

| Package | Version | Scope | License | Justification |
|---------|---------|-------|---------|---------------|
| grdl-runtime | >=0.1.0 | runtime | MIT | Workflow execution engine for image processing |
| PyYAML | >=6.0 | runtime | MIT | Workflow definition serialization |

---

## Task Group 12: Spatial Query & Selection Tools

### Agent Profile

You are a **Python geospatial developer** specializing in spatial indexing, query engines, and interactive selection. You are building the spatial query system for **tkgis**, a desktop GIS application. Read `CLAUDE.md` before starting — it contains all project conventions, constraints, and patterns you must follow.

### Context

Spatial queries let users interrogate data by location. tkgis needs:
- Point queries (identify features at a click location)
- Rectangular queries (select features in a box)
- Polygon queries (select features in a drawn polygon)
- Buffer queries (select features within N meters of a point/line)
- Expression queries (select features matching attribute conditions)

These build on geopandas' spatial indexing (R-tree via `sindex`) and the vector layer's `get_features_in_bbox()` / `get_features_at_point()` methods from TG7.

### Files to Read Before Starting

1. `src/tkgis/io/vector.py` — VectorLayerData (from TG7)
2. `src/tkgis/models/tools.py` — BaseTool (from TG3)
3. `src/tkgis/crs/engine.py` — CRSEngine (from TG6)
4. `src/tkgis/models/events.py` — EventBus (from TG3)

### Constraints

- Use geopandas/shapely spatial predicates — do **NOT** implement custom spatial indexing
- Query results must be selectable (highlight on map) and exportable
- Expression queries must be safe — do **NOT** use `eval()` on user input; use a restricted expression parser

### Tasks

#### T12.1: Implement the Spatial Query Engine

```python
# src/tkgis/query/engine.py
class SpatialQueryEngine:
    """Executes spatial queries against vector layers."""

    def query_point(self, layers: list[Layer], x: float, y: float,
                    tolerance: float = 10.0) -> list[QueryResult]: ...

    def query_bbox(self, layers: list[Layer],
                   bbox: BoundingBox) -> list[QueryResult]: ...

    def query_polygon(self, layers: list[Layer],
                      polygon: list[tuple[float, float]]) -> list[QueryResult]: ...

    def query_buffer(self, layers: list[Layer],
                     geometry, distance_m: float) -> list[QueryResult]: ...

    def query_expression(self, layer: Layer,
                         expression: str) -> QueryResult:
        """Attribute filter: 'population > 10000 AND name LIKE \"New%\"'"""
        ...

@dataclass
class QueryResult:
    layer: Layer
    features: gpd.GeoDataFrame
    count: int
```

#### T12.2: Implement the Expression Parser

A safe subset of SQL WHERE syntax for attribute queries:

```python
# src/tkgis/query/expression.py
class ExpressionParser:
    """Parses safe attribute filter expressions.

    Supported: =, !=, <, >, <=, >=, LIKE, IN, AND, OR, NOT, IS NULL, IS NOT NULL
    Translates to pandas query syntax.
    """
    def parse(self, expression: str) -> pd.Series:
        """Return a boolean mask for the expression."""
        ...
```

#### T12.3: Implement the Query Dialog

```python
# src/tkgis/query/dialog.py
class QueryDialog(ctk.CTkToplevel):
    """Dialog for building and executing spatial/attribute queries."""

    # Tab 1: Spatial query (draw bbox/polygon on map)
    # Tab 2: Attribute query (expression builder with column names, operators)
    # Results count display
    # Select / Zoom to Results / Export buttons
```

#### T12.4: Write Query Tests

```python
def test_point_query(): ...
def test_bbox_query(): ...
def test_polygon_query(): ...
def test_expression_parser_simple(): ...
def test_expression_parser_like(): ...
def test_expression_parser_injection_safe(): ...
```

### Success Criteria

- [ ] Point query returns features near a coordinate
- [ ] Bbox query returns features intersecting a rectangle
- [ ] Expression parser handles AND/OR/comparisons correctly
- [ ] Expression parser rejects dangerous input (no eval, no code injection)
- [ ] Query results are selectable and highlight on map
- [ ] `pytest tests/test_query.py` — all tests pass

### Produces / Consumes

- **Produces**: SpatialQueryEngine, ExpressionParser, QueryDialog → consumed by TG10 (identify/select tools), TG15 (attribute table filtering)
- **Consumes**: VectorLayerData from TG7; CRSEngine from TG6; BaseTool from TG3

---

## Task Group 13: Charting & Plotting Widgets

### Agent Profile

You are a **Python data visualization developer** specializing in matplotlib integration, interactive charts, and scientific plotting. You are building the charting system for **tkgis**, a desktop GIS application. Read `CLAUDE.md` before starting — it contains all project conventions, constraints, and patterns you must follow.

### Context

tkgis needs embedded charts and plots for data analysis. We use **matplotlib** with its tkinter backend (`FigureCanvasTkAgg`) to embed interactive plots directly in the application. Charts are displayed in a dockable bottom panel and respond to map interactions (e.g., clicking a pixel shows its spectral profile).

### Files to Read Before Starting

1. `src/tkgis/panels/base.py` — BasePanel ABC (from TG1)
2. `src/tkgis/models/events.py` — EventBus (from TG3)
3. `src/tkgis/models/layers.py` — Layer, LayerStyle (from TG3)

### Constraints

- Use **matplotlib** with `FigureCanvasTkAgg` — do **NOT** add plotly, bokeh, or other heavy plotting libraries
- Charts must be non-blocking — use `fig.canvas.draw_idle()` for deferred rendering
- Chart panel must support multiple chart types via a tab interface
- Charts must respond to theme changes (dark/light background)

### Tasks

#### T13.1: Implement the Chart Framework

```python
# src/tkgis/charts/base.py
class BaseChart(ABC):
    """Base class for all embeddable charts."""

    name: str
    title: str

    @abstractmethod
    def create_figure(self) -> Figure: ...

    @abstractmethod
    def update(self, data: Any) -> None: ...

    def set_theme(self, dark: bool) -> None:
        """Apply dark/light theme to matplotlib figure."""
        ...

# src/tkgis/charts/container.py
class ChartContainer(ctk.CTkFrame):
    """Embeds a matplotlib Figure in a tkinter frame."""

    def __init__(self, parent, chart: BaseChart):
        ...
        self._figure = chart.create_figure()
        self._canvas = FigureCanvasTkAgg(self._figure, master=self)
        self._toolbar = NavigationToolbar2Tk(self._canvas, self)
```

#### T13.2: Implement the Spectral Profile Chart

For multispectral/hyperspectral imagery: click a pixel → show band values as a line chart.

```python
# src/tkgis/charts/spectral.py
class SpectralProfileChart(BaseChart):
    name = "spectral_profile"
    title = "Spectral Profile"

    def update(self, band_values: np.ndarray, wavelengths: list[float] | None = None):
        """Plot pixel values across bands."""
        ...
```

#### T13.3: Implement the Histogram Chart

Show the value distribution for a raster band or vector attribute.

```python
# src/tkgis/charts/histogram.py
class HistogramChart(BaseChart):
    name = "histogram"
    title = "Histogram"

    def update(self, data: np.ndarray, bins: int = 256, label: str = ""):
        """Plot value distribution."""
        ...
```

#### T13.4: Implement the Scatter Plot Chart

For comparing two attributes or two bands.

```python
# src/tkgis/charts/scatter.py
class ScatterPlotChart(BaseChart):
    name = "scatter"
    title = "Scatter Plot"

    def update(self, x: np.ndarray, y: np.ndarray,
               xlabel: str = "", ylabel: str = ""):
        ...
```

#### T13.5: Implement the Chart Panel

```python
# src/tkgis/panels/chart_panel.py
class ChartPanel(BasePanel):
    name = "charts"
    title = "Charts"
    dock_position = "bottom"
    default_visible = False

    def create_widget(self, parent) -> ctk.CTkFrame:
        """Tabbed chart container:
        - Tab per chart type (Spectral, Histogram, Scatter, Time Series)
        - Chart selector dropdown if multiple charts of same type
        - Auto-updates when user clicks on map (for spectral profile)
        """
        ...
```

#### T13.6: Implement the Time Series Chart

For temporal layers: plot pixel value over time at a clicked location.

```python
# src/tkgis/charts/time_series.py
class TimeSeriesChart(BaseChart):
    name = "time_series"
    title = "Time Series"

    def update(self, times: list[datetime], values: np.ndarray, label: str = ""):
        """Plot values over time with datetime x-axis."""
        ...
```

#### T13.7: Write Chart Tests

```python
def test_chart_container_embeds_figure(): ...
def test_spectral_profile_updates(): ...
def test_histogram_renders(): ...
def test_scatter_plot_renders(): ...
def test_time_series_renders(): ...
def test_dark_theme_applied(): ...
```

### Success Criteria

- [ ] matplotlib figures embed in tkinter frames without errors
- [ ] Spectral profile chart shows band values for a pixel
- [ ] Histogram chart renders value distribution
- [ ] Scatter plot renders two-variable comparison
- [ ] Time series chart renders with datetime x-axis
- [ ] Charts respond to dark/light theme switching
- [ ] `pytest tests/test_charts.py` — all tests pass

### Produces / Consumes

- **Produces**: ChartPanel, SpectralProfileChart, HistogramChart, ScatterPlotChart, TimeSeriesChart → consumed by TG14 (spatiotemporal analysis), TG16 (app integration)
- **Consumes**: BasePanel from TG1; EventBus from TG3; matplotlib (external)

### Dependencies

| Package | Version | Scope | License | Justification |
|---------|---------|-------|---------|---------------|
| matplotlib | >=3.7.0 | runtime | PSF (MIT-compatible) | Plotting and chart rendering with tkinter backend |

---

## Task Group 14: Spatiotemporal Analysis Tools

### Agent Profile

You are a **Python data scientist** specializing in spatiotemporal analysis, change detection, and time-series remote sensing. You are building the analysis toolkit for **tkgis**, a desktop GIS application. Read `CLAUDE.md` before starting — it contains all project conventions, constraints, and patterns you must follow.

### Context

tkgis aims to rival QGIS/ArcPro in analytical capability. This task group implements spatiotemporal analysis tools that operate on temporal raster stacks and vector layers. Analyses run through grdl-runtime workflows where possible, and fall back to direct numpy/scipy for novel algorithms.

### Files to Read Before Starting

1. `src/tkgis/temporal/manager.py` — TemporalLayerManager (from TG9)
2. `src/tkgis/temporal/raster_stack.py` — TemporalRasterStack (from TG9)
3. `src/tkgis/processing/executor.py` — ProcessingExecutor (from TG11)
4. `src/tkgis/charts/time_series.py` — TimeSeriesChart (from TG13)
5. `src/tkgis/models/layers.py` — Layer (from TG3)

### Constraints

- Heavy computation MUST run in background threads — never freeze the GUI
- Results must be new layers (raster or vector) — do NOT modify input data
- Use grdl-runtime workflows for processing chains where possible
- Use numpy/scipy for algorithms not available in the GRDL processor catalog
- All results must include metadata documenting the analysis parameters

### Tasks

#### T14.1: Implement Pixel Time Series Extraction

```python
# src/tkgis/analysis/time_series.py
class PixelTimeSeriesAnalyzer:
    """Extracts and analyzes time series at individual pixels or regions."""

    def extract_point(self, stack: TemporalRasterStack,
                      row: int, col: int) -> pd.DataFrame:
        """Extract time series at a single pixel. Return DataFrame with time index."""
        ...

    def extract_region(self, stack: TemporalRasterStack,
                       bbox: BoundingBox) -> pd.DataFrame:
        """Extract mean time series for a region."""
        ...

    def compute_statistics(self, series: pd.DataFrame) -> dict:
        """Compute temporal statistics: mean, std, trend, seasonality."""
        ...
```

#### T14.2: Implement Change Detection

```python
# src/tkgis/analysis/change_detection.py
class ChangeDetector:
    """Detects changes between two raster layers or temporal stack frames."""

    def difference(self, layer_a: Layer, layer_b: Layer) -> Layer:
        """Simple image differencing. Returns difference layer."""
        ...

    def ratio(self, layer_a: Layer, layer_b: Layer) -> Layer:
        """Log ratio change detection (for SAR)."""
        ...

    def threshold_change(self, diff_layer: Layer,
                         threshold: float) -> Layer:
        """Binary change mask from a difference layer."""
        ...
```

#### T14.3: Implement Zonal Statistics

```python
# src/tkgis/analysis/zonal.py
class ZonalStatistics:
    """Compute raster statistics within vector polygon zones."""

    def compute(self, raster_layer: Layer, vector_layer: Layer,
                stats: list[str] = ["mean", "std", "min", "max", "count"]
                ) -> gpd.GeoDataFrame:
        """Return the vector layer with added statistic columns."""
        ...
```

Uses `rasterio.features.rasterize` or manual polygon masking to extract zonal values.

#### T14.4: Implement Spatial Interpolation

```python
# src/tkgis/analysis/interpolation.py
class SpatialInterpolator:
    """Interpolates sparse point data to a continuous raster surface."""

    def idw(self, points: gpd.GeoDataFrame, value_column: str,
            resolution: float, power: float = 2.0) -> Layer:
        """Inverse Distance Weighting interpolation."""
        ...

    def kriging(self, points: gpd.GeoDataFrame, value_column: str,
                resolution: float) -> Layer:
        """Ordinary Kriging interpolation (via scipy)."""
        ...
```

#### T14.5: Implement the Analysis Dialog

A unified dialog for launching analysis tools:

```python
# src/tkgis/analysis/dialog.py
class AnalysisDialog(ctk.CTkToplevel):
    """Dialog for configuring and running analysis tools."""

    # Tool selector (dropdown: Change Detection, Zonal Stats, Interpolation, etc.)
    # Dynamic parameter panel based on selected tool
    # Input layer selectors
    # Output layer name
    # Run / Cancel / Preview buttons
```

#### T14.6: Write Analysis Tests

```python
def test_pixel_time_series_extraction(): ...
def test_change_detection_difference(): ...
def test_zonal_statistics(): ...
def test_idw_interpolation(): ...
def test_analysis_results_are_new_layers(): ...
```

### Success Criteria

- [ ] Pixel time series extraction returns correct values from temporal stack
- [ ] Change detection (difference, ratio) produces valid change layers
- [ ] Zonal statistics compute correct mean/std/min/max within polygons
- [ ] IDW interpolation produces a raster from point data
- [ ] All analyses run in background threads
- [ ] Results are added as new layers with analysis metadata
- [ ] `pytest tests/test_analysis.py` — all tests pass

### Produces / Consumes

- **Produces**: PixelTimeSeriesAnalyzer, ChangeDetector, ZonalStatistics, SpatialInterpolator → consumed by TG16
- **Consumes**: TemporalRasterStack from TG9; ProcessingExecutor from TG11; TimeSeriesChart from TG13; Layer from TG3

### Dependencies

| Package | Version | Scope | License | Justification |
|---------|---------|-------|---------|---------------|
| pandas | >=2.0.0 | runtime | BSD-3-Clause | Time series DataFrames and zonal statistics |
| scipy | >=1.7.0 | runtime | BSD-3-Clause | Kriging interpolation and spatial algorithms |
| rasterio | >=1.3.0 | runtime | BSD-3-Clause | Polygon rasterization for zonal statistics |

---

## Task Group 15: Attribute Table & Data Inspector

### Agent Profile

You are a **Python GUI developer** specializing in data table widgets, spreadsheet interfaces, and data browsing. You are building the attribute table for **tkgis**, a desktop GIS application. Read `CLAUDE.md` before starting — it contains all project conventions, constraints, and patterns you must follow.

### Context

The Attribute Table is a core GIS feature — it shows the tabular data behind vector features. In tkgis, it displays the geopandas GeoDataFrame for a selected vector layer as a sortable, filterable, editable table. It also highlights the corresponding features on the map when rows are selected, and vice versa (map selection highlights table rows).

### Files to Read Before Starting

1. `src/tkgis/io/vector.py` — VectorLayerData (from TG7)
2. `src/tkgis/panels/base.py` — BasePanel (from TG1)
3. `src/tkgis/models/events.py` — EventBus (from TG3)
4. `src/tkgis/query/expression.py` — ExpressionParser (from TG12)

### Constraints

- Must handle large tables (100k+ rows) without freezing — use virtual scrolling (load visible rows only)
- Do **NOT** use a third-party table widget if it's not MIT-compatible
- Table edits must propagate back to the GeoDataFrame
- Column sorting and filtering must be non-blocking

### Tasks

#### T15.1: Implement the Virtual Table Widget

```python
# src/tkgis/widgets/data_table.py
class DataTableWidget(ctk.CTkFrame):
    """Virtual-scrolling table for displaying pandas DataFrames."""

    def __init__(self, parent):
        ...
        # Header row with column names (CTkLabels in a frame)
        # Virtual scroll area showing only visible rows
        # Scrollbar (vertical and horizontal)

    def set_data(self, df: pd.DataFrame) -> None: ...
    def get_selected_rows(self) -> list[int]: ...
    def sort_by_column(self, column: str, ascending: bool = True) -> None: ...
    def filter_rows(self, mask: pd.Series) -> None: ...
    def scroll_to_row(self, index: int) -> None: ...
```

Use `ttkbootstrap.Treeview` as the underlying widget for the table body — it handles virtual scrolling natively with large datasets when populated correctly.

#### T15.2: Implement the Attribute Table Panel

```python
# src/tkgis/panels/attribute_table.py
class AttributeTablePanel(BasePanel):
    name = "attribute_table"
    title = "Attribute Table"
    dock_position = "bottom"
    default_visible = False

    def create_widget(self, parent) -> ctk.CTkFrame:
        """Build attribute table with:
        - Layer selector dropdown (which vector layer to display)
        - Filter/search bar with expression input
        - DataTableWidget for the data
        - Status bar: "Showing X of Y features (Z selected)"
        - Toolbar: Select All, Deselect, Invert, Zoom to Selected, Export
        """
        ...

    def _on_layer_selected(self, layer_name): ...
    def _on_table_selection_changed(self): ...
    def _on_map_selection_changed(self, **kwargs): ...
    def _apply_filter(self, expression: str): ...
```

#### T15.3: Implement Map-Table Selection Synchronization

When the user selects rows in the table, highlight those features on the map. When the user selects features on the map (via SelectTool), highlight those rows in the table.

```python
# Bidirectional sync via EventBus:
# Table → Map: emit FEATURES_SELECTED with feature indices
# Map → Table: listen for FEATURES_SELECTED and scroll/highlight
```

#### T15.4: Implement Column Statistics

Right-click a column header to show:
- Min, Max, Mean, Median, Std Dev (numeric columns)
- Unique count, Most common value (text columns)
- Null count

Display in a small popup below the column header.

#### T15.5: Implement Export Functions

- **Export selected features**: Save selected rows as GeoJSON/Shapefile/CSV
- **Export full table**: Save as CSV/Excel
- **Copy selected to clipboard**: Tab-separated values

#### T15.6: Write Attribute Table Tests

```python
def test_data_table_displays_dataframe(): ...
def test_column_sorting(): ...
def test_expression_filter(): ...
def test_row_selection(): ...
def test_export_selected_features(): ...
def test_large_table_performance():
    """Table with 100k rows loads in < 2 seconds."""
    ...
```

### Success Criteria

- [ ] Attribute table displays all columns and rows from a GeoDataFrame
- [ ] Column sorting works (click header to sort ascending/descending)
- [ ] Expression filtering reduces displayed rows
- [ ] Table selection highlights features on map
- [ ] Map selection highlights rows in table
- [ ] Column statistics popup shows correct values
- [ ] 100k-row table loads and scrolls without freezing
- [ ] `pytest tests/test_attribute_table.py` — all tests pass

### Produces / Consumes

- **Produces**: AttributeTablePanel, DataTableWidget → consumed by TG16
- **Consumes**: VectorLayerData from TG7; BasePanel from TG1; EventBus from TG3; ExpressionParser from TG12

---

## Task Group 19: Visual DAG Workflow Builder (Model-Driven Development)

### Agent Profile

You are a **Python GUI engineer** specializing in visual programming environments, node graph editors, and model-driven development tools. You have deep experience with QGIS Model Builder, ArcGIS ModelBuilder, and Orange Data Mining's visual canvas. You are building the visual workflow builder for **tkgis**, a desktop GIS application. Read `CLAUDE.md` before starting — it contains all project conventions, constraints, and patterns you must follow.

### Context

The Visual DAG Workflow Builder is tkgis's flagship feature — a drag-and-drop canvas where users compose data processing workflows by connecting nodes. This follows the same model-driven development paradigm as:

- **QGIS Model Builder**: Drag processing algorithms onto a canvas, connect inputs/outputs, save as models
- **ArcGIS ModelBuilder**: Visual programming for geoprocessing workflows
- **Orange Data Mining**: Widget-based visual programming for data science

In tkgis, **every** processing component is a node: GRDL image processors, GRDL vector operators (from TG17), geopandas operations, I/O readers/writers, and custom Python functions. Nodes are discovered from the **grdl-runtime processor catalog** and from tkgis's own plugin system.

**The critical differentiator**: Workflows built in the visual builder are saved as **grdl-runtime `WorkflowDefinition` YAML** (v3.0 schema from TG18). This means:
1. Workflows are portable — they can run headless via grdl-runtime CLI
2. Workflows can be published to **AuraGrid** for distributed execution
3. Workflows serialize completely — no GUI state leaks into the execution model
4. The visual builder is purely a construction tool; execution goes through grdl-runtime's DAG executor

The visual builder uses the **`WorkflowGraph` API** (from TG18) as its backend data model. The GUI is a projection of the `WorkflowGraph` — adding a node calls `graph.add_node()`, connecting nodes calls `graph.connect()`, validation errors come from `graph.validate()`.

### Files to Read Before Starting

1. `grdl_rt/execution/graph.py` — WorkflowGraph, NodeInfo, EdgeInfo (from TG18)
2. `grdl_rt/execution/workflow.py` — WorkflowDefinition, ProcessingStep (from TG18)
3. `grdl_rt/execution/discovery.py` — discover_processors, filter_processors
4. `grdl_rt/catalog/models.py` — Artifact model with type metadata (from TG18)
5. `grdl/vocabulary.py` — DataType, ProcessorCategory, ImageModality
6. `grdl/image_processing/params.py` — Range, Options, Desc (for parameter editors)
7. `src/tkgis/panels/base.py` — BasePanel ABC (from TG1)
8. `src/tkgis/processing/executor.py` — ProcessingExecutor (from TG11)
9. `src/tkgis/models/events.py` — EventBus (from TG3)
10. `src/tkgis/models/layers.py` — Layer (from TG3)

### Constraints

- The node canvas MUST be implemented in tkinter Canvas — do NOT add PyQt, web views, or JavaScript
- All workflow state MUST live in the `WorkflowGraph` API — the GUI is a view, not the source of truth
- Saved workflows MUST be valid grdl-runtime YAML (v3.0) — no tkgis-specific fields in the workflow model
- GUI layout positions (node x,y) ARE persisted in the YAML `position` field — this is a v3.0 feature
- Do **NOT** implement execution logic — use `ProcessingExecutor` from TG11 and grdl-runtime's DAG executor
- Node colors must follow the data type convention:
  - Blue: Raster (ndarray)
  - Green: Vector (FeatureSet)
  - Orange: Detection (DetectionSet)
  - Gray: I/O (readers/writers)
  - Purple: Conversion (raster↔vector)
- Do **NOT** add any dependencies beyond what tkgis already has

### Tasks

#### T19.1: Implement the Node Graph Canvas

```python
# src/tkgis/workflow/canvas.py
class WorkflowCanvas(tk.Canvas):
    """Visual node graph editor for composing data processing workflows.

    Renders nodes and edges from a WorkflowGraph. All mutations go through
    the graph API — the canvas is a reactive view.
    """

    NODE_WIDTH = 180
    NODE_HEIGHT = 80
    PORT_RADIUS = 6
    GRID_SIZE = 20  # Snap-to-grid

    # Data type → node color
    TYPE_COLORS = {
        "raster": "#89b4fa",        # Blue
        "feature_set": "#a6e3a1",   # Green
        "detection_set": "#fab387", # Orange
        None: "#9399b2",            # Gray (unknown/any)
    }

    def __init__(self, parent, graph: WorkflowGraph, event_bus: EventBus):
        super().__init__(parent, bg="#1e1e2e", highlightthickness=0)
        self._graph = graph
        self._event_bus = event_bus
        self._node_widgets: dict[str, NodeWidget] = {}
        self._edge_widgets: dict[tuple[str, str], EdgeWidget] = {}
        self._selected_node: str | None = None
        self._dragging: bool = False
        self._connecting: bool = False  # Drawing a new edge
        self._connection_start: tuple[str, str | None] | None = None
        self._bind_events()

    def refresh(self) -> None:
        """Rebuild all node and edge widgets from the graph."""
        ...

    def add_node_at(self, processor_name: str, x: float, y: float) -> str:
        """Add a node at canvas position. Returns step_id."""
        step_id = self._graph.add_node(processor_name, position=(x, y))
        self._render_node(step_id)
        return step_id

    def remove_selected_node(self) -> None: ...

    def _render_node(self, step_id: str) -> None:
        """Draw a node rectangle with title, ports, and type-colored header."""
        node = self._graph.get_node(step_id)
        color = self.TYPE_COLORS.get(node.output_type, self.TYPE_COLORS[None])
        # Draw: rounded rectangle, header bar with color, title text,
        # input port circle (left), output port circle (right),
        # parameter summary text
        ...

    def _render_edge(self, source_id: str, target_id: str) -> None:
        """Draw a bezier curve connecting output port to input port."""
        ...

    # --- Mouse interaction ---
    def _on_press(self, event): ...
    def _on_drag(self, event):
        """If dragging a node, move it. If drawing an edge, update rubber band."""
        ...
    def _on_release(self, event):
        """If drawing an edge, complete connection via graph.connect()."""
        ...
    def _on_double_click(self, event):
        """Open parameter editor for the clicked node."""
        ...
    def _on_right_click(self, event):
        """Context menu: Delete, Disconnect, Properties."""
        ...
    def _on_key(self, event):
        """Delete key removes selected node. Ctrl+Z undo. Ctrl+S save."""
        ...

    # --- Validation overlay ---
    def show_validation_errors(self, errors: list) -> None:
        """Highlight nodes/edges with validation issues (red borders, tooltips)."""
        ...
```

Node visual structure:
```
┌──────────────────────────┐
│ ■ [Colored Header Bar]   │
│   Processor Name         │
│ ●──────────────────────● │  ← Input port (left), Output port (right)
│   param1=val, param2=val │
│   [type: feature_set]    │
└──────────────────────────┘
```

#### T19.2: Implement the Node Palette Panel

A panel listing all available nodes grouped by category, with drag-to-canvas support.

```python
# src/tkgis/workflow/palette.py
class NodePalettePanel(BasePanel):
    name = "node_palette"
    title = "Node Palette"
    dock_position = "left"
    default_visible = False  # Only visible when workflow builder is open

    def create_widget(self, parent) -> ctk.CTkFrame:
        """Build palette with:
        - Search entry (filter by name/description)
        - Category tree:
          - I/O (Readers, Writers)
          - Raster Processing (Filters, Intensity, SAR, Ortho)
          - Vector Operations (Buffer, Join, Clip, Dissolve)
          - Detection (CFAR, CSI, Custom)
          - Conversion (Raster→Vector, Vector→Raster)
          - Analysis (Zonal Stats, Change Detection)
          - Workflow (Aggregator, Splitter)
        - Node items showing name, type badge, description tooltip
        - Drag handle for drag-to-canvas
        """
        ...

    def _populate_from_catalog(self) -> None:
        """Query grdl-runtime catalog for all processors and group by category."""
        from grdl_rt import discover_processors
        ...

    def _add_builtin_nodes(self) -> None:
        """Add tkgis-specific nodes (vector I/O, geopandas operations)."""
        ...

    def _on_drag_start(self, event, processor_name: str) -> None:
        """Start DnD from palette to workflow canvas."""
        ...
```

Categories auto-populate from `ProcessorCategory` enum and `@processor_tags`. Nodes show a colored badge matching their output data type.

#### T19.3: Implement the Node Property Inspector

When a node is selected, show its parameters in an editable panel.

```python
# src/tkgis/workflow/inspector.py
class NodeInspectorPanel(BasePanel):
    name = "node_inspector"
    title = "Node Properties"
    dock_position = "right"
    default_visible = False  # Only visible when workflow builder is open

    def create_widget(self, parent) -> ctk.CTkFrame:
        """Build inspector with:
        - Node name (editable step_id)
        - Processor name and version (read-only)
        - Input type / Output type badges
        - Parameter editors (auto-generated from __param_specs__):
          - Range → CTkSlider with min/max labels
          - Options → CTkComboBox dropdown
          - bool → CTkSwitch toggle
          - int/float → CTkEntry with validation
          - str → CTkEntry
        - Depends-on list (read-only, shows incoming connections)
        - Condition expression editor (optional)
        """
        ...

    def set_node(self, step_id: str) -> None:
        """Load a node's parameters into the inspector."""
        node = self._graph.get_node(step_id)
        specs = self._get_param_specs(node.processor_name)
        self._build_param_editors(specs, node.params)
        ...

    def _build_param_editors(self, specs: dict, current_values: dict) -> None:
        """Auto-generate parameter widgets from processor parameter specs."""
        for name, spec in specs.items():
            if 'range' in spec:
                # CTkSlider
                ...
            elif 'options' in spec:
                # CTkComboBox
                ...
            elif spec['type'] == 'bool':
                # CTkSwitch
                ...
            else:
                # CTkEntry
                ...

    def _on_param_changed(self, param_name: str, value: Any) -> None:
        """Update the graph node's parameter."""
        self._graph.update_node_params(self._current_node, {param_name: value})
        self._canvas.refresh()  # Redraw to show updated parameter summary
```

#### T19.4: Implement Edge Drawing and Connection Logic

```python
# src/tkgis/workflow/edges.py
class EdgeRenderer:
    """Draws bezier curve edges between node ports on the canvas."""

    @staticmethod
    def draw_edge(canvas: tk.Canvas, x1, y1, x2, y2,
                  data_type: str | None = None,
                  selected: bool = False) -> int:
        """Draw a smooth bezier curve from (x1,y1) to (x2,y2).

        Color matches data type. Selected edges are thicker.
        Uses canvas.create_line() with smooth=True and splinesteps.
        """
        # Compute control points for S-curve:
        # cp1 = (x1 + dx/2, y1), cp2 = (x2 - dx/2, y2)
        ...

    @staticmethod
    def draw_rubber_band(canvas: tk.Canvas, x1, y1, x2, y2) -> int:
        """Draw a dashed line while user is connecting nodes."""
        ...

class ConnectionValidator:
    """Validates whether two ports can be connected."""

    @staticmethod
    def can_connect(graph: WorkflowGraph,
                    source_id: str, target_id: str) -> tuple[bool, str]:
        """Return (valid, reason).

        Checks:
        - No self-loops
        - No duplicate edges
        - Type compatibility (via WorkflowGraph.connect validation)
        - No cycles
        """
        ...
```

When dragging from an output port, valid target ports glow green, invalid ones glow red.

#### T19.5: Implement the Workflow Builder Window

The main orchestration window that combines canvas, palette, and inspector.

```python
# src/tkgis/workflow/builder_window.py
class WorkflowBuilderWindow(ctk.CTkToplevel):
    """Top-level window for the visual workflow builder.

    Opens as a separate window (not a panel) because it needs maximum canvas space.
    """

    def __init__(self, parent, project: Project, event_bus: EventBus):
        super().__init__(parent)
        self.title("tkgis — Workflow Builder")
        self.geometry("1400x800")

        self._graph = WorkflowGraph(WorkflowDefinition(
            name="New Workflow", version="1.0.0", schema_version="3.0"
        ))
        self._project = project
        self._event_bus = event_bus

        self._setup_layout()
        self._setup_menu()
        self._setup_toolbar()

    def _setup_layout(self):
        """Three-pane layout: Palette | Canvas | Inspector"""
        # Left: NodePalettePanel (250px)
        # Center: WorkflowCanvas (fills)
        # Right: NodeInspectorPanel (300px, hidden until node selected)
        # Bottom: Validation log
        ...

    def _setup_menu(self):
        """File menu: New, Open, Save, Save As, Export YAML
        Edit menu: Undo, Redo, Delete, Select All
        Run menu: Validate, Execute, Execute on AuraGrid (placeholder)
        """
        ...

    def _setup_toolbar(self):
        """Toolbar:
        - New, Open, Save
        - Undo, Redo
        - Validate (check for errors)
        - Run (execute workflow)
        - Zoom In, Zoom Out, Fit All
        - Auto-Layout (arrange nodes)
        """
        ...

    # --- File operations ---
    def new_workflow(self) -> None: ...

    def open_workflow(self) -> None:
        """Load WorkflowDefinition YAML, build WorkflowGraph, render."""
        path = filedialog.askopenfilename(filetypes=[("YAML", "*.yaml *.yml")])
        if path:
            from grdl_rt import load_workflow
            wf_def = load_workflow(path)
            self._graph = WorkflowGraph.from_workflow_definition(wf_def)
            self._canvas.set_graph(self._graph)
            self._canvas.refresh()

    def save_workflow(self, path: str | None = None) -> None:
        """Export WorkflowGraph as grdl-runtime YAML v3.0."""
        if path is None:
            path = filedialog.asksaveasfilename(
                defaultextension=".yaml",
                filetypes=[("YAML", "*.yaml *.yml")]
            )
        if path:
            wf_def = self._graph.to_workflow_definition()
            import yaml
            with open(path, 'w') as f:
                yaml.safe_dump(wf_def.to_dict(), f, sort_keys=False)

    # --- Execution ---
    def validate_workflow(self) -> None:
        """Run graph.validate() and show errors on canvas + log."""
        errors = self._graph.validate()
        self._canvas.show_validation_errors(errors)
        self._log_validation_results(errors)

    def execute_workflow(self) -> None:
        """Execute via ProcessingExecutor with input from selected layer."""
        self.validate_workflow()
        errors = self._graph.validate()
        if any(e.severity == "error" for e in errors):
            return  # Don't execute with errors

        wf_def = self._graph.to_workflow_definition()
        # Use ProcessingExecutor from TG11
        ...

    # --- Auto-layout ---
    def auto_layout(self) -> None:
        """Arrange nodes in topological order using Sugiyama-style layered layout."""
        levels = self._graph.topological_levels()
        y_start = 100
        for level_idx, step_ids in enumerate(levels):
            x_start = 100
            for step_id in step_ids:
                self._graph.update_node_position(step_id, (x_start, y_start))
                x_start += WorkflowCanvas.NODE_WIDTH + 60
            y_start += WorkflowCanvas.NODE_HEIGHT + 80
        self._canvas.refresh()
```

#### T19.6: Implement Drag-and-Drop from Palette to Canvas

```python
# src/tkgis/workflow/dnd.py
class PaletteToCanvasDnD:
    """Handles drag-and-drop from the node palette to the workflow canvas."""

    def __init__(self, palette: NodePalettePanel, canvas: WorkflowCanvas):
        self._palette = palette
        self._canvas = canvas
        self._dragging = False
        self._drag_data: str | None = None  # Processor name being dragged

    def start_drag(self, event, processor_name: str) -> None:
        """Begin dragging a node from the palette."""
        self._dragging = True
        self._drag_data = processor_name
        # Create a ghost image following the cursor
        ...

    def on_drag(self, event) -> None:
        """Move ghost image with cursor."""
        ...

    def on_drop(self, event) -> None:
        """Drop node on canvas at cursor position."""
        if self._dragging and self._drag_data:
            # Convert screen coords to canvas coords
            cx = self._canvas.canvasx(event.x)
            cy = self._canvas.canvasy(event.y)
            # Snap to grid
            cx = round(cx / WorkflowCanvas.GRID_SIZE) * WorkflowCanvas.GRID_SIZE
            cy = round(cy / WorkflowCanvas.GRID_SIZE) * WorkflowCanvas.GRID_SIZE
            self._canvas.add_node_at(self._drag_data, cx, cy)
        self._dragging = False
        self._drag_data = None
```

#### T19.7: Implement Undo/Redo for the Workflow Canvas

```python
# src/tkgis/workflow/history.py
class WorkflowHistory:
    """Undo/redo stack for workflow graph operations."""

    def __init__(self, max_history: int = 100):
        self._undo_stack: list[WorkflowDefinition] = []
        self._redo_stack: list[WorkflowDefinition] = []

    def push(self, state: WorkflowDefinition) -> None:
        """Save current state before a mutation."""
        self._undo_stack.append(state)
        self._redo_stack.clear()
        if len(self._undo_stack) > self._max_history:
            self._undo_stack.pop(0)

    def undo(self) -> WorkflowDefinition | None: ...
    def redo(self) -> WorkflowDefinition | None: ...
    def can_undo(self) -> bool: ...
    def can_redo(self) -> bool: ...
```

Snapshot-based undo: before each mutation, serialize the `WorkflowGraph` to a `WorkflowDefinition` and push it onto the stack.

#### T19.8: Implement Layer-as-Input Node

Users need to feed their loaded map layers into the workflow as source data.

```python
# src/tkgis/workflow/layer_nodes.py
class LayerInputNode:
    """Pseudo-processor that represents a loaded layer as a workflow input."""

    def __init__(self, layer: Layer):
        self._layer = layer

    @property
    def processor_name(self) -> str:
        return f"tkgis.input.{self._layer.layer_type.name.lower()}"

    @property
    def output_type(self) -> str:
        if self._layer.layer_type in (LayerType.RASTER, LayerType.TEMPORAL_RASTER):
            return "raster"
        else:
            return "feature_set"

class LayerOutputNode:
    """Pseudo-processor that writes workflow output as a new map layer."""

    @property
    def input_type(self) -> str:
        return None  # Accepts any type

    @property
    def processor_name(self) -> str:
        return "tkgis.output.layer"
```

These register as special nodes in the palette under "I/O" category. At execution time, they are resolved to GRDL readers/writers or in-memory data sources.

#### T19.9: Implement Workflow Preview

Live preview that runs the workflow on the visible map extent and shows the result as a temporary overlay.

```python
# src/tkgis/workflow/preview.py
class WorkflowPreview:
    """Runs workflow on visible extent for live preview."""

    def __init__(self, canvas: MapCanvas, executor: ProcessingExecutor):
        self._map_canvas = canvas
        self._executor = executor
        self._preview_layer: Layer | None = None
        self._debounce_timer: str | None = None

    def preview(self, graph: WorkflowGraph, input_layer: Layer) -> None:
        """Execute on visible extent in background, display result as overlay."""
        visible = self._map_canvas._transform.get_visible_extent()
        wf_def = graph.to_workflow_definition()
        self._executor.execute_preview(wf_def, input_layer, visible)
        ...

    def clear_preview(self) -> None:
        """Remove preview overlay from map."""
        ...
```

#### T19.10: Write Workflow Builder Tests

```python
# tests/test_workflow_canvas.py
def test_canvas_renders_nodes(): ...
def test_canvas_add_node_at_position(): ...
def test_canvas_remove_node(): ...
def test_canvas_connect_nodes(): ...
def test_canvas_prevent_invalid_connection(): ...
def test_canvas_show_validation_errors(): ...

# tests/test_workflow_palette.py
def test_palette_lists_catalog_processors(): ...
def test_palette_search_filters(): ...
def test_palette_category_grouping(): ...

# tests/test_workflow_inspector.py
def test_inspector_generates_slider_for_range(): ...
def test_inspector_generates_combo_for_options(): ...
def test_inspector_param_change_updates_graph(): ...

# tests/test_workflow_builder.py
def test_save_load_yaml_roundtrip(): ...
def test_auto_layout(): ...
def test_undo_redo(): ...
def test_execute_simple_workflow(): ...
def test_layer_input_node_resolves(): ...
def test_dnd_palette_to_canvas(): ...

# tests/test_workflow_mixed_types.py
def test_raster_to_vector_workflow():
    """Build: SICD Reader → CFAR Detector → Buffer → Write GeoJSON"""
    ...

def test_vector_to_raster_workflow():
    """Build: Read Shapefile → Buffer → Rasterize → Write GeoTIFF"""
    ...

def test_mixed_fan_in_workflow():
    """Build: Two detectors → FeatureSetAggregator(union) → Dissolve → Write"""
    ...
```

### Success Criteria

- [ ] Node canvas renders nodes with type-colored headers and bezier edges
- [ ] Drag-and-drop from palette to canvas creates nodes at cursor position
- [ ] Clicking output port and dragging to input port creates validated connections
- [ ] Invalid connections (raster→vector without conversion) are rejected with visual feedback
- [ ] Node inspector auto-generates parameter editors from processor specs
- [ ] Parameter changes update the WorkflowGraph and re-render the node
- [ ] Saved workflows are valid grdl-runtime YAML v3.0
- [ ] Loaded YAML workflows render correctly on the canvas
- [ ] Auto-layout arranges nodes in topological order
- [ ] Undo/redo works for node add, remove, connect, disconnect, and param changes
- [ ] Validation highlights error nodes with red borders and tooltips
- [ ] Layer input/output nodes connect loaded map data to workflows
- [ ] Workflow execution runs through grdl-runtime DAG executor
- [ ] Mixed-type workflows (raster + vector) build and validate correctly
- [ ] `pytest tests/test_workflow*.py` — all tests pass

### Produces / Consumes

- **Produces**: WorkflowBuilderWindow, WorkflowCanvas, NodePalettePanel, NodeInspectorPanel → consumed by TG16 (app integration)
- **Produces**: Saved grdl-runtime YAML workflows → consumable by grdl-runtime CLI and AuraGrid
- **Consumes**: WorkflowGraph API from TG18; ProcessingExecutor from TG11; grdl-runtime catalog from TG11; FeatureSet/VectorProcessor from TG17; Layer, EventBus from TG3; BasePanel from TG1

---

## Task Group 16: Integration, Testing & Polish

### Agent Profile

You are a **Python integration engineer** specializing in end-to-end testing, system integration, and UX polish. You are performing the final integration of **tkgis**, merging all prior task groups into a cohesive application. Read `CLAUDE.md` before starting — it contains all project conventions, constraints, and patterns you must follow.

### Context

Phases 1–5 built all components independently. This task group:
1. Wires everything together in `app.py`
2. Registers all panels, tools, and plugins
3. Resolves any conflicts from the Shared File Conflict Map
4. Writes end-to-end integration tests
5. Performs UX polish (keyboard shortcuts, default tool, window title, icon)

### Files to Read Before Starting

1. `src/tkgis/app.py` — Main application (from TG1)
2. All panel implementations (from TG5, TG9, TG10, TG11, TG13, TG15)
3. All plugin implementations (from TG7, TG8)
4. `src/tkgis/models/events.py` — EventBus (from TG3)
5. `src/tkgis/canvas/map_canvas.py` — MapCanvas (from TG4)
6. `pyproject.toml` — Dependencies from all TGs

### Constraints

- Do **NOT** rewrite any component — only wire them together
- If merging conflicts exist in shared files, resolve per the Conflict Map strategy
- The final application must launch with `python -m tkgis` and show a usable window
- Default state: dark theme, pan tool active, layer tree visible, log console visible

### Tasks

#### T16.1: Wire All Panels into the Application Shell

In `app.py`, register all panels:

```python
def _register_all_panels(self):
    panels = [
        LayerTreePanel(self._project, self._event_bus),
        TimeSliderPanel(self._temporal_manager, self._event_bus),
        ProcessingToolboxPanel(self._event_bus),
        WorkflowBuilderPanel(self._event_bus),
        ChartPanel(self._event_bus),
        AttributeTablePanel(self._event_bus),
        LogConsolePanel(),
        PluginManagerPanel(self._plugin_manager),
    ]
    for panel in panels:
        self._panel_registry.register(panel)
```

Create the MapCanvas as the central widget. Wire the StatusBar to the MapCanvas (coordinate updates, CRS display, scale).

#### T16.2: Wire All Tools and Menu Actions

Connect toolbar buttons to tools:
- Pan → PanTool
- Zoom In → ZoomInTool
- Zoom Out → ZoomOutTool
- Select → SelectTool
- Workflow Builder → Open WorkflowBuilderWindow (TG19)
- Measure Distance → DistanceTool
- Measure Area → AreaTool
- Run Workflow → Open ProcessingRunDialog

Connect menu items to actions:
- File → Import Layer → DataProviderRegistry.open_file()
- File → New/Open/Save Project → Project.load/save
- Layer → Add Raster/Vector → File dialog with provider filters
- Processing → Toolbox → Toggle ProcessingToolboxPanel
- View → Panels → Dynamic panel toggles

#### T16.3: Wire Plugin System Startup

On application start:
1. Create `PluginContext` with all registries
2. Load and activate built-in plugins (VectorProviderPlugin, RasterProviderPlugin)
3. Discover and load external plugins
4. Wire Plugins menu to show discovered plugin entries

#### T16.4: Merge Shared Files

Resolve all conflicts from the Shared File Conflict Map:
- `src/tkgis/__init__.py`: Consolidate exports
- `src/tkgis/app.py`: Merge all panel registrations, tool wiring, menu connections
- `pyproject.toml`: Consolidate all dependency sections
- `tests/conftest.py`: Merge all shared fixtures

#### T16.5: Implement UX Polish

- **Window title**: "tkgis — {project_name}" (updates on project load/save)
- **Default state**: Pan tool active, dark theme, layer tree + log console visible
- **Drag-and-drop file import**: Drop a file on the map canvas to import it
- **Recent files**: Track last 10 opened files in config
- **Keyboard shortcuts**:
  | Shortcut | Action |
  |----------|--------|
  | Ctrl+N | New Project |
  | Ctrl+O | Open Project |
  | Ctrl+S | Save Project |
  | Ctrl+Shift+S | Save As |
  | Ctrl+L | Add Layer |
  | Ctrl+Z | Undo |
  | Ctrl+Shift+Z | Redo |
  | F5 | Refresh Map |
  | F11 | Toggle Full Screen |

#### T16.6: Write Integration Tests

```python
def test_app_launches_with_all_panels(): ...
def test_open_vector_layer_appears_in_tree(): ...
def test_open_raster_layer_renders_on_map(): ...
def test_layer_visibility_toggle_updates_map(): ...
def test_tool_switching(): ...
def test_processing_workflow_end_to_end(): ...
def test_attribute_table_syncs_with_map(): ...
def test_project_save_load_roundtrip(): ...
def test_plugin_manager_lists_builtin_plugins(): ...
def test_theme_toggle(): ...
def test_workflow_builder_opens_and_renders(): ...
def test_workflow_builder_save_load_yaml(): ...
def test_workflow_builder_mixed_raster_vector(): ...
def test_workflow_builder_execute_from_layer(): ...
```

#### T16.7: Consolidate Dependencies in pyproject.toml

Final dependency list (validate all are MIT-compatible):

```toml
[project]
dependencies = [
    "customtkinter>=5.2.0",
    "ttkbootstrap>=1.10.0",
    "Pillow>=10.0.0",
    "geopandas>=0.14.0",
    "pyogrio>=0.7.0",
    "pyproj>=3.6.0",
    "grdl>=0.1.0",
    "grdl-runtime>=0.1.0",
    "matplotlib>=3.7.0",
    "numpy>=1.20.0",
    "scipy>=1.7.0",
    "pandas>=2.0.0",
    "pydantic>=2.0.0",
    "PyYAML>=6.0",
    "rasterio>=1.3.0",
    "shapely>=2.0.0",
]
```

### Success Criteria

- [ ] `python -m tkgis` launches with all panels, tools, and plugins active
- [ ] Opening a GeoTIFF shows it on the map with correct geolocation
- [ ] Opening a Shapefile shows features on the map and in the attribute table
- [ ] Pan, zoom, measure, identify, and select tools all function
- [ ] Processing toolbox lists GRDL processors and workflows execute
- [ ] Visual workflow builder opens, renders nodes, and saves valid YAML
- [ ] Drag-and-drop workflow with mixed raster + vector nodes validates and executes
- [ ] Saved workflow YAML is loadable by grdl-runtime CLI independently
- [ ] Project save/load preserves all state
- [ ] All keyboard shortcuts work
- [ ] Dark/light theme toggle works
- [ ] All integration tests pass
- [ ] `pytest tests/ -x -q` — 0 failures

### Produces / Consumes

- **Produces**: Complete, integrated tkgis application with visual workflow builder
- **Consumes**: All artifacts from TG1–TG15, TG17–TG19

---

## Appendix: Architectural Decisions

### A1. customtkinter + ttkbootstrap over PyQt/PySide

**Decision**: Use customtkinter as the primary GUI toolkit, supplemented by ttkbootstrap.

**Alternatives considered**: PySide6/PyQt6 (more capable but LGPL/GPL licensing complexity), DearPyGui (modern but immature ecosystem), Kivy (mobile-focused).

**Why**: customtkinter is MIT-licensed, provides modern dark/light themes out of the box, and has a lower learning curve than Qt. ttkbootstrap fills gaps (Treeview, Notebook styling). Both are pure Python, cross-platform, and pip-installable. The trade-off is less widget variety than Qt, but for a GIS application the map canvas (custom tkinter Canvas) is the dominant widget.

### A2. GRDL for Raster I/O, Not rasterio Directly

**Decision**: All raster I/O goes through GRDL, not rasterio/GDAL directly.

**Alternatives considered**: Direct rasterio usage (simpler for GeoTIFF), GDAL Python bindings.

**Why**: GRDL provides unified readers for SAR (SICD, CPHD, Sentinel-1), multispectral (VIIRS), and standard formats (GeoTIFF) with a consistent API. It handles complex SAR metadata, geolocation models, and chip-based reading natively. Using GRDL means tkgis automatically supports every format GRDL adds in the future. The trade-off is an extra dependency, but GRDL is MIT-licensed and purpose-built for this use case.

### A3. grdl-runtime for Processing, Not Direct Processor Calls

**Decision**: Image processing workflows are constructed and executed through grdl-runtime's Workflow builder.

**Alternatives considered**: Direct calls to GRDL processor `.apply()` methods.

**Why**: grdl-runtime provides metadata injection, GPU dispatch, progress callbacks, retry/resilience, and a processor catalog. Using it gives tkgis these capabilities for free. Workflows are serializable (YAML), enabling save/load and sharing. The catalog enables the Processing Toolbox to discover available algorithms at runtime.

### A4. Tile-Based Rendering for Large Images

**Decision**: Render raster layers as 256x256 tile pyramids, loaded on demand.

**Alternatives considered**: Load full image and downsample (fails for large images), use GDAL overviews (ties to GDAL directly).

**Why**: Remotely sensed imagery is routinely 10,000–50,000 pixels per side. Loading the full image into memory is infeasible. Tile-based rendering with an LRU cache and background loading provides smooth pan/zoom at any image size. The tile pyramid is computed on-the-fly from GRDL's chip-reading capability rather than requiring pre-built overviews.

### A5. geopandas for Vector Data

**Decision**: Use geopandas as the vector data backend.

**Alternatives considered**: Direct Fiona/shapely usage, OGR Python bindings.

**Why**: geopandas provides a DataFrame API that naturally feeds the Attribute Table, supports all common vector formats via pyogrio, includes spatial indexing (R-tree) for fast queries, and handles CRS reprojection. It is the de facto standard for vector geospatial data in Python. BSD-3-Clause license is MIT-compatible.

### A6. EventBus for Decoupled Communication

**Decision**: Use a publish-subscribe EventBus for component communication instead of direct callbacks.

**Alternatives considered**: Direct method calls between components, Qt-style signals/slots.

**Why**: The plugin architecture requires decoupled communication — plugins must emit and receive events without knowing about other components. An EventBus with typed events provides this cleanly. The trade-off is slightly harder debugging (event flow isn't visible in the call stack), but structured logging mitigates this.

### A7. Plugin Architecture with Three Discovery Vectors

**Decision**: Support built-in, entry-point, and directory plugins.

**Alternatives considered**: Only entry-point plugins (pip-only), only built-in (no extensibility).

**Why**: Built-in plugins (GRDL raster, geopandas vector) ensure core functionality works without extra installs. Entry-point plugins enable pip-installable extensions. Directory plugins enable casual users to drop in plugins without pip. This mirrors QGIS's plugin model, which is one of its strongest adoption drivers.

### A8. Visual DAG Builder over Code-Only Workflows

**Decision**: Build a drag-and-drop visual node graph editor for composing grdl-runtime workflows, following the QGIS Model Builder / ArcGIS ModelBuilder / Orange Data Mining paradigm.

**Alternatives considered**: Code-only workflow composition (Python DSL or YAML editing), embedded Jupyter notebook, web-based node editor (React Flow).

**Why**: The target user is a GIS analyst / remote sensing scientist — they think in "connect processing blocks" not "write Python." Visual builders have proven adoption in QGIS, ArcGIS, and Orange. The critical constraint is that workflows serialize to **grdl-runtime YAML v3.0**, making them portable: they can run headless, on other machines, or on AuraGrid without the GUI. The visual builder is a construction tool, not a runtime. This separation means we never have "GUI-only workflows" — everything that can be built visually can also run on the grid.

### A9. Upstream GRDL/grdl-runtime Extensions (Phase 0)

**Decision**: Extend GRDL with a `FeatureSet` data model and `VectorProcessor` ABC, and extend grdl-runtime with data type declarations and a `WorkflowGraph` introspection API — as upstream PRs, not tkgis-internal code.

**Alternatives considered**: Build vector handling inside tkgis only (wrapping geopandas without GRDL integration), fork grdl-runtime to add features.

**Why**: The visual workflow builder must save workflows as grdl-runtime YAML. If vector operations only exist in tkgis, they can't execute on AuraGrid or via the grdl-runtime CLI. By adding `FeatureSet` and `VectorProcessor` to GRDL itself, vector operations become first-class citizens in the same ecosystem as raster processors. This also benefits GRDK (Orange-based GUI) and any other grdl-runtime consumer. The `WorkflowGraph` API in grdl-runtime provides a clean backend for any visual builder, not just tkgis. The trade-off is that Phase 0 blocks the rest of the build, but the alternative — building on a foundation that can't support the flagship feature — is worse.

### A10. FeatureSet as Universal Vector Container

**Decision**: Create `FeatureSet` in GRDL as a generic vector container parallel to `DetectionSet`, with bridge methods between them.

**Alternatives considered**: Extend `DetectionSet` to be generic (breaking change), use geopandas `GeoDataFrame` directly (adds hard dependency), create a separate `VectorResult` in grdl-runtime only.

**Why**: `DetectionSet` is tightly scoped to detector outputs with confidence fields, output_fields declarations, and detector metadata. Making it generic would break the CFAR detector contract. `GeoDataFrame` is too heavy (geopandas is optional in GRDL). `FeatureSet` provides a lightweight, shapely-based container that: (a) bridges to/from `DetectionSet` losslessly, (b) bridges to/from `GeoDataFrame` when geopandas is available, (c) serializes to GeoJSON natively (no deps beyond shapely), and (d) follows the same `execute()` protocol as raster processors. The `VectorProcessor.process(features) → FeatureSet` pattern mirrors `ImageTransform.apply(source) → ndarray`.

### A11. DataType Annotations on Processors

**Decision**: Add `input_type` and `output_type` to `@processor_tags` and `ProcessingStep` so the visual builder can validate connections at design time.

**Alternatives considered**: Runtime-only type checking (detect errors at execution), no type checking (let users figure it out).

**Why**: A visual builder without type validation is frustrating — users connect incompatible nodes, run the workflow, wait for execution, then get a cryptic error. QGIS Model Builder validates parameter types at connection time. By declaring types on processors and steps, the builder shows valid/invalid connections instantly (green/red port highlights). Types are optional — existing processors without annotations still work (treated as "any" type). The v3.0 YAML schema stores types for cross-tool validation.
