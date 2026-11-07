
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <winsock2.h>
#include <ws2tcpip.h>

#include "layers.h"

#define PORT 8080
#define PACKET_SIZE 4096

// Send all bytes
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

// Receive exactly the requested bytes
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

int main(void) {

    // IMPORTANT: Enable real-time output for Python
    setvbuf(stdout, NULL, _IONBF, 0);

    WSADATA wsa;

    SOCKET server_socket = INVALID_SOCKET;
    SOCKET client_socket = INVALID_SOCKET;

    struct sockaddr_in server_addr;
    struct sockaddr_in client_addr;

    int client_size = sizeof(client_addr);

    char packet[PACKET_SIZE] = {0};

    uint32_t network_length;

    printf("[SYSTEM] Server starting...\n");

    // Initialize Winsock
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {

        printf("[ERROR] Winsock initialization failed!\n");
        return 1;
    }

    printf("[SERVER] Winsock initialized.\n");

    // Create TCP socket
    server_socket = socket(
        AF_INET,
        SOCK_STREAM,
        IPPROTO_TCP
    );

    if (server_socket == INVALID_SOCKET) {

        printf("[ERROR] Socket creation failed!\n");
        WSACleanup();
        return 1;
    }

    // Allow address reuse
    {
        int reuse = 1;

        setsockopt(
            server_socket,
            SOL_SOCKET,
            SO_REUSEADDR,
            (const char*)&reuse,
            sizeof(reuse)
        );
    }

    // Configure server
    memset(&server_addr, 0, sizeof(server_addr));

    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);
    server_addr.sin_port = htons(PORT);

    // Bind
    if (bind(
        server_socket,
        (struct sockaddr*)&server_addr,
        sizeof(server_addr)
    ) == SOCKET_ERROR) {

        printf("[ERROR] Bind failed: %d\n",
               WSAGetLastError());

        closesocket(server_socket);
        WSACleanup();
        return 1;
    }

    // Listen
    if (listen(server_socket, 5) == SOCKET_ERROR) {

        printf("[ERROR] Listen failed!\n");

        closesocket(server_socket);
        WSACleanup();
        return 1;
    }

    printf("[SERVER] Listening on port %d...\n", PORT);

    printf("EVENT|SERVER_READY\n");

    // Accept client
    client_socket = accept(
        server_socket,
        (struct sockaddr*)&client_addr,
        &client_size
    );

    if (client_socket == INVALID_SOCKET) {

        printf("[ERROR] Accept failed: %d\n",
               WSAGetLastError());

        closesocket(server_socket);
        WSACleanup();
        return 1;
    }

    printf("[SERVER] Client connected!\n");

    printf("EVENT|CONNECTED\n");

    // Receive packet length
    if (!recv_all(
        client_socket,
        (char*)&network_length,
        sizeof(network_length)
    )) {

        printf("[ERROR] Failed to receive packet length.\n");
        goto cleanup;
    }

    uint32_t packet_length = ntohl(network_length);

    if (packet_length == 0 ||
        packet_length >= PACKET_SIZE) {

        printf("[ERROR] Invalid packet length!\n");
        goto cleanup;
    }

    // Receive complete packet
    if (!recv_all(
        client_socket,
        packet,
        (int)packet_length
    )) {

        printf("[ERROR] Packet reception failed!\n");
        goto cleanup;
    }

    packet[packet_length] = '\0';

    printf("\n[SERVER] Packet received successfully!\n");

    printf("EVENT|PACKET_RECEIVED\n");

    // ==========================================
    // DECAPSULATION
    // ==========================================

    printf("\n========== DECAPSULATION ==========\n");

    printf("EVENT|DECAPSULATION_START\n");

    if (!osi_decapsulate(
        packet,
        (int)packet_length + 1
    )) {

        printf("[ERROR] Decapsulation failed!\n");
        goto cleanup;
    }

    printf("EVENT|DECAPSULATION_COMPLETE\n");

    printf("\n[DECAPSULATION COMPLETE]\n");

    // ==========================================
    // SEND SERVER RESPONSE
    // ==========================================

    {
        const char *reply = "Hello from OSI Server!";

        uint32_t reply_length =
            (uint32_t)strlen(reply);

        uint32_t reply_network_length =
            htonl(reply_length);

        printf("\n[SERVER] Sending response...\n");

        if (!send_all(
            client_socket,
            (const char*)&reply_network_length,
            sizeof(reply_network_length)
        ) || !send_all(
            client_socket,
            reply,
            (int)reply_length
        )) {

            printf("[ERROR] Response transmission failed!\n");
            goto cleanup;
        }
    }

    printf("[SERVER] Response sent successfully!\n");

    printf("EVENT|RESPONSE_SENT\n");

    printf("EVENT|COMPLETED\n");

cleanup:

    printf("[SERVER] Closing connection...\n");

    if (client_socket != INVALID_SOCKET) {
        closesocket(client_socket);
    }

    if (server_socket != INVALID_SOCKET) {
        closesocket(server_socket);
    }

    WSACleanup();

    printf("[SERVER] Server closed.\n");

    return 0;
}
