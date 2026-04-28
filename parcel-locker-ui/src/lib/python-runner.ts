import { spawn } from 'child_process';

export async function detectPythonCommand(): Promise<string> {
  const isWindows = process.platform === "win32";
  const candidates = isWindows ? ["py", "python"] : ["python3", "python"];

  for (const cmd of candidates) {
    try {
      await new Promise<void>((resolve, reject) => {
        const proc = spawn(cmd, ["--version"]);
        proc.on('error', reject);
        proc.on('close', (code) => {
          if (code === 0) resolve();
          else reject(new Error(`Exit code ${code}`));
        });
      });
      return cmd;
    } catch (e) {
      // Continue trying next candidate
    }
  }

  const tried = candidates.join(", ");
  throw new Error(`Python command could not be resolved. Tried: ${tried}.`);
}

export async function runPythonScript(scriptPath: string, args: string[] = []): Promise<{ stdout: string; stderr: string }> {
  const pythonCmd = await detectPythonCommand();
  console.log(`Detected Python command: ${pythonCmd}`);

  return new Promise((resolve, reject) => {
    const proc = spawn(pythonCmd, [scriptPath, ...args]);
    
    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    proc.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    proc.on("error", (error) => {
      reject({
        message: "Failed to spawn Python process",
        error,
        pythonCmd,
        scriptPath,
        args,
        stderr
      });
    });

    proc.on("close", (code) => {
      if (code !== 0) {
        reject({
          message: `Python script failed with exit code ${code}`,
          code,
          pythonCmd,
          scriptPath,
          args,
          stderr
        });
      } else {
        resolve({ stdout, stderr });
      }
    });
  });
}
