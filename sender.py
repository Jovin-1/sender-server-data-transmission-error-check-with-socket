# sender.py
"""
Interactive Sender (formerly Server client).
Runs a loop prompting the user for data to transmit.
Each iteration sends a TRANSMISSION_REQUEST, receives the Server's replies,
and displays the outcome.
It now supports an optional *noise* mode that inserts a delay before
sending the request and also probabilistically corrupts the payload
according to the chosen delay – higher delay means a noisier environment
and a higher chance of corruption.
"""
import argparse
import socket
import sys
import math
import time
import random

from config import HOST, PORT, BLOCK_SIZE, SIMULATE_ERROR
from protocol import send_message, receive_message, crc32
from noise import get_delay


def parse_args():
    parser = argparse.ArgumentParser(description="Interactive Sender for reliable protocol.")
    parser.add_argument(
        "--error",
        action="store_true",
        help="Enable global error simulation (corrupt payload after CRC).",
    )
    parser.add_argument(
        "--noise-mode",
        choices=["no_noise", "noise"],
        default="no_noise",
        help="Select transmission noise mode. 'noise' asks for a delay between 0.1 and 10 seconds.",
    )
    return parser.parse_args()


def maybe_corrupt(payload: str, delay: float) -> str:
    """Corrupt *payload* based on *delay*.

    The larger the *delay* (i.e., the noisier the environment), the higher
    the probability of corruption.  We map the delay linearly to a probability
    in the range 0 – 1 using ``prob = min(1.0, delay / 10)``.
    If a random draw falls below *prob*, we flip a single random character
    (simple bit‑flip) to simulate data disturbance.
    """
    prob = min(1.0, delay / 10.0)
    if random.random() < prob:
        if not payload:
            return payload
        idx = random.randrange(len(payload))
        # Flip the lowest bit of the selected character
        orig_char = payload[idx]
        corrupted_char = chr(ord(orig_char) ^ 0x01)
        corrupted = payload[:idx] + corrupted_char + payload[idx + 1 :]
        print(f"[SENDER] Environmental disturbance applied – payload corrupted at position {idx}.")
        return corrupted
    return payload


def main():
    args = parse_args()
    # Propagate error flag to config (global) for this run
    global SIMULATE_ERROR
    SIMULATE_ERROR = args.error

    print("\n=== SENDER STARTED ===")
    print("Enter data to send. Empty line to quit.")

    while True:
        data = input("[SENDER] Payload: ")
        if data == "":
            print("[SENDER] No data entered – exiting.")
            break

        payload = data
        size = len(payload.encode("utf-8"))
        filename = "demo_file.txt"

        # Determine optional noise delay before establishing connection
        delay = get_delay(args.noise_mode)
        if delay > 0:
            print(f"[SENDER] Simulating environmental disturbance: sleeping {delay:.2f}s before connecting.")
            time.sleep(delay)
        # Open a fresh connection for each transmission
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.settimeout(120)  # increased timeout for operator decision
                sock.connect((HOST, PORT))
                # No additional delay here after connection
                print("[SENDER] Sending TRANSMISSION_REQUEST ...")
            except (socket.timeout, ConnectionRefusedError) as exc:
                print(f"[SENDER] Connection failed: {exc}")
                continue

            # 1️⃣ TRANSMISSION_REQUEST
            request_msg = {
                "type": "TRANSMISSION_REQUEST",
                "source": "Sender",
                "filename": filename,
                "size": size,
            }
            send_message(sock, request_msg)

            # 2️⃣ WAIT FOR ACCEPT / REJECT
            reply = receive_message(sock)
            if reply.get("type") == "REQUEST_REJECTED":
                print(f"[SENDER] Request rejected: {reply.get('error')}")
                continue
            print("[SENDER] Request accepted by Server.")

            # 3️⃣ STORAGE_REPLY (available / rejected)
            storage_reply = receive_message(sock)
            if storage_reply.get("type") == "STORAGE_REJECTED":
                print(f"[SENDER] Storage rejected: {storage_reply.get('reason')}")
                continue
            print(
                f"[SENDER] Storage available – required blocks: {storage_reply.get('required_blocks')}, free: {storage_reply.get('available_blocks')}"
            )

            # 4️⃣ AUTHORIZATION_ACK
            auth_ack = receive_message(sock)
            if auth_ack.get("type") != "AUTHORIZATION_ACK":
                print("[SENDER] Expected AUTHORIZATION_ACK – aborting.")
                continue
            print("[SENDER] Received AUTHORIZATION_ACK.")

            # 5️⃣ POSSIBLE CORRUPTION BEFORE CRC CALCULATION
            # Apply environmental disturbance based on delay
            crc_val = crc32(payload)
            payload_to_send = maybe_corrupt(payload, delay)
            crc_to_send = int(maybe_corrupt(str(crc_val), delay/7))
            # 6️⃣ SEND DATA + CRC (calculated on possibly corrupted payload)

            data_msg = {"type": "DATA", "payload": payload_to_send, "crc": crc_to_send}
            print(f"[SENDER] Calculated CRC: {crc_val}")
            send_message(sock, data_msg)

            # 7️⃣ FINAL_ACK / NACK
            final_reply = receive_message(sock)
            if final_reply.get("type") == "FINAL_ACK":
                print("[SENDER] Transaction successful – FINAL_ACK received.")
            elif final_reply.get("type") == "NACK":
                print(f"[SENDER] Transaction failed – {final_reply.get('error')}")
            else:
                print(f"[SENDER] Unexpected reply: {final_reply}")

            # Optional graceful disconnect
            try:
                send_message(sock, {"type": "DISCONNECT"})
            except Exception:
                pass

    print("[SENDER] Exiting.")

if __name__ == "__main__":
    main()
