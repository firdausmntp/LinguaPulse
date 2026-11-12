"""Post-submission reviews use the frozen attempt, never today's answer keys."""
import json
from .database import get_connection


def build_section_reviews(bank, answers):
    groups = {'listening': bank.get('listening', {}).get('questions', []),
              'grammar': bank.get('grammar_mc', []),
              'reading': bank.get('reading', {}).get('questions', [])}
    reviews = {}
    for section, questions in groups.items():
        items = []
        for q in questions:
            options = q.get('options', [])
            answer = str(q.get('answer', ''))
            if not answer.isdigit() or int(answer) >= len(options):
                continue
            selected = answers.get(q['id'])
            unanswered = selected is None or str(selected).strip() == ''
            selected_index = int(str(selected)) if str(selected).isdigit() and int(str(selected)) < len(options) else None
            status = 'unanswered' if unanswered else 'correct' if str(selected) == answer else 'incorrect'
            passage = q.get('passage') or ''
            if section == 'reading' and not passage:
                shared = {item.get('passage') for item in questions if item.get('title') == q.get('title') and item.get('passage')}
                passage = shared.pop() if len(shared) == 1 else ''
            items.append({'id': q['id'], 'title': q.get('title', ''), 'prompt': q['prompt'],
                          'options': options, 'correct_answer': int(answer), 'selected_answer': selected_index,
                          'status': status, 'explanation': q.get('explanation', ''),
                          'passage': passage if section == 'reading' else '',
                          'audio_url': q.get('audio_url', '') if section == 'listening' else ''})
        reviews[section] = items
    return reviews


def enrich_saved_review(data, session_id, user):
    """Add reviews to older saved results only when their original snapshot survives."""
    result = data.get('toefl_practice_result', {})
    if result.get('section_reviews'):
        return data
    with get_connection() as conn:
        row = conn.execute("""SELECT a.bank_json, s.answers_json, s.submitted_at
            FROM exam_attempts a JOIN exam_submissions s ON s.session_id = 'SES-' || a.attempt_id
            WHERE a.user_id=? AND s.participant_code=? AND s.session_id=?""",
            (user['user_id'], user['participant_code'], session_id)).fetchone()
    if row:
        result['section_reviews'] = build_section_reviews(json.loads(row['bank_json']), json.loads(row['answers_json']))
        data.setdefault('submitted_at', row['submitted_at'])
    return data
