from __future__ import annotations

import asyncio
import json
import re
from uuid import uuid4

from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.llm import LLMResponder
from backend.app.models.agent_action import AgentAction
from backend.app.models.audit_log import AuditLog
from backend.app.models.compliance_record import ComplianceRecord
from backend.app.models.support_ticket import SupportTicket
from backend.app.models.transaction import Transaction
from backend.app.services.agent_actions import AgentActionService

# ── LLM intent-parsing prompt ─────────────────────────────────────────────────

_PARSE_SYSTEM = """You are an ops data parser. Given a user message, return ONLY valid JSON.

Supported intents:

ADD_TRANSACTION        data: {amount, merchant, item_name, location, category, notes}
DELETE_TRANSACTION     data: {merchant, amount}            — at least one field
UPDATE_TRANSACTION     data: {merchant, amount, field, new_value}
                             field: category|location|notes|amount|merchant|item_name|flagged|risk_score

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
        self.agent_actions = AgentActionService()

    # ── Public entry point ────────────────────────────────────────────────────

    async def process(
        self,
        text: str,
        db: AsyncSession,
        history: list[dict] | None = None,
    ) -> str | None:
        action_reply = await self._handle_agent_action_command(text, db)
        if action_reply is not None:
            return action_reply

        parsed = await asyncio.to_thread(self._parse_intent, text, history)
        intent: str = parsed.get("intent", "UNKNOWN")
        data: dict = parsed.get("data", {})

        if intent in {"UNKNOWN", "CHAT"}:
            return None

        try:
            return await self._dispatch(intent, data, text, db, history)
        except Exception as exc:  # noqa: BLE001
            return f"Something went wrong: {str(exc)[:120]}"

    # ── Intent parsing via LLM (with keyword fallback) ────────────────────────

    def _parse_intent(self, text: str, history: list[dict] | None) -> dict:
        t = text.lower().strip()

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
                raw = self.llm.generate_reply(prompt, system_prompt=_PARSE_SYSTEM)
                m = re.search(r"\{.*\}", raw, re.DOTALL)
                if m:
                    return json.loads(m.group())
            except Exception:  # noqa: BLE001
                pass

        # Fallback keyword classifier
        return self._keyword_classify(t)

    def _keyword_classify(self, t: str) -> dict:
        t = t.lower().strip()
        has_num = bool(re.search(r"\d", t))

        if self._is_conversational_or_meta(t):
            return {"intent": "UNKNOWN", "data": {}}

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

        # QUERY
        query_kws = ["show me", "how many", "what is the", "list ", "tell me about", "what are",
                     "any open", "any pending", "flagged transaction", "open ticket",
                     "pending compliance", "biggest transaction", "highest risk", "most common"]
        domain_words = (
            "transaction", "spending", "merchant", "amount", "flagged", "risk",
            "ticket", "support", "issue", "customer", "refund", "login",
            "compliance", "policy", "audit", "approval", "pending",
        )
        if any(k in t for k in query_kws) or (t.rstrip().endswith("?") and any(w in t for w in domain_words)):
            return {"intent": "QUERY_DATA", "data": {}}

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

    # ── Agent action approvals ───────────────────────────────────────────────

    async def _handle_agent_action_command(self, text: str, db: AsyncSession) -> str | None:
        t = text.lower().strip()
        mentions_action = any(
            phrase in t
            for phrase in (
                "agent action",
                "agent actions",
                "approval",
                "approvals",
                "recommendation",
                "recommendations",
                "pending action",
                "pending actions",
                "next action",
                "latest action",
            )
        )
        if not mentions_action:
            return None

        if any(word in t for word in ("generate", "scan", "recommend", "suggest", "create")):
            created = await self.agent_actions.generate_recommendations(db)
            if not created:
                pending = await self._pending_agent_actions(db, limit=3)
                if not pending:
                    return "No new approval actions right now."
                return "No new actions. Pending: " + self._format_agent_actions(pending)
            return f"Created {len(created)} approval actions. " + self._format_agent_actions(created[:3])

        if any(word in t for word in ("show", "list", "what", "pending", "open", "need")):
            pending = await self._pending_agent_actions(db, limit=3)
            if not pending:
                return "No pending approval actions right now."
            return "Pending approvals: " + self._format_agent_actions(pending)

        if any(word in t for word in ("approve", "yes", "confirm", "do it")):
            action = await self._latest_pending_agent_action(db)
            if action is None:
                return "No pending agent action to approve."
            await self.agent_actions.approve(db, action)
            return f"Approved: {action.title}."

        if any(word in t for word in ("reject", "no", "cancel", "skip", "deny")):
            action = await self._latest_pending_agent_action(db)
            if action is None:
                return "No pending agent action to reject."
            await self.agent_actions.reject(db, action, reason="Rejected from SMS")
            return f"Rejected: {action.title}."

        return None

    async def _pending_agent_actions(self, db: AsyncSession, limit: int = 3) -> list[AgentAction]:
        return list(
            (
                await db.execute(
                    select(AgentAction)
                    .where(AgentAction.status == "pending")
                    .order_by(desc(AgentAction.created_at))
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )

    async def _latest_pending_agent_action(self, db: AsyncSession) -> AgentAction | None:
        return await db.scalar(
            select(AgentAction)
            .where(AgentAction.status == "pending")
            .order_by(desc(AgentAction.created_at))
            .limit(1)
        )

    @staticmethod
    def _format_agent_actions(actions: list[AgentAction]) -> str:
        pieces = [
            f"{idx + 1}. {action.title} ({action.priority}, {round(action.confidence * 100)}%)"
            for idx, action in enumerate(actions)
        ]
        return " ".join(pieces)

    # ── Conversational replies ───────────────────────────────────────────────

    # ── ADD ───────────────────────────────────────────────────────────────────

    async def _add_transaction(self, data: dict, text: str, db: AsyncSession) -> str:
        fallback_data = self._regex_parse_transaction(text)
        if not data.get("amount") or not data.get("merchant"):
            # Data wasn't extracted by LLM — fall back to regex.
            data = fallback_data
        else:
            for key in ("item_name", "location", "category", "notes"):
                if not data.get(key) and fallback_data.get(key):
                    data[key] = fallback_data[key]
            if data.get("category") in {"general", "retail"} and fallback_data.get("category") not in {None, "retail"}:
                data["category"] = fallback_data["category"]

        amount = float(data.get("amount", 0))
        merchant = str(data.get("merchant", "Unknown")).strip()
        item_name = self._clean_optional_text(data.get("item_name"))
        location = str(data.get("location") or "Unknown").strip()
        category = str(data.get("category") or "retail").strip()
        notes = self._clean_optional_text(data.get("notes"))
        risk = self._compute_risk(amount, category)

        tx = Transaction(
            id=str(uuid4()), amount=amount, merchant=merchant, location=location,
            item_name=item_name, category=category, risk_score=risk, flagged=risk >= 71, notes=notes, source="sms",
        )
        db.add(tx)
        await self._audit(db, "transaction_added", "transactions",
                          f"Added: ${amount:.2f} at {merchant}", "SMS input", "sms", tx.id)
        await db.flush()

        risk_label = "low" if risk < 31 else ("medium" if risk < 71 else "high")
        flag_note = " ⚑ Auto-flagged." if tx.flagged else ""
        item_note = f" Item: {item_name}." if item_name else ""
        return f"✓ Transaction added: ${amount:.2f} at {merchant} ({location}).{item_note} Category: {category}. Risk: {risk_label}.{flag_note}"

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
        allowed = {"category", "location", "notes", "amount", "merchant", "item_name", "flagged", "risk_score"}
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
        item_context = f"Item: {tx.item_name}\n" if tx.item_name else ""
        context = (
            f"Merchant: {tx.merchant} | Amount: ${tx.amount:.2f} | Location: {tx.location}\n"
            f"{item_context}"
            f"Category: {tx.category} | Date: {tx.created_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"Risk score: {tx.risk_score}/100 ({risk_label}) | Flagged: {tx.flagged}\n"
            f"Source: {tx.source}"
            + (f"\nNotes: {tx.notes}" if tx.notes else "")
        )

        if self.llm.enabled:
            prompt = (
                "Explain clearly why this transaction was flagged (or not). "
                "Cite the strongest signal only. Keep it to 1-2 short SMS-friendly sentences.\n\n"
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
                "Keep the reply SMS-friendly: 1-2 short sentences by default. "
                "If the user explicitly asked for a list, show at most the top 3 items and say they can ask for more.\n\n"
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
                "and identify any pattern. Keep it to 2 short SMS-friendly sentences, with one next action.\n\n"
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

        notes = self._extract_field_after_label(text, ("notes", "note", "memo", "reason"))
        item_name = self._extract_field_after_label(text, ("item name", "item", "product name", "product"))
        as_merchant_m = re.search(r"(.+?)\s+as\s+(?:the\s+)?merchant", text, re.IGNORECASE)
        merchant_is_m = re.search(r"merchant\s+(?:is|:)\s+(.+?)(?:\s+and\s+(?:the\s+)?amount|\s*$)", text, re.IGNORECASE)
        at_m = re.search(r"at\s+([A-Za-z][^,\n]+?)(?:\s+in\s+|\s+for\s+|\s+notes?\b|\s+memo\b|\s+reason\b|\s+and\s+|\s*$)", text, re.IGNORECASE)

        if as_merchant_m:
            merchant = re.sub(r"\$?\d[\d,]*(?:\.\d{1,2})?", "", as_merchant_m.group(1)).strip(" ,")
            merchant = re.sub(r"^(?:add|log|record|put|create|new)\s+", "", merchant, flags=re.IGNORECASE).strip()
        elif merchant_is_m:
            merchant = merchant_is_m.group(1).strip(" ,")
        elif at_m:
            merchant = at_m.group(1).strip()
        else:
            merchant = "Unknown"

        if not item_name:
            item_patterns = (
                r"\b(?:bought|purchased|ordered)\s+(.+?)(?:\s+for\s+\$?\s*\d|\s+at\s+|\s+from\s+|\s+in\s+|\s+notes?\b|\s+memo\b|\s+reason\b|$)",
                r"\b(?:spent|paid)\s+\$?\s*\d[\d,]*(?:\.\d{1,2})?\s+(?:on|for)\s+(.+?)(?:\s+at\s+|\s+from\s+|\s+in\s+|\s+notes?\b|\s+memo\b|\s+reason\b|$)",
                r"\bfor\s+(.+?)(?:\s+at\s+|\s+from\s+|\s+in\s+|\s+notes?\b|\s+memo\b|\s+reason\b|$)",
            )
            for pattern in item_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    item_name = self._clean_optional_text(match.group(1))
                    break

        in_m = re.search(r"\bin\s+([A-Z][a-zA-Z ]+?)(?:\s+notes?\b|\s+memo\b|\s+reason\b|$)", text)
        location = in_m.group(1).strip() if in_m else "Unknown"
        return {
            "amount": amount,
            "merchant": merchant,
            "item_name": item_name,
            "location": location,
            "category": self._infer_transaction_category(text, item_name),
            "notes": notes,
        }

    # ── Small inference helpers ───────────────────────────────────────────────

    @staticmethod
    def _clean_optional_text(value: object) -> str | None:
        if value is None:
            return None
        cleaned = re.sub(r"\s+", " ", str(value)).strip(" ,.;:-")
        return cleaned or None

    @staticmethod
    def _extract_field_after_label(text: str, labels: tuple[str, ...]) -> str | None:
        label_pattern = "|".join(re.escape(label) for label in labels)
        stop_labels = "merchant|amount|location|category|risk|flag|notes?|memo|reason|item(?: name)?|product(?: name)?"
        match = re.search(
            rf"\b(?:{label_pattern})\s*(?:is|:|-)?\s+(.+?)(?=\s+\b(?:{stop_labels})\b\s*(?:is|:|-)?|$)",
            text,
            re.IGNORECASE,
        )
        return OpsProcessor._clean_optional_text(match.group(1)) if match else None

    @staticmethod
    def _infer_transaction_category(text: str, item_name: str | None = None) -> str:
        t = f"{text} {item_name or ''}".lower()
        _LUXURY = {
            "louis vuitton", "vuitton", "gucci", "prada", "chanel", "hermès", "hermes",
            "rolex", "versace", "burberry", "fendi", "balenciaga", "dior", "cartier",
            "tiffany", "bentley", "ferrari", "lamborghini", "bvlgari", "bulgari",
            "bottega", "saint laurent", "ysl", "givenchy", "valentino", "moncler",
        }
        if any(brand in t for brand in _LUXURY) or "luxury" in t:
            return "luxury"
        if any(w in t for w in ("laptop", "computer", "phone", "ipad", "iphone", "macbook", "monitor", "keyboard", "software", "samsung", "galaxy")):
            return "electronics"
        if any(w in t for w in ("flight", "hotel", "airbnb", "uber", "lyft", "travel", "airline", "rental car", "airways", "airlines")):
            return "travel"
        if any(w in t for w in ("restaurant", "lunch", "dinner", "coffee", "food", "meal", "cafe", "sushi", "pizza", "burger")):
            return "meals"
        if any(w in t for w in ("transfer", "wire", "ach", "zelle", "venmo", "cashapp")):
            return "transfers"
        if any(w in t for w in ("grocery", "groceries", "supermarket", "whole foods", "costco", "trader joe")):
            return "groceries"
        return "retail"

    @staticmethod
    def _compute_risk(amount: float, category: str) -> int:
        # Matches _risk_from_transaction in ops.py exactly
        risk = 15
        if amount >= 2000:
            risk += 55
        elif amount >= 500:
            risk += 30
        elif amount >= 150:
            risk += 12
        if category.lower() in {"travel", "electronics", "luxury", "cash", "crypto", "transfers"}:
            risk += 15
        return min(risk, 100)

    @staticmethod
    def _is_conversational_or_meta(text: str) -> bool:
        t = text.lower().strip()
        conversational = {"hello", "hi", "hey", "thanks", "thank you", "ok", "okay", "yes", "no", "bye"}
        return (
            t in conversational
            or (len(t.split()) <= 2 and not re.search(r"\d", t))
            or OpsProcessor._is_conversational_status(t)
            or OpsProcessor._is_capability_question(t)
            or OpsProcessor._is_meta_usage_question(t)
        )

    @staticmethod
    def _is_conversational_status(text: str) -> bool:
        status_patterns = (
            r"\bare you (active|alive|there|online|working|running|available)\b",
            r"\byou (active|alive|there|online|working|running|available)\b",
            r"\bis (anyone|somebody) (there|available)\b",
            r"\bcan you (hear|see) me\b",
            r"\bping\b",
            r"\bstatus check\b",
        )
        return any(re.search(pattern, text) for pattern in status_patterns)

    @staticmethod
    def _is_capability_question(text: str) -> bool:
        capability_patterns = (
            r"\bwhat can you do\b",
            r"\bwhat do you do\b",
            r"\bhow can you help\b",
            r"\bhow do you work\b",
            r"\bwhat are you for\b",
            r"^help[.!?]?$",
            r"\bcommands?\b",
            r"\bwhat should i ask\b",
        )
        return any(re.search(pattern, text) for pattern in capability_patterns)

    @staticmethod
    def _is_meta_usage_question(text: str) -> bool:
        meta_patterns = (
            r"\bwhat can i ask\b",
            r"\bwhat should i ask\b",
            r"\bwhat questions can i ask\b",
            r"\bwhat can i say\b",
            r"\bwhat should i say\b",
            r"\bhow do i ask\b",
            r"\bhow should i ask\b",
            r"\bwhy did you (give|show|send|reply with)\b",
            r"\bwhy are you (giving|showing|sending)\b",
        )
        return any(re.search(pattern, text) for pattern in meta_patterns)

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
