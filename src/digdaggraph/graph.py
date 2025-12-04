"""Graph rendering for Digdag workflows using Graphviz."""

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from graphviz import Digraph
import json

from .parser import find_workflow_name, schedule_info, is_task_key, task_operator
from .exceptions import GraphRenderError
from .logger import get_logger
from .sql_pages import read_and_generate_sql_page

logger = get_logger(__name__)


# Node styling configuration
NODE_SHAPES = {
    "default": "box",
    "group": "box",  # was folder
    "if>": "diamond",
    "call>": "box",  # was component
    "require>": "box", # was oval
    "loop>": "box", # was circle
    "http>": "box",
    "mail>": "box",
    "_do": "note",
    "_error": "Mcircle",
    "root": "box",
}

# Border colors (from didaggraph_v2)
NODE_COLORS = {
    "default": "#4A4A4A",   # Gray
    "group": "#9013FE",     # Purple
    "root": "#8B572A",      # Brown
    "if>": "#BD10E0",       # Magenta
    "call>": "#9013FE",     # Purple
    "require>": "#9013FE",  # Purple
    "loop>": "#50E3C2",     # Teal
    "for_each>": "#50E3C2", # Teal
    "sh>": "#7ED321",       # Green
    "td>": "#4A90E2",       # Blue
    "echo>": "#9B9B9B",     # Light Gray
    "py>": "#F5A623",       # Orange
    "rb>": "#D0021B",       # Red
    "http_call>": "#417505",# Dark Green
    "http>": "#417505",     # Dark Green
    "mail>": "#D0021B",     # Crimson
    "_export": "#F8E71C",   # Yellow
    "_parallel": "#9013FE", # Purple
    "_do": "#7ED321",       # Green
    "_error": "#D0021B",    # Red
}

OPERATOR_ICONS = {
    "td>": "📊",
    "sh>": "💻",
    "py>": "🐍",
    "echo>": "📢",
    "call>": "📞",
    "require>": "🔗",
    "loop>": "🔄",
    "for_each>": "🔄",
    "if>": "❓",
    "mail>": "📧",
    "http>": "🌐",
    "_error": "⚠️",
    "root": "📦",
}

NODE_PENWIDTHS = {
    "default": "1.0",
    "group": "1.0",
    "call>": "3.0",
    "require>": "3.0",
    "td>": "1.5",
    "echo>": "1.9",
    "_export": "2.0",
}


def style_for(op: Optional[str], custom_colors: Optional[Dict[str, str]] = None) -> Tuple[str, str, str]:
    """Get shape, color, and penwidth for an operator.
    
    Args:
        op: Operator name (e.g., 'td>', 'sh>')
        custom_colors: Optional custom color mappings
    
    Returns:
        Tuple of (shape, color, penwidth)
    """
    colors = {**NODE_COLORS, **(custom_colors or {})}
    
    if not op:
        return (NODE_SHAPES["default"], colors["default"], NODE_PENWIDTHS["default"])
    
    shape = NODE_SHAPES.get(op, NODE_SHAPES["default"])
    color = colors.get(op, colors["default"])
    penwidth = NODE_PENWIDTHS.get(op, NODE_PENWIDTHS["default"])
    
    return (shape, color, penwidth)


def add_node(
    g: Digraph,
    node_id: str,
    label: str,
    op: Optional[str],
    custom_colors: Optional[Dict[str, str]] = None
):
    """Add a node to the graph with appropriate styling.
    
    Args:
        g: Graphviz Digraph instance
        node_id: Unique node identifier
        label: Node label text
        op: Operator type
        custom_colors: Optional custom color mappings
    """
    shape, color, penwidth = style_for(op, custom_colors)
    # Style: rounded (not filled), colored border
    g.node(node_id, label=label, shape=shape, style="rounded", color=color, penwidth=penwidth, fontname="Helvetica")


def normalized_id(prefix_stack: List[str], name: str) -> str:
    """Create unique node ID from prefix stack and name.
    
    Args:
        prefix_stack: List of parent task names
        name: Current task name
    
    Returns:
        Unique node identifier
    """
    parts = [*prefix_stack, name]
    return "/".join(parts)


