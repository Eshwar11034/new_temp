#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Experiment 1b (Fig. 3) on main.cpp:
- Sweeps α,β for each (matrix_size, threads, mode) on main.cpp
- Runs each config RUNS_PER_CONFIG times (interleaved across sizes to avoid cache bias)
- Parses "Execution Time ... ms" (or "Time taken ... ms")
- Writes results incrementally to CSV (preserves progress)
- Maintains a 'best per (size,threads,mode)' CSV as it goes
- Optionally generates matrices if missing (skips too-large by default)

USAGE (examples)
---------------
python3 scripts/run_fig3_main.py \
  --repo-root ../Dynamic-Task-Scheduling \
  --matrix-sizes 300,2400,4800,7200,10800 \
  --threads 26 \
  --alphas 2:33:2 \
  --betas  2:33:2

python3 scripts/run_fig3_main.py \
  --repo-root ../Dynamic-Task-Scheduling \
  --matrix-sizes 5400,7200,9000 \
  --threads 26,52 \
  --modes 0,1 \
  --runs 3
"""

import os
import re
import sys
import csv
import time
import math
import shutil
import random
import argparse
import pathlib
import subprocess
from collections import defaultdict, deque
import platform
import tempfile
import glob

# ---------------------
# Default configuration
# ---------------------
DEFAULT_REPO_ROOT = ".."     # where the Makefile & src/main.cpp live
DEFAULT_MAIN_CPP  = "main.cpp"
DEFAULT_MAKEFILE  = "Makefile"
DEFAULT_EXEC      = "./a.out"                        # adjust if your binary is different
DEFAULT_TESTCASE  = "testcase"                       # folder for matrix_ NxN .txt

# Parameter ranges
DEFAULT_MATRIX_SIZES = [512, 1024, 2048, 4096, 8192]
DEFAULT_THREADS_LIST = [26]
DEFAULT_MODES        = [0, 1]  # 0 = without priority, 1 = with priority
DEFAULT_ALPHA_RANGE  = list(range(2, 33, 2))
DEFAULT_BETA_RANGE   = list(range(2, 33, 2))
RUNS_PER_CONFIG      = 3

# File outputs
RESULTS_DIR          = "results"
CSV_ALL_RUNS         = "fig3_all_runs.csv"
CSV_AGG_BY_CONFIG    = "fig3_agg_by_config.csv"
CSV_BEST_BY_STM      = "fig3_best_by_size_threads.csv"  # per (size,threads,mode)

# Time parsing
TIME_REGEX = re.compile(r"(?:Execution\s*Time|Time\s*taken)\D*([0-9]+(?:\.[0-9]+)?)\s*ms", re.I)

# Matrix generation
MAX_GENERATE_SIZE    = 100000000     # avoid generating huge files accidentally; override with --allow-large
ALLOW_GENERATE_LARGE = False
#----
# intel heplers
#----
def _run(cmd, cwd=None, check=True, env=None, capture=False):
    import subprocess
    res = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=capture)
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")
    return res

def _sudo_prefix():
    for candidate in ([], ["sudo","-n"], ["sudo"]):
        try:
            _run(candidate + ["bash","-lc","true"], check=True)
            return candidate
        except Exception:
            continue
    return []

# >>> ADD
def _tbb_compile_test(cxx=None, extra_cflags=None, extra_ldflags=None):
    cxx = cxx or shutil.which("c++") or shutil.which("g++") or "c++"
    code = r"""
