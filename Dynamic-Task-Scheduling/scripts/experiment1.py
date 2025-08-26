#!/usr/bin/env python3
import re
import subprocess
import sys
import numpy as np
import csv
import os
import matplotlib.pyplot as plt # For plotting graphs
from collections import defaultdict

# ------------------------------------------------------------------------------
# Script for Experiment 1: Parameter Tuning (Alpha, Beta) for QR Factorization
# Corresponds to generating data for heatmaps like Figure 2 in the paper.
# ------------------------------------------------------------------------------

# --- Configuration Parameters ---
# For Figure 2 (Heatmap): Fixed matrix size and thread count
FIXED_MATRIX_SIZE_FOR_TUNING = 10800 # As per paper for Fig 2
FIXED_THREADS_FOR_TUNING = 26       # As per paper for Fig 2

# Range for Alpha and Beta parameters (Paper Fig 2: 2 to 32)
ALPHA_RANGE = range(2, 33) # 2 to 32 inclusive
BETA_RANGE = range(2, 33)  # 2 to 32 inclusive

RUNS_PER_CONFIG = 3  # Number of times to run each (alpha, beta) pair for averaging

# File and Path Settings (assuming script is in ParQR/scripts/)
TESTCASE_FOLDER = "../testcase"
EXECUTABLE_NAME = "../a.out"
MAKEFILE_NAME = "../Makefile"
INTEL_SRC_FILE_NAME = "intel.cpp" # Source file for lock-free queue versions
# BARRIER_SRC_FILE_NAME = "barrier_main.cpp" # If you also want to tune barrier

# --- Helper Functions (Adapted from previous scripts) ---

def update_makefile_for_source(source_file_name_only):
    source_path_in_makefile = f"src/{source_file_name_only}"
    cmd = f"sed -i 's|^MAIN_SRC * =.*|MAIN_SRC = {source_path_in_makefile}|' {MAKEFILE_NAME}"
    subprocess.run(cmd, shell=True, check=True)
    print(f"[INFO] Makefile updated to use MAIN_SRC = {source_path_in_makefile}")

def get_cpp_source_path(source_file_name_only):
    return os.path.join("..", source_file_name_only)

def update_threads_in_cpp(cpp_file_path, threads):
    cmd = f"sed -i 's/^#define[[:space:]]\\+NUM_THREADS[[:space:]]\\+[0-9]\\+/#define NUM_THREADS {threads}/' {cpp_file_path}"
    subprocess.run(cmd, shell=True, check=True)
    print(f"[INFO] {os.path.basename(cpp_file_path)}: NUM_THREADS set to {threads}.")

def update_priority_in_cpp(cpp_file_path, priority_flag): # 0 for no priority, 1 for with priority
    cmd = f"sed -i 's/^#define[[:space:]]\\+USE_PRIORITY_MAIN_QUEUE[[:space:]]\\+[0-9]\\+/#define USE_PRIORITY_MAIN_QUEUE {priority_flag}/' {cpp_file_path}"
    subprocess.run(cmd, shell=True, check=True)
    mode = "WITH PRIORITY" if priority_flag == 1 else "WITHOUT PRIORITY"
    print(f"[INFO] {os.path.basename(cpp_file_path)}: USE_PRIORITY_MAIN_QUEUE set to {priority_flag} ({mode}).")

def update_alpha_beta_in_cpp(cpp_file_path, alpha, beta):
    cmd_alpha = f"sed -i 's/^#define[[:space:]]\\+ALPHA[[:space:]]\\+[0-9.]\\+/#define ALPHA {alpha}/' {cpp_file_path}"
    cmd_beta  = f"sed -i 's/^#define[[:space:]]\\+BETA[[:space:]]\\+[0-9.]\\+/#define BETA {beta}/' {cpp_file_path}"
    subprocess.run(cmd_alpha, shell=True, check=True)
    subprocess.run(cmd_beta, shell=True, check=True)
    print(f"[INFO] {os.path.basename(cpp_file_path)}: ALPHA set to {alpha}, BETA set to {beta}.")

