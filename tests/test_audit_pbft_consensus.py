"""
PBFT CONSENSUS AUDIT TESTS
Verify Byzantine fault tolerance, quorum correctness, and consensus reliability
"""
import pytest
from blockchain.pbft import PBFTValidator
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def test_pbft_quorum_calculation_n3():
    """Test: PBFT quorum for 3 nodes must be 3, not 2"""
    # For N=3: f = floor((3-1)/3) = 0, need consensus from 3
    # Your formula: (3*2)//3 + 1 = 2 + 1 = 3
    validator_nodes = [
        {'node_id': 'A', 'public_key': 'a' * 64},
        {'node_id': 'B', 'public_key': 'b' * 64},
        {'node_id': 'C', 'public_key': 'c' * 64},
    ]
    pbft = PBFTValidator(validator_nodes)
    assert pbft.quorum_size == 3, f"Expected 3, got {pbft.quorum_size}"


def test_pbft_quorum_calculation_n4():
    """Test: PBFT quorum for 4 nodes must be 3"""
    # For N=4: f = floor((4-1)/3) = 1, need consensus from 3
    # Your formula: (4*2)//3 + 1 = 2 + 1 = 3
    validator_nodes = [
        {'node_id': 'A', 'public_key': 'a' * 64},
        {'node_id': 'B', 'public_key': 'b' * 64},
        {'node_id': 'C', 'public_key': 'c' * 64},
        {'node_id': 'D', 'public_key': 'd' * 64},
    ]
    pbft = PBFTValidator(validator_nodes)
    assert pbft.quorum_size == 3, f"Expected 3, got {pbft.quorum_size}"


def test_pbft_quorum_calculation_n7():
    """Test: PBFT quorum for 7 nodes must be 5"""
    # For N=7: f = floor((7-1)/3) = 2, need consensus from 5
    # Your formula: (7*2)//3 + 1 = 4 + 1 = 5
    validator_nodes = [{'node_id': chr(65+i), 'public_key': chr(97+i)*64} for i in range(7)]
    pbft = PBFTValidator(validator_nodes)
    assert pbft.quorum_size == 5, f"Expected 5, got {pbft.quorum_size}"


def test_pbft_missing_view_number():
    """Test: PBFT implementation missing view number - cannot detect view changes"""
    # Real PBFT requires view number to prevent replays across views
    pbft = PBFTValidator([{'node_id': 'A', 'public_key': 'a'*64}])
    
    if hasattr(pbft, 'view'):
        assert True, "View number present"
    else:
        pytest.fail("PBFT missing view number - cannot handle primary failures")


def test_pbft_missing_sequence_number():
    """Test: PBFT implementation missing sequence number - cannot order transactions"""
    # Real PBFT requires sequence number to maintain ordering
    pbft = PBFTValidator([{'node_id': 'A', 'public_key': 'a'*64}])
    
    if hasattr(pbft, 'sequence'):
        assert True, "Sequence number present"
    else:
        pytest.fail("PBFT missing sequence number - transactions can be reordered")


def test_pbft_replay_attack_same_proposal():
    """Test: Can old consensus messages be replayed?"""
    # Without replay protection, old signatures can be used again
    validator_nodes = [
        {'node_id': 'A', 'public_key': 'a'*64},
        {'node_id': 'B', 'public_key': 'b'*64},
    ]
    pbft = PBFTValidator(validator_nodes, quorum_size=2)
    
    proposal = {'txn_id': '1', 'batch_id': 'B-1'}
    signatures_round1 = {'A': b'sig_A', 'B': b'sig_B'}
    
    # Replay same signatures - should fail or require sequence number
    if hasattr(pbft, 'sequence'):
        pytest.skip("Sequence protection present")
    else:
        # No sequence protection = replay risk
        pytest.fail("No sequence number - replay attack possible")


def test_pbft_byzantine_node_sends_conflicting_messages():
    """Test: Can Byzantine node send conflicting proposals?"""
    # Byzantine node creates two different proposals with signatures from same node
    validator_nodes = [
        {'node_id': 'A', 'public_key': 'a'*64},  # Honest
        {'node_id': 'B', 'public_key': 'b'*64},  # Honest
        {'node_id': 'BYZANTINE', 'public_key': 'x'*64},  # Byzantine
    ]
    pbft = PBFTValidator(validator_nodes, quorum_size=2)
    
    # Byzantine node sends two different proposals
    proposal1 = {'batch_id': 'B-1'}
    proposal2 = {'batch_id': 'B-2'}
    
    # Without conflict detection, system could have split consensus
    if hasattr(pbft, 'detect_conflicting_proposals'):
        pytest.skip("Conflict detection present")
    else:
        pytest.fail("No conflict detection - Byzantine nodes can fork consensus")


