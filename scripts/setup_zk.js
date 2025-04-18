// Helper script for ZK trusted setup steps using SnarkJS
 // This script automates the setup (key generation, verifier generation), assuming compilation is done separately.
 const snarkjs = require("snarkjs");
 const fs = require("fs");
 const path = require("path");
 const util = require('util');
 // const exec = util.promisify(require('child_process').exec); // No longer needed here

 // --- Configuration ---
 const circuitName = "attestation";
 const ptauName = "powersOfTau28_hez_final_14.ptau"; // User needs to download this
 const baseDir = path.resolve(__dirname, ".."); // Project root directory
 const zkOutDir = path.join(baseDir, "zk-out"); // Directory for ZK artifacts
 const circuitsDir = path.join(baseDir, "circuits"); // Directory containing circuit source and ptau
 const contractsDir = path.join(baseDir, "contracts"); // Directory for Solidity contracts
 const ptauPath = path.join(circuitsDir, ptauName); // Full path to Powers of Tau file
 const circuitFilePath = path.join(circuitsDir, circuitName, `${circuitName}.circom`); // Path to the main circuit file
 // ---

 async function setup() {
     console.log(`Starting ZK setup for circuit: ${circuitName}...`);
     console.log(`Base directory: ${baseDir}`);

     // --- Pre-checks ---
     if (!fs.existsSync(ptauPath)) {
         console.error(`\n❌ Error: Powers of Tau file not found at ${ptauPath}`);
         console.error(`   Please download it (e.g., from Perpetual Powers of Tau ceremony archives)`);
         console.error(`   and place it in the '${path.relative(baseDir, circuitsDir)}' directory.`);
         process.exit(1);
     }
     // Check for circuit file existence for context, though compilation happens elsewhere
     if (!fs.existsSync(circuitFilePath)) {
         console.error(`\n❌ Error: Circuit file not found at ${circuitFilePath}`);
         process.exit(1);
     }

     // --- Check for Compiled Artifacts (Expected from 'npm run compile:circuit') ---
     const r1csPath = path.join(zkOutDir, `${circuitName}.r1cs`);
     const wasmPath = path.join(zkOutDir, `${circuitName}_js`, `${circuitName}.wasm`); // WASM path might differ based on compile script
     const symPath = path.join(zkOutDir, `${circuitName}.sym`);

     console.log(`\n1. Checking for compiled circuit artifacts in ${zkOutDir}...`);
     if (!fs.existsSync(r1csPath) || !fs.existsSync(wasmPath) || !fs.existsSync(symPath)) {
         console.error(`\n❌ Error: Compiled circuit artifacts (R1CS, WASM, SYM) not found in ${zkOutDir}.`);
         console.error(`   Please ensure 'npm run compile:circuit' runs successfully first before running 'node scripts/setup_zk.js'.`);
         process.exit(1);
     } else {
         console.log(`   Found compiled artifacts.`);
     }

     // --- Step 2: Generate Initial ZKey (Phase 2 Ceremony - Part 1) ---
     const zkeyPathPhase1 = path.join(zkOutDir, `${circuitName}_0000.zkey`);
     console.log(`\n2. Generating initial zkey (${path.basename(zkeyPathPhase1)})...`);
     try {
         // Use logger (console) for progress updates from snarkjs
         await snarkjs.zKey.newZKey(r1csPath, ptauPath, zkeyPathPhase1, console);
         console.log("   Initial zkey generated successfully.");
     } catch (error) {
         console.error(`\n❌ Error generating initial zkey: ${error}`);
         process.exit(1);
     }

     // --- Step 3: Contribute to Phase 2 (Single contribution for demo) ---
     const zkeyPathFinal = path.join(zkOutDir, `${circuitName}_final.zkey`);
     console.log(`\n3. Contributing to phase 2 (generating ${path.basename(zkeyPathFinal)})...`);
     try {
         // In a real setup, multiple contributions are essential for security.
         // The "entropy" string should ideally be truly random.
         await snarkjs.zKey.contribute(zkeyPathPhase1, zkeyPathFinal, "Demo Contribution 1", "Some random entropy string for demo", console);
         console.log("   Phase 2 contribution complete.");
         // Clean up intermediate key
         // fs.unlinkSync(zkeyPathPhase1);
         // console.log(`   Removed intermediate key: ${path.basename(zkeyPathPhase1)}`);
     } catch (error) {
         console.error(`\n❌ Error during phase 2 contribution: ${error}`);
         process.exit(1);
     }

     // --- Step 4: Export Verification Key ---
     const verificationKeyPath = path.join(zkOutDir, `${circuitName}_verification_key.json`);
     console.log(`\n4. Exporting verification key (${path.basename(verificationKeyPath)})...`);
     try {
         const verificationKey = await snarkjs.zKey.exportVerificationKey(zkeyPathFinal, console);
         fs.writeFileSync(verificationKeyPath, JSON.stringify(verificationKey, null, 2));
         console.log("   Verification key exported successfully.");
     } catch (error) {
         console.error(`\n❌ Error exporting verification key: ${error}`);
         process.exit(1);
     }

     // --- Step 5: Generate Verifier Contract ---
     const verifierContractPath = path.join(contractsDir, "Verifier.sol"); // Place directly in contracts
     console.log(`\n5. Generating Verifier contract (${path.basename(verifierContractPath)})...`);
     try {
         // Get the correct Solidity template for snarkjs v0.7.0+
         const templates = { groth16: await snarkjs.zKey.getVerifierGroth16() };
         const verifierCode = await snarkjs.zKey.exportSolidityVerifier(zkeyPathFinal, templates, console);
         fs.writeFileSync(verifierContractPath, verifierCode);
         console.log("   Verifier contract generated successfully.");
     } catch (error) {
         console.error(`\n❌ Error generating Verifier contract: ${error}`);
         process.exit(1);
     }

     console.log("\n✅ ZK Setup Complete (Key Generation & Verifier Export)!");
     console.log("   Summary of generated artifacts:");
     console.log(`   - Final Proving Key: ${path.relative(baseDir, zkeyPathFinal)}`);
     console.log(`   - Verification Key:  ${path.relative(baseDir, verificationKeyPath)}`);
     console.log(`   - Verifier Contract: ${path.relative(baseDir, verifierContractPath)}`);
 }

 // Execute the setup function
 setup().catch(err => {
     console.error("\n❌ ZK Setup failed:", err);
     process.exit(1);
 });