def compile_code():
    print("[INFO] Compiling QR factorization code...")
    compile_dir = os.path.dirname(MAKEFILE_NAME) # Should be ParQR root
    subprocess.run("make clean", shell=True, check=True, cwd=compile_dir, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    compile_process = subprocess.run("make all", shell=True, cwd=compile_dir, capture_output=True, text=True)
    if compile_process.returncode != 0:
        print("[ERROR] Compilation failed!")
        print("STDOUT:\n", compile_process.stdout)
        print("STDERR:\n", compile_process.stderr)
        sys.exit(1)
    print("[INFO] Compilation successful.")

def get_matrix_file_path(matrix_dim):
    filename = os.path.join(TESTCASE_FOLDER, f"matrix_{matrix_dim}x{matrix_dim}.txt")
    if not os.path.exists(filename):
        print(f"[ERROR] Matrix file {filename} not found. Please ensure it exists.")
        # TODO: Optionally, add a call to a matrix generation script if available.
        sys.exit(1)
    return filename

def run_qr_executable(matrix_dim, matrix_file_path_abs_or_rel_to_script):
    # Executable expects matrix path relative to its own location (ParQR root)
    matrix_file_for_exe = os.path.join(os.path.basename(TESTCASE_FOLDER), os.path.basename(matrix_file_path_abs_or_rel_to_script))
    cmd_list = [EXECUTABLE_NAME, str(matrix_dim), str(matrix_dim), matrix_file_for_exe]

    print(f"[INFO] Executing: {' '.join(cmd_list)}")
    try:
        exec_dir = os.path.dirname(EXECUTABLE_NAME) # ParQR root if EXECUTABLE_NAME is ../bin/QR
        run_output = subprocess.run(cmd_list, capture_output=True, text=True, check=True, cwd=exec_dir, timeout=600) # 10 min timeout
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Execution failed for {cmd_list} with code {e.returncode}.")
        print("STDOUT:\n", e.stdout)
        print("STDERR:\n", e.stderr)
        return None
    except subprocess.TimeoutExpired:
        print(f"[ERROR] Execution timed out for {cmd_list}.")
        return None

    # Extract execution time
    match = re.search(r"(?:Execution Time|Time taken):\s*([0-9.]+)\s*ms", run_output.stdout)
    if match:
        time_ms = float(match.group(1))
        print(f"[RESULT] Execution time: {time_ms:.2f} ms")
        return time_ms
    else:
        print("[ERROR] Could not parse execution time from output.")
        print("STDOUT:\n", run_output.stdout)
        return None

# --- Main Experiment Logic ---
def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"[INFO] Changed working directory to: {script_dir}")
    print(f"[INFO] Starting Parameter Tuning Experiment (for Fig. 2 style heatmap data).")
    print(f"[CONFIG] Matrix Size: {FIXED_MATRIX_SIZE_FOR_TUNING}x{FIXED_MATRIX_SIZE_FOR_TUNING}")
    print(f"[CONFIG] Threads: {FIXED_THREADS_FOR_TUNING}")
    print(f"[CONFIG] Alpha/Beta Range: {ALPHA_RANGE.start}-{ALPHA_RANGE.stop-1}")
    print(f"[CONFIG] Runs per (Alpha, Beta) pair: {RUNS_PER_CONFIG}")

    # Prepare matrix file path once
    matrix_file = get_matrix_file_path(FIXED_MATRIX_SIZE_FOR_TUNING)

    # Ensure initial compilation with default settings in intel.cpp
    # This also sets the NUM_THREADS for the first run.
    intel_cpp_path = get_cpp_source_path(INTEL_SRC_FILE_NAME)
    update_makefile_for_source(INTEL_SRC_FILE_NAME)
    update_threads_in_cpp(intel_cpp_path, FIXED_THREADS_FOR_TUNING)
    # Initial compile will happen before the first parameter update.

    # Iterate for "Without Priority" (0) and "With Priority" (1)
    for priority_setting in [0, 1]:
        priority_str = "with_priority" if priority_setting == 1 else "without_priority"
        print(f"\n[PHASE] Running parameter tuning for: {priority_str.upper().replace('_', ' ')}")
        
        # Update priority setting in intel.cpp
        update_priority_in_cpp(intel_cpp_path, priority_setting)
        # No need to recompile here, will happen after alpha/beta update

        results_for_this_priority = []
        output_csv_filename = f"param_tuning_results_{priority_str}_m{FIXED_MATRIX_SIZE_FOR_TUNING}_t{FIXED_THREADS_FOR_TUNING}.csv"
        
        total_configs = len(ALPHA_RANGE) * len(BETA_RANGE)
        current_config_num = 0

        for alpha_val in ALPHA_RANGE:
            for beta_val in BETA_RANGE:
                current_config_num += 1
                print(f"\n[PROGRESS] Config {current_config_num}/{total_configs} ({priority_str}) | Alpha={alpha_val}, Beta={beta_val}")

                # --- Condition from original script: if beta % alpha != 0: continue ---
                # This condition significantly prunes the search space.
                # For a full heatmap as in Fig 2, you might want to remove this.
                # If kept, the heatmap will be sparse.
                # For now, let's keep it to match your original logic, but add a note.
                if beta_val % alpha_val != 0:
                    print(f"[SKIP] Skipping Alpha={alpha_val}, Beta={beta_val} because Beta is not a multiple of Alpha.")
                    continue
                
                # --- Condition from original: if alpha == beta and n % alpha == 0 and n % beta == 0 ---
                # The `alpha == beta` part is too restrictive for a general heatmap.
                # The `n % alpha == 0` might be a specific requirement of your tiling.
                # For Fig 2, it's an exhaustive sweep. Let's remove these specific conditions for general tuning.
                # If your QR *requires* matrix_size % alpha == 0, you should add that check.
                # if FIXED_MATRIX_SIZE_FOR_TUNING % alpha_val != 0 or FIXED_MATRIX_SIZE_FOR_TUNING % beta_val != 0:
                #     print(f"[SKIP] Skipping Alpha={alpha_val}, Beta={beta_val} because matrix size {FIXED_MATRIX_SIZE_FOR_TUNING} is not divisible by Alpha or Beta.")
                #     continue

                update_alpha_beta_in_cpp(intel_cpp_path, alpha_val, beta_val)
                compile_code() # Recompile because ALPHA/BETA are macros

                run_times_ms = []
                for run_num in range(1, RUNS_PER_CONFIG + 1):
                    print(f"[RUN {run_num}/{RUNS_PER_CONFIG}] Alpha={alpha_val}, Beta={beta_val}, Prio={priority_setting}")
                    exec_time_ms = run_qr_executable(FIXED_MATRIX_SIZE_FOR_TUNING, matrix_file)
                    if exec_time_ms is not None:
                        run_times_ms.append(exec_time_ms)
                    else:
                        print(f"[WARN] Run {run_num} failed for Alpha={alpha_val}, Beta={beta_val}. Skipping this run.")
                        # Optionally, break or decide how to handle failed runs for averaging
                
                if run_times_ms: # If at least one run was successful
                    avg_time_ms = np.mean(run_times_ms)
                    print(f"[RESULT] Avg time for Alpha={alpha_val}, Beta={beta_val} ({priority_str}): {avg_time_ms:.2f} ms")
                    results_for_this_priority.append({
                        "MatrixSize": FIXED_MATRIX_SIZE_FOR_TUNING,
                        "Threads": FIXED_THREADS_FOR_TUNING,
                        "Priority": priority_setting,
                        "Alpha": alpha_val,
                        "Beta": beta_val,
                        "AvgTime_ms": avg_time_ms
                    })
                else:
                    print(f"[WARN] All runs failed for Alpha={alpha_val}, Beta={beta_val}. No data recorded.")
        
        # Save results for the current priority setting
        if results_for_this_priority:
            results_dir = "results_param_tuning"
            os.makedirs(results_dir, exist_ok=True)
            full_csv_path = os.path.join(results_dir, output_csv_filename)
            
            df_results = pd.DataFrame(results_for_this_priority)
            df_results.to_csv(full_csv_path, index=False)
            print(f"\n[SUCCESS] Parameter tuning results for {priority_str} saved to: {full_csv_path}")

            # Find and print optimal for this priority setting
            if not df_results.empty:
                optimal_row = df_results.loc[df_results['AvgTime_ms'].idxmin()]
                print(f"[OPTIMAL for {priority_str.upper()}]")
                print(f"  Alpha: {optimal_row['Alpha']}, Beta: {optimal_row['Beta']}")
                print(f"  Average Time: {optimal_row['AvgTime_ms']:.2f} ms")
        else:
            print(f"[WARN] No results collected for {priority_str}. CSV not written.")

    print("\n[INFO] All parameter tuning experiments completed.")
    print("[INFO] You can now use the generated CSV files to create heatmaps (e.g., using Python's Matplotlib/Seaborn).")

if __name__ == "__main__":
    main()
