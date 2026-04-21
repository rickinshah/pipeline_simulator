"""
Scalar-6 Pipeline Simulator — Tkinter GUI  (v2 rewrite)
Tokens are tracked by instruction identity and slide between stages.
"""
import tkinter as tk
import re
import random

# ─────────────────────────────────────────────────────────────────────────────
# COLOUR PALETTE
# ─────────────────────────────────────────────────────────────────────────────
BG   = "#0d1117"
BG2  = "#161b22"
BG3  = "#21262d"
FG   = "#e6edf3"
FG2  = "#8b949e"
FG3  = "#3a4048"

CYAN   = "#39d0d8"
GREEN  = "#3fb950"
AMBER  = "#d29922"
RED    = "#f85149"
PURPLE = "#a371f7"
BLUE   = "#58a6ff"
ORANGE = "#e3b341"

STAGE_BG = {
    "IF":  "#112233", "ID": "#111a2e",
    "OF":  "#161133", "EX": "#231133",
    "MEM": "#2a1122", "WB": "#112211",
}
STAGE_ACCENT = {
    "IF": CYAN, "ID": BLUE, "OF": PURPLE,
    "EX": AMBER, "MEM": ORANGE, "WB": GREEN,
}
OP_COLOR = {
    "MOV": BLUE,
    "ADD": GREEN, "SUB": GREEN, "AND": GREEN,
    "OR":  GREEN, "XOR": GREEN, "NEG": GREEN,
    "LD":  ORANGE, "ST": "#f0883e",
    "JMP": RED,
    "BEQ": PURPLE, "BNE": PURPLE, "BLT": PURPLE,
    "BGT": PURPLE, "BLE": PURPLE, "BGE": PURPLE,
}

FM  = ("Courier New", 10)
FMB = ("Courier New", 10, "bold")
FMS = ("Courier New",  9)
FMT = ("Courier New", 16, "bold")
FLB = ("Courier New",  8, "bold")

STAGES = ["IF", "ID", "OF", "EX", "MEM", "WB"]
BRANCH_OPS = {"JMP","BEQ","BNE","BLT","BGT","BLE","BGE"}

SAMPLES = {
    "Arithmetic":   "MOV R0, #10\nMOV R1, #3\nADD R2, R0, R1\nSUB R3, R0, R1\nADD R4, R2, R3",
    "Branch Skip":  "MOV R0, #7\nMOV R1, #7\nBEQ R0, R1, skip\nMOV R2, #99\nskip: MOV R3, #42",
    "Loop":         "MOV R0, #0\nMOV R1, #4\nMOV R2, #1\nloop: ADD R0, R0, R2\nBNE R0, R1, loop",
    "Load/Store":   "MOV R0, #200\nMOV R1, #77\nST R1, [R0+0]\nLD R2, [R0+0]\nADD R3, R1, R2",
    "Hazard chain": "MOV R0, #3\nADD R1, R0, R0\nADD R2, R1, R0\nADD R3, R2, R1",
}

# ─────────────────────────────────────────────────────────────────────────────
# INSTRUCTION
# ─────────────────────────────────────────────────────────────────────────────
_uid_counter = 0

class Instruction:
    def __init__(self, op, dest=None, src1=None, src2=None, imm=None, offset=0, idx=0):
        global _uid_counter
        _uid_counter += 1
        self._uid = _uid_counter
        self.op = op; self.dest = dest; self.src1 = src1; self.src2 = src2
        self.imm = imm; self.offset = offset; self.idx = idx
        self.result = None; self.addr = None; self.store_val = None
        self.branch_taken = False

    def label(self):
        op = self.op
        if op == "MOV": return f"MOV {self.dest},#{self.imm}"
        if op in ("ADD","SUB","AND","OR","XOR"): return f"{op} {self.dest},{self.src1},{self.src2}"
        if op == "NEG": return f"NEG {self.dest},{self.src1}"
        if op == "LD":  return f"LD {self.dest},[{self.src1}+{self.offset}]"
        if op == "ST":  return f"ST {self.src1},[{self.dest}+{self.offset}]"
        if op == "JMP": return f"JMP {self.imm:+d}"
        if op in BRANCH_OPS: return f"{op} {self.src1},{self.src2},{self.imm:+d}"
        return op

    def clone(self):
        """Return a copy of this instruction with a brand-new uid.
        Used on every fetch so that loop/branch re-executions of the same
        program instruction get their own pipeline token."""
        global _uid_counter
        _uid_counter += 1
        c = Instruction.__new__(Instruction)
        c.__dict__.update(self.__dict__)
        c._uid          = _uid_counter
        c.result        = None
        c.addr          = None
        c.store_val     = None
        c.branch_taken  = False
        return c

    def __repr__(self): return f"I{self.idx}:{self.label()}"