def render_tasks(
    g: Digraph,
    doc: Dict[str, Any],
    parent_stack: List[str],
    tasks: List[Tuple[str, Dict[str, Any]]],
    custom_colors: Optional[Dict[str, str]] = None,
    max_depth: Optional[int] = None,
    current_depth: int = 0,
    parent_is_parallel: bool = False
) -> List[str]:
    """Recursively render tasks and their relationships.
    
    Args:
        parent_is_parallel: If True, tasks are parallel siblings and should not be connected sequentially
    
    Returns:
        List of node IDs representing the "last" nodes (completion points) of this task group
    """
    # Check depth limit
    if max_depth is not None and current_depth >= max_depth:
        logger.debug(f"Reached max depth {max_depth}, skipping deeper tasks")
        return []
    
    # Track completion points from previous sibling (sequential) or all siblings (parallel)
    prev_last_nodes: List[str] = []
    all_parallel_last_nodes: List[str] = []  # Accumulate when parent_is_parallel
    
    for (tkey, tbody) in tasks:
        tname = tkey[1:]  # Remove + prefix
        node_id = normalized_id(parent_stack, tkey)
        op_pair = task_operator(tbody if isinstance(tbody, dict) else {})
        op = op_pair[0] if op_pair else None

        # Build a readable label
        op_suffix = f"\\n[{op}]" if op else ""
        label = f"{tname}{op_suffix}"

        add_node(g, node_id, label, op, custom_colors)

        # Connect from previous sibling's completion points (ONLY if not parallel)
        if prev_last_nodes and not parent_is_parallel:
            for last_node in prev_last_nodes:
                g.edge(last_node, node_id)
        
        # If parent is parallel, connect each child to the parent instead
        if parent_is_parallel and len(parent_stack) > 0:
            parent_id = normalized_id(parent_stack[:-1], parent_stack[-1])
            g.edge(parent_id, node_id)

        # Operator-specific edges/labels
        if isinstance(tbody, dict):
            # require> and call> are handled via URLs in interactive mode
            # No need to create separate visual nodes for them

            # loop> / for_each> / for_range> annotate
            for loopish in ("loop>", "for_each>", "for_range>"):
                if loopish in tbody:
                    g.edge(node_id, node_id, label=loopish, style="dotted", dir="none")

            # retry / _error handlers visually as side-notes
            if "retry" in tbody:
                g.edge(node_id, node_id, label=f"retry={tbody['retry']}", style="dotted", dir="none")
            
            if "_error" in tbody:
                add_node(g, f"{node_id}__error", f"{tname} error handler", "_error", custom_colors)
                g.edge(node_id, f"{node_id}__error", style="dashed", label="_error")

            # Check if THIS task has _parallel for its children
            is_parallel = tbody.get("_parallel", False)

            # Recurse into children (+ subtasks)
            child_tasks = [(k, v) for k, v in tbody.items() if is_task_key(k)]
            if child_tasks:
                child_last_nodes = render_tasks(
                    g, doc, parent_stack + [tkey], child_tasks,
                    custom_colors, max_depth, current_depth + 1,
                    parent_is_parallel=is_parallel
                )
                # This task completes when all its children complete
                current_task_last_nodes = child_last_nodes
            else:
                # Leaf task - it completes itself
                current_task_last_nodes = [node_id]
        else:
            # Non-dict task body (edge case)
            current_task_last_nodes = [node_id]
        
        # Update tracking based on whether we're in parallel mode
        if parent_is_parallel:
            # Accumulate ALL children's last nodes
            all_parallel_last_nodes.extend(current_task_last_nodes)
        else:
            # Sequential: next sibling connects from this task's completion
            prev_last_nodes = current_task_last_nodes
    
    # Return appropriate last nodes
    if parent_is_parallel:
        return all_parallel_last_nodes
    else:
        return prev_last_nodes


def build_graph(
    doc: Dict[str, Any],
    file_path: Path,
    outdir: Path,
    graph_format: str = "svg",
    direction: str = "LR",
    custom_colors: Optional[Dict[str, str]] = None,
    max_depth: Optional[int] = None
) -> str:
    """Build and render workflow graph."""
    try:
        wf_name = find_workflow_name(doc, file_path)
        cron, tz = schedule_info(doc)
        
        # Build title with schedule info
        title = wf_name
        if cron:
            title += f"  (schedule: {cron}{' '+tz if tz else ''})"

        logger.debug(f"Building graph for workflow: {wf_name}")
        
        # Create graph with RED edges by default
        g = Digraph(comment=f"{wf_name}", format=graph_format, graph_attr={'rankdir': direction, 'labelloc': 't', 'fontsize': '20', 'label': title, 'fontname': 'Helvetica'}, node_attr={'fontname': 'Helvetica', 'fontsize': '11'}, edge_attr={'color': 'red'})
        g.attr("edge", color="red")  # Default edge color

        # Root "workflow" node
        root_id = f"{wf_name}__root"
        add_node(g, root_id, wf_name, "root", custom_colors)

        # Collect top-level tasks in order
        top_tasks = [(k, v) for k, v in doc.items() if is_task_key(k)]
        render_tasks(g, doc, [wf_name], top_tasks, custom_colors, max_depth)

        # Connect root to first task
        if top_tasks:
            first_id = normalized_id([wf_name], top_tasks[0][0])
            g.edge(root_id, first_id)

        # Write file
        outdir.mkdir(parents=True, exist_ok=True)
        output_path = outdir / f"{file_path.stem}"
        
        logger.debug(f"Rendering graph to {output_path}.{graph_format}")
        g.render(output_path, cleanup=True)
        
        return f"{file_path.stem}.{graph_format}"
        
    except Exception as e:
        raise GraphRenderError(f"Failed to render graph for {file_path}: {e}")


