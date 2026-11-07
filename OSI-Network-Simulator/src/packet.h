
#ifndef PACKET_H
#define PACKET_H

#define DATA_SIZE 1024
#define PACKET_SIZE 4096

typedef struct {

    int session_id;

    char source_ip[16];
    char destination_ip[16];

    int source_port;
    int destination_port;

    char source_mac[18];
    char destination_mac[18];

    char data[DATA_SIZE];

} OSIPacket;

#endif
