class ClanBaseException(Exception):
    pass

class ImmutableRecordError(ClanBaseException):
    pass

class InvalidStatusTransitionError(ClanBaseException):
    pass

class InsufficientFundsError(ClanBaseException):
    pass

class PermissionDeniedError(ClanBaseException):
    pass

class DuplicateRelationshipError(ClanBaseException):
    pass

class CircularAncestryError(ClanBaseException):
    pass

class ApprovalRequiredError(ClanBaseException):
    pass