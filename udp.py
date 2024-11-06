import socket
import threading
import sys
from random import *


class Peer2peer:
    def __init__(self, client_ip, client_port, target_ip, target_port, msgsize):
        self.client_ip = client_ip
        self.client_port = client_port
        self.target_ip = target_ip
        self.target_port = target_port
        self.msgsize = msgsize
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.client_ip, self.client_port))
        self.running = True
        self.connected = False
        self.sequence_number_int = 0

    def merge_bits(self, sequence_number, acknowledgment_number, fragment_id, flags, msg_type, checksum):
        #Merge individual bit fields into a single bit sequence."""
        big_bit_sequence = (
            sequence_number +  # 32 bits
            acknowledgment_number +  # 32 bits
            fragment_id +  # 16 bits
            flags +  # 5 bits
            msg_type +  # 3 bits
            checksum  # 16 bits
        )
        # Convert the bit string to a byte array before sending
        return int(big_bit_sequence, 2).to_bytes(len(big_bit_sequence) // 8, byteorder='big')


    def create_new_bit_field(self, sequence_number, acknowledgment_number, flags, msg_type, checksum):


        sequence_number_bits = f'{sequence_number:032b}'  # 32-bit sequence number
        acknowledgment_number_bits = f'{acknowledgment_number:032b}'  # 32-bit acknowledgment number
        fragment_id_bits = f'{randint(0,2**16):016b}'  # 16-bit fragment ID
        flags_bits = f'{flags:05b}'  # 5-bit flags (for example, SYN flag)
        msg_type_bits = f'{msg_type:03b}'  # 3-bit message type
        checksum_bits = f'{checksum:016b}'  # 16-bit checksum (set to zero for now)

        return self.merge_bits(sequence_number_bits, acknowledgment_number_bits, fragment_id_bits, flags_bits, msg_type_bits, checksum_bits)

    def send_handshake(self):
        """Send a handshake with a custom protocol message in binary."""
        random_value = randint(0, 10000)  # Generate random sequence numbe

        # Create bit fields
        bit_message = self.create_new_bit_field(random_value, 0,16,4, 0 )  # 16-bit checksum (set to zero for now)

        # Merge all bits into a single message

        # Send the binary message
        print("Sending INIT to initiate connection...")
        self.sock.sendto(bit_message, (self.target_ip, self.target_port))

    def receive_handshake(self):
        #Receive and handle handshake messages.
        while not self.connected:
            try:
                data, addr = self.sock.recvfrom(self.msgsize)
                bit_message = ''.join(f'{byte:08b}' for byte in data)  # Convert received bytes to a bit string

                # Extract flag bits to check handshake status (for simplicity, using fixed bit positions)
                syn_flag = bit_message[80]
                ack_flag = bit_message[81]

                if syn_flag == '1' and ack_flag == '0':
                    # Received SYN, respond with SYN-ACK
                    print(f"Received INIT from {addr}. \nSending INIT-ACK...")
                    self.sequence_number_int = randint(0, 10000)
                    acknowledgment_number_int = int(bit_message[0:32], 2) + 1
                    data = self.create_new_bit_field(self.sequence_number_int,acknowledgment_number_int, 24, 4, 0)
                    self.sock.sendto(data, addr)


                elif syn_flag == '1' and ack_flag == '1':
                    # Received SYN-ACK, send ACK to complete handshake
                    print(f"Received INIT-ACK from {addr}. \nSending ACK to complete handshake... ")
                    self.sequence_number_int = randint(0, 10000)
                    acknowledgment_number_int = int(bit_message[0:32], 2) + 1
                    data = self.create_new_bit_field(self.sequence_number_int,acknowledgment_number_int, 8, 4, 0)
                    self.sock.sendto(data, addr)
                    self.connected = True

                elif syn_flag == '0' and ack_flag == '1':
                    print(f"Received ACK from {addr}.\n*** PRESS ENTER TO CONTINUE ***")
                    self.connected = True
            except Exception as e:
                self.connected = False
                continue




    def send_message(self):
        while self.running and self.connected:
            message = input("Enter message ('quit' to end connection): ")
            if message.lower() == 'quit':
                self.running = False
                self.sequence_number_int += 1
                packet = self.create_new_bit_field(self.sequence_number_int, 0, 4, 7, 0)
                self.sock.sendto(packet, (self.target_ip, self.target_port))
                break

            self.sequence_number_int += 1
            packet = self.create_new_bit_field(self.sequence_number_int, 0, 4, 2, 0)

            self.sock.sendto(packet + message.encode('utf-8'), (self.target_ip, self.target_port))


    def receive_message(self):
        while self.running and self.connected:
            try:
                data, addr = self.sock.recvfrom(self.msgsize)
                bit_message = ''.join(f'{byte:08b}' for byte in data)

                msg_type_bits = int(bit_message[85:88])
                if msg_type_bits == 111:
                    self.connected = False
                    break

                data = data[13:]

                # Move the cursor to the beginning of the line before printing the received message
                sys.stdout.write(f"\rReceived from {addr}: {data.decode('utf-8')}\n")
                sys.stdout.flush()
                # Show the input prompt again on the next line
                sys.stdout.write("Enter message ('quit' to end connection): ")
                sys.stdout.flush()
            except socket.error:
                pass

    def start_communication(self):
        # Initiate the handshake
        handshake_thread = threading.Thread(target=self.receive_handshake)
        handshake_thread.daemon = True
        handshake_thread.start()



        # Wait for the handshake to complete
        while not self.connected:

            cmd = input("Enter message 'Handshake': ")
            if cmd == "Handshake" and not self.connected:
                self.send_handshake()
                while not self.connected:
                    pass

        print("Connection established. You can now send messages.")

        # Start sending and receiving messages after cquionnection is established
        receive_thread = threading.Thread(target=self.receive_message)
        receive_thread.daemon = True
        receive_thread.start()

        send_thread = threading.Thread(target=self.send_message)
        send_thread.daemon = True
        send_thread.start()

        try:

            while self.running and self.connected:
                pass
        except KeyboardInterrupt:
            print("Shutting down...")
        finally:
            if self.running:
                return
            print("CLOSING...")
            self.sock.close()


if __name__ == "__main__":
    local_ip = '147.175.160.79'
    local_port = input("local port:")  # 55554 for example
    target_ip = '147.175.160.79'
    target_port = input("target port:")  # 55555 for exapmle

    node = Peer2peer(local_ip, int(local_port), target_ip, int(target_port), 1024)
    while node.running:
        node.start_communication()

