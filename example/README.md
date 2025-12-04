# Example Project

This is a minimal example to demonstrate the Digdag Workflow Visualizer.

## Quick Test

```bash
# From the repository root:
python digdag-graph example --outdir example-output

# Open the result:
open example-output/index.html
```

## What's Included

- **daily_processing.dig**: A simple ETL workflow with 4 tasks
  - Extract data from source (SQL)
  - Transform and aggregate (SQL)
  - Load to warehouse (Shell script)
  - Send notification (Echo)

- **queries/**: SQL files referenced by the workflow
  - `extract.sql`: Extracts events from the last 24 hours
  - `transform.sql`: Aggregates user activity

## Expected Output

The tool will generate:
- `example-output/index.html` - Main dashboard
- `example-output/daily_processing.html` - Interactive workflow graph
- `example-output/scheduled_workflows.html` - Schedule overview
- `example-output/queries/extract.html` - SQL viewer for extract query
- `example-output/queries/transform.html` - SQL viewer for transform query

## What to Look For

1. **Color-coded tasks**: Each operator type has a different color
2. **Interactive graph**: Click on tasks to see details
3. **SQL links**: Click on `td>` tasks to view the SQL queries
4. **Schedule info**: The workflow shows up in the scheduled workflows page

## Next Steps

After verifying this works, try it on your own workflows:
```bash
python digdag-graph /path/to/your/workflows --outdir output
```