def _parse_one(line, idx, labels):
    """Parse a single instruction line (uppercased, label prefix already stripped).
    labels maps NAME->instruction-index for resolving symbolic branch targets."""
    line = line.strip()
    if not line: return None

    def resolve(token, from_idx):
        token = token.strip()
        try:
            return int(token)
        except ValueError:
            pass
        name = token.upper()
        if name in labels:
            return labels[name] - from_idx
        raise ValueError(f"Unknown label {token!r}")

    try:
        if line.startswith("MOV"):
            m = re.match(r"MOV\s+(R\d+),\s*#(-?\d+)", line)
            return Instruction("MOV", m[1], imm=int(m[2]), idx=idx)
        if line.startswith(("ADD","SUB","AND","OR","XOR")):
            m = re.match(r"(ADD|SUB|AND|OR|XOR)\s+(R\d+),\s*(R\d+),\s*(R\d+)", line)
            return Instruction(m[1], m[2], m[3], m[4], idx=idx)
        if line.startswith("NEG"):
            m = re.match(r"NEG\s+(R\d+),\s*(R\d+)", line)
            return Instruction("NEG", m[1], m[2], idx=idx)
        if line.startswith("LD"):
            m = re.match(r"LD\s+(R\d+),\s*\[(R\d+)\s*\+?\s*(-?\d+)?\]", line)
            return Instruction("LD", m[1], m[2], offset=int(m[3] or 0), idx=idx)
        if line.startswith("ST"):
            m = re.match(r"ST\s+(R\d+),\s*\[(R\d+)\s*\+?\s*(-?\d+)?\]", line)
            return Instruction("ST", m[2], m[1], offset=int(m[3] or 0), idx=idx)
        if line.startswith("JMP"):
            m = re.match(r"JMP\s+(\S+)", line)
            return Instruction("JMP", imm=resolve(m[1], idx), idx=idx)
        for op in ("BEQ","BNE","BLT","BGT","BLE","BGE"):
            if line.startswith(op):
                m = re.match(rf"{op}\s+(R\d+),\s*(R\d+),\s*(\S+)", line)
                return Instruction(op, src1=m[1], src2=m[2],
                                   imm=resolve(m[3], idx), idx=idx)
    except Exception:
        pass
    return None


def assemble(source_lines):
    """Two-pass assembler. Returns (prog, errors, labels).
    Pass 1: strip labels, build label->index map.
    Pass 2: parse instructions with label resolution."""
    labels = {}   # label_name (upper) -> instruction index
    raw    = []   # (original_line, body_upper) per instruction line

    for raw_line in source_lines:
        line = raw_line.strip()
        if not line or line.startswith(";"): continue
        body = line.split(";")[0].strip()
        label_match = re.match(r'^([A-Za-z_]\w*)\s*:(.*)', body)
        if label_match:
            lname = label_match.group(1).upper()
            rest  = label_match.group(2).strip()
            labels[lname] = len(raw)
            if not rest:
                continue
            body = rest
        raw.append((line, body.upper()))

    prog   = []
    errors = []
    for idx, (orig, body) in enumerate(raw):
        ins = _parse_one(body, idx, labels)
        if ins:
            prog.append(ins)
        else:
            errors.append(orig)

    return prog, errors, labels


