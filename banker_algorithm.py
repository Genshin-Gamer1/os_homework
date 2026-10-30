# -*- coding: utf-8 -*-
"""
实验三：银行家算法模拟
实现：银行家算法（资源请求试分配） + 安全性算法（安全序列判定）
运行：python 银行家算法.py
"""

import random


def read_int(prompt, minimum):
    """读取一个不小于 minimum 的整数（带校验）"""
    while True:
        try:
            v = int(input(prompt))
        except ValueError:
            print("输入无效，请输入整数！")
            continue
        if v >= minimum:
            return v
        print(f"输入无效，请输入不小于 {minimum} 的整数！")


def read_vector(prompt, m):
    """读取长度为 m 的非负整数向量"""
    while True:
        parts = input(prompt).replace(",", " ").split()
        if len(parts) != m:
            print(f"请输入 {m} 个数据（用空格分隔）！")
            continue
        try:
            vec = [int(x) for x in parts]
        except ValueError:
            print("输入无效，请输入整数！")
            continue
        if any(v < 0 for v in vec):
            print("资源数量不能为负数！")
            continue
        return vec


def fmt(vec, width=3):
    """把向量格式化成对齐的字符串"""
    return " ".join(f"{v:>{width}}" for v in vec)


def pad(text, cols):
    """按终端显示宽度左对齐补空格（中文按 2 列计算），用于表格表头对齐"""
    w = sum(2 if ord(c) > 127 else 1 for c in text)
    return text + " " * max(0, cols - w)


