#!/usr/bin/env python3
"""Патч workflows.json: approval-send (кнопки + job-state) и telegram-router (Правки + сообщения)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF_PATH = ROOT / "workflows.json"

BOT_TOKEN = "8791844060:AAEY6cZt-CmanY3jyw6ui1tqRSHrAN-wUzA"
TG = f"https://api.telegram.org/bot{BOT_TOKEN}"
OWNER_ID = "492912584"
OPENCLAW_HOOK = "http://openclaw-gateway:18789/hooks/agent"
OPENCLAW_AUTH = "Bearer fd5c8a699789ba6beb43c59b5ad6834a3830c6e8e683b429"


def nb(type_name, type_ver, nid, name, pos, params):
    return {
        "parameters": params,
        "type": f"n8n-nodes-base.{type_name}",
        "typeVersion": type_ver,
        "position": pos,
        "id": nid,
        "name": name,
    }


# --- approval-send ---
AFTER_ALBUM_JS = r"""const parse = $('Parse approval body').first().json;
const res = $input.first().json;
const body = res.body !== undefined ? res.body : res;
const result = body.result || [];
const ids = Array.isArray(result) ? result.map((m) => m.message_id) : [];
return [{ json: { ...parse, approve_media_message_ids: ids } }];"""

AFTER_PHOTO_JS = r"""const parse = $('Parse approval body').first().json;
const res = $input.first().json;
const body = res.body !== undefined ? res.body : res;
const mid = body.result && body.result.message_id;
const ids = mid ? [mid] : [];
return [{ json: { ...parse, approve_media_message_ids: ids } }];"""

WRITE_STATE_ALBUM_JS = r"""const fs = require('fs');
const path = require('path');
const parse = $('Parse approval body').first().json;
const album = $('After mediaGroup merge').first().json;
const http = $input.first().json;
const body = http.body !== undefined ? http.body : http;
const textMsgId = body.result && body.result.message_id;
const jobId = parse.job_id;
const blogger = parse.blogger;
const dir = `/home/node/shared/bloggers/${blogger}/jobs/${jobId}`;
if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
const state = {
  job_id: jobId,
  blogger: parse.blogger,
  platform: parse.platform,
  chat_id: String(parse.chat_id),
  approve_media_message_ids: album.approve_media_message_ids || [],
  approve_text_message_id: textMsgId,
  approval_ui_kind: 'album',
  status: 'pending_approval',
  updated_at: new Date().toISOString()
};
fs.writeFileSync(path.join(dir, 'job-state.json'), JSON.stringify(state, null, 2));
return [{ json: { ok: true, job_id: jobId } }];"""

WRITE_STATE_ONE_JS = r"""const fs = require('fs');
const path = require('path');
const parse = $('Parse approval body').first().json;
const photo = $('After sendPhoto merge').first().json;
const http = $input.first().json;
const body = http.body !== undefined ? http.body : http;
const textMsgId = body.result && body.result.message_id;
const jobId = parse.job_id;
const blogger = parse.blogger;
const dir = `/home/node/shared/bloggers/${blogger}/jobs/${jobId}`;
if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
const state = {
  job_id: jobId,
  blogger: parse.blogger,
  platform: parse.platform,
  chat_id: String(parse.chat_id),
  approve_media_message_ids: photo.approve_media_message_ids || [],
  approve_text_message_id: textMsgId,
  approval_ui_kind: 'single_photo',
  status: 'pending_approval',
  updated_at: new Date().toISOString()
};
fs.writeFileSync(path.join(dir, 'job-state.json'), JSON.stringify(state, null, 2));
return [{ json: { ok: true, job_id: jobId } }];"""

WRITE_STATE_NONE_JS = r"""const fs = require('fs');
const path = require('path');
const parse = $('Parse approval body').first().json;
const http = $input.first().json;
const body = http.body !== undefined ? http.body : http;
const textMsgId = body.result && body.result.message_id;
const jobId = parse.job_id;
const blogger = parse.blogger;
const dir = `/home/node/shared/bloggers/${blogger}/jobs/${jobId}`;
if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
const state = {
  job_id: jobId,
  blogger: parse.blogger,
  platform: parse.platform,
  chat_id: String(parse.chat_id),
  approve_media_message_ids: [],
  approve_text_message_id: textMsgId,
  approval_ui_kind: 'text_only',
  status: 'pending_approval',
  updated_at: new Date().toISOString()
};
fs.writeFileSync(path.join(dir, 'job-state.json'), JSON.stringify(state, null, 2));
return [{ json: { ok: true, job_id: jobId } }];"""

KB_ALBUM = (
    "={{ ({ chat_id: $json.chat_id, text: $json.content, reply_markup: { inline_keyboard: [["
    "{ text: '✅ A', callback_data: 'approve_a_' + $json.job_id }, "
    "{ text: '✅ B', callback_data: 'approve_b_' + $json.job_id }, "
    "{ text: '✏️ Правки', callback_data: 'revise_' + $json.job_id }, "
    "{ text: '❌', callback_data: 'reject_' + $json.job_id }]] } }) }}"
)

KB_ONE = (
    "={{ ({ chat_id: $json.chat_id, text: $json.content, reply_markup: { inline_keyboard: [["
    "{ text: '✅ Опубликовать', callback_data: 'approve_' + $json.job_id }, "
    "{ text: '✏️ Правки', callback_data: 'revise_' + $json.job_id }, "
    "{ text: '❌ Отклонить', callback_data: 'reject_' + $json.job_id }]] } }) }}"
)

KB_NONE = (
    "={{ ({ chat_id: $json.chat_id, text: $json.text_no_image, reply_markup: { inline_keyboard: [["
    "{ text: '✅ Опубликовать', callback_data: 'approve_' + $json.job_id }, "
    "{ text: '✏️ Правки', callback_data: 'revise_' + $json.job_id }, "
    "{ text: '❌ Отклонить', callback_data: 'reject_' + $json.job_id }]] } }) }}"
)

PARSE_JS = r"""const raw = $input.first().json;
const data = raw.body !== undefined ? raw.body : raw;

