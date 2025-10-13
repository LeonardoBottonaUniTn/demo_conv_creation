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
  const flatNodes = JSON.parse(fs.readFileSync(dataPath, "utf-8"));

  const tree = buildTree(flatNodes);

  console.log(JSON.stringify(tree, null, 2));
  // Optionally, save to a file:
  fs.writeFileSync(
    path.join(__dirname, "files_root", "bp_130_0_d3.json"),
    JSON.stringify(tree, null, 2)
  );
}
