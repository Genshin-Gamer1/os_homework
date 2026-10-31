/* 实验一：进程同步 —— 生产者-消费者问题（Windows API 版，可交互配置）
 * 文件必须保存为 UTF-8 带 BOM，否则 MSVC 会报 C4819 / C2001 / C2143
 */
#define _CRT_SECURE_NO_WARNINGS

#include <stdio.h>
#include <stdlib.h>
#include <windows.h>

static int BUFFER_SIZE      = 10;
static int PRODUCER_COUNT   = 1;
static int CONSUMER_COUNT   = 1;
static int OPERATION_COUNT  = 10;
static int SIMULATION_SPEED = 100;

static int *buffer = NULL;
static int  in_pos = 0;
static int  out_pos = 0;
static int  produced_count = 0;
static int  consumed_count = 0;

static HANDLE hEmpty;
static HANDLE hFull;
static HANDLE hMutex;

static void fix_console_codepage(void)
{
    /* 探测编译器把中文字面量编成了 UTF-8(3字节) 还是 GBK(2字节)，让控制台保持一致 */
    const char *probe = "生";
    if (probe[2] != '\0') {
        SetConsoleOutputCP(CP_UTF8);
    } else {
        SetConsoleOutputCP(936);
    }
}

static int read_int(const char *prompt, int def)
{
    char line[64];
    int  value = 0;

    printf("%s", prompt);
    fflush(stdout);
    if (fgets(line, sizeof(line), stdin) == NULL) {
        printf("%d\n", def);
        return def;
    }
    if (sscanf(line, "%d", &value) != 1 || value <= 0) {
        return def;
    }
    return value;
}

static void get_user_input(void)
{
    printf("=== 生产者-消费者问题配置 ===\n");
    BUFFER_SIZE      = read_int("请输入缓冲区大小(默认10): ", 10);
    PRODUCER_COUNT   = read_int("请输入生产者数量(默认1): ", 1);
    CONSUMER_COUNT   = read_int("请输入消费者数量(默认1): ", 1);
    OPERATION_COUNT  = read_int("请输入每个线程操作次数(默认10): ", 10);
    SIMULATION_SPEED = read_int("请输入模拟速度(ms)(默认100): ", 100);

    printf("\n=== 配置总结 ===\n");
    printf("缓冲区大小: %d\n", BUFFER_SIZE);
    printf("生产者数量: %d\n", PRODUCER_COUNT);
    printf("消费者数量: %d\n", CONSUMER_COUNT);
    printf("操作次数: %d\n", OPERATION_COUNT);
    printf("模拟速度: %dms\n", SIMULATION_SPEED);
    printf("====================\n\n");
}

static char *alloc_text(void)
{
    return (char *)malloc((size_t)BUFFER_SIZE * 12 + 256);
}

static void make_buffer_text(char *dst)
{
    char *p = dst;
    int   i;

    p += sprintf(p, "缓冲区[%d]: [", BUFFER_SIZE);
    for (i = 0; i < BUFFER_SIZE; ++i) {
        if (i > 0) {
            p += sprintf(p, ", ");
        }
        if (buffer[i] == 0) {
            p += sprintf(p, "空");
        } else {
            p += sprintf(p, "%d", buffer[i]);
        }
    }
    sprintf(p, "] in=%d, out=%d 生产: %d, 消费: %d",
            in_pos, out_pos, produced_count, consumed_count);
}

DWORD WINAPI producer(LPVOID arg)
{
    int   producer_id = *(int *)arg;
    int   base_id = producer_id * 1000;
    char *text = alloc_text();
    int   i;

    if (text == NULL) {
        return 1;
    }

    for (i = 0; i < OPERATION_COUNT; ++i) {
        int item = base_id + i + 1;
        int slot;

        WaitForSingleObject(hEmpty, INFINITE);   /* P(empty) */
        WaitForSingleObject(hMutex, INFINITE);   /* P(mutex) */

        slot = in_pos;
        buffer[slot] = item;
        in_pos = (in_pos + 1) % BUFFER_SIZE;
        ++produced_count;

        make_buffer_text(text);
        printf("生产者%d 生产: %d -> 位置[%d] %s\n", producer_id, item, slot, text);
        fflush(stdout);

        ReleaseMutex(hMutex);                    /* V(mutex) */
        ReleaseSemaphore(hFull, 1, NULL);        /* V(full)  */

        Sleep(SIMULATION_SPEED);
    }
    printf("生产者%d 完成!\n", producer_id);
    free(text);
    return 0;
}

