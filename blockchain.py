import hashlib
import json
import time
import os
from typing import List, Dict, Any, Optional

from cryptography.fernet import Fernet


class Blockchain:
    """
    Simple in-app Proof-of-Work blockchain with Fernet payload encryption.

    - Fully self-contained: no external APIs or network calls.
    - Anchors are persisted locally to `anchors.json`.
    - Use `BLOCKCHAIN_KEY` environment variable to set a stable Fernet key.
    """
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
        # anchors file (simulated on-chain anchoring storage)
        self.anchors_path = os.path.join(os.getcwd(), "anchors.json")
        # ensure anchors file exists
        if not os.path.exists(self.anchors_path):
            try:
                with open(self.anchors_path, 'w') as f:
                    json.dump([], f)
            except Exception:
                pass

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

    def _load_anchors(self) -> List[Dict[str, Any]]:
        try:
            with open(self.anchors_path, 'r') as f:
                return json.load(f)
        except Exception:
            return []

    def _save_anchor(self, anchor: Dict[str, Any]):
        anchors = self._load_anchors()
        anchors.append(anchor)
        try:
            with open(self.anchors_path, 'w') as f:
                json.dump(anchors, f, indent=2)
        except Exception:
            # non-fatal
            pass

    def anchor_block(self, block_index: Optional[int] = None) -> Dict[str, Any]:
        """
        Simulate anchoring a block to an external ledger by storing an anchor record
        locally in `anchors.json`. No external keys or APIs required.
        """
        if block_index is None:
            block = self.last_block
        else:
            if block_index - 1 < 0 or block_index > len(self.chain):
                raise IndexError("block index out of range")
            block = self.chain[block_index - 1]

        block_hash = self.hash(block)
        anchor = {
            "block_index": block['index'],
            "block_hash": block_hash,
            "timestamp": time.time(),
            "anchor_id": hashlib.sha256(f"{block_hash}{time.time()}".encode()).hexdigest()
        }

        # persist locally
        self._save_anchor(anchor)

        # also record an on-chain transaction pointing to the anchor (encrypted payload)
        try:
            self.new_transaction(sender="system", recipient="anchor", amount=0, data={"type": "anchor", "anchor_id": anchor['anchor_id'], "block_index": block['index'], "block_hash": block_hash})
        except Exception:
            pass

        return anchor

    def get_anchors(self) -> List[Dict[str, Any]]:
        """Return the list of locally persisted anchors."""
        return self._load_anchors()

    def get_block(self, index: int) -> Dict[str, Any]:
        """Return a block by 1-based `index`. Raises IndexError if out of range."""
        if index - 1 < 0 or index > len(self.chain):
            raise IndexError("block index out of range")
        return self.chain[index - 1]

    def mine_block(self, miner_address: str = "miner") -> Dict[str, Any]:
        """Mine (find proof) for the current transactions, reward the miner, and
        append a new block to the chain. Returns the newly created block.

        This is a local-only mining operation — no networking or external APIs.
        """
        # reward miner with a simple coinbase transaction
        try:
            self.new_transaction(sender="0", recipient=miner_address, amount=1)
        except Exception:
            # non-fatal if transaction cannot be added
            pass

        last_proof = self.last_block['proof']
        proof = self.proof_of_work(last_proof)
        previous_hash = self.hash(self.last_block)
        block = self.new_block(proof, previous_hash)
        return block

    def get_chain(self) -> Dict[str, Any]:
        return {'chain': self.chain, 'length': len(self.chain)}


# Single global blockchain instance for the app
default_key = os.getenv('BLOCKCHAIN_KEY')
blockchain = Blockchain(key=default_key.encode() if default_key else None)
