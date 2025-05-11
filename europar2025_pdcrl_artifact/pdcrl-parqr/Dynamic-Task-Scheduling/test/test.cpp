#include <iostream>
#include <string>
#include <iomanip>
#include <fstream>
#include <sstream>    // Added for std::stringstream
#include <cstdlib>    // Added for std::remove
#include "bn2.h"     

#include <thread>

// Define color codes
#define RED "\033[31m"
#define GREEN "\033[32m"
#define YELLOW "\033[33m"
#define RESET "\033[0m"

// Global counter for total failures
int total_failures = 0;

// Redefine the CHECK macro to accept a stream parameter
#define CHECK(condition, message, stream) \
    if (!(condition)) { \
        (stream) << RED << "Failure: " << message << RESET << std::endl; \
        ++total_failures; \
    }


// ========================= Matrix_t Tests =========================

// Test Function 1: Operator Access
void test_operator_access() {
    // Initialize a local stringstream to collect error messages
    std::stringstream errors;

    // Initialize a 3x3 matrix and set values
    matrix_t<int> mat(3, 3);
    mat(0, 0) = 1;
    mat(0, 1) = 2;
    mat(0, 2) = 3;
    mat(1, 0) = 4;
    mat(1, 1) = 5;
    mat(1, 2) = 6;
    mat(2, 0) = 7;
    mat(2, 1) = 8;
    mat(2, 2) = 9;

    // Perform checks using the CHECK macro, passing the errors stream
    CHECK(mat(0, 0) == 1, "mat(0, 0) should be 1", errors);
    CHECK(mat(1, 1) == 5, "mat(1, 1) should be 5", errors);
    CHECK(mat(2, 2) == 9, "mat(2, 2) should be 9", errors);

    const matrix_t<int>& constMat = mat;
    CHECK(constMat(0, 0) == 1, "constMat(0, 0) should be 1", errors);
    CHECK(constMat(1, 1) == 5, "constMat(1, 1) should be 5", errors);
    CHECK(constMat(2, 2) == 9, "constMat(2, 2) should be 9", errors);

    // Determine if the test passed or failed
    if (errors.str().empty()) {
        std::cout << std::left << std::setw(60) << "[MT1]. Test Operator Access."
                  << GREEN << "[Passed]" << RESET << std::endl;
    } else {
        std::cout << std::left << std::setw(60) << "[MT1]. Test Operator Access."
                  << RED << "[Failed]" << RESET << std::endl;
        // Print the collected error messages
        std::cout << errors.str() << std::endl;
    }
}

// Test Function 2: Getter/Setter Methods
void test_get_set() {
    // Initialize a local stringstream to collect error messages
    std::stringstream errors;

    // Initialize a 3x3 matrix and set values using set()
    matrix_t<int> mat(3, 3);
    mat.set(0, 0, 1);
    mat.set(0, 1, 2);
    mat.set(0, 2, 3);
    mat.set(1, 0, 4);
    mat.set(1, 1, 5);
    mat.set(1, 2, 6);
    mat.set(2, 0, 7);
    mat.set(2, 1, 8);
    mat.set(2, 2, 9);

    // Perform checks using the CHECK macro, passing the errors stream
    CHECK(mat.get(0, 0) == 1, "mat.get(0, 0) should be 1", errors);
    CHECK(mat.get(1, 1) == 5, "mat.get(1, 1) should be 5", errors);
    CHECK(mat.get(2, 2) == 9, "mat.get(2, 2) should be 9", errors);

    // Determine if the test passed or failed
    if (errors.str().empty()) {
        std::cout << std::left << std::setw(60) << "[MT2]. Test Getter/Setter Methods."
                  << GREEN << "[Passed]" << RESET << std::endl;
    } else {
        std::cout << std::left << std::setw(60) << "[MT2]. Test Getter/Setter Methods."
                  << RED << "[Failed]" << RESET << std::endl;
        // Print the collected error messages
        std::cout << errors.str() << std::endl;
    }
}

// Test Function 3: Matrix Save Method
void test_save() {
    // Initialize a local stringstream to collect error messages
    std::stringstream errors;

    // Create a 3x3 matrix and set values
    matrix_t<int> mat(3, 3);
    mat.set(0, 0, 1);
    mat.set(0, 1, 2);
    mat.set(0, 2, 3);
    mat.set(1, 0, 4);
    mat.set(1, 1, 5);
    mat.set(1, 2, 6);
    mat.set(2, 0, 7);
    mat.set(2, 1, 8);
    mat.set(2, 2, 9);

    // Save the matrix to a file
    std::string filename = "test_matrix.txt";
    mat.save(filename);

    // Read the file and verify its contents
    std::ifstream infile(filename);
    if (!infile.is_open()) {
        errors << RED << "Failure: Unable to open file " << filename << RESET << std::endl;
        ++total_failures;
    } else {
        int value;
        // Perform checks using the CHECK macro, passing the errors stream
        CHECK(infile >> value && value == 1, "First value should be 1", errors);
        CHECK(infile >> value && value == 2, "Second value should be 2", errors);
        CHECK(infile >> value && value == 3, "Third value should be 3", errors);
        CHECK(infile >> value && value == 4, "Fourth value should be 4", errors);
        CHECK(infile >> value && value == 5, "Fifth value should be 5", errors);
        CHECK(infile >> value && value == 6, "Sixth value should be 6", errors);
        CHECK(infile >> value && value == 7, "Seventh value should be 7", errors);
        CHECK(infile >> value && value == 8, "Eighth value should be 8", errors);
        CHECK(infile >> value && value == 9, "Ninth value should be 9", errors);

        infile.close();

        // Clean up the test file
        if (std::remove(filename.c_str()) != 0) {
            errors << RED << "Failure: Unable to delete file " << filename << RESET << std::endl;
            ++total_failures;
        }
    }

    // Determine if the test passed or failed
    if (errors.str().empty()) {
        std::cout << std::left << std::setw(60) << "[MT3]. Test Matrix Save Method."
                  << GREEN << "[Passed]" << RESET << std::endl;
    } else {
        std::cout << std::left << std::setw(60) << "[MT3]. Test Matrix Save Method."
                  << RED << "[Failed]" << RESET << std::endl;
        // Print the collected error messages
        std::cout << errors.str()<< std::endl;
    }
}

