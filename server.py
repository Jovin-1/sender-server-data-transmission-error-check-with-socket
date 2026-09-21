# server.py
"""
Intermediary component (formerly Middleman) – now called **Server**.
It receives transmission requests from the **Sender**, lets the operator
manually decide whether to accept the request, checks storage, reserves
blocks, validates CRC, stores data, and replies appropriately.
"""
import socket
import threading
import math
from enum import Enum, auto
from typing import List

from config import HOST, PORT, BLOCK_SIZE, SIMULATE_ERROR
from protocol import send_message, receive_message, crc32
from database import Database


class ServerState(Enum):
    IDLE = auto()
    WAITING_FOR_REQUEST = auto()
    EVALUATING_REQUEST = auto()
    USER_DECISION = auto()
    CHECKING_STORAGE = auto()
    STORAGE_RESERVED = auto()
    AUTHORIZATION_SENT = auto()
    WAITING_FOR_DATA = auto()
    VALIDATING_DATA = auto()
    STORING_DATA = auto()
    COMPLETED = auto()
    REJECTED = auto()
    ERROR = auto()


class Server:
    def __init__(self):
        self.state = ServerState.IDLE
        self.db = Database()
        self.reserved_indices: List[int] = []

    # ------------------------------------------------------------------
    def log(self, msg: str) -> None:
        print(f"[SERVER] {msg}")

    # ------------------------------------------------------------------
    def handle_sender(self, conn: socket.socket, addr):
        conn.settimeout(120)  # increased to handle noise delays
        self.state = ServerState.WAITING_FOR_REQUEST
        try:
            # 1️⃣ RECEIVE TRANSMISSION_REQUEST
            request = receive_message(conn)
            if request.get("type") != "TRANSMISSION_REQUEST":
                self.log("First message not TRANSMISSION_REQUEST – rejecting.")
                send_message(
                    conn,
                    {"type": "REQUEST_REJECTED", "error": "Expected TRANSMISSION_REQUEST"},
                )
                self.state = ServerState.REJECTED
                return

            self.state = ServerState.EVALUATING_REQUEST
            self.log(f"Request received: {request}")
            size = request.get("size")
            filename = request.get("filename")
            source = request.get("source")
            if (
                not isinstance(size, int)
                or size <= 0
                or not isinstance(filename, str)
                or not isinstance(source, str)
            ):
                send_message(
                    conn,
                    {"type": "REQUEST_REJECTED", "error": "Malformed request fields"},
                )
                self.state = ServerState.REJECTED
                return

            # ----------------------------------------------------------
            # 2️⃣ USER MANUAL DECISION – accept or reject the request
            # ----------------------------------------------------------
            self.state = ServerState.USER_DECISION
            while True:
                decision = input("[SERVER] Accept this transmission request? (y/n): ").strip().lower()
                if decision in ("y", "n"):
                    break
                print("Please answer 'y' or 'n'.")
            if decision == "n":
                send_message(
                    conn,
                    {"type": "REQUEST_REJECTED", "error": "Operator rejected the request"},
                )
                self.log("Operator rejected the request.")
                self.state = ServerState.REJECTED
                return

            # Operator accepted – acknowledge request
            send_message(conn, {"type": "REQUEST_ACCEPTED", "message": "Operator accepted request."})
            self.state = ServerState.CHECKING_STORAGE

            # 3️⃣ STORAGE CHECK
            required_blocks = math.ceil(size / BLOCK_SIZE)
            if not self.db.check_storage(required_blocks):
                send_message(
                    conn,
                    {"type": "STORAGE_REJECTED", "reason": "Not enough free blocks."},
                )
                self.log("Insufficient storage – rejecting.")
                self.state = ServerState.REJECTED
                return

            # Reserve blocks temporarily
            self.reserved_indices = self.db.reserve_storage(required_blocks)
            self.log(f"Reserved blocks indices: {self.reserved_indices}")

            # Inform sender about storage availability (optional)
            send_message(
                conn,
                {
                    "type": "STORAGE_AVAILABLE",
                    "required_blocks": required_blocks,
                    "available_blocks": len(self.db._free_indices()),
                },
            )
            self.state = ServerState.AUTHORIZATION_SENT

            # 4️⃣ AUTHORIZATION_ACK
            send_message(
                conn,
                {"type": "AUTHORIZATION_ACK", "message": "Storage reserved, send data."},
            )
            self.state = ServerState.WAITING_FOR_DATA

            # 5️⃣ RECEIVE DATA
            data_msg = receive_message(conn)
            if data_msg.get("type") != "DATA":
                send_message(conn, {"type": "NACK", "error": "Expected DATA after ACK"})
                self.state = ServerState.ERROR
                return
            payload = data_msg.get("payload")
            recv_crc = data_msg.get("crc")
            if payload is None or recv_crc is None:
                send_message(conn, {"type": "NACK", "error": "Missing payload or CRC"})
                self.state = ServerState.ERROR
                return

            # 6️⃣ OPTIONAL error simulation (kept from config flag)
            if SIMULATE_ERROR:
                if payload:
                    corrupted = chr(ord(payload[0]) ^ 0x01) + payload[1:]
                    self.log("[SIMULATION] Corrupting payload to force CRC mismatch.")
                    payload = corrupted

            self.state = ServerState.VALIDATING_DATA
            calculated_crc = crc32(payload)
            self.log(f"Received CRC: {recv_crc}, Calculated CRC: {calculated_crc}")
            if calculated_crc != recv_crc:
                # CRC mismatch – release reservation and NACK
                self.db.release_reservation(self.reserved_indices)
                self.log("CRC mismatch – reservation released.")
                send_message(conn, {"type": "NACK", "error": "CRC mismatch"})
                self.state = ServerState.REJECTED
                return

            # 7️⃣ STORE DATA
            self.state = ServerState.STORING_DATA
            self.db.store_data(payload, self.reserved_indices)
            self.log("Data stored successfully.")
            send_message(conn, {"type": "FINAL_ACK", "message": "Data stored."})
            self.state = ServerState.COMPLETED

        except (ConnectionError, socket.timeout) as exc:
            self.log(f"Connection problem: {exc}")
            self.state = ServerState.ERROR
            if self.reserved_indices:
                self.db.release_reservation(self.reserved_indices)
        finally:
            conn.close()
            self.log("Connection closed.")
            self.db.display()
            self.state = ServerState.IDLE


def start_server():
    print("\n=== INTERMEDIARY SERVER STARTED ===")
    srv = Server()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listen_sock:
        listen_sock.bind((HOST, PORT))
        listen_sock.listen(1)
        print(f"[SERVER] Listening on {HOST}:{PORT}")
        while True:
            try:
                conn, addr = listen_sock.accept()
                print(f"[SERVER] Accepted connection from {addr}")
                thread = threading.Thread(
                    target=srv.handle_sender, args=(conn, addr), daemon=True
                )
                thread.start()
                thread.join()
                print("[SERVER] Ready for next sender.\n")
            except KeyboardInterrupt:
                print("\n[SERVER] Shutting down.")
                break

if __name__ == "__main__":
    start_server()
