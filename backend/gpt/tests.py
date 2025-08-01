from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from django.urls import reverse
from unittest.mock import patch
from gpt.models import Role, Permission

class GeminiFeatureTests(TestCase):
    def setUp(self):
        # Setup test user, role, permission
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        self.role = Role.objects.create(name='Uploader')
        self.permission = Permission.objects.create(name='file_upload', role=self.role)
        self.user.role = self.role
        self.user.save()

    def test_rag_generate_success(self):
        # Valid query returns 200
        url = reverse('gemini:rag_generate')
        response = self.client.post(url, {'query': 'Test query'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('answer', response.data)
        self.assertIn('retrieved_documents', response.data)

    def test_rag_generate_missing_query(self):
        # Missing query returns 400
        url = reverse('gemini:rag_generate')
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)

    def test_file_upload_no_file(self):
        # No file returns 400
        url = reverse('gemini:file_upload')
        response = self.client.post(url, {}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)

    @patch('gpt.views.process_file')
    def test_file_upload_success(self, mock_process_file):
        # Valid file upload returns 200
        url = reverse('gemini:file_upload')
        file = {'file': ('test.txt', b'dummy content', 'text/plain')}
        response = self.client.post(url, file, format='multipart')
        self.assertEqual(response.status_code, 200)
        self.assertIn('file_url', response.data)
        mock_process_file.assert_called_once()

    def test_file_upload_with_role_permission_denied(self):
        # User with no role gets 403
        self.user.role = None
        self.user.save()
        url = reverse('gemini:file_upload_with_role_permission')
        file = {'file': ('test.txt', b'dummy content', 'text/plain')}
        response = self.client.post(url, file, format='multipart')
        self.assertEqual(response.status_code, 403)

    @patch('gpt.views.process_file')
    def test_file_upload_with_role_permission_success(self, mock_process_file):
        # Valid upload with role returns 200
        url = reverse('gemini:file_upload_with_role_permission')
        file = {'file': ('test.txt', b'dummy content', 'text/plain')}
        response = self.client.post(url, file, format='multipart')
        self.assertEqual(response.status_code, 200)
        self.assertIn('file_url', response.data)
        mock_process_file.assert_called_once()

    def test_file_access_with_permission(self):
        # Access allowed with role
        url = reverse('gemini:file_access')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.data)

    def test_file_access_without_permission(self):
        # Access denied without role
        self.user.role = None
        self.user.save()
        url = reverse('gemini:file_access')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_file_delete_missing_filename(self):
        # Missing filename returns 400
        url = reverse('gemini:file_delete')
        response = self.client.delete(url, {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)

    @patch('django.core.files.storage.FileSystemStorage.delete')
    def test_file_delete_success(self, mock_delete):
        # Valid delete returns 200
        url = reverse('gemini:file_delete')
        mock_delete.return_value = None
        response = self.client.delete(url, {'filename': 'test.txt'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.data)
        mock_delete.assert_called_once_with('test.txt')

    @patch('django.core.files.storage.FileSystemStorage.delete')
    def test_file_delete_failure(self, mock_delete):
        # Delete error returns 500
        url = reverse('gemini:file_delete')
        mock_delete.side_effect = Exception('delete failed')
        response = self.client.delete(url, {'filename': 'test.txt'}, format='json')
        self.assertEqual(response.status_code, 500)
        self.assertIn('error', response.data)

    def test_conversation_summary_missing_id(self):
        # Missing ID returns 400
        url = reverse('gemini:conversation_summary')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)

    @patch('chat.utils.summarizer.generate_summary')
    def test_conversation_summary_cache_and_generate(self, mock_generate_summary):
        # First call generates and caches summary
        from chat.models import Message, Version
        version = Version.objects.create(conversation_id=1)
        Message.objects.create(version=version, content="Hello", created_at="2025-07-30T10:00:00Z")
        Message.objects.create(version=version, content="World", created_at="2025-07-30T10:01:00Z")
        mock_generate_summary.return_value = "Summary of conversation"
        url = reverse('gemini:conversation_summary') + '?conversation_id=1'

        response1 = self.client.get(url)
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response1.data['summary'], "Summary of conversation")
        mock_generate_summary.assert_called_once()

        # Second call uses cached summary
        mock_generate_summary.reset_mock()
        response2 = self.client.get(url)
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response2.data['summary'], "Summary of conversation")
        mock_generate_summary.assert_not_called()