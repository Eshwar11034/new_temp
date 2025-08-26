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
    if not os.path.exists(filepath) or force_regenerate:
        print(f"[INFO] Matrix file {filepath} not found or regeneration forced. Generating new matrix {rows}x{cols}...")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        seed_value = rows * 100000 + cols 
        np.random.seed(seed_value)
        matrix_data = np.random.rand(rows, cols) * 20 - 10
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
# Global Parameters for Experiment 4 (Throughput Evaluation - Fig 5)
# ------------------------------------------------------------------------------
fixed_matrix_size = 8192
runs_per_config = 3

# --- Paths RELATIVE TO THIS SCRIPT'S LOCATION (e.g., ParQR/scripts/) ---
base_testcase_folder_rel = "../testcase" 
executable_name_rel = "../a.out"        
makefile_name_rel = "../Makefile"        
parqr_root_dir_rel = ".."                
# --- Absolute paths will be resolved in main() or relevant functions ---

# Thread configurations for data collection (dense)
thread_configs_to_run = [4 * i for i in range(1, 27)] # 2, 4, ..., 104
# Thread configurations for plotting Figure 5 style
thread_configs_for_fig5_plot = [4, 24, 44, 64, 84, 100]

# Alpha/Beta configurations
# For Figure 5, the paper says "optimal alpha/beta from Exp 4.2".
# If these (32,32) and (16,16) are NOT those optimal ones, you should adjust them
# or add runs for the actual optimal ones (e.g., 12,12 for no-prio, 30,30 for prio).
ALPHA_BETA_CONFIGS = {
    "intel_32_np": {"alpha": 32, "beta": 32, "prio": 0, "source_file": "intel.cpp", "label": "Intel 32,32 (no prio)", "method_label": "Without Priority (32,32)"},
    "intel_32_wp": {"alpha": 32, "beta": 32, "prio": 1, "source_file": "intel.cpp", "label": "Intel 32,32 (with prio)", "method_label": "With Priority (32,32)"},
    #"intel_16_np": {"alpha": 16, "beta": 16, "prio": 0, "source_file": "intel.cpp", "label": "Intel 16,16 (no prio)", "method_label": "Without Priority (16,16)"},
    #"intel_16_wp": {"alpha": 16, "beta": 16, "prio": 1, "source_file": "intel.cpp", "label": "Intel 16,16 (with prio)", "method_label": "With Priority (16,16)"},
    "barrier_32":  {"alpha": 32, "beta": 32, "prio": None, "source_file": "barrier_main.cpp", "label": "Barrier 32,32", "method_label": "Barrier (32,32)"},
    #"barrier_16":  {"alpha": 16, "beta": 16, "prio": None, "source_file": "barrier_main.cpp", "label": "Barrier 16,16", "method_label": "Barrier (16,16)"},
    # --- ADD OPTIMAL CONFIGS HERE IF DIFFERENT FOR FIG 5 ---
    # Example for optimal values from Exp 4.2 (Parameter Tuning)
    # "intel_optimal_np": {"alpha": 12, "beta": 12, "prio": 0, "source_file": "intel.cpp", "label": "Intel Optimal (no prio)", "method_label": "Without Priority (Optimal)"},
    # "intel_optimal_wp": {"alpha": 30, "beta": 30, "prio": 1, "source_file": "intel.cpp", "label": "Intel Optimal (with prio)", "method_label": "With Priority (Optimal)"},
    # "barrier_optimal":  {"alpha": 12, "beta": 12, "prio": None, "source_file": "barrier_main.cpp", "label": "Barrier Optimal", "method_label": "Barrier (Optimal)"},
}
# Which configurations to use for the main Figure 5 plot
# UPDATE THESE KEYS TO POINT TO THE "OPTIMAL" CONFIGURATIONS IF YOU ADD THEM ABOVE
FIG5_PLOT_KEYS = {
    "Without Priority": "intel_32_np", # Change to "intel_optimal_np" if using optimal
    "With Priority": "intel_32_wp",    # Change to "intel_optimal_wp" if using optimal
    "Barrier": "barrier_32"            # Change to "barrier_optimal" if using optimal
}

# ------------------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------------------
def update_makefile(abs_makefile_path, source_file_name_only):
    # MAIN_SRC in Makefile expects just the filename (e.g., intel.cpp) as .cpp files are in root
    cmd = f"sed -i 's|^MAIN_SRC * =.*|MAIN_SRC = {source_file_name_only}|' {abs_makefile_path}"
    subprocess.run(cmd, shell=True, check=True)
    print(f"[DEBUG] Updated Makefile ({abs_makefile_path}) to use {source_file_name_only}")

def update_cpp_macro(abs_source_file_path, macro_name, macro_value):
    regex = f"'s/^#define[[:space:]]\\+{macro_name}[[:space:]]\\+[0-9.]\\+/#define {macro_name} {macro_value}/'"
    cmd = f"sed -i {regex} {abs_source_file_path}"
    subprocess.run(cmd, shell=True, check=True)
    print(f"[DEBUG] Updated {abs_source_file_path}: {macro_name}={macro_value}")

