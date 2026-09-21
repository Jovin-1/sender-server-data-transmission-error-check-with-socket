"""
protocol_states.py
==================
Protocol State Machine Definitions
Captures every distinct state that each component (Server, Middleman, Database)
can occupy during the transmission lifecycle.

State-transition diagram (high-level):

  SERVER                   MIDDLEMAN                  DATABASE
  ──────                   ─────────                  ────────
  IDLE ──────────────────► IDLE
  REQUESTING               EVALUATING
  AWAITING_AUTH ◄────────  QUERYING_DB ─────────────► IDLE
                                        ◄──────────────RESPONDING
  TRANSMITTING ──────────► (RECEIVING)
  AWAITING_FINAL_ACK ◄──── VALIDATING
  DONE / ERROR             ACK_SENT / ERROR
"""

from enum import Enum, auto


class ServerState(Enum):
    """States for the Server component."""
    IDLE              = auto()   # Doing nothing; ready to start
    REQUESTING        = auto()   # Sending a transmission request to MM
    AWAITING_AUTH     = auto()   # Waiting for ACK-1 (authorization) from MM
    TRANSMITTING      = auto()   # Actively sending EDC-encoded data frames
    AWAITING_FINAL_ACK= auto()   # Waiting for ACK-2 (completion) from MM
    DONE              = auto()   # Transaction completed successfully
    ERROR             = auto()   # Unrecoverable error; session aborted


class MiddlemanState(Enum):
    """States for the Middleman component."""
    IDLE         = auto()   # Waiting for incoming requests
    EVALUATING   = auto()   # Deciding whether to accept or reject the request
    QUERYING_DB  = auto()   # Asking the Database for available space
    AUTHORIZING  = auto()   # Sending ACK-1 to the Server
    RECEIVING    = auto()   # Collecting incoming data frames
    VALIDATING   = auto()   # Running EDC verification on received data
    ACK_SENT     = auto()   # Final ACK-2 dispatched to Server
    REJECTED     = auto()   # Request was rejected (policy / DB full)
    ERROR        = auto()   # Validation failure or unexpected condition


class DatabaseState(Enum):
    """States for the Database component."""
    IDLE         = auto()   # Standby; no active query
    QUERIED      = auto()   # Received a storage-check query from MM
    RESPONDING   = auto()   # Computing and returning available-space answer
    WRITING      = auto()   # Persisting data blocks into the 2D array
    DONE         = auto()   # Write operation completed successfully
    ERROR        = auto()   # Insufficient space or write failure


# ---------------------------------------------------------------------------
# Lightweight protocol-message tokens passed between components
# ---------------------------------------------------------------------------
class Signal(Enum):
    """Inter-component signals (akin to PDU control fields)."""
    REQUEST         = "REQUEST"          # Server → MM: "I want to transmit"
    ACCEPT          = "ACCEPT"           # MM internal: request passes policy
    REJECT          = "REJECT"           # MM internal: request denied
    DB_QUERY        = "DB_QUERY"         # MM → DB: "do you have N bytes free?"
    DB_OK           = "DB_OK"            # DB → MM: "yes, space confirmed"
    DB_FULL         = "DB_FULL"          # DB → MM: "insufficient space"
    ACK_1           = "ACK_1"            # MM → Server: "authorized, start sending"
    NACK            = "NACK"             # MM → Server: "request rejected"
    DATA_FRAME      = "DATA_FRAME"       # Server → MM: data payload frame
    VALIDATE_OK     = "VALIDATE_OK"      # MM internal: EDC check passed
    VALIDATE_FAIL   = "VALIDATE_FAIL"    # MM internal: EDC check failed
    ACK_2           = "ACK_2"            # MM → Server: "data received & stored"
    DB_WRITE        = "DB_WRITE"         # MM → DB: "persist this data"
    DB_WRITE_OK     = "DB_WRITE_OK"      # DB → MM: "write successful"
