# Standardized warning codes for API/analysis
TP1_FLOOR = 'TP1_FLOOR'
TP2_FLOOR = 'TP2_FLOOR'
TP3_CAP = 'TP3_CAP'
SL_FLOOR = 'SL_FLOOR'
BE_FLOOR = 'BE_FLOOR'
TS_TRIGGER_FLOOR = 'TS_TRIGGER_FLOOR'
TS_STEP_FLOOR = 'TS_STEP_FLOOR'
TS_FLOOR_CANONICAL = 'TS_FLOOR_CANONICAL'
INFO = 'INFO'

# Optional human-friendly descriptions
CODE_DESCRIPTIONS = {
    TP1_FLOOR: 'TP1 floored to minimum',
    TP2_FLOOR: 'TP2 floored to minimum',
    TP3_CAP: 'TP3 capped or floored',
    SL_FLOOR: 'Stop-Loss floored to minimum',
    BE_FLOOR: 'Breakeven floored to minimum',
    TS_TRIGGER_FLOOR: 'Trailing Stop trigger floored to minimum',
    TS_STEP_FLOOR: 'Trailing Stop step floored to minimum',
    TS_FLOOR_CANONICAL: 'Canonical TS floor message',
    INFO: 'Informational'
}
