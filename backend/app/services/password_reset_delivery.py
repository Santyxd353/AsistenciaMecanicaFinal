import os
from datetime import datetime
from pathlib import Path


PASSWORD_RESET_TRANSPORT = os.getenv("PASSWORD_RESET_TRANSPORT", "console").strip().lower()
PASSWORD_RESET_FILE_PATH = os.getenv(
    "PASSWORD_RESET_FILE_PATH",
    "/tmp/asistencia_mecanica_password_reset_links.log",
)


def send_password_reset_email(email: str, reset_url: str) -> None:
    if PASSWORD_RESET_TRANSPORT == "file":
        _write_reset_link_to_file(email=email, reset_url=reset_url)
        return

    _print_reset_link(email=email, reset_url=reset_url)


def _print_reset_link(*, email: str, reset_url: str) -> None:
    print("=== PASSWORD RESET LINK ===")
    print(f"email: {email}")
    print(f"reset_url: {reset_url}")
    print("===========================")


def _write_reset_link_to_file(*, email: str, reset_url: str) -> None:
    timestamp = datetime.utcnow().isoformat()
    path = Path(PASSWORD_RESET_FILE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handler:
        handler.write(f"[{timestamp}] email={email} reset_url={reset_url}\n")
