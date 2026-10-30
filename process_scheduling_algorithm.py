
import random
import re

try:
    import matplotlib.pyplot as plt
    # 中文字体配置，避免图表中文乱码
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun"]
    plt.rcParams["axes.unicode_minus"] = False
    HAVE_MPL = True
except Exception:
    HAVE_MPL = False


class Process:
    """进程控制块"""
    def __init__(self, name, arrival_time, service_time):
        self.name = name                  # 进程名（不能重复）
        self.arrival_time = arrival_time  # 创建时间 / 到达时间
        self.service_time = service_time  # 执行时间 / 服务时间


class Result:
    """调度结果（每个进程一行）"""
    def __init__(self, p, start):
        self.name = p.name
        self.arrival = p.arrival_time
        self.service = p.service_time
        self.start = start
        self.finish = start + p.service_time
        self.turnaround = self.finish - self.arrival        # 周转时间
        self.weighted = self.turnaround / self.service      # 带权周转时间


# ---------- 辅助函数 ----------

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


ALGO_NAMES = {
    "FCFS": "先来先服务 FCFS",
    "SJF": "最短作业优先 SJF（非抢占式）",
    "SRTF": "最短剩余时间优先 SRTF（SJF 抢占式）",
    "HRRN": "最高响应比优先 HRRN",
}


def name_num(name):
    """从进程名中提取数字部分，用于按 P1、P2、P3……从小到大排序"""
    m = re.search(r"(\d+)", name)
    return int(m.group(1)) if m else float("inf")


def better_than(a, b, ai, bi, t, algo):
    """判断在“当前时刻 t”下，进程 a 是否应优先于进程 b 被调度"""
    if algo == "SJF":
        if a.service_time != b.service_time:
            return a.service_time < b.service_time  # 执行时间短的优先
    elif algo == "HRRN":
        # 响应比 = (等待时间 + 执行时间) / 执行时间
        ra = (t - a.arrival_time + a.service_time) / a.service_time
        rb = (t - b.arrival_time + b.service_time) / b.service_time
        if ra != rb:
            return ra > rb  # 响应比高的优先
    # 平局时：先到达的优先；仍相同则按创建顺序
    if a.arrival_time != b.arrival_time:
        return a.arrival_time < b.arrival_time
    return ai < bi


def schedule_fcfs(procs):
    """先来先服务：按到达时间排序依次执行"""
    order = sorted(range(len(procs)), key=lambda i: (procs[i].arrival_time, i))
    res = []
    t = 0
    for i in order:
        if t < procs[i].arrival_time:
            t = procs[i].arrival_time  # 空闲则推进到下一个到达时刻
        res.append(Result(procs[i], t))
        t = res[-1].finish
    return res


def schedule(procs, algo):
    """SJF / HRRN：每一时刻在“已到达且未完成”的进程中挑选最优者"""
    n = len(procs)
    done = [False] * n
    res = []
    t, finished = 0, 0

    while finished < n:
        best = None
        for i in range(n):
            if done[i] or procs[i].arrival_time > t:
                continue  # 未到达的进程不能调度
            if best is None or better_than(procs[i], procs[best], i, best, t, algo):
                best = i

        if best is None:
            # 当前没有已到达进程，时间推进到最近的一个到达时刻
            t = min(procs[i].arrival_time for i in range(n) if not done[i])
            continue

        done[best] = True
        finished += 1
        res.append(Result(procs[best], t))
        t = res[-1].finish
    return res


