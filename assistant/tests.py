from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import AssistantConversation
from .serializers import AssistantConversationCreateSerializer
from .utils import generate_conversation_title, normalize_mode


class AssistantUtilsTests(TestCase):
    def test_normalize_mode_defaults_to_general(self):
        self.assertEqual(normalize_mode(None), AssistantConversation.MODE_GENERAL)
        self.assertEqual(normalize_mode(""), AssistantConversation.MODE_GENERAL)
        self.assertEqual(normalize_mode("invalid"), AssistantConversation.MODE_GENERAL)

    def test_generate_conversation_title_uses_prefix_and_seed(self):
        title, is_auto = generate_conversation_title(
            mode=AssistantConversation.MODE_GRAMMAR,
            first_message="Explain used to vs be used to",
        )
        self.assertTrue(is_auto)
        self.assertTrue(title.startswith("Grammar: "))


class AssistantSerializerTests(TestCase):
    def test_create_conversation_defaults_to_general_mode(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="assistant-user",
            email="assistant-user@example.com",
            password="testpass123",
        )
        request = SimpleNamespace(user=user)

        serializer = AssistantConversationCreateSerializer(
            data={"level": "B1"},
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        conversation = serializer.save()

        self.assertEqual(conversation.user, user)
        self.assertEqual(conversation.mode, AssistantConversation.MODE_GENERAL)
        self.assertEqual(conversation.title, "New Chat")
        self.assertTrue(conversation.is_title_auto)
