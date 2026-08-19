"""SQLAlchemy ORM models for YantraSetu.

Importing this package pulls in every model so they register on the shared
Base.metadata. That is what makes Base.metadata.create_all() see all tables and
lets string-based relationships (e.g. "Machine") resolve correctly.
"""
from app.models.booking import Booking, BookingStatus
from app.models.chc import CHC
from app.models.demand_request import DemandRequest
from app.models.farmer import Farmer
from app.models.field import Field
from app.models.machine import Machine
from app.models.machine_availability import MachineAvailability
from app.models.notification import Notification, NotificationType
from app.models.relocation_recommendation import RelocationRecommendation
from app.models.route import Route, RouteStop
from app.models.user import User, UserRole

__all__ = [
    "CHC",
    "Machine",
    "Farmer",
    "Field",
    "MachineAvailability",
    "DemandRequest",
    "RelocationRecommendation",
    "Route",
    "RouteStop",
    "User",
    "UserRole",
    "Notification",
    "NotificationType",
    "Booking",
    "BookingStatus",
]
