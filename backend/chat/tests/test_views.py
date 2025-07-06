# test_views.py
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from chat.models import Conversation, UploadedFile
from authentication.models import CustomUser

from django.test.utils import override_settings
import tempfile
import fitz 
import docx

@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class FileUploadTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="user@example.com", password="testpass", role="uploader", is_active=True
        )
        self.conversation = Conversation.objects.create(user=self.user, title="Test Conversation")
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

    def test_file_upload(self):
        url = reverse('file-upload')
        file_data = SimpleUploadedFile("test.txt", b"Some sample content", content_type="text/plain")

        data = {
            "file": file_data,
            "conversation": str(self.conversation.id)
        }

        response = self.client.post(url, data, format='multipart')
        print(response.status_code)
        print(response.data)

        self.assertEqual(response.status_code, 201)
        self.assertTrue(UploadedFile.objects.exists())
        
    def extract_text_from_file(self, uploaded_file):
        try:
            file_path = uploaded_file.file.path
        except Exception:
        # For test cases or in-memory files
            return [uploaded_file.file.read().decode('utf-8', errors='ignore')]

        chunks = []

        if file_path.endswith(".pdf"):
            doc = fitz.open(file_path)
            for page in doc:
                text = page.get_text()
                if text.strip():
                    chunks.append(text.strip())

        elif file_path.endswith(".docx"):
            doc = docx.Document(file_path)
            text = "\n".join([p.text for p in doc.paragraphs])
            if text.strip():
                chunks.append(text.strip())
        elif file_path.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
                if text.strip():
                    chunks.append(text.strip())


        return chunks

