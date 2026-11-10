#include "neuro_mantle.h"
#include <limits.h>
#include <stdlib.h>
#include <string.h>

static int add_i64(int64_t a, int64_t b, int64_t *out) {
    return !__builtin_add_overflow(a, b, out);
}
void nm_init(nm_network *n) { if (n) memset(n, 0, sizeof(*n)); }
int nm_add_neuron(nm_network *n, uint16_t id, int64_t reset, int64_t threshold,
                  uint32_t leak, uint32_t refractory) {
    if (!n || id >= NM_MAX_NEURONS || n->neurons[id].configured || leak > NM_Q16 ||
        threshold <= reset || refractory > NM_MAX_DELAY || reset < -(1LL<<45) || threshold > (1LL<<45)) return -1;
    n->neurons[id] = (nm_neuron){.voltage=reset,.reset=reset,.threshold=threshold,
        .leak_q16=leak,.refractory=refractory,.configured=1};
    return 0;
}
int nm_add_edge(nm_network *n,uint16_t src,uint16_t dst,int32_t weight,
                uint16_t delay,uint16_t plus,uint16_t minus,uint16_t window,
                int32_t min_weight,int32_t max_weight) {
    if (!n || src >= NM_MAX_NEURONS || dst >= NM_MAX_NEURONS ||
        !n->neurons[src].configured || !n->neurons[dst].configured ||
        !delay || delay > NM_MAX_DELAY || !window || window > 4096 ||
        min_weight > max_weight || weight < min_weight || weight > max_weight ||
        n->edge_count >= NM_MAX_EDGES) return -1;
    n->edges[n->edge_count++] = (nm_edge){src,dst,delay,weight,weight,min_weight,max_weight,plus,minus,window,0,0,0,0,0};
    return 0;
}
int nm_set_fast_facilitation(nm_network *n, size_t edge_index,
                             uint16_t decay_q15, int16_t increment, int16_t capacity) {
    if (!n || n->tick != 0 || edge_index >= n->edge_count ||
        decay_q15 > 32768 || increment <= 0 || capacity <= 0 || increment > capacity)
        return -1;
    nm_edge *e = &n->edges[edge_index];
    e->stf_decay_q15=decay_q15;
    e->stf_increment=increment;
    e->stf_capacity=capacity;
    e->stf_trace=0;
    return 0;
}
int nm_set_edge_branch(nm_network *n,size_t edge_index,uint8_t branch_id) {
    if(!n||n->tick!=0||edge_index>=n->edge_count||branch_id>2)return -1;
    n->edges[edge_index].branch_id=branch_id;
    return 0;
}
int nm_set_branch_coincidence(nm_network *n,uint16_t dst,
                              int32_t min_branch_current,int32_t gain) {
    if(!n||n->tick!=0||dst>=NM_MAX_NEURONS||!n->neurons[dst].configured||
       min_branch_current<=0||gain<=0)return -1;
    n->neurons[dst].branch_threshold=min_branch_current;
    n->neurons[dst].branch_gain=gain;
    return 0;
}
int nm_inject(nm_network *n,uint16_t id,uint64_t tick,int64_t current) {
    int64_t value;
    if (!n || id >= NM_MAX_NEURONS || !n->neurons[id].configured || tick < n->tick ||
        tick - n->tick > NM_MAX_DELAY || !add_i64(n->pending[tick % (NM_MAX_DELAY+1)][id],current,&value)) return -1;
    n->pending[tick % (NM_MAX_DELAY+1)][id]=value;
    return 0;
}
static int32_t clamp_weight(int64_t value, const nm_edge *e) {
    if (value < e->min_weight) return e->min_weight;
    if (value > e->max_weight) return e->max_weight;
    return (int32_t)value;
}
typedef struct {
    uint32_t key,order;
    int32_t weight;
    uint8_t branch_id;
    int64_t group_value; /* staged next ring-slot value; atomic commit */
} nm_delivery;
static int compare_delivery(const void *a,const void *b){
    const nm_delivery *x=a,*y=b;
    if(x->key!=y->key)return x->key<y->key?-1:1;
    return x->order<y->order?-1:x->order>y->order;
}
int nm_step(nm_network *n,nm_spikes *out) {
    if (!n || !out || n->tick == UINT64_MAX) return -1;
    /* Validate all writes before committing. No full-network copy or rollback is needed. */
    nm_neuron next[NM_MAX_NEURONS];
    int32_t weights[NM_MAX_EDGES];
    int16_t stf_next[NM_MAX_EDGES];
    nm_delivery deliveries[NM_MAX_EDGES];
    size_t delivery_count=0;
    unsigned char fired[NM_MAX_NEURONS]={0};
    nm_spikes result={.count=0,.tick=n->tick};
    const size_t slot=n->tick % (NM_MAX_DELAY+1);
    for (size_t id=0;id<NM_MAX_NEURONS;++id) {
        if (!n->neurons[id].configured) continue;
        if(n->neurons[id].branch_gain<0 ||
           (n->neurons[id].branch_gain>0 && n->neurons[id].branch_threshold<=0))
            return -1; /* corrupted or unsupported branch rule */
        next[id]=n->neurons[id];nm_neuron *v=&next[id];
        if (v->remaining) { --v->remaining; v->voltage=v->reset; continue; }
        int64_t delta,leaked,voltage;
        if (__builtin_sub_overflow(v->voltage,v->reset,&delta)) return -1;
        if (__builtin_mul_overflow(delta,(int64_t)v->leak_q16,&leaked)) return -1;
        leaked /= NM_Q16;
        if (!add_i64(v->reset,leaked,&voltage) ||
            !add_i64(voltage,n->pending[slot][id],&voltage)) return -1;
        if (voltage >= v->threshold) {
            if (v->spikes==UINT64_MAX) return -1;
            v->voltage=v->reset; v->remaining=v->refractory;
            v->last_spike=n->tick+1; ++v->spikes;
            fired[id]=1;result.ids[result.count++]=(uint16_t)id;
        } else v->voltage=voltage;
    }
    /* All pre/post events use the old timestamps. Simultaneous spikes do not train. */
    for (size_t i=0;i<n->edge_count;++i) {
        const nm_edge *e=&n->edges[i];
        if(e->branch_id>2)return -1; /* malformed state: no OOB branch index */
        const nm_neuron *pre=&n->neurons[e->src], *post=&n->neurons[e->dst];
        int64_t w=e->weight;
        if (fired[e->src]) {
            if (post->last_spike && n->tick+1-post->last_spike<=e->window)
                w-= (int64_t)e->minus*(e->window-(n->tick+1-post->last_spike)+1)/e->window;
        }
        if (fired[e->dst] && pre->last_spike && n->tick+1-pre->last_spike<=e->window)
            w+= (int64_t)e->plus*(e->window-(n->tick+1-pre->last_spike)+1)/e->window;
        weights[i]=clamp_weight(w,e);
        /* A presynaptic spike leaves a transient facilitating trace; silent
           ticks decay it. The delivery for this tick uses the OLD trace.
           All next traces are staged until after overflow validation. */
        if (e->stf_capacity > 0) {
            int32_t t=((int32_t)e->stf_trace * e->stf_decay_q15)/32768;
            if (fired[e->src]) {
                t += e->stf_increment;
                if (t > e->stf_capacity) t=e->stf_capacity;
            }
            stf_next[i]=(int16_t)t;
        } else stf_next[i]=0;
    }
    /* Gather only firing-edge deliveries; preserve edge order within each destination. */
    for (size_t i=0;i<n->edge_count;++i) {
        const nm_edge *e=&n->edges[i];
        if (!fired[e->src]) continue;
        const size_t target=(slot+e->delay)%(NM_MAX_DELAY+1);
        const int64_t efficacy=(int64_t)e->weight + e->stf_trace;
        if (efficacy < INT32_MIN || efficacy > INT32_MAX) return -1;
        deliveries[delivery_count++]=(nm_delivery){
            (uint32_t)(target*NM_MAX_NEURONS+e->dst),(uint32_t)i,
            (int32_t)efficacy,e->branch_id,0};
    }
    qsort(deliveries,delivery_count,sizeof(*deliveries),compare_delivery);
    /* Group current by target tick/neuron. Every nonlinear junction is
       evaluated in the SAME original nm_step before anything is committed.
       Compaction occurs only behind the read index; no duplicate executor.
       An absent branch rule reproduces the original linear transition. */
    size_t group_count=0;
    for(size_t i=0;i<delivery_count;){
        const uint32_t key=deliveries[i].key;
        int64_t combined=n->pending[key/NM_MAX_NEURONS][key%NM_MAX_NEURONS];
        int64_t branches[2]={0,0};
        size_t j=i;
        while(j<delivery_count && deliveries[j].key==key){
            const nm_delivery *e=&deliveries[j];
            if(!add_i64(combined,e->weight,&combined))return -1;
            if(e->branch_id && !add_i64(branches[e->branch_id-1],
                                          e->weight,&branches[e->branch_id-1]))return -1;
            ++j;
        }
        const nm_neuron *dst=&n->neurons[key%NM_MAX_NEURONS];
        if(dst->branch_gain>0 &&
           branches[0]>=dst->branch_threshold &&
           branches[1]>=dst->branch_threshold &&
           !add_i64(combined,dst->branch_gain,&combined))return -1;
        deliveries[group_count].key=key;
        deliveries[group_count].group_value=combined;
        ++group_count;
        i=j;
    }
    for(size_t id=0;id<NM_MAX_NEURONS;++id)if(n->neurons[id].configured)n->neurons[id]=next[id];
    for(size_t i=0;i<n->edge_count;++i) {
        n->edges[i].weight=weights[i];
        n->edges[i].stf_trace=stf_next[i];
    }
    memset(n->pending[slot],0,sizeof(n->pending[slot]));
    for(size_t i=0;i<group_count;++i){
        const uint32_t key=deliveries[i].key;
        n->pending[key/NM_MAX_NEURONS][key%NM_MAX_NEURONS]=deliveries[i].group_value;
    }
    ++n->tick;
    *out=result;
    return 0;
}
