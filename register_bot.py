#!/usr/bin/env python3


import argparse
import shutil
import subprocess
import sys

from config import (
    BOT_PASSWORD,
    BOT_USERNAME,
    MATRIX_REMOTE_DIR,
    REGISTRATION_SHARED_SECRET,
    SSH_HOST,
    SSH_KEY,
    SSH_PASSWORD,
    SSH_PORT,
    SSH_USER,
    SYNAPSE_CONTAINER,
)


def find_sshpass() -> str | None:
    paths = [
        "/usr/bin/sshpass",
        "/opt/homebrew/bin/sshpass",
        "/usr/local/bin/sshpass",
    ]
    for p in paths:
        if shutil.which(p):
            return p
    return shutil.which("sshpass")


def build_ssh_cmd() -> list[str]:
    base_ssh = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-p", str(SSH_PORT)]

    if SSH_PASSWORD:
        sshpass = find_sshpass()
        if not sshpass:
            print(
                "[WARN] SSH_PASSWORD is set but sshpass is not installed.\n"
                "       Install it: brew install sshpass  (or use SSH_KEY instead)\n"
                "       Falling back to plain ssh (may prompt for password)."
            )
        else:
            return [sshpass, "-p", SSH_PASSWORD] + base_ssh

    if SSH_KEY:
        base_ssh += ["-i", SSH_KEY]

    return base_ssh


def register_via_ssh(
    username: str,
    password: str,
    shared_secret: str,
    admin: bool = False,
) -> None:
    ssh_cmd = build_ssh_cmd()
    target = f"{SSH_USER}@{SSH_HOST}"

    # Find the actual running container name (may have a prefix from docker-compose project)
    find_container = (
        f"docker ps --format '{{{{.Names}}}}' | grep -i {SYNAPSE_CONTAINER} | head -1"
    )

    admin_flag = "--admin" if admin else "--no-admin"

    # register_new_matrix_user is bundled with the Synapse Docker image
    remote_script = f"""
set -e
cd {MATRIX_REMOTE_DIR}
CONTAINER=$({find_container})
if [ -z "$CONTAINER" ]; then
  echo "ERROR: Synapse container not found (looked for '{SYNAPSE_CONTAINER}')"
  docker ps --format '{{{{.Names}}}}'
  exit 1
fi
echo "Using container: $CONTAINER"
docker exec "$CONTAINER" register_new_matrix_user \\
  -u '{username}' \\
  -p '{password}' \\
  {admin_flag} \\
  -c /data/homeserver.yaml \\
  http://localhost:8008
"""

    full_cmd = ssh_cmd + [target, remote_script]

    print(f"Connecting to {target}:{SSH_PORT} ...")
    print(f"Registering user '{username}' via docker exec in container '{SYNAPSE_CONTAINER}' ...\n")

    result = subprocess.run(full_cmd, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode != 0:
        print(f"\n[ERROR] Registration failed (exit code {result.returncode})")
        sys.exit(1)

    print(f"User @{username} registered successfully!")
    print(f"Now run: python3 bot.py")


def main():
    parser = argparse.ArgumentParser(
        description="Register Matrix bot user via SSH + docker exec"
    )
    parser.add_argument("--username", default=BOT_USERNAME, help="Bot username")
    parser.add_argument("--password", default=BOT_PASSWORD, help="Bot password")
    parser.add_argument("--admin", action="store_true", help="Make admin user")
    args = parser.parse_args()

    if not SSH_HOST:
        print("[ERROR] SSH_HOST is not set. Configure it in .env")
        sys.exit(1)

    if not REGISTRATION_SHARED_SECRET:
        print(
            "[WARN] REGISTRATION_SHARED_SECRET is not set in .env.\n"
            "       The register command will only work if the shared secret\n"
            "       is already configured in homeserver.yaml on the server."
        )

    register_via_ssh(
        username=args.username,
        password=args.password,
        shared_secret=REGISTRATION_SHARED_SECRET,
        admin=args.admin,
    )


if __name__ == "__main__":
    main()
