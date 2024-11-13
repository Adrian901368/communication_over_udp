import socket
import threading
import sys
from random import *
import os
import time
import crcmod

HEARTBEAT_INTERVAL = 5         # interval odosielania heartbeat správ v sekundách
HEARTBEAT_TIMEOUT = 10        # timeout na prijatie odpovede v sekundách
MAX_MISSED_HEARTBEATS = 3

FRAGMENT_SIZE = 1500
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
        self.missed_heartbeats = 0
        self.keep_alive_running = True
        self.last_heartbeat_time = None
        self.last_received_msg_time = time.time()
        self.ack_nack_packet = None
        self.crc_success = True

    def crc16(self, data):
        crc16_func = crcmod.predefined.mkPredefinedCrcFun('xmodem')
        return crc16_func(data)

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


    def create_new_bit_field(self, sequence_number, acknowledgment_number, fragment_id, flags, msg_type, checksum):


        sequence_number_bits = f'{sequence_number:032b}'  # 32-bit sequence number
        acknowledgment_number_bits = f'{acknowledgment_number:032b}'  # 32-bit acknowledgment number
        fragment_id_bits = f'{fragment_id:016b}'  # 16-bit fragment ID
        flags_bits = f'{flags:05b}'  # 5-bit flags (for example, SYN flag)F
        msg_type_bits = f'{msg_type:03b}'  # 3-bit message type
        checksum_bits = f'{checksum:016b}'  # 16-bit checksum (set to zero for now)

        return self.merge_bits(sequence_number_bits, acknowledgment_number_bits, fragment_id_bits, flags_bits, msg_type_bits, checksum_bits)

    def send_handshake(self):
        """Send a handshake with a custom protocol message in binary."""
        random_value = randint(0, 10000)  # Generate random sequence numbe

        # Create bit fields
        bit_message = self.create_new_bit_field(random_value, 0,0,16,4, 0 )  # 16-bit checksum (set to zero for now)

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
                    data = self.create_new_bit_field(self.sequence_number_int,acknowledgment_number_int,0, 24, 4, 0)
                    self.sock.sendto(data, addr)


                elif syn_flag == '1' and ack_flag == '1':
                    # Received SYN-ACK, send ACK to complete handshake
                    print(f"Received INIT-ACK from {addr}. \nSending ACK to complete handshake... ")
                    self.sequence_number_int = randint(0, 10000)
                    acknowledgment_number_int = int(bit_message[0:32], 2) + 1
                    data = self.create_new_bit_field(self.sequence_number_int,acknowledgment_number_int,0, 8, 4, 0)
                    self.sock.sendto(data, addr)
                    self.last_received_msg_time = time.time()
                    self.connected = True

                elif syn_flag == '0' and ack_flag == '1':
                    print(f"Received ACK from {addr}.\n*** PRESS ENTER TO CONTINUE ***")
                    self.last_received_msg_time = time.time()
                    self.connected = True
            except Exception as e:
                self.connected = False
                continue

    def send_keep_alive(self):
        while self.keep_alive_running:
            if not self.connected or time.time() - self.last_received_msg_time < HEARTBEAT_TIMEOUT:
                time.sleep(1)
                continue

            if self.missed_heartbeats > 0:

                print(f"Missed heartbeat message({self.missed_heartbeats})")

            # Kontrola, či spojenie nie je ukončené
            if self.missed_heartbeats >= MAX_MISSED_HEARTBEATS:
                print("Connection lost.\nCLOSING...")
                self.keep_alive_running = False
                self.connected = False
                break

            # Odoslanie heartbeat správy
            packet = self.create_new_bit_field(self.sequence_number_int, 0, 0, 1, 2, 0)
            self.sock.sendto(packet, (self.target_ip, self.target_port))
            print("Sent heartbeat message")
            self.last_received_msg_time = time.time()
            sys.stdout.write("Enter 'M' to send a message, 'F' to send a file, or 'Quit' to end connection: ")
            sys.stdout.flush()

            self.missed_heartbeats += 1
            # Ak nie sú prijaté odpovede, zväčši počítadlo


      # Send an ACK for the heartbeat

    def receive_keep_alive(self, ack_flag):
        """Listen for incoming heartbeat messages and respond."""
        self.missed_heartbeats = 0
        if ack_flag:
            return

        # Reset missed heartbeats counter when a heartbeat is received
        print("Received heartbeat message")
        sys.stdout.write("Enter 'M' to send a message, 'F' to send a file, or 'Quit' to end connection: ")
        sys.stdout.flush()

            # Optionally, send an acknowledgment back
        packet = self.create_new_bit_field(self.sequence_number_int, 0, 0, 9, 2, 0)
        self.sock.sendto(packet, (self.target_ip, self.target_port))
            # Reset the last heartbeat time
        self.last_heartbeat_time = time.time()

    def send_ack(self, addr):
        # Send an ACK message
        flags = 8
        ack_packet = self.create_new_bit_field(self.sequence_number_int, 0, 0, flags, 2, 0)
        self.sock.sendto(ack_packet, addr)
        #print('ACK sent')


    def send_nack(self, addr):
        # Send a NACK message (ack_flag set to 0)
        flags = 0  # No ACK flag
        nack_packet = self.create_new_bit_field(self.sequence_number_int, 0, 0, flags, 2, 0)
        self.sock.sendto(nack_packet, addr)
        #print('NACK sent')


    def wait_for_ack_nack(self):
        """Wait for an ACK or NACK response and return the received flags."""
        while True:

            if self.ack_nack_packet is not None:
                break


        bit_message = self.ack_nack_packet
        self.ack_nack_packet = None
        try:

            # Extract the flags from the response
              # Extract header bits
            flags_bits = bit_message[80:85]
            flags = int(flags_bits, 2)
            return flags
        except Exception as e:
            print(f"Error receiving ACK/NACK: {e}")
            return None


    def send_message(self):
        last_action_time = time.time()
        while self.running and self.connected:
            choice = input("Enter 'M' to send a message, 'F' to send a file, or 'Quit' to end connection: ").strip().lower()

            if choice == 'm':
                message = input("Enter message ('Quit' to end connection): ")
                if message.lower() == 'quit':
                    self.running = False
                    self.sequence_number_int += 1
                    packet = self.create_new_bit_field(self.sequence_number_int, 0,0, 4, 7, 0)
                    self.sock.sendto(packet, (self.target_ip, self.target_port))
                    break
                else:
                    print("Message sent.")


                crc = self.crc16(message.encode('utf-8'))

                self.sequence_number_int += 1
                packet = self.create_new_bit_field(self.sequence_number_int, 0,0, 4, 2, crc)
                self.sock.sendto(packet + message.encode('utf-8'), (self.target_ip, self.target_port))

            elif choice == 'f':
                file_path = input("Enter the file path: ").strip()
                self.send_file(file_path)

            elif choice == 'quit':
                self.running = False
                self.sequence_number_int += 1
                packet = self.create_new_bit_field(self.sequence_number_int, 0, 0,4, 7, 0)
                self.sock.sendto(packet, (self.target_ip, self.target_port))
                break

            else:
                print("Invalid input. Please enter 'M', 'F', or 'Quit'.")

    def receive_message(self):
        while self.running and self.connected:
            try:
                data, addr = self.sock.recvfrom(self.msgsize)
                self.last_received_msg_time = time.time()
                bit_message = ''.join(f'{byte:08b}' for byte in data[:13])  # Extract header bits

                # Parse message type and flags from header
                msg_type_bits = int(bit_message[85:88], 2)
                crc_control = int(bit_message[88:], 2)

                if msg_type_bits == 111:
                    # End of connection
                    self.connected = False
                    break

                if msg_type_bits == 4:  # File message type
                    # Call receive_file to handle the file transfer
                    self.receive_file(data, addr)
                        # Send ACK if fragment received successfully
                    #self.send_ack(addr)
                    #else:
                        # Send NACK if fragment is invalid or timed out
                     #   self.send_nack(addr)

                else:
                    flags = int(bit_message[80:85], 2)

                    if flags in [0, 8]:
                        self.ack_nack_packet = bit_message
                        continue

                    keep_alive_flag = int(bit_message[84], 2)
                    if keep_alive_flag == 1:
                        ack_flag = int(bit_message[81], 2)
                        self.receive_keep_alive(ack_flag)
                        continue


                    # Assume it's a text message if msg_type is not file
                    data = data[13:]  # Strip header bits
                    crc = self.crc16(data)
                    received_text = data.decode('utf-8')


                    # Move cursor to the beginning of the line, clear it, then print the received message
                    sys.stdout.write(f"\r{' ' * 80}\r")  # Clear the current line
                    if crc == crc_control:
                        sys.stdout.write(f"Received from {addr} (crc success): {received_text}\n")
                    else:
                        sys.stdout.write(f"Received from {addr} (crc failure): {received_text}\n")
                    sys.stdout.flush()

                    # Show the input prompt again on the next line
                    sys.stdout.write("Enter 'M' to send a message, 'F' to send a file, or 'Quit' to end connection: ")
                    sys.stdout.flush()
            except socket.error:
                pass

    def send_file(self, file_path):
        """Send a file in fragments if needed."""
        try:

            with open(file_path, 'rb') as f:

                fragment_id = 1
                while True:
                    # Read a fragment of the file
                    file_data = f.read(self.msgsize - 13)  # Reserve 13 bytes for the header

                    if not file_data:
                        # No more data to read, file is fully sent
                        break

                    # Set flags based on whether this is the last fragment
                    if len(file_data) < (self.msgsize - 13):
                        flags = 4  # Last fragment
                    else:
                        flags = 2  # More fragments

                    crc = self.crc16(file_data)
                    # Create the packet with headers and file data
                    packet = self.create_new_bit_field(
                        sequence_number=self.sequence_number_int,
                        acknowledgment_number=0,
                        fragment_id=fragment_id,
                        flags=flags,
                        msg_type=4,  # File message type
                        checksum=crc
                    )
                    packet += file_data

                    # Send the fragment
                    self.sock.sendto(packet, (self.target_ip, self.target_port))

                    # Log the fragment being sent
                    print(f"Sent fragment {fragment_id} with sequence number {self.sequence_number_int}")

                    retry_count = 0
                    while retry_count < 3:
                        flags = self.wait_for_ack_nack()

                        # Handle ACK/NACK based on received flags
                        if flags == 8:
                            #print(f"ACK received for fragment {fragment_id}")
                            break  # Break the retry loop if ACK is received
                        elif flags == 0:
                            print(f"NACK received for fragment {fragment_id}, retransmitting...")
                            self.sock.sendto(packet, (self.target_ip, self.target_port))  # Retransmit the fragment
                            retry_count += 1  # Increment retry counter
                        else:
                            print(f"Unexpected flags {flags} received, ignoring.")
                            break  # Exit retry loop for unexpected flags

                    # If retry count reaches 3, mark the fragment as lost
                    if retry_count == 3:
                        print(f"Fragment {fragment_id} lost after 3 attempts.")
                        # Optionally, handle the lost fragment (log, skip, etc.)

                    fragment_id += 1
                    self.sequence_number_int += 1

            print("File sent successfully.")


        except FileNotFoundError:
            print("File not found. Please check the file path and try again.")
        except Exception as e:
            print(f"An error occurred while sending the file: {e}")

    def receive_file(self, data, addr):
        #data, addr = self.sock.recvfrom(self.msgsize)
        """Receive a file in fragments and reconstruct it."""
        fragments = {}
        fragment_id = 0
        while self.running and self.connected:
            try:



                bit_message = ''.join(f'{byte:08b}' for byte in data[:13])  # Extract header bits

                # Parse the header bits for file data
                flags = int(bit_message[80:85], 2)

                fragment_id = int(bit_message[64:80], 2)

                crc_control = int(bit_message[88:], 2)  # crc checksum
                # Save fragment data (after header) in the correct order
                fragments[fragment_id] = data[13:]


                crc = self.crc16(fragments[fragment_id])

                if crc == crc_control:
                    print(f"fragment number {fragment_id} -- flags {flags} -- crc succesfull")

                else:
                    print(f"fragment number {fragment_id} -- flags {flags} -- error crc not succesfull")
                    self.crc_success = False

                self.send_ack(addr)

                # If this is the last fragment (no more fragments flag), break out of loop
                if flags == 4 :
                    break
                data, addr = self.sock.recvfrom(self.msgsize)
                self.last_received_msg_time = time.time()


            except socket.timeout:
                print("Timeout occurred while waiting for fragment.")
                # Send NACK if there was a timeout waiting for the fragment
                self.send_nack(addr)

            except Exception as e:
                print(f"Error receiving fragment {fragment_id}: {e}")
                # Send NACK if there was an error with the fragment
                self.send_nack(addr)

        # Reconstruct the file from fragments
        file_data = b''.join([fragments[i] for i in sorted(fragments)])

        # Define the downloads folder path and file name
        download_path = "C:/Users/001ba/Downloads"  # Using expanduser to resolve paths
        file_path = os.path.join(download_path, "new_file")

        # Save the reconstructed file data
        try:
            with open(file_path, 'wb') as f:
                f.write(file_data)
            if self.crc_success:
                print(f"File received and saved as '{file_path}' ")
            elif not self.crc_success:
                print(f"File received and saved as '{file_path}' with error crc not succesful")
            sys.stdout.write("Enter 'M' to send a message, 'F' to send a file, or 'Quit' to end connection: ")
            sys.stdout.flush()

        except socket.timeout:
            print("Timeout occurred while receiving file.")

        except FileNotFoundError:
            print("Downloads folder path does not exist.")
            sys.stdout.write("Enter 'M' to send a message, 'F' to send a file, or 'Quit' to end connection: ")
            sys.stdout.flush()

        except PermissionError:
            print("Permission denied: unable to save the file in the specified directory.")
            sys.stdout.write("Enter 'M' to send a message, 'F' to send a file, or 'Quit' to end connection: ")
            sys.stdout.flush()

        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            sys.stdout.write("Enter 'M' to send a message, 'F' to send a file, or 'Quit' to end connection: ")
            sys.stdout.flush()


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

        keep_alive_send_thread = threading.Thread(target=self.send_keep_alive)
        keep_alive_send_thread.daemon = True
        keep_alive_send_thread.start()

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
    local_ip =  '10.10.18.243'
    local_port = input("local port:")  # 55554 for example
    target_ip =  '10.10.18.243'
    target_port = input("target port:")  # 55555 for exapmle

    node = Peer2peer(local_ip, int(local_port), target_ip, int(target_port), FRAGMENT_SIZE)
    while node.running:
        node.start_communication()