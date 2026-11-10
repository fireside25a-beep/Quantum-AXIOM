# Grover search, target |11> (two computational sites)
qubits 2
cbits 2
H 0
H 1
CZ 0 1
H 0
H 1
X 0
X 1
CZ 0 1
X 0
X 1
H 0
H 1
MEASURE 0 0
MEASURE 1 1