def schedule_srtf(procs):
    """抢占式 SJF（SRTF，最短剩余时间优先）。
    返回 (segments, results)：
      segments - [(进程名, 开始时刻, 结束时刻), ...]，每个连续执行段一条，
                 相邻同进程段已合并；
      results  - 每个进程一行汇总（周转/带权周转按“最后完成-到达”计算）。
    """
    n = len(procs)
    remaining = [p.service_time for p in procs]
    done = [False] * n
    first_start = [None] * n
    last_finish = [0] * n
    segments = []  # (name, start, finish)
    t, finished = 0, 0

    def srtf_better(i, j):
        """剩余时间短者优先；相同则先到达者优先；再相同按创建顺序"""
        if remaining[i] != remaining[j]:
            return remaining[i] < remaining[j]
        if procs[i].arrival_time != procs[j].arrival_time:
            return procs[i].arrival_time < procs[j].arrival_time
        return i < j

    while finished < n:
        # 1. 在当前时刻已到达且未完成的进程中，选剩余时间最短者
        best = None
        for i in range(n):
            if done[i] or procs[i].arrival_time > t:
                continue
            if best is None or srtf_better(i, best):
                best = i

        # 2. 没有可用进程：推进到最近的到达时刻
        if best is None:
            t = min(procs[i].arrival_time for i in range(n) if not done[i])
            continue

        # 3. 计算本次最多能连续运行到何时（可能中途被新到达的进程抢占）
        next_arrival = None
        for i in range(n):
            if not done[i] and procs[i].arrival_time > t:
                if next_arrival is None or procs[i].arrival_time < next_arrival:
                    next_arrival = procs[i].arrival_time

        run_end = t + remaining[best]
        # 如果完成之前有新进程到达，则先运行到该到达时刻再重新决策
        stop_at = run_end if next_arrival is None else min(run_end, next_arrival)

        if first_start[best] is None:
            first_start[best] = t
        segments.append((procs[best].name, t, stop_at))
        remaining[best] -= stop_at - t
        t = stop_at

        # 4. 若已运行完，标记完成；否则回到循环顶部重新挑选（可能被抢占）
        if remaining[best] == 0:
            done[best] = True
            last_finish[best] = t
            finished += 1

    # 合并相邻的同一进程段，使甘特图与文字输出更整洁
    merged = []
    for name, s, f in segments:
        if merged and merged[-1][0] == name and merged[-1][2] == s:
            merged[-1] = (name, merged[-1][1], f)
        else:
            merged.append((name, s, f))
    segments = merged

    results = []
    for i in range(n):
        r = Result(procs[i], first_start[i] if first_start[i] is not None
                   else procs[i].arrival_time)
        r.finish = last_finish[i]
        r.turnaround = r.finish - r.arrival
        r.weighted = r.turnaround / r.service
        results.append(r)

    return segments, results


# ---------- 输出 ----------

def avg_turnaround(res):
    return sum(r.turnaround for r in res) / len(res)


def avg_weighted(res):
    return sum(r.weighted for r in res) / len(res)


def print_schedule(algo, res, segments=None):
    """输出某一算法的完整调度过程。
    segments 仅用于抢占式算法：[(进程名, 开始, 结束), ...]
    """
    print("\n" + "=" * 50)
    print(f"调度算法：{ALGO_NAMES[algo]}")
    print("-" * 50)

    print("调度过程：")
    if segments:
        for name, s, f in segments:
            print(f"  时刻 {s:>3} 调度 {name}，运行至时刻 {f}")
        print("调度顺序：" + " -> ".join(name for name, _, _ in segments))
    else:
        for r in res:
            print(f"  时刻 {r.start:>3} 调度 {r.name}（到达 {r.arrival}，执行 {r.service}），运行至时刻 {r.finish}")
        print("调度顺序：" + " -> ".join(r.name for r in res))

    print("-" * 50)
    print(f"{'进程名':<8}{'到达':>6}{'执行':>6}{'开始':>6}{'完成':>6}{'周转':>8}{'带权周转':>10}")
    for r in res:
        print(f"{r.name:<8}{r.arrival:>6}{r.service:>6}{r.start:>6}{r.finish:>6}"
              f"{r.turnaround:>8}{r.weighted:>10.3f}")

    print("-" * 50)
    print(f"平均周转时间     = {avg_turnaround(res):.3f}")
    print(f"平均带权周转时间 = {avg_weighted(res):.3f}")


def print_comparison(data):
    """输出多种算法的优劣总结"""
    print("\n" + "=" * 50)
    print("算法优劣总结：")
    print("  FCFS：实现简单、公平，但可能出现长作业阻塞短作业的“护送效应”。")
    print("  SJF（非抢占）：平均周转时间通常较小，但长作业可能长期得不到服务（饥饿）。")
    print("  SRTF（SJF 抢占）：只要出现更短作业就抢占，平均周转时间通常最小。")
    print("  HRRN：兼顾作业长短，响应比高的优先，既提高吞吐率又不致长作业饥饿。")


# ---------- 可视化 ----------

