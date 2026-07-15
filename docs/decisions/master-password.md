# ADR: Master password (break-glass superadmin login)

## Context

The user asked for a master password: one credential that, stored in
config, logs into *any* account — tenant admin, customer, or platform
superadmin — in every environment, production included. Before building
it, the risk was flagged explicitly: a single leaked credential
compromises every account on the platform simultaneously, with no way to
scope or revoke access to just one incident, unlike a per-account password
reset or a per-support-ticket impersonation token. The user was offered
narrower alternatives (audited support impersonation; a master password
gated to non-production environments only) and chose, with that risk
stated, to proceed with the full-scope version anyway — "literal master
password, works everywhere including production." This ADR documents that
decision and the three mitigations it was built with as a condition of
building it this way at all.

## Decision

Built exactly what was asked, with three mitigations that were the
explicit condition for building it:

1. **Never store the plaintext password.** `MASTER_PASSWORD_HASH` is a
   bcrypt hash (`scripts/hash_master_password.py` generates it);
   `MasterPasswordGate.matches()` calls the same `verify_password()` every
   other password check in this codebase uses. Leaving it `None` disables
   the feature entirely — that's the default.

   It's a **hardcoded constant in `src/core/master_password.py`, not an
   env var** — a deliberate change from the first version of this
   feature, made per explicit follow-up direction after the initial
   config-based version was built. Rotating it is then always an explicit
   code change + redeploy (no config edit anyone with deploy-dashboard
   access can make silently), and it can't leak via an env-var
   dump/log/dashboard the way a `Settings` field can. The tradeoff runs
   the other way from every other secret in this codebase: it lives in
   git, and in git history, once set — the usual reason secrets go in env
   vars instead. Given the master password already sits outside this
   codebase's normal "every credential is one account's blast radius"
   model, keeping the *hash* in source isn't a meaningfully bigger
   exposure than the feature already is, and the explicit-rotation
   property was judged worth it.
2. **Rate-limit failed logins by IP, platform-wide.** `RedisRateLimiter`
   (a fixed-window failure counter, mirroring the existing
   `RedisTokenBlacklist` pattern) locks out an IP after
   `MASTER_PASSWORD_MAX_ATTEMPTS` (default 5) failures within
   `MASTER_PASSWORD_LOCKOUT_WINDOW_SECONDS` (default 900). This applies to
   *every* failed login attempt on all three login endpoints, not just
   ones that happened to try the master password — the check can't tell
   in advance which a caller was attempting, and the byproduct is that the
   app now has login throttling at all, which it didn't before this.
3. **Audit-log every successful master-password use.** A new
   `master_password_usages` table (global, no RLS — same shape as
   `platform_admins`, since a use can span any tenant) records who was
   authenticated as (account type, id, email, tenant if any), from what
   IP, and when. Function logs alone weren't enough — Vercel serverless
   function logs are short-retention, and this needs to be durably
   reviewable. `GET /api/v1/platform/master-password-usages`
   (superadmin-only) exposes it.

### How it's wired in

Each of the three login use cases (`LoginUseCase`, `LoginCustomerUseCase`,
`LoginPlatformAdminUseCase`) now takes a `RateLimiter` and a
`MasterPasswordGate` alongside its repository, and each `*Input` DTO
carries the caller's `ip_address` (extracted server-side from
`X-Forwarded-For`, never client-supplied). The flow is the same in all
three:

1. If the IP is locked out, reject immediately — don't even look up the
   account.
2. Look up the account by email. If it's missing (or, for admin users,
   inactive), record a failure and reject — same error message as a wrong
   password, so a prober can't distinguish "no such account" from "wrong
   password" from "master password wrong too."
3. Try the account's own password first. If that fails, try the master
   password. If both fail, record a failure and reject.
4. On success via the master password specifically, log to the audit
   table. On success either way, reset that IP's failure counter.

`MasterPasswordGate` itself only knows two things: whether a password
string matches the configured hash, and how to append to the audit log.
It doesn't touch the rate limiter — that lives in the three use cases
because it has to fire on *every* failed attempt, not just master-password
ones.

## Why this shape and not something safer

The safer options (scoped to non-prod; a proper audited impersonation
token that's per-incident and revocable) were offered and declined. Given
that starting point, the goal was to make the version that *was* chosen
as containable as a single shared secret can be: unrecoverable from the
database if it leaks (hash only), throttled against brute-force, and
observable after the fact even though it can't be prevented in advance.
None of these mitigations change the fundamental shape of the risk — one
password compromises every account — they only bound how it can be
attacked and guarantee it's noticed when used.

## What's still true

This remains categorically different from every other credential in this
system. Every other password authenticates exactly one account; this one
authenticates all of them, forever, until the operator rotates
`MASTER_PASSWORD_HASH` in `src/core/master_password.py` and redeploys —
there's no schema for scoping it to one tenant, one time window, or one
incident. Treat it accordingly: restrict who has the plaintext and who has
merge access to the file, rotate it if anyone who had either leaves, and
review `GET /api/v1/platform/master-password-usages` periodically rather
than only after an incident is already suspected.