def compile_code_cli(abs_parqr_root_dir):
    print("[DEBUG] Compiling code...")
    subprocess.run("make clean", shell=True, check=True, cwd=abs_parqr_root_dir)
    ret = subprocess.run("make -j", shell=True, cwd=abs_parqr_root_dir)
    if ret.returncode != 0: print("[ERROR] Compilation failed."); sys.exit(1)
    print("[DEBUG] Compilation succeeded.")

def get_matrix_file_path_for_exe(current_rows, current_cols, abs_parqr_root_dir, rel_testcase_folder_from_root="testcase"):
    abs_testcase_dir = os.path.join(abs_parqr_root_dir, rel_testcase_folder_from_root)
    matrix_file_abs_path = os.path.join(abs_testcase_dir, f"matrix_{current_rows}x{current_cols}.txt")
    generate_matrix_if_needed(current_rows, current_cols, matrix_file_abs_path)
    if not os.path.exists(matrix_file_abs_path): print(f"[ERROR] Matrix file {matrix_file_abs_path} still not found."); sys.exit(1)
    return os.path.join(rel_testcase_folder_from_root, f"matrix_{current_rows}x{current_cols}.txt")

def run_executable_cli(abs_parqr_root_dir, current_rows, current_cols, matrix_file_path_for_exe):
    executable_in_cwd = "./a.out" 
    cmd_list = [executable_in_cwd, matrix_file_path_for_exe]
    print(f"[DEBUG] Running command (from {abs_parqr_root_dir}): {' '.join(cmd_list)}")
    try:
        result = subprocess.run(cmd_list, capture_output=True, text=True, check=True, cwd=abs_parqr_root_dir)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Error running executable. Return code: {e.returncode}"); print(f"  Stdout: {e.stdout.strip()}"); print(f"  Stderr: {e.stderr.strip()}"); return None
    except FileNotFoundError as e:
        print(f"[ERROR] FileNotFoundError: {e}"); print(f"  Cmd: {' '.join(cmd_list)}, CWD: {abs_parqr_root_dir}"); return None
    match = re.search(r"(?:Execution Time|Time taken):\s*([0-9.]+)\s*ms", result.stdout)
    if match: return float(match.group(1))
    else: print("[ERROR] Time not found in output."); print("--- STDOUT ---"); print(result.stdout.strip()); print("--- STDERR ---"); print(result.stderr.strip()); return None

def run_throughput_experiment(abs_parqr_root_dir, abs_makefile_path, source_file_name_only, 
                              thread_count, priority_val, alpha_val, beta_val):
    # .cpp files are in the abs_parqr_root_dir
    abs_source_file_path = os.path.join(abs_parqr_root_dir, source_file_name_only)

    update_makefile(abs_makefile_path, source_file_name_only) # Pass only filename
    update_cpp_macro(abs_source_file_path, "NUM_THREADS", thread_count)
    if priority_val is not None:
        update_cpp_macro(abs_source_file_path, "USE_PRIORITY_MAIN_QUEUE", priority_val)
    update_cpp_macro(abs_source_file_path, "ALPHA", alpha_val)
    update_cpp_macro(abs_source_file_path, "BETA", beta_val)
    
    compile_code_cli(abs_parqr_root_dir)
    matrix_file_for_exe = get_matrix_file_path_for_exe(fixed_matrix_size, fixed_matrix_size, abs_parqr_root_dir)
    exec_time = run_executable_cli(abs_parqr_root_dir, fixed_matrix_size, fixed_matrix_size, matrix_file_for_exe)
    return exec_time

# ------------------------------------------------------------------------------
# Main Experiment Execution
# ------------------------------------------------------------------------------
# ... (all helper functions and global parameters from your script remain unchanged) ...
# generate_matrix_if_needed, ALPHA_BETA_CONFIGS, FIG5_PLOT_KEYS, update_makefile, etc.

