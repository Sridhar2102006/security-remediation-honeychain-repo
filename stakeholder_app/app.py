
from backend.auth import AUTH_SERVICE


def authorize_request(username, required_role):
    return AUTH_SERVICE.has_role(username, required_role)