def build_interactive_graph(
    doc: Dict[str, Any],
    file_path: Path,
    outdir: Path,
    direction: str = "LR",
    custom_colors: Optional[Dict[str, str]] = None,
    max_depth: Optional[int] = None,
    project_root: Optional[Path] = None
) -> Tuple[str, str]:
    """Build interactive workflow graph with inline SVG."""
    try:
        wf_name = find_workflow_name(doc, file_path)
        cron, tz = schedule_info(doc)
        
        # Build title with schedule info
        title = wf_name
        if cron:
            title += f"  (schedule: {cron}{' '+tz if tz else ''})"

        logger.debug(f"Building interactive graph for workflow: {wf_name}")
        
        # Create TWO graphs: one for SVG, one for imagemap (legacy logic kept but we only use SVG now)
        map_name = file_path.stem
        
        # SVG graph with RED edges
        g_svg = Digraph(name=map_name, format="svg", graph_attr={'rankdir': direction, 'labelloc': 't', 'fontsize': '20', 'label': title, 'fontname': 'Helvetica'}, node_attr={'fontname': 'Helvetica', 'fontsize': '11'}, edge_attr={'color': 'red'})
        g_svg.attr(target="_top")  # Keep links in same tab
        
        # Imagemap graph (legacy, kept for structure parity if needed)
        g_map = Digraph(name=map_name, format="cmapx", graph_attr={'rankdir': direction, 'labelloc': 't', 'fontsize': '20', 'label': title, 'fontname': 'Helvetica'}, node_attr={'fontname': 'Helvetica', 'fontsize': '11'}, edge_attr={'color': 'red'})
        g_map.attr(target="_top")

        # Root "workflow" node
        root_id = f"{wf_name}__root"
        # Root node styling
        shape, color, penwidth = style_for("root", custom_colors)
        
        # Add root to both
        g_svg.node(root_id, wf_name, shape=shape, style="rounded", color=color, penwidth=penwidth, URL="../../index.html", tooltip="Back to index")
        g_map.node(root_id, wf_name, shape=shape, style="rounded", color=color, penwidth=penwidth, URL="../../index.html", tooltip="Back to index")

        # Collect top-level tasks
        top_tasks = [(k, v) for k, v in doc.items() if is_task_key(k)]
        
        # Collect task definitions for sidebar
        task_defs = {}
        
        render_tasks_with_links(
            g_svg, g_map, doc, [wf_name], top_tasks,
            custom_colors, max_depth, 0,
            file_path, outdir, project_root,
            task_defs=task_defs,
            initial_prev_nodes=[root_id]
        )

        # Handle root-level special directive blocks (_error, _do, _else_do)
        # These need special handling because they don't start with +
        special_directives = []
        
        # Check for _error block
        if "_error" in doc and isinstance(doc["_error"], dict):
            special_directives.append(("_error", doc["_error"], "#D0021B", "[ERROR]"))
        
        # Check for _do block (inside if>, for_each>, etc.)
        if "_do" in doc and isinstance(doc["_do"], dict):
            special_directives.append(("_do", doc["_do"], "#7ED321", "[DO]"))
        
        # Check for _else_do block (inside if>)
        if "_else_do" in doc and isinstance(doc["_else_do"], dict):
            special_directives.append(("_else_do", doc["_else_do"], "#F5A623", "[ELSE]"))
        
        # Render each special directive block
        for directive_name, directive_body, color, icon in special_directives:
            directive_id = normalized_id([wf_name], directive_name)
            directive_label = f"{wf_name}\\n{directive_name}"
            directive_shape = NODE_SHAPES.get(directive_name, "box")
            
            # Create the directive node
            g_svg.node(directive_id, label=f"{icon} {directive_label}",
                      shape=directive_shape, color=color, style="filled",
                      fillcolor=f"{color}20", fontname="Inter")  # 20 = 12% opacity in hex
            g_map.node(directive_id, label=f"{icon} {directive_label}",
                      shape=directive_shape, color=color, style="filled",
                      fillcolor=f"{color}20", fontname="Inter")
            
            # Connect root to directive with dashed line
            g_svg.edge(root_id, directive_id, style="dashed", label=directive_name, color=color)
            g_map.edge(root_id, directive_id, style="dashed", label=directive_name, color=color)
            
            # Recursively render directive's child tasks
            directive_child_tasks = [(k, v) for k, v in directive_body.items() if is_task_key(k)]
            if directive_child_tasks:
                render_tasks_with_links(
                    g_svg, g_map, doc, [wf_name, directive_name],
                    directive_child_tasks, custom_colors, max_depth, 1,
                    file_path, outdir, project_root,
                    task_defs=task_defs,
                    initial_prev_nodes=[directive_id]
                )


        # Write SVG

        # Write SVG
        outdir.mkdir(parents=True, exist_ok=True)
        svg_path = outdir / f"{file_path.stem}"
        g_svg.render(svg_path, cleanup=True)
        
        svg_filename = f"{file_path.stem}.svg"
        html_filename = f"{file_path.stem}.html"
        html_path = outdir / html_filename
        
        # Read the generated SVG content
        svg_file = outdir / svg_filename
        svg_content = svg_file.read_text(encoding='utf-8')
        
        # Clean up SVG content
        svg_start = svg_content.find('<svg')
        if svg_start >= 0:
            svg_content = svg_content[svg_start:]
        
        # Generate professional HTML with modern UI
        html_content = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{wf_name} - Digdag Workflow Graph</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/@panzoom/panzoom@4.5.1/dist/panzoom.min.js"></script>
  <style>
    :root {{
      --primary: #1a365d;
      --primary-light: #2c5282;
      --accent: #3182ce;
      --success: #38a169;
      --warning: #d69e2e;
      --gray-50: #f7fafc;
      --gray-100: #edf2f7;
      --gray-200: #e2e8f0;
      --gray-300: #cbd5e0;
      --gray-400: #a0aec0;
      --gray-600: #4a5568;
      --gray-800: #1a202c;
      --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
      --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ 
      margin: 0; height: 100vh; display: flex; flex-direction: column;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #ffffff; color: var(--gray-800); overflow: hidden;
      font-size: 14px; line-height: 1.5;
      -webkit-font-smoothing: antialiased;
    }}
    header {{ 
      padding: 0 32px; height: 64px; background: var(--primary);
      border-bottom: 1px solid #0f2744; display: flex;
      align-items: center; justify-content: space-between;
      box-shadow: var(--shadow); z-index: 1000;
    }}
    .brand {{ 
      font-weight: 600; font-size: 18px; color: white;
      text-decoration: none; display: flex; align-items: center;
      gap: 12px; letter-spacing: -0.01em;
    }}
    .brand-icon {{
      width: 32px; height: 32px; background: var(--accent);
      border-radius: 6px; display: flex; align-items: center;
      justify-content: center; font-weight: 700; font-size: 16px;
    }}
    .workflow-title {{
      color: var(--gray-300); font-weight: 400; font-size: 14px;
      margin-left: 8px; padding-left: 12px;
      border-left: 1px solid var(--primary-light);
    }}
    .nav-links {{ display: flex; align-items: center; gap: 4px; }}
    .nav-links a {{ 
      color: rgba(255, 255, 255, 0.9); text-decoration: none; 
      font-size: 14px; font-weight: 500; padding: 8px 16px;
      border-radius: 6px; transition: all 0.2s ease;
    }}
    .nav-links a:hover {{ background: var(--primary-light); color: white; }}
    .search-box {{ position: relative; margin-left: 24px; }}
    .search-box input {{
      background: var(--primary-light); border: 1px solid var(--primary-light);
      color: white; padding: 8px 16px 8px 40px; border-radius: 6px;
      font-size: 14px; width: 240px; outline: none;
      font-family: 'Inter', sans-serif; transition: all 0.2s ease;
    }}
    .search-box input::placeholder {{ color: rgba(255, 255, 255, 0.6); }}
    .search-box input:focus {{ 
      background: white; color: var(--gray-800);
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(49, 130, 206, 0.1);
    }}
    .search-box input:focus::placeholder {{ color: var(--gray-400); }}
    .search-icon {{
      position: absolute; left: 12px; top: 50%;
      transform: translateY(-50%); color: rgba(255, 255, 255, 0.6);
      pointer-events: none; font-size: 16px;
    }}
    .search-box input:focus ~ .search-icon {{ color: var(--gray-400); }}
    main {{ 
      flex: 1; position: relative; background: var(--gray-50);
      overflow: hidden; cursor: grab;
    }}
    main:active {{ cursor: grabbing; }}
    #scene {{ width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; }}
    svg {{ max-width: none; height: auto; background: white; border-radius: 8px; box-shadow: var(--shadow-lg); }}
    #sidebar {{
      position: fixed; top: 64px; right: -450px; width: 450px;
      height: calc(100vh - 64px); background: white;
      box-shadow: -4px 0 16px rgba(0,0,0,0.1);
      transition: right 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      z-index: 999; overflow-y: auto; border-left: 1px solid var(--gray-200);
    }}
    #sidebar.open {{ right: 0; }}
    .sidebar-header {{
      display: flex; justify-content: space-between; align-items: center;
      padding: 24px; border-bottom: 1px solid var(--gray-200);
      background: var(--gray-50); position: sticky; top: 0; z-index: 10;
    }}
    .sidebar-title {{ font-size: 18px; font-weight: 600; color: var(--gray-800); }}
    .close-btn {{ 
      cursor: pointer; font-size: 24px; color: var(--gray-600);
      width: 32px; height: 32px; display: flex; align-items: center;
      justify-content: center; border-radius: 6px; transition: all 0.2s;
    }}
    .close-btn:hover {{ background: var(--gray-100); color: var(--gray-800); }}
    .sidebar-content {{ padding: 24px; }}
    .task-prop {{ margin-bottom: 20px; }}
    .prop-label {{ 
      font-size: 11px; font-weight: 600; color: var(--gray-600);
      text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;
    }}
    .prop-value {{ 
      font-size: 14px; color: var(--gray-800); word-break: break-word;
      white-space: pre-wrap; background: var(--gray-50); padding: 12px;
      border-radius: 6px; border: 1px solid var(--gray-200); line-height: 1.6;
    }}
    .prop-value.code {{ 
      font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
      font-size: 13px;
    }}
    .node {{ transition: all 0.3s ease; }}
    .edge {{ transition: all 0.3s ease; }}
    .node.dimmed {{ opacity: 0.15; }}
    .edge.dimmed {{ opacity: 0.1; }}
    .node.highlighted polygon, .node.highlighted ellipse, .node.highlighted path {{
      stroke: var(--accent) !important; stroke-width: 3px !important;
      filter: drop-shadow(0 0 8px rgba(49, 130, 206, 0.4));
    }}
    .node.upstream polygon, .node.upstream ellipse, .node.upstream path {{
      stroke: #4A90E2 !important; stroke-width: 3px !important; fill: #EBF5FF !important;
    }}
    .node.downstream polygon, .node.downstream ellipse, .node.downstream path {{
      stroke: var(--success) !important; stroke-width: 3px !important; fill: #F0FFF4 !important;
    }}
    .node.current polygon, .node.current ellipse, .node.current path {{
      stroke: var(--warning) !important; stroke-width: 4px !important; fill: #FFFAF0 !important;
    }}
    .edge.upstream path {{
      stroke: #4A90E2 !important; stroke-width: 2px !important; fill: none !important;
    }}
    .edge.upstream polygon {{
      stroke: #4A90E2 !important; stroke-width: 2px !important; fill: #4A90E2 !important;
    }}
    .edge.downstream path {{
      stroke: var(--success) !important; stroke-width: 2px !important; fill: none !important;
    }}
    .edge.downstream polygon {{
      stroke: var(--success) !important; stroke-width: 2px !important; fill: var(--success) !important;
    }}
    .controls {{
      position: absolute; bottom: 24px; right: 24px;
      display: flex; flex-direction: column; gap: 8px; z-index: 100;
    }}
    .btn {{
      width: 44px; height: 44px; border-radius: 8px;
      border: 1px solid var(--gray-200); background: white;
      color: var(--gray-800); font-size: 18px; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      box-shadow: var(--shadow); transition: all 0.2s ease; font-weight: 500;
    }}
    .btn:hover {{
      background: var(--primary); color: white; border-color: var(--primary);
      transform: translateY(-1px); box-shadow: var(--shadow-lg);
    }}
    .btn:active {{ transform: translateY(0); }}
  </style>