class Banker:
    """银行家算法核心：维护系统状态并负责安全性检查与请求试分配"""

    def __init__(self, res_names, available, max_demand, allocation):
        self.res_names = res_names                  # 资源名称，如 ['A','B','C']
        self.m = len(res_names)                     # 资源种类数
        self.n = len(max_demand)                    # 进程数
        self.available = list(available)            # 可用资源向量 Available
        self.max = [list(r) for r in max_demand]    # 最大需求矩阵 Max
        self.allocation = [list(r) for r in allocation]   # 分配矩阵 Allocation
        self.need = [[self.max[i][j] - self.allocation[i][j]
                      for j in range(self.m)] for i in range(self.n)]  # Need = Max - Allocation

    # ---------- 输出 ----------

    def print_state(self, title="当前系统状态"):
        """打印 T0 时刻的系统状态表"""
        print("\n" + "-" * 68)
        print(title)
        print("-" * 68)
        head = pad("进程", 6)
        for name in ("Max", "Allocation", "Need"):
            head += name.center(18)
        print(head)
        block = " ".join(f"{name:>4}" for name in self.res_names).ljust(18)
        print(" " * 6 + block * 3)
        for i in range(self.n):
            print(pad(f"P{i}", 6)
                  + f"{fmt(self.max[i], 4):<18}"
                  + f"{fmt(self.allocation[i], 4):<18}"
                  + f"{fmt(self.need[i], 4):<18}")
        print("-" * 68)
        avail = "  ".join(f"{self.res_names[j]}={self.available[j]}"
                          for j in range(self.m))
        print(f"Available：{avail}")

    # ---------- 安全性算法 ----------

    def is_safe(self, verbose=True):
        """安全性算法。返回 (是否安全, 安全序列)"""
        work = list(self.available)          # 工作向量 Work 初值 = Available
        finish = [False] * self.n            # Finish 全部置 false
        sequence = []                        # 安全序列

        if verbose:
            print("\n安全性检查过程：")
            print("-" * 82)
            print(pad("步骤", 6) + pad("进程", 6) + pad("Work", 15)
                  + pad("Need", 15) + pad("Allocation", 15)
                  + pad("Work+Alloc", 15) + "Finish")
            print("-" * 82)

        step = 0
        while len(sequence) < self.n:
            found = False
            for i in range(self.n):
                if finish[i]:
                    continue
                # Need[i] <= Work 才能满足该进程
                if all(self.need[i][j] <= work[j] for j in range(self.m)):
                    step += 1
                    old_work = list(work)
                    work = [work[j] + self.allocation[i][j] for j in range(self.m)]
                    finish[i] = True
                    sequence.append(i)
                    found = True
                    if verbose:
                        print(pad(str(step), 6) + pad(f"P{i}", 6)
                              + pad(fmt(old_work, 4), 15)
                              + pad(fmt(self.need[i], 4), 15)
                              + pad(fmt(self.allocation[i], 4), 15)
                              + pad(fmt(work, 4), 15) + "true")
                    break   # 每轮找到一个就重新从头扫描（可得到一条安全序列）
            if not found:
                break   # 找不到可满足的进程，系统不安全

        safe = all(finish)
        if verbose:
            print("-" * 82)
            if safe:
                print("检查结果：系统安全，安全序列为 "
                      + " -> ".join(f"P{i}" for i in sequence))
            else:
                unfinished = [f"P{i}" for i in range(self.n) if not finish[i]]
                print("检查结果：系统不安全！无法满足以下进程的剩余需求："
                      + "、".join(unfinished))
        return safe, sequence if safe else []

    # ---------- 银行家算法 ----------

    def request(self, pid, req):
        """银行家算法：对进程 pid 的请求向量 req 做检查与试分配。
        返回 True 表示已分配，False 表示拒绝分配（进程需等待）。"""
        print("\n" + "=" * 62)
        print(f"进程 P{pid} 提出资源请求：Request = ({fmt(req)})")
        print("=" * 62)

        # 步骤 1：Request <= Need ?
        ok1 = all(req[j] <= self.need[pid][j] for j in range(self.m))
        print(f"1) Request({fmt(req)}) ≤ Need({fmt(self.need[pid])}) ? "
              f"{'是' if ok1 else '否'}")
        if not ok1:
            print("   请求量超过该进程声明的最大需求，属于非法请求，拒绝分配！")
            return False

        # 步骤 2：Request <= Available ?
        ok2 = all(req[j] <= self.available[j] for j in range(self.m))
        print(f"2) Request({fmt(req)}) ≤ Available({fmt(self.available)}) ? "
              f"{'是' if ok2 else '否'}")
        if not ok2:
            print(f"   可用资源不足，进程 P{pid} 必须等待。")
            return False

        # 步骤 3：试分配，然后做安全性检查
        print("3) 试探性分配资源，修改系统状态：")
        self.available = [self.available[j] - req[j] for j in range(self.m)]
        self.allocation[pid] = [self.allocation[pid][j] + req[j]
                                for j in range(self.m)]
        self.need[pid] = [self.need[pid][j] - req[j] for j in range(self.m)]
        print(f"   Available 变为 ({fmt(self.available)})")
        print(f"   Allocation[P{pid}] 变为 ({fmt(self.allocation[pid])})")
        print(f"   Need[P{pid}] 变为 ({fmt(self.need[pid])})")

        safe, sequence = self.is_safe(verbose=True)

        if safe:
            print("\n结论：试分配后系统仍安全，可以分配资源！")
            print("分配后系统状态：")
            self.print_state("分配后的系统状态")
            return True

        # 不安全：回滚（恢复原来的状态）
        print("\n结论：试分配后系统将进入不安全状态，本次分配作废，"
              "进程 P{} 必须等待。".format(pid))
        self.available = [self.available[j] + req[j] for j in range(self.m)]
        self.allocation[pid] = [self.allocation[pid][j] - req[j]
                                for j in range(self.m)]
        self.need[pid] = [self.need[pid][j] + req[j] for j in range(self.m)]
        print("已恢复分配前的系统状态。")
        return False


# ---------- 数据输入 ----------

