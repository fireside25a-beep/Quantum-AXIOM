# Reversible echo through 12 sites, checks exact order inversion
qubits 12
cbits 2
H 0
S 1
T 2
CX 0 11
CX 1 10
CZ 2 9
RZ8 3 4
RZ8 3 -4
CZ 2 9
CX 1 10
CX 0 11
TDG 2
SDG 1
H 0
MEASURE 0 0
MEASURE 11 1
