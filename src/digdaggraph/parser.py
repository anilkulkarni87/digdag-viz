"""YAML parser for Digdag workflow files with !include support."""

import io
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import yaml

from .exceptions import WorkflowParseError, ValidationError
from .logger import get_logger

logger = get_logger(__name__)


class LoaderWithInclude(yaml.SafeLoader):
    """YAML loader that understands !include and resolves relative to the current file."""
    
    def __init__(self, stream, root_dir: Path):
        """Initialize loader with root directory for resolving includes.
        
        Args:
            stream: YAML stream (text or file-like)
            root_dir: Root directory for resolving relative includes
        """
        if isinstance(stream, (str, bytes)):
            stream = io.StringIO(stream if isinstance(stream, str) else stream.decode("utf-8"))
        super().__init__(stream)
        self._root_dir = Path(root_dir)


def _include_constructor(loader: LoaderWithInclude, node):
    """Handle !include directive in YAML files.
    
    Supports:
        key: !include relative/path.yml
    
    If the target is YAML (.yml/.yaml/.dig), parse it (recursively supports !include).
    Otherwise, return the file contents as a string.
    
    Args:
        loader: YAML loader instance
        node: YAML node containing the include path
    
    Returns:
        Parsed YAML content or raw text
    
    Raises:
        FileNotFoundError: If included file doesn't exist
    """
    rel_path = loader.construct_scalar(node)
    target = (loader._root_dir / rel_path).resolve()

    if not target.exists():
        raise FileNotFoundError(f"!include file not found: {target}")
    
    # Skip directories
    if target.is_dir():
        logger.warning(f"!include target is a directory, skipping: {target}")
        return None

    # If including YAML, parse it so structures merge naturally
    if target.suffix.lower() in (".yml", ".yaml", ".dig"):
        text = target.read_text(encoding="utf-8")
        # Support multi-doc includes; return a list if multiple docs
        docs = list(yaml.load_all(text, Loader=lambda s: LoaderWithInclude(s, target.parent)))
        return docs[0] if len(docs) == 1 else docs
    else:
        # Non-YAML: return raw text
        return target.read_text(encoding="utf-8")


# Register the !include tag
yaml.add_constructor("!include", _include_constructor, Loader=LoaderWithInclude)


def _yaml_load_all_with_includes(text: str, base_dir: Path):
    """Load YAML with !include support.
    
    Args:
        text: YAML text content
        base_dir: Base directory for resolving includes
    
    Returns:
        Generator of parsed YAML documents
    """
    return yaml.load_all(text, Loader=lambda s: LoaderWithInclude(s, base_dir))


def validate_path(path: Path, base_dir: Optional[Path] = None) -> Path:
    """Validate that a path exists and is within base directory if specified.
    
    Args:
        path: Path to validate
        base_dir: Optional base directory for security check
    
    Returns:
        Resolved path
    
    Raises:
        ValidationError: If path is invalid or outside base directory
    """
    if not path.exists():
        raise ValidationError(f"Path does not exist: {path}")
    
    resolved = path.resolve()
    
    if base_dir:
        base_resolved = base_dir.resolve()
        try:
            resolved.relative_to(base_resolved)
        except ValueError:
            raise ValidationError(f"Path outside base directory: {path}")
    
    return resolved