#include <tbb/tbb.h>
#include <cstdio>
int main(){ tbb::parallel_for(0, 1000, [](int){}); std::puts("tbb-ok"); return 0; }
"""
    with tempfile.TemporaryDirectory() as td:
        src  = os.path.join(td, "t.cpp")
        binp = os.path.join(td, "a.out")
        with open(src, "w") as f: f.write(code)
        cflags = (extra_cflags or [])
        ldflags= (extra_ldflags or ["-ltbb"])
        try:
            _run([cxx, "-std=gnu++17", src, "-O2", "-o", binp] + cflags + ldflags, capture=True)
            out = _run([binp], capture=True)
            return "tbb-ok" in (out.stdout or "")
        except Exception:
            return False

def _ensure_tbb_linux():
    if _tbb_compile_test():  # already fine
        return
    sudo = _sudo_prefix()
    # Try distro packages first
    try:
        if shutil.which("apt-get"):
            _run(sudo + ["apt-get","update"], capture=True)
            _run(sudo + ["apt-get","install","-y","libtbb-dev"], capture=True)
        elif shutil.which("dnf"):
            _run(sudo + ["dnf","install","-y","tbb-devel"], capture=True)
        elif shutil.which("yum"):
            _run(sudo + ["yum","install","-y","tbb-devel"], capture=True)
        elif shutil.which("zypper"):
            _run(sudo + ["zypper","install","-y","tbb-devel"], capture=True)
        elif shutil.which("pacman"):
            _run(sudo + ["pacman","-Sy","--noconfirm","tbb"], capture=True)
    except Exception as e:
        print(f"[WARN] Distro TBB install attempt: {e}")
    if _tbb_compile_test():
        return
    # Fallback: Intel oneAPI TBB on Debian/Ubuntu
    if shutil.which("apt-get"):
        try:
            _run(sudo + ["bash","-lc",
                "set -e; "
                "install -m 0755 -d /usr/share/keyrings; "
                "wget -qO- https://apt.repos.intel.com/intel-gpg-keys/Intel-GPG-KEY-scs | "
                "gpg --dearmor | tee /usr/share/keyrings/oneapi-archive-keyring.gpg >/dev/null; "
                "echo 'deb [signed-by=/usr/share/keyrings/oneapi-archive-keyring.gpg] https://apt.repos.intel.com/oneapi all main' | "
                "tee /etc/apt/sources.list.d/oneAPI.list >/dev/null; "
                "apt-get update; apt-get install -y intel-oneapi-tbb-devel"
            ], capture=True)
            # Export lib/include so our child processes see it
            candidates = glob.glob("/opt/intel/oneapi/tbb/*/lib/intel64*/**/libtbb.so*", recursive=True)
            if candidates:
                libdir = os.path.dirname(candidates[0])
                os.environ["LD_LIBRARY_PATH"] = libdir + ":" + os.environ.get("LD_LIBRARY_PATH","")
                inc = "/opt/intel/oneapi/tbb/latest/include"
                if os.path.isdir(inc):
                    os.environ["CPLUS_INCLUDE_PATH"] = inc + ":" + os.environ.get("CPLUS_INCLUDE_PATH","")
        except Exception as e:
            print(f"[WARN] Intel oneAPI install path failed: {e}")
    # Final probe with any env we set
    _tbb_compile_test()

def _ensure_tbb_macos():
    # Prefer Homebrew install
    if _tbb_compile_test():
        return
    brew = shutil.which("brew")
    if not brew:
        print("[WARN] Homebrew not found; cannot auto-install TBB on macOS.")
        return
    try:
        _run([brew, "install", "tbb"], capture=True)
        # Use brew prefix for include/lib
        pref = _run([brew, "--prefix", "tbb"], capture=True).stdout.strip()
        inc  = os.path.join(pref, "include")
        lib  = os.path.join(pref, "lib")
        if os.path.isdir(inc):
            os.environ["CPLUS_INCLUDE_PATH"] = inc + ":" + os.environ.get("CPLUS_INCLUDE_PATH","")
        if os.path.isdir(lib):
            os.environ["DYLD_LIBRARY_PATH"] = lib + ":" + os.environ.get("DYLD_LIBRARY_PATH","")
        # Re-probe with flags
        _tbb_compile_test(extra_cflags=[f"-I{inc}"] if os.path.isdir(inc) else None,
                          extra_ldflags=[f"-L{lib}","-ltbb"] if os.path.isdir(lib) else None)
    except Exception as e:
        print(f"[WARN] brew install tbb failed: {e}")

def ensure_tbb_unix():
    sysname = platform.system().lower()
    if sysname == "linux":
        _ensure_tbb_linux()
    elif sysname == "darwin":
        _ensure_tbb_macos()
    else:
        # Non-Unix platforms: do nothing
        pass


# ------------
# Util helpers
# ------------
def info(msg):  print(f"[INFO] {msg}", flush=True)
def warn(msg):  print(f"[WARN] {msg}", flush=True)
def error(msg): print(f"[ERROR] {msg}", flush=True)

def rel(p, base):
    return os.path.normpath(os.path.join(base, p))

def read_text(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def write_text(path, s):
    with open(path, "w", encoding="utf-8") as f:
        f.write(s)

def define_replace_or_add(file_path, macro, value):
    """
    Replace '#define MACRO <...>' with '#define MACRO value'.
    If not present, insert near the top (after the #include block if found).
    """
    txt = read_text(file_path)
    pat = re.compile(rf"(?m)^(#define\s+{re.escape(macro)}\s+)[^\r\n]+")
    if pat.search(txt):
        # IMPORTANT: use lambda or \g<1> to avoid \112 ambiguity
        txt = pat.sub(lambda m: f"{m.group(1)}{value}", txt)
    else:
        lines = txt.splitlines()
        insert_at = 0
        for i, line in enumerate(lines[:100]):
            if line.strip().startswith("#include"):
                insert_at = i + 1
        lines.insert(insert_at, f"#define {macro} {value}")
        txt = "\n".join(lines)
    write_text(file_path, txt)
    info(f"{os.path.basename(file_path)}: {macro}={value}")


def compile_repo(repo_root):
    # Clean and build
    makefile_dir = repo_root
    p1 = subprocess.run(["make", "clean"], cwd=makefile_dir, capture_output=True, text=True)
    p2 = subprocess.run(["make", "-j"], cwd=makefile_dir, capture_output=True, text=True)
    if p2.returncode != 0:
        error("Compilation failed.")
        print(p2.stdout)
        print(p2.stderr)
        sys.exit(1)
    info("Compilation OK.")

def run_binary(exec_path, cwd, matrix_rel_path, timeout_sec=None):
    cmd = [exec_path, matrix_rel_path]
    info(f"Run: {' '.join(cmd)} (cwd={cwd})")
    _log_runtime_libs(exec_path)
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout_sec, check=False)
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    m = TIME_REGEX.search(out)
    if not m:
        warn("Time not parsed. Last 40 lines of output:")
        tail = "\n".join(out.strip().splitlines()[-40:])
        print(tail)
        return None
    return float(m.group(1))

def ensure_dir(d):
    os.makedirs(d, exist_ok=True)

def open_csv_writer(path, header):
    newfile = not os.path.exists(path)
    f = open(path, "a", newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=header)
    if newfile:
        w.writeheader()
        f.flush()
        os.fsync(f.fileno())
    return f, w

def parse_list_ints(s):
    return [int(x.strip()) for x in s.split(",") if x.strip()]

def parse_range_or_list(s):
    s = s.strip()
    if ":" in s:
        parts = [int(p) for p in s.split(":")]
        if len(parts) == 3:
            a, b, step = parts
            return list(range(a, b, step))
        elif len(parts) == 2:
            a, b = parts
            return list(range(a, b))
    return parse_list_ints(s)

# -----------------------
# Matrix generation / IO
# -----------------------
def matrix_path(testcase_dir, n):
    return os.path.join(testcase_dir, f"matrix_{n}x{n}.txt")

def generate_matrix_if_needed(testcase_dir, n, allow_large=False):
    path = matrix_path(testcase_dir, n)
    if os.path.exists(path):
        return path
    if not allow_large and n > MAX_GENERATE_SIZE:
        warn(f"Matrix {n}x{n} missing and too large to auto-generate "
             f"(>{MAX_GENERATE_SIZE}). Please create it at: {path}")
        return path  # will fail later if truly needed
    ensure_dir(testcase_dir)
    info(f"Generating deterministic matrix {n}x{n} at {path} ...")
    rnd = random.Random(n * 100000 + n)
    # Simple i.i.d. uniform [-0.5, 0.5] to keep numbers small; text format
    with open(path, "w", encoding="utf-8") as f:
        for i in range(n):
            row = [f"{rnd.random() - 0.5:.6f}" for _ in range(n)]
            f.write(" ".join(row) + "\n")
    return path

# ------------------------
# Scheduling / aggregation
# ------------------------
def build_config_list(matrix_sizes, threads_list, modes, a_vals, b_vals):
    """
    Returns a list of (matrix_size, threads, mode, alpha, beta) that satisfy:
      beta>=alpha, beta%alpha==0, size%alpha==0, size%beta==0
    """
    cfgs_by_size = defaultdict(list)
    for n in matrix_sizes:
        for t in threads_list:
            for mode in modes:
                for a in a_vals:
                    for b in b_vals:
                        if not (b >= a and (b % a == 0) and (n % a == 0) and (n % b == 0)):
                            continue
                        cfgs_by_size[n].append((n, t, mode, a, b))
    return cfgs_by_size

def round_robin_runs(cfgs_by_size, runs_per_config):
    """
    Build an execution order that interleaves sizes:
    For r in 0..runs-1:
      For each size S in round-robin:
        For each config belonging to S:
          yield (S-config, run_idx=r)
    This spaces out repeated runs of the same dataset.
    """
    order = []
    sizes = sorted(cfgs_by_size.keys())
    for r in range(runs_per_config):
        for n in sizes:
            for cfg in cfgs_by_size[n]:
                order.append((cfg, r))
    return order

# >>> ADD
def _log_runtime_libs(exec_path):
    sysname = platform.system().lower()
    if sysname == "linux":
        info(f"LD_LIBRARY_PATH={os.environ.get('LD_LIBRARY_PATH','')}")
        if shutil.which("ldd") and os.path.exists(exec_path):
            try:
                out = _run(["ldd", exec_path], capture=True)
                lines = [ln for ln in (out.stdout or "").splitlines() if "tbb" in ln.lower()]
                if lines:
                    info("ldd (TBB):\n" + "\n".join(lines))
            except Exception as e:
                warn(f"ldd failed: {e}")
    elif sysname == "darwin":
        info(f"DYLD_LIBRARY_PATH={os.environ.get('DYLD_LIBRARY_PATH','')}")
        if shutil.which("otool") and os.path.exists(exec_path):
            try:
                out = _run(["otool","-L", exec_path], capture=True)
                lines = [ln for ln in (out.stdout or "").splitlines() if "tbb" in ln.lower()]
                if lines:
                    info("otool -L (TBB):\n" + "\n".join(lines))
            except Exception as e:
                warn(f"otool -L failed: {e}")


# ------------------------
# Main experiment procedure
# ------------------------
def main():
    ap = argparse.ArgumentParser(description="Run Experiment 1b (Fig.3) on main.cpp")
    ap.add_argument("--repo-root", type=str, default=DEFAULT_REPO_ROOT)
    ap.add_argument("--main-cpp",  type=str, default=DEFAULT_MAIN_CPP)
    ap.add_argument("--makefile",  type=str, default=DEFAULT_MAKEFILE)
    ap.add_argument("--exec",      type=str, default=DEFAULT_EXEC)
    ap.add_argument("--testcase",  type=str, default=DEFAULT_TESTCASE)
    ap.add_argument("--matrix-sizes", type=str, default=",".join(map(str, DEFAULT_MATRIX_SIZES)))
    ap.add_argument("--threads",      type=str, default=",".join(map(str, DEFAULT_THREADS_LIST)))
    ap.add_argument("--modes",        type=str, default=",".join(map(str, DEFAULT_MODES)))
    ap.add_argument("--alphas",       type=str, default="2:33:2")
    ap.add_argument("--betas",        type=str, default="2:33:2")
    ap.add_argument("--runs",         type=int, default=RUNS_PER_CONFIG)
    ap.add_argument("--allow-large",  action="store_true", help="Allow auto-generation of very large matrices")
    args = ap.parse_args()

    repo_root   = os.path.abspath(args.repo_root)
    main_cpp    = rel(args.main_cpp, repo_root)
    makefile    = rel(args.makefile, repo_root)
    exec_path   = rel(args.exec, repo_root)
    testcase    = rel(args.testcase, repo_root)

    assert os.path.exists(repo_root), f"Repo root not found: {repo_root}"
    assert os.path.exists(main_cpp),  f"main.cpp not found: {main_cpp}"
    assert os.path.exists(makefile),  f"Makefile not found: {makefile}"

    sizes   = parse_list_ints(args.matrix_sizes)
    thrs    = parse_list_ints(args.threads)
    modes   = parse_list_ints(args.modes)
    a_vals  = parse_range_or_list(args.alphas)
    b_vals  = parse_range_or_list(args.betas)
    runs    = int(args.runs)

    global ALLOW_GENERATE_LARGE
    ALLOW_GENERATE_LARGE = bool(args.allow_large)

    info(f"Repo: {repo_root}")
    info(f"main.cpp: {main_cpp}")
    info(f"Exec: {exec_path}")
    info(f"Testcase dir: {testcase}")
    info(f"Matrix sizes: {sizes}")
    info(f"Threads: {thrs}")
    info(f"Modes: {modes}")
    info(f"Alphas: {a_vals}")
    info(f"Betas: {b_vals}")
    info(f"Runs/config: {runs}")
    ensure_tbb_unix()

    # Prepare results files (append mode, immediate flush)
    ensure_dir(rel(RESULTS_DIR, repo_root))
    path_all  = rel(os.path.join(RESULTS_DIR, CSV_ALL_RUNS), repo_root)
    path_agg  = rel(os.path.join(RESULTS_DIR, CSV_AGG_BY_CONFIG), repo_root)
    path_best = rel(os.path.join(RESULTS_DIR, CSV_BEST_BY_STM),  repo_root)

    f_all,  w_all  = open_csv_writer(path_all,  ["matrix_size","threads","mode","alpha","beta","run_idx","time_ms"])
    f_agg,  w_agg  = open_csv_writer(path_agg,  ["matrix_size","threads","mode","alpha","beta","runs","avg_time_ms","std_time_ms","min_time_ms","max_time_ms"])
    f_best, w_best = open_csv_writer(path_best, ["matrix_size","threads","mode","best_alpha","best_beta","runs","avg_time_ms","std_time_ms"])

    # Keep a local copy of main.cpp to restore later
    backup_cpp = main_cpp + ".bak_fig3"
    shutil.copy2(main_cpp, backup_cpp)
    info(f"Backed up {main_cpp} -> {backup_cpp}")

    # Ensure matrices exist (or create when not too large)
    for n in sizes:
        generate_matrix_if_needed(testcase, n, allow_large=ALLOW_GENERATE_LARGE)

    # Build config schedule and interleave runs by size
    cfgs_by_size = build_config_list(sizes, thrs, modes, a_vals, b_vals)
    total_cfgs = sum(len(v) for v in cfgs_by_size.values())
    if total_cfgs == 0:
        error("No valid (alpha,beta) pairs for given sizes/threads. Check divisibility constraints.")
        sys.exit(2)

    schedule = round_robin_runs(cfgs_by_size, runs)
    info(f"Planned runs: {len(schedule)} across {total_cfgs} configs")

    # In-memory aggregation & best tracking
    accum = defaultdict(list)       # (n,t,mode,a,b) -> [times]
    best  = {}                      # (n,t,mode) -> dict

    try:
        last_compiled_signature = None

        for idx, ((n, t, mode, a, b), r_idx) in enumerate(schedule, 1):
            info(f"[{idx}/{len(schedule)}] size={n} thr={t} mode={'with_priority' if mode==1 else 'without_priority'} a={a} b={b} run={r_idx+1}/{runs}")

            # Update macros only when they change to avoid wasteful rebuilds
            signature = (t, mode, a, b)
            if signature != last_compiled_signature:
                define_replace_or_add(main_cpp, "NUM_THREADS", str(t))
                define_replace_or_add(main_cpp, "ALPHA",       str(a))
                define_replace_or_add(main_cpp, "BETA",        str(b))
                define_replace_or_add(main_cpp, "USE_PRIORITY_MAIN_QUEUE", str(mode))
                compile_repo(repo_root)
                last_compiled_signature = signature

            # Run executable with matrix path relative to exec CWD
            exec_cwd = repo_root
            matrix_rel = os.path.join(os.path.basename(testcase), os.path.basename(matrix_path(testcase, n)))
            t_ms = run_binary(exec_path, exec_cwd, matrix_rel, timeout_sec=None)

            if t_ms is None:
                # still record a NaN to keep trace of failures
                w_all.writerow({"matrix_size": n,"threads": t,"mode": mode,"alpha": a,"beta": b,"run_idx": r_idx,"time_ms": float("nan")})
                f_all.flush(); os.fsync(f_all.fileno())
                continue

            # Write per-run immediately
            w_all.writerow({"matrix_size": n,"threads": t,"mode": mode,"alpha": a,"beta": b,"run_idx": r_idx,"time_ms": t_ms})
            f_all.flush(); os.fsync(f_all.fileno())

            key = (n, t, mode, a, b)
            vals = accum[key]
            vals.append(t_ms)

            # If this config completed all its runs, write aggregate & maybe update best
            if len(vals) == runs:
                avg = sum(vals)/len(vals)
                var = sum((x-avg)**2 for x in vals) / (len(vals)-1) if len(vals) > 1 else 0.0
                std = math.sqrt(var)
                row_agg = {
                    "matrix_size": n, "threads": t, "mode": mode,
                    "alpha": a, "beta": b, "runs": len(vals),
                    "avg_time_ms": round(avg, 4),
                    "std_time_ms": round(std, 4),
                    "min_time_ms": round(min(vals), 4),
                    "max_time_ms": round(max(vals), 4),
                }
                w_agg.writerow(row_agg)
                f_agg.flush(); os.fsync(f_agg.fileno())
                info(f"Aggregated: {row_agg}")

                # Update best per (size,threads,mode)
                kbest = (n, t, mode)
                cur = best.get(kbest)
                if (cur is None) or (avg < cur["avg_time_ms"]):
                    best[kbest] = {
                        "matrix_size": n, "threads": t, "mode": mode,
                        "best_alpha": a, "best_beta": b,
                        "runs": len(vals),
                        "avg_time_ms": round(avg, 4),
                        "std_time_ms": round(std, 4),
                    }
                    # Re-write full best CSV (small) to preserve progress
                    # Reopen in write mode to refresh header + all rows
                    f_best.close()
                    with open(path_best, "w", newline="", encoding="utf-8") as fb:
                        wb = csv.DictWriter(fb, fieldnames=["matrix_size","threads","mode","best_alpha","best_beta","runs","avg_time_ms","std_time_ms"])
                        wb.writeheader()
                        for _, rec in sorted(best.items()):
                            wb.writerow(rec)
                        fb.flush(); os.fsync(fb.fileno())
                    # Reopen append handle for further updates
                    f_best, w_best = open_csv_writer(path_best, ["matrix_size","threads","mode","best_alpha","best_beta","runs","avg_time_ms","std_time_ms"])
                    info(f"[BEST] Updated: {(n,t,mode)} -> α={a}, β={b}, avg={avg:.3f} ms")

    finally:
        # Restore original main.cpp
        try:
            shutil.move(backup_cpp, main_cpp)
            info(f"Restored {main_cpp} from backup.")
        except Exception as e:
            warn(f"Could not restore {main_cpp} automatically: {e}. Backup at: {backup_cpp}")

        # Close CSVs
        try: f_all.close()
        except: pass
        try: f_agg.close()
        except: pass
        try: f_best.close()
        except: pass

    info("Done. CSVs written under: " + rel(RESULTS_DIR, repo_root))
    info(f"- {os.path.relpath(path_all, repo_root)}")
    info(f"- {os.path.relpath(path_agg, repo_root)}")
    info(f"- {os.path.relpath(path_best, repo_root)}")


if __name__ == "__main__":
    main()
