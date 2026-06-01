"""GenesiX custom exceptions hierarchy."""


class GenesiXError(Exception):
    """Base exception for all GenesiX errors."""
    pass


class DataFetchError(GenesiXError):
    """Failed to fetch data from external source."""
    
    def __init__(self, source: str, detail: str = ""):
        self.source = source
        self.detail = detail
        msg = f"Failed to fetch data from {source}"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


class InsufficientDataError(GenesiXError):
    """Not enough data for the requested computation."""
    
    def __init__(self, required: int, available: int, context: str = ""):
        self.required = required
        self.available = available
        self.context = context
        msg = f"Need {required} data points, only {available} available"
        if context:
            msg += f" ({context})"
        super().__init__(msg)


class ModelTrainingError(GenesiXError):
    """ML model failed to train."""
    
    def __init__(self, model_type: str, detail: str = ""):
        self.model_type = model_type
        self.detail = detail
        msg = f"{model_type} training failed"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


class PortfolioError(GenesiXError):
    """Invalid portfolio configuration."""
    
    def __init__(self, detail: str = ""):
        self.detail = detail
        super().__init__(f"Invalid portfolio: {detail}" if detail else "Invalid portfolio")


class CacheError(GenesiXError):
    """Cache read/write failure."""
    
    def __init__(self, operation: str, detail: str = ""):
        self.operation = operation
        self.detail = detail
        msg = f"Cache {operation} failed"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


class ValidationError(GenesiXError):
    """Input validation error."""
    
    def __init__(self, field: str, detail: str = ""):
        self.field = field
        self.detail = detail
        msg = f"Validation error in {field}"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)