# ─────────────────────────────────────────────────────────────────────────────
# ENGINE
# ─────────────────────────────────────────────────────────────────────────────
class Engine:
    def __init__(self, program):
        self.program  = program
        self.REG      = {f"R{i}": 0 for i in range(16)}
        self.READY    = {f"R{i}": True for i in range(16)}
        self.PRODUCER = {f"R{i}": None for i in range(16)}
        self.MEM      = {}
        self.pipe     = {s: None for s in STAGES}
        self.pc       = 0
        self.cycle    = 0
        self.done     = False

    def _mread(self, a):
        a &= 0xFFFFFFFF
        return self.MEM.get(a, random.randint(0, 0xFFFF))

    def _mwrite(self, a, v):
        self.MEM[a & 0xFFFFFFFF] = v

    def _forward_val(self, reg):
        """Return the most up-to-date value for reg, checking forward paths first.
        Priority: EX result > MEM result > WB result > register file."""
        p = self.pipe
        for stage in ("EX", "MEM", "WB"):
            i = p[stage]
            if i and i.dest == reg and i.op not in BRANCH_OPS and i.op != "ST":
                if i.result is not None:
                    return i.result
        return self.REG[reg]

    def _hazard(self, instr):
        """Only stall for load-use: LD in OF whose dest is needed by instr in ID.
        (LD result is not available until end of MEM; MEM->EX forwarding can't help
        because the consumer would need it at the START of EX, one cycle too early.)"""
        if not instr: return []
        of = self.pipe["OF"]
        if of and of.op == "LD" and of.dest in (instr.src1, instr.src2):
            return [(of.dest, of)]
        return []

    def _exec(self, instr):
        """Execute using forwarded register values."""
        if not instr: return
        op = instr.op
        # resolve source values through forwarding network
        def R(reg): return self._forward_val(reg) if reg else 0
        if op=="MOV":   instr.result = instr.imm
        elif op=="ADD": instr.result = R(instr.src1)+R(instr.src2)
        elif op=="SUB": instr.result = R(instr.src1)-R(instr.src2)
        elif op=="AND": instr.result = R(instr.src1)&R(instr.src2)
        elif op=="OR":  instr.result = R(instr.src1)|R(instr.src2)
        elif op=="XOR": instr.result = R(instr.src1)^R(instr.src2)
        elif op=="NEG": instr.result = -R(instr.src1)
        elif op=="LD":  instr.addr   = R(instr.src1)+instr.offset
        elif op=="ST":
            instr.addr      = R(instr.dest)+instr.offset
            instr.store_val = R(instr.src1)
        elif op=="JMP": instr.branch_taken = True
        elif op=="BEQ": instr.branch_taken = R(instr.src1)==R(instr.src2)
        elif op=="BNE": instr.branch_taken = R(instr.src1)!=R(instr.src2)
        elif op=="BLT": instr.branch_taken = R(instr.src1)< R(instr.src2)
        elif op=="BGT": instr.branch_taken = R(instr.src1)> R(instr.src2)
        elif op=="BLE": instr.branch_taken = R(instr.src1)<=R(instr.src2)
        elif op=="BGE": instr.branch_taken = R(instr.src1)>=R(instr.src2)

    def step(self):
        if self.done: return None
        self.cycle += 1
        p = self.pipe
        events = []; stall_info = []; branch_flush = False; branch_target = None

        # WB
        if p["WB"]:
            wb = p["WB"]
            if wb.dest and wb.op not in BRANCH_OPS and wb.op != "ST":
                old = self.REG[wb.dest]
                self.REG[wb.dest] = wb.result
                self.READY[wb.dest] = True
                self.PRODUCER[wb.dest] = None
                events.append(("wb", f"{wb.dest} <- {wb.result}  (was {old})"))

        # Hazard check
        stall_info = self._hazard(p["ID"])
        stall = bool(stall_info)
        for src, prod in stall_info:
            events.append(("stall", f"Load-use stall: {p['ID'].label()} needs {src} (forwarding cannot help)"))

        # MEM
        if p["MEM"]:
            i = p["MEM"]
            if i.op == "LD":
                i.result = self._mread(i.addr)
                events.append(("mem", f"LD  [{i.addr}] -> {i.result}"))
            elif i.op == "ST":
                self._mwrite(i.addr, i.store_val)
                events.append(("mem", f"ST  [{i.addr}] <- {i.store_val}"))

        p["WB"]  = p["MEM"]
        p["MEM"] = p["EX"]

        if p["EX"]:
            ex = p["EX"]
            # Detect and log forwarding paths before exec reads them
            fwd_srcs = [s for s in (ex.src1, ex.src2) if s and not self.READY.get(s, True)]
            self._exec(ex)
            for src in fwd_srcs:
                for stage in ("EX", "MEM", "WB"):
                    fwd = self.pipe[stage]
                    if fwd and fwd is not ex and fwd.dest == src and fwd.result is not None:
                        events.append(("fwd", f"FWD {stage}->EX: {src} = {fwd.result}  ({fwd.label()} -> {ex.label()})"))
                        break

        # Branch resolution
        if p["EX"] and p["EX"].op in BRANCH_OPS and p["EX"].branch_taken:
            bi  = p["EX"]
            tgt = bi.idx + bi.imm
            if 0 <= tgt < len(self.program):
                self.pc = tgt
                branch_flush = True
                branch_target = tgt
                p["IF"] = p["ID"] = p["OF"] = None
                events.append(("branch", f"Branch taken -> I{tgt}  (flushed IF/ID/OF)"))
            else:
                events.append(("warn", f"Branch target {tgt} out of range"))

        def fetch():
            if self.pc < len(self.program):
                # Clone so each pipeline pass of the same instruction
                # gets a unique _uid — required for correct token display
                # when a branch/loop re-fetches an already-in-flight instruction.
                p["IF"] = self.program[self.pc].clone()
                self.pc += 1
            else:
                p["IF"] = None

        def mark_dest_in_flight(instr):
            """Reserve dest register when instruction clears ID and enters OF."""
            if instr and instr.dest and instr.op not in BRANCH_OPS:
                self.READY[instr.dest] = False
                self.PRODUCER[instr.dest] = instr

        if stall:
            p["EX"] = p["OF"]
            p["OF"] = None
            # p["ID"] stays, p["IF"] stays — no new fetch, no new reservation
        elif branch_flush:
            p["EX"] = None
            fetch()
        else:
            p["EX"] = p["OF"]
            entering_of = p["ID"]   # instruction graduating past the hazard gate
            p["OF"] = p["ID"]
            mark_dest_in_flight(entering_of)
            p["ID"] = p["IF"]
            fetch()

        if not any(p.values()) and self.pc >= len(self.program):
            self.done = True

        return dict(
            cycle=self.cycle,
            pipe={s: p[s] for s in STAGES},
            regs=dict(self.REG),
            mem=dict(self.MEM),
            stall=stall,
            stall_info=stall_info,
            branch_flush=branch_flush,
            branch_target=branch_target,
            events=events,
            done=self.done,
        )


# ─────────────────────────────────────────────────────────────────────────────
# ANIMATED TOKEN
# ─────────────────────────────────────────────────────────────────────────────
ANIM_STEPS = 12
ANIM_MS    = 14   # ~70fps


