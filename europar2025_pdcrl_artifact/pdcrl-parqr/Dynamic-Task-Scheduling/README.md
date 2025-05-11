# Dynamic Task Scheduling for Triangular Linear Algebra Systems

## Overview
This project implements dynamic task scheduling for triangular linear algebra systems. The code is written in C++ and uses a Makefile for building and managing the project.

## Prerequisites
- g++ (GCC) compiler
- Make

## Directory Structure
- `src/`: Contains the source files.
- `include/`: Contains the header files.
- `build/`: Directory where object files will be placed.
- `test/`: Contains test source files.
- `main.cpp`: The main source file.

## Building the Project

### Compile the Code
To compile the code, run the following command:
```sh
make
```

This will create the target executable a.out in the project root directory.

### Compile the Debug Version
To compile the debug version of the code, run:

```sh
make debug
```

This will create the debug executable debug.out in the project root directory.

### Clean the Build
To clean the build files, run:

```sh
make clean
```

This will remove all object files and executables.

### Running the Program
To run the compiled program, use:

```sh
./a.out
```

### Debugging the Program
To debug the program using gdb, first compile the debug version as shown above, then run:

```sh
gdb ./debug.out
```

### Running Tests
To compile and run the tests, use:

```sh
make test
```

This will create the test executable test.out and run the tests.

### Additional Targets
```sh
make run
```
Runs the compiled program.

```sh
make create_build_dir
```
Creates the build directory if it doesn't exist.
