# ADR 001: Cached Vector Reprojection

## Status
Accepted

## Context
Rendering large vector datasets on the `MapCanvas` was identified as a major performance bottleneck. Profiling revealed that `VectorTileProvider` was reprojecting the entire `GeoDataFrame` to EPSG:4326 on every tile request when the source CRS differed. This caused severe UI freezing during pan and zoom operations.

## Decision
We implemented a lazy-reprojection and caching mechanism directly within `VectorLayerData`. When `get_features_in_bbox_4326` is called, the layer will reproject its geometries to EPSG:4326 once, cache the result, and use the cached version's spatial index (`sindex`) for all subsequent tile queries. We also added a 10% bounding box buffer to prevent feature clipping at tile boundaries.

## Consequences
- **Positive:** Tile rendering speed improved dramatically (rendering time for 100k features reduced by >80%), enabling smooth interaction.
- **Positive:** Reprojection cost is paid only once per layer instead of per-tile.
- **Negative:** Increased memory footprint, as both the original geometries and the EPSG:4326 geometries are now held in memory for projected datasets.