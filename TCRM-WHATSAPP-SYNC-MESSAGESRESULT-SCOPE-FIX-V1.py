from pathlib import Path

p = Path("server/services/finalParityV2Service.ts")
s = p.read_text()

old = '''  const contacts=arr(cr),chats=arr(hr),groups=arr(gr),c=await db().getConnection();
  try{await c.beginTransaction();'''
new = '''  const contacts=arr(cr),chats=arr(hr),groups=arr(gr),c=await db().getConnection();
  let messagesResult = { synced: 0, errors: 0 };
  try{await c.beginTransaction();'''

if old not in s:
    raise SystemExit("OUTER_ANCHOR_MISSING")

s = s.replace(old, new, 1)
s = s.replace("   let messagesResult = { synced: 0, errors: 0 };\n", "", 1)
p.write_text(s)

v = p.read_text()
assert "let messagesResult = { synced: 0, errors: 0 };" in v
assert "messages:messagesResult.synced" in v
print("PATCH=TCRM-WHATSAPP-SYNC-MESSAGESRESULT-SCOPE-FIX-V1 APPLY=PASS")