# ------------------------------------------------------------------------------
# Main Experiment Execution (Reordered for Experiment 4)
# ------------------------------------------------------------------------------
def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    abs_parqr_root_dir = os.path.abspath(parqr_root_dir_rel)
    abs_executable_path = os.path.join(abs_parqr_root_dir, executable_name_rel.lstrip("../").lstrip("./"))
    abs_makefile_path = os.path.join(abs_parqr_root_dir, makefile_name_rel.lstrip("../").lstrip("./"))

    if not os.path.exists(abs_executable_path):
        print(f"[INFO] Executable not found at {abs_executable_path}. Attempting initial compile...")
        compile_code_cli(abs_parqr_root_dir)
        if not os.path.exists(abs_executable_path): 
            print(f"[ERROR] Executable still not found at {abs_executable_path}. Exiting.")
            sys.exit(1)
        else: 
            print(f"[INFO] Executable found at {abs_executable_path} after compilation.")
    else: 
        print(f"[INFO] Executable found at {abs_executable_path}.")

    all_run_data = [] # This will store data from EACH individual run (not averaged yet)

    for threads in thread_configs_to_run:
        print(f"\n[INFO] Starting experiments for {threads} THREADS\n" + "="*50)
        # Loop for each cycle (run)
        for cycle in range(1, runs_per_config + 1):
            print(f"[INFO] --- Cycle {cycle}/{runs_per_config} for {threads} THREADS ---")
            # Loop through all defined Alpha/Beta configurations for this cycle
            for config_key, params in ALPHA_BETA_CONFIGS.items():
                current_source_name = params["source_file"]
                
                print(f"[INFO] Running Config: {params['label']}, Threads: {threads}")
                time_val = run_throughput_experiment(abs_parqr_root_dir, abs_makefile_path, current_source_name, 
                                                     threads, params["prio"], params["alpha"], params["beta"])
                print(f"  => {time_val} ms")
                
                if time_val is not None:
                    all_run_data.append({
                        "MethodLabel": params["method_label"], 
                        "ConfigKey": config_key, 
                        "Threads": threads,
                        "Time_ms": time_val # Store individual time, not yet averaged
                    })
        print(f"[INFO] Completed all cycles for all configurations for Threads = {threads}")

    if not all_run_data: 
        print("[WARN] No data collected. Exiting.")
        return
    
    # --- Averaging after all individual runs are collected ---
    df_all_runs = pd.DataFrame(all_run_data)
    # Group by the unique combination of MethodLabel, ConfigKey, and Threads, then average Time_ms
    df_averaged_results = df_all_runs.groupby(["MethodLabel", "ConfigKey", "Threads"], as_index=False)["Time_ms"].mean()
    df_averaged_results.rename(columns={"Time_ms": "AvgTime_ms"}, inplace=True)
    df_averaged_results["AvgTime_s"] = df_averaged_results["AvgTime_ms"] / 1000.0

    results_dir = "results_throughput"
    os.makedirs(results_dir, exist_ok=True)
    csv_filename = os.path.join(results_dir, "throughput_analysis_results.csv")
    df_averaged_results.to_csv(csv_filename, index=False) # Save the averaged results
    print(f"[INFO] Averaged results saved to: {os.path.abspath(csv_filename)}")

    # --- Plotting (uses df_averaged_results) ---
    # Diagnostic plot (all collected data, now using averaged results)
    plt.figure(figsize=(12, 7))
    # Group by the broader method label from the averaged data
    for method_label, group_data in df_averaged_results.groupby("MethodLabel"): 
        plt.plot(group_data["Threads"], group_data["AvgTime_s"], marker='o', linestyle='-', label=method_label)
    plt.xlabel("Thread Count")
    plt.ylabel("Average Execution Time (s)")
    plt.title(f"Throughput Comparison (All Configs, Matrix: {fixed_matrix_size}x{fixed_matrix_size})")
    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    plt.grid(True, which="both", ls="-")
    plt.yscale('log')
    plt.tight_layout(rect=[0, 0, 0.80, 1]) 
    diag_plot_path = os.path.abspath(os.path.join(results_dir, "diagnostic_throughput_all_configs.png"))
    plt.savefig(diag_plot_path, dpi=300)
    plt.close()
    print(f"[INFO] Generated diagnostic plot: {diag_plot_path}")

    # Figure 5 style plot (uses df_averaged_results)
    plt.figure(figsize=(10, 6))
    markers = {'Barrier': '^', 'Without Priority': 'o', 'With Priority': 's'}
    linestyles = {'Barrier': ':', 'Without Priority': '-', 'With Priority': '--'}

    for paper_label, target_config_key in FIG5_PLOT_KEYS.items():
        if target_config_key not in ALPHA_BETA_CONFIGS:
            print(f"[WARN] Config key '{target_config_key}' for paper label '{paper_label}' not found in ALPHA_BETA_CONFIGS. Skipping.")
            continue
        
        # Filter the averaged DataFrame using ConfigKey
        subset = df_averaged_results[(df_averaged_results["ConfigKey"] == target_config_key) &
                                     (df_averaged_results["Threads"].isin(thread_configs_for_fig5_plot))]
        if not subset.empty:
            plt.plot(subset["Threads"], subset["AvgTime_s"],
                     marker=markers.get(paper_label, 'x'),
                     linestyle=linestyles.get(paper_label, '-'),
                     label=paper_label)
        else:
            print(f"[WARN] No averaged data for Fig5 plot: {paper_label} (using config key: {target_config_key})")
            
    plt.xlabel("Thread Count")
    plt.ylabel("Execution Time (s)")
    plt.title(f"Throughput Evaluation (Matrix: {fixed_matrix_size}x{fixed_matrix_size}) - Fig. 5 Style")
    plt.legend()
    plt.grid(True, which="both", ls="-")
    plt.yscale('log')
    plt.xticks(thread_configs_for_fig5_plot)
    plt.xlim(min(thread_configs_for_fig5_plot)-2, max(thread_configs_for_fig5_plot)+2)
    fig5_plot_path = os.path.abspath(os.path.join(results_dir, "fig5_generated_throughput.png"))
    plt.savefig(fig5_plot_path, dpi=300)
    print(f"[INFO] Generated Fig. 5 style plot: {fig5_plot_path}")
    plt.close()

if __name__ == "__main__":
    main()
