#!/usr/bin/env python3
import re
import subprocess
import sys
import numpy as np
import csv
import os
import matplotlib.pyplot as plt
import pandas as pd
from collections import defaultdict

# ------------------------------------------------------------------------------
# Matrix Generation Helper
# ------------------------------------------------------------------------------
def generate_matrix_if_needed(rows, cols, filepath, force_regenerate=False):
    """
    Checks if a matrix file exists. If not, or if force_regenerate is True,
    generates a new matrix with a fixed seed and saves it.
    """
    if not os.path.exists(filepath) or force_regenerate:
        print(f"[INFO] Matrix file {filepath} not found or regeneration forced. Generating new matrix {rows}x{cols}...")
        
        # Ensure the directory for the filepath exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        seed_value = rows * 100000 + cols 
        np.random.seed(seed_value)
        matrix_data = np.random.rand(rows, cols) * 20 - 10 # Values between -10 and 10

        try:
            with open(filepath, 'w') as f:
                for i in range(rows):
                    f.write(' '.join(map(lambda x: f"{x:.6f}", matrix_data[i])) + '\n')
            print(f"[INFO] Successfully generated and saved matrix to {filepath}")
        except IOError as e:
            print(f"[ERROR] Could not write matrix file {filepath}: {e}")
            sys.exit(1)
    else:
        print(f"[DEBUG] Matrix file {filepath} found. Using existing file.")

# ------------------------------------------------------------------------------
# Global Parameters for Experiment 3 (Scalability Analysis - Fig 4a, 4b)
# ------------------------------------------------------------------------------
matrix_sizes_to_test = [300, 2400, 4800, 7200, 10800]
fixed_thread_counts = [26, 52]
runs_per_config = 3 # Number of cycles per configuration

# --- Paths RELATIVE TO THIS SCRIPT'S LOCATION (e.g., ParQR/scripts/) ---
base_testcase_folder_rel = "../testcase" 
executable_name_rel = "../a.out"        
makefile_name_rel = "../Makefile"        
parqr_root_dir_rel = ".."                
# --- Absolute paths will be resolved in main() or relevant functions ---

# Optimal Alpha/Beta from Experiment 4.2 (Parameter Tuning)
ALPHA_BETA_NO_PRIORITY = {"alpha": 12, "beta": 12}
ALPHA_BETA_WITH_PRIORITY = {"alpha": 30, "beta": 30}
ALPHA_BETA_BARRIER = {"alpha": 12, "beta": 12} # VERIFY THIS CHOICE for Barrier

# ------------------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------------------
def update_makefile(abs_makefile_path, source_file_name_only):
    source_path_in_makefile = f"{source_file_name_only}" # Assumes Makefile expects src/file.cpp
    cmd = f"sed -i 's|^MAIN_SRC * =.*|MAIN_SRC = {source_path_in_makefile}|' {abs_makefile_path}"
    subprocess.run(cmd, shell=True, check=True)
    print(f"[DEBUG] Updated Makefile ({abs_makefile_path}) to use {source_path_in_makefile}")

def update_cpp_macro(abs_source_file_path, macro_name, macro_value):
    regex = f"'s/^#define[[:space:]]\\+{macro_name}[[:space:]]\\+[0-9.]\\+/#define {macro_name} {macro_value}/'"
    cmd = f"sed -i {regex} {abs_source_file_path}"
    subprocess.run(cmd, shell=True, check=True)
    print(f"[DEBUG] Updated {abs_source_file_path}: {macro_name}={macro_value}")

def compile_code_cli(abs_parqr_root_dir):
    print("[DEBUG] Compiling code...")
    subprocess.run("make clean", shell=True, check=True, cwd=abs_parqr_root_dir)
    ret = subprocess.run("make -j", shell=True, cwd=abs_parqr_root_dir) # Use make -j for faster compiles
    if ret.returncode != 0:
        print("[ERROR] Compilation failed.")
        sys.exit(1)
    print("[DEBUG] Compilation succeeded.")

def get_matrix_file_path_for_exe(current_rows, current_cols, abs_parqr_root_dir, rel_testcase_folder_from_root="testcase"):
    # Path to the testcase folder from the ParQR root
    abs_testcase_dir = os.path.join(abs_parqr_root_dir, rel_testcase_folder_from_root)
    matrix_file_abs_path = os.path.join(abs_testcase_dir, f"matrix_{current_rows}x{current_cols}.txt")
    
    generate_matrix_if_needed(current_rows, current_cols, matrix_file_abs_path)
    
    if not os.path.exists(matrix_file_abs_path):
        print(f"[ERROR] Matrix file {matrix_file_abs_path} still does not exist after generation attempt.")
        sys.exit(1)
    # Return path relative to parqr_root_dir for the executable
    return os.path.join(rel_testcase_folder_from_root, f"matrix_{current_rows}x{current_cols}.txt")