</head>
<body>
  <header>
    <div style="display: flex; align-items: center;">
      <a href="index.html" class="brand">
        <div class="brand-icon">D</div>
        <span>Digdag Workflow Graph</span>
      </a>
      <span class="workflow-title">{wf_name}</span>
    </div>
    <div style="display: flex; align-items: center;">
      <nav class="nav-links">
        <a href="index.html">Home</a>
        <a href="index.html">Workflows</a>
        <a href="scheduled_workflows.html">Scheduled</a>
        <a href="unscheduled_workflows.html">Unscheduled</a>
      </nav>
      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input type="text" id="searchInput" placeholder="Search tasks..." />
      </div>
    </div>
  </header>
  <main id="scene">{svg_content}</main>
  <div id="sidebar">
    <div class="sidebar-header">
      <div class="sidebar-title">Task Details</div>
      <div class="close-btn" onclick="closeSidebar()">×</div>
    </div>
    <div class="sidebar-content" id="sidebarContent">
      <p style="color: var(--gray-600); text-align: center; padding: 40px 20px;">
        Click on a task to view details
      </p>
    </div>
  </div>
  <div class="controls">
    <button class="btn" onclick="zoomIn()" title="Zoom In">+</button>
    <button class="btn" onclick="zoomOut()" title="Zoom Out">−</button>
    <button class="btn" onclick="resetZoom()" title="Reset">⟲</button>
  </div>
  <script>
    const taskDefs = {json.dumps(task_defs)};
    const scene = document.getElementById('scene');
    const svgElement = scene.querySelector('svg');
    const panzoomInstance = Panzoom(svgElement, {{
      maxScale: 5, minScale: 0.1, startScale: 1, canvas: true
    }});
    scene.parentElement.addEventListener('wheel', panzoomInstance.zoomWithWheel);
    function zoomIn() {{ panzoomInstance.zoomIn(); }}
    function zoomOut() {{ panzoomInstance.zoomOut(); }}
    function resetZoom() {{ panzoomInstance.reset(); }}
    function openSidebar(taskId) {{
      const sidebar = document.getElementById('sidebar');
      const content = document.getElementById('sidebarContent');
      const taskDef = taskDefs[taskId];
      if (!taskDef) {{
        content.innerHTML = '<p style="color: var(--gray-600);">No details available for this task.</p>';
        sidebar.classList.add('open');
        return;
      }}
      let html = '';
      html += '<div class="task-prop"><div class="prop-label">Task Name</div><div class="prop-value">' + taskId.split('__').pop() + '</div></div>';
      const operators = ['td>', 'sh>', 'py>', 'echo>', 'call>', 'require>', 'loop>', 'for_each>'];
      let operator = 'unknown';
      for (const op of operators) {{
        if (taskDef[op]) {{ operator = op; break; }}
      }}
      html += '<div class="task-prop"><div class="prop-label">Operator</div><div class="prop-value">' + operator + '</div></div>';
      if (taskDef[operator]) {{
        let commandHtml = escapeHtml(String(taskDef[operator]));
        if (taskDef._url && taskDef._url !== '#') {{
          commandHtml = '<a href="' + taskDef._url + '" target="_blank" style="color: var(--primary); text-decoration: underline;">' + commandHtml + '</a>';
        }}
        html += '<div class="task-prop"><div class="prop-label">Command</div><div class="prop-value code">' + commandHtml + '</div></div>';
      }}
      for (const [key, value] of Object.entries(taskDef)) {{
        if (!operators.includes(key) && !key.startsWith('_') && !key.startsWith('+')) {{
          html += '<div class="task-prop"><div class="prop-label">' + escapeHtml(key) + '</div><div class="prop-value">' + escapeHtml(JSON.stringify(value, null, 2)) + '</div></div>';
        }}
      }}
      content.innerHTML = html;
      sidebar.classList.add('open');
    }}
    function closeSidebar() {{ document.getElementById('sidebar').classList.remove('open'); }}
    function escapeHtml(text) {{
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }}
    const searchInput = document.getElementById('searchInput');
    const nodes = Array.from(document.querySelectorAll('.node'));
    const edges = Array.from(document.querySelectorAll('.edge'));
    searchInput.addEventListener('input', (e) => {{
      const query = e.target.value.toLowerCase().trim();
      if (!query) {{
        nodes.forEach(n => n.classList.remove('dimmed', 'highlighted'));
        edges.forEach(e => e.classList.remove('dimmed'));
        return;
      }}
      nodes.forEach(node => {{
        const title = node.querySelector('title');
        const text = title ? title.textContent.toLowerCase() : '';
        if (text.includes(query)) {{
          node.classList.remove('dimmed');
          node.classList.add('highlighted');
        }} else {{
          node.classList.add('dimmed');
          node.classList.remove('highlighted');
        }}
      }});
      edges.forEach(edge => edge.classList.add('dimmed'));
    }});
    const dependencyGraph = {{}};
    const reverseDependencyGraph = {{}};
    edges.forEach(edge => {{
      const title = edge.querySelector('title');
      if (!title) return;
      const match = title.textContent.match(/(.+)->(.+)/);
      if (!match) return;
      const [, from, to] = match.map(s => s.trim());
      if (!dependencyGraph[from]) dependencyGraph[from] = [];
      if (!reverseDependencyGraph[to]) reverseDependencyGraph[to] = [];
      dependencyGraph[from].push(to);
      reverseDependencyGraph[to].push(from);
    }});
    nodes.forEach(node => {{
      const title = node.querySelector('title');
      if (!title) return;
      const nodeId = title.textContent.trim();
      node.addEventListener('mouseenter', () => {{
        nodes.forEach(n => n.classList.add('dimmed'));
        edges.forEach(e => e.classList.add('dimmed'));
        node.classList.remove('dimmed');
        node.classList.add('current');
        const upstream = new Set();
        const queue = [nodeId];
        while (queue.length) {{
          const current = queue.shift();
          const deps = reverseDependencyGraph[current] || [];
          deps.forEach(dep => {{
            if (!upstream.has(dep)) {{ upstream.add(dep); queue.push(dep); }}
          }});
        }}
        upstream.forEach(upId => {{
          const upNode = nodes.find(n => n.querySelector('title')?.textContent.trim() === upId);
          if (upNode) {{ upNode.classList.remove('dimmed'); upNode.classList.add('upstream'); }}
        }});
        const downstream = new Set();
        const queue2 = [nodeId];
        while (queue2.length) {{
          const current = queue2.shift();
          const deps = dependencyGraph[current] || [];
          deps.forEach(dep => {{
            if (!downstream.has(dep)) {{ downstream.add(dep); queue2.push(dep); }}
          }});
        }}
        downstream.forEach(downId => {{
          const downNode = nodes.find(n => n.querySelector('title')?.textContent.trim() === downId);
          if (downNode) {{ downNode.classList.remove('dimmed'); downNode.classList.add('downstream'); }}
        }});
        edges.forEach(edge => {{
          const edgeTitle = edge.querySelector('title');
          if (!edgeTitle) return;
          const match = edgeTitle.textContent.match(/(.+)->(.+)/);
          if (!match) return;
          const [, from, to] = match.map(s => s.trim());
          if (upstream.has(from) || from === nodeId) {{
            edge.classList.remove('dimmed');
            edge.classList.add('upstream');
          }}
          if (downstream.has(to) || to === nodeId) {{
            edge.classList.remove('dimmed');
            edge.classList.add('downstream');
          }}
        }});
      }});
      node.addEventListener('mouseleave', () => {{
        nodes.forEach(n => n.classList.remove('dimmed', 'current', 'upstream', 'downstream'));
        edges.forEach(e => e.classList.remove('dimmed', 'upstream', 'downstream'));
      }});
      node.addEventListener('click', () => {{ openSidebar(nodeId); }});
    }});
  </script>
