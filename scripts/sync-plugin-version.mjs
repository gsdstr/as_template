import { readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const packagePath = join(root, "package.json");
const pluginPath = join(root, ".codex-plugin", "plugin.json");
const check = process.argv.includes("--check");

const packageJson = JSON.parse(await readFile(packagePath, "utf8"));

let pluginJson;
try {
    pluginJson = JSON.parse(await readFile(pluginPath, "utf8"));
} catch (error) {
    if (error.code === "ENOENT") {
        process.exit(0);
    }
    throw error;
}

if (pluginJson.version === packageJson.version) {
    process.exit(0);
}

if (check) {
    console.error(
        `Plugin version (${pluginJson.version}) does not match package.json (${packageJson.version}).`,
    );
    process.exitCode = 1;
} else {
    pluginJson.version = packageJson.version;
    await writeFile(pluginPath, `${JSON.stringify(pluginJson, null, 2)}\n`);
}
