import json
import os
import subprocess # To call Node.js script for proof generation
import time
from fastapi import FastAPI, HTTPException
from merkletools import MerkleTools
import hashlib
from pathlib import Path
import sys
import logging

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- FastAPI App Initialization ---
app = FastAPI(title="Demo ASP Service", description="Simulates an ASP generating ZK attestations.")

# --- Configuration ---
# Determine project base directory relative to this file's location
# Assumes main.py is in asp-service/
BASE_DIR = Path(__file__).resolve().parent.parent
CIRCUIT_DIR = BASE_DIR / "circuits" / "attestation"
ZK_OUT_DIR = BASE_DIR / "zk-out"
MOCK_OFAC_FILE = Path(__file__).resolve().parent / "mock_ofac.json"
NODE_PATH = "node" # Assumes 'node' is in the system PATH
GENERATE_PROOF_SCRIPT = BASE_DIR / "scripts" / "generate_proof.js"
CIRCUIT_NAME = "attestation" # Name of the circuit (without extension)
TREE_LEVELS = 4 # Must match the 'levels' parameter in the Circom template
TREE_SIZE = 2**TREE_LEVELS # Expected number of leaves (16 for levels=4)

# --- State (In-memory for this demonstration) ---
# Stores the latest generated attestation data
current_commitment = {
    "root": None,           # Merkle root (hex string)
    "timestamp": 0,         # Unix timestamp of generation
    "proof": None,          # ZK proof object (from SnarkJS)
    "publicSignals": None   # Public signals used for the proof (decimal strings)
}
merkle_tree = None          # The MerkleTree object
exclusion_set_hashes = []   # List of leaf hashes in the tree (hex strings)

# --- Helper Functions ---

def calculate_leaf_hash(address: str) -> str:
    """Calculates the SHA3-256 hash of an address string."""
    return hashlib.sha3_256(address.encode('utf-8')).hexdigest()

def load_exclusion_set():
    """Loads addresses from the mock file, calculates hashes, pads, sorts, and builds the Merkle tree."""
    global exclusion_set_hashes, merkle_tree
    logging.info(f"Loading exclusion set from {MOCK_OFAC_FILE}...")
    try:
        if not MOCK_OFAC_FILE.exists():
            logging.error(f"Mock OFAC file not found at {MOCK_OFAC_FILE}")
            merkle_tree = None
            exclusion_set_hashes = []
            return

        with open(MOCK_OFAC_FILE, 'r') as f:
            addresses = json.load(f)

        # Calculate hashes for all addresses
        raw_hashes = [calculate_leaf_hash(addr) for addr in addresses]
        logging.info(f"Loaded {len(raw_hashes)} addresses, calculated hashes.")

        # Define a consistent padding value (as hex hash)
        padding_value = b"__DEFAULT_PADDING_LEAF__" # Use a distinct padding value
        padding_hash = calculate_leaf_hash(padding_value.decode())

        # Pad the list with the padding hash to reach the exact TREE_SIZE
        num_to_pad = TREE_SIZE - len(raw_hashes)
        if num_to_pad < 0:
            logging.warning(f"Exclusion list has more items ({len(raw_hashes)}) than tree size ({TREE_SIZE}). Truncating.")
            padded_hashes = raw_hashes[:TREE_SIZE]
        elif num_to_pad > 0:
            logging.info(f"Padding list with {num_to_pad} default hashes.")
            padded_hashes = raw_hashes + [padding_hash] * num_to_pad
        else:
            padded_hashes = raw_hashes

        # Sort the final list of hashes (important for consistency if order matters)
        exclusion_set_hashes = sorted(padded_hashes)
        logging.info(f"Final leaf hash list size: {len(exclusion_set_hashes)}")

        # Build the Merkle tree using the py-merkle-trees library
        merkle_tree = MerkleTree(exclusion_set_hashes, sha256)
        logging.info(f"Merkle tree built successfully. Root: {merkle_tree.root.hex() if merkle_tree else 'N/A'}")

    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from {MOCK_OFAC_FILE}")
        merkle_tree = None
        exclusion_set_hashes = []
    except Exception as e:
        logging.error(f"Error loading exclusion set: {e}", exc_info=True)
        merkle_tree = None
        exclusion_set_hashes = []

