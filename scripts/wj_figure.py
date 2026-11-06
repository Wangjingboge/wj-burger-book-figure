# -*- coding: utf-8 -*-
"""望京博格书籍配图 —— 统一版式生成器

用法：
    python wj_figure.py --config my_config.json

只负责「版式」，不负责算数据。所有数字必须先从 Wind / 用户处取到，
写进 config 的 series.points 里。输出：
    1) 透明底 PNG（正式交付）
    2) 同名 _白底预览.png（校对用，深色界面下才看得清）
"""
import argparse
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib import font_manager as fm

# ---------------------------------------------------------------- 样式常量
INK = "#111111"      # 主线条、主文字
BODY = "#2b2b2b"     # 轴标签、刻度
MUTED = "#4f4f4f"    # 次要说明
GRID = "#c9c9c9"     # 网格点线
DPI = 120

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\STSONG.TTF",                       # 华文宋体（首选）
    r"C:\Windows\Fonts\simsun.ttc",                       # 中易宋体
    "/System/Library/Fonts/Supplemental/Songti.ttc",      # macOS 宋体
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
]

RATIO = {
    "4:3": dict(figsize=(12, 9), rect=[0.083, 0.150, 0.834, 0.725],
                title_y=0.950, legend_default="in",
                legend_anchor=[0.083, 0.126]),
    "3:4": dict(figsize=(9, 12), rect=[0.150, 0.302, 0.798, 0.550],
                title_y=0.952, legend_default="out-bottom",
                legend_anchor=[0.150, 0.214]),
}

LINE_STYLE = {
    "solid": dict(lw=1.8, ls="-"),
    "dashed": dict(lw=1.5, ls=(0, (5, 2.5))),
    "dotted": dict(lw=1.5, ls=(0, (1.6, 2.2))),
}


def pick_font():
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            fm.fontManager.addfont(p)
            return fm.FontProperties(fname=p).get_name()
    sys.exit("找不到可用的中文衬线字体，请在 FONT_CANDIDATES 里补一个字体路径。")


def setup(font_name, ratio):
    plt.rcParams["font.family"] = font_name
    plt.rcParams["axes.unicode_minus"] = False
    geo = RATIO[ratio]
    fig = plt.figure(figsize=geo["figsize"], dpi=DPI)
    return fig, geo


