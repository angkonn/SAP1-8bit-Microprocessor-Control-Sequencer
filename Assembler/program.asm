; TEST 8 — ROTATE left and right
;
; B4 = 10110100
; Rotate left 1  -> 01101001 = 69
; Rotate right 2 -> 01011010 = 5A

START:
    LDA DATA
    ROTATE LEFT 1d
    STA RESULT_LEFT

    ROTATE RIGHT 2d
    STA RESULT_RIGHT
    HLT

.ORG 0Ch
RESULT_LEFT:  DB 00h
RESULT_RIGHT: DB 00h
DATA:         DB 0B4h
