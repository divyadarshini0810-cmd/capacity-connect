"""Safe, provider-agnostic assistance with an offline retrieval fallback."""
import os
import re
from collections import Counter


def tokenize(value: str):
    return [token for token in re.findall(r"[a-zA-Z]{3,}", value.lower()) if token not in {"with", "from", "that", "this", "have", "your", "into", "about", "what", "when", "where"}]


def rank_chunks(query, chunks):
    query_terms = Counter(tokenize(query))
    ranked = []
    for chunk in chunks:
        corpus = " ".join([chunk.content, chunk.section, " ".join(chunk.keywords or [])])
        terms = Counter(tokenize(corpus))
        score = sum(query_terms[word] * terms[word] for word in query_terms)
        if score:
            ranked.append((score, chunk))
    return [chunk for _, chunk in sorted(ranked, key=lambda item: item[0], reverse=True)[:3]]


def local_answer(question, chunks):
    sources = rank_chunks(question, chunks)
    if not sources:
        return {"answer": "I could not find a trusted, approved source for that question. Please try a more specific question or ask an expert.", "sources": [], "provider": "Local trusted retrieval"}
    facts = " ".join(source.content for source in sources)
    summary = facts[:650].rsplit(" ", 1)[0] + "." if len(facts) > 650 else facts
    return {"answer": summary, "sources": [{"document": item.document.title, "section": item.section} for item in sources], "provider": "Local trusted retrieval"}


def answer_with_provider(question, chunks):
    """Use Gemini only with selected approved sources; otherwise use local retrieval."""
    fallback = local_answer(question, chunks)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or not fallback["sources"]:
        return fallback
    try:
        from google import genai
        context = "\n\n".join(f"[{c.document.title} — {c.section}] {c.content}" for c in rank_chunks(question, chunks))
        client = genai.Client(api_key=api_key)
        model = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
        response = client.models.generate_content(
            model=model,
            contents=(
                "You are Prithvi AI, an Earth-science learning assistant for Capacity Connect. "
                "Answer only from the approved source text below. If the source lacks the answer, say so clearly. "
                "Give a concise, practical explanation and never make employment, promotion, or eligibility decisions.\n\n"
                f"Approved sources:\n{context}\n\nQuestion: {question}"
            ),
        )
        text = (response.text or "").strip()
        if text:
            return {**fallback, "answer": text, "provider": f"Gemini {model} grounded retrieval"}
    except Exception:
        pass
    return fallback
