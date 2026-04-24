from __future__ import annotations

import asyncio
import json
import re
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.llm import LLMResponder
from backend.app.models.audit_log import AuditLog
from backend.app.models.compliance_record import ComplianceRecord
from backend.app.models.support_ticket import SupportTicket
from backend.app.models.transaction import Transaction

# ── LLM intent-parsing prompt ─────────────────────────────────────────────────

_PARSE_SYSTEM = """You are an ops data parser. Given a user message, return ONLY valid JSON.

Supported intents:

ADD_TRANSACTION        data: {amount, merchant, location, category, notes}
DELETE_TRANSACTION     data: {merchant, amount}            — at least one field
UPDATE_TRANSACTION     data: {merchant, amount, field, new_value}
                             field: category|location|notes|amount|merchant|flagged|risk_score

ADD_SUPPORT_TICKET     data: {description, category, priority, customer_identifier}
                             category: refund_delay|login_issue|payment_failure|duplicate_charge|
                                       verification_problem|account_locked|transfer_issue|general
DELETE_SUPPORT_TICKET  data: {keywords}
UPDATE_SUPPORT_TICKET  data: {keywords, field, new_value}
                             field: status|priority|description|category
                             status values: open|in_review|resolved

ADD_COMPLIANCE_RECORD     data: {description, record_type, policy_flag, severity}
                                record_type: expense_policy|missing_documentation|manual_override|
                                             unusual_approval|reimbursement|general
DELETE_COMPLIANCE_RECORD  data: {keywords}
UPDATE_COMPLIANCE_RECORD  data: {keywords, field, new_value}
                                field: status|severity|description|recommendation
                                status values: pending|approved|rejected

FLAG_TRANSACTION    data: {merchant, amount}
UNFLAG_TRANSACTION  data: {merchant, amount}
EXPLAIN_TRANSACTION data: {merchant, amount, temporal}   temporal=true if "recent/last/latest"
QUERY_DATA          data: {domain, wants_list, wants_recent, wants_flagged, filter_status}
                         domain: transactions|support|compliance|all
RUN_ANALYSIS        data: {}
UNKNOWN             data: {}

Return exactly: {"intent": "INTENT_NAME", "data": {...}}"""


