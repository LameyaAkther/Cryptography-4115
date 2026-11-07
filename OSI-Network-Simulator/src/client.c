
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

// Winsock must come before windows.h
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>

#include "layers.h"

#define PORT 8080
#define PACKET_SIZE 4096

// ==========================================
// SEND ALL BYTES
// ==========================================

int send_all(SOCKET sock, const char *data, int length) {

    int total = 0;

    while (total < length) {

        int sent = send(
            sock,
            data + total,
            length - total,
            0
        );

        if (sent == SOCKET_ERROR || sent == 0) {
            return 0;
        }

        total += sent;
    }

    return 1;
}

// ==========================================
// RECEIVE ALL REQUESTED BYTES
// ==========================================

int recv_all(SOCKET sock, char *data, int length) {

    int total = 0;

    while (total < length) {

        int received = recv(
            sock,
            data + total,
            length - total,
            0
        );

        if (received <= 0) {
            return 0;
        }

        total += received;
    }

    return 1;
}

// ==========================================
// PERFORMANCE TIMER
// ==========================================

double elapsed_ms(
    LARGE_INTEGER start,
    LARGE_INTEGER end,
    LARGE_INTEGER frequency
) {

    return (double)(end.QuadPart - start.QuadPart)
           * 1000.0 / (double)frequency.QuadPart;
}

// ==========================================
// MAIN CLIENT
// ==========================================

int main(int argc, char *argv[]) {

    setvbuf(stdout, NULL, _IONBF, 0);

    WSADATA wsa;

    SOCKET client_socket = INVALID_SOCKET;

    struct sockaddr_in server_addr;

    char packet[PACKET_SIZE] = {0};
    char response[PACKET_SIZE] = {0};

    uint32_t network_length;

    LARGE_INTEGER frequency;
    LARGE_INTEGER total_start, total_end;
    LARGE_INTEGER encaps_start, encaps_end;
    LARGE_INTEGER rtt_start, rtt_end;

    if (!QueryPerformanceFrequency(&frequency)) {
        printf("[ERROR] High-resolution timer unavailable.\n");
        return 1;
    }

    QueryPerformanceCounter(&total_start);

    const char *message = (argc > 1)
        ? argv[1]
        : "Hello from OSI Client!";

    if (strlen(message) >= PACKET_SIZE) {
        printf("[ERROR] Message too large.\n");
        return 1;
    }

    printf("[SYSTEM] Client starting...\n");

    // ======================================
    // WINSOCK INITIALIZATION
    // ======================================

    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {

        printf("[ERROR] Winsock initialization failed.\n");
        return 1;
    }

    printf("[CLIENT] Winsock initialized.\n");

    // ======================================
    // CREATE TCP SOCKET
    // ======================================

    client_socket = socket(
        AF_INET,
        SOCK_STREAM,
        IPPROTO_TCP
    );

    if (client_socket == INVALID_SOCKET) {

        printf("[ERROR] Socket creation failed: %d\n",
               WSAGetLastError());

        WSACleanup();
        return 1;
    }

    // ======================================
    // SERVER CONFIGURATION
    // ======================================

    memset(&server_addr, 0, sizeof(server_addr));

    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(PORT);

    server_addr.sin_addr.s_addr = inet_addr("127.0.0.1");

    // ======================================
    // CONNECT TO SERVER
    // ======================================

    printf("[CLIENT] Connecting to server...\n");

    if (connect(
        client_socket,
        (struct sockaddr*)&server_addr,
        sizeof(server_addr)
    ) == SOCKET_ERROR) {

        printf("[ERROR] Connection failed: %d\n",
               WSAGetLastError());

        closesocket(client_socket);
        WSACleanup();
        return 1;
    }

    printf("[CLIENT] Connected to server!\n");
    printf("EVENT|CONNECTED\n");

    printf("[CLIENT] Original message: %s\n", message);

    // ======================================
    // ENCAPSULATION
    // ======================================

    QueryPerformanceCounter(&encaps_start);

    if (!osi_encapsulate(
        message,
        packet,
        sizeof(packet)
    )) {

        printf("[ERROR] Encapsulation failed.\n");

        closesocket(client_socket);
        WSACleanup();
        return 1;
    }

    QueryPerformanceCounter(&encaps_end);

    double encapsulation_ms = elapsed_ms(
        encaps_start,
        encaps_end,
        frequency
    );

    // ======================================
    // PACKET INSPECTOR
    // ======================================

    uint32_t packet_length = (uint32_t)strlen(packet);

    printf("\n[CLIENT] Encapsulated packet:\n");

    printf("PACKET|%s\n", packet);

    printf("[CLIENT] Packet size: %u bytes\n",
           packet_length);

    printf(
        "METRIC|PACKET_BYTES|%u\n",
        packet_length
    );

    // ======================================
    // SEND PACKET
    // ======================================

    network_length = htonl(packet_length);

    QueryPerformanceCounter(&rtt_start);

    if (!send_all(
        client_socket,
        (const char*)&network_length,
        sizeof(network_length)
    ) || !send_all(
        client_socket,
        packet,
        (int)packet_length
    )) {

        printf("[ERROR] Packet transmission failed.\n");

        closesocket(client_socket);
        WSACleanup();
        return 1;
    }

    printf("[CLIENT] Packet transmitted successfully!\n");

    // ======================================
    // RECEIVE SERVER RESPONSE LENGTH
    // ======================================

    if (!recv_all(
        client_socket,
        (char*)&network_length,
        sizeof(network_length)
    )) {

        printf("[ERROR] Response length reception failed.\n");

        closesocket(client_socket);
        WSACleanup();
        return 1;
    }

    uint32_t response_length = ntohl(network_length);

    if (response_length == 0 ||
        response_length >= PACKET_SIZE) {

        printf("[ERROR] Invalid response length.\n");

        closesocket(client_socket);
        WSACleanup();
        return 1;
    }

    // ======================================
    // RECEIVE SERVER RESPONSE
    // ======================================

    if (!recv_all(
        client_socket,
        response,
        (int)response_length
    )) {

        printf("[ERROR] Response reception failed.\n");

        closesocket(client_socket);
        WSACleanup();
        return 1;
    }

    QueryPerformanceCounter(&rtt_end);

    response[response_length] = '\0';

    double rtt_ms = elapsed_ms(
        rtt_start,
        rtt_end,
        frequency
    );

    printf("\n[CLIENT] Server response: %s\n", response);

    // ======================================
    // PERFORMANCE METRICS
    // ======================================

    printf("\n========== PERFORMANCE METRICS ==========\n");

    printf(
        "METRIC|ENCAPSULATION_MS|%.6f\n",
        encapsulation_ms
    );

    printf(
        "METRIC|RTT_MS|%.6f\n",
        rtt_ms
    );

    QueryPerformanceCounter(&total_end);

    double total_ms = elapsed_ms(
        total_start,
        total_end,
        frequency
    );

    printf(
        "METRIC|TOTAL_CLIENT_MS|%.6f\n",
        total_ms
    );

    printf("[CLIENT] Performance measurement complete.\n");

    printf("EVENT|COMPLETED\n");

    // ======================================
    // CLEANUP
    // ======================================

    closesocket(client_socket);

    WSACleanup();

    printf("\n[CLIENT] Connection closed.\n");

    return 0;
}
