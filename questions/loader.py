"""Read the active question bank from MySQL."""
from backend.database import get_connection
from contextlib import nullcontext


def get_structured_questions(include_inactive=False, question_ids=None, conn=None):
    with (get_connection() if conn is None else nullcontext(conn)) as conn:
        conditions = [] if include_inactive else ['is_active = 1']
        params = []
        if question_ids is not None:
            conditions.append('question_id IN (' + ','.join(['%s'] * len(question_ids)) + ')' if question_ids else '1=0')
            params = question_ids
        sql = 'SELECT * FROM questions' + (' WHERE ' + ' AND '.join(conditions) if conditions else '') + ' ORDER BY question_id'
        rows = [dict(row) for row in conn.execute(sql, params)]
        row_ids = [row['question_id'] for row in rows]
        opt_rows = conn.execute('SELECT question_id, option_text FROM question_options WHERE question_id IN ('
                               + ','.join(['%s'] * len(row_ids)) + ') ORDER BY question_id, option_index', row_ids).fetchall() if row_ids else []
    if question_ids is not None:
        order = {qid: i for i, qid in enumerate(question_ids)}
        rows.sort(key=lambda row: order[row['question_id']])
    opts_by_qid = {}
    for r in opt_rows:
        opts_by_qid.setdefault(r['question_id'], []).append(r['option_text'])
    grammar_mc, rewrites, reading, listening, writing, all_items = [], [], [], [], [], []
    for row in rows:
        item = {name: row.get(name) or '' for name in (
            'question_id', 'section', 'question_type', 'title', 'passage', 'prompt',
            'correct_answer', 'explanation', 'sample_ai_reference', 'audio_url')}
        item.update({
            'id': row['question_id'], 'options': opts_by_qid.get(row['question_id'], []),
            'answer': int(row['correct_answer']) if str(row['correct_answer']).isdigit() else row['correct_answer'],
            'is_active': int(row['is_active']),
        })
        all_items.append(item)
        if not row['is_active']:
            continue
        if row['section'] == 'listening':
            listening.append(item)
        elif row['section'] == 'reading':
            reading.append(item)
        elif row['section'] == 'writing':
            writing.append(item)
        elif row['question_type'] == 'rewrite':
            rewrites.append(item)
        else:
            grammar_mc.append(item)
    # Legacy rows sometimes store a shared Reading passage on only one question.
    passages = {}
    for item in reading:
        passage = item['passage'].strip()
        if passage:
            passages.setdefault(item['title'], set()).add(passage)
    for item in reading:
        choices = passages.get(item['title'], set())
        if not item['passage'].strip() and item['title'] and len(choices) == 1:
            item['passage'] = next(iter(choices))
    selected_writing = writing[0] if writing else {
        'id': 'W-NONE', 'title': 'Writing tambahan', 'prompt': 'Belum ada tugas Writing aktif.',
        'sample_ai_reference': '', 'options': []}
    return {
        'listening': {'questions': listening}, 'grammar_mc': grammar_mc, 'grammar_rewrite': rewrites,
        'reading': {'questions': reading, 'title': reading[0]['title'] if reading else 'Reading',
                    'passage': reading[0]['passage'] if reading else ''},
        'writing': selected_writing, 'writing_tasks': writing, 'all_questions': all_items,
    }


def _public_question(item, condition=None):
    section = item.get('section') or ''
    q = {
        'id': item.get('id') or item.get('question_id') or '',
        'section': section,
        'question_type': item.get('question_type') or '',
        'title': item.get('title') or '',
        'passage': (item.get('passage') or '') if section == 'reading' else '',
        'prompt': item.get('prompt') or '',
        'options': list(item.get('options') or []),
        'audio_url': (item.get('audio_url') or '') if section == 'listening' else '',
    }
    if section == 'writing' and condition in {'COPY_TYPING', 'AI_PARAPHRASE'}:
        q['sample_ai_reference'] = item.get('sample_ai_reference') or ''
    return q


def public_bank(bank, condition=None, include_list=False, transcripts=None):
    listening = [_public_question(item, condition) for item in bank.get('listening', {}).get('questions', [])]
    if transcripts:
        for item in listening:
            item['transcript'] = transcripts[item['audio_url']]
    reading = [_public_question(item, condition) for item in bank.get('reading', {}).get('questions', [])]
    grammar_mc = [_public_question(item, condition) for item in bank.get('grammar_mc', [])]
    grammar_rewrite = [_public_question(item, condition) for item in bank.get('grammar_rewrite', [])]
    writing_tasks = [_public_question(item, condition) for item in bank.get('writing_tasks', [])]
    writing_raw = bank.get('writing') or {}
    writing = _public_question({**writing_raw, 'section': 'writing'}, condition) if writing_raw and writing_raw.get('id') != 'W-NONE' else None
    output = {
        'listening': {'questions': listening},
        'grammar_mc': grammar_mc,
        'grammar_rewrite': grammar_rewrite,
        'reading': {'questions': reading, 'title': reading[0]['title'] if reading else 'Reading',
                    'passage': reading[0]['passage'] if reading else ''},
        'writing': writing,
        'writing_tasks': writing_tasks,
    }
    if bank.get('package'):
        output['package'] = dict(bank['package'])
    if bank.get('schedule'):
        output['schedule'] = dict(bank['schedule'])
    if include_list:
        output['all_questions'] = [{
            'question_id': item.get('question_id') or item.get('id') or '',
            'id': item.get('id') or item.get('question_id') or '',
            'section': item.get('section') or '',
            'question_type': item.get('question_type') or '',
            'title': item.get('title') or '',
            'prompt': item.get('prompt') or '',
            'is_active': int(item.get('is_active', 1)),
            'audio_url': item.get('audio_url') or '',
        } for item in bank.get('all_questions', [])]
    return output