class OpsProcessor:
    def __init__(self) -> None:
        self.llm = LLMResponder()

    # ── Public entry point ────────────────────────────────────────────────────

    async def process(
        self,
        text: str,
        db: AsyncSession,
        history: list[dict] | None = None,
    ) -> str | None:
        parsed = await asyncio.to_thread(self._parse_intent, text, history)
        intent: str = parsed.get("intent", "UNKNOWN")
        data: dict = parsed.get("data", {})

        if intent == "UNKNOWN":
            return None

        try:
            return await self._dispatch(intent, data, text, db, history)
        except Exception as exc:  # noqa: BLE001
            return f"Something went wrong: {str(exc)[:120]}"

    # ── Intent parsing via LLM (with keyword fallback) ────────────────────────

    def _parse_intent(self, text: str, history: list[dict] | None) -> dict:
        # Fast-path: clearly conversational — skip LLM entirely
        t = text.lower().strip()
        conversational = {"hello", "hi", "hey", "thanks", "thank you", "ok", "okay", "yes", "no", "bye"}
        if t in conversational or (len(t.split()) <= 2 and not re.search(r"\d", t)):
            return {"intent": "UNKNOWN", "data": {}}

        if self.llm.enabled:
            context = ""
            if history:
                last = history[-4:]  # last 2 turns for context
                context = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in last)
                context = f"\nRecent conversation:\n{context}\n"

            prompt = (
                f"{context}\nMessage: \"{text}\"\n\n"
                "Return JSON only — no explanation, no markdown."
            )
            try:
                raw = self.llm.generate_reply(prompt, [{"role": "system", "content": _PARSE_SYSTEM}])
                m = re.search(r"\{.*\}", raw, re.DOTALL)
                if m:
                    return json.loads(m.group())
            except Exception:  # noqa: BLE001
                pass

        # Fallback keyword classifier
        return self._keyword_classify(t)

    def _keyword_classify(self, t: str) -> dict:
        has_num = bool(re.search(r"\d", t))

        # DELETE
        del_kws = ["delete ", "remove ", "erase ", "get rid of", "drop ", "wipe ", "cancel "]
        if any(k in t for k in del_kws):
            if "ticket" in t or "support" in t or "issue" in t:
                return {"intent": "DELETE_SUPPORT_TICKET", "data": {"keywords": t}}
            if "compliance" in t or "record" in t or "policy" in t:
                return {"intent": "DELETE_COMPLIANCE_RECORD", "data": {"keywords": t}}
            return {"intent": "DELETE_TRANSACTION", "data": {"merchant": t, "amount": None}}

        # UPDATE
        upd_kws = ["update ", "change ", "mark ", "set ", "close ", "resolve ", "approve ", "reject ", "edit "]
        if any(k in t for k in upd_kws):
            if "ticket" in t or "support" in t or "issue" in t:
                return {"intent": "UPDATE_SUPPORT_TICKET", "data": {"keywords": t, "field": "status", "new_value": "resolved" if "resolv" in t or "clos" in t else "in_review"}}
            if "compliance" in t or "record" in t:
                val = "approved" if "approv" in t else ("rejected" if "reject" in t else "pending")
                return {"intent": "UPDATE_COMPLIANCE_RECORD", "data": {"keywords": t, "field": "status", "new_value": val}}
            return {"intent": "UPDATE_TRANSACTION", "data": {"merchant": t, "field": "notes", "new_value": t}}

        # UNFLAG
        if any(k in t for k in ["unflag", "clear flag", "remove flag", "unmark"]):
            return {"intent": "UNFLAG_TRANSACTION", "data": {}}

        # FLAG
        flag_kws = ["flag ", "mark as flagged", "mark transaction", "flag it", "flag this", "flag that"]
        if any(k in t for k in flag_kws) and "fraud" not in t and "report" not in t:
            return {"intent": "FLAG_TRANSACTION", "data": {}}
        if re.match(r"^flag\s+[\w$]", t) and "fraud" not in t:
            return {"intent": "FLAG_TRANSACTION", "data": {}}

        # EXPLAIN
        explain_kws = ["why was", "why is", "why did", "explain ", "reason for", "what flagged",
                       "what triggered", "tell me why", "how come", "what's wrong"]
        if any(k in t for k in explain_kws):
            temporal = any(w in t for w in ("recent", "latest", "last", "newest"))
            return {"intent": "EXPLAIN_TRANSACTION", "data": {"temporal": temporal}}

        # ADD_TRANSACTION
        spend_kws = ["spent ", "i paid", " paid ", "bought ", "purchased ", "add transaction",
                     "add merchant", "as merchant", "as the merchant", "merchant is",
                     "the merchant is", "to transactions", "log a ", "log purchase",
                     "log transaction", "new transaction", "add purchase", "add a transaction",
                     "record a purchase"]
        if has_num and any(k in t for k in spend_kws):
            return {"intent": "ADD_TRANSACTION", "data": {}}

        # ADD_SUPPORT_TICKET
        support_kws = ["customer reports", "customer says", "issue for", "login issue",
                       "payment fail", "refund delay", "refund not", "card declined",
                       "support ticket", "can't login", "cannot login", "transfer pending",
                       "account locked", "password reset not", "charge dispute", "login problem",
                       "duplicate charge"]
        if any(k in t for k in support_kws):
            return {"intent": "ADD_SUPPORT_TICKET", "data": {}}

        # ADD_COMPLIANCE_RECORD
        compliance_kws = ["compliance note", "add compliance", "missing receipt",
                          "expense reimburse", "first class", "premium seat", "out of policy",
                          "audit note", "compliance record", "manual override", "unusual approval",
                          "policy violation", "reimbursement claim"]
        if any(k in t for k in compliance_kws):
            return {"intent": "ADD_COMPLIANCE_RECORD", "data": {}}

        # ANALYSIS
        analysis_kws = ["check fraud", "fraud activity", "analyze", "summarize",
                        "what should i worry", "risk summary", "what needs attention",
                        "run analysis", "anomal"]
        if any(k in t for k in analysis_kws):
            return {"intent": "RUN_ANALYSIS", "data": {}}

        # QUERY
        query_kws = ["show me", "how many", "what is the", "list ", "tell me about", "what are",
                     "any open", "any pending", "flagged transaction", "open ticket",
                     "pending compliance", "biggest transaction", "highest risk", "most common"]
        if any(k in t for k in query_kws) or t.rstrip().endswith("?"):
            return {"intent": "QUERY_DATA", "data": {}}

        return {"intent": "UNKNOWN", "data": {}}

    # ── Dispatch ──────────────────────────────────────────────────────────────

    async def _dispatch(
        self,
        intent: str,
        data: dict,
        text: str,
        db: AsyncSession,
        history: list[dict] | None,
    ) -> str | None:
        if intent == "ADD_TRANSACTION":
            return await self._add_transaction(data, text, db)
        if intent == "DELETE_TRANSACTION":
            return await self._delete_transaction(data, text, db)
        if intent == "UPDATE_TRANSACTION":
            return await self._update_transaction(data, text, db)
        if intent == "ADD_SUPPORT_TICKET":
            return await self._add_support_ticket(data, text, db)
        if intent == "DELETE_SUPPORT_TICKET":
            return await self._delete_support_ticket(data, text, db)
        if intent == "UPDATE_SUPPORT_TICKET":
            return await self._update_support_ticket(data, text, db)
        if intent == "ADD_COMPLIANCE_RECORD":
            return await self._add_compliance(data, text, db)
        if intent == "DELETE_COMPLIANCE_RECORD":
            return await self._delete_compliance(data, text, db)
        if intent == "UPDATE_COMPLIANCE_RECORD":
            return await self._update_compliance(data, text, db)
        if intent == "FLAG_TRANSACTION":
            return await self._flag_transaction(data, text, db, flagged=True)
        if intent == "UNFLAG_TRANSACTION":
            return await self._flag_transaction(data, text, db, flagged=False)
        if intent == "EXPLAIN_TRANSACTION":
            return await self._explain_transaction(data, text, db, history)
        if intent == "QUERY_DATA":
            return await self._query(data, text, db, history)
        if intent == "RUN_ANALYSIS":
            return await self._analysis(text, db, history)
        return None

    # ── ADD ───────────────────────────────────────────────────────────────────

    async def _add_transaction(self, data: dict, text: str, db: AsyncSession) -> str:
        if not data.get("amount") or not data.get("merchant"):
            # Data wasn't extracted by LLM — fall back to regex
            data = self._regex_parse_transaction(text)

        amount = float(data.get("amount", 0))
        merchant = str(data.get("merchant", "Unknown")).strip()
        location = str(data.get("location") or "Unknown").strip()
        category = str(data.get("category") or "retail").strip()
        notes = data.get("notes") or None
        risk = self._compute_risk(amount, category)

        tx = Transaction(
            id=str(uuid4()), amount=amount, merchant=merchant, location=location,
            category=category, risk_score=risk, flagged=risk > 50, notes=notes, source="sms",
        )
        db.add(tx)
        await self._audit(db, "transaction_added", "transactions",
                          f"Added: ${amount:.2f} at {merchant}", "SMS input", "sms", tx.id)
        await db.flush()

        risk_label = "low" if risk < 31 else ("medium" if risk < 71 else "high")
        flag_note = " ⚑ Auto-flagged." if tx.flagged else ""
        return f"✓ Transaction added: ${amount:.2f} at {merchant} ({location}). Category: {category}. Risk: {risk_label}.{flag_note}"

    async def _add_support_ticket(self, data: dict, text: str, db: AsyncSession) -> str:
        desc = str(data.get("description") or text[:500]).strip()
        category = str(data.get("category") or self._infer_ticket_category(text)).strip()
        priority = str(data.get("priority") or "medium").strip()
        customer = data.get("customer_identifier") or self._extract_customer(text)

        ticket = SupportTicket(
            id=str(uuid4()), customer_identifier=customer, description=desc,
            category=category, status="open", priority=priority, source="sms",
        )
        db.add(ticket)
        await self._audit(db, "support_ticket_created", "support",
                          f"Ticket created: {category}", "SMS input", "sms", ticket.id)
        await db.flush()

        cat = category.replace("_", " ").title()
        who = f" for {customer}" if customer else ""
        return f"✓ Support ticket created: {cat}{who}. Status: Open. Priority: {priority.title()}."

    async def _add_compliance(self, data: dict, text: str, db: AsyncSession) -> str:
        desc = str(data.get("description") or text[:500]).strip()
        rtype = str(data.get("record_type") or self._infer_compliance_type(text)).strip()
        policy_flag = bool(data.get("policy_flag", self._infer_policy_flag(text)))
        severity = data.get("severity") or ("medium" if policy_flag else "low")

        record = ComplianceRecord(
            id=str(uuid4()), record_type=rtype, description=desc, status="pending",
            policy_flag=policy_flag, severity=severity, source="sms",
        )
        db.add(record)
        await self._audit(db, "compliance_record_added", "compliance",
                          f"Compliance: {rtype}", "SMS input", "sms", record.id)
        await db.flush()

        flag_note = " Policy flag raised." if policy_flag else ""
        return f"✓ Compliance record added (status: pending).{flag_note} Severity: {severity}."

    # ── DELETE ────────────────────────────────────────────────────────────────

    async def _delete_transaction(self, data: dict, text: str, db: AsyncSession) -> str:
        merchant = str(data.get("merchant") or "").strip()
        amount = data.get("amount")

        # Clean merchant — strip action words
        merchant = re.sub(
            r"^(?:delete|remove|erase|get rid of|drop|wipe|cancel)\s+(?:the\s+|that\s+|this\s+)?(?:transaction\s+(?:at|from|for)\s+)?",
            "", merchant, flags=re.IGNORECASE,
        ).strip()
        merchant = re.sub(r"\s+transaction$", "", merchant, flags=re.IGNORECASE).strip()

        rows = await self._find_transactions(db, merchant or None, amount)
        if not rows:
            return f"No transaction found matching \"{merchant or amount}\". Try being more specific."
        if len(rows) > 1:
            opts = "\n".join(f"  {i+1}. ${r.amount:.2f} at {r.merchant} ({r.location}) — {r.created_at.date()}" for i, r in enumerate(rows[:4]))
            return f"Found {len(rows)} matches. Which one?\n{opts}\nReply with the amount to narrow it down."

        tx = rows[0]
        desc = f"${tx.amount:.2f} at {tx.merchant}"
        await db.execute(delete(Transaction).where(Transaction.id == tx.id))
        await self._audit(db, "transaction_deleted", "transactions",
                          f"Deleted transaction: {desc}", "SMS request", "sms")
        await db.flush()
        return f"✓ Transaction deleted: {desc} ({tx.location}) from {tx.created_at.date()}."

    async def _delete_support_ticket(self, data: dict, text: str, db: AsyncSession) -> str:
        keywords = str(data.get("keywords") or text)
        keywords = re.sub(r"^(?:delete|remove|erase|close|cancel)\s+(?:the\s+|that\s+)?(?:support\s+)?(?:ticket\s+)?", "", keywords, flags=re.IGNORECASE).strip()

        rows = await self._find_tickets_by_keywords(db, keywords)
        if not rows:
            return f"No support ticket found matching \"{keywords[:60]}\". Try different keywords."
        if len(rows) > 1:
            opts = "\n".join(f"  {i+1}. [{r.status}] {r.description[:60]}..." for i, r in enumerate(rows[:4]))
            return f"Found {len(rows)} tickets. Which one?\n{opts}"

        tk = rows[0]
        await db.execute(delete(SupportTicket).where(SupportTicket.id == tk.id))
        await self._audit(db, "support_ticket_deleted", "support",
                          f"Deleted ticket: {tk.category}", "SMS request", "sms")
        await db.flush()
        return f"✓ Support ticket deleted: {tk.category.replace('_',' ').title()} — \"{tk.description[:60]}...\""

    async def _delete_compliance(self, data: dict, text: str, db: AsyncSession) -> str:
        keywords = str(data.get("keywords") or text)
        keywords = re.sub(r"^(?:delete|remove|erase|cancel)\s+(?:the\s+|that\s+)?(?:compliance\s+)?(?:record\s+)?", "", keywords, flags=re.IGNORECASE).strip()

        rows = await self._find_compliance_by_keywords(db, keywords)
        if not rows:
            return f"No compliance record found matching \"{keywords[:60]}\"."
        if len(rows) > 1:
            opts = "\n".join(f"  {i+1}. [{r.status}] {r.description[:60]}..." for i, r in enumerate(rows[:4]))
            return f"Found {len(rows)} records. Which one?\n{opts}"

        rec = rows[0]
        await db.execute(delete(ComplianceRecord).where(ComplianceRecord.id == rec.id))
        await self._audit(db, "compliance_record_deleted", "compliance",
                          f"Deleted compliance record: {rec.record_type}", "SMS request", "sms")
        await db.flush()
        return f"✓ Compliance record deleted: \"{rec.description[:60]}...\""

    # ── UPDATE ────────────────────────────────────────────────────────────────

    async def _update_transaction(self, data: dict, text: str, db: AsyncSession) -> str:
        merchant = str(data.get("merchant") or "").strip()
        amount = data.get("amount")
        field = str(data.get("field") or "").strip().lower()
        new_value = data.get("new_value")

        rows = await self._find_transactions(db, merchant or None, amount)
        if not rows:
            return f"No transaction found matching \"{merchant or amount}\"."
        if len(rows) > 1:
            opts = "\n".join(f"  {i+1}. ${r.amount:.2f} at {r.merchant} — {r.created_at.date()}" for i, r in enumerate(rows[:4]))
            return f"Found {len(rows)} matches. Which one?\n{opts}"

        tx = rows[0]
        allowed = {"category", "location", "notes", "amount", "merchant", "flagged", "risk_score"}
        if field not in allowed:
            return f"Can't update field \"{field}\". Allowed: {', '.join(sorted(allowed))}."

        old = getattr(tx, field)
        if field == "amount":
            setattr(tx, field, float(new_value))
        elif field == "flagged":
            setattr(tx, field, str(new_value).lower() in ("true", "yes", "1"))
        elif field == "risk_score":
            setattr(tx, field, int(new_value))
        else:
            setattr(tx, field, str(new_value))

        await self._audit(db, "transaction_updated", "transactions",
                          f"Updated {field} on ${tx.amount:.2f} at {tx.merchant}: {old!r} → {new_value!r}",
                          "SMS request", "sms", tx.id)
        await db.flush()
        return f"✓ Transaction updated: {field} changed to \"{new_value}\" for ${tx.amount:.2f} at {tx.merchant}."

    async def _update_support_ticket(self, data: dict, text: str, db: AsyncSession) -> str:
        keywords = str(data.get("keywords") or text)
        field = str(data.get("field") or "status").strip().lower()
        new_value = str(data.get("new_value") or "").strip()

        # Infer value if not provided
        if not new_value:
            t = text.lower()
            if field == "status":
                if any(w in t for w in ("resolv", "clos", "done", "fix")):
                    new_value = "resolved"
                elif any(w in t for w in ("review", "escalat", "investigate")):
                    new_value = "in_review"
                else:
                    new_value = "open"
            elif field == "priority":
                new_value = "high" if "high" in t or "urgent" in t else ("low" if "low" in t else "medium")

        rows = await self._find_tickets_by_keywords(db, keywords)
        if not rows:
            return f"No support ticket found matching \"{keywords[:60]}\"."
        if len(rows) > 1:
            opts = "\n".join(f"  {i+1}. [{r.status}] {r.description[:60]}..." for i, r in enumerate(rows[:4]))
            return f"Found {len(rows)} tickets. Which one?\n{opts}"

        tk = rows[0]
        allowed = {"status", "priority", "description", "category"}
        if field not in allowed:
            return f"Can't update \"{field}\". Allowed: {', '.join(sorted(allowed))}."

        old = getattr(tk, field)
        setattr(tk, field, new_value)
        await self._audit(db, "support_ticket_updated", "support",
                          f"Updated ticket {field}: {old!r} → {new_value!r}", "SMS request", "sms", tk.id)
        await db.flush()
        cat = tk.category.replace("_", " ").title()
        return f"✓ Ticket updated: {field} set to \"{new_value}\" for [{cat}] ticket."

    async def _update_compliance(self, data: dict, text: str, db: AsyncSession) -> str:
        keywords = str(data.get("keywords") or text)
        field = str(data.get("field") or "status").strip().lower()
        new_value = str(data.get("new_value") or "").strip()

        if not new_value:
            t = text.lower()
            if field == "status":
                new_value = "approved" if "approv" in t else ("rejected" if "reject" in t else "pending")

        rows = await self._find_compliance_by_keywords(db, keywords)
        if not rows:
            return f"No compliance record found matching \"{keywords[:60]}\"."
        if len(rows) > 1:
            opts = "\n".join(f"  {i+1}. [{r.status}] {r.description[:60]}..." for i, r in enumerate(rows[:4]))
            return f"Found {len(rows)} records. Which one?\n{opts}"

        rec = rows[0]
        allowed = {"status", "severity", "description", "recommendation", "policy_flag"}
        if field not in allowed:
            return f"Can't update \"{field}\". Allowed: {', '.join(sorted(allowed))}."

        old = getattr(rec, field)
        if field == "policy_flag":
            setattr(rec, field, str(new_value).lower() in ("true", "yes", "1"))
        else:
            setattr(rec, field, new_value)
        await self._audit(db, "compliance_record_updated", "compliance",
                          f"Updated compliance {field}: {old!r} → {new_value!r}", "SMS request", "sms", rec.id)
        await db.flush()
        return f"✓ Compliance record updated: {field} set to \"{new_value}\"."

    # ── FLAG / UNFLAG ─────────────────────────────────────────────────────────

    async def _flag_transaction(self, data: dict, text: str, db: AsyncSession, flagged: bool) -> str:
        merchant = str(data.get("merchant") or "").strip()
        amount = data.get("amount")

        # Clean action words from merchant
        merchant = re.sub(
            r"^(?:flag|unflag|mark|clear\s+flag\s+(?:from)?|remove\s+flag\s+from)\s+(?:the\s+|that\s+|this\s+|last\s+)?(?:transaction\s+(?:at|from|for)\s+)?",
            "", merchant, flags=re.IGNORECASE,
        ).strip()
        merchant = re.sub(r"\s+(?:transaction|as\s+flagged|as\s+suspicious)$", "", merchant, flags=re.IGNORECASE).strip()

        rows = await self._find_transactions(db, merchant or None, amount)
        if not rows:
            # Last resort: most recent transaction
            rows = (await db.execute(
                select(Transaction).order_by(Transaction.created_at.desc()).limit(1)
            )).scalars().all()
            if not rows:
                return "No transactions found."

        if len(rows) > 1:
            opts = "\n".join(f"  {i+1}. ${r.amount:.2f} at {r.merchant} ({r.location}) — {r.created_at.date()}" for i, r in enumerate(rows[:4]))
            return f"Found {len(rows)} matches. Which one?\n{opts}"

        tx = rows[0]
        tx.flagged = flagged
        if flagged and tx.risk_score < 50:
            tx.risk_score = max(tx.risk_score, 55)
        action = "flagged" if flagged else "unflagged"
        await self._audit(db, f"transaction_{action}", "transactions",
                          f"Transaction {action}: ${tx.amount:.2f} at {tx.merchant}", "SMS request", "sms", tx.id)
        await db.flush()
        icon = "⚑" if flagged else "✓"
        return f"{icon} Transaction {action}: ${tx.amount:.2f} at {tx.merchant} ({tx.location}), {tx.created_at.date()}. Risk: {tx.risk_score}/100."

    # ── EXPLAIN ───────────────────────────────────────────────────────────────

    async def _explain_transaction(
        self, data: dict, text: str, db: AsyncSession, history: list[dict] | None
    ) -> str:
        merchant = str(data.get("merchant") or "").strip()
        amount = data.get("amount")
        temporal = bool(data.get("temporal", False))

        # Strip noise words from merchant
        noise = {"why", "was", "is", "did", "the", "that", "this", "a", "an", "explain",
                 "reason", "for", "flagged", "transaction", "tell", "me", "how", "come",
                 "what", "wrong", "with", "triggered", "it", "get", "been", "got",
                 "marked", "suspicious", "flag", "recent", "latest", "last", "newest",
                 "first", "most", "just", "one"}
        if not merchant:
            words = [w for w in re.sub(r"[?']", "", text).split() if w.lower() not in noise]
            merchant = " ".join(words).strip()

        rows = await self._find_transactions(db, merchant or None, amount)

        if not rows or temporal:
            flagged_rows = (await db.execute(
                select(Transaction).where(Transaction.flagged.is_(True))
                .order_by(Transaction.created_at.desc()).limit(1)
            )).scalars().all()
            if flagged_rows:
                rows = flagged_rows

        if not rows:
            return "No matching transaction found. Try: 'Why was the Walmart transaction flagged?'"

        tx = rows[0]
        risk_label = "low" if tx.risk_score < 31 else ("medium" if tx.risk_score < 71 else "high")
        context = (
            f"Merchant: {tx.merchant} | Amount: ${tx.amount:.2f} | Location: {tx.location}\n"
            f"Category: {tx.category} | Date: {tx.created_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"Risk score: {tx.risk_score}/100 ({risk_label}) | Flagged: {tx.flagged}\n"
            f"Source: {tx.source}"
            + (f"\nNotes: {tx.notes}" if tx.notes else "")
        )

        if self.llm.enabled:
            prompt = (
                "Explain clearly why this transaction was flagged (or not). "
                "Cite specific risk signals. Be direct and concise (2-3 sentences).\n\n"
                f"{context}\n\nUser: {text}\n\nAnswer:"
            )
            try:
                return await asyncio.to_thread(self.llm.generate_reply, prompt, history)
            except Exception:  # noqa: BLE001
                pass

        flag_note = "This transaction IS flagged." if tx.flagged else "This transaction is not flagged."
        return f"{flag_note}\n{context}"

    # ── QUERY ─────────────────────────────────────────────────────────────────

    async def _query(
        self, data: dict, text: str, db: AsyncSession, history: list[dict] | None
    ) -> str:
        t = text.lower()
        domain = str(data.get("domain") or "all")
        wants_recent = bool(data.get("wants_recent")) or any(w in t for w in ("recent", "latest", "last", "newest"))
        wants_flagged = bool(data.get("wants_flagged")) or "flagged" in t
        wants_list = bool(data.get("wants_list")) or any(w in t for w in ("show", "list", "display"))
        filter_status = data.get("filter_status")

        parts: list[str] = []

        if domain in ("transactions", "all") or any(w in t for w in ("transaction", "spending", "amount", "flagged")):
            total = await db.scalar(select(func.count(Transaction.id)))
            flagged_ct = await db.scalar(select(func.count(Transaction.id)).where(Transaction.flagged.is_(True)))
            parts.append(f"Transactions: {total} total, {flagged_ct} flagged.")

            if wants_list:
                if wants_recent and wants_flagged:
                    q = select(Transaction).where(Transaction.flagged.is_(True)).order_by(Transaction.created_at.desc()).limit(25)  # type: ignore[arg-type]
                    label = "flagged (newest first)"
                elif wants_flagged:
                    q = select(Transaction).where(Transaction.flagged.is_(True)).order_by(Transaction.risk_score.desc()).limit(25)  # type: ignore[arg-type]
                    label = "flagged (highest risk first)"
                else:
                    q = select(Transaction).order_by(Transaction.created_at.desc()).limit(15)  # type: ignore[arg-type]
                    label = "recent"
                rows = (await db.execute(q)).scalars().all()
                if rows:
                    lines = "\n".join(
                        f"  {i+1}. ${r.amount:,.2f} at {r.merchant} ({r.location}) — {r.category}, risk {r.risk_score}"
                        + (" ⚑" if r.flagged else "")
                        for i, r in enumerate(rows)
                    )
                    parts.append(f"{len(rows)} {label} transactions:\n{lines}")

        if domain in ("support", "all") or any(w in t for w in ("ticket", "support", "issue")):
            status_q = filter_status or ("open" if "open" in t else None)
            q = select(func.count(SupportTicket.id))
            if status_q:
                q = q.where(SupportTicket.status == status_q)
            ct = await db.scalar(q)
            parts.append(f"Support tickets ({status_q or 'all'}): {ct}.")
            if wants_list:
                lq = select(SupportTicket).order_by(SupportTicket.created_at.desc()).limit(15)  # type: ignore[arg-type]
                if status_q:
                    lq = lq.where(SupportTicket.status == status_q)
                rows = (await db.execute(lq)).scalars().all()
                if rows:
                    lines = "\n".join(
                        f"  {i+1}. [{r.priority}/{r.status}] {r.category.replace('_',' ')}: {r.description[:70]}"
                        + (f" ({r.customer_identifier})" if r.customer_identifier else "")
                        for i, r in enumerate(rows)
                    )
                    parts.append(f"Tickets:\n{lines}")

        if domain in ("compliance", "all") or any(w in t for w in ("compliance", "policy", "pending")):
            status_q = filter_status or ("pending" if "pending" in t else None)
            q = select(func.count(ComplianceRecord.id))
            if status_q:
                q = q.where(ComplianceRecord.status == status_q)
            ct = await db.scalar(q)
            parts.append(f"Compliance records ({status_q or 'all'}): {ct}.")
            if wants_list:
                lq = select(ComplianceRecord).order_by(ComplianceRecord.created_at.desc()).limit(15)  # type: ignore[arg-type]
                if status_q:
                    lq = lq.where(ComplianceRecord.status == status_q)
                rows = (await db.execute(lq)).scalars().all()
                if rows:
                    lines = "\n".join(
                        f"  {i+1}. [{r.status}/{r.severity or 'low'}] {r.record_type.replace('_',' ')}: {r.description[:70]}"
                        for i, r in enumerate(rows)
                    )
                    parts.append(f"Compliance:\n{lines}")

        if not parts:
            tx_ct = await db.scalar(select(func.count(Transaction.id)))
            fl_ct = await db.scalar(select(func.count(Transaction.id)).where(Transaction.flagged.is_(True)))
            tk_ct = await db.scalar(select(func.count(SupportTicket.id)).where(SupportTicket.status == "open"))
            cp_ct = await db.scalar(select(func.count(ComplianceRecord.id)).where(ComplianceRecord.status == "pending"))
            parts.append(f"System: {tx_ct} transactions ({fl_ct} flagged), {tk_ct} open tickets, {cp_ct} pending compliance.")

        context = "\n".join(parts)
        if self.llm.enabled:
            prompt = (
                "You are an ops assistant. Answer using only the data below. "
                "Present every listed item — do not omit any. Formatted for SMS.\n\n"
                f"Data:\n{context}\n\nQuestion: {text}\n\nAnswer:"
            )
            try:
                return await asyncio.to_thread(self.llm.generate_reply, prompt, history)
            except Exception:  # noqa: BLE001
                pass
        return context

    # ── ANALYSIS ──────────────────────────────────────────────────────────────

    async def _analysis(self, text: str, db: AsyncSession, history: list[dict] | None) -> str:
        flagged = (await db.execute(
            select(Transaction).where(Transaction.flagged.is_(True))
            .order_by(Transaction.risk_score.desc()).limit(5)  # type: ignore[arg-type]
        )).scalars().all()
        total_tx = await db.scalar(select(func.count(Transaction.id)))
        open_tk = await db.scalar(select(func.count(SupportTicket.id)).where(SupportTicket.status == "open"))
        pending_cp = await db.scalar(select(func.count(ComplianceRecord.id)).where(ComplianceRecord.status == "pending"))

        snapshot = (
            f"Total transactions: {total_tx}, flagged: {len(flagged)}\n"
            f"Open support tickets: {open_tk}\nPending compliance: {pending_cp}"
        )
        if flagged:
            top = flagged[0]
            snapshot += f"\nHighest risk: ${top.amount:.2f} at {top.merchant} ({top.location}), score {top.risk_score}"

        if self.llm.enabled:
            prompt = (
                "You are an ops risk analyst. Analyze this data, surface what needs immediate attention, "
                "and identify any patterns. Specific and actionable, 2-4 sentences.\n\n"
                f"{snapshot}\n\nUser: {text}\n\nAnalysis:"
            )
            try:
                return await asyncio.to_thread(self.llm.generate_reply, prompt, history)
            except Exception:  # noqa: BLE001
                pass
        return snapshot

    # ── DB helpers ────────────────────────────────────────────────────────────

    async def _find_transactions(
        self, db: AsyncSession, merchant: str | None, amount: float | None, limit: int = 5
    ) -> list[Transaction]:
        q = select(Transaction).order_by(Transaction.created_at.desc())  # type: ignore[arg-type]
        if merchant and len(merchant) >= 2:
            q = q.where(Transaction.merchant.ilike(f"%{merchant}%"))
        if amount is not None:
            q = q.where(Transaction.amount == float(amount))
        return list((await db.execute(q.limit(limit))).scalars().all())

    async def _find_tickets_by_keywords(self, db: AsyncSession, keywords: str) -> list[SupportTicket]:
        words = [w for w in keywords.split() if len(w) >= 3][:4]
        q = select(SupportTicket).order_by(SupportTicket.created_at.desc())  # type: ignore[arg-type]
        for w in words:
            q = q.where(SupportTicket.description.ilike(f"%{w}%"))
        rows = list((await db.execute(q.limit(5))).scalars().all())
        if not rows and words:
            q2 = select(SupportTicket).where(SupportTicket.description.ilike(f"%{words[0]}%")).order_by(SupportTicket.created_at.desc()).limit(5)  # type: ignore[arg-type]
            rows = list((await db.execute(q2)).scalars().all())
        return rows

    async def _find_compliance_by_keywords(self, db: AsyncSession, keywords: str) -> list[ComplianceRecord]:
        words = [w for w in keywords.split() if len(w) >= 3][:4]
        q = select(ComplianceRecord).order_by(ComplianceRecord.created_at.desc())  # type: ignore[arg-type]
        for w in words:
            q = q.where(ComplianceRecord.description.ilike(f"%{w}%"))
        rows = list((await db.execute(q.limit(5))).scalars().all())
        if not rows and words:
            q2 = select(ComplianceRecord).where(ComplianceRecord.description.ilike(f"%{words[0]}%")).order_by(ComplianceRecord.created_at.desc()).limit(5)  # type: ignore[arg-type]
            rows = list((await db.execute(q2)).scalars().all())
        return rows

    # ── Regex fallback parsers ────────────────────────────────────────────────

    def _regex_parse_transaction(self, text: str) -> dict:
        amount_m = re.search(r"\$?\s*(\d[\d,]*(?:\.\d{1,2})?)", text)
        amount = float(amount_m.group(1).replace(",", "")) if amount_m else 0.0

        as_merchant_m = re.search(r"(.+?)\s+as\s+(?:the\s+)?merchant", text, re.IGNORECASE)
        merchant_is_m = re.search(r"merchant\s+(?:is|:)\s+(.+?)(?:\s+and\s+(?:the\s+)?amount|\s*$)", text, re.IGNORECASE)
        at_m = re.search(r"at\s+([A-Za-z][^,\n]+?)(?:\s+in\s+|\s+for\s+|\s+and\s+|\s*$)", text, re.IGNORECASE)

        if as_merchant_m:
            merchant = re.sub(r"\$?\d[\d,]*(?:\.\d{1,2})?", "", as_merchant_m.group(1)).strip(" ,")
            merchant = re.sub(r"^(?:add|log|record|put|create|new)\s+", "", merchant, flags=re.IGNORECASE).strip()
        elif merchant_is_m:
            merchant = merchant_is_m.group(1).strip(" ,")
        elif at_m:
            merchant = at_m.group(1).strip()
        else:
            merchant = "Unknown"

        in_m = re.search(r"\bin\s+([A-Z][a-zA-Z ]+)", text)
        location = in_m.group(1).strip() if in_m else "Unknown"
        return {"amount": amount, "merchant": merchant, "location": location, "category": "retail"}

    # ── Small inference helpers ───────────────────────────────────────────────

    @staticmethod
    def _compute_risk(amount: float, category: str) -> int:
        score = 0
        if amount > 2500:
            score += 40
        elif amount > 1000:
            score += 20
        elif amount > 500:
            score += 10
        if category in ("electronics", "travel", "transfers") and amount > 500:
            score += 15
        return min(score, 100)

    @staticmethod
    def _infer_ticket_category(text: str) -> str:
        t = text.lower()
        if "refund" in t:
            return "refund_delay"
        if "login" in t or "password" in t:
            return "login_issue"
        if "payment" in t or "charge" in t:
            return "payment_failure"
        if "duplicate" in t:
            return "duplicate_charge"
        if "locked" in t:
            return "account_locked"
        if "transfer" in t:
            return "transfer_issue"
        return "general"

    @staticmethod
    def _extract_customer(text: str) -> str | None:
        order_m = re.search(r"order\s*[#]?\s*(\d+)", text, re.IGNORECASE)
        if order_m:
            return f"Order #{order_m.group(1)}"
        name_m = re.search(r"(?:for|customer|user)\s+([A-Z][a-z]+)", text)
        return name_m.group(1) if name_m else None

    @staticmethod
    def _infer_compliance_type(text: str) -> str:
        t = text.lower()
        if "expense" in t or "reimburs" in t:
            return "expense_policy"
        if "receipt" in t or "document" in t:
            return "missing_documentation"
        if "override" in t:
            return "manual_override"
        if "approval" in t:
            return "unusual_approval"
        return "general"

    @staticmethod
    def _infer_policy_flag(text: str) -> bool:
        flags = ["first class", "premium", "luxury", "upgrade", "missing receipt",
                 "no receipt", "not justified", "out of policy"]
        return any(f in text.lower() for f in flags)

    # ── Audit ─────────────────────────────────────────────────────────────────

    async def _audit(
        self, db: AsyncSession, event_type: str, domain: str,
        action: str, reasoning: str | None, source: str, entity_id: str | None = None,
    ) -> None:
        db.add(AuditLog(
            id=str(uuid4()), event_type=event_type, domain=domain,
            action_taken=action, reasoning=reasoning, source=source,
            related_entity_id=entity_id,
        ))
