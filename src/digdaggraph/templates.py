"""Template management for HTML output."""

from pathlib import Path
from typing import Dict, List, Any, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template

from .exceptions import ConfigurationError
from .logger import get_logger

logger = get_logger(__name__)


# Default embedded template for schedule page (modern professional theme)
DEFAULT_SCHEDULE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Scheduled Workflows - Digdag Graph</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --primary: #1a365d;
    --primary-light: #2c5282;
    --accent: #3182ce;
    --gray-50: #f7fafc;
    --gray-100: #edf2f7;
    --gray-200: #e2e8f0;
    --gray-300: #cbd5e0;
    --gray-600: #4a5568;
    --gray-800: #1a202c;
    --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { 
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #ffffff; color: var(--gray-800); font-size: 14px; line-height: 1.5;
    min-height: 100vh; display: flex; flex-direction: column;
  }
  header { 
    padding: 0 32px; height: 64px; background: var(--primary);
    border-bottom: 1px solid #0f2744; display: flex;
    align-items: center; justify-content: space-between;
    box-shadow: var(--shadow); position: sticky; top: 0; z-index: 1000;
  }
  .brand { 
    font-weight: 600; font-size: 18px; color: white;
    text-decoration: none; display: flex; align-items: center; gap: 12px;
  }
  .brand-icon {
    width: 32px; height: 32px; background: var(--accent);
    border-radius: 6px; display: flex; align-items: center;
    justify-content: center; font-weight: 700; font-size: 16px;
  }
  .nav-links { display: flex; gap: 4px; }
  .nav-links a { 
    color: rgba(255, 255, 255, 0.9); text-decoration: none; 
    font-size: 14px; font-weight: 500; padding: 8px 16px;
    border-radius: 6px; transition: all 0.2s ease;
  }
  .nav-links a:hover { background: var(--primary-light); color: white; }
  .nav-links a.active { background: var(--accent); color: white; }
  
  main { flex: 1; padding: 32px; max-width: 1200px; width: 100%; margin: 0 auto; }
  h1 { font-size: 24px; font-weight: 700; margin-bottom: 8px; color: var(--gray-800); }
  .subtitle { color: var(--gray-600); margin-bottom: 24px; }
  
  .controls { display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; }
  input[type="search"], select {
    background: white; color: var(--gray-800); border: 1px solid var(--gray-200);
    border-radius: 6px; padding: 10px 14px; outline: none; font-family: 'Inter', sans-serif;
    font-size: 14px; transition: all 0.2s;
  }
  input[type="search"] { flex: 1; min-width: 250px; }
  input[type="search"]:focus, select:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(49, 130, 206, 0.1); }
  input[type="search"]::placeholder { color: var(--gray-600); }
  select { padding-right: 32px; }
  
  table { width: 100%; border-collapse: separate; border-spacing: 0; 
    border: 1px solid var(--gray-200); border-radius: 8px;
    background: white; box-shadow: var(--shadow);
  }
  thead th { 
    background: var(--gray-50); border-bottom: 1px solid var(--gray-200);
    text-align: left; padding: 14px 16px; font-weight: 600; font-size: 13px;
    color: var(--gray-800); position: sticky; top: 64px; z-index: 1;
  }
  tbody tr { background: white; transition: background 0.15s; }
  tbody tr:nth-child(even) { background: var(--gray-50); }
  tbody tr:hover { background: var(--gray-100); }
  tbody td { padding: 14px 16px; border-bottom: 1px solid var(--gray-200); vertical-align: top; }
  tbody tr:last-child td { border-bottom: none; }
  
  code { 
    background: var(--gray-100); padding: 3px 8px; border-radius: 4px;
    font-family: 'SF Mono', Monaco, monospace; font-size: 13px;
    color: var(--gray-800); display: inline-block;
  }
  
  .c-project { width: 18%; font-weight: 500; }
  .c-workflow { width: 25%; }
  .c-schedule { width: 57%; }
  .badge { 
    background: var(--accent); color: white; border-radius: 999px;
    padding: 4px 12px; font-size: 12px; font-weight: 500;
  }
  a { color: var(--accent); text-decoration: none; font-weight: 500; }
  a:hover { text-decoration: underline; }
  
  footer { 
    color: var(--gray-600); font-size: 12px; padding: 24px 32px;
    text-align: center; border-top: 1px solid var(--gray-200);
  }
</style>
</head>
<body>

