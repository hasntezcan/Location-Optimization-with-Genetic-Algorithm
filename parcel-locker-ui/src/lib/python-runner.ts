import { spawn } from 'child_process';

export async function detectPythonCommand(): Promise<string> {
  if (process.env.PYTHON_CMD && process.env.PYTHON_CMD.trim()) {
    return process.env.PYTHON_CMD.trim();
  }

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
    } catch {
      // Continue trying next candidate
    }
  }

  const tried = candidates.join(", ");
  throw new Error(`Python command could not be resolved. Tried: ${tried}.`);
}

type PythonRunOptions = {
  cwd?: string;
  env?: NodeJS.ProcessEnv;
};

export async function runPythonScript(
  scriptPath: string,
  args: string[] = [],
  options: PythonRunOptions = {}
): Promise<{ stdout: string; stderr: string }> {
  const pythonCmd = await detectPythonCommand();
  console.log(`Detected Python command: ${pythonCmd}`);

  return new Promise((resolve, reject) => {
    const proc = spawn(pythonCmd, [scriptPath, ...args], {
      cwd: options.cwd,
      env: options.env,
    });
    
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
