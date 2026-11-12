import json
import os
import urllib.request
from typing import Dict, Any

AI_API_URL = os.environ.get("TOEFL_AI_API_URL", "https://api.openai.com/v1/chat/completions")
AI_API_KEY = os.environ.get("TOEFL_AI_API_KEY", "")
AI_MODEL_NAME = os.environ.get("TOEFL_AI_MODEL", "gpt-4o-mini")


def generate_ai_tutor_explanation(submission_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Menghubungkan hasil jawaban TOEFL peserta ke API AI (LLM Bridge) untuk memberikan
    penjelasan singkat pasca-ujian (Grammar Breakdown, Sentence Rewrite Review, & Essay Feedback).
    Dilengkapi Fallback Pedagogis Lokal apabila API Key belum diisi.
    """
    grammar_fb = submission_data.get("grammar_feedback", [])
    essay_text = (submission_data.get("essay_text") or "").strip()
    rewrite_answers = submission_data.get("rewrite_answers", {})
    accuracy = submission_data.get("accuracy_percent", 0)

    # Jika pengguna sudah mengisi TOEFL_AI_API_KEY di environment, panggil API LLM eksternal
    if AI_API_KEY:
        try:
            prompt_text = (
                f"Berikan evaluasi singkat Bahasa Indonesia untuk peserta latihan TOEFL EPT (Ketepatan pilihan ganda: {accuracy}%, bukan skor TOEFL resmi).\n"
                f"Jawaban Rewrite Grammar: {json.dumps(rewrite_answers, ensure_ascii=False)}\n"
                f"Esai Writing ({len(essay_text.split())} kata): {essay_text[:600]}\n"
                "Berikan 3 poin singkat: (1) Evaluasi Grammar & Rewrite, (2) Evaluasi Struktur & Kosakata Esai, (3) Tips Cepat Menaikkan Skor."
            )
            req_body = json.dumps({
                "model": AI_MODEL_NAME,
                "messages": [
                    {"role": "system", "content": "Kamu adalah instruktur persiapan TOEFL EPT yang ringkas, suportif, dan akurat."},
                    {"role": "user", "content": prompt_text}
                ],
                "temperature": 0.4,
                "max_tokens": 350
            }).encode("utf-8")

            req = urllib.request.Request(
                AI_API_URL,
                data=req_body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {AI_API_KEY}"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                ai_reply = res_json["choices"][0]["message"]["content"]
                return {
                    "source": f"External AI API ({AI_MODEL_NAME})",
                    "summary": ai_reply,
                }
        except Exception as exc:
            pass

    # Built-in Pedagogical AI Coach (Berjalan instan tanpa perlu API key berbayar)
    wrong_items = [item for item in grammar_fb if not item.get("is_correct")]
    words = essay_text.split()
    wc = len(words)
    unique_words = len(set(w.lower().strip(".,!?;:\"'()") for w in words)) if wc > 0 else 0
    lexical_diversity = round((unique_words / wc) * 100, 1) if wc > 0 else 0.0

    has_transitions = any(
        t in essay_text.lower()
        for t in ("first", "second", "furthermore", "moreover", "however", "therefore", "consequently", "in conclusion")
    )

    grammar_note = (
        "Seluruh soal pilihan ganda Structure berhasil dijawab dengan tepat. Pertahankan penguasaan pola inversi dan klausa subordinatif."
        if not wrong_items
        else f"Terdapat {len(wrong_items)} topik grammar yang perlu diperkuat: "
             + ", ".join(item["title"] for item in wrong_items)
             + ". Perhatikan kembali kesesuaian subjek-predikat dan struktur paralel."
    )

    essay_note = (
        f"Esai terdiri atas {wc} kata dengan keragaman kosakata (lexical diversity) sebesar {lexical_diversity}%. "
        + (
            "Penggunaan penanda wacana akademik (discourse markers seperti 'First', 'Therefore', 'However') sudah baik dan menjaga kohesi antar-argumen."
            if has_transitions
            else "Disarankan menambahkan kata penghubung akademik ('Furthermore', 'However', 'Consequently') agar transisi antar-paragraf lebih mengalir."
        )
    )

    return {
        "source": "Built-in AI Pedagogical Engine (Siap di-bridge ke OpenAI/Gemini via TOEFL_AI_API_KEY)",
        "grammar_review": grammar_note,
        "essay_review": essay_note,
        "actionable_tip": (
            "Tulis esai 80 hingga 150 kata dengan pendapat utama, dua alasan pendukung, dan kesimpulan. Tinjau kejelasan argumen serta hubungan antarparagraf."
        ),
    }

