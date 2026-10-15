"""Modelo canónico: lo único que ven el portal, Subsidios y la app móvil.

Ningún nombre de tabla, columna o código legacy aparece aquí: el adapter traduce.
"""

from dataclasses import dataclass
from typing import Optional

MEMBER_STATUSES = ("ACTIVE", "RETIRED", "SUSPENDED")
RELATIONSHIPS = ("SPOUSE", "CHILD", "FATHER", "MOTHER")


@dataclass(frozen=True)
class CompanyRef:
    id: str
    name: str


@dataclass(frozen=True)
class Member:
    document: str
    full_name: str
    status: str
    company: Optional[CompanyRef]

    def to_dict(self):
        company = {"id": self.company.id, "name": self.company.name} if self.company else None
        return {"document": self.document, "fullName": self.full_name, "status": self.status, "company": company}


@dataclass(frozen=True)
class Beneficiary:
    document: str
    full_name: str
    relationship: str

    def to_dict(self):
        return {"document": self.document, "fullName": self.full_name, "relationship": self.relationship}


@dataclass(frozen=True)
class Company:
    id: str
    name: str
    active_members: int

    def to_dict(self):
        return {"id": self.id, "name": self.name, "activeMembers": self.active_members}


# Resultado de registrar un retiro en el legacy.
CREATED = "CREATED"        # se aplicó ahora
DUPLICATE = "DUPLICATE"    # el mismo requestId ya estaba aplicado: no se duplicó
NOT_FOUND = "NOT_FOUND"    # el afiliado no existe
CONFLICT = "CONFLICT"      # el requestId ya se usó con otro afiliado


@dataclass(frozen=True)
class RetirementOutcome:
    status: str
    movement_id: Optional[int] = None
