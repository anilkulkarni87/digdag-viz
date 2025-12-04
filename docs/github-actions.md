# GitHub Actions Integration

This guide shows how to integrate Digdag Viz into your GitHub Actions workflows.

## Basic Setup

### Step 1: Create Workflow File

Create `.github/workflows/visualize-workflows.yml`:

```yaml
name: Generate Workflow Visualizations

on:
  push:
    branches: [main, develop]
    paths:
      - '**/*.dig'
      - '**/*.yml'
  pull_request:
    paths:
      - '**/*.dig'
  workflow_dispatch:

jobs:
  visualize:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Generate workflow graphs
        uses: anilkulkarni87/digdag-viz@v1
        with:
          workflow-path: '.'
          output-dir: 'docs/graphs'
          graph-format: 'svg'
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: workflow-graphs
          path: docs/graphs/
```

### Step 2: Commit and Push

```bash
git add .github/workflows/visualize-workflows.yml
git commit -m "Add workflow visualization"
git push
```

## Action Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `workflow-path` | Path to .dig files or directory | Yes | `.` |
| `output-dir` | Output directory for graphs | No | `docs/graphs` |
| `graph-format` | Output format (svg, png, pdf) | No | `svg` |
| `graph-direction` | Graph direction (LR, TB, RL, BT) | No | `LR` |
| `exclude-patterns` | Comma-separated exclude patterns | No | `''` |
| `include-patterns` | Comma-separated include patterns | No | `''` |
| `config-file` | Path to configuration file | No | `''` |
| `no-schedule` | Skip schedule page generation | No | `false` |
| `max-depth` | Maximum task nesting depth | No | `''` |
| `verbose` | Enable verbose output | No | `false` |

## Common Use Cases

### Auto-Commit Generated Graphs

```yaml
- name: Generate graphs
  uses: anilkulkarni87/digdag-viz@v1
  with:
    workflow-path: '.'
    output-dir: 'docs/graphs'

- name: Commit graphs
  if: github.ref == 'refs/heads/main'
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"
    git add docs/graphs/
    git diff --staged --quiet || git commit -m "docs: update workflow visualizations [skip ci]"
    git push
```

### Deploy to GitHub Pages

```yaml
- name: Generate graphs
  uses: anilkulkarni87/digdag-viz@v1
  with:
    workflow-path: '.'
    output-dir: 'public'

- name: Deploy to GitHub Pages
  if: github.ref == 'refs/heads/main'
  uses: peaceiris/actions-gh-pages@v3
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_dir: ./public
```

### Multiple Formats

```yaml
- name: Generate SVG graphs
  uses: anilkulkarni87/digdag-viz@v1
  with:
    workflow-path: '.'
    output-dir: 'docs/graphs/svg'
    graph-format: 'svg'

- name: Generate PNG graphs
  uses: anilkulkarni87/digdag-viz@v1
  with:
    workflow-path: '.'
    output-dir: 'docs/graphs/png'
    graph-format: 'png'
```

### With Filtering

```yaml
- name: Generate production graphs only
  uses: anilkulkarni87/digdag-viz@v1
  with:
    workflow-path: '.'
    output-dir: 'docs/graphs'
    include-patterns: '**/prod_*.dig,**/production/**'
    exclude-patterns: '**/test_*.dig,**/.archive/**'
```

### PR Comments with Graphs

```yaml
- name: Generate graphs
  uses: anilkulkarni87/digdag-viz@v1
  with:
    workflow-path: '.'
    output-dir: 'graphs'

- name: Comment PR
  if: github.event_name == 'pull_request'
  uses: actions/github-script@v7
  with:
    script: |
      const fs = require('fs');
      const graphs = fs.readdirSync('graphs').filter(f => f.endsWith('.svg'));
      const comment = `## Workflow Visualizations\n\n${graphs.length} workflows visualized. [View artifacts](https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }})`;
      github.rest.issues.createComment({
        issue_number: context.issue.number,
        owner: context.repo.owner,
        repo: context.repo.repo,
        body: comment
      });
```

## Scheduled Runs

Generate graphs on a schedule:

```yaml
on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:

jobs:
  visualize:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: anilkulkarni87/digdag-viz@v1
        with:
          workflow-path: '.'
          output-dir: 'docs/graphs'
```

## Matrix Strategy

Generate graphs for multiple projects:

```yaml
jobs:
  visualize:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        project: [project1, project2, project3]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Generate graphs for ${{ matrix.project }}
        uses: anilkulkarni87/digdag-viz@v1
        with:
          workflow-path: './${{ matrix.project }}'
          output-dir: 'docs/graphs/${{ matrix.project }}'
```

## Caching

Speed up runs with caching:

```yaml
- name: Cache Graphviz
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}

- name: Generate graphs
  uses: anilkulkarni87/digdag-viz@v1
  with:
    workflow-path: '.'
    output-dir: 'docs/graphs'
```

## Troubleshooting

### Action Not Found

Ensure you're using the correct version:

```yaml
uses: anilkulkarni87/digdag-viz@v1  # Use specific version
# or
uses: anilkulkarni87/digdag-viz@main  # Use latest
```

### Permission Denied

Grant write permissions for auto-commit:

```yaml
permissions:
  contents: write

jobs:
  visualize:
    # ...
