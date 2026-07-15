"use client";

import { useState } from "react";

import { httpClient } from "@/infrastructure/api/httpClient";
import { ApiError } from "@/application/interfaces/ApiClient";
import { subscribeToPlan, usePlans, useSubscription } from "@/application/use-cases/useBilling";

import styles from "./page.module.css";

export default function BillingPage() {
  const { data: plans, isLoading: plansLoading, error: plansError } = usePlans(httpClient);
  const { data: subscription, isLoading: subLoading } = useSubscription(httpClient);
  const [pendingPlanId, setPendingPlanId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubscribe(planId: string) {
    setError(null);
    setPendingPlanId(planId);
    try {
      const { checkout_url } = await subscribeToPlan(
        httpClient,
        planId,
        `${window.location.origin}/billing?success=1`,
        `${window.location.origin}/billing?canceled=1`,
      );
      window.location.href = checkout_url;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start checkout");
      setPendingPlanId(null);
    }
  }

  return (
    <section>
      <h1>Billing</h1>
      {subLoading ? null : subscription ? (
        <p className={styles.current}>
          Current plan status: <strong>{subscription.status}</strong>
        </p>
      ) : (
        <p className={styles.current}>No active subscription.</p>
      )}

      {error ? <p className={styles.error}>{error}</p> : null}
      {plansError ? <p className={styles.error}>{plansError}</p> : null}
      {plansLoading ? (
        <p>Loading plans...</p>
      ) : (
        <div className={styles.plans}>
          {(plans ?? []).map((plan) => {
            const isCurrent = subscription?.plan_id === plan.id;
            return (
              <div key={plan.id} className={styles.plan}>
                <h2>{plan.name}</h2>
                <p className={styles.price}>${plan.price}/mo</p>
                <ul>
                  <li>Up to {plan.max_products} products</li>
                  <li>Up to {plan.max_banners} banners</li>
                  <li>{plan.custom_domain_allowed ? "Custom domain included" : "No custom domain"}</li>
                </ul>
                <button
                  disabled={isCurrent || pendingPlanId === plan.id}
                  onClick={() => handleSubscribe(plan.id)}
                >
                  {isCurrent ? "Current plan" : pendingPlanId === plan.id ? "Redirecting..." : "Choose plan"}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
