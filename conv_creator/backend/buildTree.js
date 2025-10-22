// Utility to convert flat array of nodes to d3-hierarchy compatible tree
// Usage: import and call buildTree(nodesArray)

import fs from "fs";
import path from "path";
import { fileURLToPath, pathToFileURL } from "url";

export function buildTree(flatNodes, rootId = "0") {
  const nodeMap = {};
  flatNodes.forEach((node) => (nodeMap[node.id] = { ...node, children: [] }));

  let root = null;
  flatNodes.forEach((node) => {
    if (node.target_id === rootId) {
      root = nodeMap[node.id];
    } else if (nodeMap[node.target_id]) {
      nodeMap[node.target_id].children.push(nodeMap[node.id]);
    }
  });
  return root;
}

// Only run if called directly
if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const __dirname = path.dirname(fileURLToPath(import.meta.url));
  const dataPath = path.join(__dirname, "files_root", "bp_130_0.json");
  const jsonData = JSON.parse(fs.readFileSync(dataPath, "utf-8"));

  // Expecting { users: [...], tree: {...} }
  const users = jsonData.users;
  const treeData = jsonData.tree;

  // If you need to process users, do it here
  // For now, just print them
  console.log("Users:", JSON.stringify(users, null, 2));

  // If you need to convert treeData to d3-hierarchy, you can use it directly
  // If buildTree is needed for legacy reasons, you can adapt it
  // For now, just print the tree
  console.log("Tree:", JSON.stringify(treeData, null, 2));

  // Optionally, save to a file:
  fs.writeFileSync(
    path.join(__dirname, "files_root", "bp_130_0_d3.json"),
    JSON.stringify(treeData, null, 2)
  );
}
