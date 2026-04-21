import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promises as fs } from 'fs';
import path from 'path';
import { promisify } from 'util';

const execPromise = promisify(exec);

const UI_ROOT = process.cwd();
const PROJECT_ROOT = path.resolve(UI_ROOT, "..");

const GA_PARAMETERS_PATH = path.join(PROJECT_ROOT, "src/main/java/config/GAParameters.java");
const PLOT_SCRIPT_PATH = path.join(PROJECT_ROOT, "scripts/plot_archives.py");
const PROCESS_SCRIPT_PATH = path.join(UI_ROOT, "src/scripts/process_ga_data.py");
const OUTPUT_LATEST_PLOT_PATH = path.join(PROJECT_ROOT, "output/archive_comparison_latest.png");
const UI_LATEST_PLOT_PATH = path.join(UI_ROOT, "public/mock/archive_comparison_latest.png");

export async function POST(request: Request) {
  try {
    const { k, populationSize, maxGenerations, mutationRate } = await request.json();

    if (typeof k !== 'number' || k < 1) {
      return NextResponse.json({ error: 'Invalid k value' }, { status: 400 });
    }

    console.log(`Updating GA Parameters in ${GA_PARAMETERS_PATH}`);

    // 1. Update GAParameters.java
    let content = await fs.readFile(GA_PARAMETERS_PATH, 'utf8');
    
    // Update K
    content = content.replace(
      /public static final int K = \d+;/,
      `public static final int K = ${k};`
    );
    
    // Update POPULATION_SIZE if provided
    if (typeof populationSize === 'number') {
      content = content.replace(
        /public static final int POPULATION_SIZE = \d+;/,
        `public static final int POPULATION_SIZE = ${populationSize};`
      );
    }
    
    // Update MAX_GENERATIONS if provided
    if (typeof maxGenerations === 'number') {
      content = content.replace(
        /public static final int MAX_GENERATIONS = \d+;/,
        `public static final int MAX_GENERATIONS = ${maxGenerations};`
      );
    }
    
    // Update MUTATION_RATE if provided
    if (typeof mutationRate === 'number') {
      content = content.replace(
        /public static final double MUTATION_RATE = [\d\.]+;/,
        `public static final double MUTATION_RATE = ${mutationRate};`
      );
    }

    await fs.writeFile(GA_PARAMETERS_PATH, content);

    console.log('Running Maven optimization...');

    // 2. Run Maven optimization
    const { stdout: mvnStdout } = await execPromise('mvn compile exec:java', {
      cwd: PROJECT_ROOT,
    });

    console.log('Maven Output:', mvnStdout);

    console.log('Generating Plots...');

    // 3. Run Plot script
    const { stdout: plotStdout } = await execPromise(`python3 "${PLOT_SCRIPT_PATH}"`, {
      cwd: PROJECT_ROOT,
    });
    console.log('Plot Output:', plotStdout);

    try {
      await fs.copyFile(OUTPUT_LATEST_PLOT_PATH, UI_LATEST_PLOT_PATH);
      console.log(`Updated UI plot: ${UI_LATEST_PLOT_PATH}`);
    } catch (copyError: unknown) {
      const message = copyError instanceof Error ? copyError.message : String(copyError);
      console.error('Failed to copy latest plot into UI public folder:', message);
    }

    console.log('Processing GA data for UI...');

    // 4. Run Python process script
    const { stdout: pyStdout } = await execPromise(`python3 "${PROCESS_SCRIPT_PATH}"`, {
      cwd: PROJECT_ROOT,
    });

    console.log('Python Output:', pyStdout);

    return NextResponse.json({ 
      success: true, 
      message: 'Optimization completed, plot generated, and data processed',
      k: k,
      populationSize,
      maxGenerations,
      mutationRate,
      paretoInfo: pyStdout.split('\n').filter(l => l.includes('Pareto')).pop()
    });

  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error);
    console.error('Error running GA:', message);
    return NextResponse.json({ 
      error: 'Failed to run optimization', 
      details: message 
    }, { status: 500 });
  }
}
