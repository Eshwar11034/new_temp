#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <pthread.h>
#include "include/bn2.h"
#include <tbb/concurrent_priority_queue.h>
#include <tbb/tbb.h>
#include <unistd.h>
#include <csignal>
#include <cstdlib>
#include <mutex>

#define NUM_THREADS 28

#define BETA 16
#define ALPHA 4
#define BETA_DIV_ALPHA ((int)BETA / (int)ALPHA)

#define USE_PRIORITY_MAIN_QUEUE 0
typedef struct
{
    int tid;
    int total_task_rows;
    int total_task_cols;
    int m;
    int n;
    double *mat;
} thread_args_ts;

std::vector<std::stringstream> logstreams(NUM_THREADS);

TaskTable task_table;
DependencyTableAtomic dependency_table;

std::vector<double> global_up_array, global_b_array;


struct TaskComparator {
    bool operator()(const Task* a, const Task* b) const {
        return a->priority < b->priority; 
    }
};

tbb::concurrent_queue<Task *> wait_queue;//, taskPQ;

#if USE_PRIORITY_MAIN_QUEUE
tbb::concurrent_priority_queue<Task *, TaskComparator> taskPQ;
#else
tbb::concurrent_queue<Task *> taskPQ;
#endif
//tbb::concurrent_priority_queue<Task *, TaskComparator> taskPQ(1024);

void complete_task1(double *&mat, int m, int n, int row_start, int row_end, int col_start, int col_end)
{

    double sm, sm1, cl, clinv, up, b;
    int _row_start = row_start == 1 ? 0 : row_start;

    for (int lpivot = _row_start; lpivot < row_end; lpivot++)
    {
        cl = fabs(mat[lpivot * n + lpivot]);
        sm1 = 0;

        for (int k = lpivot + 1; k < n; k++)
        {
            sm = fabs(mat[lpivot * n + k]);
            sm1 += sm * sm;
            cl = fmax(sm, cl);
        }

        if (cl <= 0.0)
        {
            return;
        }
        clinv = 1.0 / cl;

        double d__1 = mat[lpivot * n + lpivot] * clinv;
        sm = d__1 * d__1;
        sm += sm1 * clinv * clinv;

        cl *= sqrt(sm);

        if (mat[lpivot * n + lpivot] > 0.0)
        {
            cl = -cl;
        }

        up = mat[lpivot * n + lpivot] - cl;
        mat[lpivot * n + lpivot] = cl;

        if (row_end - lpivot < 0)
        {
            return;
        }

        b = up * mat[lpivot * n + lpivot];

        if (b >= 0.0)
        {
            return;
        }

        b = 1.0 / b;

        global_up_array[lpivot] = up;
        global_b_array[lpivot] = b;

        for (int j = lpivot + 1; j < col_end; j++)
        {
            sm = mat[j * n + lpivot] * up;

            for (int i__ = lpivot + 1; i__ < n; i__++)
            {
                sm += mat[j * n + i__] * mat[lpivot * n + i__];
            }

            if (sm == 0.0)
            {
                continue;
            }

            sm *= b;
            mat[j * n + lpivot] += sm * up;

            for (int i__ = lpivot + 1; i__ < n; i__++)
            {
                mat[j * n + i__] += sm * mat[lpivot * n + i__];
            }
        }
    }
}

void complete_task2(double *&mat, int m, int n, int row_start, int row_end, int col_start, int col_end)
{

    int _row_start = row_start == 1 ? 0 : row_start;
    int _col_start = col_start == 1 ? 0 : col_start;

    double up = 0.0, b = 0.0, sm = 0.0;

    for (int lpivot = _row_start; lpivot < row_end; lpivot++)
    {
        up = global_up_array[lpivot];
        b = global_b_array[lpivot];

        for (int j = _col_start; j < col_end; j++)
        {
            sm = mat[j * n + lpivot] * up;

            for (int i__ = lpivot + 1; i__ < n; i__++)
            {
                sm += mat[j * n + i__] * mat[lpivot * n + i__];
            }

            if (sm == 0.0)
            {
                continue;
            }

            sm *= b;
            mat[j * n + lpivot] += sm * up;

            for (int i__ = lpivot + 1; i__ < n; i__++)
            {
                mat[j * n + i__] += sm * mat[lpivot * n + i__];
            }
        }
    }
}

