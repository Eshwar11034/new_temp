#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <pthread.h>
#include "bn2.h"
#include <unistd.h>
#include <csignal>
#include <cstdlib>
#include <random>
#include <chrono>

#define NUM_THREADS 52

#define BETA 32
#define ALPHA 32
#define BETA_DIV_ALPHA ((int)BETA/(int)ALPHA)


typedef struct {
    int tid;
    int total_task_rows;
    int total_task_cols;
    int m;
    int n;
    double* mat;
}thread_args_t;

std::vector<std::stringstream> logstreams(NUM_THREADS);

TaskTable task_table;
std::vector<double> global_up_array, global_b_array;
pthread_barrier_t barrier;

void complete_task1(double* &mat, int m, int n, int row_start, int row_end, int col_start, int col_end){

    double sm, sm1, cl, clinv, up, b;
    int _row_start = row_start == 1 ? 0 : row_start;

    for (int lpivot = _row_start; lpivot < row_end; lpivot++){
        cl = fabs(mat[lpivot * n + lpivot]);
        sm1 = 0;

        for (int k = lpivot+1; k < n; k++){
            sm = fabs(mat[lpivot * n + k]);
            sm1 += sm * sm;
            cl = fmax(sm, cl);
        }

        if (cl <= 0.0) { continue; } clinv = 1.0/cl;

        double d__1 = mat[lpivot * n + lpivot] * clinv;
        sm = d__1 * d__1;
        sm += sm1 * clinv * clinv;

        cl *= sqrt(sm);

        if (mat[lpivot * n + lpivot] > 0.0) { cl = -cl; }

        up = mat[lpivot * n + lpivot] - cl;
        mat[lpivot * n + lpivot] = cl;

        if (row_end - lpivot < 0) { continue;; }

        b = up * mat[lpivot * n + lpivot];

        if (b >= 0.0) { continue; }

        b = 1.0/b;

        global_up_array[lpivot] = up;
        global_b_array[lpivot] = b;

        for (int j = lpivot+1; j < col_end; j++){
            sm = mat[j * n + lpivot] * up;

            for (int i__ = lpivot+1; i__ < n; i__++){
                sm += mat[j * n + i__] * mat[lpivot * n + i__];
            }

            if (sm == 0.0) { continue; }

            sm *= b;
            mat[j * n + lpivot] += sm * up;

            for (int i__ = lpivot+1; i__ < n; i__++){
                mat[j * n + i__] += sm * mat[lpivot * n + i__];
            }
        }
    }
}

void complete_task2(double* &mat, int m, int n, int row_start, int row_end, int col_start, int col_end){
    
    int _row_start = row_start == 1 ? 0 : row_start;
    int _col_start = col_start == 1 ? 0 : col_start;

    double up = 0.0, b = 0.0, sm = 0.0;

    for (int lpivot = _row_start; lpivot < row_end; lpivot++){
        up = global_up_array[lpivot];
        b  = global_b_array[lpivot];

        for (int j = _col_start; j < col_end; j++){
            sm = mat[j * n + lpivot] * up;

            for (int i__ = lpivot+1; i__ < n; i__++){
                sm += mat[j * n + i__] * mat[lpivot * n + i__];
            }

            if (sm == 0.0) { continue; }

            sm *= b;
            mat[j * n + lpivot] += sm * up;

            for (int i__ = lpivot+1; i__ < n; i__++){
                mat[j * n + i__] += sm * mat[lpivot * n + i__];
            }
        }
    }
}

void* thdwork(void* params){
    thread_args_t* thread_args = (thread_args_t*)params;
    int tid = thread_args->tid;
    double* mat = thread_args->mat;
    int m = thread_args->m;
    int n = thread_args->n;

    pthread_barrier_wait(&barrier);

    for (int j = 0; j < task_table.cols(); j++){
        int ctr = 0;
        for (int i = 0; i < task_table.rows(); i++){

            if (task_table.getTask(i, j) == nullptr) { ctr++; continue; }

            if (ctr == i){
                Task* first_task = task_table.getTask(ctr, j);
                //printf("Before T1 Barrier: %d %zu %d\n", tid, ctr, j);
                pthread_barrier_wait(&barrier);
                if (tid == 0){
                    //printf("Inside T1 Barrier: %d %d %d %d\n", tid, ctr, j, first_task->type);
                    complete_task1(mat, m, n, first_task->row_start, first_task->row_end, first_task->col_start, first_task->col_end);
                }
                pthread_barrier_wait(&barrier);
            }

            int taskid = tid + ctr * NUM_THREADS + (ctr+1);

            if (taskid < task_table.rows()){
                //printf("After T1 barrier: %d %d %d\n", tid, taskid, j);
                Task* task = task_table.getTask(taskid, j);
                complete_task2(mat, m, n, task->row_start, task->row_end, task->col_start, task->col_end);
            }
            pthread_barrier_wait(&barrier);
        }
    }

    return nullptr;
}

int main(int argc, char *argv[]){
    std::cout << "[1]. Inside main." << std::endl;

    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <filename>" << std::endl;
        return EXIT_FAILURE;
    }

    matrix_t<double> data_matrix(argv[1]);

    int total_task_rows = std::ceil(data_matrix.rows()/BETA);
    int total_task_cols = std::ceil(data_matrix.rows()/ALPHA);

    global_up_array.resize(data_matrix.rows(), 0.0);
    global_b_array.resize(data_matrix.rows() , 0.0);

    task_table.init(total_task_rows, total_task_cols, ALPHA, BETA, data_matrix);

    std::vector<pthread_t> threads(NUM_THREADS);
    std::vector<thread_args_t> thread_args(NUM_THREADS);
    
    for (int i = 0; i < NUM_THREADS; i++){
        thread_args[i].tid = i;
        thread_args[i].total_task_rows = total_task_rows;
        thread_args[i].total_task_cols = total_task_cols;
        thread_args[i].m = data_matrix.rows();
        thread_args[i].n = data_matrix.cols();
        thread_args[i].mat = data_matrix.data_ptr();
    }

    pthread_barrier_init(&barrier, NULL, NUM_THREADS);

    auto start = std::chrono::high_resolution_clock::now();
    
    for (int i = 0; i < NUM_THREADS; i++){
        pthread_create(&threads[i], NULL, thdwork, &thread_args[i]);
    }

    for (int i = 0; i < NUM_THREADS; i++){
        pthread_join(threads[i], NULL);
    }
    
    auto end = std::chrono::high_resolution_clock::now();

    auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();

    std::cout << "Time taken: " << elapsed << " ms" << std::endl;

    pthread_barrier_destroy(&barrier);

    //data_matrix.save("output.txt");

    return 0;
}