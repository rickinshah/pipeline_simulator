# Pipeline Simulator

A visual, interactive pipeline simulator built with Tkinter that models a scalar 6-stage CPU pipeline.
It is designed for understanding instruction flow, hazards, forwarding, and branching behavior through a step-by-step graphical interface.

## Overview

This project simulates a 6-stage instruction pipeline:
- IF - Instruction Fetch
- ID - Instruction Decode
- OF – Operand Fetch
- EX – Execute
- MEM – Memory Access
- WB – Write Back

Each instruction is represented as a moving token that flows through the pipeline stages, making internal behavior visually traceable.

## Features

- Cycle-by-cycle pipeline execution
- Two-pass assembler with label support
- Load-use hazard detection (stalling)
- Data forwarding (EX/MEM/WB → EX)
- Supports conditional and unconditional branches:
    - `JMP`, `BEQ`, `BNE`, `BLT`, `BGT`, `BLE`, `BGE`
- Pipeline flush on branch taken

## Supported Instructions Set

```
MOV Rd, #imm
ADD Rd, Ra, Rb
SUB Rd, Ra, Rb
AND Rd, Ra, Rb
OR  Rd, Ra, Rb
XOR Rd, Ra, Rb
NEG Rd, Rs

LD Rd, [Rs + offset]
ST Rs, [Rd + offset]

JMP offset
BEQ Ra, Rb, offset
BNE Ra, Rb, offset
BLT Ra, Rb, offset
BGT Ra, Rb, offset
BLE Ra, Rb, offset
BGE Ra, Rb, offset
```

## Running the Simulator

### Requirements

- Python 3.x
- Tkinter

### Run

```
python main.py
```

