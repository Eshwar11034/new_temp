# Dockerfile - For x86_64 (amd64) build using Intel oneAPI TBB
# File: Dockerfile
# Location: europar2025_pdcrl_artifact/Dockerfile
# -------------------------------------------------------------
    FROM ubuntu:22.04
    ARG DEBIAN_FRONTEND=noninteractive
    
    # 1. Install System Prerequisites & Build Tools
    # Includes tools for adding Intel's APT repository (wget, gpg)
    # build-essential provides gcc, g++, make etc.
    RUN apt-get update && \
        apt-get install -y --no-install-recommends \
            build-essential \
            g++ \
            cmake \
            git \
            wget \
            curl \
            gpg \
            gpg-agent \
            python3 \
            python3-pip \
        && rm -rf /var/lib/apt/lists/*
    
    # 2. Install Python Packages
    # Includes pandas, numpy, matplotlib for data processing and plotting,
    # and seaborn for heatmap generation.
    RUN python3 -m pip install --no-cache-dir --upgrade pip && \
        python3 -m pip install --no-cache-dir \
            pandas \
            numpy \
            matplotlib \
            seaborn \
        && rm -rf /root/.cache/pip
    
    # 2a. Create 'python' alias for 'python3' for convenience
    RUN ln -s /usr/bin/python3 /usr/local/bin/python
    
    # 3. Install Intel oneAPI Threading Building Blocks (TBB)
    # This section adds Intel's official APT repository and installs the TBB development package.
    RUN apt-get update && \
        # Add Intel's GPG key
        wget -O- https://apt.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS.PUB \
            | gpg --dearmor | tee /usr/share/keyrings/oneapi-archive-keyring.gpg > /dev/null && \
        # Add Intel's oneAPI repository
        echo "deb [signed-by=/usr/share/keyrings/oneapi-archive-keyring.gpg] https://apt.repos.intel.com/oneapi all main" \
            | tee /etc/apt/sources.list.d/oneAPI.list && \
        # Update package list again to include Intel's repo
        apt-get update && \
        # Install the TBB development package (includes headers and libraries)
        apt-get install -y --no-install-recommends intel-oneapi-tbb-devel && \
        # Clean up APT cache and lists
        rm -rf /var/lib/apt/lists/*
    
    # 4. Set up Environment Variables for Intel oneAPI TBB
    # These help compilers and linkers find TBB.
    # TBB_ROOT points to the 'latest' version installed by oneAPI.
    ENV ONEAPI_ROOT=/opt/intel/oneapi
    ENV TBB_ROOT=${ONEAPI_ROOT}/tbb/latest
    ENV CPATH=${TBB_ROOT}/include:${CPATH}
    
    # Determine the actual library path for TBB.
    # The 'intel-oneapi-tbb-devel' package should place libraries in a path discoverable
    # by the linker after ldconfig, or your Makefile should use TBB_ROOT.
    # For robustness, we'll add the common library location to LD_LIBRARY_PATH and LIBRARY_PATH.
    # Based on your previous 'ls' output, libtbb.so is in ${TBB_ROOT}/lib.
    # If it were in a deeper arch-specific path like 'lib/intel64/gccX.Y', that would be used.
    ENV TBB_LIB_DIR=${TBB_ROOT}/lib
    ENV LIBRARY_PATH=${TBB_LIB_DIR}:${LIBRARY_PATH}
    ENV LD_LIBRARY_PATH=${TBB_LIB_DIR}:${LD_LIBRARY_PATH}
    
    # Update the dynamic linker cache to recognize the new TBB libraries.
    # The intel-oneapi-tbb-devel package might do this, but being explicit is safer.
    RUN echo "${TBB_LIB_DIR}" > /etc/ld.so.conf.d/oneapi-tbb.conf && \
        ldconfig
    
    # 5. Sanity Checks (Executed during Docker build)
    RUN echo "--- Sanity Checks ---" && \
        echo "Host Architecture (reported by container's kernel via uname): $(uname -m)" && \
        echo "Target Package Architecture (reported by dpkg): $(dpkg --print-architecture)" && \
        echo "---" && \
        echo "GCC Version:" && (gcc --version | head -n1 || echo "GCC not found") && \
        echo "G++ Version:" && (g++ --version | head -n1 || echo "G++ not found") && \
        echo "---" && \
        echo "Python Alias Version:" && (python --version || echo "Python alias not found") && \
        echo "Python3 Version:" && (python3 --version || echo "Python3 not found") && \
        echo "Python Deps Check:" && (python -c "import pandas, numpy, matplotlib, seaborn; print('✓ Python scientific stack (pandas, numpy, matplotlib, seaborn) OK')" || echo "✗ Python scientific stack import FAILED") && \
        echo "---" && \
        echo "TBB_ROOT (from ENV): ${TBB_ROOT}" && \
        echo "TBB_LIB_DIR (from ENV): ${TBB_LIB_DIR}" && \
        echo "CPATH (effective): $CPATH" && \
        echo "LIBRARY_PATH (effective): $LIBRARY_PATH" && \
        echo "LD_LIBRARY_PATH (effective): $LD_LIBRARY_PATH" && \
        echo "Checking TBB header (tbb.h):" && (ls -l ${TBB_ROOT}/include/tbb/tbb.h || echo "✗ TBB header tbb.h not found at expected path") && \
        echo "Checking TBB library (libtbb.so):" && (ls -l ${TBB_LIB_DIR}/libtbb.so || echo "✗ libtbb.so not found in ${TBB_LIB_DIR}") && \
        echo "Checking ldconfig for libtbb:" && (ldconfig -p | grep libtbb || echo "libtbb not found by ldconfig -p (might be okay if LD_LIBRARY_PATH is set and used)") && \
        echo "---" && \
        echo "Attempting to compile and run a small TBB test program..." && \
        echo -e '#include <iostream>\n#include <vector>\n#include <numeric>\n#include <tbb/parallel_for.h>\n#include <tbb/blocked_range.h>\n#include <tbb/spin_mutex.h>\ntbb::spin_mutex my_mutex;\nint main() { std::vector<int> data(100); std::iota(data.begin(), data.end(), 0); tbb::parallel_for(tbb::blocked_range<size_t>(0,data.size()), [&](const tbb::blocked_range<size_t>& r){ for(size_t i=r.begin(); i!=r.end(); ++i) { tbb::spin_mutex::scoped_lock lock(my_mutex); data[i]++; } }); int sum = 0; for(int x : data) sum+=x; if (sum == 5050) {std::cout << "TBB test sum correct." << std::endl; std::cout << "✓ TBB Compilation & Runtime Test OK" << std::endl; return 0;} else {std::cout << "TBB test sum incorrect: " << sum << std::endl; return 1;} }' > /tmp/test_tbb.cpp && \
        (g++ /tmp/test_tbb.cpp -o /tmp/test_tbb_exec -std=c++17 -ltbb -pthread && /tmp/test_tbb_exec || (echo "✗ TBB Compilation or Runtime Test FAILED. Check CPATH, LIBRARY_PATH, LD_LIBRARY_PATH and linker flags (-ltbb)." && exit 1)) && \
        rm -f /tmp/test_tbb.cpp /tmp/test_tbb_exec && \
        echo "--- End Sanity Checks ---"
    
    # Set the default working directory for the container
    WORKDIR /workspace
    
    # Default command if the container is run without arguments
    CMD ["/bin/bash"]