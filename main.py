"""
Scalar-6 Pipeline Simulator — Tkinter GUI  (v2 rewrite)
Tokens are tracked by instruction identity and slide between stages.
"""
import tkinter as tk
import re
import random

# ─────────────────────────────────────────────────────────────────────────────
# FONT SELECTION  (JetBrains Mono → Consolas → Courier New)
# ─────────────────────────────────────────────────────────────────────────────
def _pick_font():
    import tkinter.font as tkfont
    try:
        root = tk.Tk(); root.withdraw()
        available = set(tkfont.families())
        root.destroy()
    except Exception:
        available = set()
    for name in ("JetBrains Mono", "Consolas", "Courier New"):
        if name in available:
            return name
    return "Courier New"

_CODE_FONT_TEMP = _pick_font()

# ─────────────────────────────────────────────────────────────────────────────
# THEME — dark only
# ─────────────────────────────────────────────────────────────────────────────
_DARK_THEME = dict(
    BG   = "#12141a",
    BG2  = "#1a1d27",
    BG3  = "#222638",
    BG4  = "#1e2130",
    FG   = "#cdd6f4",
    FG2  = "#89b4fa",
    FG3  = "#45475a",
    CYAN   = "#89dceb",
    GREEN  = "#3da84a",
    AMBER  = "#c8960a",
    RED    = "#f38ba8",
    PURPLE = "#cba6f7",
    BLUE   = "#89b4fa",
    ORANGE = "#fab387",
    STAGE_BG = {
        "IF":  "#141e2e", "ID": "#131c30",
        "OF":  "#1a1535", "EX": "#241535",
        "MEM": "#2a1525", "WB": "#152514",
    },
    TOKEN_FG = "#11111b",
    SEL_BG   = "#3d4577",
    SCROLL_BG = "#222638",
    SCROLL_TR = "#1a1d27",
    ARROW_COL = "#585b70",
    BUBBLE_COL= "#45475a",
    FSM_ARROW = "#585b70",
)



_CURRENT_THEME = "dark"

def _apply_theme(name="dark"):
    global _CURRENT_THEME
    global BG, BG2, BG3, BG4, FG, FG2, FG3
    global CYAN, GREEN, AMBER, RED, PURPLE, BLUE, ORANGE
    global STAGE_BG, TOKEN_FG, SEL_BG, SCROLL_BG, SCROLL_TR
    global ARROW_COL, BUBBLE_COL, FSM_ARROW
    global STAGE_ACCENT, OP_COLOR
    _CURRENT_THEME = "dark"
    t = _DARK_THEME
    BG   = t["BG"];  BG2  = t["BG2"];  BG3  = t["BG3"];  BG4  = t["BG4"]
    FG   = t["FG"];  FG2  = t["FG2"];  FG3  = t["FG3"]
    CYAN   = t["CYAN"];   GREEN  = t["GREEN"]; AMBER  = t["AMBER"]
    RED    = t["RED"];    PURPLE = t["PURPLE"]; BLUE  = t["BLUE"]
    ORANGE = t["ORANGE"]; STAGE_BG = t["STAGE_BG"]
    TOKEN_FG  = t["TOKEN_FG"];  SEL_BG    = t["SEL_BG"]
    SCROLL_BG = t["SCROLL_BG"]; SCROLL_TR = t["SCROLL_TR"]
    ARROW_COL = t["ARROW_COL"]; BUBBLE_COL= t["BUBBLE_COL"]
    FSM_ARROW = t["FSM_ARROW"]
    STAGE_ACCENT = {
        "IF": CYAN, "ID": BLUE, "OF": PURPLE,
        "EX": AMBER, "MEM": ORANGE, "WB": GREEN,
    }
    OP_COLOR = {
        "MOV": BLUE,
        "ADD": GREEN, "SUB": GREEN, "AND": GREEN,
        "OR":  GREEN, "XOR": GREEN, "NEG": GREEN,
        "LD":  ORANGE, "ST": ORANGE,
        "JMP": RED,
        "BEQ": PURPLE, "BNE": PURPLE, "BLT": PURPLE,
        "BGT": PURPLE, "BLE": PURPLE, "BGE": PURPLE,
    }

# Initialise dark theme globals
_apply_theme("dark")

# Font: JetBrains Mono is ideal; fall back to Consolas then Courier New
_CODE_FONT = _CODE_FONT_TEMP
FM  = (_CODE_FONT, 10)
FMB = (_CODE_FONT, 10, "bold")
FMS = (_CODE_FONT,  9)
FMT = (_CODE_FONT, 15, "bold")
FLB = (_CODE_FONT,  9, "bold")

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
# 2-BIT SMITH PREDICTOR
# ─────────────────────────────────────────────────────────────────────────────
# States: 0=Strongly Not Taken, 1=Weakly Not Taken,
#         2=Weakly Taken,       3=Strongly Taken
_SNT, _WNT, _WT, _ST = 0, 1, 2, 3
_STATE_NAMES = {_SNT: "Strongly Not Taken", _WNT: "Weakly Not Taken",
                _WT:  "Weakly Taken",        _ST:  "Strongly Taken"}
_STATE_SHORT = {_SNT: "SNT", _WNT: "WNT", _WT: "WT", _ST: "ST"}

class TwoBitPredictor:
    """One 2-bit saturating counter per branch instruction index."""
    def __init__(self):
        # instruction-index -> state (0-3)
        self._table: dict[int, int] = {}
        # history: list of dicts for UI display
        self.history: list[dict] = []

    def _get(self, idx):
        return self._table.get(idx, _WT)  # default: Weakly Taken

    def predict(self, instr) -> bool:
        """Return True if we predict taken."""
        state = self._get(instr.idx)
        return state >= _WT

    def update(self, instr, actually_taken: bool):
        """Saturating counter update after branch is resolved."""
        idx = instr.idx
        old = self._get(idx)
        if actually_taken:
            new = min(old + 1, _ST)
        else:
            new = max(old - 1, _SNT)
        self._table[idx] = new
        correct = (old >= _WT) == actually_taken
        self.history.append({
            "instr":   instr.label(),
            "idx":     idx,
            "old":     old,
            "new":     new,
            "taken":   actually_taken,
            "correct": correct,
        })
        return new, correct

    def stats(self):
        total   = len(self.history)
        correct = sum(1 for h in self.history if h["correct"])
        return total, correct

    def reset(self):
        self._table.clear()
        self.history.clear()