def plot_schedules(procs, r_fcfs, r_sjf, r_srtf, r_hrrn, srtf_segments):
    """用 matplotlib 绘制甘特图与两个结果表格"""
    if not HAVE_MPL:
        print("\n[提示] 未安装 matplotlib，无法绘图。可执行：pip install matplotlib")
        return

    # 每种算法对应一组连续执行段：(进程名, 开始, 结束)
    algo_items = [
        ("FCFS 先来先服务", [(r.name, r.start, r.finish) for r in r_fcfs]),
        ("SJF 非抢占式", [(r.name, r.start, r.finish) for r in r_sjf]),
        ("SRTF 抢占式(SJF)", list(srtf_segments)),
        ("HRRN 最高响应比优先", [(r.name, r.start, r.finish) for r in r_hrrn]),
    ]

    # 为每个进程分配固定颜色，保证所有算法里同一进程颜色一致
    # 进程顺序按进程名中的数字从小到大（与表格一致）
    order_map = {p.name: i for i, p in enumerate(procs)}
    names = []
    for _, segs in algo_items:
        for name, _, _ in segs:
            if name not in names:
                names.append(name)
    names.sort(key=lambda n: (name_num(n), order_map[n]))
    colors = {name: plt.get_cmap("tab10")(i % 10) for i, name in enumerate(names)}

    fig = plt.figure(figsize=(15, 12))
    gs = fig.add_gridspec(3, 1, height_ratios=[1.2, 0.5, 0.9], hspace=0.4)
    ax_gantt = fig.add_subplot(gs[0])
    ax_info = fig.add_subplot(gs[1])
    ax_result = fig.add_subplot(gs[2])
    fig.suptitle("进程调度算法可视化", fontsize=15, fontweight="bold")

    # ---- 第 1 部分：甘特图（每种算法一行）----
    n_algos = len(algo_items)
    for idx, (label, segs) in enumerate(algo_items):
        y = n_algos - 1 - idx  # 最上面是 FCFS（y 最大）
        for name, s, f in segs:
            ax_gantt.barh(y, f - s, left=s, height=0.55,
                          color=colors[name], edgecolor="black", linewidth=0.8)
            # 段足够宽时才在中间标进程名，避免抢占产生的小段文字重叠
            if f - s >= 0.8:
                ax_gantt.text((s + f) / 2, y, name, ha="center", va="center",
                              color="white", fontsize=10, fontweight="bold")

    ax_gantt.set_yticks(range(n_algos))
    ax_gantt.set_yticklabels([label for label, _ in reversed(algo_items)])
    ax_gantt.set_xlabel("时间")
    ax_gantt.set_xlim(0, max(r.finish for r in r_fcfs + r_sjf + r_srtf + r_hrrn))
    ax_gantt.grid(axis="x", linestyle="--", alpha=0.4)
    ax_gantt.set_title("调度过程甘特图（条块上为进程名，条块间空隙为等待/空闲）")

    handles = [plt.Rectangle((0, 0), 1, 1, color=colors[n]) for n in names]
    ax_gantt.legend(handles, names, loc="upper left", bbox_to_anchor=(1.01, 1),
                    title="进程", fontsize=9)

    def style_table(t):
        """统一表格样式：表头蓝底白字"""
        t.auto_set_font_size(False)
        t.set_fontsize(9)
        t.scale(1, 1.7)
        for (i, j), cell in t.get_celld().items():
            if i == 0:
                cell.set_facecolor("#4472C4")
                cell.set_text_props(color="white", fontweight="bold")

    # ---- 第 2 部分：进程基本信息表（到达时间、执行时间）----
    # 表格中进程按进程名中的数字从小到大排列（P1、P2、P3……）
    ordered = sorted(procs, key=lambda p: (name_num(p.name), order_map[p.name]))

    info_labels = ["进程", "到达时间", "执行时间"]
    info_cells = [[p.name, str(p.arrival_time), str(p.service_time)] for p in ordered]

    ax_info.axis("off")
    t_info = ax_info.table(cellText=info_cells, colLabels=info_labels,
                           cellLoc="center", loc="center")
    style_table(t_info)

    # ---- 第 3 部分：各算法周转时间与带权周转时间表 ----
    d_fcfs = {r.name: r for r in r_fcfs}
    d_sjf = {r.name: r for r in r_sjf}
    d_srtf = {r.name: r for r in r_srtf}
    d_hrrn = {r.name: r for r in r_hrrn}

    result_labels = ["进程",
                     "FCFS 周转", "FCFS 带权",
                     "SJF 周转", "SJF 带权",
                     "SRTF 周转", "SRTF 带权",
                     "HRRN 周转", "HRRN 带权"]
    result_cells = []
    for p in ordered:
        r1 = d_fcfs[p.name]
        r2 = d_sjf[p.name]
        r3 = d_srtf[p.name]
        r4 = d_hrrn[p.name]
        result_cells.append([
            p.name,
            str(r1.turnaround), f"{r1.weighted:.3f}",
            str(r2.turnaround), f"{r2.weighted:.3f}",
            str(r3.turnaround), f"{r3.weighted:.3f}",
            str(r4.turnaround), f"{r4.weighted:.3f}",
        ])

    ax_result.axis("off")
    ax_result.set_title("各进程在不同算法下的周转时间与带权周转时间")
    t_result = ax_result.table(cellText=result_cells, colLabels=result_labels,
                               cellLoc="center", loc="center")
    style_table(t_result)

    plt.show()
    plt.close(fig)


