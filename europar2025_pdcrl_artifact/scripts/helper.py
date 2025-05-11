# File: scripts_for_docker/master_experiment_runner.py
import argparse
import json
import os
import re
import subprocess
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
import time # For basic timing if needed

# --- Configuration (paths relative to Dynamic-Task-Scheduling/ inside container) ---
MAKEFILE_NAME = "Makefile"
TESTCASE_DIR = "testcase" 
RESULTS_DIR = "results" # Subdirectory for CSVs and plots
EXECUTABLE_NAME = "./a.out" 

# --- Helper Functions (from previous version, mostly unchanged) ---
def log_info(message):
    print(f"[INFO] {message}", flush=True)

def log_warn(message):
    print(f"[WARN] {message}", flush=True)

def log_error(message):
    print(f"[ERROR] {message}", flush=True, file=sys.stderr)

def generate_matrix_if_needed(rows, cols, filepath):
    log_info(f"Ensuring matrix {rows}x{cols} at {filepath}...")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if not os.path.exists(filepath):
        log_info(f"Generating matrix {rows}x{cols} at {filepath}...")
        seed_value = rows * 100000 + cols
        np.random.seed(seed_value)
        matrix_data = np.random.rand(rows, cols) * 20 - 10
        try:
            with open(filepath, 'w') as f:
                for i in range(rows):
                    f.write(' '.join(map(lambda x: f"{x:.6f}", matrix_data[i])) + '\n')
            log_info(f"Successfully generated matrix: {filepath}")
        except IOError as e:
            log_error(f"Could not write matrix file {filepath}: {e}")
            sys.exit(1)
    else:
        log_info(f"Using existing matrix: {filepath}")
    return filepath

def update_makefile(source_file_name_only):
    log_info(f"Updating Makefile: MAIN_SRC = {source_file_name_only}")
    cmd = f"sed -i 's|^MAIN_SRC * =.*|MAIN_SRC = {source_file_name_only}|' {MAKEFILE_NAME}"
    try:
        subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        log_error(f"Failed to update Makefile: {e.stderr.decode() if e.stderr else e.stdout.decode()}")
        sys.exit(1)

def update_cpp_macro(cpp_file_path, macro_name, macro_value):
    log_info(f"Updating {cpp_file_path}: {macro_name} = {macro_value}")
    regex = f"'s/^#define[[:space:]]\\+{macro_name}[[:space:]]\\+[0-9.]\\+/#define {macro_name} {macro_value}/'"
    cmd = f"sed -i {regex} {cpp_file_path}"
    try:
        subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        log_error(f"Failed to update macro {macro_name} in {cpp_file_path}: {e.stderr.decode() if e.stderr else e.stdout.decode()}")
        sys.exit(1)