if (data.callback_query) {
  const cb = data.callback_query;
  const cbData = String(cb.data || '');
  let action;
  let jobId;
  if (cbData.startsWith('approve_a_')) {
    action = 'approve_a';
    jobId = cbData.slice('approve_a_'.length);
  } else if (cbData.startsWith('approve_b_')) {
    action = 'approve_b';
    jobId = cbData.slice('approve_b_'.length);
  } else if (cbData.startsWith('approve_')) {
    action = 'approve';
    jobId = cbData.slice('approve_'.length);
  } else if (cbData.startsWith('reject_')) {
    action = 'reject';
    jobId = cbData.slice('reject_'.length);
  } else if (cbData.startsWith('revise_')) {
    action = 'revise';
    jobId = cbData.slice('revise_'.length);
  } else {
    const underscoreIdx = cbData.indexOf('_');
    action = underscoreIdx === -1 ? cbData : cbData.substring(0, underscoreIdx);
    jobId = underscoreIdx === -1 ? '' : cbData.substring(underscoreIdx + 1);
  }
  return [{
    json: {
      event_type: 'callback',
      action,
      job_id: jobId,
      message_id: cb.message.message_id,
      chat_id: cb.from.id,
      callback_chat_id: cb.message.chat.id,
      callback_message_id: cb.message.message_id,
      callback_query_id: cb.id
    }
  }];
}

if (data.message) {
  const m = data.message;
  return [{
    json: {
      event_type: 'message',
      text: m.text || '',
      chat_id: m.chat.id,
      from_id: m.from && m.from.id,
      message_id: m.message_id
    }
  }];
}

