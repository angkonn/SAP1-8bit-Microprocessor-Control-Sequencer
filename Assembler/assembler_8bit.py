#!/usr/bin/env python3
"""
Assembler for the custom 8-bit SAP-1 processor.

Instruction format:
    bits 7..4 = 4-bit opcode
    bits 3..0 = 4-bit operand

RAM:
    16 addresses × 8 bits

Usage:
    python assembler_8bit.py program.asm

Outputs:
    ram_image.hex  - Logisim v3.0 hexadecimal image
    listing.txt    - address-by-address assembly listing
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


OPCODES = {
    "NOP":    0x0,
    "LDA":    0x1,
    "LDB":    0x2,
    "STA":    0x3,
    "ADD":    0x4,
    "SUB":    0x5,
    "AND":    0x6,
    "OR":     0x7,
    "XOR":    0x8,
    "CLR":    0x9,
    "JMP":    0xA,
    "JC":     0xB,
    "JNZ":    0xC,
    "SHIFT":  0xD,
    "ROTATE": 0xE,
    "HLT":    0xF,
}

ADDRESS_OPS = {"LDA", "LDB", "STA", "JMP", "JC", "JNZ"}
NO_OPERAND_OPS = {"NOP", "ADD", "SUB", "AND", "OR", "XOR", "CLR", "HLT"}
MODE_OPS = {"SHIFT", "ROTATE"}

RAM_SIZE = 16


class AssemblerError(Exception):
    pass


@dataclass
class SourceLine:
    number: int
    text: str
    label: str | None
    statement: str


def remove_comment(line: str) -> str:
    """Remove ';' or '#' comments."""
    semicolon = line.find(";")
    hash_mark = line.find("#")
    cuts = [p for p in (semicolon, hash_mark) if p != -1]
    if cuts:
        line = line[:min(cuts)]
    return line.strip()


def split_label(line: str, line_number: int) -> tuple[str | None, str]:
    """Return (label, remaining statement)."""
    if ":" not in line:
        return None, line.strip()

    label_text, statement = line.split(":", 1)
    label = label_text.strip().upper()

    if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", label):
        raise AssemblerError(
            f"Line {line_number}: invalid label '{label_text.strip()}'."
        )

    return label, statement.strip()


def parse_number(token: str, bits: int, line_number: int) -> int:
    """
    Parse a number with b/d/h suffix.

    Examples:
        1010b
        10d
        0Ah
    """
    tok = token.strip().lower()

    if not re.fullmatch(r"[0-9a-f]+[bdh]", tok):
        raise AssemblerError(
            f"Line {line_number}: invalid number '{token}'. "
            "Use a b/d/h suffix, for example 1010b, 10d, or 0Ah."
        )

    digits, suffix = tok[:-1], tok[-1]
    base = {"b": 2, "d": 10, "h": 16}[suffix]

    try:
        value = int(digits, base)
    except ValueError as exc:
        raise AssemblerError(
            f"Line {line_number}: bad numeric format '{token}'."
        ) from exc

    maximum = (1 << bits) - 1
    if not 0 <= value <= maximum:
        raise AssemblerError(
            f"Line {line_number}: value '{token}' does not fit in {bits} bits "
            f"(allowed 0 to {maximum})."
        )

    return value


def resolve_value(
    token: str,
    labels: dict[str, int],
    bits: int,
    line_number: int,
) -> int:
    """Resolve either a label or a suffixed number."""
    name = token.strip().upper()
    if name in labels:
        value = labels[name]
        maximum = (1 << bits) - 1
        if not 0 <= value <= maximum:
            raise AssemblerError(
                f"Line {line_number}: label '{token}' resolves to {value}, "
                f"which does not fit in {bits} bits."
            )
        return value

    return parse_number(token, bits, line_number)


def statement_size(statement: str, line_number: int) -> int:
    """Return the number of RAM bytes occupied by a statement."""
    if not statement:
        return 0

    parts = statement.replace(",", " ").split()
    keyword = parts[0].upper()

    if keyword == ".ORG":
        if len(parts) != 2:
            raise AssemblerError(
                f"Line {line_number}: .ORG requires exactly one address."
            )
        return 0

    if keyword == "DB":
        if len(parts) != 2:
            raise AssemblerError(
                f"Line {line_number}: DB requires exactly one 8-bit value."
            )
        return 1

    if keyword in OPCODES:
        return 1

    raise AssemblerError(
        f"Line {line_number}: unknown instruction or directive '{parts[0]}'."
    )


def parse_source(source: str) -> list[SourceLine]:
    parsed: list[SourceLine] = []

    for number, raw_line in enumerate(source.splitlines(), start=1):
        cleaned = remove_comment(raw_line)
        if not cleaned:
            continue

        label, statement = split_label(cleaned, number)
        parsed.append(SourceLine(number, raw_line.rstrip(), label, statement))

    return parsed


def first_pass(lines: list[SourceLine]) -> dict[str, int]:
    """Collect labels and calculate their RAM addresses."""
    labels: dict[str, int] = {}
    address = 0

    for item in lines:
        if item.label:
            if item.label in labels:
                raise AssemblerError(
                    f"Line {item.number}: duplicate label '{item.label}'."
                )
            if not 0 <= address < RAM_SIZE:
                raise AssemblerError(
                    f"Line {item.number}: label '{item.label}' is outside RAM."
                )
            labels[item.label] = address

        if not item.statement:
            continue

        parts = item.statement.replace(",", " ").split()
        keyword = parts[0].upper()

        if keyword == ".ORG":
            address = parse_number(parts[1], 4, item.number)
            continue

        address += statement_size(item.statement, item.number)
        if address > RAM_SIZE:
            raise AssemblerError(
                f"Line {item.number}: program exceeds the 16-byte RAM."
            )

    return labels


def encode_mode(
    parts: list[str],
    labels: dict[str, int],
    line_number: int,
) -> int:
    """
    Encode SHIFT/ROTATE operand nibble as D N2 N1 N0.

    Supported forms:
        SHIFT 0001b
        SHIFT 1d
        SHIFT LEFT 1d
        SHIFT RIGHT 2d
    """
    if len(parts) == 2:
        return resolve_value(parts[1], labels, 4, line_number)

    if len(parts) == 3:
        direction = parts[1].upper()
        if direction not in {"LEFT", "RIGHT"}:
            raise AssemblerError(
                f"Line {line_number}: direction must be LEFT or RIGHT."
            )

        amount = resolve_value(parts[2], labels, 3, line_number)
        direction_bit = 0 if direction == "LEFT" else 1
        return (direction_bit << 3) | amount

    raise AssemblerError(
        f"Line {line_number}: use '{parts[0]} mode' or "
        f"'{parts[0]} LEFT/RIGHT amount'."
    )


def encode_statement(
    statement: str,
    labels: dict[str, int],
    line_number: int,
) -> int:
    parts = statement.replace(",", " ").split()
    keyword = parts[0].upper()

    if keyword == "DB":
        if len(parts) != 2:
            raise AssemblerError(
                f"Line {line_number}: DB requires exactly one value."
            )
        return resolve_value(parts[1], labels, 8, line_number)

    if keyword in ADDRESS_OPS:
        if len(parts) != 2:
            raise AssemblerError(
                f"Line {line_number}: {keyword} requires one 4-bit address."
            )
        operand = resolve_value(parts[1], labels, 4, line_number)
        return (OPCODES[keyword] << 4) | operand

    if keyword in NO_OPERAND_OPS:
        if len(parts) != 1:
            raise AssemblerError(
                f"Line {line_number}: {keyword} takes no operand."
            )
        return OPCODES[keyword] << 4

    if keyword in MODE_OPS:
        operand = encode_mode(parts, labels, line_number)
        return (OPCODES[keyword] << 4) | operand

    raise AssemblerError(
        f"Line {line_number}: cannot encode '{statement}'."
    )


def assemble(source: str) -> tuple[list[int], list[str], dict[str, int]]:
    lines = parse_source(source)
    labels = first_pass(lines)

    memory = [0x00] * RAM_SIZE
    listing = ["Address  Byte  Source"]
    used_addresses: dict[int, int] = {}
    address = 0

    for item in lines:
        if not item.statement:
            continue

        parts = item.statement.replace(",", " ").split()
        keyword = parts[0].upper()

        if keyword == ".ORG":
            address = parse_number(parts[1], 4, item.number)
            continue

        if not 0 <= address < RAM_SIZE:
            raise AssemblerError(
                f"Line {item.number}: address {address:X} is outside RAM."
            )

        if address in used_addresses:
            previous_line = used_addresses[address]
            raise AssemblerError(
                f"Line {item.number}: address {address:X} is already occupied "
                f"by line {previous_line}."
            )

        byte = encode_statement(item.statement, labels, item.number)
        memory[address] = byte
        used_addresses[address] = item.number
        listing.append(f"{address:X}        {byte:02X}    {item.text.strip()}")
        address += 1

    return memory, listing, labels


def main() -> int:
    if len(sys.argv) not in {2, 3}:
        print("Usage: python assembler_8bit.py program.asm [ram_image.hex]")
        return 2

    source_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) == 3 else Path("ram_image.hex")
    listing_path = output_path.with_name("listing.txt")

    try:
        source = source_path.read_text(encoding="utf-8")
        memory, listing, labels = assemble(source)
    except FileNotFoundError:
        print(f"Error: input file not found: {source_path}")
        return 1
    except AssemblerError as exc:
        print(f"Assembly failed: {exc}")
        return 1

    hex_words = " ".join(f"{byte:02x}" for byte in memory)
    output_path.write_text(
        "v3.0 hex words addressed\n"
        f"0: {hex_words}\n",
        encoding="utf-8",
    )

    label_lines = ["", "Labels:"]
    if labels:
        for name, value in sorted(labels.items(), key=lambda pair: pair[1]):
            label_lines.append(f"{name:<16} = {value:X}h")
    else:
        label_lines.append("(none)")

    listing_path.write_text(
        "\n".join(listing + label_lines) + "\n",
        encoding="utf-8",
    )

    print("Assembly successful.")
    print(f"RAM image : {output_path}")
    print(f"Listing   : {listing_path}")
    print("Memory    :", " ".join(f"{byte:02X}" for byte in memory))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
