
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <windows.h>

#include "layers.h"

// ==========================================
// HIGH PRECISION TIMER
// ==========================================

static double get_time_ms(void) {

    LARGE_INTEGER frequency;
    LARGE_INTEGER counter;

    QueryPerformanceFrequency(&frequency);
    QueryPerformanceCounter(&counter);

    return (double)counter.QuadPart * 1000.0 /
           (double)frequency.QuadPart;
}

// ==========================================
// ADD SIMULATED HEADER
// ==========================================

static int add_header(
    char *packet,
    int packet_size,
    const char *header
) {

    char temp[LAYER_BUFFER_SIZE];

    int result = snprintf(
        temp,
        sizeof(temp),
        "%s%s",
        header,
        packet
    );

    if (result < 0 ||
        result >= (int)sizeof(temp) ||
        result >= packet_size) {

        printf("[ERROR] Packet buffer overflow!\n");
        return 0;
    }

    memcpy(packet, temp, (size_t)result + 1);

    return 1;
}

// ==========================================
// REMOVE SIMULATED HEADER
// ==========================================

static int remove_header(
    char *packet,
    const char *header
) {

    size_t length = strlen(header);

    if (strncmp(packet, header, length) != 0) {

        printf("[ERROR] Header validation failed: %s\n",
               header);

        return 0;
    }

    memmove(
        packet,
        packet + length,
        strlen(packet + length) + 1
    );

    return 1;
}

// ==========================================
// ENCAPSULATION
// ==========================================

int osi_encapsulate(
    const char *message,
    char *packet,
    int packet_size
) {

    if (message == NULL ||
        packet == NULL ||
        packet_size <= 0 ||
        strlen(message) >= (size_t)packet_size ||
        packet_size > LAYER_BUFFER_SIZE) {

        return 0;
    }

    double start_time = get_time_ms();

    strcpy(packet, message);

    printf("\n========== ENCAPSULATION ==========\n");

    // Layer 7
    printf("\n[L7 - Application] User message: %s\n",
           packet);

    // Layer 6
    printf("[L6 - Presentation] Encoding data...\n");

    if (!add_header(packet, packet_size, "L6|"))
        return 0;

    // Layer 5
    printf("[L5 - Session] Adding session information...\n");

    if (!add_header(
        packet,
        packet_size,
        "L5|SESSION_1001|"
    ))
        return 0;

    // Layer 4
    printf("[L4 - Transport] Adding transport metadata...\n");

    if (!add_header(packet, packet_size, "L4|TCP|"))
        return 0;

    // Layer 3
    printf("[L3 - Network] Adding IP metadata...\n");

    if (!add_header(
        packet,
        packet_size,
        "L3|127.0.0.1|"
    ))
        return 0;

    // Layer 2
    printf("[L2 - Data Link] Creating simulated frame...\n");

    if (!add_header(packet, packet_size, "L2|FRAME|"))
        return 0;

    // Layer 1
    printf("[L1 - Physical] Converting data into bits...\n");

    printf("[L1 - Physical] Transmission representation ready.\n");

    printf("\n[ENCAPSULATION COMPLETE]\n");

    

    // Performance metrics
    double end_time = get_time_ms();

    
    return 1;
}

// ==========================================
// DECAPSULATION
// ==========================================

int osi_decapsulate(
    char *packet,
    int packet_size
) {

    if (packet == NULL ||
        packet_size <= 0 ||
        memchr(packet, '\0', (size_t)packet_size) == NULL) {

        return 0;
    }

    double start_time = get_time_ms();

    printf("\n========== DECAPSULATION ==========\n");

   

    // Layer 1
    printf("\n[L1 - Physical] Receiving transmitted bytes...\n");

    // Layer 2
    printf("[L2 - Data Link] Processing simulated frame...\n");

    if (!remove_header(packet, "L2|FRAME|"))
        return 0;

    // Layer 3
    printf("[L3 - Network] Removing IP metadata...\n");

    if (!remove_header(packet, "L3|127.0.0.1|"))
        return 0;

    // Layer 4
    printf("[L4 - Transport] Processing TCP metadata...\n");

    if (!remove_header(packet, "L4|TCP|"))
        return 0;

    // Layer 5
    printf("[L5 - Session] Processing session information...\n");

    if (!remove_header(packet, "L5|SESSION_1001|"))
        return 0;

    // Layer 6
    printf("[L6 - Presentation] Decoding data...\n");

    if (!remove_header(packet, "L6|"))
        return 0;

    // Layer 7
    printf("[L7 - Application] Final message received!\n");

    printf("\nReceived Message: %s\n", packet);

    printf("\n[DECAPSULATION COMPLETE]\n");

    // Decapsulation metrics
    double end_time = get_time_ms();

    printf(
        "METRIC|decapsulation_ms|%.4f\n",
        end_time - start_time
    );

    return 1;
}
