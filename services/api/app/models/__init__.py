"""Re-export models so Alembic and the app see them.

Import every model module so SQLAlchemy's metadata is fully populated and
`alembic revision --autogenerate` (and `Base.metadata.create_all` in
tests) see every table.
"""

from app.models.cost_item import CostItem
from app.models.data_source import DataSource
from app.models.exchange_rate import ExchangeRate
from app.models.expense import Expense
from app.models.funding_source import FundingSource
from app.models.payment_event import PaymentEvent
from app.models.savings_goal import SavingsGoal
from app.models.session import Session
from app.models.study_plan import StudyPlan
from app.models.study_plan_comparison import StudyPlanComparison
from app.models.stress_scenario import StressScenario
from app.models.user import User

__all__ = [
    "CostItem",
    "DataSource",
    "ExchangeRate",
    "Expense",
    "FundingSource",
    "PaymentEvent",
    "SavingsGoal",
    "Session",
    "StressScenario",
    "StudyPlan",
    "StudyPlanComparison",
    "User",
]