def run_executable_cli(abs_parqr_root_dir, current_rows, current_cols, matrix_file_path_for_exe):
    # Executable is expected to be in abs_parqr_root_dir, named "a.out"
    executable_in_cwd = "./a.out" 

    cmd_list = [executable_in_cwd, matrix_file_path_for_exe]
    print(f"[DEBUG] Running command (from {abs_parqr_root_dir}): {' '.join(cmd_list)}")
    try:
        result = subprocess.run(cmd_list, capture_output=True, text=True, check=True, cwd=abs_parqr_root_dir)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Error running executable. Return code: {e.returncode}")
        print(f"  Stdout: {e.stdout.strip()}")
        print(f"  Stderr: {e.stderr.strip()}")
        return None
    except FileNotFoundError as e:
        print(f"[ERROR] FileNotFoundError when trying to run executable: {e}")
        print(f"  Attempted to run: {' '.join(cmd_list)}")
        print(f"  From CWD: {abs_parqr_root_dir}")
        abs_exe_path_check = os.path.join(abs_parqr_root_dir, executable_in_cwd.lstrip('./'))
        print(f"  Does '{abs_exe_path_check}' exist? {os.path.exists(abs_exe_path_check)}")
        return None

    match = re.search(r"(?:Execution Time|Time taken):\s*([0-9.]+)\s*ms", result.stdout)
    if match:
        return float(match.group(1))
    else:
        print("[ERROR] Time not found in executable output."); print("--- STDOUT ---"); print(result.stdout.strip()); print("--- STDERR ---"); print(result.stderr.strip())
        return None

def run_scalability_experiment(abs_parqr_root_dir, abs_makefile_path, source_file_name_only, 
                               current_matrix_size, thread_count, priority_val, alpha_val, beta_val):
    # Path to the specific C++ source file (e.g., intel.cpp, barrier_main.cpp)
    abs_source_file_path = os.path.join(abs_parqr_root_dir, source_file_name_only)

    update_makefile(abs_makefile_path, source_file_name_only)
    update_cpp_macro(abs_source_file_path, "NUM_THREADS", thread_count)
    if priority_val is not None: # For intel.cpp
        update_cpp_macro(abs_source_file_path, "USE_PRIORITY_MAIN_QUEUE", priority_val)
    update_cpp_macro(abs_source_file_path, "ALPHA", alpha_val)
    update_cpp_macro(abs_source_file_path, "BETA", beta_val)

    compile_code_cli(abs_parqr_root_dir)
    
    # Get matrix path relative to project root, as expected by executable
    matrix_file_for_exe = get_matrix_file_path_for_exe(current_matrix_size, current_matrix_size, abs_parqr_root_dir)
    
    exec_time = run_executable_cli(abs_parqr_root_dir, current_matrix_size, current_matrix_size, matrix_file_for_exe)
    return exec_time