def draw(cfg, out_dir):
    ratio = cfg.get("ratio", "4:3")
    FS = int(cfg.get("font_size", 17))
    font_name = pick_font()
    fig, geo = setup(font_name, ratio)

    # ---------- 标题（居中加粗；不用字号区分层级） ----------
    title = cfg.get("title", "")
    if title:
        fig.text(0.5, geo["title_y"], title, fontsize=FS, color=INK,
                 ha="center", va="top",
                 path_effects=[pe.withStroke(linewidth=0.95, foreground=INK)])

    sub = cfg.get("subtitle")
    if sub:
        fig.text(0.5, geo["title_y"] - 0.045, sub, fontsize=FS, color=MUTED,
                 ha="center", va="top")

    ax = fig.add_axes(cfg.get("rect") or geo["rect"])
    ax.set_facecolor("none")

    xcfg = cfg.get("x", {})
    ycfg = cfg.get("y", {})
    ax.set_xlim(*xcfg.get("lim", [0, 1]))
    ax.set_ylim(*ycfg.get("lim", [0, 1]))

    if xcfg.get("ticks"):
        ax.set_xticks(xcfg["ticks"])
        labels = xcfg.get("tick_labels") or [str(t) for t in xcfg["ticks"]]
        ax.set_xticklabels(labels)
    if ycfg.get("ticks"):
        ax.set_yticks(ycfg["ticks"])

    ax.tick_params(axis="both", direction="in", length=5.5, width=1.0,
                   color=INK, labelsize=FS, pad=8)
    for lab in ax.get_xticklabels() + ax.get_yticklabels():
        lab.set_color(BODY)

    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_linewidth(1.2)
        ax.spines[s].set_color(INK)

    ax.set_axisbelow(True)
    ax.yaxis.grid(True, linestyle=(0, (1, 4)), linewidth=0.8, color=GRID)

    if ycfg.get("label"):
        ax.set_ylabel(ycfg["label"], fontsize=FS, color=BODY, labelpad=16)
    if xcfg.get("label"):
        ax.set_xlabel(xcfg["label"], fontsize=FS, color=BODY, labelpad=10)

    # ---------- 参考横线（成本线 / 目标线） ----------
    hline = cfg.get("hline")
    if hline:
        st = LINE_STYLE.get(hline.get("style", "dashed"), LINE_STYLE["dashed"])
        ax.axhline(hline["value"], color=INK, lw=st["lw"], linestyle=st["ls"],
                   zorder=3)

    # ---------- 曲线 ----------
    series = cfg.get("series", [])
    for s in series:
        pts = s["points"]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        st = LINE_STYLE.get(s.get("style", "solid"), LINE_STYLE["solid"])
        ax.plot(xs, ys, color=INK, lw=s.get("lw", st["lw"]), linestyle=st["ls"],
                solid_capstyle="round", zorder=4)
        # 端点标记：ends（仅首末）| all（每个点）| none
        mk = s.get("markers", "ends")
        if mk == "all":
            idx = list(range(len(xs)))
        elif mk == "ends":
            idx = [0, -1] if len(xs) > 1 else [0]
        else:
            idx = []
        fill = s.get("marker_fill")
        for i in idx:
            if fill == "hollow":
                fc = "white"
            elif fill == "solid":
                fc = INK
            else:
                fc = "white" if (mk == "ends" and i == 0) else INK
            ax.plot([xs[i]], [ys[i]], marker="o", ms=s.get("ms", 7),
                    mfc=fc, mec=INK, mew=s.get("mew", 1.5), zorder=5)

    # ---------- 差值箭头（两组终点差距） ----------
    gap = cfg.get("gap")
    if gap:
        x = gap["x"]
        ax.annotate("", xy=(x, gap["y2"]), xytext=(x, gap["y1"]),
                    arrowprops=dict(arrowstyle="<->", color=INK, lw=1.1,
                                    shrinkA=0, shrinkB=0), zorder=6)
        mid = (gap["y1"] + gap["y2"]) / 2
        dx = gap.get("dx", 0.10)
        if gap.get("text_top"):
            ax.text(x + dx, mid + gap.get("dy_top", 3.2), gap["text_top"],
                    fontsize=FS, color=INK, ha="left", va="center", zorder=6)
        if gap.get("text_bottom"):
            ax.text(x + dx, mid - gap.get("dy_bottom", 3.2), gap["text_bottom"],
                    fontsize=FS, color=INK, ha="left", va="center", zorder=6)

    # ---------- 数据标注 ----------
    for a in cfg.get("annotations", []):
        ax.text(a["x"], a["y"], a["text"], fontsize=FS,
                color=a.get("color", INK),
                ha=a.get("ha", "left"), va=a.get("va", "center"), zorder=6)

    # ---------- 图例 ----------
    legend = cfg.get("legend") or {}
    mode = legend.get("mode", geo["legend_default"])
    rows = legend.get("rows")
    if rows is None:
        rows = []
        for s in series:
            rows.append({"kind": s.get("style", "solid"),
                         "lw": s.get("lw"),
                         "text": s.get("legend", s.get("name", ""))})
        if hline and hline.get("label"):
            rows.append({"kind": hline.get("style", "dashed"),
                         "text": hline["label"]})

    def sample(r):
        kind = r.get("kind", "solid")
        if kind == "solid":
            return dict(lw=r.get("lw") or 1.8, ls="-")
        st = LINE_STYLE.get(kind, LINE_STYLE["dashed"])
        return dict(lw=r.get("lw") or st["lw"], ls=st["ls"])

    if mode == "in" and rows:
        anc = legend.get("anchor", [0.03, 0.90])
        rgap = legend.get("row_gap", 0.052)
        slen = legend.get("sample_len", 0.085)
        for i, r in enumerate(rows):
            y = anc[1] - i * rgap
            ax.plot([anc[0], anc[0] + slen], [y, y], transform=ax.transAxes,
                    color=INK, clip_on=False, zorder=6, **sample(r))
            ax.text(anc[0] + slen + 0.022, y, r["text"], transform=ax.transAxes,
                    fontsize=FS, color=INK if i == 0 else "#333333",
                    ha="left", va="center", zorder=6)
    elif mode == "out-bottom" and rows:
        anc = legend.get("anchor", geo.get("legend_anchor", [0.083, 0.126]))
        rgap = legend.get("row_gap", 0.030)
        slen = legend.get("sample_len", 0.055)
        for i, r in enumerate(rows):
            y = anc[1] - i * rgap
            fig.add_artist(plt.Line2D([anc[0], anc[0] + slen], [y, y],
                                      transform=fig.transFigure, color=INK, **sample(r)))
            fig.text(anc[0] + slen + 0.018, y, r["text"], fontsize=FS,
                     color=BODY, va="center")

    # ---------- 输出 ----------
    out = cfg.get("output") or "figure.png"
    if not os.path.isabs(out):
        out = os.path.join(out_dir, out)
    out = os.path.abspath(out)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    fig.savefig(out, dpi=DPI, transparent=True)

    stem, ext = os.path.splitext(out)
    preview = stem + "_白底预览" + ext
    from PIL import Image
    im = Image.open(out)
    bg = Image.new("RGB", im.size, (255, 255, 255))
    bg.paste(im, mask=im.split()[-1])
    bg.save(preview)

    # ---------- 自检信息 ----------
    print("saved: %s (%dx%d, RGBA)" % (out, *im.size))
    print("preview: %s" % preview)
    for s in series:
        vals = [p[1] for p in s["points"]]
        print("  %-14s n=%d  min=%.2f  max=%.2f  last=%.2f"
              % (s.get("name", "series"), len(vals), min(vals), max(vals), vals[-1]))
    if cfg.get("note"):
        print("note:", cfg["note"])
    return out, preview


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    with open(args.config, encoding="utf-8") as f:
        cfg = json.load(f)
    draw(cfg, os.path.dirname(os.path.abspath(args.config)))


if __name__ == "__main__":
    main()
