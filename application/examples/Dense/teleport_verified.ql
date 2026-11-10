# Teleport |+> from site 0 to 2; X basis measurement should be zero
qubits 3
cbits 3
H 0
H 1
CX 1 2
CX 0 1
H 0
MEASURE 0 0
MEASURE 1 1
IF1 1 X 2
IF1 0 Z 2
H 2
MEASURE 2 2
