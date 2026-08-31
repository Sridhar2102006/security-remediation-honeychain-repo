
from blockchain.validator import ValidatorNode


def test_validator_public_key_persists_across_restart(tmp_path):
    node_id = 'validator-1'
    first = ValidatorNode.create(node_id, storage_path=str(tmp_path))
    second = ValidatorNode.load_from_storage(node_id, storage_path=str(tmp_path))
    assert first.get_public_key_bytes() == second.get_public_key_bytes()