# ---------- 创建进程 ----------

def create_manual():
    """手动创建"""
    n = read_int("请输入进程数量：", 1)
    procs = []
    names = set()
    for i in range(n):
        print(f"\n第 {i + 1} 个进程：")
        while True:
            name = input("  进程名（不能重复）：").strip()
            if name and name not in names:
                break
            print("  该进程名已存在，请重新输入！")
        names.add(name)
        arrival = read_int("  创建时间（到达时间）：", 0)
        service = read_int("  执行时间：", 1)
        procs.append(Process(name, arrival, service))
    return procs


def create_random():
    """随机创建"""
    n = read_int("请输入进程数量：", 1)
    max_arrival = read_int("请输入最大到达时间：", 0)
    max_service = read_int("请输入最大执行时间：", 1)
    procs = []
    for i in range(1, n + 1):
        procs.append(Process(f"P{i}",            # 自动保证不重复
                             random.randint(0, max_arrival),
                             random.randint(1, max_service)))
    return procs


def print_processes(procs):
    """打印输入进程表"""
    print("\n" + "-" * 20 + " 进程信息 " + "-" * 20)
    print(f"{'进程名':<8}{'到达时间':>10}{'执行时间':>10}")
    for p in procs:
        print(f"{p.name:<8}{p.arrival_time:>10}{p.service_time:>10}")
    print("-" * 46)


# ---------- 主函数 ----------

def main():
    print("=" * 20 + " 进程调度算法实验 " + "=" * 20)
    print("  1 - 先来先服务 FCFS")
    print("  2 - 最短作业优先 SJF（非抢占式）")
    print("  3 - 最短剩余时间优先 SRTF（SJF 抢占式）")
    print("  4 - 最高响应比优先 HRRN")
    print("=" * 60)

    while True:
        print("\n请选择进程创建方式：")
        print("  1 - 手动创建进程")
        print("  2 - 随机创建进程")
        print("  0 - 退出")
        try:
            mode = int(input("请输入选择："))
        except ValueError:
            print("输入无效，请重新选择！")
            continue

        if mode == 0:
            break
        if mode not in (1, 2):
            print("输入无效，请重新选择！")
            continue

        procs = create_manual() if mode == 1 else create_random()

        # 分别用四种算法调度
        r_fcfs = schedule_fcfs(procs)
        r_sjf = schedule(procs, "SJF")                 # 非抢占式 SJF
        srtf_segments, r_srtf = schedule_srtf(procs)   # 抢占式 SJF
        r_hrrn = schedule(procs, "HRRN")

        # 输出四种算法的调度过程与各进程执行信息
        print_schedule("FCFS", r_fcfs)
        print_schedule("SJF", r_sjf)
        print_schedule("SRTF", r_srtf, segments=srtf_segments)
        print_schedule("HRRN", r_hrrn)

        # 算法优劣总结
        print_comparison({"FCFS": r_fcfs, "SJF": r_sjf,
                          "SRTF": r_srtf, "HRRN": r_hrrn})

        # 绘图直观展示
        plot_schedules(procs, r_fcfs, r_sjf, r_srtf, r_hrrn, srtf_segments)

    print("程序结束。")


if __name__ == "__main__":
    main()
