# Executed program results

Results below are derived from current execution evidence.

| G11 native machine check | Result |
|---|---:|
| Native compiler generations | 3 |
| Independent register-encoding comparisons | 100 |
| Quantum machine programs | 51 |
| Complete canonical frames compared | 728 |
| Maximum guest depth | 16 |
| Native history round trips | 51 |
| Computed seed generations restored | 12 |
| Mutated journal-bit refusals | 256 |
| Recomputed-checksum semantic refusals | 2 |

| Direct Clifford program | Lowered gates | Full-tableau oracle |
|---|---:|---|
| bell_pair | 2 | PASS |
| coherent_ring | 8 | PASS |
| cross_register | 7 | PASS |
| error_syndrome_unitary | 5 | PASS |
| ghz_32 | 32 | PASS |
| phase_echo | 6 | PASS |
| phase_inverse | 6 | PASS |

| Dense source | Sites | Operations | Recompiled | Full-amplitude oracle | Replay |
|---|---:|---:|---|---|---|
| bell_measure | 2 | 4 | PASS | PASS | PASS |
| bernstein_vazirani_4 | 5 | 16 | PASS | PASS | PASS |
| comptime_unroll | 7 | 10 | PASS | PASS | PASS |
| ghz_12 | 12 | 13 | PASS | PASS | PASS |
| ghz_16 | 16 | 18 | PASS | PASS | PASS |
| grover_2 | 2 | 14 | PASS | PASS | PASS |
| inverse_12 | 12 | 16 | PASS | PASS | PASS |
| phase_kickback | 6 | 8 | PASS | PASS | PASS |
| reversible_echo | 8 | 9 | PASS | PASS | PASS |
| t_interference | 5 | 10 | PASS | PASS | PASS |
| teleport_plus | 3 | 9 | PASS | PASS | PASS |
| teleport_verified | 3 | 11 | PASS | PASS | PASS |
| wide20 | 20 | 5 | PASS | Sparse analytical check | PASS |

The 32-qubit machine is an exact digital stabilizer profile. The dense non-Clifford profile uses Q30 arithmetic. Neither establishes physical coherence. Full machine reversal requires retained history; numerical dense inverse tests have the error limits in `evidence/mathematical_laws.json`.
