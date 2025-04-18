// Define the circom version
pragma circom 2.0.0;

// Include necessary libraries from circomlib
// MerkleTree: For verifying Merkle proofs
// Comparators: For checking equality/inequality
include "../../node_modules/circomlib/circuits/merkleTree.circom";
include "../../node_modules/circomlib/circuits/comparators.circom";

/*
 * @title Simplified ASP Attestation Circuit (Demo)
 * @notice This circuit demonstrates a basic ZK proof concept for ASPs.
 * It proves knowledge of a Merkle path for a given leaf ('safe' leaf)
 * that correctly hashes up to the publicly committed root.
 * It also includes a *very basic* check ensuring this 'safe' leaf
 * is different from a publicly known 'bad' leaf hash.
 *
 * @dev **IMPORTANT LIMITATIONS FOR DEMO:**
 *   - This circuit DOES NOT prove non-membership of the 'safe' leaf within the
 *     entire exclusion set represented by the root. It only proves knowledge
 *     of *one* valid path for the provided 'safe' leaf.
 *   - The check against 'knownBadLeafHash' is only comparing the *single*
 *     proven 'safe' leaf against *one* known bad leaf. It doesn't prevent
 *     the 'safe' leaf from being another bad leaf not provided as input.
 *   - A production system would require more sophisticated cryptographic
 *     accumulators or set membership/non-membership proof techniques.
 *
 * @param levels The number of levels in the Merkle tree (e.g., 4 for 2^4=16 leaves).
 */
template Attestation (levels) {
    // === Public Signals ===
    // These values are known by both the prover (ASP) and the verifier (contract).

    // The committed Merkle root hash of the ASP's exclusion set.
    signal input root;

    // The hash of a *single*, publicly known "bad" address/leaf.
    // In a real system, verifying against a full set would be needed.
    signal input knownBadLeafHash;

    // === Private Signals ===
    // These values are known only by the prover (ASP).

    // A leaf hash that the ASP knows is in the tree and wants to prove knowledge of.
    // For this demo's purpose, this leaf should NOT be the knownBadLeafHash.
    signal input leaf;

    // The sibling nodes along the Merkle path from the 'leaf' to the 'root'.
    signal input pathElements[levels];

    // The position (0 for left, 1 for right) of the nodes at each level of the path.
    signal input pathIndices[levels];

    // === Constraints (Circuit Logic) ===

    // 1. Verify the Merkle Proof
    // Instantiate the MerkleProof component from circomlib.
    component merkleProof = MerkleProof(levels);
    // Connect the private inputs (leaf, path) to the MerkleProof component.
    merkleProof.leaf <== leaf;
    for (var i = 0; i < levels; i++) {
        merkleProof.pathElements[i] <== pathElements[i];
        merkleProof.pathIndices[i] <== pathIndices[i];
    }
    // Add a constraint: The root calculated by the MerkleProof component using
    // the private inputs must equal the public input 'root'.
    // This proves the prover knows a valid path for 'leaf' within the committed tree.
    merkleProof.root === root;

    // 2. Verify the 'safe' leaf is not the specific 'knownBadLeafHash'
    // Instantiate the IsEqual component to compare the proven leaf and the bad leaf.
    component isNotBad = IsEqual();
    // Connect the inputs for comparison.
    isNotBad.in[0] <== leaf;
    isNotBad.in[1] <== knownBadLeafHash;
    // Add a constraint: The output of IsEqual must be 0.
    // IsEqual outputs 1 if inputs are equal, 0 otherwise.
    // This asserts that 'leaf' and 'knownBadLeafHash' are different.
    isNotBad.out === 0;
}

/*
 * @notice Instantiate the main component for the circuit.
 * @dev We define the public inputs here. For this demo, 'root' and 'knownBadLeafHash' are public.
 * @param levels Set the tree depth. 4 levels = 2^4 = 16 leaves. Adjust if needed.
 */
component main {public [root, knownBadLeafHash]} = Attestation(4); // Tree depth = 4