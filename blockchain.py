import hashlib
import json
import time
import os
from typing import List, Dict, Any, Optional

from cryptography.fernet import Fernet


class Blockchain:
    def __init__(self, key: Optional[bytes] = None):
        self.chain: List[Dict[str, Any]] = []
        self.current_transactions: List[Dict[str, Any]] = []
        # Use provided key or environment variable for Fernet
        if key:
            self.fernet = Fernet(key)
        else:
            env_key = os.getenv('BLOCKCHAIN_KEY')
            if env_key:
                self.fernet = Fernet(env_key.encode())
            else:
                # generate ephemeral key (not for production)
                self.fernet = Fernet(Fernet.generate_key())

        # Create the genesis block
        self.new_block(previous_hash='1', proof=100)

    def encrypt_data(self, payload: Any) -> str:
        raw = json.dumps(payload, sort_keys=True).encode()
        return self.fernet.encrypt(raw).decode()

    def decrypt_data(self, token: str) -> Any:
        raw = self.fernet.decrypt(token.encode())
        return json.loads(raw.decode())

    def new_block(self, proof: int, previous_hash: str = None) -> Dict[str, Any]:
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time.time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]) if self.chain else previous_hash,
        }

        # Reset the current list of transactions
        self.current_transactions = []
        self.chain.append(block)
        return block

    def new_transaction(self, sender: str, recipient: str, amount: float = 0, data: Dict = None) -> int:
        tx = {
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        }
        if data is not None:
            # encrypt sensitive payload
            tx['data_encrypted'] = self.encrypt_data(data)
        else:
            tx['data_encrypted'] = None

        self.current_transactions.append(tx)
        return self.last_block['index'] + 1

    @staticmethod
    def hash(block: Dict[str, Any]) -> str:
        # We must ensure the dictionary is ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self) -> Dict[str, Any]:
        return self.chain[-1]

    def proof_of_work(self, last_proof: int) -> int:
        proof = 0
        while not self.valid_proof(last_proof, proof):
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof: int, proof: int) -> bool:
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == '0000'

    def valid_chain(self, chain: List[Dict[str, Any]]) -> bool:
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            if block['previous_hash'] != self.hash(last_block):
                return False
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False
            last_block = block
            current_index += 1

        return True

    def get_chain(self) -> Dict[str, Any]:
        return {'chain': self.chain, 'length': len(self.chain)}


# Single global blockchain instance for the app
default_key = os.getenv('BLOCKCHAIN_KEY')
blockchain = Blockchain(key=default_key.encode() if default_key else None)
