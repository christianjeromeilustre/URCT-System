
from uuid import uuid4

from app.auto_history import ArchiveRequest, archive_message

# Bob's previously tested contact.
CONTACT_ID = "f8d266c6-1113-4efb-8a56-e7ed9d5f1465"
CONVERSATION_ID = 2

event_id = uuid4()

test_event = ArchiveRequest(
    event_id=event_id,
    conversation_id=CONVERSATION_ID,
    contact_id=CONTACT_ID,
    direction="incoming",
    original_text="Good morning! How are you today?",
    translated_text="좋은 아침이에요! 오늘 어떻게 지내세요?",
    source_language="en",
    target_language="ko",
    engine_name="test"
)

print("First save:")
print(archive_message(test_event))

print("\nSecond save with same event ID:")
print(archive_message(test_event))
