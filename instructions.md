# ZK ASP Attestation PoC - Setup & Execution Guide

This guide provides detailed step-by-step instructions to set up the development environment, compile the necessary components (ZK circuits, smart contracts), and run the end-to-end demonstration of the ZK ASP Attestation framework.

**Project Goal:** Demonstrate how an Association Set Provider (ASP) can generate Zero-Knowledge Proofs attesting to the integrity of its exclusion set (list of "bad" addresses) and how these proofs can be verified on-chain using a registry contract.

**Disclaimer:** This is a demo project with simplified ZK logic and without significant security audits and enhancements.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

1.  **Node.js:** Version 18 or higher recommended. (Verify with `node -v`)
2.  **npm:** Node Package Manager, usually installed with Node.js. (Verify with `npm -v`)
3.  **Python:** Version 3.9 or higher recommended. (Verify with `python --version` or `python3 --version`)
4.  **pip:** Python package installer, usually installed with Python. (Verify with `pip --version` or `pip3 --version`)
5.  **Git:** For cloning the repository (if applicable).
6.  **Circom Compiler:** Install globally via npm:
    ```bash
    npm install -g circom
    ```
    (Verify with `circom --version`)

## Setup Steps

**(Run these commands in your terminal, navigated to the project's root directory: `d:/ZK Eng/ASP Project`)**

---

**Step 1: Install Node.js Dependencies**

*   **Command:**
    ```bash
    npm install
    ```
*   **What it does:** Reads the `package.json` file and downloads/installs all the necessary Node.js libraries listed under `dependencies` and `devDependencies`. This includes:
    *   `hardhat`: Ethereum development environment for compiling, deploying, and testing smart contracts.
    *   `@nomicfoundation/hardhat-toolbox`: Includes useful Hardhat plugins like ethers.js, waffle, etc.
    *   `snarkjs`: Library for Zero-Knowledge proof generation and verification (Groth16).
    *   `circomlib`: Standard library of Circom circuits (like MerkleTree).
    *   `axios`: HTTP client used by the submission script to talk to the ASP service.
*   **Expected Outcome:** A `node_modules` directory will be created containing all installed packages. You might see warnings about optional dependencies, which are usually safe to ignore for this demo. Success is indicated by the command completing without errors.
*   **Troubleshooting:**
    *   *Error: `npm command not found`*: Ensure Node.js and npm are installed and their paths are configured correctly in your system's environment variables.
    *   *Network Errors*: Check your internet connection.
    *   *Permission Errors*: Try running the command with administrator privileges (e.g., using `sudo` on Linux/macOS, or "Run as Administrator" on Windows), although this shouldn't typically be necessary.

---

**Step 2: Install Python Dependencies**

*   **Command:**
    ```bash
    pip install -r asp-service/requirements.txt
    ```
    *(**Recommended:** Create and activate a Python virtual environment first to avoid conflicts with global packages. Commands:*
    *   `python -m venv venv` (or `python3`)
    *   `source venv/bin/activate` (Linux/macOS) OR `venv\Scripts\activate` (Windows)
    *   *Then run the `pip install` command.*)
*   **What it does:** Reads the `asp-service/requirements.txt` file and installs the required Python libraries for the ASP backend service:
    *   `fastapi`: Modern web framework for building APIs.
    *   `uvicorn`: ASGI server to run the FastAPI application. `[standard]` includes recommended extras.
    *   `python-dotenv`: For potentially loading environment variables (though not strictly used in this demo).
    *   `py-merkle-trees`: Library used to construct the Merkle tree for the exclusion set.
*   **Expected Outcome:** The command should download and install the packages, finishing with a success message.
*   **Troubleshooting:**
    *   *Error: `pip command not found`*: Ensure Python and pip are installed and in your system's PATH.
    *   *Network Errors*: Check your internet connection.
    *   *Build Errors (rare for these packages)*: Might indicate missing system dependencies (like C compilers). Check the specific error message for clues. Using a virtual environment often helps.

---

**Step 3: Download Powers of Tau File**

*   **ACTION REQUIRED:** This step requires manual intervention.
*   **What it does:** The ZK-SNARK setup (specifically Groth16 Phase 2) requires a "Powers of Tau" file. This file contains cryptographic parameters generated from a secure multi-party computation ceremony. It's essential for the security of the generated keys.
*   **How to do it:**
    1.  Search online for a trusted source for the "Perpetual Powers of Tau" ceremony files. The snarkjs documentation often provides links.
    2.  You need a file suitable for the circuit's complexity. Our circuit (`Attestation(4)`) is small, so `powersOfTau28_hez_final_14.ptau` (supporting up to 2^14 constraints) is sufficient and commonly available.
    3.  Download this file (it will be around 100MB).
    4.  **Crucially, place the downloaded `.ptau` file directly inside the `circuits/` directory within your project.**
    5.  **Ensure the filename is exactly `powersOfTau28_hez_final_14.ptau`.** If you download a file with a different name or for a different constraint level, you *must* update the `ptauName` variable inside `scripts/setup_zk.js`.
*   **Expected Outcome:** The `.ptau` file exists in the `circuits/` directory.
*   **Troubleshooting:**
    *   *Cannot find file*: Double-check download sources. Ensure you are downloading the `.ptau` file itself, not a webpage.
    *   *Wrong file*: If the `setup:zk` script later fails mentioning the ptau file, ensure you downloaded the correct one and placed it correctly.

---

**Step 4: Compile Circuit & Run ZK Setup**

*   **Command:**
    ```bash
    npm run setup:zk
    ```
*   **What it does:** This command executes the script defined as `setup:zk` in your `package.json`. It performs several critical ZK-related tasks using `circom` and `snarkjs`:
    1.  **Compiles Circuit (`npm run compile:circuit` called internally):** Runs `circom` on `circuits/attestation/attestation.circom`. This checks the circuit for errors and generates:
        *   `zk-out/attestation.r1cs`: The constraint system in R1CS format.
        *   `zk-out/attestation_js/attestation.wasm`: The WebAssembly code for generating witnesses.
        *   `zk-out/attestation.sym`: Symbol file for debugging.
    2.  **Generates Initial ZKey:** Creates the first phase 2 key (`zk-out/attestation_0000.zkey`) using the R1CS file and the downloaded Powers of Tau file.
    3.  **Contributes Entropy (Demo):** Performs a single contribution to the phase 2 ceremony (for demonstration purposes only) to generate the final proving key (`zk-out/attestation_final.zkey`). **This step is insecure for production.**
    4.  **Exports Verification Key:** Extracts the verification key (`zk-out/attestation_verification_key.json`) from the final proving key.
    5.  **Generates Verifier Contract:** Creates the Solidity smart contract (`contracts/Verifier.sol`) based on the verification key. This contract will be deployed to the blockchain to verify proofs.
*   **Expected Outcome:** The script should run for a minute or two, printing progress for each step. It should finish with "✅ ZK Setup Complete!" and list the generated artifact paths. Crucially, `contracts/Verifier.sol` should now exist.
*   **Troubleshooting:**
    *   *Error: `circom command not found`*: Ensure Circom is installed globally (`npm install -g circom`).
    *   *Error: Powers of Tau file not found*: Verify Step 3 was completed correctly. Check the filename and location.
    *   *Circom compilation errors*: Check `circuits/attestation/attestation.circom` for syntax errors.
    *   *SnarkJS errors*: Often related to file paths, permissions, or issues during the setup phases. Check the specific error message. Ensure the `.ptau` file is valid.

---

**Step 5: Compile Smart Contracts**

*   **Command:**
    ```bash
    npm run compile:contracts
    ```
*   **What it does:** Uses Hardhat to compile all Solidity contracts found in the `contracts/` directory (`ASPRegistry.sol` and the generated `Verifier.sol`). This generates bytecode and Application Binary Interfaces (ABIs) needed for deployment and interaction, storing them in the `artifacts/` directory.
*   **Expected Outcome:** Hardhat will print compilation status, hopefully ending with a success message like "Compiled 2 Solidity files successfully". The `artifacts/` directory will be created/updated.
*   **Troubleshooting:**
    *   *Solidity Compiler Errors*: Check the contract code (`ASPRegistry.sol`, `Verifier.sol`) for syntax errors or version mismatches (ensure the `pragma` version matches the one specified in `hardhat.config.js`).
    *   *Missing Artifacts Error*: If `Verifier.sol` wasn't generated correctly in Step 4, this step will fail. Re-run Step 4.

---

## Running the End-to-End Demo

You will need **three separate terminal windows/tabs**, all navigated to the project root (`d:/ZK Eng/ASP Project`).

**Step 6: Run Local Blockchain (Terminal 1)**

*   **Command:**
    ```bash
    npx hardhat node
    ```
*   **What it does:** Starts a local Hardhat Ethereum node, simulating a real blockchain for testing. It provides RPC endpoints (usually `http://127.0.0.1:8545/`) and pre-funded accounts for deployment and transactions.
*   **Expected Outcome:** The terminal will show output indicating the node has started, listing available accounts and their private keys (keep these private if using on a public testnet!). **Keep this terminal running in the background.**
*   **Troubleshooting:**
    *   *Port Conflict*: If port 8545 is already in use, Hardhat might fail. Stop the other process or configure Hardhat to use a different port in `hardhat.config.js`.
    *   *Hardhat Errors*: Ensure Hardhat is installed correctly (`npm install`).

---

**Step 7: Deploy Contracts (Terminal 2)**

*   **Command:**
    ```bash
    npm run deploy:local
    ```
*   **What it does:** Executes the `scripts/deploy.js` script using Hardhat. This script connects to the local Hardhat node (running in Terminal 1), deploys the compiled `Verifier` contract, then deploys the `ASPRegistry` contract (passing the Verifier's address to its constructor), and finally registers the deployer's address as an initial ASP in the registry.
*   **Expected Outcome:** The script will print deployment progress for both contracts and their addresses. It will finish with a "Deployment Summary" and a reminder to copy the `ASPRegistry Address`.
*   **ACTION REQUIRED:** **Carefully copy the `ASPRegistry Address`** (e.g., `0x5FbDB2315678afecb367f032d93F642f64180aa3`) printed in this terminal.
*   **Troubleshooting:**
    *   *Cannot connect to node*: Ensure the Hardhat node (Terminal 1) is running and accessible. Check the RPC URL if needed.
    *   *Deployment Errors*: Could be due to contract compilation issues (re-run Step 5), insufficient gas (unlikely on local node), or errors in the deployment script logic. Check the specific error message.

---

**Step 8: Configure Submission Script (Manual Action)**

*   **ACTION REQUIRED:**
    1.  Open the file `scripts/submit_attestation.js` in your text editor.
    2.  Find the line: `const REGISTRY_ADDRESS = "YOUR_ASP_REGISTRY_CONTRACT_ADDRESS";`
    3.  **Replace the placeholder string** `"YOUR_ASP_REGISTRY_CONTRACT_ADDRESS"` **with the actual `ASPRegistry Address` you copied in Step 7.**
    4.  Save the `submit_attestation.js` file.
*   **What it does:** This configures the script that simulates the ASP, telling it where the registry contract is deployed on the local blockchain.
*   **Expected Outcome:** The `submit_attestation.js` file is saved with the correct contract address.
*   **Troubleshooting:**
    *   *Incorrect Address*: If you paste the wrong address, the final submission step will fail to interact with the contract. Double-check the address from Step 7.

---

**Step 9: Start ASP Service (Terminal 3)**

*   **Command:**
    ```bash
    npm run start:asp
    ```
*   **What it does:** Executes the `asp-service/main.py` script using `uvicorn`. This starts the Python FastAPI backend server. On startup, it loads the mock exclusion list, builds the Merkle tree, and calls the Node.js helper script (`scripts/generate_proof.js`) via a subprocess to generate the initial ZK proof for the current state.
*   **Expected Outcome:** The terminal will show Uvicorn startup messages. Then, you should see logging output from the Python script indicating it's loading the list, building the tree, running the SnarkJS command (via the Node.js helper), and finally confirming "Successfully generated new ZK attestation". The service will then wait for API requests. **Keep this terminal running.**
*   **Troubleshooting:**
    *   *Python Errors*: Check `asp-service/main.py` for syntax errors. Ensure all Python dependencies from `requirements.txt` are installed (re-run Step 2 if needed).
    *   *Error running SnarkJS*: This usually means the `generate_proof.js` script failed. Check its output/errors printed in this terminal. Common causes: Node.js not found, incorrect paths passed to the script, issues with the ZK artifacts (`.wasm`, `.zkey`) generated in Step 4.
    *   *Port Conflict*: If port 8000 is in use, Uvicorn will fail. Stop the other process or change the port in the `npm run start:asp` command (e.g., `uvicorn main:app --reload --port 8001 ...`). If you change the port, you also need to update `ASP_SERVICE_URL` in `scripts/submit_attestation.js`.

---

**Step 10: Submit Attestation (Terminal 2)**

*   **Command:**
    ```bash
    npm run submit
    ```
    *(Run this in the same terminal where you deployed the contracts in Step 7, after ensuring the ASP service in Terminal 3 has successfully started and generated the initial proof).*
*   **What it does:** Executes the `scripts/submit_attestation.js` script. This script:
    1.  Makes an HTTP GET request to the running ASP service (Terminal 3) at `/latest-attestation` to fetch the current Merkle root, ZK proof, and public signals.
    2.  Formats the proof and public signals correctly for the Solidity contract.
    3.  Connects to the `ASPRegistry` contract (using the address you configured in Step 8) on the local Hardhat node (Terminal 1).
    4.  Sends a transaction calling the `submitAttestation` function, passing the proof components and public inputs.
    5.  Waits for the transaction to be confirmed.
    6.  Calls `getLatestValidAttestation` on the contract to verify the data was stored correctly.
*   **Expected Outcome:** The script should print messages indicating it fetched the data, formatted the proof, sent the transaction, and received confirmation. It should end with "✅ Attestation submitted successfully!" and display the details of the attestation retrieved from the contract, confirming the on-chain root matches the submitted one and `isValid` is true.
*   **Troubleshooting:**
    *   *Error fetching attestation*: Ensure the ASP service (Terminal 3) is running and accessible at `http://127.0.0.1:8000`. Check for errors in Terminal 3.
    *   *Invalid REGISTRY_ADDRESS*: Ensure you correctly copied and pasted the address in Step 8.
    *   *Transaction Reverted*: This usually means the on-chain proof verification failed.
        *   Check the revert reason printed (e.g., "ASPRegistry: Invalid ZK proof provided").
        *   Verify the `Verifier.sol` contract was generated correctly (Step 4) and deployed (Step 7).
        *   Ensure the proof generated by the ASP service (Step 9) is valid for the inputs. Check Terminal 3 for errors during proof generation.
        *   Confirm the public inputs passed to `submitAttestation` match those expected by the `Verifier.sol` contract (in this case, just the root).
    *   *Network Errors*: Ensure the Hardhat node (Terminal 1) is still running.

---

This completes the setup and execution flow. You have now simulated an ASP generating a ZK proof of its exclusion set's integrity and submitted it for on-chain verification.