# ------------------------------------------------------------------------------
# Main Experiment Execution
# ------------------------------------------------------------------------------
def main():
    # --- Resolve absolute paths once at the beginning ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir) # Set current working directory to the script's directory

    abs_parqr_root_dir = os.path.abspath(parqr_root_dir_rel)
    abs_executable_path = os.path.join(abs_parqr_root_dir, executable_name_rel.lstrip("../").lstrip("./"))
    abs_makefile_path = os.path.join(abs_parqr_root_dir, makefile_name_rel.lstrip("../").lstrip("./"))
    # --- End of path resolution ---

    if not os.path.exists(abs_executable_path):
        print(f"[INFO] Executable not found at {abs_executable_path}. Attempting initial compile...")
        compile_code_cli(abs_parqr_root_dir) 
        if not os.path.exists(abs_executable_path):
             print(f"[ERROR] Executable still not found at {abs_executable_path} after compile. Exiting.")
             sys.exit(1)
        else:
            print(f"[INFO] Executable found at {abs_executable_path} after compilation.")
    else:
        print(f"[INFO] Executable found at {abs_executable_path}.")


    all_run_data = []
    intel_source_name = "intel.cpp" # Just the filename
    barrier_source_name = "barrier_main.cpp" # Just the filename

    for threads in fixed_thread_counts:
        print(f"\n[INFO] Starting experiments for {threads} THREADS\n" + "="*50)
        for m_size in matrix_sizes_to_test:
            print(f"[INFO] --- Matrix Size: {m_size}x{m_size} ---")
            for cycle in range(1, runs_per_config + 1):
                print(f"[INFO] Cycle {cycle}/{runs_per_config}")

                # 1. Without Priority
                ab_np = ALPHA_BETA_NO_PRIORITY
                time_val = run_scalability_experiment(abs_parqr_root_dir, abs_makefile_path, intel_source_name, 
                                                      m_size, threads, 0, ab_np["alpha"], ab_np["beta"])
                print(f"  Without Priority ({ab_np['alpha']},{ab_np['beta']}), {threads} Thr, {m_size}x{m_size} => {time_val} ms")
                if time_val is not None: all_run_data.append({"Method": "Without Priority", "MatrixSize": m_size, "Threads": threads, "Time_ms": time_val})

                # 2. With Priority
                ab_wp = ALPHA_BETA_WITH_PRIORITY
                time_val = run_scalability_experiment(abs_parqr_root_dir, abs_makefile_path, intel_source_name, 
                                                      m_size, threads, 1, ab_wp["alpha"], ab_wp["beta"])
                print(f"  With Priority ({ab_wp['alpha']},{ab_wp['beta']}), {threads} Thr, {m_size}x{m_size} => {time_val} ms")
                if time_val is not None: all_run_data.append({"Method": "With Priority", "MatrixSize": m_size, "Threads": threads, "Time_ms": time_val})
                
                # 3. Barrier
                ab_b = ALPHA_BETA_BARRIER
                time_val = run_scalability_experiment(abs_parqr_root_dir, abs_makefile_path, barrier_source_name, 
                                                      m_size, threads, None, ab_b["alpha"], ab_b["beta"])
                print(f"  Barrier ({ab_b['alpha']},{ab_b['beta']}), {threads} Thr, {m_size}x{m_size} => {time_val} ms")
                if time_val is not None: all_run_data.append({"Method": "Barrier", "MatrixSize": m_size, "Threads": threads, "Time_ms": time_val})

    if not all_run_data: print("[WARN] No data collected. Exiting."); return
    
    df_all_runs = pd.DataFrame(all_run_data)
    df_averaged = df_all_runs.groupby(["Method", "MatrixSize", "Threads"], as_index=False)["Time_ms"].mean()
    df_averaged.rename(columns={"Time_ms": "AvgTime_ms"}, inplace=True)
    df_averaged["AvgTime_s"] = df_averaged["AvgTime_ms"] / 1000.0

    results_dir = "results_scalability" # Will be created in the script's directory (e.g., scripts/results_scalability)
    os.makedirs(results_dir, exist_ok=True)
    csv_filename = os.path.join(results_dir, "scalability_analysis_results.csv")
    df_averaged.to_csv(csv_filename, index=False)
    print(f"[INFO] Averaged results saved to: {os.path.abspath(csv_filename)}")

    for threads_to_plot in fixed_thread_counts:
        df_plot = df_averaged[df_averaged["Threads"] == threads_to_plot]
        if df_plot.empty:
            print(f"[WARN] No data to plot for {threads_to_plot} threads.")
            continue
            
        plt.figure(figsize=(10, 6))
        markers = {'Barrier': '^', 'Without Priority': 'o', 'With Priority': 's'}
        linestyles = {'Barrier': ':', 'Without Priority': '-', 'With Priority': '--'}

        for method_name, group_data in df_plot.groupby("Method"):
            plt.plot(group_data["MatrixSize"], group_data["AvgTime_s"], 
                     marker=markers.get(method_name, 'x'), 
                     linestyle=linestyles.get(method_name, '-'),
                     label=method_name)
        
        plt.xlabel("Matrix Size")
        plt.ylabel("Execution Time (s)")
        fig_label = 'a' if threads_to_plot == 26 else 'b'
        plt.title(f"Scalability Comparison ({threads_to_plot} Threads) - Fig 4{fig_label}")
        plt.legend()
        plt.grid(True)
        # Figure 4 in paper uses linear scale for Y-axis
        plot_filename = f"fig4{fig_label}_scalability_{threads_to_plot}threads.png"
        abs_plot_path = os.path.abspath(os.path.join(results_dir, plot_filename))
        plt.savefig(abs_plot_path, dpi=300)
        print(f"[INFO] Generated plot: {abs_plot_path}")
        plt.close()

if __name__ == "__main__":
    main()
