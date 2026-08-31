
from blockchain.business_rules import can_accept_batch, can_process_batch


def test_business_rules_reject_bool_quantity_and_forward_only_transitions():
    assert can_accept_batch(True) is False
    assert can_accept_batch(2) is True
    assert can_process_batch('PENDING', 'PROCESSING') is True
    assert can_process_batch('PROCESSING_COMPLETED', 'PROCESSING') is False
