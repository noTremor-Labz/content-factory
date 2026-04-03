#!/usr/bin/env python3
"""
Обновляет workflows.json:
1) Все URL api.telegram.org/bot... → выражение с $env.TELEGRAM_APPROVAL_BOT_TOKEN || $env.TELEGRAM_BOT_TOKEN
2) Cancel / Revision: отдельные HTTP Request вместо async fetch в Code
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF_PATH = ROOT / "workflows.json"

TG_URL = (
    "={{ 'https://api.telegram.org/bot' + ($env.TELEGRAM_APPROVAL_BOT_TOKEN || $env.TELEGRAM_BOT_TOKEN) + '/"
)


def tg(method: str) -> str:
    return TG_URL + method + "' }}"


def http_node(nid: str, name: str, pos: list, method: str, path: str, json_body_expr: str):
    return {
        "parameters": {
            "method": method,
            "url": tg(path),
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": json_body_expr,
            "options": {},
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.4,
        "position": pos,
        "id": nid,
        "name": name,
    }


def code_node(nid: str, name: str, pos: list, js: str, **extra):
    p = {"jsCode": js, **extra}
    return {
        "parameters": p,
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": pos,
        "id": nid,
        "name": name,
    }


CANCEL_PREPARE_JS = r"""const st = $json.awaiting_job;
const pathState = $json.job_state_path;
const jobIdStr = String(st.job_id);
const kind = st.approval_ui_kind || 'single_photo';
let markup;
if (kind === 'album') {
  markup = { inline_keyboard: [[
    { text: '✅ A', callback_data: 'approve_a_' + jobIdStr },
    { text: '✅ B', callback_data: 'approve_b_' + jobIdStr },
    { text: '✏️ Правки', callback_data: 'revise_' + jobIdStr },
    { text: '❌', callback_data: 'reject_' + jobIdStr },
  ]] };
} else {
  markup = { inline_keyboard: [[
    { text: '✅ Опубликовать', callback_data: 'approve_' + jobIdStr },
    { text: '✏️ Правки', callback_data: 'revise_' + jobIdStr },
    { text: '❌ Отклонить', callback_data: 'reject_' + jobIdStr },
  ]] };
}
const nextState = { ...st, status: 'pending_approval', awaiting_revision_message_id: undefined, updated_at: new Date().toISOString() };
return [{ json: {
  chat_id: st.chat_id,
  del_wait_mid: st.awaiting_revision_message_id || null,
  text_mid: st.approve_text_message_id,
  markup,
  path_state: pathState,
  next_state_json: JSON.stringify(nextState),
}}];"""

CANCEL_WRITE_JS = r"""const fs = require('fs');
const p = $('Cancel prepare').first().json;
fs.writeFileSync(p.path_state, p.next_state_json);
return [{ json: { chat_id: p.chat_id } }];"""

REVISION_EXPAND_JS = r"""const st = $json.awaiting_job;
const text = ($json.text || '').trim();
const pathState = $json.job_state_path;
const chatId = st.chat_id;
const ids = [];
for (const m of (st.approve_media_message_ids || [])) ids.push(m);
if (st.approve_text_message_id) ids.push(st.approve_text_message_id);
if (st.awaiting_revision_message_id) ids.push(st.awaiting_revision_message_id);
if (ids.length === 0) {
  return [{ json: {
    skip_delete: true,
    _revision_text: text,
    _path_state: pathState,
    _st: st,
  }}];
}
return ids.map((message_id) => ({
  json: {
    chat_id: chatId,
    message_id,
    _revision_text: text,
    _path_state: pathState,
    _st: st,
  },
}));"""

REVISION_FINALIZE_JS = r"""const fs = require('fs');
const first = $('Revision expand deletes').first().json;
const text = first._revision_text;
const pathState = first._path_state;
const st = first._st;
if (!st || !text) {
  return [{ json: { error: 'missing context' } }];
}
const revisedAt = new Date().toISOString();
const jobId = st.job_id;
const blogger = st.blogger;
const platform = st.platform;
const jobDir = `/home/node/shared/bloggers/${blogger}/jobs/${jobId}`;
const approvalPath = `/home/node/shared/approvals/${jobId}.json`;
let approval = {};
try { approval = JSON.parse(fs.readFileSync(approvalPath, 'utf8')); } catch (e) {}
const nextState = {
  ...st,
  status: 'revision_requested',
  revision_comment: text,
  revised_at: revisedAt,
  awaiting_revision_message_id: undefined,
  updated_at: revisedAt,
};
fs.writeFileSync(pathState, JSON.stringify(nextState, null, 2));
const draftPath = `${jobDir}/draft_approved.md`;
fs.writeFileSync(draftPath, approval.content || '', 'utf8');
const directorMsg = `Пользователь запросил правки по job ${jobId}.\nКомментарий: ${text}\nФайл: ${draftPath}\nПередай правки Lens, затем Quill для переработки.`;
const ts = revisedAt.replace('T', ' ').slice(0, 19);
const statusText = `✏️ Правки переданы\n👤 ${blogger} | 📢 ${platform} | 🗂 ${jobId}\n💬 ${text}\n🕐 ${ts}`;
return [{ json: {
  chat_id: st.chat_id,
  director_msg: directorMsg,
  status_text: statusText,
}}];"""


def patch_all_telegram_urls(data):
    """Заменить захардкоженные bot<TOKEN> в url узлов httpRequest."""
    pat = re.compile(r"https://api\.telegram\.org/bot[^/]+/([A-Za-z]+)")
    for wf in data:
        for node in wf.get("nodes", []):
            if node.get("type") != "n8n-nodes-base.httpRequest":
                continue
            url = node.get("parameters", {}).get("url")
            if not url or not isinstance(url, str):
                continue
            m = pat.match(url)
            if m:
                method = m.group(1)
                node["parameters"]["url"] = tg(method)


def rebuild_telegram_router(wf):
    nodes = wf["nodes"]
    if any(n.get("name") == "Cancel prepare" for n in nodes):
        return
    # Удалить старые Cancel / Revision Code
    drop = {"Cancel revision flow", "Revision message flow"}
    nodes[:] = [n for n in nodes if n["name"] not in drop]

    new = [
        code_node(
            "ca111111-1111-4111-8111-111111111101",
            "Cancel prepare",
            [1180, 96],
            CANCEL_PREPARE_JS,
        ),
        {
            "parameters": {
                "conditions": {
                    "options": {
                        "caseSensitive": True,
                        "leftValue": "",
                        "typeValidation": "strict",
                        "version": 3,
                    },
                    "conditions": [
                        {
                            "id": "cif-del",
                            "leftValue": "={{ $json.del_wait_mid }}",
                            "rightValue": "",
                            "operator": {
                                "type": "string",
                                "operation": "notEmpty",
                                "singleValue": True,
                            },
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.3,
            "position": [1320, 96],
            "id": "ca111111-1111-4111-8111-111111111102",
            "name": "If cancel has wait msg",
        },
        http_node(
            "ca111111-1111-4111-8111-111111111103",
            "TG cancel delete wait",
            [1500, 32],
            "POST",
            "deleteMessage",
            "={{ ({ chat_id: $json.chat_id, message_id: $json.del_wait_mid }) }}",
        ),
        http_node(
            "ca111111-1111-4111-8111-111111111104",
            "TG cancel edit markup",
            [1680, 96],
            "POST",
            "editMessageReplyMarkup",
            "={{ ({ chat_id: $('Cancel prepare').item.json.chat_id, message_id: $('Cancel prepare').item.json.text_mid, reply_markup: $('Cancel prepare').item.json.markup }) }}",
        ),
        http_node(
            "ca111111-1111-4111-8111-111111111105",
            "TG cancel edit markup (no del)",
            [1680, 160],
            "POST",
            "editMessageReplyMarkup",
            "={{ ({ chat_id: $('Cancel prepare').item.json.chat_id, message_id: $('Cancel prepare').item.json.text_mid, reply_markup: $('Cancel prepare').item.json.markup }) }}",
        ),
        code_node(
            "ca111111-1111-4111-8111-111111111106",
            "Cancel write state",
            [1860, 96],
            CANCEL_WRITE_JS,
        ),
        http_node(
            "ca111111-1111-4111-8111-111111111107",
            "TG cancel ack",
            [2040, 96],
            "POST",
            "sendMessage",
            "={{ ({ chat_id: $json.chat_id, text: 'Отменено. Кнопки восстановлены.' }) }}",
        ),
        code_node(
            "rv222222-2222-4222-8222-222222222201",
            "Revision expand deletes",
            [1180, 288],
            REVISION_EXPAND_JS,
        ),
        {
            "parameters": {
                "conditions": {
                    "options": {
                        "caseSensitive": True,
                        "leftValue": "",
                        "typeValidation": "strict",
                        "version": 3,
                    },
                    "conditions": [
                        {
                            "id": "rv-if-skip",
                            "leftValue": "={{ $json.skip_delete }}",
                            "rightValue": True,
                            "operator": {
                                "type": "boolean",
                                "operation": "true",
                                "singleValue": True,
                            },
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.3,
            "position": [1320, 288],
            "id": "rv222222-2222-4222-8222-222222222210",
            "name": "If revision skip delete",
        },
        http_node(
            "rv222222-2222-4222-8222-222222222202",
            "TG revision delete",
            [1500, 360],
            "POST",
            "deleteMessage",
            "={{ ({ chat_id: $json.chat_id, message_id: $json.message_id }) }}",
        ),
        code_node(
            "rv222222-2222-4222-8222-222222222203",
            "Revision finalize",
            [1680, 288],
            REVISION_FINALIZE_JS,
            mode="runOnceForAllItems",
        ),
        {
            "parameters": {
                "method": "POST",
                "url": "={{ $env.OPENCLAW_GATEWAY_INTERNAL_URL || 'http://openclaw-gateway:18789' }}/hooks/agent",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {
                            "name": "Authorization",
                            "value": "={{ 'Bearer ' + ($env.OPENCLAW_GATEWAY_TOKEN || $env.OPENCLAW_HOOK_TOKEN || $env.OPENCLAW_HOOKS_TOKEN || '') }}",
                        }
                    ]
                },
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ ({ message: $json.director_msg, agentId: 'director', wakeMode: 'now' }) }}",
                "options": {},
            },
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.4,
            "position": [1860, 288],
            "id": "rv222222-2222-4222-8222-222222222204",
            "name": "HTTP Director revision",
        },
        http_node(
            "rv222222-2222-4222-8222-222222222205",
            "TG revision status",
            [2040, 288],
            "POST",
            "sendMessage",
            "={{ ({ chat_id: $json.chat_id, text: $json.status_text }) }}",
        ),
    ]
    nodes.extend(new)

    c = wf["connections"]

    c["Switch message route"]["main"][1] = [{"node": "Cancel prepare", "type": "main", "index": 0}]
    c["Switch message route"]["main"][2] = [{"node": "Revision expand deletes", "type": "main", "index": 0}]

    c["Cancel prepare"] = {"main": [[{"node": "If cancel has wait msg", "type": "main", "index": 0}]]}
    c["If cancel has wait msg"] = {
        "main": [
            [{"node": "TG cancel delete wait", "type": "main", "index": 0}],
            [{"node": "TG cancel edit markup (no del)", "type": "main", "index": 0}],
        ]
    }
    c["TG cancel delete wait"] = {"main": [[{"node": "TG cancel edit markup", "type": "main", "index": 0}]]}
    c["TG cancel edit markup"] = {"main": [[{"node": "Cancel write state", "type": "main", "index": 0}]]}
    c["TG cancel edit markup (no del)"] = {"main": [[{"node": "Cancel write state", "type": "main", "index": 0}]]}
    c["Cancel write state"] = {"main": [[{"node": "TG cancel ack", "type": "main", "index": 0}]]}

    c["Revision expand deletes"] = {"main": [[{"node": "If revision skip delete", "type": "main", "index": 0}]]}
    c["If revision skip delete"] = {
        "main": [
            [{"node": "Revision finalize", "type": "main", "index": 0}],
            [{"node": "TG revision delete", "type": "main", "index": 0}],
        ]
    }
    c["TG revision delete"] = {"main": [[{"node": "Revision finalize", "type": "main", "index": 0}]]}
    c["Revision finalize"] = {"main": [[{"node": "HTTP Director revision", "type": "main", "index": 0}]]}
    c["HTTP Director revision"] = {"main": [[{"node": "TG revision status", "type": "main", "index": 0}]]}


def main():
    with open(WF_PATH, encoding="utf-8") as f:
        data = json.load(f)

    patch_all_telegram_urls(data)

    for wf in data:
        if wf.get("name") == "telegram-router":
            rebuild_telegram_router(wf)

    with open(WF_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("OK", WF_PATH)


if __name__ == "__main__":
    main()
