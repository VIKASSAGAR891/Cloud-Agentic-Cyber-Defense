from fastapi import FastAPI, BackgroundTasks
from datetime import datetime
from collections import deque
import logging
import json
import os
import urllib.request
import threading


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("agent-service")


# ============================================================
# FastAPI
# ============================================================

app = FastAPI(
    title="Cyber Defense Agent",
    version="3.0.0"
)


# ============================================================
# Decision Storage
# ============================================================

decisions = deque(maxlen=1000)

decision_lock = threading.Lock()


# ============================================================
# Configuration
# ============================================================

BRUTE_FORCE_RISK = 80
RATE_LIMIT_ABUSE_RISK = 70
BEHAVIORAL_ANOMALY_RISK = 85

HIGH_RISK_THRESHOLD = 75
MEDIUM_RISK_THRESHOLD = 50


# ============================================================
# Ollama Configuration
# ============================================================

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://host.docker.internal:11434"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:7b"
)

# LLM runs in the background, so this timeout does NOT delay
# the security decision or the HTTP response.
OLLAMA_TIMEOUT = int(
    os.getenv("OLLAMA_TIMEOUT", "120")
)


# ============================================================
# Health Check
# ============================================================

@app.get("/")
def health_check():

    return {
        "service": "agent-service",
        "status": "running",
        "llm_enabled": True,
        "llm_provider": "ollama",
        "llm_model": OLLAMA_MODEL,
        "llm_mode": "asynchronous"
    }


# ============================================================
# Ollama LLM Reasoning
# ============================================================

def get_llm_reasoning(event: dict, deterministic_decision: dict):

    """
    Perform contextual cybersecurity reasoning using Ollama.

    IMPORTANT:
    The LLM is advisory only.

    It cannot modify:
    - risk_score
    - confidence
    - recommended_action

    The deterministic security engine remains authoritative.
    """

    prompt = f"""
You are the reasoning component of a cloud-native cybersecurity
defense system.

Analyze the following security event and provide concise,
security-focused contextual reasoning.

Security event:
{json.dumps(event, indent=2)}

Deterministic security assessment:
{json.dumps({
    "threat": deterministic_decision["threat"],
    "risk_score": deterministic_decision["risk_score"],
    "confidence": deterministic_decision["confidence"],
    "recommended_action": deterministic_decision["recommended_action"]
}, indent=2)}

Your role is to provide additional contextual reasoning.

IMPORTANT:
- Do not change the deterministic risk score.
- Do not override the deterministic recommended action.
- Do not invent evidence.
- Explain why the observed behaviour may be suspicious.
- Mention plausible benign explanations when appropriate.
- Identify useful additional telemetry.

Keep the response concise.

Return ONLY valid JSON:

{{
    "assessment": "short overall assessment",
    "severity_context": "low, medium, high, or critical",
    "reasoning": [
        "reason 1",
        "reason 2"
    ],
    "recommended_observations": [
        "observation 1",
        "observation 2"
    ]
}}
"""

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a cybersecurity incident reasoning assistant. "
                    "Return only valid JSON."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.2,
            "num_predict": 512,
            "format": "json"
        }
    }

    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:

        logger.info(
            f"LLM ANALYSIS START | "
            f"model={OLLAMA_MODEL} | "
            f"event={event.get('event_type')}"
        )

        with urllib.request.urlopen(
            request,
            timeout=OLLAMA_TIMEOUT
        ) as response:

            raw_response = response.read().decode("utf-8")

        ollama_response = json.loads(raw_response)

        content = (
            ollama_response
            .get("message", {})
            .get("content", "")
        )

        if not content:

            raise ValueError(
                "Ollama returned an empty response"
            )

        llm_result = json.loads(content)

        logger.info(
            f"LLM ANALYSIS COMPLETE | "
            f"model={OLLAMA_MODEL} | "
            f"assessment={llm_result.get('assessment')}"
        )

        return {
            **llm_result,
            "llm_available": True
        }

    except Exception as exc:

        logger.warning(
            f"LLM ANALYSIS FAILED | "
            f"model={OLLAMA_MODEL} | "
            f"error={exc}"
        )

        return {
            "assessment": (
                "LLM reasoning unavailable; "
                "deterministic security analysis retained."
            ),
            "severity_context": "unknown",
            "reasoning": [],
            "recommended_observations": [],
            "llm_available": False,
            "error": str(exc)
        }


# ============================================================
# Background LLM Worker
# ============================================================

def run_background_llm_analysis(
    event: dict,
    decision: dict
):

    """
    Execute LLM reasoning after the deterministic security
    decision has already been returned.

    This prevents slow local LLM inference from delaying
    security enforcement.
    """

    try:

        llm_result = get_llm_reasoning(
            event,
            decision
        )

        with decision_lock:

            decision["llm_analysis"] = llm_result

            decision["llm_status"] = (
                "completed"
                if llm_result.get("llm_available", False)
                else "failed"
            )

        logger.info(
            f"BACKGROUND LLM UPDATE | "
            f"client={decision.get('client_ip')} | "
            f"event={decision.get('event_type')} | "
            f"status={decision.get('llm_status')}"
        )

    except Exception as exc:

        logger.error(
            f"BACKGROUND LLM WORKER ERROR | "
            f"client={decision.get('client_ip')} | "
            f"error={exc}"
        )

        with decision_lock:

            decision["llm_status"] = "failed"