def compile_code():
    log_info("Compiling C++ code (make clean && make -j)...")
    try:
        subprocess.run("make clean", shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        compile_proc = subprocess.run("make -j", shell=True, check=True, capture_output=True, text=True)
        log_info("Compilation successful.")
    except subprocess.CalledProcessError as e:
        log_error("Compilation failed!")
        log_error(f"STDOUT:\n{e.stdout}")
        log_error(f"STDERR:\n{e.stderr}")
        sys.exit(1)

def run_executable(matrix_file_for_exe, time_regex_str, timeout_seconds=3600): # Default 1hr timeout for benchmarks
    cmd_list = [EXECUTABLE_NAME, matrix_file_for_exe]
    log_info(f"Executing: {' '.join(cmd_list)}")
    try:
        result = subprocess.run(cmd_list, capture_output=True, text=True, check=True, timeout=timeout_seconds)
        log_info("Execution finished.")
        # log_info(f"Executable STDOUT:\n{result.stdout.strip()}") # Can be very verbose
        if result.stderr:
            log_warn(f"Executable STDERR:\n{result.stderr.strip()}")

        match = re.search(time_regex_str, result.stdout)
        if match:
            exec_time_ms = float(match.group(1))
            log_info(f"Extracted execution time: {exec_time_ms:.2f} ms")
            return exec_time_ms
        else:
            log_error("Could not parse execution time from output.")
            log_info(f"Search String: {time_regex_str}")
            log_info(f"Full STDOUT for parsing failure:\n{result.stdout}")
            return None
    except subprocess.CalledProcessError as e:
        log_error(f"Execution failed with return code {e.returncode}.")
        log_error(f"STDOUT:\n{e.stdout.strip()}")
        log_error(f"STDERR:\n{e.stderr.strip()}")
        return None
    except subprocess.TimeoutExpired:
        log_error(f"Execution timed out (>{timeout_seconds}s) for: {' '.join(cmd_list)}")
        return None

def run_single_config_from_dict(config_dict, default_time_regex):
    log_info(f"--- Running Test From Dict: {config_dict.get('test_description', 'Unnamed Dict Config')} ---")
    cpp_source = config_dict["cpp_source_file"]
    num_threads = config_dict["num_threads"]
    alpha = config_dict["alpha"]
    beta = config_dict["beta"]
    use_priority = config_dict.get("use_priority_queue")
    matrix_rows = config_dict["matrix_rows"]
    matrix_cols = config_dict["matrix_cols"]
    cycles = config_dict.get("cycles", 1)
    time_regex = config_dict.get("output_time_regex", default_time_regex)

    update_makefile(cpp_source)
    update_cpp_macro(cpp_source, "NUM_THREADS", num_threads)
    update_cpp_macro(cpp_source, "ALPHA", alpha)
    update_cpp_macro(cpp_source, "BETA", beta)
    if use_priority is not None and "main" in cpp_source.lower():
        update_cpp_macro(cpp_source, "USE_PRIORITY_MAIN_QUEUE", use_priority)
    
    compile_code()
    os.makedirs(TESTCASE_DIR, exist_ok=True)
    matrix_file_for_run = os.path.join(TESTCASE_DIR, f"matrix_{matrix_rows}x{matrix_cols}.txt")
    generate_matrix_if_needed(matrix_rows, matrix_cols, matrix_file_for_run)

    total_time_ms = 0
    successful_runs = 0
    for i in range(cycles):
        log_info(f"--- Cycle {i+1}/{cycles} ---")
        exec_time = run_executable(matrix_file_for_run, time_regex, timeout_seconds=120) # Shorter timeout for single config/minimal test
        if exec_time is not None:
            total_time_ms += exec_time
            successful_runs += 1
        else:
            log_warn(f"Cycle {i+1} failed or time not parsed.")
    
    if successful_runs > 0:
        avg_time_ms = total_time_ms / successful_runs
        log_info(f"--- Average execution time over {successful_runs} successful cycle(s): {avg_time_ms:.2f} ms ---")
        return avg_time_ms
    else:
        log_error(f"--- All {cycles} cycle(s) failed for this configuration. ---")
        return None

# --- Benchmark Specific Logic ---

# Default time regex, can be overridden by specific configs if needed
DEFAULT_TIME_REGEX = r"(?:Execution Time|Time taken):\s*([0-9.]+)\s*ms"
DEFAULT_CYCLES = 3 # Default runs per configuration for benchmarks

def run_param_tuning_benchmark(results_basedir):
    log_info("===== Starting Parameter Tuning Benchmark (Experiment 1 - Fig 2 data) =====")
    
    # Configuration based on your test.py and typical Fig 2 generation
    FIXED_MATRIX_SIZE = 10800
    FIXED_THREADS = 26 # For Fig 2, typically one thread count is used for the heatmap
    
    # Alpha and Beta values range from 2 to 32 (even numbers)
    PARAM_RANGE = range(2, 33, 2) 
    
    main_cpp_file = "main.cpp" 
    
    # Ensure matrix exists for the fixed size
    matrix_file_path = os.path.join(TESTCASE_DIR, f"matrix_{FIXED_MATRIX_SIZE}x{FIXED_MATRIX_SIZE}.txt")
    generate_matrix_if_needed(FIXED_MATRIX_SIZE, FIXED_MATRIX_SIZE, matrix_file_path)

    # Set C++ source file in Makefile and fixed number of threads
    update_makefile(main_cpp_file)
    update_cpp_macro(main_cpp_file, "NUM_THREADS", FIXED_THREADS)

    # Iterate for "Without Priority" (0) and "With Priority" (1) to generate two heatmaps
    for priority_setting in [0, 1]:
        priority_str = "with_priority" if priority_setting == 1 else "without_priority"
        log_info(f"--- Running Parameter Tuning for: {priority_str.upper()} ---")
        
        # Set priority macro in intel.cpp
        update_cpp_macro(main_cpp_file, "USE_PRIORITY_MAIN_QUEUE", priority_setting)
        
        current_tuning_results = []
        
        # Estimate total valid configurations for progress logging
        estimated_valid_configs = 0
        for alpha_val_est in PARAM_RANGE:
            for beta_val_est in PARAM_RANGE:
                if beta_val_est >= alpha_val_est and \
                   beta_val_est % alpha_val_est == 0 and \
                   FIXED_MATRIX_SIZE % alpha_val_est == 0 and \
                   FIXED_MATRIX_SIZE % beta_val_est == 0:
                    estimated_valid_configs += 1
        
        actual_configs_run = 0
        for alpha_val in PARAM_RANGE:
            for beta_val in PARAM_RANGE:
                # Apply validity conditions from your test.py
                if not (beta_val >= alpha_val and \
                        beta_val % alpha_val == 0 and \
                        FIXED_MATRIX_SIZE % alpha_val == 0 and \
                        FIXED_MATRIX_SIZE % beta_val == 0):
                    continue # Skip invalid (alpha, beta) pair for this matrix size

                actual_configs_run += 1
                log_info(f"Config {actual_configs_run}/{estimated_valid_configs} ({priority_str}): Alpha={alpha_val}, Beta={beta_val}")

                update_cpp_macro(main_cpp_file, "ALPHA", alpha_val)
                update_cpp_macro(main_cpp_file, "BETA", beta_val)
                compile_code() # Recompile due to ALPHA/BETA macro changes

                cycle_times_ms = []
                for cycle in range(DEFAULT_CYCLES): # DEFAULT_CYCLES should be defined (e.g., 3)
                    log_info(f"  Run {cycle+1}/{DEFAULT_CYCLES}")
                    # DEFAULT_TIME_REGEX should be defined
                    exec_time = run_executable(matrix_file_path, DEFAULT_TIME_REGEX) 
                    if exec_time is not None:
                        cycle_times_ms.append(exec_time)
                    else:
                        log_warn(f"    Run {cycle+1} failed for Alpha={alpha_val}, Beta={beta_val}, Prio={priority_setting}. This point might be unstable.")
                        # Decide if a single failed cycle invalidates the (alpha,beta) point
                        # For parameter tuning, it's often better to get some data if possible
                
                if cycle_times_ms: # If at least one run was successful
                    avg_time_ms = np.mean(cycle_times_ms)
                    current_tuning_results.append({
                        "MatrixSize": FIXED_MATRIX_SIZE,
                        "Threads": FIXED_THREADS,
                        "Priority": priority_setting,
                        "Alpha": alpha_val,
                        "Beta": beta_val,
                        "AvgTime_ms": avg_time_ms,
                        "SuccessfulRuns": len(cycle_times_ms)
                    })
                    log_info(f"  Avg time for Alpha={alpha_val}, Beta={beta_val} ({len(cycle_times_ms)}/{DEFAULT_CYCLES} runs): {avg_time_ms:.2f} ms")
                else:
                    log_warn(f"  All runs failed for Alpha={alpha_val}, Beta={beta_val}, Prio={priority_setting}. No data recorded for this point.")
        
        # Save results and generate heatmap for the current priority setting
        if current_tuning_results:
            df = pd.DataFrame(current_tuning_results)
            csv_filename = f"param_tuning_{priority_str}_m{FIXED_MATRIX_SIZE}_t{FIXED_THREADS}.csv"
            csv_path = os.path.join(results_basedir, csv_filename)
            df.to_csv(csv_path, index=False)
            log_info(f"Parameter tuning results for {priority_str} saved to: {csv_path}")

            try:
                # Create pivot table for heatmap: Alpha on Y-axis, Beta on X-axis
                df_pivot = df.pivot_table(index='Alpha', columns='Beta', values='AvgTime_ms')
                
                plt.figure(figsize=(16, 12)) # Adjusted for better readability of heatmap
                import seaborn as sns # Ensure seaborn is in Dockerfile
                
                sns.heatmap(df_pivot, annot=True, fmt=".1f", cmap="viridis_r", 
                            linewidths=.5, annot_kws={"size": 8})
                plt.title(f"Heatmap: Avg Execution Time (ms) - {priority_str.replace('_', ' ')}\nMatrix: {FIXED_MATRIX_SIZE}x{FIXED_MATRIX_SIZE}, Threads: {FIXED_THREADS}", fontsize=14)
                plt.xlabel("Beta Value", fontsize=12)
                plt.ylabel("Alpha Value", fontsize=12)
                plt.xticks(rotation=45, ha='right')
                plt.yticks(rotation=0)
                plt.tight_layout() # Adjust layout to prevent labels from overlapping

                plot_filename = f"param_tuning_heatmap_{priority_str}_m{FIXED_MATRIX_SIZE}_t{FIXED_THREADS}.png"
                plot_path = os.path.join(results_basedir, plot_filename)
                plt.savefig(plot_path, dpi=150)
                plt.close()
                log_info(f"Heatmap saved to: {plot_path}")

                # Find and print optimal for this priority setting
                if not df.empty:
                    optimal_row = df.loc[df['AvgTime_ms'].idxmin()]
                    log_info(f"[OPTIMAL for {priority_str.upper()}] Alpha: {optimal_row['Alpha']}, Beta: {optimal_row['Beta']}, AvgTime: {optimal_row['AvgTime_ms']:.2f} ms")

            except ImportError:
                log_warn("Seaborn library not found. Skipping heatmap generation.")
            except Exception as e:
                log_warn(f"Could not generate heatmap plot for {priority_str}: {e}")
        else:
            log_warn(f"No results collected for parameter tuning ({priority_str}).")
            
    log_info("===== Parameter Tuning Benchmark FINISHED =====")


# Experiment 2: Scalability (Fig 4a, 4b)
def run_scalability_benchmark(results_basedir):
    log_info("===== Starting Scalability Benchmark (Experiment 2 - Fig 4a, 4b) =====")
    matrix_sizes = [300, 2400, 4800, 7200, 10800]
    fixed_threads_list = [26, 52]
    
    optimal_ab_no_prio = {"alpha": 18, "beta": 18, "prio": 0, "source": "main.cpp", "label": "Without Priority"}
    optimal_ab_with_prio = {"alpha": 20, "beta": 20, "prio": 1, "source": "main.cpp", "label": "With Priority"}
    optimal_ab_barrier = {"alpha": 16, "beta": 16, "prio": None, "source": "barrier_main.cpp", "label": "Barrier"}
    
    configs_to_run = [optimal_ab_no_prio, optimal_ab_with_prio, optimal_ab_barrier]
    all_results = []

    for threads in fixed_threads_list:
        log_info(f"--- Running for {threads} THREADS ---")
        for m_size in matrix_sizes:
            log_info(f"  Matrix Size: {m_size}x{m_size}")
            matrix_file_path = os.path.join(TESTCASE_DIR, f"matrix_{m_size}x{m_size}.txt")
            generate_matrix_if_needed(m_size, m_size, matrix_file_path)

            for config in configs_to_run:
                log_info(f"    Config: {config['label']}")
                update_makefile(config['source'])
                update_cpp_macro(config['source'], "NUM_THREADS", threads)
                update_cpp_macro(config['source'], "ALPHA", config['alpha'])
                update_cpp_macro(config['source'], "BETA", config['beta'])
                if config['prio'] is not None:
                    update_cpp_macro(config['source'], "USE_PRIORITY_MAIN_QUEUE", config['prio'])
                compile_code()

                cycle_times_ms = []
                for cycle in range(DEFAULT_CYCLES):
                    log_info(f"      Run {cycle+1}/{DEFAULT_CYCLES}")
                    exec_time = run_executable(matrix_file_path, DEFAULT_TIME_REGEX)
                    if exec_time is not None:
                        cycle_times_ms.append(exec_time)
                
                if cycle_times_ms:
                    avg_time = np.mean(cycle_times_ms)
                    all_results.append({
                        "Method": config['label'], "MatrixSize": m_size, 
                        "Threads": threads, "AvgTime_ms": avg_time
                    })
                    log_info(f"      Avg time: {avg_time:.2f} ms")
    
    if all_results:
        df = pd.DataFrame(all_results)
        df["AvgTime_s"] = df["AvgTime_ms"] / 1000.0
        csv_path = os.path.join(results_basedir, "scalability_results.csv")
        df.to_csv(csv_path, index=False)
        log_info(f"Scalability results saved to {csv_path}")

        # Plotting Fig 4a and 4b
        for threads_to_plot in fixed_threads_list:
            df_plot = df[df["Threads"] == threads_to_plot]
            if df_plot.empty: continue
            plt.figure(figsize=(10, 6))
            markers = {'Barrier': '^', 'Without Priority': 'o', 'With Priority': 's'}
            for method_name, group_data in df_plot.groupby("Method"):
                plt.plot(group_data["MatrixSize"], group_data["AvgTime_s"], marker=markers.get(method_name, 'x'), label=method_name)
            plt.xlabel("Matrix Size")
            plt.ylabel("Execution Time (s)")
            fig_label = 'a' if threads_to_plot == 26 else 'b'
            plt.title(f"Scalability Comparison ({threads_to_plot} Threads) - Fig 4{fig_label}")
            plt.legend()
            plt.grid(True)
            plot_path = os.path.join(results_basedir, f"fig4{fig_label}_scalability_{threads_to_plot}threads.png")
            plt.savefig(plot_path)
            plt.close()
            log_info(f"Plot saved to {plot_path}")
    else:
        log_warn("No results for scalability benchmark.")
    log_info("===== Scalability Benchmark FINISHED =====")


# Experiment 3: Throughput (Fig 5)
def run_throughput_benchmark(results_basedir):
    log_info("===== Starting Throughput Benchmark (Experiment 3 - Fig 5) =====")
    fixed_m_size = 8192 
    thread_points_for_plot = [4, 24, 44, 64, 84, 100]
    threads_to_run_data_for = sorted(list(set(thread_points_for_plot + [4*i for i in range(1,27)]))) # Combine and unique

    # Use same optimal_ab configs as scalability
    optimal_ab_no_prio = {"alpha": 12, "beta": 12, "prio": 0, "source": "main.cpp", "label": "Without Priority"}
    optimal_ab_with_prio = {"alpha": 20, "beta": 20, "prio": 1, "source": "main.cpp", "label": "With Priority"}
    optimal_ab_barrier = {"alpha": 12, "beta": 12, "prio": None, "source": "barrier_main.cpp", "label": "Barrier"}
    configs_to_run = [optimal_ab_no_prio, optimal_ab_with_prio, optimal_ab_barrier]
    
    all_results = []
    matrix_file_path = os.path.join(TESTCASE_DIR, f"matrix_{fixed_m_size}x{fixed_m_size}.txt")
    generate_matrix_if_needed(fixed_m_size, fixed_m_size, matrix_file_path)

    for config in configs_to_run:
        log_info(f"--- Running for Config: {config['label']} ---")
        update_makefile(config['source'])
        update_cpp_macro(config['source'], "ALPHA", config['alpha'])
        update_cpp_macro(config['source'], "BETA", config['beta'])
        if config['prio'] is not None:
            update_cpp_macro(config['source'], "USE_PRIORITY_MAIN_QUEUE", config['prio'])

        for threads in threads_to_run_data_for:
            log_info(f"  Threads: {threads}")
            update_cpp_macro(config['source'], "NUM_THREADS", threads)
            compile_code() # Recompile if NUM_THREADS changed

            cycle_times_ms = []
            for cycle in range(DEFAULT_CYCLES):
                log_info(f"    Run {cycle+1}/{DEFAULT_CYCLES}")
                exec_time = run_executable(matrix_file_path, DEFAULT_TIME_REGEX)
                if exec_time is not None:
                    cycle_times_ms.append(exec_time)
            
            if cycle_times_ms:
                avg_time = np.mean(cycle_times_ms)
                all_results.append({
                    "Method": config['label'], "Threads": threads, 
                    "MatrixSize": fixed_m_size, "AvgTime_ms": avg_time
                })
                log_info(f"    Avg time: {avg_time:.2f} ms")

    if all_results:
        df = pd.DataFrame(all_results)
        df["AvgTime_s"] = df["AvgTime_ms"] / 1000.0
        csv_path = os.path.join(results_basedir, "throughput_results.csv")
        df.to_csv(csv_path, index=False)
        log_info(f"Throughput results saved to {csv_path}")

        # Plotting Fig 5
        plt.figure(figsize=(10, 6))
        markers = {'Barrier': '^', 'Without Priority': 'o', 'With Priority': 's'}
        df_plot_fig5 = df[df["Threads"].isin(thread_points_for_plot)] # Filter for plot points

        for method_name, group_data in df_plot_fig5.groupby("Method"):
            plt.plot(group_data["Threads"], group_data["AvgTime_s"], marker=markers.get(method_name, 'x'), label=method_name)
        
        plt.xlabel("Thread Count")
        plt.ylabel("Execution Time (s)")
        plt.title(f"Throughput Evaluation (Matrix: {fixed_m_size}x{fixed_m_size}) - Fig 5 Style")
        plt.legend()
        plt.grid(True, which="both", ls="-")
        plt.yscale('log') # Fig 5 uses log scale for Y-axis
        plt.xticks(thread_points_for_plot)
        plt.xlim(min(thread_points_for_plot)-2, max(thread_points_for_plot)+2 if thread_points_for_plot else 0)
        plot_path = os.path.join(results_basedir, "fig5_throughput.png")
        plt.savefig(plot_path)
        plt.close()
        log_info(f"Plot saved to {plot_path}")
    else:
        log_warn("No results for throughput benchmark.")
    log_info("===== Throughput Benchmark FINISHED =====")


# --- Main Entry Point ---
def main():
    parser = argparse.ArgumentParser(description="Master experiment runner for ParQR artifact.")
    parser.add_argument("--config", type=str, help="Path to a JSON configuration file for a single run (e.g., minimal test).")
    parser.add_argument("--experiment", type=str, 
                        choices=["param_tuning", "scalability", "throughput", "all_required", "all"], 
                        help="Run a predefined benchmark experiment or all.")
    
    args = parser.parse_args()

    log_info(f"Master runner script CWD: {os.getcwd()}")
    # Basic check for Makefile
    if not os.path.exists(MAKEFILE_NAME):
        log_error(f"Makefile '{MAKEFILE_NAME}' not found in CWD. Ensure Docker -w flag is correct.")
        sys.exit(1)
    
    # Create base results directory
    os.makedirs(RESULTS_DIR, exist_ok=True)

    if args.config:
        log_info(f"Running single configuration from: {args.config}")
        try:
            with open(args.config, 'r') as f:
                config_data = json.load(f)
        except FileNotFoundError:
            log_error(f"Configuration file not found: {args.config}"); sys.exit(1)
        except json.JSONDecodeError:
            log_error(f"Error decoding JSON: {args.config}"); sys.exit(1)
        
        avg_time = run_single_config_from_dict(config_data, DEFAULT_TIME_REGEX)
        if avg_time is not None:
            log_info(f"Minimal test '{config_data.get('test_description')}' completed. Avg time: {avg_time:.2f} ms")
            print(f"MINIMAL_TEST_PASSED: Average time {avg_time:.2f} ms")
        else:
            log_error(f"Minimal test '{config_data.get('test_description')}' FAILED.")
            print("MINIMAL_TEST_FAILED")
            sys.exit(1)

    elif args.experiment:
        if args.experiment == "param_tuning" or args.experiment == "all":
            run_param_tuning_benchmark(RESULTS_DIR)
        if args.experiment == "scalability" or args.experiment == "all_required" or args.experiment == "all":
            run_scalability_benchmark(RESULTS_DIR)
        if args.experiment == "throughput" or args.experiment == "all_required" or args.experiment == "all":
            run_throughput_benchmark(RESULTS_DIR)
        log_info(f"Benchmark experiment(s) '{args.experiment}' finished.")
        container_results_path = os.path.abspath(RESULTS_DIR)
        log_info(f"All results for this run were saved inside the container at: {container_results_path}")
        print(f"BENCHMARK_COMPLETED:{args.experiment}")


    else:
        log_warn("No --config or --experiment specified. Nothing to do.")
        parser.print_help()

if __name__ == "__main__":
    # Ensure seaborn is available if plotting heatmaps directly
    try:
        import seaborn
    except ImportError:
        log_warn("Seaborn not installed, heatmap for parameter tuning might not be generated by this script.")
        pass # Continue without it, plotting will try/except
    main()