return [{ json: { event_type: 'unknown' } }];"""

MSG_SCAN_JS = r"""const fs = require('fs');
const path = require('path');
function walk(dir, acc) {
  if (!fs.existsSync(dir)) return acc;
  for (const n of fs.readdirSync(dir)) {
    const p = path.join(dir, n);
    let st;
    try { st = fs.statSync(p); } catch (e) { continue; }
    if (st.isDirectory()) walk(p, acc);
    else if (n === 'job-state.json') acc.push(p);
  }
  return acc;
}
const files = walk('/home/node/shared/bloggers', []);
const chatId = String($json.chat_id);
const fromId = String($json.from_id || '');
const ownerId = '__OWNER__';
if (fromId && fromId !== ownerId) {
  return [{ json: { ...$json, is_awaiting: false, not_owner: true } }];
}
for (const fp of files) {
  try {
    const st = JSON.parse(fs.readFileSync(fp, 'utf8'));
    if (st.status === 'awaiting_revision' && String(st.chat_id) === chatId) {
      return [{ json: { ...$json, is_awaiting: true, awaiting_job: st, job_state_path: fp } }];
    }
  } catch (e) {}
}
return [{ json: { ...$json, is_awaiting: false } }];""".replace(
    "__OWNER__", OWNER_ID
)

ROUTE_MSG_JS = r"""if (!$json.is_awaiting) {
  return [{ json: { ...$json, route: 'legacy' } }];
}
const t = ($json.text || '').trim();
const first = (t.split(/\s+/)[0] || '');
if (first === '/cancel' || first.indexOf('/cancel@') === 0) {
  return [{ json: { ...$json, route: 'cancel' } }];
}
return [{ json: { ...$json, route: 'revision' } }];"""

REVISE_LOAD_JS = r"""const fs = require('fs');
const jobId = $json.job_id;
const approval = JSON.parse(fs.readFileSync(`/home/node/shared/approvals/${jobId}.json`, 'utf8'));
const blogger = approval.blogger;
const jobDir = `/home/node/shared/bloggers/${blogger}/jobs/${jobId}`;
const statePath = `${jobDir}/job-state.json`;
let state = {};
try { state = JSON.parse(fs.readFileSync(statePath, 'utf8')); } catch (e) {}
const chatId = state.chat_id || String(approval.chat_id || '492912584');
const textMid = state.approve_text_message_id || $json.callback_message_id;
return [{ json: {
  job_id: jobId,
  callback_query_id: $json.callback_query_id,
  callback_chat_id: $json.callback_chat_id,
  chat_id: chatId,
  approve_text_message_id: textMid,
  job_state_path: statePath,
  blogger,
  platform: approval.platform
}}];"""

REVISE_SAVE_JS = r"""const fs = require('fs');
const prev = $('Revise load context').first().json;
const http = $input.first().json;
const body = http.body !== undefined ? http.body : http;
const waitMid = body.result && body.result.message_id;
let state = {};
try { state = JSON.parse(fs.readFileSync(prev.job_state_path, 'utf8')); } catch (e) {}
const jobDir = `/home/node/shared/bloggers/${prev.blogger}/jobs/${prev.job_id}`;
if (!fs.existsSync(jobDir)) fs.mkdirSync(jobDir, { recursive: true });
const next = {
  ...state,
  job_id: prev.job_id,
  blogger: prev.blogger,
  platform: prev.platform,
  chat_id: String(prev.chat_id),
  status: 'awaiting_revision',
  awaiting_revision_message_id: waitMid,
  updated_at: new Date().toISOString()
};
fs.writeFileSync(prev.job_state_path, JSON.stringify(next, null, 2));
return [{ json: { ok: true, job_id: prev.job_id } }];"""

CANCEL_JS = f"""const fs = require('fs');
const token = '{BOT_TOKEN}';
return (async () => {{
  const st = $json.awaiting_job;
  const pathState = $json.job_state_path;
  const jobId = st.job_id;
  const chatId = st.chat_id;
  const jobIdStr = String(jobId);

  if (st.awaiting_revision_message_id) {{
    await fetch(`https://api.telegram.org/bot${{token}}/deleteMessage`, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ chat_id: chatId, message_id: st.awaiting_revision_message_id }}),
    }});
  }}

  const kind = st.approval_ui_kind || 'single_photo';
  let markup;
  if (kind === 'album') {{
    markup = {{ inline_keyboard: [[
      {{ text: '✅ A', callback_data: 'approve_a_' + jobIdStr }},
      {{ text: '✅ B', callback_data: 'approve_b_' + jobIdStr }},
      {{ text: '✏️ Правки', callback_data: 'revise_' + jobIdStr }},
      {{ text: '❌', callback_data: 'reject_' + jobIdStr }},
    ]] }};
  }} else {{
    markup = {{ inline_keyboard: [[
      {{ text: '✅ Опубликовать', callback_data: 'approve_' + jobIdStr }},
      {{ text: '✏️ Правки', callback_data: 'revise_' + jobIdStr }},
      {{ text: '❌ Отклонить', callback_data: 'reject_' + jobIdStr }},
    ]] }};
  }}

  if (st.approve_text_message_id) {{
    await fetch(`https://api.telegram.org/bot${{token}}/editMessageReplyMarkup`, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ chat_id: chatId, message_id: st.approve_text_message_id, reply_markup: markup }}),
    }});
  }}

  const next = {{ ...st, status: 'pending_approval', awaiting_revision_message_id: undefined, updated_at: new Date().toISOString() }};
  fs.writeFileSync(pathState, JSON.stringify(next, null, 2));

  await fetch(`https://api.telegram.org/bot${{token}}/sendMessage`, {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify({{ chat_id: chatId, text: 'Отменено. Кнопки восстановлены.' }}),
  }});

  return [{{ json: {{ ok: true }} }}];
}})();"""

REVISION_PROCESS_JS = f"""const fs = require('fs');
const token = '{BOT_TOKEN}';
const openclawUrl = '{OPENCLAW_HOOK}';
return (async () => {{
  const st = $json.awaiting_job;
  const pathState = $json.job_state_path;
  const text = ($json.text || '').trim();
  const chatId = st.chat_id;
  const jobId = st.job_id;
  const blogger = st.blogger;
  const platform = st.platform;
  const jobDir = `/home/node/shared/bloggers/${{blogger}}/jobs/${{jobId}}`;

  for (const mid of (st.approve_media_message_ids || [])) {{
    await fetch(`https://api.telegram.org/bot${{token}}/deleteMessage`, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ chat_id: chatId, message_id: mid }}),
    }});
  }}
  if (st.approve_text_message_id) {{
    await fetch(`https://api.telegram.org/bot${{token}}/deleteMessage`, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ chat_id: chatId, message_id: st.approve_text_message_id }}),
    }});
  }}
  if (st.awaiting_revision_message_id) {{
    await fetch(`https://api.telegram.org/bot${{token}}/deleteMessage`, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ chat_id: chatId, message_id: st.awaiting_revision_message_id }}),
    }});
  }}

  const revisedAt = new Date().toISOString();
  const approvalPath = `/home/node/shared/approvals/${{jobId}}.json`;
  let approval = {{}};
  try {{ approval = JSON.parse(fs.readFileSync(approvalPath, 'utf8')); }} catch (e) {{}}

  const nextState = {{
    ...st,
    status: 'revision_requested',
    revision_comment: text,
    revised_at: revisedAt,
    awaiting_revision_message_id: undefined,
    updated_at: revisedAt,
  }};
  fs.writeFileSync(pathState, JSON.stringify(nextState, null, 2));

  const draftPath = `${{jobDir}}/draft_approved.md`;
  fs.writeFileSync(draftPath, approval.content || '', 'utf8');

  const directorMsg = `Пользователь запросил правки по job ${{jobId}}.\\nКомментарий: ${{text}}\\nФайл: ${{draftPath}}\\nПередай правки Lens, затем Quill для переработки.`;
  await fetch(openclawUrl, {{
    method: 'POST',
    headers: {{
      'Content-Type': 'application/json',
      Authorization: '{OPENCLAW_AUTH}',
    }},
    body: JSON.stringify({{ message: directorMsg, agentId: 'director', wakeMode: 'now' }}),
  }});

  const ts = revisedAt.replace('T', ' ').slice(0, 19);
  const statusText = `✏️ Правки переданы\\n👤 ${{blogger}} | 📢 ${{platform}} | 🗂 ${{jobId}}\\n💬 ${{text}}\\n🕐 ${{ts}}`;
  await fetch(`https://api.telegram.org/bot${{token}}/sendMessage`, {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify({{ chat_id: chatId, text: statusText }}),
  }});

  return [{{ json: {{ ok: true, job_id: jobId }} }}];
}})();"""


def patch_approval_send(wf):
    nodes_by_name = {n["name"]: n for n in wf["nodes"]}
    nodes_by_name["TG album + buttons msg"]["parameters"]["jsonBody"] = KB_ALBUM
    nodes_by_name["TG one image buttons"]["parameters"]["jsonBody"] = KB_ONE
    nodes_by_name["TG no image msg"]["parameters"]["jsonBody"] = KB_NONE

    new_nodes = [
        nb("code", 2, "a1f2e3d4-5c6b-4a5f-8e9d-0c1b2a3f4e5d", "After mediaGroup merge", [620, -200], {"jsCode": AFTER_ALBUM_JS}),
        nb("code", 2, "b2f3e4d5-6c7b-5a6f-9e0d-1d2c3b4a5f6e", "Write job-state (album)", [1160, -200], {"jsCode": WRITE_STATE_ALBUM_JS}),
        nb("code", 2, "c3f4e5d6-7c8b-6a7f-0e1d-2e3d4c5b6a7f", "After sendPhoto merge", [620, 0], {"jsCode": AFTER_PHOTO_JS}),
        nb("code", 2, "d4f5e6d7-8c9b-7a8f-1e2d-3f4e5d6c8b9a", "Write job-state (one)", [1160, 0], {"jsCode": WRITE_STATE_ONE_JS}),
        nb("code", 2, "e5f6e7d8-9c0b-8a9f-2e3d-4a5f6e7d9c0b1", "Write job-state (none)", [940, 200], {"jsCode": WRITE_STATE_NONE_JS}),
    ]
    names_new = {n["name"] for n in new_nodes}
    wf["nodes"] = [n for n in wf["nodes"] if n["name"] not in names_new] + new_nodes

    c = wf["connections"]
    c["TG sendMediaGroup"] = {"main": [[{"node": "After mediaGroup merge", "type": "main", "index": 0}]]}
    c["After mediaGroup merge"] = {"main": [[{"node": "TG album + buttons msg", "type": "main", "index": 0}]]}
    c["TG album + buttons msg"] = {"main": [[{"node": "Write job-state (album)", "type": "main", "index": 0}]]}

    c["TG sendPhoto"] = {"main": [[{"node": "After sendPhoto merge", "type": "main", "index": 0}]]}
    c["After sendPhoto merge"] = {"main": [[{"node": "TG one image buttons", "type": "main", "index": 0}]]}
    c["TG one image buttons"] = {"main": [[{"node": "Write job-state (one)", "type": "main", "index": 0}]]}

    c["TG no image msg"] = {"main": [[{"node": "Write job-state (none)", "type": "main", "index": 0}]]}


def switch_route():
    return {
        "parameters": {
            "rules": {
                "values": [
                    {
                        "conditions": {
                            "options": {
                                "caseSensitive": True,
                                "leftValue": "",
                                "typeValidation": "strict",
                                "version": 3,
                            },
                            "conditions": [
                                {
                                    "leftValue": "={{ $json.route }}",
                                    "rightValue": "legacy",
                                    "operator": {"type": "string", "operation": "equals"},
                                    "id": "r1",
                                }
                            ],
                            "combinator": "and",
                        },
                        "renameOutput": True,
                        "outputKey": "legacy",
                    },
                    {
                        "conditions": {
                            "options": {
                                "caseSensitive": True,
                                "leftValue": "",
                                "typeValidation": "strict",
                                "version": 3,
                            },
                            "conditions": [
                                {
                                    "leftValue": "={{ $json.route }}",
                                    "rightValue": "cancel",
                                    "operator": {"type": "string", "operation": "equals"},
                                    "id": "r2",
                                }
                            ],
                            "combinator": "and",
                        },
                        "renameOutput": True,
                        "outputKey": "cancel",
                    },
                    {
                        "conditions": {
                            "options": {
                                "caseSensitive": True,
                                "leftValue": "",
                                "typeValidation": "strict",
                                "version": 3,
                            },
                            "conditions": [
                                {
                                    "leftValue": "={{ $json.route }}",
                                    "rightValue": "revision",
                                    "operator": {"type": "string", "operation": "equals"},
                                    "id": "r3",
                                }
                            ],
                            "combinator": "and",
                        },
                        "renameOutput": True,
                        "outputKey": "revision",
                    },
                ]
            },
            "options": {},
        },
        "type": "n8n-nodes-base.switch",
        "typeVersion": 3.4,
        "position": [1040, 192],
        "id": "f1000009-0000-4000-8000-000000000009",
        "name": "Switch message route",
    }


def patch_telegram_router(wf):
    for n in wf["nodes"]:
        if n["name"] == "Code in JavaScript":
            n["parameters"]["jsCode"] = PARSE_JS

    wf["nodes"] = [n for n in wf["nodes"] if n["name"] not in ("HTTP Request2",)]

    extra = [
        nb("code", 2, "f1000001-0000-4000-8000-000000000001", "Revise load context", [1100, -176], {"jsCode": REVISE_LOAD_JS}),
        nb(
            "httpRequest",
            4.4,
            "f1000002-0000-4000-8000-000000000002",
            "TG answerCb revise",
            [1280, -176],
            {
                "method": "POST",
                "url": f"{TG}/answerCallbackQuery",
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": '={{ ({ callback_query_id: $json.callback_query_id, text: "✏️" }) }}',
                "options": {},
            },
        ),
        nb(
            "httpRequest",
            4.4,
            "f1000003-0000-4000-8000-000000000003",
            "TG editMarkup revise",
            [1460, -176],
            {
                "method": "POST",
                "url": f"{TG}/editMessageReplyMarkup",
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ ({ chat_id: $json.callback_chat_id, message_id: $json.approve_text_message_id, reply_markup: {} }) }}",
                "options": {},
            },
        ),
        nb(
            "httpRequest",
            4.4,
            "f1000004-0000-4000-8000-000000000004",
            "TG sendInvite revise",
            [1640, -176],
            {
                "method": "POST",
                "url": f"{TG}/sendMessage",
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": (
                    "={{ ({ chat_id: $json.chat_id, text: "
                    "'✏️ Жду правки по посту ' + $json.job_id + ' (' + $json.blogger + ' | ' + $json.platform + ').\\n' + "
                    "'Следующим сообщением напиши что изменить — передам Quill через Director.' }) }}"
                ),
                "options": {},
            },
        ),
        nb("code", 2, "f1000005-0000-4000-8000-000000000005", "Revise save job-state", [1820, -176], {"jsCode": REVISE_SAVE_JS}),
        nb("code", 2, "f100000a-0000-4000-8000-00000000000a", "Msg scan awaiting", [720, 192], {"jsCode": MSG_SCAN_JS}),
        nb("code", 2, "f100000b-0000-4000-8000-00000000000b", "Route message kind", [880, 192], {"jsCode": ROUTE_MSG_JS}),
        switch_route(),
        nb("code", 2, "f100000c-0000-4000-8000-00000000000c", "Cancel revision flow", [1220, 96], {"jsCode": CANCEL_JS}),
        nb("code", 2, "f100000d-0000-4000-8000-00000000000d", "Revision message flow", [1220, 288], {"jsCode": REVISION_PROCESS_JS}),
    ]
    wf["nodes"].extend(extra)

    c = wf["connections"]

    c["If1"] = {
        "main": [
            [{"node": "Switch1", "type": "main", "index": 0}],
            [{"node": "Msg scan awaiting", "type": "main", "index": 0}],
        ]
    }

    c["Msg scan awaiting"] = {"main": [[{"node": "Route message kind", "type": "main", "index": 0}]]}
    c["Route message kind"] = {"main": [[{"node": "Switch message route", "type": "main", "index": 0}]]}

    c["Switch message route"] = {
        "main": [
            [{"node": "Code in JavaScript2", "type": "main", "index": 0}],
            [{"node": "Cancel revision flow", "type": "main", "index": 0}],
            [{"node": "Revision message flow", "type": "main", "index": 0}],
        ]
    }

    sw = c["Switch1"]["main"]
    sw[3] = [{"node": "Revise load context", "type": "main", "index": 0}]

    c["Revise load context"] = {"main": [[{"node": "TG answerCb revise", "type": "main", "index": 0}]]}
    c["TG answerCb revise"] = {"main": [[{"node": "TG editMarkup revise", "type": "main", "index": 0}]]}
    c["TG editMarkup revise"] = {"main": [[{"node": "TG sendInvite revise", "type": "main", "index": 0}]]}
    c["TG sendInvite revise"] = {"main": [[{"node": "Revise save job-state", "type": "main", "index": 0}]]}


def main():
    with open(WF_PATH, encoding="utf-8") as f:
        data = json.load(f)

    for wf in data:
        if wf.get("name") == "approval-send":
            patch_approval_send(wf)
        elif wf.get("name") == "telegram-router":
            patch_telegram_router(wf)

    with open(WF_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("OK:", WF_PATH)


if __name__ == "__main__":
    main()
