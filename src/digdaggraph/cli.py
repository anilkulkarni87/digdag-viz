#!/usr/bin/env python3
"""Command-line interface for digdag graph visualization."""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any

from .config import Config
from .logger import setup_logging, get_logger
from .parser import load_dig_docs, find_workflow_name, schedule_info
from .graph import build_interactive_graph
from .templates import TemplateManager
from .exceptions import DigdagGraphError
from . import __version__

logger = get_logger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser.
    
    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="Generate interactive visualizations for Treasure Data Digdag workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  digdag-graph ./workflows
  
  # Custom output directory and format
  digdag-graph ./workflows --outdir docs/graphs --format png
  
  # Use config file
  digdag-graph ./workflows --config .digdag-graph.yml
  
  # Exclude patterns
  digdag-graph ./workflows --exclude "**/test_*.dig" --exclude "**/.archive/**"
  
  # Verbose output
  digdag-graph ./workflows --verbose
  
  # Data lineage for a specific table
  digdag-graph ./workflows --lineage customers_enriched
  
  # Show all table lineage
  digdag-graph ./workflows --lineage-all

Environment Variables:
  OUTPUT_DIR          Output directory for graphs
  GRAPH_FORMAT        Output format (svg, png, pdf)
  GRAPH_DIRECTION     Graph direction (LR, TB, RL, BT)
  EXCLUDE_PATTERNS    Comma-separated exclude patterns
  INCLUDE_PATTERNS    Comma-separated include patterns
  TEMPLATE_DIR        Custom template directory
  MAX_GRAPH_DEPTH     Maximum task nesting depth
        """
    )
    
    # Required arguments
    parser.add_argument(
        "path",
        nargs='?',  # Make optional when --version is used
        help="Path to .dig file or directory containing workflows"
    )
    
    # Version
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    
    # Output options
    parser.add_argument(
        "--outdir",
        default=None,
        help="Output directory for generated graphs (default: graphs)"
    )
    parser.add_argument(
        "--format",
        choices=["svg", "png", "pdf"],
        default=None,
        help="Graph output format (default: svg)"
    )
    
    # Configuration
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file (.yml)"
    )
    parser.add_argument(
        "--no-schedule",
        action="store_true",
        help="Skip schedule page generation"
    )
    
    # Filtering
    parser.add_argument(
        "--exclude",
        action="append",
        dest="exclude_patterns",
        help="Exclude patterns (glob format, can be used multiple times)"
    )
    parser.add_argument(
        "--include-only",
        action="append",
        dest="include_patterns",
        help="Include only matching patterns (can be used multiple times)"
    )
    
    # Graph options
    parser.add_argument(
        "--direction",
        choices=["LR", "TB", "RL", "BT"],
        default=None,
        help="Graph direction: LR (left-right), TB (top-bottom), RL, BT (default: LR)"
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Maximum task nesting depth to visualize"
    )
    
    # Templates
    parser.add_argument(
        "--template-dir",
        type=Path,
        help="Custom template directory"
    )
    
    # Lineage options
    parser.add_argument(
        "--lineage",
        metavar="TABLE",
        help="Extract and display lineage for a specific table"
    )
    parser.add_argument(
        "--lineage-all",
        action="store_true",
        help="Generate lineage graph for all tables"
    )
    parser.add_argument(
        "--lineage-direction",
        choices=["upstream", "downstream", "both"],
        default="both",
        help="Lineage direction: upstream (sources), downstream (consumers), or both (default: both)"
    )
    parser.add_argument(
        "--lineage-depth",
        type=int,
        default=None,
        help="Maximum lineage depth to trace"
    )
    
    # Logging
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output (debug logging)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Minimal output (warnings and errors only)"
    )
    
    return parser


def main(argv=None):
    """Main entry point.
    
    Args:
        argv: Command-line arguments (defaults to sys.argv)
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = create_parser()
    args = parser.parse_args(argv)
    
    # Setup logging first
    setup_logging(verbose=args.verbose, quiet=args.quiet)
    
    # Validate that path is provided
    if not args.path:
        logger.error("❌ Error: the following arguments are required: path")
        logger.error("")
        logger.error("Usage: digdag-graph PATH [options]")
        logger.error("")
        logger.error("Examples:")
        logger.error("  digdag-graph ./workflows")
        logger.error("  digdag-graph ./project --outdir output")
        logger.error("")
        logger.error("For help: digdag-graph --help")
        return 1
    
    try:
        # Build configuration
        cli_args = {
            'output_dir': args.outdir,
            'graph_format': args.format,
            'graph_direction': args.direction,
            'include_schedule': not args.no_schedule,
            'exclude_patterns': args.exclude_patterns,
            'include_patterns': args.include_patterns,
            'template_dir': args.template_dir,
            'max_depth': args.max_depth,
            'verbose': args.verbose,
            'quiet': args.quiet,
        }
        
        config = Config(config_file=args.config, cli_args=cli_args)
        
        logger.info("Digdag Graph Visualization Tool")
        logger.debug(f"Configuration: {config.to_dict()}")
        
        # Parse input path
        input_path = Path(args.path).resolve()
        output_dir = Path(config['output_dir']).resolve()
        
        # Validate input path exists
        if not input_path.exists():
            logger.error(f"❌ Input path does not exist: {input_path}")
            logger.error("")
            logger.error("Please check the path and try again.")
            logger.error("Example: python digdag-graph ./workflows")
            return 1
        
        # Determine project root for SQL file resolution
        project_root = input_path if input_path.is_dir() else input_path.parent
        
        logger.info(f"Input: {input_path}")
        logger.info(f"Output: {output_dir}")
        
        # Load workflow documents
        docs = load_dig_docs(
            input_path,
            exclude_patterns=config['exclude_patterns'],
            include_patterns=config['include_patterns']
        )
        
        if not docs:
            logger.error("❌ No workflow documents found")
            logger.error("")
            logger.error("Please ensure:")
            logger.error("  1. The path contains .dig files")
            logger.error("  2. Files are not excluded by --exclude patterns")
            logger.error("")
            logger.error(f"Searched in: {input_path}")
            if config['exclude_patterns']:
                logger.error(f"Excluded patterns: {config['exclude_patterns']}")
            logger.error("")
            logger.error("💡 Tip: Use --verbose to see which files were found")
            return 1
        
        # Handle lineage extraction if requested
        if args.lineage or args.lineage_all:
            from .lineage import WorkflowLineageExtractor, LineageGraph
            
            logger.info("Extracting data lineage...")
            
            extractor = WorkflowLineageExtractor()
            lineage_graph = LineageGraph()
            
            # Extract lineage from all workflows
            for file_path, doc in docs:
                # Create simple workflow doc wrapper
                class SimpleWorkflowDoc:
                    def __init__(self, name, content, tasks):
                        self.name = name
                        self.content = content
                        self.tasks = tasks
                
                workflow_doc = SimpleWorkflowDoc(
                    name=file_path.stem,
                    content=doc,
                    tasks={k: v for k, v in doc.items() if k.startswith('+')}
                )
                
                # Extract lineage
                task_lineages = extractor.extract_from_workflow(
                    workflow_doc,
                    file_path.parent
                )
                
                # Add to graph
                for task_lineage in task_lineages:
                    lineage_graph.add_task_lineage(task_lineage)
            
            # Display lineage results
            all_tables = lineage_graph.get_all_tables()
            logger.info(f"Found {len(all_tables)} tables in lineage")
            
            if args.lineage:
                # Show lineage for specific table
                table_name = args.lineage
                logger.info("")
                logger.info(f"📊 Data Lineage for: {table_name}")
                logger.info("=" * 60)
                
                # Get upstream/downstream based on direction
                if args.lineage_direction in ["upstream", "both"]:
                    upstream = lineage_graph.get_upstream_tables(table_name)
                    if upstream:
                        logger.info("")
                        logger.info("⬆️  Upstream (Sources):")
                        for table in sorted(upstream):
                            logger.info(f"  • {table}")
                
                if args.lineage_direction in ["downstream", "both"]:
                    downstream = lineage_graph.get_downstream_tables(table_name)
                    if downstream:
                        logger.info("")
                        logger.info("⬇️  Downstream (Consumers):")
                        for table in sorted(downstream):
                            logger.info(f"  • {table}")
                
                # Show workflows using this table
                workflows_using = lineage_graph.get_workflows_for_table(table_name)
                if workflows_using:
                    logger.info("")
                    logger.info("📁 Workflows:")
                    for wf in sorted(workflows_using):
                        logger.info(f"  • {wf}")
                
                logger.info("")
                
                # Generate visualization
                output_dir = Path(config['output_dir']).resolve()
                graph_path = output_dir / "lineage" / table_name.replace('.', '_')
                
                logger.info("Generating lineage graph...")
                svg_file = lineage_graph.generate_graph(
                    graph_path,
                    table_filter=table_name,
                    direction=args.lineage_direction,
                    max_depth=args.lineage_depth
                )
                logger.info(f"📈 Lineage graph saved to: {svg_file}")
                logger.info("")
                
                return 0
            
            elif args.lineage_all:
                # Show all tables and their relationships
                logger.info("")
                logger.info("📊 All Tables in Lineage Graph")
                logger.info("=" * 60)
                
                for table in sorted(all_tables):
                    logger.info(f"\n{table}")
                    
                    upstream = lineage_graph.get_upstream_tables(table)
                    if upstream:
                        logger.info(f"  ⬆️  Sources: {', '.join(sorted(upstream))}")
                    
                    downstream = lineage_graph.get_downstream_tables(table)
                    if downstream:
                        logger.info(f"  ⬇️  Consumers: {', '.join(sorted(downstream))}")
                
                logger.info("")
                logger.info(f"Total: {len(all_tables)} tables")
                
                # Generate full lineage graph
                output_dir = Path(config['output_dir']).resolve()
                graph_path = output_dir / "lineage" / "full_lineage"
                
                logger.info("")
                logger.info("Generating full lineage graph...")
                svg_file = lineage_graph.generate_graph(graph_path)
                logger.info(f"📈 Lineage graph saved to: {svg_file}")
                logger.info("")
                
                return 0
        
        # Generate graphs
        logger.info(f"Generating interactive graphs for {len(docs)} workflows...")
        
        schedules: List[Dict[str, str]] = []
        workflows: List[Dict[str, Any]] = []
        
        # Initialize template manager
        template_mgr = TemplateManager(template_dir=config['template_dir'])
        
        # Determine if input_path is a single project or a workspace
        # If input_path contains any .dig files directly, it's a single project.
        is_single_project = False
        if input_path.is_dir():
             is_single_project = any(input_path.glob('*.dig'))

        for file_path, doc in docs:
            try:
                # Determine project root for this specific workflow
                if is_single_project:
                    current_project_root = input_path
                elif input_path.is_dir():
                    # Workspace mode: project root is the top-level directory inside input_path
                    rel_parts = file_path.relative_to(input_path).parts
                    if rel_parts:
                        current_project_root = input_path / rel_parts[0]
                    else:
                        current_project_root = input_path
                else:
                    current_project_root = file_path.parent

                # Build interactive graph data
                svg_filename, svg_content, task_defs = build_interactive_graph(
                    doc,
                    file_path,
                    output_dir,
                    direction=config['graph_direction'],
                    max_depth=config['max_depth'],
                    project_root=current_project_root
                )
                
                wf_name = find_workflow_name(doc, file_path)
                
                # Render interactive HTML
                html_filename = f"{file_path.stem}.html"
                template_mgr.render_interactive_graph(
                    wf_name=wf_name,
                    svg_content=svg_content,
                    task_defs=task_defs,
                    output_path=output_dir / html_filename
                )
                cron, tz = schedule_info(doc)
                
                # Collect workflow info
                rel_path = str(file_path.relative_to(input_path if input_path.is_dir() else file_path.parent))
                
                # Determine project name
                if is_single_project:
                    project_name = input_path.name
                elif input_path.is_dir():
                    # Workspace mode: use top-level directory as project name
                    rel_parts = file_path.relative_to(input_path).parts
                    project_name = rel_parts[0] if rel_parts else input_path.name
                else:
                    # Single file input
                    project_name = file_path.parent.name

                workflows.append({
                    'name': wf_name,
                    'file': rel_path,
                    'schedule': cron,
                    'timezone': tz,
                    'timezone': tz,
                    'graph': html_filename,  # Link to interactive HTML
                    'project': project_name  # Add project name for filtering
                })
                
                # Collect schedule info
                if cron:
                    schedules.append({
                        'workflow': wf_name,
                        'schedule': cron,
                        'timezone': tz or '',
                        'path': rel_path,
                        'timezone': tz or '',
                        'path': rel_path,
                        'svg': html_filename,  # Link to interactive HTML
                        'project': file_path.parent.name  # Add project name for filtering
                    })
                
                logger.info(f"✓ Generated graph for {wf_name}")
                
            except Exception as e:
                logger.error(f"Failed to generate graph for {file_path}: {e}")
                continue
        
        # Generate HTML pages
        
        # Generate index page
        template_mgr.render_index_page(workflows, output_dir / "index.html")
        
        # Generate schedule page if requested
        if config['include_schedule'] and schedules:
            sorted_schedules = sorted(schedules, key=lambda x: (x['workflow'], x['path']))
            template_mgr.render_schedule_page(sorted_schedules, output_dir / "scheduled_workflows.html")
            
        # Generate unscheduled page
        template_mgr.render_unscheduled_page(workflows, output_dir / "unscheduled_workflows.html")
        
        # Generate lineage page
        logger.info("Extracting data lineage...")
        from .lineage import WorkflowLineageExtractor, LineageGraph
        
        extractor = WorkflowLineageExtractor() # Keep this line for extractor to be defined
        # Build lineage graph
        lineage_graph = LineageGraph(config=config.config)
        
        # Extract lineage from all workflows
        for file_path, doc in docs: # Keep original loop variable names
            # Create simple workflow doc wrapper
            class SimpleWorkflowDoc:
                def __init__(self, name, content, tasks):
                    self.name = name
                    self.content = content
            
            workflow_doc = SimpleWorkflowDoc(
                name=file_path.stem,
                content=doc,
                tasks={k: v for k, v in doc.items() if k.startswith('+')}
            )
            
            # Extract lineage
            task_lineages = extractor.extract_from_workflow(
                workflow_doc,
                file_path.parent
            )
            
            # Add to graph
            for task_lineage in task_lineages:
                lineage_graph.add_task_lineage(task_lineage)
        
        # Get all tables and generate individual graphs
        all_tables = lineage_graph.get_all_tables()
        lineage_data = []
        
        for table_name in sorted(all_tables):
            # Parse table name
            if '.' in table_name:
                parts = table_name.split('.')
                database = parts[0] if len(parts) > 1 else None
                name = parts[-1]
            else:
                database = None
                name = table_name
            
            # Get lineage info
            upstream = lineage_graph.get_upstream_tables(table_name)
            downstream = lineage_graph.get_downstream_tables(table_name)
            workflows_using = lineage_graph.get_workflows_for_table(table_name)
            
            # Generate individual graph
            graph_path = None
            if upstream or downstream:
                try:
                    safe_name = table_name.replace('.', '_')
                    graph_file = output_dir / "lineage" / f"{safe_name}"
                    html_file = lineage_graph.generate_graph(
                        graph_file,
                        table_filter=table_name,
                        direction="both"
                    )
                    # Relative path from lineage.html
                    graph_path = f"lineage/{safe_name}.html"
                except Exception as e:
                    logger.debug(f"Failed to generate graph for {table_name}: {e}")
            
            lineage_data.append({
                'name': name,
                'full_name': table_name,
                'database': database,
                'layer': lineage_graph.get_table_layer(table_name),
                'upstream_count': len(upstream),
                'downstream_count': len(downstream),
                'workflow_count': len(workflows_using),
                'graph_path': graph_path
            })
        
        # Generate comprehensive full lineage graph
        logger.info("Generating comprehensive lineage graph...")
        try:
            full_graph_file = output_dir / "lineage" / "full_lineage"
            full_html = lineage_graph.generate_graph(full_graph_file)
            logger.info(f"✓ Full lineage graph: {full_html}")
        except Exception as e:
            logger.warning(f"Failed to generate full lineage graph: {e}")
        
        # Render lineage page
        template_mgr.render_lineage_page(lineage_data, output_dir / "lineage.html")
        
        # Summary
        logger.info("")
        logger.info("=" * 50)
        logger.info(f"✓ Generated {len(workflows)} workflow graphs")
        logger.info(f"✓ Output directory: {output_dir}")
        logger.info(f"✓ Index page: {output_dir / 'index.html'}")
        if config['include_schedule'] and schedules:
            logger.info(f"✓ Schedule page: {output_dir / 'scheduled_workflows.html'}")
        logger.info(f"✓ Unscheduled page: {output_dir / 'unscheduled_workflows.html'}")
        logger.info(f"✓ Lineage page: {output_dir / 'lineage.html'} ({len(all_tables)} tables)")
        logger.info("=" * 50)
        
        return 0
        
    except FileNotFoundError as e:
        if "graphviz" in str(e).lower() or "dot" in str(e).lower():
            logger.error("❌ Graphviz not found!")
            logger.error("")
            logger.error("Graphviz is required to generate workflow visualizations.")
            logger.error("Please install it:")
            logger.error("")
            logger.error("  macOS:    brew install graphviz")
            logger.error("  Ubuntu:   sudo apt-get install graphviz")
            logger.error("  Windows:  Download from https://graphviz.org/download/")
            logger.error("")
        else:
            logger.error(f"❌ File not found: {e}")
            logger.error("Please check that the path exists and is accessible.")
        return 1
    except PermissionError as e:
        logger.error(f"❌ Permission denied: {e}")
        logger.error("")
        logger.error("Please check file/directory permissions:")
        logger.error(f"  Input:  {args.path}")
        logger.error(f"  Output: {config.get('output_dir', 'graphs')}")
        return 1
    except DigdagGraphError as e:
        logger.error(f"❌ {e}")
        if args.verbose:
            logger.exception("Detailed error information:")
        else:
            logger.error("")
            logger.error("💡 Tip: Run with --verbose for more details")
        return 1
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        logger.error("")
        logger.error("This might be a bug. Please report it with:")
        logger.error("  1. The command you ran")
        logger.error("  2. The error message above")
        logger.error("  3. Output from running with --verbose")
        logger.error("")
        logger.error("GitHub Issues: https://github.com/treasure-data/digdag-graph/issues")
        if args.verbose:
            logger.exception("Stack trace:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
