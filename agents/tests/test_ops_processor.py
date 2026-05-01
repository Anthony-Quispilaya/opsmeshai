import pytest

from backend.app.services.ops_processor import OpsProcessor


@pytest.fixture()
def processor() -> OpsProcessor:
    proc = OpsProcessor()
    proc.llm.api_key = ""
    return proc


def test_status_question_is_chat_not_dashboard_query(processor: OpsProcessor) -> None:
    parsed = processor._parse_intent("hey are you active?", history=None)

    assert parsed["intent"] == "UNKNOWN"


def test_status_question_skips_ops_processor(processor: OpsProcessor) -> None:
    parsed = processor._keyword_classify("hey are you active?")

    assert parsed["intent"] == "UNKNOWN"


def test_capability_question_skips_ops_processor(processor: OpsProcessor) -> None:
    parsed = processor._parse_intent("what can you do?", history=None)

    assert parsed["intent"] == "UNKNOWN"


def test_what_do_you_do_skips_ops_processor(processor: OpsProcessor) -> None:
    parsed = processor._parse_intent("I said what do you do?", history=None)

    assert parsed["intent"] == "UNKNOWN"


def test_meta_question_about_transactions_stays_chat(processor: OpsProcessor) -> None:
    parsed = processor._keyword_classify("Okay what can I ask about transactions?")

    assert parsed["intent"] == "UNKNOWN"


def test_meta_question_about_bad_reply_stays_chat(processor: OpsProcessor) -> None:
    parsed = processor._keyword_classify("I said what can I ask about why did you give me data?")

    assert parsed["intent"] == "UNKNOWN"


def test_support_creation_routes_to_support_ticket(processor: OpsProcessor) -> None:
    parsed = processor._keyword_classify("customer reports a login issue and needs help")

    assert parsed["intent"] == "ADD_SUPPORT_TICKET"


def test_compliance_creation_routes_to_compliance_record(processor: OpsProcessor) -> None:
    parsed = processor._keyword_classify("add compliance note for missing receipt on reimbursement")

    assert parsed["intent"] == "ADD_COMPLIANCE_RECORD"


def test_domain_question_routes_to_query_data(processor: OpsProcessor) -> None:
    parsed = processor._keyword_classify("what pending compliance records do we have?")

    assert parsed["intent"] == "QUERY_DATA"
