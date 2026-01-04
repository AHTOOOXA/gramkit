class BackendException(Exception):
    """Base exception for application-specific errors"""

    def __init__(self, message: str = "Service is unavailable", name: str = "BackendException"):
        self.message = message
        self.name = name
        self.code = self.__class__.__name__
        super().__init__(self.message, self.name)


class UserNotFoundException(BackendException):
    """Raised when a user is not found"""


class FriendAlreadyExistsException(BackendException):
    """Raised when trying to add an existing friend"""


class NoAvailableReadingsError(BackendException):
    """Raised when user has no available readings"""

    pass


class NoChatMessagesError(BackendException):
    """Raised when user has no available chat messages"""

    pass


class NoTrainerAttemptsError(BackendException):
    """Raised when user has no available trainer attempts"""

    pass


class DailyReadingError(BackendException):
    """Base class for daily reading errors"""

    pass


class QuestionReadingError(BackendException):
    """Raised when question reading fails"""

    pass


class LLMError(BackendException):
    """Raised when LLM fails to generate response"""

    pass


class AllLLMProvidersFailedError(BackendException):
    """Raised when all LLM providers fail to generate response"""

    pass