</body>
</html>"""
        
        html_path.write_text(html_content, encoding='utf-8')
        logger.info(f"Generated interactive graph: {{html_path}}")
        
        # Cleanup
        try:
            intermediate = outdir / file_path.stem
            if intermediate.exists():
                intermediate.unlink()
        except Exception as e:
            logger.debug(f"Cleanup warning: {{e}}")
        
        return (svg_filename, html_filename)
        
    except Exception as e:
        raise GraphRenderError(f"Failed to render interactive graph for {file_path}: {e}")


def render_tasks_with_links(
    g_svg: Digraph,
    g_map: Digraph,
    doc: Dict[str, Any],
    parent_stack: List[str],
    tasks: List[Tuple[str, Dict[str, Any]]],
    custom_colors: Optional[Dict[str, str]],
    max_depth: Optional[int],
    current_depth: int,
    file_path: Path,
    outdir: Path,
    project_root: Optional[Path],
    parent_is_parallel: bool = False,
    task_defs: Optional[Dict[str, Any]] = None,
    initial_prev_nodes: Optional[List[str]] = None
) -> List[str]:
    """Render tasks recursively with links for interactive map."""
    if max_depth is not None and current_depth >= max_depth:
        logger.debug(f"Reached max depth {max_depth}, skipping deeper tasks")
        return []
    
    # Track completion points from previous sibling (sequential) or all siblings (parallel)
    prev_last_nodes: List[str] = list(initial_prev_nodes) if initial_prev_nodes else []
    all_parallel_last_nodes: List[str] = []  # Accumulate when parent_is_parallel
    
    for (tkey, tbody) in tasks:
        tname = tkey.replace("+", "")
        node_id = normalized_id(parent_stack, tname)
        
        # Store definition if tracking
        if task_defs is not None and isinstance(tbody, dict):
            task_defs[node_id] = tbody
        
        # Determine operator
        op_pair = task_operator(tbody if isinstance(tbody, dict) else {})
        op = op_pair[0] if op_pair else None

        # Add icon to label
        icon = OPERATOR_ICONS.get(op, "") if op else ""
        if op == "root": icon = OPERATOR_ICONS.get("root", "")
        
        label_text = f"{icon} {tname}" if icon else tname
        label = f"{label_text}\\n[{op}]" if op else label_text
        
        shape, color, penwidth = style_for(op, custom_colors)
        
        # Default URL and tooltip
        url = "#"
        tooltip = f"Task: {tname}"
        
        # Handle special operators
        if op == "call>":
            target = tbody.get("call>")
            if target:
                url = f"{target}.html"
                tooltip = f"Call workflow: {target}"
        elif op == "require>":
            target = tbody.get("require>")
            if target:
                url = f"{target}.html"
                tooltip = f"Require workflow: {target}"
        elif op == "td>":
            # Link to SQL query page
            query_val = tbody.get("td>")
            if query_val:
                # Handle both string and dict formats
                # String: td>: queries/my_query.sql
                # Dict: td>: {query: queries/my_query.sql, database: mydb}
                query_str = None
                if isinstance(query_val, str):
                    query_str = query_val
                elif isinstance(query_val, dict):
                    # Extract query from dict (could be 'query' or other keys)
                    query_str = query_val.get('query') or query_val.get('sql')
                
                if query_str and isinstance(query_str, str):
                    if query_str.endswith('.sql'):
                        # File-based query
                        sql_path = project_root / query_str if project_root else Path(query_str)
                        if sql_path.exists():
                            project_name = file_path.parent.name
                            rel_path = read_and_generate_sql_page(sql_path, query_str, project_name, outdir)
                            url = rel_path
                            tooltip = f"View SQL: {query_str}"
                    else:
                        # Inline query
                        # Create a safe filename for the inline query
                        import hashlib
                        query_hash = hashlib.md5(query_str.encode('utf-8')).hexdigest()[:8]
                        inline_name = f"inline_{tname}_{query_hash}.sql"
                        
                        # Write inline SQL to temp file
                        queries_dir = outdir / "queries"
                        queries_dir.mkdir(parents=True, exist_ok=True)
                        inline_sql_path = queries_dir / inline_name
                        inline_sql_path.write_text(query_str, encoding='utf-8')
                        
                        project_name = file_path.parent.name
                        rel_path = read_and_generate_sql_page(inline_sql_path, f"inline: {tname}", project_name, outdir)
                        url = rel_path
                        tooltip = "View Inline SQL"

        # Check if this is a parallel group container
        is_parallel_group = False
        if isinstance(tbody, dict):
            is_parallel_group = tbody.get("_parallel", False)

        # Skip node creation entirely for parallel group containers
        # The children will be rendered in the cluster and connect from prev_last_nodes
        if not is_parallel_group:
            # Add URL to task_defs for sidebar
            if task_defs is not None and node_id in task_defs:
                task_defs[node_id]['_url'] = url

            # Add node to SVG graph
            g_svg.node(node_id, label, shape=shape, style="rounded,filled", color=color, penwidth=penwidth, fillcolor="white", URL=url, tooltip=tooltip, id=node_id)
            g_map.node(node_id, label, shape=shape, style="rounded,filled", color=color, penwidth=penwidth, fillcolor="white", URL=url, tooltip=tooltip)

            # Connect from previous nodes
            # Special case: if we have initial_prev_nodes, these are entry points from upstream
            # and should connect even if we're in a parallel group
            if prev_last_nodes:
                if not parent_is_parallel or (parent_is_parallel and initial_prev_nodes):
                    for last_node in prev_last_nodes:
                        g_svg.edge(last_node, node_id)
                        g_map.edge(last_node, node_id)
        
        # Current task's last nodes (default to itself)
        current_task_last_nodes: List[str] = []

        if isinstance(tbody, dict):
            # Operator-specific edges
            for loopish in ("loop>", "for_each>", "for_range>"):
                if loopish in tbody:
                    g_svg.edge(node_id, node_id, label=loopish, style="dotted", dir="none")
                    g_map.edge(node_id, node_id, label=loopish, style="dotted", dir="none")

            if "retry" in tbody:
                # Add a self-loop or similar to indicate retry
                # For now, just a dotted edge to self
                g_svg.edge(node_id, node_id, label="retry", style="dotted")
                g_map.edge(node_id, node_id, label="retry", style="dotted")
            
            # Handle special directive blocks (_error, _do, _else_do) AFTER regular tasks
            # These need special handling because they don't start with +
            special_directives = []
            
            # Check for _error block
            if "_error" in tbody and isinstance(tbody["_error"], dict):
                special_directives.append(("_error", tbody["_error"], "#D0021B", "[ERROR]"))
            
            # Check for _do block (inside if>, for_each>, etc.)
            if "_do" in tbody and isinstance(tbody["_do"], dict):
                special_directives.append(("_do", tbody["_do"], "#7ED321", "[DO]"))
            
            # Check for _else_do block (inside if>)
            if "_else_do" in tbody and isinstance(tbody["_else_do"], dict):
                special_directives.append(("_else_do", tbody["_else_do"], "#F5A623", "[ELSE]"))
            
            # Render each special directive block
            for directive_name, directive_body, color, icon in special_directives:
                directive_id = normalized_id(parent_stack + [tkey], directive_name)
                directive_label = f"{tname}\\n{directive_name}"
                directive_shape = NODE_SHAPES.get(directive_name, "box")
                
                # Create the directive node
                g_svg.node(directive_id, label=f"{icon} {directive_label}",
                          shape=directive_shape, color=color, style="filled",
                          fillcolor=f"{color}20", fontname="Inter")  # 20 = 12% opacity in hex
                g_map.node(directive_id, label=f"{icon} {directive_label}",
                          shape=directive_shape, color=color, style="filled",
                          fillcolor=f"{color}20", fontname="Inter")
                
                # Connect parent task to directive with dashed line
                g_svg.edge(node_id, directive_id, style="dashed", label=directive_name, color=color)
                g_map.edge(node_id, directive_id, style="dashed", label=directive_name, color=color)
                
                # Recursively render directive's child tasks
                directive_child_tasks = [(k, v) for k, v in directive_body.items() if is_task_key(k)]
                if directive_child_tasks:
                    render_tasks_with_links(
                        g_svg, g_map, doc, parent_stack + [tkey, directive_name],
                        directive_child_tasks, custom_colors, max_depth, current_depth + 1,
                        file_path, outdir, project_root,
                        task_defs=task_defs,
                        initial_prev_nodes=[directive_id]
                    )

            is_parallel = tbody.get("_parallel", False)

            # Recurse
            child_tasks = [(k, v) for k, v in tbody.items() if is_task_key(k)]
            if child_tasks:
                # Determine what the children should connect from
                if is_parallel_group:
                    # Parallel group: children connect from OUR previous nodes
                    nodes_to_connect_from = prev_last_nodes
                else:
                    # Sequential group: children connect from US
                    nodes_to_connect_from = [node_id]

                if is_parallel:
                    # Create a cluster for parallel tasks
                    cluster_name = f"cluster_{node_id}"
                    
                    # IMPORTANT: Create entry edges BEFORE entering cluster context
                    # This prevents external nodes (like root) from being pulled into the cluster
                    if is_parallel_group and nodes_to_connect_from:
                        # Connect from upstream nodes to each parallel child
                        for child_key, child_body in child_tasks:
                            child_node_id = normalized_id(parent_stack + [tkey], child_key.replace("+", ""))
                            for upstream_node in nodes_to_connect_from:
                                g_svg.edge(upstream_node, child_node_id)
                                g_map.edge(upstream_node, child_node_id)
                    
                    with g_svg.subgraph(name=cluster_name) as c:
                        c.attr(style='dashed', color='#aaaaaa', label='parallel', fontcolor='#aaaaaa', fontsize='10')
                        
                        # Pass None for initial_prev_nodes since we already created the entry edges
                        child_last_nodes = render_tasks_with_links(
                            c, g_map, doc, parent_stack + [tkey], child_tasks,
                            custom_colors, max_depth, current_depth + 1,
                            file_path, outdir, project_root,
                            parent_is_parallel=is_parallel,
                            task_defs=task_defs,
                            initial_prev_nodes=None if is_parallel_group else nodes_to_connect_from
                        )
                else:
                    child_last_nodes = render_tasks_with_links(
                        g_svg, g_map, doc, parent_stack + [tkey], child_tasks,
                        custom_colors, max_depth, current_depth + 1,
                        file_path, outdir, project_root,
                        parent_is_parallel=is_parallel,
                        task_defs=task_defs,
                        initial_prev_nodes=nodes_to_connect_from
                    )
                # This task completes when all its children complete
                current_task_last_nodes = child_last_nodes
            else:
                # Leaf task - it completes itself
                current_task_last_nodes = [node_id]
        else:
            # Non-dict task body (edge case)
            current_task_last_nodes = [node_id]
        
        # Update tracking based on whether we're in parallel mode
        if parent_is_parallel:
            # Accumulate ALL children's last nodes
            all_parallel_last_nodes.extend(current_task_last_nodes)
        else:
            # Sequential: next sibling connects from this task's completion
            prev_last_nodes = current_task_last_nodes
    
    # Return appropriate last nodes
    if parent_is_parallel:
        return all_parallel_last_nodes
    else:
        return prev_last_nodes