<header>
  <a href="index.html" class="brand">
    <div class="brand-icon">D</div>
    <span>Digdag Workflow Graph</span>
  </a>
  <nav class="nav-links">
    <a href="index.html">Home</a>
    <a href="index.html">Workflows</a>
    <a href="scheduled_workflows.html" class="active">Scheduled</a>
    <a href="unscheduled_workflows.html">Unscheduled</a>
  </nav>
</header>

<main>
  <h1>Scheduled Workflows</h1>
  <div class="subtitle">Search and filter schedules from your Digdag projects</div>
  
  <div class="controls">
    <input id="q" type="search" placeholder="Search workflows, projects, schedule text...">
    <select id="proj">
      <option value="">All projects</option>
      {% for p in projects %}
      <option value="{{ p }}">{{ p }}</option>
      {% endfor %}
    </select>
    <span class="badge" id="count"></span>
  </div>
  
  <table id="tbl">
    <thead>
      <tr>
        <th>Project</th>
        <th>Workflow</th>
        <th>Schedule</th>
      </tr>
    </thead>
    <tbody>
      {% for it in items %}
      <tr data-project="{{ it.project }}">
        <td class="c-project">{{ it.project }}</td>
        <td class="c-workflow"><a href="{{ it.svg }}">{{ it.workflow }}</a></td>
        <td class="c-schedule"><code>{{ it.schedule }}{% if it.timezone %} ({{ it.timezone }}){% endif %}</code></td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</main>

<footer>Generated by digdag-graph</footer>

<script>
(function() {
  const q = document.getElementById('q');
  const proj = document.getElementById('proj');
  const tbody = document.querySelector('#tbl tbody');
  const count = document.getElementById('count');
  const rows = Array.from(tbody.querySelectorAll('tr'));

  function norm(s) { return (s||'').toLowerCase(); }

  function apply() {
    const term = norm(q.value);
    const pf = proj.value;
    let visible = 0;

    rows.forEach(tr => {
      const projName = tr.getAttribute('data-project');
      const text = norm(tr.innerText);
      const matchesProj = !pf || projName === pf;
      const matchesText = !term || text.includes(term);

      if (matchesProj && matchesText) {
        tr.style.display = 'table-row';
        visible++;
      } else {
        tr.style.display = 'none';
      }
    });

    count.textContent = visible + ' shown';
  }

  if (q && proj) {
    q.addEventListener('input', apply);
    proj.addEventListener('change', apply);
    // Initial apply
    setTimeout(apply, 10);
  }
})();
</script>

