"""Regression tests for the core blockchain hash-chain integrity behavior."""

import hashlib

from blockchain.ledger import BlockchainLedger


def test_ledger_add_block_chains_hashes_and_tracks_entries():
    ledger = BlockchainLedger()
    first = ledger.add_block({'data': 'block1'})
    second = ledger.add_block({'data': 'block2'})

    assert len(ledger.chain) == 2
    assert first['hash']
    assert second['hash']
    assert first['hash'] != second['hash']
    assert hasattr(ledger, 'lock')


def test_ledger_hash_is_linked_to_previous_block_hash():
    ledger = BlockchainLedger()
    ledger.add_block({'data': 'block1'})
    ledger.add_block({'data': 'block2'})

    prev_hash = ledger.chain[0]['hash']
    current_hash = ledger.chain[1]['hash']
    expected = hashlib.sha256((str(prev_hash) + str(ledger.chain[1]['block'])).encode('utf-8')).hexdigest()
    assert current_hash == expected


def test_ledger_retain_working_chain_after_multiple_blocks():
    ledger = BlockchainLedger()
    for idx in range(5):
        ledger.add_block({'data': f'block{idx}'})
    assert len(ledger.chain) == 5
    assert all(entry['hash'] for entry in ledger.chain)