class Token:
    """A coloured chip on the canvas that can slide smoothly to a new position."""

    def __init__(self, canvas, x, y, w, h, text, color):
        self.canvas = canvas
        self.w = w; self.h = h
        self.color = color
        self._x = float(x); self._y = float(y)
        self._anim_id = None
        self.alive = True

        self.rect  = canvas.create_rectangle(
            x, y, x+w, y+h,
            fill=color, outline="#ffffff", width=1, tags="tok")
        self.text_id = canvas.create_text(
            x + w/2, y + h/2,
            text=text, fill="#0c1014",
            font=("Courier New", 9, "bold"),
            width=w - 12, tags="tok")

    def set_text(self, text):
        if self.alive:
            self.canvas.itemconfig(self.text_id, text=text)

    def slide_to(self, nx, ny):
        if not self.alive: return
        if self._anim_id:
            self.canvas.after_cancel(self._anim_id)
            self._anim_id = None
        dx = (nx - self._x) / ANIM_STEPS
        dy = (ny - self._y) / ANIM_STEPS
        self._step(dx, dy, ANIM_STEPS, nx, ny)

    def _step(self, dx, dy, remaining, tx, ty):
        if not self.alive: return
        if remaining <= 0:
            # Snap exactly
            self.canvas.coords(self.rect,    tx, ty, tx+self.w, ty+self.h)
            self.canvas.coords(self.text_id, tx+self.w/2, ty+self.h/2)
            self._x = tx; self._y = ty
            return
        self.canvas.move(self.rect,    dx, dy)
        self.canvas.move(self.text_id, dx, dy)
        self._x += dx; self._y += dy
        self._anim_id = self.canvas.after(
            ANIM_MS, lambda: self._step(dx, dy, remaining-1, tx, ty))

    def flash(self, color, n=4):
        orig = self.color
        def tog(i, c):
            if not self.alive: return
            self.canvas.itemconfig(self.rect, fill=c)
            if i > 0:
                nc = color if c == orig else orig
                self.canvas.after(100, lambda: tog(i-1, nc))
        tog(n*2, color)

    def destroy(self):
        if not self.alive: return
        self.alive = False
        if self._anim_id:
            self.canvas.after_cancel(self._anim_id)
        self.canvas.delete(self.rect)
        self.canvas.delete(self.text_id)


