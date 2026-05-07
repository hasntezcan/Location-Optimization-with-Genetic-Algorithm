import { spawn } from 'child_process';
import { promises as fs } from 'fs';
import path from 'path';
import { runPythonScript } from '@/lib/python-runner';

const UI_ROOT = process.cwd();
const PROJECT_ROOT = path.resolve(UI_ROOT, "..");
const PLOT_SCRIPT_PATH = path.join(PROJECT_ROOT, "scripts/plot_archives.py");
const PROCESS_SCRIPT_PATH = path.join(UI_ROOT, "src/scripts/process_ga_data.py");
const OUTPUT_LATEST_PLOT_PATH = path.join(PROJECT_ROOT, "output/archive_comparison_latest.png");
const UI_LATEST_PLOT_PATH = path.join(UI_ROOT, "public/mock/archive_comparison_latest.png");

type StreamEvent = Record<string, unknown>;

type ProcessErrorInfo = {
  message: string;
  scriptPath?: string;
  stderr?: string;
};

function getErrorInfo(error: unknown): ProcessErrorInfo {
  if (error instanceof Error) {
    return { message: error.message };
  }

  if (typeof error === "object" && error !== null) {
    const value = error as { message?: unknown; scriptPath?: unknown; stderr?: unknown };
    return {
      message: typeof value.message === "string" ? value.message : String(error),
      scriptPath: typeof value.scriptPath === "string" ? value.scriptPath : undefined,
      stderr: typeof value.stderr === "string" ? value.stderr : undefined,
    };
  }

  return { message: String(error) };
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { 
      k, 
      populationSize, 
      maxGenerations, 
      mutationRate, 
      crossoverRate, 
      archiveSize, 
      randomSeed 
    } = body;

    if (typeof k !== 'number' || k < 1) {
      return new Response(JSON.stringify({ error: 'Invalid k value' }), { status: 400 });
    }

    const encoder = new TextEncoder();

    const stream = new ReadableStream({
      async start(controller) {
        function sendEvent(data: StreamEvent) {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`));
        }

        try {
          sendEvent({ stage: 'Starting optimization', message: 'Preparing Maven environment...' });

          const args: string[] = [];
          if (k !== undefined) args.push('--k', String(k));
          if (populationSize !== undefined) args.push('--populationSize', String(populationSize));
          if (maxGenerations !== undefined) args.push('--maxGenerations', String(maxGenerations));
          if (mutationRate !== undefined) args.push('--mutationRate', String(mutationRate));
          if (crossoverRate !== undefined) args.push('--crossoverRate', String(crossoverRate));
          if (archiveSize !== undefined) args.push('--archiveSize', String(archiveSize));
          if (randomSeed !== undefined && randomSeed !== null && randomSeed !== '') {
            args.push('--randomSeed', String(randomSeed));
          }

          console.log(`Running Maven GA with args: ${args.join(' ')}`);

          // Need to use exec args like -Dexec.args="--k 8 --populationSize 100"
          const execArgsStr = args.length > 0 ? `-Dexec.args=${args.join(' ')}` : '';
          const mvnArgs = ['compile', 'exec:java'];
          if (execArgsStr) {
            mvnArgs.push(execArgsStr);
          }

          sendEvent({ stage: 'Running Java GA', message: 'Compiling and starting GA...' });

          const isWindows = process.platform === "win32";
          const command = isWindows ? "cmd.exe" : "mvn";
          const commandArgs = isWindows 
            ? ["/d", "/s", "/c", "mvn.cmd", ...mvnArgs] 
            : mvnArgs;

          await new Promise<void>((resolve, reject) => {
            const proc = spawn(command, commandArgs, { 
              cwd: PROJECT_ROOT,
              windowsHide: true,
            });

            let errorBuffer = '';

            proc.stdout.on('data', (data) => {
              const lines = data.toString().split('\n');
              for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed) continue;
                
                const progressMatch = trimmed.match(/PROGRESS\s+generation=(\d+)\s+max=(\d+)/i);
                if (progressMatch) {
                  const currentGeneration = parseInt(progressMatch[1], 10);
                  const parsedMaxGenerations = parseInt(progressMatch[2], 10);
                  const pct = Math.round((currentGeneration / parsedMaxGenerations) * 100);
                  sendEvent({
                    stage: 'Running Java GA',
                    currentGeneration,
                    maxGenerations: parsedMaxGenerations,
                    progressPercent: pct,
                    log: `[Gen ${currentGeneration}/${parsedMaxGenerations}] Optimizing… ${pct}%`
                  });
                } else if (trimmed.startsWith('STAGE')) {
                   sendEvent({
                     stage: 'Running Java GA',
                     log: trimmed
                   });
                } else if (
                  trimmed.startsWith('BOUNDS_DEBUG') ||
                  trimmed.includes('BOUNDS DEBUG') ||
                  trimmed.includes('ASSESSMENT BOUNDS') ||
                  trimmed.includes('NORMALIZED RANGES') ||
                  trimmed.includes('HYPERVOLUME') ||
                  trimmed.includes('Total runtime') ||
                  trimmed.includes('Bounds pool size') ||
                  trimmed.includes('Initial archive') ||
                  trimmed.includes('Final archive') ||
                  trimmed.includes('ideal') ||
                  trimmed.includes('nadir') ||
                  trimmed.includes('Ideal') ||
                  trimmed.includes('Nadir') ||
                  trimmed.includes('Initial ND') ||
                  trimmed.includes('Final ND') ||
                  trimmed.includes('hypervolume')
                ) {
                   console.log(`[java] ${trimmed}`);
                   // Do NOT send verbose debug logs to the UI, keep them in terminal only
                   if (!trimmed.includes('BOUNDS_DEBUG') && !trimmed.includes('BOUNDS DEBUG')) {
                     sendEvent({ stage: 'Running Java GA', log: trimmed });
                   }
                }
              }
            });

            proc.stderr.on('data', (data) => {
              errorBuffer += data.toString();
            });

            proc.on('error', (err) => {
              const detailedError = [
                'Failed to spawn Maven process.',
                `Command: ${command}`,
                `Args: ${commandArgs.join(' ')}`,
                `CWD: ${PROJECT_ROOT}`,
                `Platform: ${process.platform}`,
                `Original error: ${err.message}`
              ].join('\n');
              reject(new Error(detailedError));
            });

            proc.on('close', (code) => {
              if (code !== 0) {
                reject(new Error(`Java GA process failed with exit code ${code}. Stderr: ${errorBuffer}`));
              } else {
                resolve();
              }
            });
          });

          sendEvent({ stage: 'Generating plots', message: 'Running plot_archives.py...' });
          console.log('Generating Plots...');
          const plotResult = await runPythonScript(PLOT_SCRIPT_PATH);
          console.log('Plot Output:', plotResult.stdout);

          sendEvent({ stage: 'Syncing UI assets', message: 'Copying latest plot...' });
          try {
            await fs.copyFile(OUTPUT_LATEST_PLOT_PATH, UI_LATEST_PLOT_PATH);
            console.log(`Updated UI plot: ${UI_LATEST_PLOT_PATH}`);
          } catch (copyError: unknown) {
            const message = copyError instanceof Error ? copyError.message : String(copyError);
            console.error('Failed to copy latest plot into UI public folder:', message);
          }

          sendEvent({ stage: 'Processing GA output', message: 'Running process_ga_data.py...' });
          console.log('Processing GA data for UI...');
          const processResult = await runPythonScript(PROCESS_SCRIPT_PATH);
          console.log('Python Output:', processResult.stdout);

          const paretoInfo = processResult.stdout.split('\n').filter(l => l.includes('Pareto')).pop();

          sendEvent({ 
            stage: 'Completed', 
            message: 'Optimization completed successfully.',
            success: true,
            paretoInfo 
          });

          controller.close();
        } catch (error: unknown) {
          const errorInfo = getErrorInfo(error);
          console.error('Optimization error:', error);
          
          let stage = 'Failed';
          let errorMessage = errorInfo.message;
          let stderr = '';

          if (errorInfo.message.includes('Python command could not be resolved')) {
            stage = 'Failed while detecting Python';
          } else if (errorInfo.scriptPath === PLOT_SCRIPT_PATH) {
            stage = 'Failed while generating plots';
            stderr = errorInfo.stderr || '';
            errorMessage = errorInfo.message;
          } else if (errorInfo.scriptPath === PROCESS_SCRIPT_PATH) {
            stage = 'Failed while processing GA output';
            stderr = errorInfo.stderr || '';
            errorMessage = errorInfo.message;
          } else if (errorInfo.message.includes('Java GA process failed')) {
            stage = 'Failed during Java GA execution';
          }

          sendEvent({
            stage,
            error: errorMessage,
            stderr
          });
          controller.close();
        }
      }
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });

  } catch (error: unknown) {
    const errorInfo = getErrorInfo(error);
    console.error('Error starting GA stream:', error);
    return new Response(JSON.stringify({ 
      error: 'Failed to start optimization', 
      details: errorInfo.message
    }), { status: 500, headers: { 'Content-Type': 'application/json' } });
  }
}
