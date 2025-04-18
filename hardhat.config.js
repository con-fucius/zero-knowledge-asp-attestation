// Import Hardhat toolbox for common tasks and plugins
require("@nomicfoundation/hardhat-toolbox");

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  // Specify the Solidity compiler version used in the contracts
  solidity: "0.8.19",
  // Define network configurations
  networks: {
    // Default local network configuration provided by Hardhat
    hardhat: {
      // chainId: 1337 // Optional: Uncomment if you need a specific chain ID for local testing
    },
    // Example configuration for deploying to a testnet like Sepolia (optional)
    // sepolia: {
    //   url: process.env.SEPOLIA_RPC_URL || "YOUR_SEPOLIA_RPC_URL", // Use environment variable or replace placeholder
    //   accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : ["YOUR_PRIVATE_KEY"] // Use environment variable or replace placeholder
    // }
  },
  // Optional: Configure paths if your project structure differs from default Hardhat layout
  // paths: {
  //   sources: "./contracts",
  //   tests: "./test",
  //   cache: "./cache",
  //   artifacts: "./artifacts"
  // }
};