# ─────────────────────────────────────────────────────────────────────────────
# APPLICATION
# ─────────────────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Scalar-6  Pipeline Simulator")
        self.configure(bg=BG)
        self.minsize(1000, 640)
        self.geometry("1280x800")

        self.engine    = None
        self.auto_run  = False
        self._after_id = None

        # uid -> Token  (tokens persist and slide between stages)
        self._tokens: dict = {}
        # stage -> uid currently displayed there (None = empty)
        self._stage_uid: dict = {s: None for s in STAGES}
        # stage -> (x0,y0,x1,y1) on canvas
        self._stage_rects: dict = {}

        self._prev_regs = {f"R{i}": 0 for i in range(16)}

        self._build()

    # ══════════════════════════════════════════════════════════════════════════
    # UI BUILD
    # ══════════════════════════════════════════════════════════════════════════
    def _build(self):
        top = tk.Frame(self, bg=BG, pady=5)
        top.pack(fill="x", padx=12)
        tk.Label(top, text="◈  SCALAR-6  PIPELINE  VISUALIZER",
                 font=FMT, fg=CYAN, bg=BG).pack(side="left")
        self.cycle_lbl = tk.Label(top, text="CYCLE  —",
                                   font=("Courier New",13,"bold"), fg=FG2, bg=BG)
        self.cycle_lbl.pack(side="right", padx=8)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=8, pady=(0,8))
        body.columnconfigure(0, minsize=230, weight=1)
        body.columnconfigure(1, weight=4)
        body.columnconfigure(2, minsize=210, weight=1)
        body.rowconfigure(0, weight=1)

        left   = tk.Frame(body, bg=BG)
        center = tk.Frame(body, bg=BG)
        right  = tk.Frame(body, bg=BG)
        left.grid  (row=0, column=0, sticky="nsew", padx=(0,5))
        center.grid(row=0, column=1, sticky="nsew", padx=2)
        right.grid (row=0, column=2, sticky="nsew", padx=(5,0))

        self._build_left(left)
        self._build_center(center)
        self._build_right(right)

    # ── LEFT
    def _build_left(self, p):
        p.rowconfigure(1, weight=1)
        p.columnconfigure(0, weight=1)

        # Samples panel
        sf = self._section(p, "EXAMPLES", row=0)
        for name in SAMPLES:
            tk.Button(sf, text=name, font=("Courier New",8),
                      bg=BG3, fg=FG2, activebackground=BG2, activeforeground=CYAN,
                      relief="flat", bd=0, cursor="hand2", pady=3,
                      command=lambda n=name: self._load_sample(n)
                      ).pack(fill="x", pady=1)

        # Editor
        ef = self._section(p, "PROGRAM EDITOR", row=1, expand=True)
        self.editor = tk.Text(ef, bg=BG, fg=FG, insertbackground=CYAN,
                               font=FM, bd=0, padx=6, pady=6,
                               selectbackground="#264f78", undo=True)
        self.editor.pack(fill="both", expand=True)
        self.editor.insert("1.0", SAMPLES["Arithmetic"])

        # Syntax ref
        rf = self._section(p, "SYNTAX", row=2)
        tk.Label(rf, text=(
            "MOV Rd,#imm\n"
            "ADD/SUB/AND/OR/XOR Rd,Ra,Rb\n"
            "NEG Rd,Rs\n"
            "LD Rd,[Rs+off]   ST Rs,[Rd+off]\n"
            "JMP ±off\n"
            "BEQ/BNE/BLT/BGT/BLE/BGE Ra,Rb,±off"
        ), font=("Courier New",8), fg=FG3, bg=BG2, justify="left").pack(anchor="w")

        # Buttons
        bp = tk.Frame(p, bg=BG)
        bp.grid(row=3, column=0, sticky="ew", pady=(4,0))
        bp.columnconfigure(0, weight=1)
        bp.columnconfigure(1, weight=1)

        self._mkbtn(bp, "▶  LOAD", CYAN,  self._do_load, 0, 0, cs=2)
        self.step_btn = self._mkbtn(bp, "⏭  STEP",  BLUE,  self._do_step, 1, 0)
        self.auto_btn = self._mkbtn(bp, "⚡  AUTO",  GREEN, self._do_auto, 1, 1)
        self._mkbtn(bp, "↺   RESET",     FG2,   self._do_reset, 2, 0, cs=2)

        self.step_btn.config(state="disabled")
        self.auto_btn.config(state="disabled")

        # Speed
        sp = tk.Frame(p, bg=BG)
        sp.grid(row=4, column=0, sticky="ew", pady=(4,0))
        tk.Label(sp, text="FAST", font=FLB, fg=FG3, bg=BG).pack(side="left", padx=4)
        self.speed_var = tk.IntVar(value=700)
        tk.Scale(sp, from_=150, to=2000, orient="horizontal",
                 variable=self.speed_var, bg=BG, fg=FG2, troughcolor=BG3,
                 highlightthickness=0, bd=0, showvalue=False
                 ).pack(side="left", fill="x", expand=True)
        tk.Label(sp, text="SLOW", font=FLB, fg=FG3, bg=BG).pack(side="left", padx=4)

    def _section(self, parent, title, row, expand=False):
        outer = tk.Frame(parent, bg=BG2)
        kw = dict(row=row, column=0, sticky="nsew" if expand else "ew", pady=(0,4))
        outer.grid(**kw)
        if expand:
            parent.rowconfigure(row, weight=1)
        tk.Label(outer, text=title, font=FLB, fg=FG2, bg=BG3,
                 padx=8, pady=4).pack(fill="x")
        inner = tk.Frame(outer, bg=BG2, padx=6, pady=4)
        inner.pack(fill="both", expand=True)
        return inner

    def _mkbtn(self, parent, text, color, cmd, row, col, cs=1):
        b = tk.Button(parent, text=text, font=FMB, bg=BG3, fg=color,
                      activebackground=BG2, activeforeground=color,
                      relief="flat", bd=0, cursor="hand2", pady=5,
                      command=cmd)
        b.grid(row=row, column=col, columnspan=cs, sticky="ew", padx=2, pady=2)
        return b

    # ── CENTER
    def _build_center(self, p):
        p.rowconfigure(1, weight=1)
        p.columnconfigure(0, weight=1)

        hdr = tk.Frame(p, bg=BG3, padx=8, pady=4)
        hdr.grid(row=0, column=0, sticky="ew", pady=(0,4))
        tk.Label(hdr, text="PIPELINE DATAPATH", font=FLB, fg=FG2, bg=BG3).pack(side="left")
        self.status_lbl = tk.Label(hdr, text="", font=FLB, fg=FG2, bg=BG3)
        self.status_lbl.pack(side="right")

        self.canvas = tk.Canvas(p, bg=BG, highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", self._on_resize)

        log_wrap = tk.Frame(p, bg=BG2)
        log_wrap.grid(row=2, column=0, sticky="ew", pady=(4,0))
        tk.Label(log_wrap, text="EVENT LOG", font=FLB, fg=FG2, bg=BG3,
                 padx=8, pady=3).pack(fill="x")
        self.log = tk.Text(log_wrap, bg=BG, fg=FG2, font=FMS, bd=0,
                            padx=6, pady=4, height=7,
                            state="disabled", wrap="word")
        sb = tk.Scrollbar(log_wrap, command=self.log.yview, bg=BG3)
        self.log.config(yscrollcommand=sb.set)
        self.log.pack(side="left", fill="x", expand=True)
        sb.pack(side="right", fill="y")
        for tag, col in [("stall",AMBER),("branch",PURPLE),("wb",GREEN),
                         ("mem",ORANGE),("warn",RED),("cycle",CYAN),("done",GREEN),
                         ("fwd",BLUE)]:
            self.log.tag_config(tag, foreground=col)

    # ── RIGHT
    def _build_right(self, p):
        p.rowconfigure(2, weight=1)
        p.columnconfigure(0, weight=1)

        rf = tk.Frame(p, bg=BG2)
        rf.grid(row=0, column=0, sticky="ew", pady=(0,4))
        tk.Label(rf, text="REGISTER FILE", font=FLB, fg=FG2, bg=BG3,
                 padx=8, pady=4).pack(fill="x")
        grid = tk.Frame(rf, bg=BG2, padx=4, pady=4)
        grid.pack(fill="both")
        self.reg_labels = {}
        for i in range(16):
            rn = f"R{i}"
            row_, col_ = divmod(i, 2)
            tk.Label(grid, text=f"{rn:>3}", font=FMB, fg=FG2, bg=BG2,
                     width=4, anchor="e").grid(row=row_, column=col_*2,
                                               padx=(2,0), pady=1, sticky="e")
            vl = tk.Label(grid, text="0", font=FM, fg=FG, bg=BG3,
                          width=8, anchor="e", padx=3)
            vl.grid(row=row_, column=col_*2+1, padx=(2,6), pady=1, sticky="ew")
            self.reg_labels[rn] = vl

        hf = tk.Frame(p, bg=BG2)
        hf.grid(row=1, column=0, sticky="ew", pady=(0,4))
        tk.Label(hf, text="HAZARD STATUS", font=FLB, fg=FG2, bg=BG3,
                 padx=8, pady=4).pack(fill="x")
        self.hazard_lbl = tk.Label(hf, text="--  clear", font=FMS,
                                    fg=GREEN, bg=BG2, padx=8, pady=6,
                                    justify="left", anchor="w")
        self.hazard_lbl.pack(fill="x")

        mf = tk.Frame(p, bg=BG2)
        mf.grid(row=2, column=0, sticky="nsew", pady=(0,4))
        tk.Label(mf, text="MEMORY", font=FLB, fg=FG2, bg=BG3,
                 padx=8, pady=4).pack(fill="x")
        self.mem_text = tk.Text(mf, bg=BG, fg=ORANGE, font=FMS, bd=0,
                                 padx=6, pady=4, height=7, state="disabled")
        self.mem_text.pack(fill="both", expand=True)

        pcf = tk.Frame(p, bg=BG3, padx=8, pady=6)
        pcf.grid(row=3, column=0, sticky="ew")
        tk.Label(pcf, text="PC ->", font=FLB, fg=FG2, bg=BG3).pack(side="left")
        self.pc_lbl = tk.Label(pcf, text="--",
                                font=("Courier New",14,"bold"), fg=CYAN, bg=BG3)
        self.pc_lbl.pack(side="right")

    # ══════════════════════════════════════════════════════════════════════════
    # CANVAS / STAGE DRAWING
    # ══════════════════════════════════════════════════════════════════════════
    def _on_resize(self, event=None):
        self._redraw_stages()
        # Re-snap live tokens to their stage positions after resize
        for stage, uid in self._stage_uid.items():
            if uid is not None and uid in self._tokens:
                tok = self._tokens[uid]
                if tok.alive and stage in self._stage_rects:
                    tx, ty, tw, th = self._token_geom(stage)
                    self.canvas.coords(tok.rect,    tx, ty, tx+tw, ty+th)
                    self.canvas.coords(tok.text_id, tx+tw/2, ty+th/2)
                    tok._x = float(tx); tok._y = float(ty)

    def _redraw_stages(self):
        c = self.canvas
        c.delete("stage")
        W = c.winfo_width(); H = c.winfo_height()
        if W < 20 or H < 20: return

        n   = len(STAGES)
        PX  = 12; PY = 44; GAP = 6
        sw  = (W - 2*PX - GAP*(n-1)) / n
        sh  = min(H - PY - 10, 180)
        sy  = PY + 18
        self._stage_rects.clear()

        for i, s in enumerate(STAGES):
            x0 = PX + i*(sw+GAP); x1 = x0+sw
            y0 = sy; y1 = sy+sh
            acc = STAGE_ACCENT[s]

            # shadow
            c.create_rectangle(x0+3, y0+3, x1+3, y1+3,
                                fill="#000000", outline="", tags="stage")
            # body
            c.create_rectangle(x0, y0, x1, y1,
                                fill=STAGE_BG[s], outline=acc, width=2, tags="stage")
            # accent stripe
            c.create_rectangle(x0+2, y0+2, x1-2, y0+7,
                                fill=acc, outline="", tags="stage")
            # label above
            c.create_text((x0+x1)/2, y0-15, text=s,
                           font=("Courier New",11,"bold"), fill=acc, tags="stage")

            # arrow
            if i < n-1:
                ay = (y0+y1)/2
                c.create_line(x1+1, ay, x1+GAP-1, ay,
                               fill="#40484f", width=2,
                               arrow="last", arrowshape=(7,9,4), tags="stage")

            self._stage_rects[s] = (x0, y0, x1, y1)

        self._draw_bubbles()

    def _draw_bubbles(self):
        self.canvas.delete("bubble")
        for stage, uid in self._stage_uid.items():
            if uid is None and stage in self._stage_rects:
                tx, ty, tw, th = self._token_geom(stage)
                self.canvas.create_rectangle(
                    tx, ty, tx+tw, ty+th,
                    fill="", outline="#3a4048", dash=(4,5), width=1, tags="bubble")
                self.canvas.create_text(
                    tx+tw/2, ty+th/2, text="bubble",
                    font=("Courier New",8), fill="#3a4048", tags="bubble")

    def _token_geom(self, stage):
        """Return (x, y, w, h) for a token inside stage."""
        x0, y0, x1, y1 = self._stage_rects[stage]
        pad = 10
        tw = x1 - x0 - pad*2
        th = min(52, y1 - y0 - pad*2)
        tx = x0 + pad
        ty = y0 + (y1-y0-th)/2
        return tx, ty, tw, th

    # ══════════════════════════════════════════════════════════════════════════
    # TOKEN MANAGEMENT  — the key fix: track by uid, slide between stages
    # ══════════════════════════════════════════════════════════════════════════
    def _sync_tokens(self, pipe_state, stall, branch_flush, forwarding=False):
        """
        Compare new pipeline state against what we're showing.
        For each stage:
          - Empty  → destroy any token there.
          - Has instr → if token for that uid already exists, slide it here.
                        Otherwise spawn a fresh token.
        """
        if not self._stage_rects:
            return

        new_uid = {
            s: (pipe_state[s]._uid if pipe_state[s] else None)
            for s in STAGES
        }

        # Collect all uids still active in the new pipe state (they must not be destroyed)
        active_uids = {uid for uid in new_uid.values() if uid is not None}

        # First pass: destroy tokens for stages that are now empty,
        # but only if that token's uid has truly left the pipeline entirely.
        for stage in STAGES:
            if new_uid[stage] is None:
                old_uid = self._stage_uid[stage]
                if old_uid is not None and old_uid not in active_uids:
                    if old_uid in self._tokens:
                        self._tokens[old_uid].destroy()
                        del self._tokens[old_uid]
                self._stage_uid[stage] = None

        # Orphan sweep: destroy any token whose uid is no longer anywhere in the
        # pipeline. This catches instructions that have fully exited WB (the last
        # stage) — they were never explicitly removed by the stage-based pass above
        # because no later stage ever becomes None with their uid as old_uid.
        for uid in list(self._tokens.keys()):
            if uid not in active_uids:
                self._tokens[uid].destroy()
                del self._tokens[uid]

        # Second pass: place/move tokens for occupied stages
        for stage in STAGES:
            uid = new_uid[stage]
            if uid is None:
                continue

            instr = pipe_state[stage]
            text  = f"I{instr.idx}: {instr.label()}"
            color = OP_COLOR.get(instr.op, CYAN)

            tx, ty, tw, th = self._token_geom(stage)

            if uid in self._tokens and self._tokens[uid].alive:
                # Token already exists — slide it to this stage
                tok = self._tokens[uid]
                tok.set_text(text)
                tok.slide_to(tx, ty)
            else:
                # Spawn new token directly in this stage
                tok = Token(self.canvas, tx, ty, tw, th, text, color)
                self._tokens[uid] = tok

            self._stage_uid[stage] = uid

            # Flash effects
            if stall and stage == "ID":
                self.canvas.after(80, lambda t=tok: t.flash(AMBER))
            elif branch_flush and stage in ("IF", "ID", "OF"):
                self.canvas.after(40, lambda t=tok: t.flash(RED, 5))
            elif forwarding and stage == "EX":
                self.canvas.after(40, lambda t=tok: t.flash(BLUE, 3))

        # Raise tokens above stage backgrounds and bubbles
        self.canvas.tag_raise("tok")
        self._draw_bubbles()
        self.canvas.tag_raise("tok")

    def _clear_tokens(self):
        for tok in list(self._tokens.values()):
            tok.destroy()
        self._tokens.clear()
        self._stage_uid = {s: None for s in STAGES}
        self.canvas.delete("tok")
        self.canvas.delete("bubble")

    # ══════════════════════════════════════════════════════════════════════════
    # CONTROLS
    # ══════════════════════════════════════════════════════════════════════════
    def _load_sample(self, name):
        self.editor.delete("1.0","end")
        self.editor.insert("1.0", SAMPLES[name])

    def _do_load(self):
        self._do_reset()
        lines = self.editor.get("1.0","end").strip().splitlines()
        prog, errors, labels = assemble(lines)
        for e in errors:
            self._log(f"  Parse error: {e!r}", "warn")
        if labels:
            self._log("  Labels: " + ", ".join(f"{k}->I{v}" for k,v in labels.items()), "cycle")
        if not prog:
            self._log("No valid instructions.", "warn"); return

        self.engine = Engine(prog)
        self.step_btn.config(state="normal")
        self.auto_btn.config(state="normal")
        self._log(f"Loaded {len(prog)} instructions.", "cycle")
        self._redraw_stages()
        self._clear_tokens()
        self._prev_regs = {f"R{i}": 0 for i in range(16)}
        self._update_regs({f"R{i}": 0 for i in range(16)})
        self.pc_lbl.config(text="0")
        self.cycle_lbl.config(text="CYCLE  0", fg=FG2)

    def _do_step(self):
        if not self.engine: return
        if self.engine.done: self._finish(); return
        state = self.engine.step()
        if state: self._apply(state)

    def _do_auto(self):
        self.auto_run = not self.auto_run
        if self.auto_run:
            self.auto_btn.config(text="|| PAUSE", fg=AMBER)
            self._tick()
        else:
            self.auto_btn.config(text=">> AUTO", fg=GREEN)
            if self._after_id:
                self.after_cancel(self._after_id)
                self._after_id = None

    def _tick(self):
        if not self.auto_run: return
        if self.engine and not self.engine.done:
            self._do_step()
            self._after_id = self.after(max(200, self.speed_var.get()), self._tick)
        else:
            self._finish()
            self.auto_run = False
            self.auto_btn.config(text=">> AUTO", fg=GREEN)

    def _do_reset(self):
        self.auto_run = False
        self.auto_btn.config(text=">> AUTO", fg=GREEN)
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self.engine = None
        self.step_btn.config(state="disabled")
        self.auto_btn.config(state="disabled")
        self._clear_tokens()
        self._redraw_stages()
        self.cycle_lbl.config(text="CYCLE  --", fg=FG2)
        self.status_lbl.config(text="")
        self.pc_lbl.config(text="--")
        self.hazard_lbl.config(text="--  clear", fg=GREEN)
        self._update_regs({f"R{i}": 0 for i in range(16)})
        self._update_mem({})
        self.log.config(state="normal")
        self.log.delete("1.0","end")
        self.log.config(state="disabled")

    def _finish(self):
        self._log("--  Execution complete  --", "done")
        self.status_lbl.config(text="DONE", fg=GREEN)
        self.cycle_lbl.config(fg=GREEN)

    # ══════════════════════════════════════════════════════════════════════════
    # STATE DISPLAY
    # ══════════════════════════════════════════════════════════════════════════
    def _apply(self, state):
        cyc = state["cycle"]
        self.cycle_lbl.config(text=f"CYCLE  {cyc}", fg=CYAN)
        self.pc_lbl.config(text=str(self.engine.pc))

        fwd_active = any(kind == "fwd" for kind, _ in state["events"])
        self._sync_tokens(state["pipe"], state["stall"], state["branch_flush"], fwd_active)

        if state["stall"]:
            self.status_lbl.config(text="STALL", fg=AMBER)
        elif state["branch_flush"]:
            self.status_lbl.config(text="BRANCH", fg=PURPLE)
        elif state["done"]:
            self.status_lbl.config(text="DONE", fg=GREEN)
        else:
            self.status_lbl.config(text="RUNNING", fg=GREEN)

        fwd_events = [msg for kind, msg in state["events"] if kind == "fwd"]
        if state["stall_info"]:
            lines = [f"  {src} <- {prod.label()}" for src,prod in state["stall_info"]]
            self.hazard_lbl.config(text="LOAD-USE STALL\n"+"\n".join(lines), fg=AMBER)
        elif fwd_events:
            self.hazard_lbl.config(text="FORWARDING\n" + "\n".join(f"  {m}" for m in fwd_events), fg=BLUE)
        elif state["branch_flush"]:
            self.hazard_lbl.config(
                text=f"BRANCH TAKEN\n  -> I{state['branch_target']}", fg=PURPLE)
        else:
            self.hazard_lbl.config(text="--  clear", fg=GREEN)

        self._update_regs(state["regs"])
        self._update_mem(state["mem"])

        self._log(f"-- Cycle {cyc} --", "cycle")
        for kind, msg in state["events"]:
            self._log(f"  {msg}", kind)

        if state["done"]:
            self._finish()

    def _update_regs(self, regs):
        for rn, lbl in self.reg_labels.items():
            val = regs.get(rn, 0)
            lbl.config(text=str(val))
            if val != self._prev_regs.get(rn, 0):
                lbl.config(fg=GREEN, bg="#1a3a1a")
                self.after(500, lambda l=lbl: l.config(fg=FG, bg=BG3))
        self._prev_regs = dict(regs)

    def _update_mem(self, mem):
        self.mem_text.config(state="normal")
        self.mem_text.delete("1.0","end")
        if mem:
            for a in sorted(mem):
                self.mem_text.insert("end", f"  [{a:08x}] = {mem[a]}\n")
        else:
            self.mem_text.insert("end","  (empty)")
        self.mem_text.config(state="disabled")

    def _log(self, msg, tag=""):
        self.log.config(state="normal")
        self.log.insert("end", msg+"\n", tag)
        self.log.see("end")
        if int(self.log.index("end").split(".")[0]) > 400:
            self.log.delete("1.0","60.0")
        self.log.config(state="disabled")


if __name__ == "__main__":
    App().mainloop()
