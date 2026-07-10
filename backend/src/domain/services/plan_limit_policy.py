from src.domain.entities.subscription_plan import SubscriptionPlan
from src.domain.exceptions import PlanLimitExceededError


class PlanLimitPolicy:
    """Pure cross-cutting checks against a tenant's current plan — no I/O; the
    caller resolves the effective plan and current usage counts and passes
    them in."""

    @staticmethod
    def check_product_limit(current_count: int, plan: SubscriptionPlan) -> None:
        if current_count >= plan.max_products:
            raise PlanLimitExceededError(
                f"Product limit reached ({plan.max_products} max on the {plan.name} plan)"
            )

    @staticmethod
    def check_banner_limit(current_count: int, plan: SubscriptionPlan) -> None:
        if current_count >= plan.max_banners:
            raise PlanLimitExceededError(
                f"Banner limit reached ({plan.max_banners} max on the {plan.name} plan)"
            )

    @staticmethod
    def check_custom_domain_allowed(plan: SubscriptionPlan) -> None:
        if not plan.custom_domain_allowed:
            raise PlanLimitExceededError(
                f"Custom domains are not available on the {plan.name} plan"
            )
