"""
Lightweight NER wrapper used by the import pipeline.

This module attempts to load spaCy and a language model. If spaCy is not
available, it provides a conservative rule-based fallback so the rest of the
app can function without ML dependencies.
"""

import logging
import re
from typing import Any, Dict

logger = logging.getLogger(__name__)

SPACY_AVAILABLE = False
_nlp = None

try:
    import spacy  # type: ignore

    # do not auto-download models here; user can install with `python -m spacy download en_core_web_sm`
    try:
        _nlp = spacy.load("en_core_web_sm")
        SPACY_AVAILABLE = True
    except Exception:
        # model not installed
        logger.info(
            "spaCy installed but model 'en_core_web_sm' not available; ML extraction disabled"
        )
        SPACY_AVAILABLE = False
except Exception:
    SPACY_AVAILABLE = False


def extract_entities_spacy(text: str) -> Dict[str, Any]:
    """Extract a best-effort mapping from free text using spaCy NER.

    Returns a dict with possible keys: name, email, dob, job_title, role, year_start, year_end, contract_type
    """
    out = {}
    if not SPACY_AVAILABLE or _nlp is None:
        return out
    doc = _nlp(text)
    # collect common entities
    names = [ent.text for ent in doc.ents if ent.label_ in ("PERSON",)]
    orgs = [ent.text for ent in doc.ents if ent.label_ in ("ORG", "NORP")]
    dates = [ent.text for ent in doc.ents if ent.label_ in ("DATE",)]
    # heuristics
    if names:
        out["name"] = names[0]
    if orgs:
        out["job_title"] = orgs[0]
    if dates:
        # pick the first plausible date as dob if it's in past and looks like a birth year
        out["dob"] = dates[0]

    # email regex
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    if m:
        out["email"] = m.group(0)

    # year heuristics
    y = re.search(r"(19\d{2}|20\d{2})", text)
    if y:
        out.setdefault("year_start", int(y.group(0)))

    return out


def extract_entities_fallback(text: str) -> Dict[str, Any]:
    """Conservative rule-based fallback for extracting a few fields from text."""
    out: Dict[str, Any] = {}
    # email
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    if m:
        out["email"] = m.group(0)
    # name: look for lines like 'Name: John Doe'
    m = re.search(r"(?im)^\s*name\s*[:\-]\s*(.+)$", text)
    if m:
        out["name"] = m.group(1).strip()
    # dob
    m = re.search(r"(?i)date of birth[:\-]\s*([0-9/\-\.]+)", text)
    if m:
        out["dob"] = m.group(1).strip()
    return out


def extract_entities(text: str) -> Dict[str, Any]:
    """Public API: try spaCy, else fallback."""
    if SPACY_AVAILABLE:
        try:
            return extract_entities_spacy(text)
        except Exception as e:
            logger.exception("spaCy extraction failed: %s", e)
            return extract_entities_fallback(text)
    else:
        return extract_entities_fallback(text)
