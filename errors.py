class SourcePointError(Exception):
    """Base exception for all application-specific errors."""
    pass

class BusinessValidationError(SourcePointError):
    """Raised when a business rule is violated (e.g. negative stock)."""
    def __init__(self, message="Invalid operation."):
        self.message = message
        super().__init__(self.message)

class ResourceNotFoundError(SourcePointError):
    """Raised when a requested resource (ID) does not exist."""
    def __init__(self, resource_name, resource_id):
        self.message = f"{resource_name} with ID {resource_id} not found."
        super().__init__(self.message)

class PermissionDeniedError(SourcePointError):
    """Raised when a user tries to access a forbidden resource."""
    def __init__(self, message="You do not have permission to perform this action."):
        self.message = message
        super().__init__(self.message)

class StockError(BusinessValidationError):
    """Specific error for inventory issues."""
    pass