# Backyard Sun Exposure Modeling Tool

Command-line simulator that computes direct sun exposure over a backyard grid using pvlib/pysolar for sun positions and shapely-based ray casting. Distances are expressed in feet.

## Setup

```bash
uv sync
```

## Usage

```bash
uv run sun_map \
  --scene scenes/backyard_example.yaml \
  --start "2025-06-21T08:00" \
  --end "2025-06-21T18:00" \
  --step-minutes 15 \
  --height-ft 3.3 \
  --grid-resolution-ft 0.82 \
  --output-prefix outputs/june21 \
  --save-scene-overhead
```

This writes a heatmap PNG, optional numpy array, and optional overhead scene rendering under `outputs/`.

## Development

```bash
uv run -- ruff check .                 # Ruff lint
uv run -- ruff format .                # Ruff format
uv run -- ty check backyard_sun_map    # Ty type checking
```
