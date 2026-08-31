
from blockchain.state_machine import TRANSITIONS


def can_process_batch(current_status, next_status):
    if current_status is None:
        return False
    allowed = TRANSITIONS.get(current_status, set())
    return next_status in allowed


def can_accept_batch(quantity):
    if isinstance(quantity, bool):
        return False
    if not isinstance(quantity, (int, float)):
        return False
    return quantity > 0