// ========================= DependencyTable Tests =========================

// Test Function 4: Default Constructor
void test_default_constructor() {
    std::stringstream errors;

    DependencyTable dt;

    // Check initial dimensions
    CHECK(dt.rows() == 0, "Default constructor should initialize rows to 0", errors);
    CHECK(dt.cols() == 0, "Default constructor should initialize columns to 0", errors);

    // Check data pointer is nullptr (Not directly accessible, so we rely on rows and cols)
    // Alternatively, if you add a method to check data pointer, you can test it here

    // Determine if the test passed or failed
    if (errors.str().empty()) {
        std::cout << std::left << std::setw(60) << "[DT1]. Test Default Constructor."
                  << GREEN << "[Passed]" << RESET << std::endl;
    } else {
        std::cout << std::left << std::setw(60) << "[DT1]. Test Default Constructor."
                  << RED << "[Failed]" << RESET << std::endl;
        std::cout << errors.str()<< std::endl;
    }
}

// Test Function 5: Parameterized Constructor
void test_parameterized_constructor() {
    std::stringstream errors;

    size_t rows = 3;
    size_t cols = 4;
    DependencyTable dt(rows, cols);

    // Check dimensions
    CHECK(dt.rows() == rows, "Parameterized constructor should set correct number of rows", errors);
    CHECK(dt.cols() == cols, "Parameterized constructor should set correct number of columns", errors);

    // Check all dependencies are initialized to false (default)
    for (size_t i = 0; i < rows; ++i) {
        for (size_t j = 0; j < cols; ++j) {
            CHECK(dt.getDependency(i, j) == false, "All dependencies should be initialized to false", errors);
        }
    }

    // Determine if the test passed or failed
    if (errors.str().empty()) {
        std::cout << std::left << std::setw(60) << "[DT2]. Test Parameterized Constructor."
                  << GREEN << "[Passed]" << RESET << std::endl;
    } else {
        std::cout << std::left << std::setw(60) << "[DT2]. Test Parameterized Constructor."
                  << RED << "[Failed]" << RESET << std::endl;
        std::cout << errors.str()<< std::endl;
    }
}

// Test Function 6: Init Method
void test_init() {
    std::stringstream errors;

    DependencyTable dt;
    size_t initial_rows = 2;
    size_t initial_cols = 2;
    dt.init(initial_rows, initial_cols);

    // Check dimensions after init
    CHECK(dt.rows() == initial_rows, "Init method should set correct number of rows", errors);
    CHECK(dt.cols() == initial_cols, "Init method should set correct number of columns", errors);

    // Check all dependencies are initialized to false
    for (size_t i = 0; i < initial_rows; ++i) {
        for (size_t j = 0; j < initial_cols; ++j) {
            CHECK(dt.getDependency(i, j) == false, "All dependencies should be initialized to false after init", errors);
        }
    }

    // Re-initialize with different dimensions
    size_t new_rows = 4;
    size_t new_cols = 5;
    dt.init(new_rows, new_cols);

    // Check new dimensions
    CHECK(dt.rows() == new_rows, "Init method should correctly reinitialize number of rows", errors);
    CHECK(dt.cols() == new_cols, "Init method should correctly reinitialize number of columns", errors);

    // Check all dependencies are reset to false
    for (size_t i = 0; i < new_rows; ++i) {
        for (size_t j = 0; j < new_cols; ++j) {
            CHECK(dt.getDependency(i, j) == false, "All dependencies should be reset to false after re-init", errors);
        }
    }

    // Determine if the test passed or failed
    if (errors.str().empty()) {
        std::cout << std::left << std::setw(60) << "[DT3]. Test Init Method."
                  << GREEN << "[Passed]" << RESET << std::endl;
    } else {
        std::cout << std::left << std::setw(60) << "[DT3]. Test Init Method."
                  << RED << "[Failed]" << RESET << std::endl;
        std::cout << errors.str()<< std::endl;
    }
}

// Test Function 7: Move Constructor
void test_move_constructor() {
    std::stringstream errors;

    size_t rows = 3;
    size_t cols = 3;
    DependencyTable dt1(rows, cols);
    dt1.setDependency(0, 0, true);
    dt1.setDependency(1, 1, true);
    dt1.setDependency(2, 2, true);

    // Move construct dt2 from dt1
    DependencyTable dt2(std::move(dt1));

    // Check dt2 has the data
    CHECK(dt2.rows() == rows, "Move constructor should transfer correct number of rows", errors);
    CHECK(dt2.cols() == cols, "Move constructor should transfer correct number of columns", errors);
    CHECK(dt2.getDependency(0, 0) == true, "Move constructor should transfer dependency at (0,0)", errors);
    CHECK(dt2.getDependency(1, 1) == true, "Move constructor should transfer dependency at (1,1)", errors);
    CHECK(dt2.getDependency(2, 2) == true, "Move constructor should transfer dependency at (2,2)", errors);

    // Check dt1 is in a valid state (rows and cols should be 0)
    CHECK(dt1.rows() == 0, "After move, source should have rows set to 0", errors);
    CHECK(dt1.cols() == 0, "After move, source should have columns set to 0", errors);

    // Determine if the test passed or failed
    if (errors.str().empty()) {
        std::cout << std::left << std::setw(60) << "[DT4]. Test Move Constructor."
                  << GREEN << "[Passed]" << RESET << std::endl;
    } else {
        std::cout << std::left << std::setw(60) << "[DT4]. Test Move Constructor."
                  << RED << "[Failed]" << RESET << std::endl;
        std::cout << errors.str()<< std::endl;
    }
}

