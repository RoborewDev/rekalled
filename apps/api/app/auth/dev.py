from app.auth.principal import ALL_SCOPES, Principal

DEV_SUBJECT = "dev|local"


def dev_principal(x_dev_user: str | None) -> Principal:
    # X-Dev-User lets you act as a second user when testing isolation by hand.
    return Principal(provider="dev", subject=x_dev_user or DEV_SUBJECT, scopes=ALL_SCOPES)