# ─────────────────────────────────────────────────────────────────────────────
# ENGINE
# ─────────────────────────────────────────────────────────────────────────────
class Engine:
    def __init__(self, program):
        self.program   = program
        self.REG       = {f"R{i}": 0 for i in range(16)}
        self.READY     = {f"R{i}": True for i in range(16)}
        self.PRODUCER  = {f"R{i}": None for i in range(16)}
        self.MEM       = {}
        self.pipe      = {s: None for s in STAGES}
        self.pc        = 0
        self.cycle     = 0
        self.done      = False
        self.predictor = TwoBitPredictor()
        # Always-current FSM state for persistent FSM glow (per branch in flight)
        self._fsm_state: int = _WT  # matches TwoBitPredictor._get() default for unseen branches
        # CPU Status Flags — updated after every arithmetic/logic operation in WB
        self.FLAGS = {"neg": False, "carry": False, "zero": False}

    def _mread(self, a):
        a &= 0xFFFFFFFF
        return self.MEM.get(a, random.randint(0, 0xFFFF))

    def _mwrite(self, a, v):
        self.MEM[a & 0xFFFFFFFF] = v

    def _forward_val(self, reg):
        """Return the most up-to-date value for reg, checking forward paths first.
        Priority: EX result > MEM result > WB result > register file.
        WB inclusion enables MEM->MEM forwarding: a LD whose result was
        computed in MEM last cycle is now in WB and can feed the instruction
        currently entering MEM (e.g. an ST needing the loaded value)."""
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
        if op=="MOV":
            instr.result = instr.imm
            self._set_flags(instr.result)             # ZERO if imm==0, NEG if imm<0
        elif op=="ADD":
            a, b = R(instr.src1), R(instr.src2)
            instr.result = a + b
            self._set_flags(instr.result, carry=((a & 0xFFFFFFFF) + (b & 0xFFFFFFFF)) > 0xFFFFFFFF)
        elif op=="SUB":
            a, b = R(instr.src1), R(instr.src2)
            instr.result = a - b
            self._set_flags(instr.result, carry=(a & 0xFFFFFFFF) < (b & 0xFFFFFFFF))
        elif op=="AND":
            instr.result = R(instr.src1) & R(instr.src2)
            self._set_flags(instr.result)             # carry always 0 for bitwise
        elif op=="OR":
            instr.result = R(instr.src1) | R(instr.src2)
            self._set_flags(instr.result)
        elif op=="XOR":
            instr.result = R(instr.src1) ^ R(instr.src2)
            self._set_flags(instr.result)             # ZERO when both operands equal
        elif op=="NEG":
            src = R(instr.src1)
            instr.result = -src
            self._set_flags(instr.result, carry=(src != 0))  # carry set if src was nonzero
        elif op=="LD":
            instr.addr = R(instr.src1) + instr.offset
            # flags set in step() MEM stage after the value is loaded
        elif op=="ST":
            instr.addr      = R(instr.dest) + instr.offset
            instr.store_val = R(instr.src1)
            # ST stores a value but produces no result → flags unchanged
        elif op=="JMP":
            instr.branch_taken = True
            # unconditional jump → no comparison → flags unchanged
        elif op in ("BEQ","BNE","BLT","BGT","BLE","BGE"):
            # All conditional branches do an implicit CMP (src1 − src2) and update flags,
            # exactly like a real CPU compare-then-branch model.
            a, b = R(instr.src1), R(instr.src2)
            diff = a - b
            self._set_flags(diff, carry=(a & 0xFFFFFFFF) < (b & 0xFFFFFFFF))
            if   op=="BEQ": instr.branch_taken = (diff == 0)   # ZERO=1
            elif op=="BNE": instr.branch_taken = (diff != 0)   # ZERO=0
            elif op=="BLT": instr.branch_taken = (diff <  0)   # NEG=1
            elif op=="BGT": instr.branch_taken = (diff >  0)   # NEG=0, ZERO=0
            elif op=="BLE": instr.branch_taken = (diff <= 0)   # NEG=1 or ZERO=1
            elif op=="BGE": instr.branch_taken = (diff >= 0)   # NEG=0

    def _set_flags(self, result, carry=False):
        """Update NEG, CARRY, ZERO flags from an ALU result."""
        self.FLAGS["zero"]  = (result == 0)
        self.FLAGS["neg"]   = (result < 0)
        self.FLAGS["carry"] = carry

    def step(self):
        if self.done: return None
        self.cycle += 1
        p = self.pipe
        events = []; stall_info = []; branch_flush = False; branch_target = None
        pred_info = None   # dict with prediction details emitted this cycle

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

        # EX — execute before shifts so _forward_val sees MEM/WB producers correctly
        if p["EX"]:
            ex = p["EX"]
            fwd_srcs = [s for s in (ex.src1, ex.src2) if s and not self.READY.get(s, True)]
            self._exec(ex)
            for src in fwd_srcs:
                for stage in ("MEM", "WB"):
                    fwd = self.pipe[stage]
                    if fwd and fwd.dest == src and fwd.result is not None:
                        events.append(("fwd", f"FWD {stage}->EX: {src} = {fwd.result}  ({fwd.label()} -> {ex.label()})"))
                        break

        # MEM — after EX so _forward_val can see the freshly computed EX result
        # Also detect MEM->MEM forwarding: WB (previous MEM result) -> current MEM consumer
        if p["MEM"]:
            i = p["MEM"]
            wb = p["WB"]
            # Log MEM->MEM (WB->MEM) forwarding: producer just graduated from MEM
            # into WB this cycle; consumer is the instruction now in MEM.
            for src in (i.src1, i.src2, i.dest if i.op == "ST" else None):
                if src and wb and wb.dest == src and wb.op not in BRANCH_OPS and wb.op != "ST" and wb.result is not None:
                    events.append(("fwd", f"FWD MEM->MEM (WB->MEM): {src} = {wb.result}  ({wb.label()} -> {i.label()})"))
            if i.op == "LD":
                i.result = self._mread(i.addr)
                self._set_flags(i.result)             # ZERO/NEG from loaded value; carry cleared
                events.append(("mem", f"LD  [{i.addr}] -> {i.result}"))
            elif i.op == "ST":
                self._mwrite(i.addr, i.store_val)
                events.append(("mem", f"ST  [{i.addr}] <- {i.store_val}"))

        p["WB"]  = p["MEM"]
        p["MEM"] = p["EX"]

        # ── Branch resolution + predictor update ──────────────────────────
        mispredicted = False
        if p["EX"] and p["EX"].op in BRANCH_OPS:
            bi           = p["EX"]
            actually_taken = bi.branch_taken
            tgt          = bi.idx + bi.imm
            old_state    = self.predictor._get(bi.idx)
            predicted_taken = old_state >= _WT
            new_state, correct = self.predictor.update(bi, actually_taken)

            self._fsm_state = new_state   # update persistent glow after resolution
            pred_info = {
                "instr":          bi.label(),
                "predicted_taken": predicted_taken,
                "actually_taken":  actually_taken,
                "correct":        correct,
                "old_state":      old_state,
                "new_state":      new_state,
                "old_name":       _STATE_SHORT[old_state],
                "new_name":       _STATE_SHORT[new_state],
            }

            if actually_taken and 0 <= tgt < len(self.program):
                if not predicted_taken:
                    # Mispredicted: we fetched the fall-through path — flush and redirect
                    self.pc = tgt
                    branch_flush = True
                    branch_target = tgt
                    mispredicted = True
                    p["IF"] = p["ID"] = p["OF"] = None
                    events.append(("branch",
                        f"Branch TAKEN (MISPREDICTED) -> I{tgt}  "
                        f"[predictor: {_STATE_SHORT[old_state]} -> {_STATE_SHORT[new_state]}]  "
                        f"(flushed IF/ID/OF)"))
                else:
                    # Correct prediction: speculative fetch already followed the right path
                    branch_target = tgt
                    events.append(("branch",
                        f"Branch TAKEN (correct prediction) -> I{tgt}  "
                        f"[predictor: {_STATE_SHORT[old_state]} -> {_STATE_SHORT[new_state]}]"))
            elif not actually_taken:
                if predicted_taken:
                    mispredicted = True
                    correct_pc = bi.idx + 1   # fall-through: instruction after the branch
                    self.pc = correct_pc       # fix PC — speculative fetch sent it to loop target
                    events.append(("branch",
                        f"Branch NOT TAKEN (MISPREDICTED)  "
                        f"[predictor: {_STATE_SHORT[old_state]} -> {_STATE_SHORT[new_state]}]  "
                        f"(flushed IF/ID/OF)"))
                    p["IF"] = p["ID"] = p["OF"] = None
                    branch_flush = True        # flush speculatively fetched wrong-path
                    branch_target = correct_pc
                else:
                    events.append(("branch",
                        f"Branch NOT TAKEN (correct prediction)  "
                        f"[predictor: {_STATE_SHORT[old_state]} -> {_STATE_SHORT[new_state]}]"))
            else:
                events.append(("warn", f"Branch target {tgt} out of range"))

        if_pred_event = None   # set below if a branch is fetched this cycle

        def fetch():
            nonlocal if_pred_event
            if self.pc < len(self.program):
                instr = self.program[self.pc].clone()
                # Speculative fetch: if next instruction is a branch, peek at prediction
                if instr.op in BRANCH_OPS:
                    pred_taken = self.predictor.predict(instr)
                    cur_state  = self.predictor._get(instr.idx)
                    if_pred_event = {
                        "idx":       instr.idx,
                        "instr":     instr.label(),
                        "predicted_taken": pred_taken,
                        "state":     cur_state,
                        "state_name": _STATE_SHORT[cur_state],
                    }
                    self._fsm_state = cur_state   # glow this state from IF onwards
                    if pred_taken:
                        tgt = instr.idx + instr.imm
                        if 0 <= tgt < len(self.program):
                            # Speculate: advance PC to predicted target
                            self.pc = tgt
                        else:
                            self.pc += 1
                    else:
                        self.pc += 1
                else:
                    self.pc += 1
                p["IF"] = instr
            else:
                p["IF"] = None

        def mark_dest_in_flight(instr):
            if instr and instr.dest and instr.op not in BRANCH_OPS:
                self.READY[instr.dest] = False
                self.PRODUCER[instr.dest] = instr

        if stall:
            p["EX"] = p["OF"]
            p["OF"] = None
        elif branch_flush:
            # EX holds the resolving branch — let it advance to MEM normally.
            # IF/ID/OF were already cleared above; fetch the correct next instruction.
            p["EX"] = p["OF"]  # OF was already cleared to None above
            fetch()
        else:
            p["EX"] = p["OF"]
            entering_of = p["ID"]
            p["OF"] = p["ID"]
            mark_dest_in_flight(entering_of)
            p["ID"] = p["IF"]
            fetch()

        if not any(p.values()) and self.pc >= len(self.program):
            self.done = True

        return dict(
            cycle=self.cycle,
            fsm_state=self._fsm_state,
            if_pred_event=if_pred_event,
            pipe={s: p[s] for s in STAGES},
            regs=dict(self.REG),
            flags=dict(self.FLAGS),
            mem=dict(self.MEM),
            stall=stall,
            stall_info=stall_info,
            branch_flush=branch_flush,
            branch_target=branch_target,
            mispredicted=mispredicted,
            pred_info=pred_info,
            predictor_history=list(self.predictor.history),
            predictor_stats=self.predictor.stats(),
            predictor_table=dict(self.predictor._table),
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
            text=text, fill=TOKEN_FG,
            font=("JetBrains Mono", 9, "bold"),
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
        self.minsize(400, 300)   # window can go very small — content scrolls
        self.geometry("1280x800")

        # Minimum content dimensions — if window is smaller, scrollbars appear
        self._MIN_W = 1060
        self._MIN_H = 660

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
        self._pred_hist_len = 0   # how many resolved-branch rows we've printed

        self._build()

    # ══════════════════════════════════════════════════════════════════════════
    # UI BUILD
    # ══════════════════════════════════════════════════════════════════════════
    def _build(self):
        # ── Fixed top bar — minimal, blends with background ───────────────
        top = tk.Frame(self, bg=BG, pady=4)
        top.pack(fill="x", padx=12)
        self.cycle_lbl = tk.Label(top, text="CYCLE  —",
                                   font=(_CODE_FONT, 12, "bold"), fg=FG2, bg=BG)
        self.cycle_lbl.pack(side="right", padx=8)

        # ── Scrollable viewport ────────────────────────────────────────────
        # Outer frame holds the canvas + scrollbars
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True)

        self._hbar = tk.Scrollbar(outer, orient="horizontal", bg=BG3,
                                   troughcolor=BG2, activebackground=BG3)
        self._vbar = tk.Scrollbar(outer, orient="vertical",   bg=BG3,
                                   troughcolor=BG2, activebackground=BG3)
        self._hbar.pack(side="bottom", fill="x")
        self._vbar.pack(side="right",  fill="y")

        # The viewport canvas — NOT the pipeline canvas, just a scroll container
        self._viewport = tk.Canvas(outer, bg=BG, highlightthickness=0,
                                    xscrollcommand=self._hbar.set,
                                    yscrollcommand=self._vbar.set)
        self._viewport.pack(side="left", fill="both", expand=True)
        self._hbar.config(command=self._viewport.xview)
        self._vbar.config(command=self._viewport.yview)

        # Inner frame lives inside the viewport canvas
        self._inner = tk.Frame(self._viewport, bg=BG)
        self._vp_win = self._viewport.create_window(
            (0, 0), window=self._inner, anchor="nw")

        # Bind resize events to update scroll region and stretch inner frame
        self._inner.bind("<Configure>", self._on_inner_configure)
        self._viewport.bind("<Configure>", self._on_viewport_configure)

        # Mouse-wheel scrolling (works on Windows/macOS/Linux)
        self._viewport.bind_all("<MouseWheel>",         self._on_mousewheel)
        self._viewport.bind_all("<Button-4>",           self._on_mousewheel)
        self._viewport.bind_all("<Button-5>",           self._on_mousewheel)
        self._viewport.bind_all("<Shift-MouseWheel>",   self._on_shift_mousewheel)
        self._viewport.bind_all("<Shift-Button-4>",     self._on_shift_mousewheel)
        self._viewport.bind_all("<Shift-Button-5>",     self._on_shift_mousewheel)
        self._viewport.bind_all("<Shift-Left>",         self._on_shift_left)
        self._viewport.bind_all("<Shift-Right>",        self._on_shift_right)

        # ── Build the three columns inside _inner ──────────────────────────
        self._inner.columnconfigure(0, minsize=240, weight=1)
        self._inner.columnconfigure(1, weight=2)
        self._inner.columnconfigure(2, minsize=220, weight=1)
        self._inner.rowconfigure(0, weight=1)

        left   = tk.Frame(self._inner, bg=BG)
        center = tk.Frame(self._inner, bg=BG)
        right  = tk.Frame(self._inner, bg=BG)
        left.grid  (row=0, column=0, sticky="nsew", padx=(8,5),  pady=(0,8))
        center.grid(row=0, column=1, sticky="nsew", padx=2,      pady=(0,8))
        right.grid (row=0, column=2, sticky="nsew", padx=(5,8),  pady=(0,8))

        self._build_left(left)
        self._build_center(center)
        self._build_right(right)

    # ── Viewport / scroll helpers ──────────────────────────────────────────
    def _on_inner_configure(self, event=None):
        """Update scroll region whenever inner frame changes size."""
        self._viewport.configure(scrollregion=self._viewport.bbox("all"))
        self._update_scrollbars()

    def _on_viewport_configure(self, event=None):
        """Stretch inner frame to fill viewport when window is large enough,
        and hide scrollbars when content fits comfortably."""
        self._update_scrollbars()
        vw = self._viewport.winfo_width()
        vh = self._viewport.winfo_height()
        iw = self._inner.winfo_reqwidth()
        ih = self._inner.winfo_reqheight()
        # If viewport is wider/taller than content, expand inner to fill it
        new_w = max(vw, iw)
        new_h = max(vh, ih)
        self._viewport.itemconfig(self._vp_win, width=new_w, height=new_h)
        # Propagate extra height into the inner grid row so the pipeline canvas grows
        self._inner.rowconfigure(0, minsize=max(new_h - 16, ih), weight=1)

    def _update_scrollbars(self):
        """Show scrollbars only when content overflows the viewport."""
        vw = self._viewport.winfo_width()
        vh = self._viewport.winfo_height()
        iw = self._inner.winfo_reqwidth()
        ih = self._inner.winfo_reqheight()
        # Horizontal bar
        if vw >= iw:
            self._hbar.pack_forget()
        else:
            if not self._hbar.winfo_ismapped():
                self._hbar.pack(side="bottom", fill="x")
        # Vertical bar
        if vh >= ih:
            self._vbar.pack_forget()
        else:
            if not self._vbar.winfo_ismapped():
                self._vbar.pack(side="right", fill="y")

    def _on_mousewheel(self, event):
        """Vertical scroll via mouse wheel. Redirects to horizontal if Shift is held."""
        # event.state bit 0x1 = Shift on all platforms
        if event.state & 0x1:
            self._on_shift_mousewheel(event)
            return
        if self._vbar.winfo_ismapped():
            if event.num == 4:
                self._viewport.yview_scroll(-1, "units")
            elif event.num == 5:
                self._viewport.yview_scroll(1, "units")
            else:
                self._viewport.yview_scroll(int(-event.delta / 40), "units")

    def _on_shift_mousewheel(self, event):
        """Horizontal scroll via Shift+wheel (all platforms)."""
        if self._hbar.winfo_ismapped():
            if event.num == 4:
                self._viewport.xview_scroll(-1, "units")
            elif event.num == 5:
                self._viewport.xview_scroll(1, "units")
            else:
                self._viewport.xview_scroll(int(-event.delta / 40), "units")

    def _on_shift_left(self, event):
        """Horizontal scroll left via Shift+Left."""
        if self._hbar.winfo_ismapped():
            self._viewport.xview_scroll(-3, "units")

    def _on_shift_right(self, event):
        """Horizontal scroll right via Shift+Right."""
        if self._hbar.winfo_ismapped():
            self._viewport.xview_scroll(3, "units")

    # ── LEFT
    def _build_left(self, p):
        p.rowconfigure(1, weight=1)
        p.columnconfigure(0, weight=1)

        # Samples panel — clean listbox selector
        sf = self._section(p, "EXAMPLES", row=0)
        lb_frame = tk.Frame(sf, bg=BG3, bd=1, relief="flat")
        lb_frame.pack(fill="x", pady=(0, 4))
        self._sample_lb = tk.Listbox(lb_frame,
                                     font=FMS, bg=BG3, fg=FG2,
                                     selectbackground=BG2, selectforeground=CYAN,
                                     activestyle="none", relief="flat", bd=0,
                                     highlightthickness=0, cursor="hand2",
                                     height=len(SAMPLES), exportselection=False)
        for name in SAMPLES:
            self._sample_lb.insert("end", "  " + name)
        self._sample_lb.select_set(0)
        self._sample_lb.pack(fill="x")
        self._sample_lb.bind("<Double-Button-1>", lambda e: self._load_selected_sample())
        tk.Button(sf, text="▶  Load Selected", font=FMS,
                  bg=BG2, fg=CYAN, activebackground=BG3, activeforeground=CYAN,
                  relief="flat", bd=0, cursor="hand2", pady=4,
                  command=self._load_selected_sample
                  ).pack(fill="x", pady=(3, 0))

        # Editor — gutter + syntax-highlighted text area
        ef = self._section(p, "PROGRAM EDITOR", row=1, expand=True)
        ed_frame = tk.Frame(ef, bg=BG4)
        ed_frame.pack(fill="both", expand=True)

        # ── Line-number gutter ──────────────────────────────────────────────
        self._gutter = tk.Text(
            ed_frame, bg="#161922", fg="#4a5070",
            font=FM, bd=0, padx=6, pady=8,
            width=3, state="disabled", relief="flat",
            selectbackground="#161922", selectforeground="#4a5070",
            cursor="arrow", takefocus=False,
            highlightthickness=0,
        )
        self._gutter.pack(side="left", fill="y")

        # thin separator line
        tk.Frame(ed_frame, bg="#2a2d3e", width=1).pack(side="left", fill="y")

        # ── Editor ─────────────────────────────────────────────────────────
        ed_scroll = tk.Scrollbar(ed_frame, orient="vertical", bg=BG3,
                                  troughcolor=BG2, activebackground=BG3)
        ed_scroll.pack(side="right", fill="y")
        self.editor = tk.Text(
            ed_frame, bg=BG4, fg=FG, insertbackground=CYAN,
            font=FM, bd=0, padx=8, pady=8,
            selectbackground="#3d4577", selectforeground=FG,
            undo=True, relief="flat",
            yscrollcommand=self._on_editor_scroll,
            highlightthickness=0,
        )
        ed_scroll.config(command=self._sync_editor_scroll)
        self.editor.pack(side="left", fill="both", expand=True)

        # ── Syntax tag definitions ──────────────────────────────────────────
        self.editor.tag_config("op",      foreground=AMBER)
        self.editor.tag_config("branch",  foreground=RED)
        self.editor.tag_config("reg",     foreground="#89b4fa")   # blue
        self.editor.tag_config("imm",     foreground="#a6e3a1")   # green
        self.editor.tag_config("mem",     foreground=ORANGE)
        self.editor.tag_config("label_def", foreground=PURPLE)
        self.editor.tag_config("comment",   foreground="#45475a")
        self.editor.tag_config("current_line", background="#1e2235")

        self.editor.bind("<KeyRelease>",   self._on_editor_key)
        self.editor.bind("<ButtonRelease>", self._on_editor_key)
        self.editor.insert("1.0", SAMPLES["Arithmetic"])
        self._highlight_syntax()
        self._update_gutter()

        # Syntax ref — redesigned as a clean table
        rf = self._section(p, "SYNTAX REFERENCE", row=2)
        syntax_rows = [
            ("MOV",  "Rd, #imm",        "Load immediate"),
            ("ADD",  "Rd, Ra, Rb",       "Addition"),
            ("SUB",  "Rd, Ra, Rb",       "Subtraction"),
            ("AND/OR/XOR", "Rd, Ra, Rb", "Bitwise ops"),
            ("NEG",  "Rd, Rs",           "Negate"),
            ("LD",   "Rd, [Rs+off]",     "Memory load"),
            ("ST",   "Rs, [Rd+off]",     "Memory store"),
            ("JMP",  "±offset",          "Unconditional jump"),
            ("BEQ/BNE", "Ra, Rb, ±off", "Branch equal/not"),
            ("BLT/BGT", "Ra, Rb, ±off", "Branch less/greater"),
        ]
        for op, operands, desc in syntax_rows:
            row_f = tk.Frame(rf, bg=BG2)
            row_f.pack(fill="x", pady=1)
            tk.Label(row_f, text=op, font=(_CODE_FONT, 9, "bold"),
                     fg=CYAN, bg=BG2, width=12, anchor="w").pack(side="left")
            tk.Label(row_f, text=operands, font=(_CODE_FONT, 9),
                     fg=FG2, bg=BG2, width=14, anchor="w").pack(side="left")
            tk.Label(row_f, text=desc, font=(_CODE_FONT, 9),
                     fg=FG3, bg=BG2, anchor="w").pack(side="left")

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
        tk.Label(sp, text="FAST", font=(_CODE_FONT, 8, "bold"), fg=FG3, bg=BG).pack(side="left", padx=4)
        self.speed_var = tk.IntVar(value=700)
        tk.Scale(sp, from_=150, to=2000, orient="horizontal",
                 variable=self.speed_var, bg=BG, fg=FG2, troughcolor=BG3,
                 highlightthickness=0, bd=0, showvalue=False
                 ).pack(side="left", fill="x", expand=True)
        tk.Label(sp, text="SLOW", font=(_CODE_FONT, 8, "bold"), fg=FG3, bg=BG).pack(side="left", padx=4)

    def _section(self, parent, title, row, expand=False):
        outer = tk.Frame(parent, bg=BG2, bd=0, relief="flat")
        kw = dict(row=row, column=0, sticky="nsew" if expand else "ew", pady=(0,4))
        outer.grid(**kw)
        if expand:
            parent.rowconfigure(row, weight=1)
        tk.Label(outer, text=title, font=FLB, fg=CYAN, bg=BG3,
                 padx=8, pady=5).pack(fill="x")
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

        hdr = tk.Frame(p, bg=BG3, padx=8, pady=5)
        hdr.grid(row=0, column=0, sticky="ew", pady=(0,4))
        tk.Label(hdr, text="PIPELINE DATAPATH", font=FLB, fg=CYAN, bg=BG3).pack(side="left")
        self.status_lbl = tk.Label(hdr, text="", font=FLB, fg=FG2, bg=BG3)
        self.status_lbl.pack(side="right")

        self.canvas = tk.Canvas(p, bg=BG2, highlightthickness=0, height=760)
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", self._on_resize)

        log_wrap = tk.Frame(p, bg=BG2)
        log_wrap.grid(row=2, column=0, sticky="ew", pady=(4,0))
        tk.Label(log_wrap, text="EVENT LOG", font=FLB, fg=CYAN, bg=BG3,
                 padx=8, pady=5).pack(fill="x")
        self.log = tk.Text(log_wrap, bg=BG4, fg=FG2, font=FMS, bd=0,
                            padx=8, pady=6, height=7,
                            state="disabled", wrap="word", relief="flat")
        sb = tk.Scrollbar(log_wrap, command=self.log.yview, bg=BG3,
                          troughcolor=BG2, activebackground=BG3)
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
        tk.Label(rf, text="REGISTER FILE", font=FLB, fg=CYAN, bg=BG3,
                 padx=8, pady=5).pack(fill="x")
        grid = tk.Frame(rf, bg=BG2, padx=4, pady=4)
        grid.pack(fill="both")
        self.reg_labels = {}
        for i in range(16):
            rn = f"R{i}"
            row_, col_ = divmod(i, 2)
            tk.Label(grid, text=f"{rn:>3}", font=FMB, fg=FG2, bg=BG2,
                     width=4, anchor="e").grid(row=row_, column=col_*2,
                                               padx=(4,0), pady=2, sticky="e")
            vl = tk.Label(grid, text="0", font=FM, fg=FG, bg=BG4,
                          width=8, anchor="e", padx=3)
            vl.grid(row=row_, column=col_*2+1, padx=(2,6), pady=1, sticky="ew")
            self.reg_labels[rn] = vl

        # ── CPU Status Flags — shown in the empty space below registers ──────
        sep = tk.Frame(grid, bg=BG3, height=1)
        sep.grid(row=8, column=0, columnspan=4, sticky="ew", pady=(6, 2))
        tk.Label(grid, text="FLAGS", font=FLB, fg=CYAN, bg=BG2,
                 anchor="w").grid(row=9, column=0, columnspan=4,
                                  padx=4, pady=(0,4), sticky="w")

        self._flag_labels = {}
        _FLAG_DEFS = [
            # (display_name, key,   color,  row, label_col, val_col)
            ("NEG",   "neg",   RED,   10, 0, 1),
            ("CARRY", "carry", AMBER, 10, 2, 3),
            ("ZERO",  "zero",  GREEN, 11, 0, 1),
        ]
        for fname, fkey, fcol, frow, lcol, vcol in _FLAG_DEFS:
            tk.Label(grid, text=fname, font=(_CODE_FONT, 8, "bold"),
                     fg=FG3, bg=BG2, width=6, anchor="e"
                     ).grid(row=frow, column=lcol, padx=(4, 0), pady=2, sticky="e")
            fl = tk.Label(grid, text="0", font=FMB,
                          fg=FG3, bg=BG4, width=3, anchor="c", relief="flat", padx=2)
            fl.grid(row=frow, column=vcol, padx=(2, 6), pady=1, sticky="ew")
            self._flag_labels[fkey] = (fl, fcol)

        hf = tk.Frame(p, bg=BG2)
        hf.grid(row=1, column=0, sticky="ew", pady=(0,4))
        tk.Label(hf, text="HAZARD STATUS", font=FLB, fg=CYAN, bg=BG3,
                 padx=8, pady=5).pack(fill="x")
        self.hazard_lbl = tk.Label(hf, text="--  clear", font=FMS,
                                    fg=GREEN, bg=BG2, padx=8, pady=8,
                                    justify="left", anchor="w")
        self.hazard_lbl.pack(fill="x")

        mf = tk.Frame(p, bg=BG2)
        mf.grid(row=2, column=0, sticky="nsew", pady=(0,4))
        tk.Label(mf, text="MEMORY", font=FLB, fg=CYAN, bg=BG3,
                 padx=8, pady=5).pack(fill="x")
        self.mem_text = tk.Text(mf, bg=BG4, fg=ORANGE, font=FMS, bd=0,
                                 padx=8, pady=6, height=7, state="disabled",
                                 relief="flat")
        self.mem_text.pack(fill="both", expand=True)

        pcf = tk.Frame(p, bg=BG3, padx=8, pady=8)
        pcf.grid(row=3, column=0, sticky="ew")
        tk.Label(pcf, text="PC ->", font=FLB, fg=FG2, bg=BG3).pack(side="left")
        self.pc_lbl = tk.Label(pcf, text="--",
                                font=(_CODE_FONT, 14, "bold"), fg=CYAN, bg=BG3)
        self.pc_lbl.pack(side="right")

        # ── 2-Bit Smith Branch Predictor panel ─────────────────────────────
        bpf = tk.Frame(p, bg=BG2)
        bpf.grid(row=4, column=0, sticky="nsew", pady=(4, 0))
        p.rowconfigure(4, weight=1)

        tk.Label(bpf, text="2-BIT BRANCH PREDICTOR", font=FLB, fg=PURPLE, bg=BG3,
                 padx=8, pady=5).pack(fill="x")

        # Stats bar
        stats_bar = tk.Frame(bpf, bg=BG3, padx=6, pady=4)
        stats_bar.pack(fill="x")
        tk.Label(stats_bar, text="Predictions:", font=FMS, fg=FG2, bg=BG3).pack(side="left")
        self.pred_total_lbl = tk.Label(stats_bar, text="0", font=FMB, fg=CYAN, bg=BG3, width=4)
        self.pred_total_lbl.pack(side="left", padx=(2, 8))
        tk.Label(stats_bar, text="Correct:", font=FMS, fg=FG2, bg=BG3).pack(side="left")
        self.pred_correct_lbl = tk.Label(stats_bar, text="0", font=FMB, fg=GREEN, bg=BG3, width=4)
        self.pred_correct_lbl.pack(side="left", padx=(2, 8))
        tk.Label(stats_bar, text="Accuracy:", font=FMS, fg=FG2, bg=BG3).pack(side="left")
        self.pred_acc_lbl = tk.Label(stats_bar, text="--", font=FMB, fg=AMBER, bg=BG3, width=6)
        self.pred_acc_lbl.pack(side="left")

        # FSM state diagram (canvas)
        fsm_frame = tk.Frame(bpf, bg=BG2, pady=4)
        fsm_frame.pack(fill="x")
        self.fsm_canvas = tk.Canvas(fsm_frame, bg=BG2, height=90,
                                     highlightthickness=0)
        self.fsm_canvas.pack(fill="x", padx=6)
        self.fsm_canvas.bind("<Configure>", self._draw_fsm)

        # Last prediction detail
        pred_lbl_frame = tk.Frame(bpf, bg=BG2, padx=6, pady=2)
        pred_lbl_frame.pack(fill="x")
        tk.Label(pred_lbl_frame, text="Last branch:", font=FMS, fg=FG3, bg=BG2).pack(anchor="w")
        self.pred_last_lbl = tk.Label(pred_lbl_frame, text="(none yet)",
                                       font=FMS, fg=FG2, bg=BG2, justify="left", anchor="w",
                                       wraplength=200)
        self.pred_last_lbl.pack(fill="x")

        # History log
        tk.Label(bpf, text="PREDICTION HISTORY", font=FLB, fg=PURPLE, bg=BG3,
                 padx=8, pady=3).pack(fill="x")
        hist_wrap = tk.Frame(bpf, bg=BG2)
        hist_wrap.pack(fill="both", expand=True)
        self.pred_hist = tk.Text(hist_wrap, bg=BG4, fg=FG2, font=FMS, bd=0,
                                  padx=6, pady=4, height=5, state="disabled",
                                  relief="flat", wrap="none")
        pred_sb = tk.Scrollbar(hist_wrap, command=self.pred_hist.yview,
                                bg=BG3, troughcolor=BG2, activebackground=BG3)
        self.pred_hist.config(yscrollcommand=pred_sb.set)
        self.pred_hist.pack(side="left", fill="both", expand=True)
        pred_sb.pack(side="right", fill="y")
        self.pred_hist.tag_config("correct",   foreground=GREEN)
        self.pred_hist.tag_config("wrong",     foreground=RED)
        self.pred_hist.tag_config("predict",   foreground=CYAN)
        self.pred_hist.tag_config("header",    foreground=PURPLE)

        self.pred_table_lbl = tk.Label(bpf, text="(no branches seen)",  # hidden, kept for compat
                                        font=FMS, fg=FG2, bg=BG2,
                                        justify="left", anchor="w", padx=6, pady=0)
        # counter table intentionally not packed (removed from UI)

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

        n      = len(STAGES)
        PX     = 20
        PY     = 10
        GAP    = 28          # gap between stage cards (longer arrows)
        HDR    = 26          # height of the stage-name header stripe inside each box
        sh     = 130         # fixed card height (taller = more square)
        # Cap width so stages don't become ultra-wide rectangles
        sw     = min(max(W - 2*PX, 80), W - 2*PX)
        # Centre the stages horizontally if canvas is very wide
        target_w = min(sw, int(sh * 1.8))  # max ~1.8:1 aspect ratio → more square
        sx     = PX + max(0, (sw - target_w) // 2)
        sw     = target_w

        self._stage_rects.clear()

        total_h = PY + n * sh + (n - 1) * GAP
        offset_y = max(0, (H - total_h) // 2)

        for i, s in enumerate(STAGES):
            y0 = offset_y + PY + i * (sh + GAP)
            y1 = y0 + sh
            x0 = sx
            x1 = sx + sw
            acc = STAGE_ACCENT[s]
            bg  = STAGE_BG[s]

            # subtle drop-shadow
            c.create_rectangle(x0+4, y0+4, x1+4, y1+4,
                                fill="#0a0a0f", outline="", tags="stage")
            # card body
            c.create_rectangle(x0, y0, x1, y1,
                                fill=bg, outline=acc, width=2, tags="stage")
            # top header stripe with stage name inside
            c.create_rectangle(x0+2, y0+2, x1-2, y0+HDR,
                                fill=acc, outline="", tags="stage")
            c.create_text((x0+x1)/2, y0 + HDR/2 + 1,
                          text=s, font=(_CODE_FONT, 11, "bold"),
                          fill=TOKEN_FG, tags="stage")

            # downward arrow between stages (longer to fill the bigger gap)
            if i < n - 1:
                ax = (x0 + x1) / 2
                c.create_line(ax, y1+3, ax, y1+GAP-4,
                               fill=ARROW_COL, width=2,
                               arrow="last", arrowshape=(8, 11, 5), tags="stage")

            self._stage_rects[s] = (x0, y0, x1, y1)

        self._draw_bubbles()

    def _draw_bubbles(self):
        self.canvas.delete("bubble")
        for stage, uid in self._stage_uid.items():
            if uid is None and stage in self._stage_rects:
                tx, ty, tw, th = self._token_geom(stage)
                # Make bubble square: use the smaller dimension
                sq = min(tw, th)
                bx = tx + (tw - sq) / 2
                by = ty + (th - sq) / 2
                self.canvas.create_rectangle(
                    bx, by, bx+sq, by+sq,
                    fill="", outline=BUBBLE_COL, dash=(4, 5), width=1, tags="bubble")
                self.canvas.create_text(
                    bx+sq/2, by+sq/2, text="bubble",
                    font=(_CODE_FONT, 8), fill=BUBBLE_COL, tags="bubble")

    def _draw_forwarding_arrows(self, fwd_pairs):
        """Orthogonal forwarding arrows: bottom-of-src → down → left → up → top-of-dst.

        Route (5 waypoints, 4 right-angle segments):
          P0  bottom-left of source  (exit point)
          P1  go DOWN  DROP pixels below P0
          P2  go LEFT  to the routing rail
          P3  go UP    to top-body level of destination
          P4  go RIGHT into destination (arrow tip)
        """
        c = self.canvas
        c.delete("fwd_arrow")
        if not fwd_pairs or not self._stage_rects:
            return

        FWD_COL  = "#f0a500"   # warm gold — distinct & vivid
        GLOW_MID = "#5a3a00"
        GLOW_OUT = "#1a0f00"
        HDR      = 26    # header stripe height — must match _redraw_stages
        DROP     = 14    # px to drop below the source card before turning

        seen, unique = set(), []
        for pair in fwd_pairs:
            if pair not in seen:
                seen.add(pair); unique.append(pair)

        def _draw_route(pts, label):
            c.create_line(*pts, fill=GLOW_OUT, width=9,  joinstyle="miter", tags="fwd_arrow")
            c.create_line(*pts, fill=GLOW_MID, width=5,  joinstyle="miter", tags="fwd_arrow")
            c.create_line(*pts, fill=FWD_COL,  width=2,  joinstyle="miter",
                          arrow="last", arrowshape=(10, 13, 5), tags="fwd_arrow")

            # Label badge on the vertical segment (P2→P3: pts[4..7])
            vx = pts[4]; vy = (pts[5] + pts[7]) / 2
            pad_x, pad_y = 5, 3
            est_w = len(label) * 7; est_h = 13
            bx0 = vx - est_w - pad_x*2 - 2
            by0 = vy - est_h/2 - pad_y
            c.create_rectangle(bx0, by0, bx0+est_w+pad_x*2, by0+est_h+pad_y*2,
                                fill="#0d1f35", outline=FWD_COL, width=1, tags="fwd_arrow")
            c.create_text(vx - pad_x - 2, vy + 1, text=label,
                          font=(_CODE_FONT, 8, "bold"), fill=FWD_COL,
                          anchor="e", tags="fwd_arrow")

        for rank, (src_stage, dst_stage) in enumerate(unique):
            if src_stage not in self._stage_rects or dst_stage not in self._stage_rects:
                continue

            sx0, sy0, sx1, sy1 = self._stage_rects[src_stage]
            dx0, dy0, dx1, dy1 = self._stage_rects[dst_stage]
            bulge = 42 + rank * 24   # rail distance left of stage edge

            label = f"{src_stage}\u2192{dst_stage}"

            # P0: bottom of source, shifted ~1/4 inward from left edge
            inset = (sx1 - sx0) // 4
            p0x, p0y = sx0 + inset, sy1
            # P1: go DOWN
            p1x, p1y = sx0 + inset, sy1 + DROP
            # P2: go LEFT to rail
            p2x, p2y = sx0 - bulge, sy1 + DROP
            # P3: go UP to top-body of destination
            p3x, p3y = sx0 - bulge, dy0 + HDR + 4
            # P4: go RIGHT into destination
            p4x, p4y = dx0, dy0 + HDR + 4

            pts = [p0x, p0y, p1x, p1y, p2x, p2y, p3x, p3y, p4x, p4y]
            _draw_route(pts, label)

        c.tag_raise("fwd_arrow")
        c.tag_raise("tok")


    def _token_geom(self, stage):
        """Return (x, y, w, h) for a token inside stage — below the header stripe."""
        x0, y0, x1, y1 = self._stage_rects[stage]
        HDR    = 26
        pad_x  = 10
        pad_y  = 8
        tx  = x0 + pad_x
        ty  = y0 + HDR + pad_y
        tw  = (x1 - x0) - pad_x * 2
        th  = (y1 - y0) - HDR - pad_y * 2
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
        self.canvas.delete("fwd_arrow")

    # ══════════════════════════════════════════════════════════════════════════
    # EDITOR HELPERS  — gutter, scroll sync, syntax highlighting
    # ══════════════════════════════════════════════════════════════════════════
    def _on_editor_scroll(self, *args):
        """Keep gutter in sync when editor scrolls via mouse/keyboard."""
        self._gutter.yview_moveto(args[0])

    def _sync_editor_scroll(self, *args):
        """Scrollbar commands forwarded to both widgets."""
        self.editor.yview(*args)
        self._gutter.yview(*args)

    def _on_editor_key(self, event=None):
        self._update_gutter()
        self._highlight_syntax()

    def _update_gutter(self):
        """Rebuild the line-number gutter to match current editor content."""
        lines = int(self.editor.index("end-1c").split(".")[0])
        self._gutter.config(state="normal")
        self._gutter.delete("1.0", "end")
        for i in range(1, lines + 1):
            self._gutter.insert("end", f"{i:>2}\n")
        # Sync gutter width to number of digits
        w = max(2, len(str(lines))) + 1
        self._gutter.config(width=w, state="disabled")
        # Keep gutter scrolled to same position as editor
        self._gutter.yview_moveto(self.editor.yview()[0])

    def _highlight_syntax(self):
        """Apply colour tags for assembly syntax highlighting."""
        import re as _re
        ed = self.editor
        # Remove all old syntax tags
        for tag in ("op", "branch", "reg", "imm", "mem", "label_def", "comment", "current_line"):
            ed.tag_remove(tag, "1.0", "end")

        # Highlight current line
        cur_line = ed.index("insert").split(".")[0]
        ed.tag_add("current_line", f"{cur_line}.0", f"{cur_line}.end+1c")

        content = ed.get("1.0", "end-1c")
        line_start = 0
        for lineno, line in enumerate(content.split("\n"), start=1):
            base = f"{lineno}.0"

            # — Comment  (; to end of line)
            m = _re.search(r';.*$', line)
            if m:
                ed.tag_add("comment", f"{lineno}.{m.start()}", f"{lineno}.{m.end()}")
                # Only highlight the code part before the comment
                line = line[:m.start()]

            # — Label definition  (word followed by colon at start)
            m = _re.match(r'^(\w+):', line)
            if m:
                ed.tag_add("label_def", f"{lineno}.0", f"{lineno}.{m.end()}")
                line = line[m.end():]  # strip label for further parsing
                col_off = m.end()
            else:
                col_off = 0

            stripped = line.lstrip()
            indent   = len(line) - len(stripped)
            col_off += indent

            # — Opcode  (first token)
            m = _re.match(r'^([A-Za-z]+)', stripped)
            if m:
                op = m.group(1).upper()
                tag = "branch" if op in BRANCH_OPS else "op"
                ed.tag_add(tag, f"{lineno}.{col_off}",
                               f"{lineno}.{col_off + m.end()}")
                rest      = stripped[m.end():]
                rest_off  = col_off + m.end()
            else:
                rest     = stripped
                rest_off = col_off

            # — Memory  ([Rs+off] or [Rs])
            for mm in _re.finditer(r'\[.*?\]', rest):
                ed.tag_add("mem", f"{lineno}.{rest_off + mm.start()}",
                                   f"{lineno}.{rest_off + mm.end()}")

            # — Registers  (R0–R15 as whole words)
            for mm in _re.finditer(r'\bR(1[0-5]|[0-9])\b', rest, _re.IGNORECASE):
                ed.tag_add("reg", f"{lineno}.{rest_off + mm.start()}",
                                   f"{lineno}.{rest_off + mm.end()}")

            # — Immediates  (#number or bare ±number after comma)
            # Two passes to avoid variable-width lookbehind (Python 3.14+)
            for mm in _re.finditer(r'#-?\d+', rest):
                ed.tag_add("imm", f"{lineno}.{rest_off + mm.start()}",
                                   f"{lineno}.{rest_off + mm.end()}")
            for mm in _re.finditer(r',\s*(-?\d+)\b', rest):
                s = rest_off + mm.start(1)
                ed.tag_add("imm", f"{lineno}.{s}",
                                   f"{lineno}.{s + len(mm.group(1))}")

    def _load_sample(self, name):
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", SAMPLES[name])
        self._highlight_syntax()
        self._update_gutter()

    def _load_selected_sample(self):
        sel = self._sample_lb.curselection()
        if sel:
            name = list(SAMPLES.keys())[sel[0]]
            self._load_sample(name)

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
        self._update_regs({f"R{i}": 0 for i in range(16)},
                          {"neg": False, "carry": False, "zero": False})
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
        self._update_regs({f"R{i}": 0 for i in range(16)},
                          {"neg": False, "carry": False, "zero": False})
        self._update_mem({})
        # Clear predictor panel
        self.pred_total_lbl.config(text="0")
        self.pred_correct_lbl.config(text="0")
        self.pred_acc_lbl.config(text="--", fg=AMBER)
        self.pred_last_lbl.config(text="(none yet)", fg=FG2)
        self.pred_table_lbl.config(text="(no branches seen)")
        self._pred_hist_len = 0
        self.pred_hist.config(state="normal")
        self.pred_hist.delete("1.0","end")
        self.pred_hist.config(state="disabled")
        self._draw_fsm()
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

        self.canvas.delete("fwd_arrow")


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
            mp = state.get("mispredicted", False)
            pi = state.get("pred_info")
            if mp and pi:
                self.hazard_lbl.config(
                    text=f"BRANCH MISPREDICTED\n"
                         f"  {pi['instr']}\n"
                         f"  {pi['old_name']} -> {pi['new_name']}\n"
                         f"  -> I{state['branch_target']}", fg=RED)
            else:
                self.hazard_lbl.config(
                    text=f"BRANCH TAKEN\n  -> I{state['branch_target']}", fg=PURPLE)
        else:
            self.hazard_lbl.config(text="--  clear", fg=GREEN)

        self._update_regs(state["regs"], state.get("flags"))
        self._update_mem(state["mem"])
        self._update_predictor_ui(state)

        self._log(f"-- Cycle {cyc} --", "cycle")
        for kind, msg in state["events"]:
            self._log(f"  {msg}", kind)

        if state["done"]:
            self._finish()

    def _update_regs(self, regs, flags=None):
        for rn, lbl in self.reg_labels.items():
            val = regs.get(rn, 0)
            lbl.config(text=str(val))
            if val != self._prev_regs.get(rn, 0):
                flash_bg = "#1e3a1e"
                lbl.config(fg=GREEN, bg=flash_bg)
                self.after(500, lambda l=lbl: l.config(fg=FG, bg=BG4))
        self._prev_regs = dict(regs)
        # Update flag indicators
        if flags is not None:
            for fkey, (fl, fcol) in self._flag_labels.items():
                active = flags.get(fkey, False)
                fl.config(text="1" if active else "0",
                          fg=fcol if active else FG3,
                          bg="#1a1a2a" if active else BG4)

    def _update_mem(self, mem):
        self.mem_text.config(state="normal")
        self.mem_text.delete("1.0","end")
        if mem:
            for a in sorted(mem):
                self.mem_text.insert("end", f"  [{a:08x}] = {mem[a]}\n")
        else:
            self.mem_text.insert("end","  (empty)")
        self.mem_text.config(state="disabled")

    def _draw_fsm(self, event=None, active_state=None):
        """Draw the 2-bit FSM state diagram on self.fsm_canvas."""
        c = self.fsm_canvas
        c.delete("all")
        W = c.winfo_width()
        H = c.winfo_height()
        if W < 30 or H < 30:
            return

        # 4 states arranged left to right: SNT  WNT  WT  ST
        labels   = ["SNT", "WNT", "WT", "ST"]
        full_labels = ["Strongly\nNot Taken", "Weakly\nNot Taken", "Weakly\nTaken", "Strongly\nTaken"]
        colors_normal = [RED, "#c45070", "#7aaf7a", GREEN]
        r = min(16, H // 3)
        margin = r + 4
        spacing = (W - 2 * margin) / 3

        centers = [(int(margin + i * spacing), H // 2) for i in range(4)]

        # Draw arrows between states
        arrow_opts = dict(fill=FSM_ARROW, width=1, arrow="last", arrowshape=(6, 8, 3))
        for i in range(3):
            cx1, cy1 = centers[i]
            cx2, cy2 = centers[i+1]
            # Not-taken arrow (goes left, above)
            c.create_line(cx2 - r, cy2 - 4, cx1 + r, cy1 - 4,
                          **arrow_opts)
            # Taken arrow (goes right, below)
            c.create_line(cx1 + r, cy1 + 4, cx2 - r, cy2 + 4,
                          **arrow_opts)

        # Self-loops at ends
        c.create_arc(centers[0][0] - r - 10, centers[0][1] - r,
                     centers[0][0] - r + 2, centers[0][1] + r,
                     start=90, extent=180, style="arc",
                     outline=FSM_ARROW, width=1)
        c.create_arc(centers[3][0] + r - 2, centers[3][1] - r,
                     centers[3][0] + r + 10, centers[3][1] + r,
                     start=270, extent=180, style="arc",
                     outline=FSM_ARROW, width=1)

        # Draw state circles
        for i, (cx, cy) in enumerate(centers):
            is_active = (i == active_state)
            fill  = colors_normal[i] if is_active else BG3
            out   = colors_normal[i]
            width = 3 if is_active else 1
            c.create_oval(cx - r, cy - r, cx + r, cy + r,
                          fill=fill, outline=out, width=width)
            c.create_text(cx, cy,
                          text=labels[i],
                          font=(_CODE_FONT, 7, "bold"),
                          fill=TOKEN_FG if is_active else out)

        # Taken / Not-taken labels on arrows
        if W > 200:
            mid = centers[1][0]
            c.create_text(mid, H // 2 - r - 6,  text="Not taken →",
                          font=(_CODE_FONT, 7), fill=FSM_ARROW)
            c.create_text(mid, H // 2 + r + 6,  text="← Taken",
                          font=(_CODE_FONT, 7), fill=FSM_ARROW)

    def _update_predictor_ui(self, state):
        """Refresh all predictor widgets from the latest engine state."""
        total, correct = state.get("predictor_stats", (0, 0))
        self.pred_total_lbl.config(text=str(total))
        self.pred_correct_lbl.config(text=str(correct))
        if total > 0:
            acc = 100 * correct / total
            self.pred_acc_lbl.config(text=f"{acc:.0f}%",
                                      fg=GREEN if acc >= 60 else RED)
        else:
            self.pred_acc_lbl.config(text="--", fg=AMBER)

        # FSM diagram — always glow the current persistent state
        active_state = state.get("fsm_state")   # set every cycle by engine
        self._draw_fsm(active_state=active_state)

        # Update last-prediction label only when a branch resolves in EX
        pred_info = state.get("pred_info")
        if pred_info:
            outcome  = "✓ CORRECT" if pred_info["correct"] else "✗ WRONG"
            pred_str = "TAKEN" if pred_info["predicted_taken"] else "NOT TAKEN"
            act_str  = "TAKEN" if pred_info["actually_taken"]  else "NOT TAKEN"
            col = GREEN if pred_info["correct"] else RED
            self.pred_last_lbl.config(
                text=f"{pred_info['instr']}\n"
                     f"  Predicted: {pred_str}  Actual: {act_str}\n"
                     f"  State: {pred_info['old_name']} → {pred_info['new_name']}  {outcome}",
                fg=col)

        # History log — two rows per branch: IF prediction + EX resolution
        # IF-stage row: printed when a branch is fetched
        if_ev = state.get("if_pred_event")
        if if_ev:
            pred_str = "T" if if_ev["predicted_taken"] else "N"
            line = (f"→ I{if_ev['idx']} {if_ev['instr'][:16]:16s}  "
                    f"pred:{pred_str}  [{if_ev['state_name']}] (IF)\n")
            self.pred_hist.config(state="normal")
            self.pred_hist.insert("end", line, "predict")
            self.pred_hist.see("end")
            self.pred_hist.config(state="disabled")

        # EX-resolution row: printed only when a new entry appears in history
        history = state.get("predictor_history", [])
        new_len = len(history)
        if new_len > self._pred_hist_len:
            for entry in history[self._pred_hist_len:]:
                tag = "correct" if entry["correct"] else "wrong"
                sym = "✓" if entry["correct"] else "✗"
                act = "T" if entry["taken"] else "N"
                line = (f"{sym} I{entry['idx']} {entry['instr'][:16]:16s}  "
                        f"act:{act}  {_STATE_SHORT[entry['old']]}→{_STATE_SHORT[entry['new']]} (EX)\n")
                self.pred_hist.config(state="normal")
                self.pred_hist.insert("end", line, tag)
                self.pred_hist.see("end")
                self.pred_hist.config(state="disabled")
            self._pred_hist_len = new_len

        # Counter table
        table = state.get("predictor_table", {})
        if table:
            lines = []
            for idx in sorted(table):
                s = table[idx]
                lines.append(f"  I{idx}: {_STATE_SHORT[s]} ({s})")
            self.pred_table_lbl.config(text="\n".join(lines))
        else:
            self.pred_table_lbl.config(text="(no branches seen)")

    def _log(self, msg, tag=""):
        self.log.config(state="normal")
        self.log.insert("end", msg+"\n", tag)
        self.log.see("end")
        if int(self.log.index("end").split(".")[0]) > 400:
            self.log.delete("1.0","60.0")
        self.log.config(state="disabled")


if __name__ == "__main__":
    App().mainloop()
