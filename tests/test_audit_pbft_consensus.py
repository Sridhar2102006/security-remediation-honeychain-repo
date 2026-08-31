"""Regression tests for PBFT quorum and real-signature validation."""

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from blockchain.pbft import PBFTValidator


def _validator_node_pair(node_id):
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()
    return node_id, private_key, public_key


def test_pbft_quorum_size_matches_consensus_formula():
    nodes = [
        {'node_id': 'A', 'public_key': _validator_node_pair('A')[2]},
        {'node_id': 'B', 'public_key': _validator_node_pair('B')[2]},
        {'node_id': 'C', 'public_key': _validator_node_pair('C')[2]},
    ]
    assert PBFTValidator(nodes).quorum_size == 3


def test_pbft_quorum_size_for_larger_cluster_is_forward_only_by_formula():
    nodes = [
        {'node_id': f'N{i}', 'public_key': _validator_node_pair(f'N{i}')[2]}
        for i in range(7)
    ]
    assert PBFTValidator(nodes).quorum_size == 5


def test_pbft_rejects_fake_node_ids_and_requires_real_signatures():
    node_a, key_a, pub_a = _validator_node_pair('A')
    node_b, key_b, pub_b = _validator_node_pair('B')
    proposal = {'batch_id': 'B-1'}
    signatures = {
        'A': key_a.sign(b'{"batch_id": "B-1"}'),
        'ATTACKER': b'not-a-real-signature',
    }

    validator = PBFTValidator([
        {'node_id': 'A', 'public_key': pub_a},
        {'node_id': 'B', 'public_key': pub_b},
    ], quorum_size=2)

    assert validator.validate_proposal(proposal, signatures) is False


def test_pbft_accepts_verified_quorum_from_real_validators():
    node_a, key_a, pub_a = _validator_node_pair('A')
    node_b, key_b, pub_b = _validator_node_pair('B')
    proposal = {'batch_id': 'B-1'}
    serialized = __import__('json').dumps(proposal, sort_keys=True, default=str).encode('utf-8')
    signatures = {
        'A': key_a.sign(serialized),
        'B': key_b.sign(serialized),
    }

    validator = PBFTValidator([
        {'node_id': 'A', 'public_key': pub_a},
        {'node_id': 'B', 'public_key': pub_b},
    ], quorum_size=2)

    assert validator.validate_proposal(proposal, signatures) is True
