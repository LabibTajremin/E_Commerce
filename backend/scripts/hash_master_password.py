"""Generate the bcrypt hash to put in the MASTER_PASSWORD_HASH env var.

The master password itself is never stored anywhere — only this hash is,
and only the hash is what the app checks logins against. See
docs/decisions/master-password.md for what this feature is and why it
carries the mitigations it does.

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

    print("\nMASTER_PASSWORD_HASH=" + hash_password(password))
