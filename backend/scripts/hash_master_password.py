"""Generate the bcrypt hash to paste into src/core/master_password.py.

The master password itself is never stored anywhere — only this hash is,
and only the hash is what the app checks logins against. It's a hardcoded
constant rather than an env var by design; see
docs/decisions/master-password.md for what this feature is and why it
carries the mitigations (and this storage choice) it does.

    python scripts/hash_master_password.py

Prompts for the password twice (to catch typos) rather than accepting it
as an argument, since a --password flag would leak the plaintext into
shell history and the process list.
"""

import getpass

from src.core.security import hash_password

if __name__ == "__main__":
    password = getpass.getpass("Master password: ")
    confirm = getpass.getpass("Confirm: ")
    if password != confirm:
        raise SystemExit("Passwords did not match.")
    if len(password) < 12:
        raise SystemExit("Use at least 12 characters — this password can log into any account.")

    print("\nPaste into src/core/master_password.py:")
    print(f'MASTER_PASSWORD_HASH: str | None = "{hash_password(password)}"')