// Test Function 8: Move Assignment Operator
void test_move_assignment() {
    std::stringstream errors;

    size_t rows1 = 2;
    size_t cols1 = 2;
    DependencyTable dt1(rows1, cols1);
    dt1.setDependency(0, 0, true);
    dt1.setDependency(1, 1, true);

    size_t rows2 = 4;
    size_t cols2 = 4;
    DependencyTable dt2(rows2, cols2);
    dt2.setDependency(0, 0, true);
    dt2.setDependency(3, 3, true);

    // Move assign dt1 to dt2
    dt2 = std::move(dt1);

    // Check dt2 has the data from dt1
    CHECK(dt2.rows() == rows1, "Move assignment should transfer correct number of rows", errors);
    CHECK(dt2.cols() == cols1, "Move assignment should transfer correct number of columns", errors);
    CHECK(dt2.getDependency(0, 0) == true, "Move assignment should transfer dependency at (0,0)", errors);
    CHECK(dt2.getDependency(1, 1) == true, "Move assignment should transfer dependency at (1,1)", errors);

    // Check dt1 is in a valid state
    CHECK(dt1.rows() == 0, "After move assignment, source should have rows set to 0", errors);
    CHECK(dt1.cols() == 0, "After move assignment, source should have columns set to 0", errors);

    // Ensure dt2 no longer has old data (size2 was 4x4, now 2x2)
    // Attempting to access (3,3) should throw
    try {
        dt2.getDependency(3, 3);
        errors << RED << "Failure: Accessing (3,3) should throw after move assignment." << RESET << std::endl;
        ++total_failures;
    } catch (const std::out_of_range&) {
        // Expected exception
    } catch (...) {
        errors << RED << "Failure: Unexpected exception type when accessing out-of-bounds." << RESET << std::endl;
        ++total_failures;
    }

    // Determine if the test passed or failed
    if (errors.str().empty()) {
        std::cout << std::left << std::setw(60) << "[DT5]. Test Move Assignment Operator."
                  << GREEN << "[Passed]" << RESET << std::endl;
    } else {
        std::cout << std::left << std::setw(60) << "[DT5]. Test Move Assignment Operator."
                  << RED << "[Failed]" << RESET << std::endl;
        std::cout << errors.str()<< std::endl;
    }
}

// Test Function 9: Get and Set Dependency
void test_get_set_dependency() {
    std::stringstream errors;

    size_t rows = 3;
    size_t cols = 3;
    DependencyTable dt(rows, cols);

    // Set some dependencies
    dt.setDependency(0, 0, true);
    dt.setDependency(1, 1, true);
    dt.setDependency(2, 2, true);
    dt.setDependency(0, 2, true);

    // Get and check dependencies
    CHECK(dt.getDependency(0, 0) == true, "Dependency at (0,0) should be true", errors);
    CHECK(dt.getDependency(1, 1) == true, "Dependency at (1,1) should be true", errors);
    CHECK(dt.getDependency(2, 2) == true, "Dependency at (2,2) should be true", errors);
    CHECK(dt.getDependency(0, 2) == true, "Dependency at (0,2) should be true", errors);
    CHECK(dt.getDependency(0, 1) == false, "Dependency at (0,1) should be false", errors);
    CHECK(dt.getDependency(1, 0) == false, "Dependency at (1,0) should be false", errors);

    // Determine if the test passed or failed
    if (errors.str().empty()) {
        std::cout << std::left << std::setw(60) << "[DT6]. Test Get and Set Dependency."
                  << GREEN << "[Passed]" << RESET << std::endl;
    } else {
        std::cout << std::left << std::setw(60) << "[DT6]. Test Get and Set Dependency."
                  << RED << "[Failed]" << RESET << std::endl;
        std::cout << errors.str()<< std::endl;
    }
}

// Test Function 10: Operator Overloading
void test_operator_overloading() {
    std::stringstream errors;

    size_t rows = 2;
    size_t cols = 2;
    DependencyTable dt(rows, cols);

    // Use operator() to set dependencies
    try {
        dt(0, 0, true);
        dt(1, 1, true);
        dt(0, 1, false);
        dt(1, 0, true);
    } catch (...) {
        errors << RED << "Failure: Operator() threw an unexpected exception during setting." << RESET << std::endl;
        ++total_failures;
    }

    // Use operator() to get dependencies and verify
    try {
        CHECK(dt(0, 0) == true, "Operator() should return true for (0,0)", errors);
        CHECK(dt(1, 1) == true, "Operator() should return true for (1,1)", errors);
        CHECK(dt(0, 1) == false, "Operator() should return false for (0,1)", errors);
        CHECK(dt(1, 0) == true, "Operator() should return true for (1,0)", errors);
    } catch (...) {
        errors << RED << "Failure: Operator() threw an unexpected exception during getting." << RESET << std::endl;
        ++total_failures;
    }

    // Attempt to access out-of-bounds using operator() and expect exceptions
    try {
        dt(2, 2); // Should throw
        errors << RED << "Failure: Accessing (2,2) should throw an exception." << RESET << std::endl;
        ++total_failures;
    } catch (const std::out_of_range&) {
        // Expected exception
    } catch (...) {
        errors << RED << "Failure: Unexpected exception type when accessing out-of-bounds with operator()." << RESET << std::endl;
        ++total_failures;
    }

    // Determine if the test passed or failed
    if (errors.str().empty()) {
        std::cout << std::left << std::setw(60) << "[DT7]. Test Operator Overloading."
                  << GREEN << "[Passed]" << RESET << std::endl;
    } else {
        std::cout << std::left << std::setw(60) << "[DT7]. Test Operator Overloading."
                  << RED << "[Failed]" << RESET << std::endl;
        std::cout << errors.str()<< std::endl;
    }
}

// Test Function 11: Out of Bounds Access
void test_out_of_bounds() {
    std::stringstream errors;

    size_t rows = 2;
    size_t cols = 2;
    DependencyTable dt(rows, cols);

    /*
    // Test getDependency out-of-bounds
    try {
        dt.getDependency(2, 0);
        errors << RED << "Failure: getDependency(2,0) should throw an exception." << RESET << std::endl;
        ++total_failures;
    } catch (const std::out_of_range&) {
        // Expected exception
    } catch (...) {
        errors << RED << "Failure: Unexpected exception type in getDependency out-of-bounds." << RESET << std::endl;
        ++total_failures;
    }

    // Test setDependency out-of-bounds
    try {
        dt.setDependency(0, 2, true);
        errors << RED << "Failure: setDependency(0,2) should throw an exception." << RESET << std::endl;
        ++total_failures;
    } catch (const std::out_of_range&) {
        // Expected exception
    } catch (...) {
        errors << RED << "Failure: Unexpected exception type in setDependency out-of-bounds." << RESET << std::endl;
        ++total_failures;
    }
    */

    // Test operator() get out-of-bounds
    try {
        dt(0, 3);
        errors << RED << "Failure: operator()(0,3) should throw an exception." << RESET << std::endl;
        ++total_failures;
    } catch (const std::out_of_range&) {
        // Expected exception
    } catch (...) {
        errors << RED << "Failure: Unexpected exception type in operator() get out-of-bounds." << RESET << std::endl;
        ++total_failures;
    }

    // Test operator() set out-of-bounds
    try {
        dt(3, 0, true);
        errors << RED << "Failure: operator()(3,0, true) should throw an exception." << RESET << std::endl;
        ++total_failures;
    } catch (const std::out_of_range&) {
        // Expected exception
    } catch (...) {
        errors << RED << "Failure: Unexpected exception type in operator() set out-of-bounds." << RESET << std::endl;
        ++total_failures;
    }

    // Determine if the test passed or failed
    if (errors.str().empty()) {
        std::cout << std::left << std::setw(60) << "[DT8]. Test Out of Bounds Access."
                  << GREEN << "[Passed]" << RESET << std::endl;
    } else {
        std::cout << std::left << std::setw(60) << "[DT8]. Test Out of Bounds Access."
                  << RED << "[Failed]" << RESET << std::endl;
        std::cout << errors.str()<< std::endl;
    }
}

