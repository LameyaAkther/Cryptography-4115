
#ifndef LAYERS_H
#define LAYERS_H

#define LAYER_BUFFER_SIZE 4096

// Encapsulation: Application to Physical
int osi_encapsulate(
    const char *message,
    char *packet,
    int packet_size
);

// Decapsulation: Physical to Application
int osi_decapsulate(
    char *packet,
    int packet_size
);

#endif