def generate_attestation_proof():
    """Generates the ZK proof for the current Merkle tree state."""
    global current_commitment
    if not merkle_tree or not exclusion_set_hashes:
        logging.error("Merkle tree or exclusion set not initialized. Cannot generate proof.")
        return

    logging.info("Generating ZK attestation proof...")
    try:
        # --- Prepare inputs for the ZK circuit ---
        root_hex = merkle_tree.root.hex()
        root_decimal_str = str(int(root_hex, 16))
        timestamp = int(time.time())

        # Define known bad address (must be in the mock list) and a safe address (not in the list)
        # Ensure these addresses are formatted consistently (e.g., checksummed if needed)
        bad_address_in_list = "0xBadAddress10000000000000000000000000000000"
        safe_address = "0xSafeAddress00000000000000000000000000000000" # Example safe address

        bad_leaf_hash_hex = calculate_leaf_hash(bad_address_in_list)
        bad_leaf_hash_decimal_str = str(int(bad_leaf_hash_hex, 16))
        safe_leaf_hash_hex = calculate_leaf_hash(safe_address) # Hash of the safe address

        # Find a leaf *in the tree* that is NOT the bad_leaf_hash to generate a valid path for.
        # The circuit proves knowledge of *a* path, and that the leaf for that path isn't the bad one.
        leaf_to_prove_hex = None
        for h in exclusion_set_hashes:
            if h != bad_leaf_hash_hex:
                leaf_to_prove_hex = h
                break # Found a suitable leaf

        if leaf_to_prove_hex is None:
            logging.error("Critical Error: Could not find a leaf in the tree different from the known bad leaf. Check padding/list.")
            return

        leaf_to_prove_decimal_str = str(int(leaf_to_prove_hex, 16))

        # Get the Merkle proof for the chosen leaf_to_prove
        logging.info(f"Generating Merkle proof for leaf: {leaf_to_prove_hex}")
        proof_data = merkle_tree.get_proof_for_leaf(leaf_to_prove_hex, index=True)
        logging.info(f"Merkle proof generated. Path length: {len(proof_data['path'])}")

        # Prepare the input object for the Circom circuit
        circuit_input = {
            "root": root_decimal_str,
            "knownBadLeafHash": bad_leaf_hash_decimal_str,
            "leaf": leaf_to_prove_decimal_str,
            "pathElements": [str(int(el.hex(), 16)) for el in proof_data['path']],
            "pathIndices": [str(idx) for idx in proof_data['pathIndices']]
        }

        # Define paths for temporary and output files
        input_json_path = CIRCUIT_DIR / "input.json" # Overwrite previous input
        proof_json_path = ZK_OUT_DIR / "proof.json"
        public_json_path = ZK_OUT_DIR / "public.json"

        # Save input.json
        with open(input_json_path, 'w') as f:
            json.dump(circuit_input, f, indent=2)
        logging.info(f"Saved circuit input to {input_json_path}")

        # --- Call SnarkJS via helper Node.js script ---
        ZK_OUT_DIR.mkdir(exist_ok=True) # Ensure output directory exists

        # Construct the command to run the Node.js helper script
        cmd = [
            NODE_PATH, str(GENERATE_PROOF_SCRIPT.resolve()),
            str(BASE_DIR.resolve()), # Argument 1: Base project directory
            CIRCUIT_NAME,            # Argument 2: Name of the circuit
            str(input_json_path.resolve()), # Argument 3: Path to input.json
            str(proof_json_path.resolve()), # Argument 4: Path for output proof.json
            str(public_json_path.resolve()) # Argument 5: Path for output public.json
        ]
        logging.info(f"Running SnarkJS command: {' '.join(cmd)}")

        # Execute the command
        # Run from BASE_DIR to ensure relative paths in scripts work correctly
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=BASE_DIR)

        logging.info(f"SnarkJS stdout:\n{result.stdout}")
        if result.stderr:
            logging.warning(f"SnarkJS stderr:\n{result.stderr}")

        # Load the generated proof and public signals from the output files
        with open(proof_json_path, 'r') as f:
            proof = json.load(f)
        with open(public_json_path, 'r') as f:
            # Public signals are expected to be ["root_decimal", "bad_leaf_hash_decimal"]
            public_signals = json.load(f)

        # Update the global state with the new attestation data
        current_commitment["root"] = root_hex # Store the hex root for the API response
        current_commitment["timestamp"] = timestamp
        current_commitment["proof"] = proof
        current_commitment["publicSignals"] = public_signals # Store decimal signals for contract submission

        logging.info(f"Successfully generated new ZK attestation. Root: {root_hex}, Timestamp: {timestamp}")

    except subprocess.CalledProcessError as e:
         logging.error(f"Error running SnarkJS command: {e}")
         logging.error(f"SnarkJS stdout:\n{e.stdout}")
         logging.error(f"SnarkJS stderr:\n{e.stderr}")
    except FileNotFoundError:
         logging.error(f"Error: '{NODE_PATH}' command not found. Is Node.js installed and in PATH?")
    except Exception as e:
        logging.error(f"Unexpected error during ZK proof generation: {e}", exc_info=True)


# --- API Endpoints ---

@app.on_event("startup")
async def startup_event():
    """Initializes the exclusion set and generates the first proof when the server starts."""
    logging.info("ASP Service starting up...")
    load_exclusion_set()
    if merkle_tree:
        generate_attestation_proof()
    else:
        logging.warning("Startup complete, but Merkle tree could not be initialized.")

@app.post("/refresh", summary="Refresh Exclusion Set and Generate New Proof")
async def refresh_attestation():
    """
    Endpoint to manually trigger reloading the exclusion list from the source
    (mock_ofac.json in this demo) and generating a new ZK attestation proof.
    """
    logging.info("Received request to refresh exclusion set and proof...")
    load_exclusion_set()
    if merkle_tree:
        generate_attestation_proof() # This updates the global current_commitment
        if current_commitment["proof"]:
             return {"message": "Attestation refreshed successfully", "commitment": current_commitment}
        else:
             raise HTTPException(status_code=500, detail="Failed to generate proof after refresh.")
    else:
        raise HTTPException(status_code=500, detail="Failed to load exclusion set during refresh.")

@app.get("/latest-attestation", summary="Get Latest Valid Attestation")
async def get_latest_attestation():
    """
    Returns the latest generated commitment details, including the Merkle root (hex),
    timestamp, the ZK proof object, and the public signals (decimal strings)
    required for on-chain verification.
    """
    if not current_commitment["root"] or not current_commitment["proof"]:
        logging.warning("Request for latest attestation failed: No valid attestation available.")
        raise HTTPException(status_code=404, detail="No valid attestation available yet. Try refreshing.")
    # Return the currently stored commitment data
    # Note: publicSignals are returned as decimal strings as expected by the contract interaction script
    return {
         "root": current_commitment["root"], # Hex root
         "timestamp": current_commitment["timestamp"],
         "proof": current_commitment["proof"], # Full proof object
         "publicSignals": current_commitment["publicSignals"] # Decimal signals ["root", "badLeaf"]
     }

# --- Run Server Command ---
# To run locally: uvicorn main:app --reload --port 8000 --app-dir asp-service
# Ensure you run this command from the project's root directory (zk-asp-attestation)