</body>
</html>
"""


# Default embedded template for index page (modern professional theme)
DEFAULT_INDEX_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Digdag Workflows - Digdag Graph</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --primary: #1a365d;
      --primary-light: #2c5282;
      --accent: #3182ce;
      --success: #38a169;
      --gray-50: #f7fafc;
      --gray-100: #edf2f7;
      --gray-200: #e2e8f0;
      --gray-600: #4a5568;
      --gray-800: #1a202c;
      --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #ffffff; color: var(--gray-800); font-size: 14px; line-height: 1.5;
      min-height: 100vh; display: flex; flex-direction: column;
    }
    header {
      padding: 0 32px; height: 64px; background: var(--primary);
      border-bottom: 1px solid #0f2744; display: flex;
      align-items: center; justify-content: space-between;
      box-shadow: var(--shadow); position: sticky; top: 0; z-index: 1000;
    }
    .brand {
      font-weight: 600; font-size: 18px; color: white;
      text-decoration: none; display: flex; align-items: center; gap: 12px;
    }
    .brand-icon {
      width: 32px; height: 32px; background: var(--accent);
      border-radius: 6px; display: flex; align-items: center;
      justify-content: center; font-weight: 700; font-size: 16px;
    }
    .nav-links { display: flex; gap: 4px; }
    .nav-links a {
      color: rgba(255, 255, 255, 0.9); text-decoration: none;
      font-size: 14px; font-weight: 500; padding: 8px 16px;
      border-radius: 6px; transition: all 0.2s ease;
    }
    .nav-links a:hover { background: var(--primary-light); color: white; }
    .nav-links a.active { background: var(--accent); color: white; }
    
    main { flex: 1; padding: 32px; max-width: 1200px; width: 100%; margin: 0 auto; }
    h1 { font-size: 24px; font-weight: 700; margin-bottom: 8px; color: var(--gray-800); }
    .subtitle { color: var(--gray-600); margin-bottom: 32px; }
    
    .workflow-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 20px; margin-top: 24px;
    }
    .workflow-card {
      border: 1px solid var(--gray-200); border-radius: 8px;
      padding: 20px; background: white; box-shadow: var(--shadow);
      transition: all 0.2s ease;
    }
    .workflow-card:hover {
      box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
      transform: translateY(-2px);
    }
    .workflow-card h3 {
      margin: 0 0 12px; font-size: 18px; font-weight: 600; color: var(--gray-800);
    }
    .workflow-card p {
      margin: 8px 0; font-size: 14px; color: var(--gray-600);
    }
    .workflow-card a {
      color: var(--accent); text-decoration: none; font-weight: 500;
    }
    .workflow-card a:hover { text-decoration: underline; }
    code {
      background: var(--gray-100); padding: 3px 8px; border-radius: 4px;
      font-family: 'SF Mono', Monaco, monospace; font-size: 13px;
      color: var(--gray-800);
    }
    .schedule-badge {
      display: inline-block; background: var(--success); color: white;
      padding: 4px 10px; border-radius: 4px; font-size: 12px;
      font-weight: 500; margin-top: 8px;
    }
    .quick-links {
      display: flex; gap: 12px; margin-top: 32px; padding-top: 32px;
      border-top: 1px solid var(--gray-200);
    }
    .quick-link {
      flex: 1; padding: 16px; background: var(--gray-50);
      border: 1px solid var(--gray-200); border-radius: 8px;
      text-decoration: none; color: var(--gray-800);
      transition: all 0.2s ease;
    }
    .quick-link:hover {
      background: white; box-shadow: var(--shadow);
    }
    .quick-link h4 {
      font-size: 14px; font-weight: 600; margin-bottom: 4px;
    }
    .quick-link p {
      font-size: 13px; color: var(--gray-600); margin: 0;
    }
    
    footer {
      color: var(--gray-600); font-size: 12px; padding: 24px 32px;
      text-align: center; border-top: 1px solid var(--gray-200);
    }
  </style>
</head>
<body>
  <header>
    <a href="index.html" class="brand">
      <div class="brand-icon">D</div>
      <span>Digdag Workflow Graph</span>
    </a>
    <nav class="nav-links">
      <a href="index.html" class="active">Home</a>
      <a href="index.html">Workflows</a>
      <a href="scheduled_workflows.html">Scheduled</a>
      <a href="unscheduled_workflows.html">Unscheduled</a>
    </nav>
  </header>
  
  <main>
    <h1>Digdag Workflows</h1>
    <div class="subtitle">Total workflows: {{ workflows|length }}</div>
    
    <div class="workflow-grid">
    {% for wf in workflows %}
      <div class="workflow-card">
        <h3>{{ wf.name }}</h3>
        <p><code>{{ wf.file }}</code></p>
        {% if wf.schedule %}
        <p>Schedule: <code>{{ wf.schedule }}</code></p>
        <span class="schedule-badge">Scheduled</span>
        {% endif %}
        {% if wf.graph %}
        <p><a href="{{ wf.graph }}">View Graph →</a></p>
        {% endif %}
      </div>
    {% endfor %}
    </div>
    
    {% if scheduled_workflows %}
    <div class="quick-links">
      <a href="scheduled_workflows.html" class="quick-link">
        <h4>Scheduled Workflows</h4>
        <p>View all workflows with schedules</p>
      </a>
      <a href="unscheduled_workflows.html" class="quick-link">
        <h4>Unscheduled Workflows</h4>
        <p>View workflows without schedules</p>
      </a>
    </div>
    {% endif %}
  </main>
  
  <footer>Generated by digdag-graph</footer>
</body>
</html>
"""


