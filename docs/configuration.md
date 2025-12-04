# Configuration Guide

This guide covers all configuration options for the Digdag Workflow Visualizer.

## Configuration Priority

Settings are loaded in the following order (later sources override earlier ones):

1. **Default values** (built-in)
2. **Configuration file** (`.digdag-graph.yml`)
3. **Environment variables**
4. **CLI arguments** (highest priority)

## Configuration File

Create a `.digdag-graph.yml` file in your project root:

```yaml
output:
  directory: graphs        # Output directory
  format: svg             # svg, png, or pdf

graph:
  direction: LR           # LR, TB, RL, or BT
  max_depth: null         # Maximum nesting depth (null = unlimited)
  include_schedule: true  # Generate schedule page

styling:
  node_colors:            # Custom colors (optional)
    default: "#e8f0fe"
    group: "#e6ffed"
    td>: "#b2dfdb"
    sh>: "#bbdefb"

filters:
  exclude_patterns:       # Glob patterns to exclude
    - "**/test_*.dig"
    - "**/.archive/**"
  include_only: []        # Only process these patterns
```

## Environment Variables

All settings can be configured via environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `OUTPUT_DIR` | Output directory | `docs/graphs` |
| `GRAPH_FORMAT` | Output format | `svg`, `png`, `pdf` |
| `GRAPH_DIRECTION` | Graph direction | `LR`, `TB`, `RL`, `BT` |
| `EXCLUDE_PATTERNS` | Comma-separated exclude patterns | `**/test_*.dig,**/.archive/**` |
| `INCLUDE_PATTERNS` | Comma-separated include patterns | `**/prod_*.dig` |
| `TEMPLATE_DIR` | Custom template directory | `./custom-templates` |
| `MAX_GRAPH_DEPTH` | Maximum nesting depth | `5` |
| `INCLUDE_SCHEDULE` | Generate schedule page | `true`, `false` |

### Example

```bash
export OUTPUT_DIR=docs/graphs
export GRAPH_FORMAT=png
export GRAPH_DIRECTION=TB
export EXCLUDE_PATTERNS="**/test_*.dig,**/.archive/**"

digdag-graph ./workflows
```

## CLI Arguments

All options can be specified via command-line arguments:

```bash
digdag-graph ./workflows \
  --outdir docs/graphs \
  --format png \
  --direction TB \
  --exclude "**/test_*.dig" \
  --exclude "**/.archive/**" \
  --max-depth 5 \
  --verbose
```

## Common Configurations

### Development Environment

```yaml
# .digdag-graph.yml
output:
  directory: graphs
  format: svg

graph:
  direction: LR
  max_depth: null
  include_schedule: true

filters:
  exclude_patterns:
    - "**/test_*.dig"
    - "**/.archive/**"
    - "**/experimental/**"
```

### Production Environment

```yaml
# .digdag-graph.yml
output:
  directory: docs/workflows
  format: svg

graph:
  direction: LR
  max_depth: 10
  include_schedule: true

filters:
  include_only:
    - "**/prod_*.dig"
    - "**/production/**/*.dig"
```

### CI/CD Environment

Use environment variables for flexibility:

```bash
# GitHub Actions
OUTPUT_DIR=docs/graphs
GRAPH_FORMAT=svg
EXCLUDE_PATTERNS="**/test_*.dig"

# GitLab CI
OUTPUT_DIR=public
GRAPH_FORMAT=png
GRAPH_DIRECTION=TB
```

## Graph Direction

Choose the layout that works best for your workflows:

- **LR** (Left to Right): Default, good for most workflows
- **TB** (Top to Bottom): Good for deeply nested workflows
- **RL** (Right to Left): Alternative horizontal layout
- **BT** (Bottom to Top): Alternative vertical layout

## Filtering

### Exclude Patterns

Exclude specific files or directories:

```yaml
filters:
  exclude_patterns:
    - "**/test_*.dig"        # All test files
    - "**/.archive/**"       # Archive directory
    - "**/experimental/**"   # Experimental workflows
    - "**/*_backup.dig"      # Backup files
```

### Include Patterns

Process only specific files:

```yaml
filters:
  include_only:
    - "**/prod_*.dig"        # Only production workflows
    - "**/critical/**"       # Only critical workflows
```

## Custom Templates

Override default HTML templates:

1. Create a templates directory:
```bash
mkdir custom-templates
```

2. Copy and modify templates:
```bash
cp templates/schedule.html.j2 custom-templates/
cp templates/index.html.j2 custom-templates/
```

3. Use custom templates:
```bash
digdag-graph ./workflows --template-dir custom-templates
```

Or in configuration:

```yaml
output_pages:
  template_dir: ./custom-templates
```

## Troubleshooting

### Graphviz Not Found

If you get "Graphviz not found" errors:

```bash
# macOS
brew install graphviz

# Ubuntu/Debian
sudo apt-get install graphviz

# RHEL/CentOS
sudo yum install graphviz
```

### Large Repositories

For repositories with many workflows:

1. Use filtering to process subsets
2. Set `max_depth` to limit complexity
3. Use `--quiet` mode for less output

```bash
digdag-graph ./workflows \
  --max-depth 5 \
  --exclude "**/test_*.dig" \
  --quiet
```

### Memory Issues

For very large workflows:

1. Reduce `max_depth`
2. Process workflows in batches
3. Use PNG instead of SVG for smaller files

```bash
digdag-graph ./workflows \
  --format png \
  --max-depth 3
```
