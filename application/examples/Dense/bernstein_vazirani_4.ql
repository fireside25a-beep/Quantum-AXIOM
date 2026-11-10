# Hidden parity mask 1010 (little endian bits 1 and 3)
qubits 5
cbits 4
X 4
H 4
H 0
H 1
H 2
H 3
CX 1 4
CX 3 4
H 0
H 1
H 2
H 3
MEASURE 0 0
MEASURE 1 1
MEASURE 2 2
MEASURE 3 3
