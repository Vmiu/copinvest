import enum


class UserRole(str, enum.Enum):
    adviser = "adviser"
    senior_adviser = "senior_adviser"
    compliance = "compliance"


class SensitivityTier(int, enum.Enum):
    public = 1
    internal = 2
    restricted = 3
    confidential = 4


class AdviserAction(str, enum.Enum):
    approved = "approved"
    edited = "edited"
    discarded = "discarded"


class AuditStatus(str, enum.Enum):
    received = "received"
    retrieved = "retrieved"
    generated = "generated"
    completed = "completed"
