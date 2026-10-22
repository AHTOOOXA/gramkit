class BackendException(Exception):
    """Base exception for application-specific errors"""

    def __init__(self, message: str = "Service is unavailable", name: str = "BackendException"):
        self.message = message
        self.name = name
        self.code = self.__class__.__name__
        super().__init__(self.message, self.name)


class UserNotFoundException(BackendException):
    """Raised when a user is not found"""
