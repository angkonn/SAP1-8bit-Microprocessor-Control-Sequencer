# 8-Bit SAP-1 Microprocessor with Python Assembler & Auto-Loader

A fully operational, custom **8-bit SAP-1 (Simple-As-Possible) Microprocessor** designed and simulated in **Logisim-evolution**, complete with a custom software toolchain (Python Assembler) and automated hardware memory loading[cite: 103, 104]. 

Developed as part of the **ETE 404: VLSI Technology Sessional** project at the Chittagong University of Engineering & Technology (CUET)[cite: 14, 104].

---

## Key Features & Architecture
* **Data & Address Bus:** 8-bit main data bus and 4-bit memory address bus (supporting 16 unique RAM locations)[cite: 103].
* **Registers:** 8-bit Accumulator ($A$), 8-bit $B$ Register, 8-bit Instruction Register ($IR$), 4-bit Program Counter ($PC$), and 4-bit Memory Address Register ($MAR$)[cite: 103, 104].
* **Instruction Set Architecture (ISA):** 16 custom instructions including Arithmetic (`ADD`, `SUB`), Logical (`AND`, `OR`, `XOR`, `CLR`), Data Movement (`LDA`, `LDB`, `STA`), Branching (`JMP`, `JC`, `JNZ`), and Advanced Bit Manipulation (`SHIFT`, `ROTATE`).
* **Advanced Bit Manipulation Units:** Dedicated 8-bit **Barrel Shifter** and **Ring Rotator** supporting variable-distance logical shifts and cyclic rotations ranging from 0 to 7 bit positions[cite: 103].
* **Flag System:** Synchronous 1-bit Carry Register and combinational Zero Detector (8-input NOR) for conditional branching[cite: 55, 56, 104].
* **Python Assembler (`assembler_8bit.py`):** Translates human-readable assembly code with labels, `.ORG` offsets, and `DB` data directives into Logisim-compatible `v3.0 hex words`[cite: 10, 63, 104].
* **RAM Auto-Loader:** Debug-protocol based hardware auto-loader that copies machine code from template ROM into the active SRAM seamlessly[cite: 13, 63, 104].

---

## Repository Structure
```text
SAP1_8bit_Project/
│
├── SAP1_8bit_Final.circ          # Main Logisim Project file
├── assembler_8bit.py             # Custom Python Assembler
├── README.md                     # Project Documentation
├── Project_Report.pdf            # Complete LaTeX Project Report
│
├── programs/                     # Assembly Source Files (.asm)
│   ├── program.asm
│   └── test_cases.asm
│
├── generated_memory/             # Assembled Hex Files (.hex)
│   └── ram_image.hex
│
└── screenshots/                  # Circuit and Simulation Snapshots
    ├── overall_processor.png
    ├── alu.png
    ├── control_sequencer.png
    ├── barrel_shifter.png
    └── ring_rotator.png