# ============================================================
# Security Decision Engine
# ============================================================

def analyze_security_event(
    event: dict,
    background_tasks: BackgroundTasks
):

    event_type = event.get(
        "event_type",
        "UNKNOWN"
    )

    client_ip = event.get(
        "client_ip",
        "unknown"
    )

    path = event.get(
        "path",
        "/"
    )

    risk_score = 0
    threat = "UNKNOWN_ACTIVITY"
    action = "MONITOR"
    confidence = 0.50

    reasoning = []

    # --------------------------------------------------------
    # Brute Force Analysis
    # --------------------------------------------------------

    if event_type == "AUTH_FAILURE":

        risk_score = BRUTE_FORCE_RISK
        threat = "BRUTE_FORCE_SUSPECTED"
        confidence = 0.90

        reasoning.append(
            "Repeated authentication failures indicate "
            "possible credential attack behavior."
        )

    # --------------------------------------------------------
    # Rate Limit Abuse Analysis
    # --------------------------------------------------------

    elif event_type == "RATE_LIMIT":

        risk_score = RATE_LIMIT_ABUSE_RISK
        threat = "RATE_LIMIT_ABUSE"
        confidence = 0.85

        reasoning.append(
            "Repeated rate-limit violations indicate "
            "abnormal request activity."
        )

    # --------------------------------------------------------
    # Behavioural Anomaly Analysis
    # --------------------------------------------------------

    elif event_type == "BEHAVIORAL_ANOMALY":

        risk_score = BEHAVIORAL_ANOMALY_RISK
        threat = "HIGH_REQUEST_FREQUENCY"
        confidence = 0.90

        reasoning.append(
            "Behavioural analysis detected an unusually high "
            "request frequency within a short time window."
        )

    # --------------------------------------------------------
    # Unknown Activity
    # --------------------------------------------------------

    else:

        risk_score = 30
        threat = "UNKNOWN_ACTIVITY"
        confidence = 0.40

        reasoning.append(
            "The event does not match a known attack pattern."
        )

    # --------------------------------------------------------
    # Deterministic Risk-Based Decision
    # --------------------------------------------------------

    if risk_score >= HIGH_RISK_THRESHOLD:

        action = "BLOCK_CLIENT"

        reasoning.append(
            "Risk score exceeds the high-risk threshold; "
            "blocking the client is recommended."
        )

    elif risk_score >= MEDIUM_RISK_THRESHOLD:

        action = "TEMPORARY_BLOCK"

        reasoning.append(
            "Risk score indicates suspicious behavior; "
            "temporary blocking is recommended."
        )

    else:

        action = "MONITOR"

        reasoning.append(
            "Risk remains below mitigation thresholds; "
            "continue monitoring."
        )

    # --------------------------------------------------------
    # Deterministic Decision Object
    # --------------------------------------------------------

    decision = {
        "timestamp": datetime.utcnow().isoformat(),
        "client_ip": client_ip,
        "path": path,
        "event_type": event_type,
        "threat": threat,
        "risk_score": risk_score,
        "confidence": confidence,
        "recommended_action": action,
        "reasoning": reasoning,

        # LLM state starts as pending.
        "llm_status": "pending",

        "llm_analysis": {
            "assessment": (
                "LLM analysis running asynchronously."
            ),
            "severity_context": "pending",
            "reasoning": [],
            "recommended_observations": [],
            "llm_available": None
        }
    }

    # --------------------------------------------------------
    # Store Decision Immediately
    # --------------------------------------------------------

    with decision_lock:
        decisions.append(decision)

    # --------------------------------------------------------
    # Start Background LLM Analysis
    # --------------------------------------------------------

    background_tasks.add_task(
        run_background_llm_analysis,
        event,
        decision
    )

    # --------------------------------------------------------
    # Security Logging
    # --------------------------------------------------------

    logger.warning(
        f"AGENT DECISION | "
        f"client={client_ip} | "
        f"event={event_type} | "
        f"threat={threat} | "
        f"risk={risk_score} | "
        f"action={action} | "
        f"llm_status=pending"
    )

    return decision


# ============================================================
# Agent Analysis Endpoint
# ============================================================

@app.post("/analyze")
def analyze_event(
    event: dict,
    background_tasks: BackgroundTasks
):

    logger.info(
        f"AGENT ANALYSIS | "
        f"event_type={event.get('event_type')} | "
        f"client={event.get('client_ip')}"
    )

    decision = analyze_security_event(
        event,
        background_tasks
    )

    return {
        "status": "analyzed",
        "decision": decision
    }


# ============================================================
# Decision History
# ============================================================

@app.get("/decisions")
def get_decisions():

    with decision_lock:

        return {
            "total_decisions": len(decisions),
            "decisions": list(decisions)
        }