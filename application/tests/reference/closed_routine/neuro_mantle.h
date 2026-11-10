#ifndef NEURO_MANTLE_H
#define NEURO_MANTLE_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#define NM_MAX_NEURONS 1024u
#define NM_MAX_EDGES 16384u
#define NM_MAX_DELAY 64u
#define NM_Q16 65536LL

typedef struct {
    int64_t voltage, reset, threshold;
    uint32_t leak_q16, refractory, remaining;
    uint64_t spikes, last_spike;
    unsigned configured;
    /* Branch-coincidence operator is zero/disabled in original networks. */
    int32_t branch_threshold, branch_gain;
} nm_neuron;
typedef struct {
    uint16_t src, dst, delay;
    int32_t weight, initial_weight, min_weight, max_weight;
    uint16_t plus, minus, window;
    /* Optional fast, transient synaptic memory. 0-initialized: no effect.
       Units are integer current, decay_q15 in [0,32768] (1.0 means no loss).
       This state lives on the actual conducting edge; it is NOT a database. */
    uint16_t stf_decay_q15;
    int16_t stf_increment, stf_capacity, stf_trace;
    uint8_t branch_id; /* 0=ordinary input, 1/2=local dendritic branch */
} nm_edge;
typedef struct {
    nm_neuron neurons[NM_MAX_NEURONS];
    nm_edge edges[NM_MAX_EDGES];
    int64_t pending[NM_MAX_DELAY + 1][NM_MAX_NEURONS];
    size_t edge_count;
    uint64_t tick;
} nm_network;
typedef struct { uint16_t ids[NM_MAX_NEURONS]; size_t count; uint64_t tick; } nm_spikes;
void nm_init(nm_network *network);
int nm_add_neuron(nm_network *network, uint16_t id, int64_t reset, int64_t threshold,
                  uint32_t leak_q16, uint32_t refractory);
int nm_add_edge(nm_network *network, uint16_t src, uint16_t dst, int32_t weight,
                uint16_t delay, uint16_t plus, uint16_t minus, uint16_t window,
                int32_t min_weight, int32_t max_weight);
int nm_inject(nm_network *network, uint16_t id, uint64_t tick, int64_t current);
/* Configure a fast memory channel on an existing, configured synapse.
   Permitted only before the first tick. A positive increment and capacity are
   required; no STP configured leaves original source behavior unchanged. */
int nm_set_fast_facilitation(nm_network *network, size_t edge_index,
                             uint16_t decay_q15, int16_t increment, int16_t capacity);
/* Optional, pre-execution dendritic coincidence on one authentic SNN tick. */
int nm_set_edge_branch(nm_network *network, size_t edge_index, uint8_t branch_id);
int nm_set_branch_coincidence(nm_network *network, uint16_t dst,
                              int32_t min_branch_current, int32_t gain);
int nm_step(nm_network *network, nm_spikes *out);
#ifdef __cplusplus
}
#endif
#endif