// =================== DependencyTableAtomic Tests ======================== //

// Test 1: Default Constructor
void test_default_constructor_atomic() {
    std::stringstream errors;

    DependencyTableAtomic dt;

    // Check initial dimensions
    CHECK(dt.rows() == 0, "Default constructor should initialize rows to 0", errors);
    CHECK(dt.cols() == 0, "Default constructor should initialize cols to 0", errors);

    // Determine if the test passed or failed
    if (errors.str().empty()) {
        std::cout << std::left << std::setw(60)
                  << "[DTA1]. Test Default Constructor."
                  << GREEN << "[Passed]" << RESET << std::endl;
    } else {
        std::cout << std::left << std::setw(60)
                  << "[DTA1]. Test Default Constructor."
                  << RED << "[Failed]" << RESET << std::endl;
        std::cout << errors.str() << std::endl;
    }
}

// Test 2: Parameterized Constructor
void test_parameterized_constructor_atomic() {
    std::stringstream errors;

    size_t rows = 3;
    size_t cols = 4;
    DependencyTableAtomic dt(rows, cols);

    // Check dimensions
    CHECK(dt.rows() == rows, "Parameterized constructor should set correct number of rows", errors);
    CHECK(dt.cols() == cols, "Parameterized constructor should set correct number of columns", errors);

    // Check all dependencies are initialized to false by default
    for (size_t i = 0; i < rows; ++i) {
        for (size_t j = 0; j < cols; ++j) {
            CHECK(dt.getDependency(i, j) == false,
                  "All dependencies should be initialized to false", errors);
        }
    }

    // Determine if the test passed or failed
    if (errors.str().empty()) {
        std::cout << std::left << std::setw(60)
                  << "[DTA2]. Test Parameterized Constructor."
                  << GREEN << "[Passed]" << RESET << std::endl;
    } else {
        std::cout << std::left << std::setw(60)
                  << "[DTA2]. Test Parameterized Constructor."
                  << RED << "[Failed]" << RESET << std::endl;
        std::cout << errors.str() << std::endl;
    }
}

// Test 3: Init Method
void test_init_atomic() {
    std::stringstream errors;

    DependencyTableAtomic dt;
    size_t initial_rows = 2;
    size_t initial_cols = 2;
    dt.init(initial_rows, initial_cols);

    // Check dimensions after init
    CHECK(dt.rows() == initial_rows, "Init method should set correct number of rows", errors);
    CHECK(dt.cols() == initial_cols, "Init method should set correct number of columns", errors);

    // Check all dependencies are initialized to false
    for (size_t i = 0; i < initial_rows; ++i) {
        for (size_t j = 0; j < initial_cols; ++j) {
            CHECK(dt.getDependency(i, j) == false,
                  "All dependencies should be initialized to false after init", errors);
        }
    }

    // Re-initialize with different dimensions
    size_t new_rows = 4;
    size_t new_cols = 5;
    dt.init(new_rows, new_cols);

    // Check new dimensions
    CHECK(dt.rows() == new_rows, "Init method should correctly reinitialize number of rows", errors);
    CHECK(dt.cols() == new_cols, "Init method should correctly reinitialize number of columns", errors);

    // Check all dependencies are reset to false
    for (size_t i = 0; i < new_rows; ++i) {
        for (size_t j = 0; j < new_cols; ++j) {
            CHECK(dt.getDependency(i, j) == false,
                  "All dependencies should be reset to false after re-init", errors);
        }
    }

    // Determine if the test passed or failed
    if (errors.str().empty()) {
        std::cout << std::left << std::setw(60)
                  << "[DTA3]. Test Init Method."
                  << GREEN << "[Passed]" << RESET << std::endl;
    } else {
        std::cout << std::left << std::setw(60)
                  << "[DTA3]. Test Init Method."
                  << RED << "[Failed]" << RESET << std::endl;
        std::cout << errors.str() << std::endl;
    }
}

// Test 4: Move Constructor
void test_move_constructor_atomic() {
    std::stringstream errors;

    size_t rows = 3;
    size_t cols = 3;
    DependencyTableAtomic dt1(rows, cols);
    dt1.setDependency(0, 0, true);
    dt1.setDependency(1, 1, true);
    dt1.setDependency(2, 2, true);

    // Move construct dt2 from dt1
    DependencyTableAtomic dt2(std::move(dt1));

    // Check dt2 has the data
    CHECK(dt2.rows() == rows, "Move constructor should transfer correct number of rows", errors);
    CHECK(dt2.cols() == cols, "Move constructor should transfer correct number of cols", errors);
    CHECK(dt2.getDependency(0, 0) == true,  "Move constructor should transfer dependency at (0,0)", errors);
    CHECK(dt2.getDependency(1, 1) == true,  "Move constructor should transfer dependency at (1,1)", errors);
    CHECK(dt2.getDependency(2, 2) == true,  "Move constructor should transfer dependency at (2,2)", errors);

    // Check dt1 is in a valid moved-from state
    CHECK(dt1.rows() == 0, "After move, source should have rows set to 0", errors);
    CHECK(dt1.cols() == 0, "After move, source should have cols set to 0", errors);

    // Determine if the test passed or failed
    if (errors.str().empty()) {
        std::cout << std::left << std::setw(60)
                  << "[DTA4]. Test Move Constructor."
                  << GREEN << "[Passed]" << RESET << std::endl;
    } else {
        std::cout << std::left << std::setw(60)
                  << "[DTA4]. Test Move Constructor."
                  << RED << "[Failed]" << RESET << std::endl;
        std::cout << errors.str() << std::endl;
    }
}