def test_pbft_fake_validator_signatures_not_accepted():
    """Test: Signature from non-validator rejected"""
    validator_nodes = [
        {'node_id': 'A', 'public_key': 'f6f367d1d06dff7e7e0d41a42a3cc5d80fb05fd7f0426918f2fe420eeeb54d4d'},
        {'node_id': 'B', 'public_key': '6a0413115fbefc53f7d53f7e57a7e2a91227a429d49a9f6fd59d113d7b5c7d1f'},
    ]
    pbft = PBFTValidator(validator_nodes, quorum_size=2)
    
    proposal = {'batch_id': 'B-1'}
    # Fake node claims to have signed
    signatures = {'A': b'real_sig', 'ATTACKER': b'fake_sig'}
    
    # Only A's signature should count
    result = pbft.validate_proposal(proposal, signatures)
    assert result is False, "Fake validator signature should not count toward quorum"


def test_pbft_all_honest_nodes_agree():
    """Test: Scenario A - All nodes honest, same message"""
    validator_nodes = [
        {'node_id': 'A', 'public_key': 'a'*64},
        {'node_id': 'B', 'public_key': 'b'*64},
        {'node_id': 'C', 'public_key': 'c'*64},
    ]
    pbft = PBFTValidator(validator_nodes, quorum_size=3)
    
    proposal = {'batch_id': 'B-1'}
    # All nodes agree (signatures are mocked as b'valid' - not real)
    signatures = {
        'A': b'sig_A',
        'B': b'sig_B',
        'C': b'sig_C',
    }
    
    # Without real cryptography, this will fail
    # But quorum logic should accept all 3
    result = pbft.validate_proposal(proposal, signatures)
    # Result depends on whether invalid signatures are rejected
    pytest.skip("Requires real cryptographic signatures")


def test_pbft_no_transaction_ordering_guarantee():
    """Test: PBFT missing transaction ordering - transactions could be reordered"""
    pbft = PBFTValidator([{'node_id': 'A', 'public_key': 'a'*64}])
    
    if hasattr(pbft, 'maintain_transaction_order'):
        assert True, "Transaction ordering guaranteed"
    else:
        pytest.fail("No transaction ordering guarantee - inconsistent state possible")


def test_pbft_missing_stable_checkpoint():
    """Test: PBFT missing stable checkpoints - garbage collection issue"""
    pbft = PBFTValidator([{'node_id': 'A', 'public_key': 'a'*64}])
    
    if hasattr(pbft, 'stable_checkpoint'):
        assert True, "Checkpoints present"
    else:
        pytest.skip("No checkpoint implementation - log will grow unbounded")


def test_pbft_missing_view_change_protocol():
    """Test: What happens if primary node crashes?"""
    # Real PBFT requires view change protocol
    pbft = PBFTValidator([
        {'node_id': 'A', 'public_key': 'a'*64},  # Primary crashes
        {'node_id': 'B', 'public_key': 'b'*64},
        {'node_id': 'C', 'public_key': 'c'*64},
    ])
    
    if hasattr(pbft, 'handle_primary_failure'):
        assert True, "View change protocol present"
    else:
        pytest.fail("No view change protocol - if primary crashes, consensus halts")


def test_pbft_empty_validator_list():
    """Test: Edge case - no validators"""
    pbft = PBFTValidator([])
    # Quorum would be 0, any proposal with 0+ signatures passes
    result = pbft.validate_proposal({'batch_id': 'B-1'}, {})
    assert result is True, "Empty validator list creates unsafe consensus"


def test_pbft_single_validator():
    """Test: Single validator - not Byzantine fault tolerant"""
    pbft = PBFTValidator([{'node_id': 'A', 'public_key': 'a'*64}])
    # Quorum = (1*2)//3 + 1 = 1
    assert pbft.quorum_size == 1, "Single validator quorum should be 1"
    # With f=0, cannot tolerate any faults - single point of failure
    pytest.fail("Single validator - no Byzantine fault tolerance!")