# Default embedded template for unscheduled workflows page (modern professional theme)
DEFAULT_UNSCHEDULED_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Unscheduled Workflows - Digdag Graph</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --primary: #1a365d;
      --primary-light: #2c5282;
      --accent: #3182ce;
      --gray-50: #f7fafc;
      --gray-100: #edf2f7;
      --gray-200: #e2e8f0;
      --gray-600: #4a5568;
      --gray-800: #1a202c;
      --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #ffffff; color: var(--gray-800); font-size: 14px; line-height: 1.5;
      min-height: 100vh; display: flex; flex-direction: column;
    }
    header {
      padding: 0 32px; height: 64px; background: var(--primary);
      border-bottom: 1px solid #0f2744; display: flex;
      align-items: center; justify-content: space-between;
      box-shadow: var(--shadow); position: sticky; top: 0; z-index: 1000;
    }
    .brand {
      font-weight: 600; font-size: 18px; color: white;
      text-decoration: none; display: flex; align-items: center; gap: 12px;
    }
    .brand-icon {
      width: 32px; height: 32px; background: var(--accent);
      border-radius: 6px; display: flex; align-items: center;
      justify-content: center; font-weight: 700; font-size: 16px;
    }
    .nav-links { display: flex; gap: 4px; }
    .nav-links a {
      color: rgba(255, 255, 255, 0.9); text-decoration: none;
      font-size: 14px; font-weight: 500; padding: 8px 16px;
      border-radius: 6px; transition: all 0.2s ease;
    }
    .nav-links a:hover { background: var(--primary-light); color: white; }
    .nav-links a.active { background: var(--accent); color: white; }
    
    main { flex: 1; padding: 32px; max-width: 1200px; width: 100%; margin: 0 auto; }
    h1 { font-size: 24px; font-weight: 700; margin-bottom: 8px; color: var(--gray-800); }
    .subtitle { color: var(--gray-600); margin-bottom: 24px; }
    
    .controls { display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; }
    input[type="search"], select {
      background: white; color: var(--gray-800); border: 1px solid var(--gray-200);
      border-radius: 6px; padding: 10px 14px; outline: none; font-family: 'Inter', sans-serif;
      font-size: 14px; transition: all 0.2s;
    }
    input[type="search"] { flex: 1; min-width: 250px; }
    input[type="search"]:focus, select:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(49, 130, 206, 0.1); }
    input[type="search"]::placeholder { color: var(--gray-600); }
    select { padding-right: 32px; }
    
    table { width: 100%; border-collapse: separate; border-spacing: 0; 
      border: 1px solid var(--gray-200); border-radius: 8px;
      background: white; box-shadow: var(--shadow);
    }
    thead th { 
      background: var(--gray-50); border-bottom: 1px solid var(--gray-200);
      text-align: left; padding: 14px 16px; font-weight: 600; font-size: 13px;
      color: var(--gray-800); position: sticky; top: 64px; z-index: 1;
    }
    tbody tr { background: white; transition: background 0.15s; }
    tbody tr:nth-child(even) { background: var(--gray-50); }
    tbody tr:hover { background: var(--gray-100); }
    tbody td { padding: 14px 16px; border-bottom: 1px solid var(--gray-200); vertical-align: top; }
    tbody tr:last-child td { border-bottom: none; }
    
    code { 
      background: var(--gray-100); padding: 3px 8px; border-radius: 4px;
      font-family: 'SF Mono', Monaco, monospace; font-size: 13px;
      color: var(--gray-800); display: inline-block;
    }
    
    .c-project { width: 20%; font-weight: 500; }
    .c-workflow { width: 30%; }
    .c-file { width: 50%; }
    .badge { 
      background: var(--accent); color: white; border-radius: 999px;
      padding: 4px 12px; font-size: 12px; font-weight: 500;
    }
    a { color: var(--accent); text-decoration: none; font-weight: 500; }
    a:hover { text-decoration: underline; }
    
    footer { 
      color: var(--gray-600); font-size: 12px; padding: 24px 32px;
      text-align: center; border-top: 1px solid var(--gray-200);
    }
  </style>
</head>
<body>

<header>
  <a href="index.html" class="brand">
    <div class="brand-icon">D</div>
    <span>Digdag Workflow Graph</span>
  </a>
  <nav class="nav-links">
    <a href="index.html">Home</a>
    <a href="index.html">Workflows</a>
    <a href="scheduled_workflows.html">Scheduled</a>
    <a href="unscheduled_workflows.html" class="active">Unscheduled</a>
  </nav>
</header>

<main>
  <h1>Unscheduled Workflows</h1>
  <div class="subtitle">Search and filter unscheduled workflows</div>
  
  <div class="controls">
    <input id="q" type="search" placeholder="Search workflows, projects, files...">
    <select id="proj">
      <option value="">All projects</option>
      {% for p in projects %}
      <option value="{{ p }}">{{ p }}</option>
      {% endfor %}
    </select>
    <span class="badge" id="count"></span>
  </div>
  
  <table id="tbl">
    <thead>
      <tr>
        <th>Project</th>
        <th>Workflow</th>
        <th>File Path</th>
      </tr>
    </thead>
    <tbody>
      {% for wf in workflows %}
      <tr data-project="{{ wf.project }}">
        <td class="c-project">{{ wf.project }}</td>
        <td class="c-workflow"><a href="{{ wf.graph }}">{{ wf.name }}</a></td>
        <td class="c-file"><code>{{ wf.file }}</code></td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</main>

<footer>Generated by digdag-graph</footer>

