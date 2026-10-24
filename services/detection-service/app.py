from fastapi import FastAPI
from datetime import datetime
from collections import deque
import logging
import httpx


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("detection-service")


# ============================================================
# FastAPI
# ============================================================

app = FastAPI(
    title="Cyber Defense Detection Engine",
    version="2.0.0"
)


# ============================================================
# Security Event Storage
# ============================================================

security_events = deque(maxlen=1000)


# ============================================================
# Agent Service
# ============================================================

AGENT_SERVICE_URL = "http://agent-service:8003/analyze"


# ============================================================
# Health Check
# ============================================================

@app.get("/")
def health_check():

    return {
        "service": "detection-service",
        "status": "running"
    }


# ============================================================
# Security Event Ingestion
# ============================================================

@app.post("/events")
async def ingest_event(event: dict):

    timestamp = datetime.utcnow().isoformat()

    # Do not modify the original event structure
    stored_event = dict(event)

    stored_event["received_at"] = timestamp

    security_events.append(stored_event)

    client_ip = stored_event.get(
        "client_ip",
        "unknown"
    )

    logger.info(
        f"SECURITY EVENT | "
        f"type={stored_event.get('event_type')} | "
        f"client={client_ip} | "
        f"path={stored_event.get('path')}"
    )

    # --------------------------------------------------------
    # Send event to Agent Service
    # --------------------------------------------------------

    try:

        async with httpx.AsyncClient(
            timeout=5.0
        ) as client:

            response = await client.post(
                AGENT_SERVICE_URL,
                json=stored_event
            )

        response.raise_for_status()

        agent_response = response.json()

        logger.info(
            f"AGENT DECISION | "
            f"client={client_ip} | "
            f"decision={agent_response}"
        )

        # The Agent returns its final decision inside the
        # `decision` field. Flatten the important fields here so
        # the API Gateway can consume the decision directly.
        decision = agent_response.get("decision", {})

        if not isinstance(decision, dict):
            decision = {}

        return {
            "status": "analyzed",
            "threat_detected": bool(decision.get("threat")),
            "threat": decision.get("threat"),
            "risk_score": decision.get("risk_score"),
            "confidence": decision.get("confidence"),
            "recommended_action": decision.get("recommended_action"),
            "reasoning": decision.get("reasoning", []),
            "decision": decision,
            "agent_response": agent_response
        }

    except httpx.TimeoutException:

        logger.error(
            f"AGENT SERVICE TIMEOUT | "
            f"client={client_ip}"
        )

        return {
            "status": "event_recorded",
            "threat_detected": False,
            "agent_service": "timeout"
        }

    except httpx.RequestError as e:

        logger.error(
            f"AGENT SERVICE ERROR | "
            f"client={client_ip} | "
            f"error={str(e)}"
        )

        return {
            "status": "event_recorded",
            "threat_detected": False,
            "agent_service": "unavailable"
        }

    except Exception as e:

        logger.error(
            f"AGENT INTEGRATION ERROR | "
            f"client={client_ip} | "
            f"error={str(e)}"
        )

        return {
            "status": "event_recorded",
            "threat_detected": False,
            "agent_service": "error"
        }


# ============================================================
# Security Events
# ============================================================

@app.get("/events")
def get_events():

    return {
        "total_events": len(security_events),
        "events": list(security_events)
    }