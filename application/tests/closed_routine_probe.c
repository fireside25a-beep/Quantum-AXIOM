#include "neuro_world.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Run the preserved implementation itself. This is test instrumentation,
 * not a second implementation of its neuron or quantum equations. */
static int equal_rows(const pq_state *a, const pq_state *b) {
    if (a->n != b->n) return 0;
    for (unsigned i=0; i<2u*a->n; ++i)
        if (a->rows[i].x != b->rows[i].x || a->rows[i].z != b->rows[i].z ||
            a->rows[i].phase != b->rows[i].phase) return 0;
    return 1;
}

static int spiked(const nm_spikes *s, unsigned id) {
    for (size_t i=0; i<s->count; ++i) if (s->ids[i]==id) return 1;
    return 0;
}

int main(void) {
    unsigned cases=0, feedback=0, refusals=0;
    pq_state exported={0};
    const char operations[]={'X','Y','Z'};
    for (unsigned q=0; q<5; ++q) for (unsigned kind=0; kind<3; ++kind)
    for (unsigned flip=0; flip<13; ++flip) {
        nm_world *w=nm_world_new(5,1);
        if (!w || nm_world_enable_five_code(w)) return 1;
        for (unsigned i=0; i<3; ++i)
            if (nm_add_neuron(w->network,(uint16_t)i,0,1,0,0)) return 2;
        nm_world_rule fault={.trigger=0,.a=(uint16_t)q,.op=operations[kind]};
        nm_world_rule correction={.trigger=1,.output_neuron=2,.output_current=1,.op='Q'};
        if (nm_world_add_rule(w,fault) || nm_world_add_rule(w,correction)) return 3;
        const pq_state initial=w->quantum;
        nm_world_input input={.stimulus_neuron=0,.stimulus_current=1};
        nm_world_report report={0};
        if (nm_world_step(w,&input,&report) || !spiked(&report.spikes,0) ||
            report.fired_rules!=1 || equal_rows(&initial,&w->quantum)) return 4;
        /* A second fault before correction must refuse without publishing. */
        nm_network *saved=malloc(sizeof(*saved));
        if (!saved) return 5;
        memcpy(saved,w->network,sizeof(*saved));
        pq_state before=w->quantum;
        if (nm_world_step(w,&input,&report)!=-1 ||
            memcmp(saved,w->network,sizeof(*saved)) || !equal_rows(&before,&w->quantum)) return 6;
        free(saved); ++refusals;
        input=(nm_world_input){.stimulus_neuron=1,.stimulus_current=1};
        input.readout_flip[1]=(uint8_t)flip;
        if (nm_world_step(w,&input,&report) || !spiked(&report.spikes,1) ||
            !(report.corrected_rules&2u) || !report.syndromes[1] ||
            !equal_rows(&initial,&w->quantum)) return 7;
        input=(nm_world_input){0};
        if (nm_world_step(w,&input,&report) || !spiked(&report.spikes,2)) return 8;
        ++feedback; ++cases;
        exported=w->quantum;
        nm_world_free(w);
    }
    printf("{\"format\":\"AXIOM_TABLEAU_STATE_1\",\"sites\":%u,\"rows\":[",exported.n);
    for (unsigned i=0; i<2u*exported.n; ++i)
        printf("%s[%u,%u,%u]",i?",":"",exported.rows[i].x,
               exported.rows[i].z,exported.rows[i].phase);
    puts("]}");
    if (fflush(stdout)) return 9;
    fprintf(stderr,"CLOSED_ROUTINE_PASS cases=%u feedback_spikes=%u transactional_refusals=%u\n",
            cases,feedback,refusals);
    return 0;
}