// Test 5: Move Assignment Operator
void test_move_assignment_atomic() {
    std::stringstream errors;

    size_t rows1 = 2;
    size_t cols1 = 2;
    DependencyTableAtomic dt1(rows1, cols1);
    dt1.setDependency(0, 0, true);
    dt1.setDependency(1, 1, true);

    size_t rows2 = 4;
    size_t cols2 = 4;
    DependencyTableAtomic dt2(rows2, cols2);
    dt2.setDependency(0, 0, true);
    dt2.setDependency(3, 3, true);

    // Move assign dt2 <- dt1
    dt2 = std::move(dt1);

    // Check dt2 has the data from dt1
    CHECK(dt2.rows() == rows1, "Move assignment should transfer correct number of rows", errors);
    CHECK(dt2.cols() == cols1, "Move assignment should transfer correct number of cols", errors);
    CHECK(dt2.getDependency(0, 0) == true,  "Move assignment should transfer dependency at (0,0)", errors);
    CHECK(dt2.getDependency(1, 1) == true,  "Move assignment should transfer dependency at (1,1)", errors);

    // Check dt1 is in a valid moved-from state
    CHECK(dt1.rows() == 0, "After move assignment, source should have rows set to 0", errors);
    CHECK(dt1.cols() == 0, "After move assignment, source should have cols set to 0", errors);

    // Ensure dt2 no longer has old data (it should be 2x2 now)
    // Accessing (3,3) should throw
    try {
        dt2.getDependency(3, 3);
        errors << RED << "Failure: Accessing (3,3) should throw after move assignment." << RESET << std::endl;
        ++total_failures;
    } catch (const std::out_of_range&) {
        // Expected
    } catch (...) {
        errors << RED << "Failure: Unexpected exception type when accessing out-of-bounds." << RESET << std::endl;
        ++total_failures;
    }

    // Determine if the test passed or failed
    if (errors.str().empty()) {
        std::cout << std::left << std::setw(60)
                  << "[DTA5]. Test Move Assignment Operator."
                  << GREEN << "[Passed]" << RESET << std::endl;
    } else {
        std::cout << std::left << std::setw(60)
                  << "[DTA5]. Test Move Assignment Operator."
                  << RED << "[Failed]" << RESET << std::endl;
        std::cout << errors.str() << std::endl;
    }
}

// Test 6: Get and Set Dependency
void test_get_set_dependency_atomic() {
    std::stringstream errors;

    size_t rows = 3;
    size_t cols = 3;
    DependencyTableAtomic dt(rows, cols);

    // Set some dependencies
    dt.setDependency(0, 0, true);
    dt.setDependency(1, 1, true);
    dt.setDependency(2, 2, true);
    dt.setDependency(0, 2, true);

    // Verify using getDependency
    CHECK(dt.getDependency(0, 0) == true,  "Dependency at (0,0) should be true", errors);
    CHECK(dt.getDependency(1, 1) == true,  "Dependency at (1,1) should be true", errors);
    CHECK(dt.getDependency(2, 2) == true,  "Dependency at (2,2) should be true", errors);
    CHECK(dt.getDependency(0, 2) == true,  "Dependency at (0,2) should be true", errors);
    CHECK(dt.getDependency(0, 1) == false, "Dependency at (0,1) should be false", errors);
    CHECK(dt.getDependency(1, 0) == false, "Dependency at (1,0) should be false", errors);

    // Determine if the test passed or failed
    if (errors.str().empty()) {
        std::cout << std::left << std::setw(60)
                  << "[DTA6]. Test Get and Set Dependency."
                  << GREEN << "[Passed]" << RESET << std::endl;
    } else {
        std::cout << std::left << std::setw(60)
                  << "[DTA6]. Test Get and Set Dependency."
                  << RED << "[Failed]" << RESET << std::endl;
        std::cout << errors.str() << std::endl;
    }
}

// Test 7: Operator Overloading
void test_operator_overloading_atomic() {
    std::stringstream errors;

    size_t rows = 2;
    size_t cols = 2;
    DependencyTableAtomic dt(rows, cols);

    // Use operator() to set dependencies
    try {
        dt(0, 0, true);
        dt(1, 1, true);
        dt(0, 1, false);
        dt(1, 0, true);
    } catch (...) {
        errors << RED << "Failure: Operator() threw an unexpected exception during set." << RESET << std::endl;
        ++total_failures;
    }

    // Use operator() to get dependencies
    try {
        CHECK(dt(0, 0) == true,  "Operator() should return true for (0,0)", errors);
        CHECK(dt(1, 1) == true,  "Operator() should return true for (1,1)", errors);
        CHECK(dt(0, 1) == false, "Operator() should return false for (0,1)", errors);
        CHECK(dt(1, 0) == true,  "Operator() should return true for (1,0)", errors);
    } catch (...) {
        errors << RED << "Failure: Operator() threw an unexpected exception during get." << RESET << std::endl;
        ++total_failures;
    }

    // Attempt out-of-bounds access for get
    try {
        dt(2, 2); // Should throw
        errors << RED << "Failure: Accessing (2,2) should throw an exception." << RESET << std::endl;
        ++total_failures;
    } catch (const std::out_of_range&) {
        // Expected
    } catch (...) {
        errors << RED << "Failure: Unexpected exception type when accessing out-of-bounds." << RESET << std::endl;
        ++total_failures;
    }

    // Determine if the test passed or failed
    if (errors.str().empty()) {
        std::cout << std::left << std::setw(60)
                  << "[DTA7]. Test Operator Overloading."
                  << GREEN << "[Passed]" << RESET << std::endl;
    } else {
        std::cout << std::left << std::setw(60)
                  << "[DTA7]. Test Operator Overloading."
                  << RED << "[Failed]" << RESET << std::endl;
        std::cout << errors.str() << std::endl;
    }
}

