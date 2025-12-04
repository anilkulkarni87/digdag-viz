"""Custom exceptions for digdag graph."""


class DigdagGraphError(Exception):
    """Base exception for digdag graph errors."""
    pass


class WorkflowParseError(DigdagGraphError):
    """Error parsing workflow file."""
    pass


class GraphRenderError(DigdagGraphError):
    """Error rendering graph."""
    pass


class ConfigurationError(DigdagGraphError):
    """Error in configuration."""
    pass


class ValidationError(DigdagGraphError):
    """Input validation error."""
    pass