```

### Large Repositories

Use filtering to reduce processing time:

```yaml
- uses: anilkulkarni87/digdag-viz@v1
  with:
    workflow-path: '.'
    exclude-patterns: '**/test_*.dig,**/.archive/**,**/backup/**'
    max-depth: '5'
```


## Basic Setup

### Step 1: Create Workflow File

Create `.github/workflows/visualize-workflows.yml`:

```yaml
name: Generate Workflow Visualizations

on:
  push:
    branches: [main, develop]
    paths:
      - '**/*.dig'
      - '**/*.yml'
  pull_request:
    paths:
      - '**/*.dig'
  workflow_dispatch:

jobs:
  visualize:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Generate workflow graphs
        uses: treasure-data/digdag-graph@v2
        with:
          workflow-path: '.'
          output-dir: 'docs/graphs'
          graph-format: 'svg'
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: workflow-graphs
          path: docs/graphs/
```

### Step 2: Commit and Push

```bash
git add .github/workflows/visualize-workflows.yml
git commit -m "Add workflow visualization"
git push
```

## Action Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `workflow-path` | Path to .dig files or directory | Yes | `.` |
| `output-dir` | Output directory for graphs | No | `docs/graphs` |
| `graph-format` | Output format (svg, png, pdf) | No | `svg` |
| `graph-direction` | Graph direction (LR, TB, RL, BT) | No | `LR` |
| `exclude-patterns` | Comma-separated exclude patterns | No | `''` |
| `include-patterns` | Comma-separated include patterns | No | `''` |
| `config-file` | Path to configuration file | No | `''` |
| `no-schedule` | Skip schedule page generation | No | `false` |
| `max-depth` | Maximum task nesting depth | No | `''` |
| `verbose` | Enable verbose output | No | `false` |

## Common Use Cases

### Auto-Commit Generated Graphs

```yaml
- name: Generate graphs
  uses: treasure-data/digdag-graph@v2
  with:
    workflow-path: '.'
    output-dir: 'docs/graphs'

- name: Commit graphs
  if: github.ref == 'refs/heads/main'
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"
    git add docs/graphs/
    git diff --staged --quiet || git commit -m "docs: update workflow visualizations [skip ci]"
    git push
```

### Deploy to GitHub Pages

```yaml
- name: Generate graphs
  uses: treasure-data/digdag-graph@v2
  with:
    workflow-path: '.'
    output-dir: 'public'

- name: Deploy to GitHub Pages
  if: github.ref == 'refs/heads/main'
  uses: peaceiris/actions-gh-pages@v3
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_dir: ./public
```

### Multiple Formats

```yaml
- name: Generate SVG graphs
  uses: treasure-data/digdag-graph@v2
  with:
    workflow-path: '.'
    output-dir: 'docs/graphs/svg'
    graph-format: 'svg'

- name: Generate PNG graphs
  uses: treasure-data/digdag-graph@v2
  with:
    workflow-path: '.'
    output-dir: 'docs/graphs/png'
    graph-format: 'png'
```

### With Filtering

```yaml
- name: Generate production graphs only
  uses: treasure-data/digdag-graph@v2
  with:
    workflow-path: '.'
    output-dir: 'docs/graphs'
    include-patterns: '**/prod_*.dig,**/production/**'
    exclude-patterns: '**/test_*.dig,**/.archive/**'
```

### PR Comments with Graphs

```yaml
- name: Generate graphs
  uses: treasure-data/digdag-graph@v2
  with:
    workflow-path: '.'
    output-dir: 'graphs'

- name: Comment PR
  if: github.event_name == 'pull_request'
  uses: actions/github-script@v7
  with:
    script: |
      const fs = require('fs');
      const graphs = fs.readdirSync('graphs').filter(f => f.endsWith('.svg'));
      const comment = `## Workflow Visualizations\n\n${graphs.length} workflows visualized. [View artifacts](https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }})`;
      github.rest.issues.createComment({
        issue_number: context.issue.number,
        owner: context.repo.owner,
        repo: context.repo.repo,
        body: comment
      });
```

## Scheduled Runs

Generate graphs on a schedule:

```yaml
on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:

jobs:
  visualize:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: treasure-data/digdag-graph@v2
        with:
          workflow-path: '.'
          output-dir: 'docs/graphs'
```

## Matrix Strategy

Generate graphs for multiple projects:

```yaml
jobs:
  visualize:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        project: [project1, project2, project3]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Generate graphs for ${{ matrix.project }}
        uses: treasure-data/digdag-graph@v2
        with:
          workflow-path: './${{ matrix.project }}'
          output-dir: 'docs/graphs/${{ matrix.project }}'
```

## Caching

Speed up runs with caching:

```yaml
- name: Cache Graphviz
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}

- name: Generate graphs
  uses: treasure-data/digdag-graph@v2
  with:
    workflow-path: '.'
    output-dir: 'docs/graphs'
```

## Troubleshooting

### Action Not Found

Ensure you're using the correct version:

```yaml
uses: treasure-data/digdag-graph@v2  # Use specific version
# or
uses: treasure-data/digdag-graph@main  # Use latest
```

### Permission Denied

Grant write permissions for auto-commit:

```yaml
permissions:
  contents: write

jobs:
  visualize:
    # ...
```

### Large Repositories

Use filtering to reduce processing time:

```yaml
- uses: treasure-data/digdag-graph@v2
  with:
    workflow-path: '.'
    exclude-patterns: '**/test_*.dig,**/.archive/**,**/backup/**'
    max-depth: '5'
```
