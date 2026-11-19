from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from .models import Profile


def image_upload(name="avatar.png", extra_bytes=0):
    data = BytesIO()
    Image.new("RGB", (8, 8), "blue").save(data, format="PNG")
    return SimpleUploadedFile(name, data.getvalue() + b"x" * extra_bytes, content_type="image/png")


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AuthFormsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.media = TemporaryDirectory()
        cls.media_settings = override_settings(MEDIA_ROOT=cls.media.name)
        cls.media_settings.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.media_settings.disable()
        cls.media.cleanup()

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="existing", email="old@example.com", password="Strong-Pass-9327")

    def signup_data(self, **updates):
        data = {"username": "newperson", "email": "new@example.com", "first_name": "Новое имя",
                "password1": "Str0ng-Unique-Cobalt-824", "password2": "Str0ng-Unique-Cobalt-824"}
        data.update(updates)
        return data

    def test_signup_creates_user_profile_and_session(self):
        response = self.client.post("/signup/", self.signup_data())
        self.assertRedirects(response, "/")
        user = get_user_model().objects.get(username="newperson")
        self.assertTrue(user.check_password("Str0ng-Unique-Cobalt-824"))
        self.assertTrue(Profile.objects.filter(user=user).exists())
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_password_validators_and_preserved_fields(self):
        response = self.client.post("/signup/", self.signup_data(password1="123", password2="123"))
        self.assertTrue(response.context["form"].errors.get("password2"))
        self.assertContains(response, 'value="newperson"')
        self.assertFalse(get_user_model().objects.filter(username="newperson").exists())

    def test_duplicate_username(self):
        response = self.client.post("/signup/", self.signup_data(username="existing"))
        self.assertIn("username", response.context["form"].errors)

    def test_login_preserves_next_and_username_on_error(self):
        response = self.client.post("/login/?next=/hot/", {"username": "existing", "password": "wrong", "next": "/hot/"})
        self.assertTrue(response.context["form"].non_field_errors())
        self.assertContains(response, 'value="existing"')
        self.assertContains(response, 'name="next" value="/hot/"')
        self.assertRedirects(self.client.post("/login/", {"username": "existing", "password": "Strong-Pass-9327", "next": "/hot/"}), "/hot/")

    def test_external_next_is_rejected(self):
        for url in ["https://evil.example/", "//evil.example/", "javascript:alert(1)"]:
            self.client.logout()
            response = self.client.post("/login/", {"username": "existing", "password": "Strong-Pass-9327", "next": url})
            self.assertRedirects(response, "/")

    def test_logout_stays_on_current_page_and_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/logout/").status_code, 405)
        self.assertRedirects(self.client.post("/logout/", {"next": "/hot/?page=2"}), "/hot/?page=2")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_rejects_external_next(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.post("/logout/", {"next": "https://evil.example/"}), "/")

    def test_profile_and_ask_require_login_even_with_demo_cookie(self):
        self.client.cookies["demo_user"] = "1"
        for path in ["/profile/", "/ask/"]:
            self.assertRedirects(self.client.get(path), f"/login/?next={path}")

    def test_profile_prefill_errors_and_save(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get("/profile/"), 'value="old@example.com"')
        response = self.client.post("/profile/", {"email": "broken", "first_name": "Ник"})
        self.assertIn("email", response.context["form"].errors)
        self.assertContains(response, 'value="Ник"')
        self.assertRedirects(self.client.post("/profile/", {"email": "new@example.com", "first_name": "Новый ник"}), "/profile/")
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Новый ник")
        self.assertEqual(self.user.email, "new@example.com")

    def test_avatar_upload_random_path_display_and_clear(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.post("/profile/", {"email": self.user.email, "first_name": "Ник", "avatar": image_upload()}), "/profile/")
        profile = Profile.objects.get(user=self.user)
        self.assertRegex(profile.avatar.name, r"^avatars/[0-9a-f]{32}\.png$")
        self.assertTrue(Path(profile.avatar.path).exists())
        self.assertContains(self.client.get("/profile/"), profile.avatar.url)
        response = self.client.post("/profile/", {"email": self.user.email, "first_name": "Ник", "avatar-clear": "on"})
        self.assertEqual(response.status_code, 302)
        profile.refresh_from_db()
        self.assertFalse(profile.avatar)

    def test_invalid_avatar_extension_size_and_content(self):
        self.client.force_login(self.user)
        for upload in [image_upload("avatar.exe"), image_upload(extra_bytes=2*1024*1024), SimpleUploadedFile("fake.png", b"not an image")]:
            response = self.client.post("/profile/", {"email": self.user.email, "first_name": "Ник", "avatar": upload})
            self.assertIn("avatar", response.context["form"].errors)

    def test_signup_supports_avatar(self):
        data = self.signup_data(avatar=image_upload())
        self.assertEqual(self.client.post("/signup/", data).status_code, 302)
        self.assertTrue(Profile.objects.get(user__username="newperson").avatar)

    def test_csrf_is_required_for_login_and_signup(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post("/login/", {"username": "existing", "password": "Strong-Pass-9327"}).status_code, 403)
        self.assertEqual(client.post("/signup/", self.signup_data()).status_code, 403)
