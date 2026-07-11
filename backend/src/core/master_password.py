"""Break-glass master-password hash.

A hardcoded constant rather than an env var: rotating it is then always an
explicit code change + redeploy, and it can never leak via an env-var
dump/log/dashboard the way a config value can. The tradeoff is the
opposite one — it lives in git (and git history) once set. See
docs/decisions/master-password.md for the full reasoning.

Generate the value with `python scripts/hash_master_password.py`, which
prints a line ready to paste below. Leave it None to disable the feature
entirely (default).
"""

MASTER_PASSWORD_HASH: str | None = None