<script>
(function() {
  const q = document.getElementById('q');
  const proj = document.getElementById('proj');
  const tbody = document.querySelector('#tbl tbody');
  const count = document.getElementById('count');
  const rows = Array.from(tbody.querySelectorAll('tr'));

  function norm(s) { return (s||'').toLowerCase(); }

  function apply() {
    const term = norm(q.value);
    const pf = proj.value;
    let visible = 0;

    rows.forEach(tr => {
      const projName = tr.getAttribute('data-project');
      const text = norm(tr.innerText);
      const matchesProj = !pf || projName === pf;
      const matchesText = !term || text.includes(term);

      if (matchesProj && matchesText) {
        tr.style.display = 'table-row';
        visible++;
      } else {
        tr.style.display = 'none';
      }
    });

    count.textContent = visible + ' shown';
  }

  if (q && proj) {
    q.addEventListener('input', apply);
    proj.addEventListener('change', apply);
    // Initial apply
    setTimeout(apply, 10);
  }
})();
</script>
</body>
</html>
"""


class TemplateManager:
    """Manage Jinja2 templates for HTML output."""
    
    def __init__(self, template_dir: Optional[Path] = None):
        """Initialize template manager.
        
        Args:
            template_dir: Optional custom template directory
        """
        self.template_dir = template_dir
        self.env = self._create_environment()
    
    def _create_environment(self) -> Environment:
        """Create Jinja2 environment.
        
        Returns:
            Configured Jinja2 Environment
        """
        if self.template_dir and self.template_dir.exists():
            logger.info(f"Using custom templates from {self.template_dir}")
            return Environment(
                loader=FileSystemLoader(str(self.template_dir)),
                autoescape=select_autoescape(['html', 'xml'])
            )
        else:
            # Check for bundled templates
            bundled_templates = Path(__file__).parent.parent.parent / "templates"
            if bundled_templates.exists():
                logger.debug(f"Using bundled templates from {bundled_templates}")
                return Environment(
                    loader=FileSystemLoader(str(bundled_templates)),
                    autoescape=select_autoescape(['html', 'xml'])
                )
            else:
                # Use embedded templates
                logger.debug("Using embedded templates")
                return Environment(autoescape=select_autoescape(['html', 'xml']))
    
    def get_template(self, name: str) -> Template:
        """Get a template by name.
        
        Args:
            name: Template name (e.g., 'schedule.html.j2')
        
        Returns:
            Jinja2 Template instance
        """
        try:
            return self.env.get_template(name)
        except Exception:
            # Fall back to embedded templates
            logger.debug(f"Template {name} not found, using embedded default")
            if name == 'schedule.html.j2':
                return self.env.from_string(DEFAULT_SCHEDULE_TEMPLATE)
            elif name == 'index.html.j2':
                return self.env.from_string(DEFAULT_INDEX_TEMPLATE)
            elif name == 'unscheduled.html.j2':
                return self.env.from_string(DEFAULT_UNSCHEDULED_TEMPLATE)
            else:
                raise ConfigurationError(f"Template not found: {name}")
    
    def render_schedule_page(self, items: List[Dict[str, str]], output_path: Path):
        """Render schedule page.
        
        Args:
            items: List of schedule items
            output_path: Output file path
        """
        template = self.get_template('schedule.html.j2')
        
        # Extract unique projects for filter dropdown
        projects = sorted(set(item.get('project', 'unknown') for item in items))
        
        html = template.render(items=items, projects=projects)
        output_path.write_text(html, encoding='utf-8')
        logger.info(f"Generated schedule page: {output_path}")
    
    def render_index_page(self, workflows: List[Dict[str, Any]], output_path: Path):
        """Render index page.
        
        Args:
            workflows: List of workflow information
            output_path: Output file path
        """
        template = self.get_template('index.html.j2')
        scheduled = [wf for wf in workflows if wf.get('schedule')]
        html = template.render(workflows=workflows, scheduled_workflows=scheduled)
        output_path.write_text(html, encoding='utf-8')
        logger.info(f"Generated index page: {output_path}")
    
    def render_unscheduled_page(self, workflows: List[Dict[str, Any]], output_path: Path):
        """Render unscheduled workflows page.
        
        Args:
            workflows: List of workflow information
            output_path: Output file path
        """
        template = self.get_template('unscheduled.html.j2')
        unscheduled = [wf for wf in workflows if not wf.get('schedule')]
        
        # Extract unique projects for filter dropdown
        projects = sorted(set(wf.get('project', 'unknown') for wf in unscheduled))
        
        html = template.render(workflows=unscheduled, projects=projects)
        output_path.write_text(html, encoding='utf-8')
        logger.info(f"Generated unscheduled workflows page: {output_path}")