def build_manual():
    """手动输入系统状态"""
    n = read_int("请输入进程数：", 1)
    m = read_int("请输入资源种类数：", 1)
    names = [chr(ord("A") + j) for j in range(m)]

    print(f"\n请依次输入总资源数（{m} 个，用空格分隔）：")
    total = read_vector("Total = ", m)

    print("\n请依次输入各进程的最大需求矩阵 Max（每行一个进程）：")
    max_demand = []
    for i in range(n):
        row = read_vector(f"  P{i} 的 Max：", m)
        max_demand.append(row)

    print("\n请依次输入各进程的已分配矩阵 Allocation（每行一个进程）：")
    allocation = []
    for i in range(n):
        while True:
            row = read_vector(f"  P{i} 的 Allocation：", m)
            if any(row[j] > max_demand[i][j] for j in range(m)):
                print("  已分配资源不能超过该进程的最大需求，请重新输入！")
                continue
            allocation.append(row)
            break

    # Available = Total - 各进程已分配之和
    available = [total[j] - sum(allocation[i][j] for i in range(n))
                 for j in range(m)]
    if any(a < 0 for a in available):
        print("\n[警告] 已分配资源之和超过总资源数，数据不合法！")
        return None
    return names, available, max_demand, allocation


def build_example():
    """教材 P120 的经典示例（T0 时刻）"""
    names = ["A", "B", "C"]
    available = [3, 3, 2]
    max_demand = [[7, 5, 3],
                  [3, 2, 2],
                  [9, 0, 2],
                  [2, 2, 2],
                  [4, 3, 3]]
    allocation = [[0, 1, 0],
                  [2, 0, 0],
                  [3, 0, 2],
                  [2, 1, 1],
                  [0, 0, 2]]
    return names, available, max_demand, allocation


def build_random():
    """随机生成一个合法的系统状态"""
    n = read_int("请输入进程数：", 1)
    m = read_int("请输入资源种类数：", 1)
    names = [chr(ord("A") + j) for j in range(m)]

    print(f"\n请依次输入每种资源的总数量（{m} 个，用空格分隔）：")
    total = read_vector("Total = ", m)

    max_demand, allocation = [], []
    for i in range(n):
        alloc_row, max_row = [], []
        for j in range(m):
            # 每个进程最多拿走总资源的 1/n，保证不至于超额
            limit = max(0, total[j] // n)
            a = random.randint(0, limit)
            alloc_row.append(a)
            max_row.append(a + random.randint(0, max(0, limit - a) + 2))
        allocation.append(alloc_row)
        max_demand.append(max_row)

    available = [total[j] - sum(allocation[i][j] for i in range(n))
                 for j in range(m)]
    available = [max(0, a) for a in available]
    return names, available, max_demand, allocation


# ---------- 主函数 ----------

def main():
    print("=" * 20 + " 银行家算法模拟 " + "=" * 20)
    print("  1 - 手动输入系统状态")
    print("  2 - 使用教材示例（P120）")
    print("  3 - 随机生成系统状态")
    print("  0 - 退出")
    print("=" * 60)

    while True:
        try:
            mode = int(input("\n请选择："))
        except ValueError:
            print("输入无效，请重新选择！")
            continue
        if mode == 0:
            print("程序结束。")
            break
        if mode not in (1, 2, 3):
            print("输入无效，请重新选择！")
            continue

        data = (build_manual() if mode == 1
                else build_example() if mode == 2
                else build_random())
        if data is None:
            continue

        names, available, max_demand, allocation = data
        banker = Banker(names, available, max_demand, allocation)
        banker.print_state("T0 时刻系统状态")

        # 先做一次初始安全性检查
        safe, sequence = banker.is_safe(verbose=True)
        if not safe:
            print("\n[提示] 初始状态本身就不安全，后续分配均无意义。")
            continue

        # 循环处理资源请求
        while True:
            cmd = input("\n请输入提出请求的进程号（0~{}），输入 q 退出本次："
                        .format(banker.n - 1)).strip()
            if cmd.lower() == "q":
                break
            try:
                pid = int(cmd)
            except ValueError:
                print("输入无效！")
                continue
            if not (0 <= pid < banker.n):
                print(f"进程号必须在 0~{banker.n - 1} 之间！")
                continue

            req = read_vector(
                f"请输入 P{pid} 的请求向量（{banker.m} 个，用空格分隔）：",
                banker.m)
            banker.request(pid, req)


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\n程序结束。")