DWORD WINAPI consumer(LPVOID arg)
{
    int   consumer_id = *(int *)arg;
    char *text = alloc_text();
    int   i;

    if (text == NULL) {
        return 1;
    }

    for (i = 0; i < OPERATION_COUNT; ++i) {
        int slot;
        int item;

        WaitForSingleObject(hFull, INFINITE);    /* P(full)  */
        WaitForSingleObject(hMutex, INFINITE);   /* P(mutex) */

        slot = out_pos;
        item = buffer[slot];
        buffer[slot] = 0;
        out_pos = (out_pos + 1) % BUFFER_SIZE;
        ++consumed_count;

        make_buffer_text(text);
        printf("消费者%d 消费: %d <- 位置[%d] %s\n", consumer_id, item, slot, text);
        fflush(stdout);

        ReleaseMutex(hMutex);                    /* V(mutex) */
        ReleaseSemaphore(hEmpty, 1, NULL);       /* V(empty) */

        Sleep(SIMULATION_SPEED);
    }
    printf("消费者%d 完成!\n", consumer_id);
    free(text);
    return 0;
}

int main(void)
{
    HANDLE *pthreads = NULL;
    HANDLE *cthreads = NULL;
    int    *pids     = NULL;
    int    *cids     = NULL;
    char   *text     = NULL;
    int     i;

    fix_console_codepage();
    get_user_input();

    printf("按回车键开始模拟...");
    fflush(stdout);
    getchar();

    buffer = (int *)malloc((size_t)BUFFER_SIZE * sizeof(int));
    text   = alloc_text();
    if (buffer == NULL || text == NULL) {
        fprintf(stderr, "内存分配失败\n");
        return 1;
    }
    for (i = 0; i < BUFFER_SIZE; ++i) {
        buffer[i] = 0;
    }

    hEmpty = CreateSemaphore(NULL, BUFFER_SIZE, BUFFER_SIZE, NULL);
    hFull  = CreateSemaphore(NULL, 0, BUFFER_SIZE, NULL);
    hMutex = CreateMutex(NULL, FALSE, NULL);
    if (hEmpty == NULL || hFull == NULL || hMutex == NULL) {
        fprintf(stderr, "创建同步对象失败，错误码 %lu\n", GetLastError());
        return 1;
    }

    pthreads = (HANDLE *)malloc((size_t)PRODUCER_COUNT * sizeof(HANDLE));
    cthreads = (HANDLE *)malloc((size_t)CONSUMER_COUNT * sizeof(HANDLE));
    pids     = (int *)malloc((size_t)PRODUCER_COUNT * sizeof(int));
    cids     = (int *)malloc((size_t)CONSUMER_COUNT * sizeof(int));
    if (pthreads == NULL || cthreads == NULL || pids == NULL || cids == NULL) {
        fprintf(stderr, "内存分配失败\n");
        return 1;
    }

    printf("\n=== 模拟开始 ===\n");
    make_buffer_text(text);
    printf("初始状态: %s\n", text);

    for (i = 0; i < PRODUCER_COUNT; ++i) {
        pids[i] = i + 1;
        pthreads[i] = CreateThread(NULL, 0, producer, &pids[i], 0, NULL);
        if (pthreads[i] == NULL) {
            fprintf(stderr, "创建生产者线程失败，错误码 %lu\n", GetLastError());
            return 1;
        }
    }

    for (i = 0; i < CONSUMER_COUNT; ++i) {
        cids[i] = i + 1;
        cthreads[i] = CreateThread(NULL, 0, consumer, &cids[i], 0, NULL);
        if (cthreads[i] == NULL) {
            fprintf(stderr, "创建消费者线程失败，错误码 %lu\n", GetLastError());
            return 1;
        }
    }

    WaitForMultipleObjects((DWORD)PRODUCER_COUNT, pthreads, TRUE, INFINITE);
    WaitForMultipleObjects((DWORD)CONSUMER_COUNT, cthreads, TRUE, INFINITE);

    printf("\n=== 模拟结束 ===\n");
    make_buffer_text(text);
    printf("最终状态: %s\n", text);
    printf("总计: 生产了%d个产品, 消费了%d个产品\n", produced_count, consumed_count);

    for (i = 0; i < PRODUCER_COUNT; ++i) {
        CloseHandle(pthreads[i]);
    }
    for (i = 0; i < CONSUMER_COUNT; ++i) {
        CloseHandle(cthreads[i]);
    }
    CloseHandle(hEmpty);
    CloseHandle(hFull);
    CloseHandle(hMutex);
    free(buffer);
    free(text);
    free(pthreads);
    free(cthreads);
    free(pids);
    free(cids);
    return 0;
}