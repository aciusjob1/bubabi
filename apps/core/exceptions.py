"""
Custom exception hierarchy for Bubabi system.
"""


class BubabiException(Exception):
    """Base exception for all Bubabi errors."""
    status_code = 400
    detail = "An error occurred"
    
    def __init__(self, detail=None, *args, **kwargs):
        if detail:
            self.detail = detail
        super().__init__(self.detail, *args, **kwargs)


class AuthenticationError(BubabiException):
    status_code = 401
    detail = "Authentication failed"


class TermsNotAcceptedError(AuthenticationError):
    detail = "User must accept terms before proceeding"


class AuthorizationError(BubabiException):
    status_code = 403
    detail = "Permission denied"


class InsufficientPermissionError(AuthorizationError):
    detail = "You lack the required permission"


class ValidationError(BubabiException):
    status_code = 400
    detail = "Invalid input"


class InvalidFileError(ValidationError):
    detail = "Invalid or malicious file"


class InsufficientFundsError(BubabiException):
    status_code = 402
    detail = "Insufficient funds"


class LoanLimitExceededError(BubabiException):
    status_code = 400
    detail = "Loan request exceeds clan limits"


class DataIntegrityError(BubabiException):
    status_code = 409
    detail = "Data conflict or inconsistency"


class ImmutableRecordError(DataIntegrityError):
    detail = "Cannot modify immutable record"


class SeparationOfDutiesError(DataIntegrityError):
    detail = "Separation of duties violation"


class NotFoundError(BubabiException):
    status_code = 404
    detail = "Resource not found"