// Test 8: Out of Bounds Access
void test_out_of_bounds_atomic() {
    std::stringstream errors;

    size_t rows = 2;
    size_t cols = 2;
    DependencyTableAtomic dt(rows, cols);

    // Operator() get out-of-bounds
    try {
        dt(0, 3); // Should throw
        errors << RED << "Failure: operator()(0,3) should throw an exception." << RESET << std::endl;
        ++total_failures;
    } catch (const std::out_of_range&) {
        // Expected
    } catch (...) {
        errors << RED << "Failure: Unexpected exception type in operator() get out-of-bounds." << RESET << std::endl;
        ++total_failures;
    }

    // Operator() set out-of-bounds
    try {
        dt(3, 0, true); // Should throw
        errors << RED << "Failure: operator()(3,0,true) should throw an exception." << RESET << std::endl;
        ++total_failures;
    } catch (const std::out_of_range&) {
        // Expected
    } catch (...) {
        errors << RED << "Failure: Unexpected exception type in operator() set out-of-bounds." << RESET << std::endl;
        ++total_failures;
    }

    // Determine if the test passed or failed
    if (errors.str().empty()) {
        std::cout << std::left << std::setw(60)
                  << "[DTA8]. Test Out of Bounds Access."
                  << GREEN << "[Passed]" << RESET << std::endl;
    } else {
        std::cout << std::left << std::setw(60)
                  << "[DTA8]. Test Out of Bounds Access."
                  << RED << "[Failed]" << RESET << std::endl;
        std::cout << errors.str() << std::endl;
    }
}

// ====================== CircularQueueMtx Tests =========================== //

// Test Case 1: Test Empty Queue and Size
void test_queue_empty_and_size() {
    std::stringstream errors;
    CircularQueueMtx<int> q(5);

    CHECK(q.empty(), "Queue should be empty initially", errors);
    CHECK(q.size() == 0, "Queue size should be 0 initially", errors);

    if (errors.str().empty()) {
         std::cout << std::left << std::setw(60)
                   << "[QueueTest1] Test Empty and Size"
                   << GREEN << "[Passed]" << RESET << std::endl;
    } else {
         std::cout << std::left << std::setw(60)
                   << "[QueueTest1] Test Empty and Size"
                   << RED << "[Failed]" << RESET << std::endl;
         std::cout << errors.str();
         total_failures++;
    }
}

// Test Case 2: Test push_back and pop_front (FIFO behavior)
void test_queue_push_pop_fifo() {
    std::stringstream errors;
    CircularQueueMtx<int> queue(5);
    // Push several elements at the back.
    CHECK(queue.push_back(1), "Push_back 1 should succeed", errors);
    CHECK(queue.push_back(2), "Push_back 2 should succeed", errors);
    CHECK(queue.push_back(3), "Push_back 3 should succeed", errors);
    CHECK(queue.size() == 3, "Queue size should be 3 after three pushes", errors);
    CHECK(!queue.empty(), "Queue should not be empty after pushes", errors);

    // Pop the elements from the front (FIFO).
    auto a = queue.pop_front();
    CHECK(a.has_value() && a.value() == 1, "First pop_front should return 1", errors);
    auto b = queue.pop_front();
    CHECK(b.has_value() && b.value() == 2, "Second pop_front should return 2", errors);
    auto c = queue.pop_front();
    CHECK(c.has_value() && c.value() == 3, "Third pop_front should return 3", errors);
    CHECK(queue.empty(), "Queue should be empty after popping all elements", errors);

    // Additional pop from empty queue should return nullopt.
    auto d = queue.pop_front();
    CHECK(!d.has_value(), "pop_front on empty queue should return nullopt", errors);

    if (errors.str().empty()) {
         std::cout << std::left << std::setw(60)
                   << "[QueueTest2] Test Push_Back and Pop_Front FIFO"
                   << GREEN << "[Passed]" << RESET << std::endl;
    } else {
         std::cout << std::left << std::setw(60)
                   << "[QueueTest2] Test Push_Back and Pop_Front FIFO"
                   << RED << "[Failed]" << RESET << std::endl;
         std::cout << errors.str();
         total_failures++;
    }
}

// Test Case 3: Test push_front and pop_back (Reverse order)
void test_queue_push_front_pop_back() {
    std::stringstream errors;
    CircularQueueMtx<int> queue(5);
    // Insert elements using push_front.
    CHECK(queue.push_front(10), "Push_front 10 should succeed", errors);
    CHECK(queue.push_front(20), "Push_front 20 should succeed", errors);
    CHECK(queue.push_front(30), "Push_front 30 should succeed", errors);
    // The elements (in order of insertion via push_front) end up as: 30, 20, 10.
    // Popping from the back should return the element inserted first (i.e. 10, then 20, then 30).
    auto a = queue.pop_back();
    CHECK(a.has_value() && a.value() == 10, "First pop_back should return 10", errors);
    auto b = queue.pop_back();
    CHECK(b.has_value() && b.value() == 20, "Second pop_back should return 20", errors);
    auto c = queue.pop_back();
    CHECK(c.has_value() && c.value() == 30, "Third pop_back should return 30", errors);
    CHECK(queue.empty(), "Queue should be empty after pop_back operations", errors);

    if (errors.str().empty()) {
         std::cout << std::left << std::setw(60)
                   << "[QueueTest3] Test Push_Front and Pop_Back"
                   << GREEN << "[Passed]" << RESET << std::endl;
    } else {
         std::cout << std::left << std::setw(60)
                   << "[QueueTest3] Test Push_Front and Pop_Back"
                   << RED << "[Failed]" << RESET << std::endl;
         std::cout << errors.str();
         total_failures++;
    }
}