void *thdwork(void *params)
{
    thread_args_ts *thread_args = (thread_args_ts *)params;

    int total_task_rows = thread_args->total_task_rows;
    int total_task_cols = thread_args->total_task_cols;
    double *mat = thread_args->mat;
    int m = thread_args->m;
    int n = thread_args->n;
    
    while (1)
    {
        Task *new_task = nullptr;
        //auto queue_elem1 = taskPQ.pop();
        if (taskPQ.try_pop(new_task)) ///Task *new_task = queue_elem1.value_or(nullptr))
        {
            int i = new_task->chunk_idx_i;
            int j = new_task->chunk_idx_j;

            int row_start = new_task->row_start;
            int row_end = new_task->row_end;
            int col_start = new_task->col_start;
            int col_end = new_task->col_end;

            if (new_task->type == 1)
            {
                complete_task1(mat, m, n, row_start, row_end, col_start, col_end);
                dependency_table.setDependency(i, j, true);
                for (int k = i + 1; k < total_task_rows; k++)
                {
                    Task *next_task = task_table.getTask(k, j);

                    if (j == 0 || dependency_table.getDependency(k, j - 1))
                    {
                        taskPQ.push(next_task);
                    }
                    else
                    {
                        wait_queue.push(next_task);
                    }
                }
            }
            else if (new_task->type == 2)
            {
                complete_task2(mat, m, n, row_start, row_end, col_start, col_end);
                dependency_table.setDependency(i, j, true);
                if (new_task->enq_nxt_t1 && (j + 1) <= total_task_cols)
                {
                    taskPQ.push(task_table.getTask((j + 1) / BETA_DIV_ALPHA, j + 1));  
                }
            }
        }
    
        Task *local_task = nullptr;
        if (wait_queue.try_pop(local_task)) 
        {
            int i = local_task->chunk_idx_i;
            int j = local_task->chunk_idx_j;
            if (dependency_table.getDependency(i, j - 1))
            {
                taskPQ.push(local_task);
            }
            else
            {
                wait_queue.push(local_task);
            }
        }

        if (dependency_table.getDependency(total_task_rows - 1, BETA_DIV_ALPHA * (total_task_rows - 1)))
        {
            break;
        }
    }

    return nullptr;
}

int main(int argc, char *argv[])
{
    //std::cout << "[1]. Inside main." << std::endl;

    if (argc < 2)
    {
        std::cerr << "Usage: " << argv[0] << " <filename>" << std::endl;
        return EXIT_FAILURE;
    }

    matrix_t<double> data_matrix(argv[1]);

    int total_task_rows = std::ceil(data_matrix.rows() / BETA);
    int total_task_cols = std::ceil(data_matrix.rows() / ALPHA);

    global_up_array.resize(data_matrix.rows(), 0.0);
    global_b_array.resize(data_matrix.rows(), 0.0);

    dependency_table.init(total_task_rows, total_task_cols);
    task_table.init(total_task_rows, total_task_cols, ALPHA, BETA, data_matrix);
    //task_table.printTaskTable();

    std::vector<pthread_t> threads(NUM_THREADS);
    std::vector<thread_args_ts> thread_args(NUM_THREADS);

    // for(int i = 0 ; i<task_table.rows() ; i++)
    // {
    //     for(int j = 0 ; j<task_table.cols();j++)
    //     {
    //         if(task_table.getTask(i, j) !=nullptr)
    //         flat_graph.push_back(task_table.getTask(i, j));
    //     }
    // }

    // std::cout<<flat_graph.size()<<" "<<task_table.rows()<<" "<<task_table.cols()<<std::endl;
    // std::sort(flat_graph.begin(),flat_graph.end(),comparator);

    for (int i = 0; i < NUM_THREADS; i++)
    {
        thread_args[i].tid = i;
        thread_args[i].total_task_rows = total_task_rows;
        thread_args[i].total_task_cols = total_task_cols;
        thread_args[i].m = data_matrix.rows();
        thread_args[i].n = data_matrix.cols();
        thread_args[i].mat = data_matrix.data_ptr();
    }

    //taskPQ = taskpq_init(7);
    //taskpq_insert(taskPQ, task_table.getTask(0, 0), total_task_rows, total_task_cols);
    // for(int i = 0 ; i<flat_graph.size() ; i++)
    // taskPQ.push(flat_graph[i]);
    taskPQ.push(task_table.getTask(0, 0));

    auto start = std::chrono::high_resolution_clock::now();

    for (int i = 0; i < NUM_THREADS; i++)
    {
        pthread_create(&threads[i], NULL, thdwork, &thread_args[i]);
    }

    for (int i = 0; i < NUM_THREADS; i++)
    {
        pthread_join(threads[i], NULL);
    }
 
    auto end = std::chrono::high_resolution_clock::now();

    auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();

    std::cout << "Time taken: " << elapsed << " ms" << std::endl;
    //dependency_table.printDependencyTable();
    //data_matrix.save("output_intel.txt");

    return 0;
}