def load_dig_docs(
    path: Path,
    exclude_patterns: Optional[List[str]] = None,
    include_patterns: Optional[List[str]] = None
) -> List[Tuple[Path, Dict[str, Any]]]:
    """Load .dig workflow documents with filtering.
    
    Args:
        path: Path to .dig file or directory
        exclude_patterns: Glob patterns to exclude
        include_patterns: Glob patterns to include (if specified, only these are included)
    
    Returns:
        List of (file_path, document) tuples
    
    Raises:
        ValidationError: If path is invalid
        WorkflowParseError: If all files fail to parse
    """
    exclude_patterns = exclude_patterns or []
    include_patterns = include_patterns or []
    
    # Validate path
    path = validate_path(path)
    
    # Collect .dig files
    paths = []
    if path.is_dir():
        all_digs = list(path.rglob("*.dig"))
        logger.debug(f"Found {len(all_digs)} .dig files in {path}")
        
        for p in all_digs:
            # Check exclude patterns
            if any(p.match(pattern) for pattern in exclude_patterns):
                logger.debug(f"Excluding {p} (matches exclude pattern)")
                continue
            
            # Check include patterns (if specified)
            if include_patterns and not any(p.match(pattern) for pattern in include_patterns):
                logger.debug(f"Excluding {p} (doesn't match include pattern)")
                continue
            
            paths.append(p)
    elif path.suffix == ".dig":
        paths = [path]
    else:
        raise ValidationError(f"Invalid path: must be .dig file or directory: {path}")
    
    logger.info(f"Processing {len(paths)} .dig files")
    
    # Parse documents
    out = []
    errors = []
    
    for p in paths:
        try:
            logger.debug(f"Parsing {p}")
            with p.open("r", encoding="utf-8") as f:
                docs = list(_yaml_load_all_with_includes(f.read(), p.parent))
                for doc in docs:
                    if isinstance(doc, dict):
                        out.append((p, doc))
                    else:
                        logger.warning(f"Skipping non-dict document in {p}")
        except Exception as e:
            error_msg = f"Failed to parse {p}: {e}"
            logger.error(error_msg)
            errors.append((p, str(e)))
    
    # Check results
    if errors and not out:
        # All files failed
        error_details = "\n".join([f"  - {p}: {e}" for p, e in errors])
        raise WorkflowParseError(f"Failed to parse all {len(errors)} workflow files:\n{error_details}")
    elif errors:
        # Some files failed
        logger.warning(f"Successfully parsed {len(out)} files, {len(errors)} failed")
    
    logger.info(f"Successfully loaded {len(out)} workflow documents")
    return out


def find_workflow_name(doc: Dict[str, Any], file_path: Optional[Path] = None) -> str:
    """Extract workflow name from document or filename.
    
    Args:
        doc: Workflow document dictionary
        file_path: Optional path to the workflow file
    
    Returns:
        Workflow name
    """
    # Prefer filename stem if available
    if file_path:
        return file_path.stem

    # Fallback: Find first +key (task)
    plus_keys = [k for k in doc.keys() if isinstance(k, str) and k.startswith("+")]
    if plus_keys:
        return plus_keys[0][1:]  # Remove + prefix
    
    # Fallback to _name field
    return doc.get("_name", "workflow")


def is_task_key(k: str) -> bool:
    """Check if a key represents a task (starts with +).
    
    Args:
        k: Key to check
    
    Returns:
        True if key is a task key
    """
    return isinstance(k, str) and k.startswith("+")


def task_operator(task_body: Dict[str, Any]) -> Optional[Tuple[str, Any]]:
    """Extract operator from task body.
    
    Args:
        task_body: Task body dictionary
    
    Returns:
        Tuple of (operator, value) or None if no operator found
    """
    if not isinstance(task_body, dict):
        return None
    
    # Supported operators
    operators = [
        "sh>", "echo>", "td>", "call>", "require>", "loop>", 
        "for_each>", "for_range>", "if>", "py>", "rb>", "http_call>"
    ]
    
    for op in operators:
        if op in task_body:
            return (op, task_body[op])
    
    return None


def schedule_info(doc: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Extract schedule information from workflow document.
    
    Args:
        doc: Workflow document dictionary
    
    Returns:
        Tuple of (schedule_expression, timezone) or (None, None)
    """
    # Check both 'schedule' and '_schedule' keys
    sched = doc.get("schedule") or doc.get("_schedule")
    if not isinstance(sched, dict):
        return (None, None)
    
    # Digdag supports various schedule formats
    # Check for cron> (with >), cron, daily>, daily, etc.
    cron = (
        sched.get("cron>") or  # Most common format
        sched.get("cron") or 
        sched.get("daily>") or
        sched.get("daily") or 
        sched.get("weekly>") or
        sched.get("weekly") or 
        sched.get("hourly>") or
        sched.get("hourly")
    )
    
    tz = sched.get("timezone") or sched.get("time_zone") or doc.get("timezone")
    
    if isinstance(cron, (int, float)):
        cron = str(cron)
    
    return (cron, tz)