// Test Case 4: Test Full Queue Behavior
void test_queue_full() {
    std::stringstream errors;
    CircularQueueMtx<int> queue(3);
    CHECK(queue.push_back(1), "Push_back 1 should succeed", errors);
    CHECK(queue.push_back(2), "Push_back 2 should succeed", errors);
    CHECK(queue.push_back(3), "Push_back 3 should succeed", errors);
    CHECK(queue.full(), "Queue should be full after three pushes", errors);

    // Attempt additional pushes; they must fail.
    CHECK(!queue.push_back(4), "Push_back 4 should fail on full queue", errors);
    CHECK(!queue.push_front(5), "Push_front 5 should fail on full queue", errors);

    // After a pop, the queue is no longer full.
    auto a = queue.pop_front();
    CHECK(a.has_value(), "pop_front should succeed on full queue", errors);
    CHECK(!queue.full(), "Queue should not be full after a pop", errors);

    if (errors.str().empty()) {
         std::cout << std::left << std::setw(60)
                   << "[QueueTest4] Test Full Queue Behavior"
                   << GREEN << "[Passed]" << RESET << std::endl;
    } else {
         std::cout << std::left << std::setw(60)
                   << "[QueueTest4] Test Full Queue Behavior"
                   << RED << "[Failed]" << RESET << std::endl;
         std::cout << errors.str();
         total_failures++;
    }
}

// Test Case 5: Multi-threaded Producer/Consumer Operations
void test_queue_multi_threaded() {
    std::stringstream errors;
    const size_t capacity = 50;
    const int num_elements = 1000;
    CircularQueueMtx<int> queue(capacity);
    std::atomic<bool> done{false};
    std::atomic<int> produced{0};
    std::atomic<int> consumed{0};

    // Producer thread: push numbers into the queue.
    auto producer = [&]() {
         for (int i = 0; i < num_elements; ++i) {
              while (!queue.push_back(i)) {
                   std::this_thread::yield();
              }
              produced.fetch_add(1, std::memory_order_relaxed);
         }
         done = true;
    };

    // Consumer thread: pop numbers from the queue.
    auto consumer = [&]() {
         while (!done || !queue.empty()) {
              auto value = queue.pop_front();
              if (value.has_value()) {
                   consumed.fetch_add(1, std::memory_order_relaxed);
              } else {
                   std::this_thread::yield();
              }
         }
    };

    std::thread prodThread(producer);
    std::thread consThread(consumer);
    prodThread.join();
    consThread.join();

    CHECK(produced.load(std::memory_order_relaxed) == num_elements,
          "Produced count should equal num_elements", errors);
    CHECK(consumed.load(std::memory_order_relaxed) == num_elements,
          "Consumed count should equal num_elements", errors);

    if (errors.str().empty()) {
         std::cout << std::left << std::setw(60)
                   << "[QueueTest5] Test Multi-threaded Operations"
                   << GREEN << "[Passed]" << RESET << std::endl;
    } else {
         std::cout << std::left << std::setw(60)
                   << "[QueueTest5] Test Multi-threaded Operations"
                   << RED << "[Failed]" << RESET << std::endl;
         std::cout << errors.str();
         total_failures++;
    }
}


// ==================== CircularQueueAtomic Tests ========================= //

// Test 1: Verify that a new queue is empty and its size is zero.
void test_atomic_queue_empty_and_size() {
    std::stringstream errors;
    CircularQueueAtomic<int> queue(5);
    CHECK(queue.empty(), "Queue should be empty initially", errors);
    CHECK(queue.size() == 0, "Queue size should be 0 initially", errors);

    if (errors.str().empty()) {
         std::cout << std::left << std::setw(60)
                   << "[AtomicQueueTest1] Test Empty and Size"
                   << GREEN << "[Passed]" << RESET << std::endl;
    } else {
         std::cout << std::left << std::setw(60)
                   << "[AtomicQueueTest1] Test Empty and Size"
                   << RED << "[Failed]" << RESET << std::endl;
         std::cout << errors.str();
         total_failures++;
    }
}

// Test 2: Test push_back and pop_front (FIFO behavior).
void test_atomic_queue_push_pop_fifo() {
    std::stringstream errors;
    CircularQueueAtomic<int> queue(5);

    // Insert elements using push_back.
    for (int i = 0; i < 3; ++i) {
        bool ok = queue.push_back(i);
        CHECK(ok, "push_back should succeed", errors);
    }
    CHECK(queue.size() == 3, "Queue size should be 3 after 3 pushes", errors);

    // Remove the elements using pop_front and verify FIFO order.
    for (int i = 0; i < 3; ++i) {
        auto opt = queue.pop_front();
        CHECK(opt.has_value(), "pop_front should return a value", errors);
        CHECK(opt.value() == i, "pop_front value should match FIFO order", errors);
    }
    CHECK(queue.empty(), "Queue should be empty after popping all elements", errors);

    if (errors.str().empty()) {
         std::cout << std::left << std::setw(60)
                   << "[AtomicQueueTest2] Test Push_Back and Pop_Front FIFO"
                   << GREEN << "[Passed]" << RESET << std::endl;
    } else {
         std::cout << std::left << std::setw(60)
                   << "[AtomicQueueTest2] Test Push_Back and Pop_Front FIFO"
                   << RED << "[Failed]" << RESET << std::endl;
         std::cout << errors.str();
         total_failures++;
    }
}

// Test 3: Test push_front and pop_back (reverse order behavior).
void test_atomic_queue_push_front_pop_back() {
    std::stringstream errors;
    CircularQueueAtomic<int> queue(5);

    // Insert elements using push_front.
    for (int i = 0; i < 3; ++i) {
        bool ok = queue.push_front(100 + i);
        CHECK(ok, "push_front should succeed", errors);
    }
    // When using push_front, the first inserted element is at the back.
    // Removing elements via pop_back should return them in the order of insertion.
    for (int i = 0; i < 3; ++i) {
        auto opt = queue.pop_back();
        CHECK(opt.has_value(), "pop_back should return a value", errors);
        CHECK(opt.value() == 100 + i, "pop_back value should match order", errors);
    }
    CHECK(queue.empty(), "Queue should be empty after pop_back operations", errors);

    if (errors.str().empty()) {
         std::cout << std::left << std::setw(60)
                   << "[AtomicQueueTest3] Test Push_Front and Pop_Back"
                   << GREEN << "[Passed]" << RESET << std::endl;
    } else {
         std::cout << std::left << std::setw(60)
                   << "[AtomicQueueTest3] Test Push_Front and Pop_Back"
                   << RED << "[Failed]" << RESET << std::endl;
         std::cout << errors.str();
         total_failures++;
    }
}

// Test 4: Test full queue behavior.
void test_atomic_queue_full() {
    std::stringstream errors;
    CircularQueueAtomic<int> queue(3);

    // Fill the queue.
    CHECK(queue.push_back(1), "push_back 1 should succeed", errors);
    CHECK(queue.push_back(2), "push_back 2 should succeed", errors);
    CHECK(queue.push_back(3), "push_back 3 should succeed", errors);
    CHECK(queue.full(), "Queue should be full after three pushes", errors);

    // Additional pushes should fail.
    CHECK(!queue.push_back(4), "push_back 4 should fail on full queue", errors);
    CHECK(!queue.push_front(5), "push_front 5 should fail on full queue", errors);

    // After a pop, the queue should no longer be full.
    auto opt = queue.pop_front();
    CHECK(opt.has_value(), "pop_front should succeed", errors);
    CHECK(!queue.full(), "Queue should not be full after popping an element", errors);

    if (errors.str().empty()) {
         std::cout << std::left << std::setw(60)
                   << "[AtomicQueueTest4] Test Full Queue Behavior"
                   << GREEN << "[Passed]" << RESET << std::endl;
    } else {
         std::cout << std::left << std::setw(60)
                   << "[AtomicQueueTest4] Test Full Queue Behavior"
                   << RED << "[Failed]" << RESET << std::endl;
         std::cout << errors.str();
         total_failures++;
    }
}

// Test 5: Multi-threaded Producer/Consumer Operations.
void test_atomic_queue_multi_threaded() {
    std::stringstream errors;
    const size_t capacity = 50;
    const int numElements = 1000;
    CircularQueueAtomic<int> queue(capacity);
    std::atomic<bool> done{false};
    std::atomic<int> produced{0};
    std::atomic<int> consumed{0};

    // Producer thread: pushes numbers into the queue.
    auto producer = [&]() {
         for (int i = 0; i < numElements; ++i) {
              while (!queue.push_back(i)) {
                   std::this_thread::yield();
              }
              produced.fetch_add(1, std::memory_order_relaxed);
         }
         done = true;
    };

    // Consumer thread: pops numbers from the queue.
    auto consumer = [&]() {
         while (!done || !queue.empty()) {
              auto item = queue.pop_front();
              if (item.has_value()) {
                   consumed.fetch_add(1, std::memory_order_relaxed);
              } else {
                   std::this_thread::yield();
              }
         }
    };

    std::thread prodThread(producer);
    std::thread consThread(consumer);
    prodThread.join();
    consThread.join();

    CHECK(produced.load(std::memory_order_relaxed) == numElements, "Produced count should equal numElements", errors);
    CHECK(consumed.load(std::memory_order_relaxed) == numElements, "Consumed count should equal numElements", errors);

    if (errors.str().empty()) {
         std::cout << std::left << std::setw(60)
                   << "[AtomicQueueTest5] Test Multi-threaded Operations"
                   << GREEN << "[Passed]" << RESET << std::endl;
    } else {
         std::cout << std::left << std::setw(60)
                   << "[AtomicQueueTest5] Test Multi-threaded Operations"
                   << RED << "[Failed]" << RESET << std::endl;
         std::cout << errors.str();
         total_failures++;
    }
}

// Test 6: Verify the convenience push/pop methods.
void test_atomic_queue_push_and_pop() {
    std::stringstream errors;
    CircularQueueAtomic<int> queue(10);

    // Use push (alias for push_back) to insert values.
    for (int i = 0; i < 5; ++i) {
         bool ok = queue.push(i);
         CHECK(ok, "push should succeed", errors);
    }
    // Use pop (alias for pop_front) to remove values and verify FIFO order.
    for (int i = 0; i < 5; ++i) {
         auto result = queue.pop();
         CHECK(result.has_value(), "pop should return a value", errors);
         CHECK(result.value() == i, "pop should return FIFO order value", errors);
    }

    if (errors.str().empty()) {
         std::cout << std::left << std::setw(60)
                   << "[AtomicQueueTest6] Test push/pop Convenience Methods"
                   << GREEN << "[Passed]" << RESET << std::endl;
    } else {
         std::cout << std::left << std::setw(60)
                   << "[AtomicQueueTest6] Test push/pop Convenience Methods"
                   << RED << "[Failed]" << RESET << std::endl;
         std::cout << errors.str();
         total_failures++;
    }
}

int main(int argc, char *argv[]) {
    std::cout << "Inside Test.\n" << std::endl;

    std::cout << YELLOW << "Starting matrix_t Test Cases." << RESET << std::endl;

    // Run matrix_t test functions
    test_operator_access();
    test_get_set();
    test_save();

    std::cout << YELLOW << "\nStarting DependencyTable Test Cases." << RESET << std::endl;

    // Run DependencyTable test functions
    test_default_constructor();
    test_parameterized_constructor();
    test_init();
    test_move_constructor();
    test_move_assignment();
    test_get_set_dependency();
    test_operator_overloading();
    test_out_of_bounds();

    std::cout << YELLOW << "\nStarting DependencyTableAtomic Test Cases." << RESET << std::endl;

    // Run DependencyTableAtomic test functions
    test_default_constructor_atomic();
    test_parameterized_constructor_atomic();
    test_init_atomic();
    test_move_constructor_atomic();
    test_move_assignment_atomic();
    test_get_set_dependency_atomic();
    test_operator_overloading_atomic();
    test_out_of_bounds_atomic();

    std::cout << YELLOW << "\nStarting CircularQueueMtx Test Cases." << RESET << std::endl;

    test_queue_empty_and_size();
    test_queue_push_pop_fifo();
    test_queue_push_front_pop_back();
    test_queue_full();
    test_queue_multi_threaded();

    std::cout << YELLOW << "\nStarting CircularQueueAtomic Test Cases." << RESET << std::endl;

    test_atomic_queue_empty_and_size();
    test_atomic_queue_push_pop_fifo();
    test_atomic_queue_push_front_pop_back();
    test_atomic_queue_full();
    test_atomic_queue_multi_threaded();
    test_atomic_queue_push_and_pop();


    std::cout << std::endl;

    // Summary of test results
    if (total_failures == 0) {
        std::cout << GREEN << "All tests passed." << RESET << std::endl;
    } else {
        std::cout << RED << "Some tests failed. Total Failures: " << total_failures << RESET << std::endl;
    }

    return (total_failures == 0) ? 0 : 1;
}