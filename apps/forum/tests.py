from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import include, path, reverse

from .models import Category, Discussion, Post, PostVote, ContentRevision
from .community import group_directory
from .templatetags.forum_tags import safe_markdown


urlpatterns = [path("forum/", include("apps.forum.urls"))]


class DefaultGroupTests(SimpleTestCase):
    def test_defaults_visible_without_database_records(self):
        sections = group_directory([])
        self.assertEqual([len(section["groups"]) for section in sections], [5, 8, 4])
        self.assertEqual(sections[0]["groups"][0]["name"], "gcd-main")
        self.assertTrue(all(group["category"] is None
                            for section in sections for group in section["groups"]))


class ForumTestCase(TestCase):
    def test_group_directory_uses_internal_links_and_gcd_logo(self):
        self.client.force_login(self.author)
        response = self.client.get(reverse("forum:index"), {"view": "groups"})
        self.assertContains(response, self.category.get_absolute_url())
        self.assertContains(response, "img/gcd_logo.png")
        self.assertContains(response, "gcd-main")
        self.assertContains(response, "gcd-italia")
        self.assertNotContains(response, "googlegroups.com")
        self.assertNotContains(response, "mailto:")
        self.assertNotContains(response, "Request subscription")

    def setUp(self):
        user_model = get_user_model()
        self.author = user_model.objects.create_user("author", password="test-password")
        self.other = user_model.objects.create_user("other", password="test-password")
        self.category = Category.objects.create(name="General", slug="general")
        self.discussion = Discussion.objects.create(
            title="A forum topic",
            category=self.category,
            author=self.author,
            created_by=self.author,
            updated_by=self.author,
            ip_address="127.0.0.1",
        )
        self.post = Post.objects.create(
            discussion=self.discussion,
            author=self.author,
            content="First post",
            created_by=self.author,
            updated_by=self.author,
            ip_address="127.0.0.1",
        )

    def test_slug_and_soft_delete_preserve_record(self):
        self.assertEqual(self.discussion.slug, "a-forum-topic")
        self.discussion.delete()
        self.assertFalse(Discussion.objects.filter(pk=self.discussion.pk).exists())
        self.assertTrue(Discussion.all_objects.get(pk=self.discussion.pk).is_deleted)

    def test_vote_endpoint_toggles_one_vote_per_user(self):
        self.client.force_login(self.other)
        url = reverse("forum:post-vote", args=(self.post.pk,))
        response = self.client.post(url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PostVote.objects.filter(post=self.post, user=self.other).count(), 1)
        self.client.post(url, HTTP_HX_REQUEST="true")
        self.assertFalse(PostVote.objects.filter(post=self.post, user=self.other).exists())

    def test_only_author_or_staff_can_soft_delete_post(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse("forum:post-delete", args=(self.post.pk,)))
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.author)
        response = self.client.post(reverse("forum:post-delete", args=(self.post.pk,)))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Post.all_objects.get(pk=self.post.pk).is_deleted)

    def test_reply_rejects_parent_from_another_discussion(self):
        other_discussion = Discussion.objects.create(
            title="Other topic",
            category=self.category,
            author=self.author,
            created_by=self.author,
            updated_by=self.author,
            ip_address="127.0.0.1",
        )
        foreign_post = Post.objects.create(
            discussion=other_discussion,
            author=self.author,
            content="Foreign post",
            created_by=self.author,
            updated_by=self.author,
            ip_address="127.0.0.1",
        )
        self.client.force_login(self.other)
        response = self.client.post(
            reverse("forum:reply", args=(self.discussion.slug,)),
            {"content": "Reply", "parent": foreign_post.pk},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(Post.objects.filter(discussion=self.discussion).count(), 1)

    def test_gcd_link_fields_must_be_set_together(self):
        self.discussion.content_type = ContentType.objects.get_for_model(Category)
        self.discussion.object_id = None
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.discussion.save()

    def test_deleted_discussion_blocks_post_endpoints(self):
        self.discussion.delete()
        self.client.force_login(self.author)
        for route in ("post-vote", "post-delete", "post-edit"):
            response = self.client.post(reverse(f"forum:{route}", args=(self.post.pk,)))
            self.assertEqual(response.status_code, 404)

    def test_locked_discussion_rejects_reply(self):
        self.discussion.is_locked = True
        self.discussion.save()
        self.client.force_login(self.author)
        response = self.client.post(
            reverse("forum:reply", args=(self.discussion.slug,)),
            {"content": "Blocked reply"},
        )
        self.assertEqual(response.status_code, 403)

    def test_reply_parent_is_hidden(self):
        from .forms import PostForm

        self.assertTrue(PostForm(discussion=self.discussion)["parent"].is_hidden)

    def test_anonymous_cannot_read_any_forum_content(self):
        for url in (reverse("forum:index"), self.discussion.get_absolute_url(),
                    self.category.get_absolute_url(), reverse("forum:post-edit", args=[self.post.pk])):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)
            self.assertContains(response, "Iscriviti", status_code=403)
            self.assertNotContains(response, self.discussion.title, status_code=403)
            self.assertNotContains(response, self.post.content, status_code=403)

    def test_three_levels_and_cycles_validated_on_save(self):
        second = Category.objects.create(name="Second", slug="second", parent=self.category)
        third = Category.objects.create(name="Third", slug="third", parent=second)
        with self.assertRaises(ValidationError):
            Category.objects.create(name="Fourth", slug="fourth", parent=third)
        self.category.parent = third
        with self.assertRaises(ValidationError):
            self.category.save()

    def test_moving_subtree_cannot_exceed_three_levels(self):
        child = Category.objects.create(name="Child", slug="child", parent=self.category)
        Category.objects.create(name="Leaf", slug="leaf", parent=child)
        new_root = Category.objects.create(name="New root", slug="new-root")
        self.category.parent = new_root
        with self.assertRaises(ValidationError):
            self.category.save()

    def test_restricted_parent_applies_to_child_and_all_content_endpoints(self):
        self.category.is_restricted = True
        self.category.save()
        child = Category.objects.create(name="Restricted child", slug="restricted-child", parent=self.category)
        self.client.force_login(self.other)
        for url in (self.discussion.get_absolute_url(), child.get_absolute_url()):
            self.assertEqual(self.client.get(url).status_code, 404)
        for route in ("post-vote", "post-delete", "post-edit"):
            self.assertEqual(self.client.post(reverse(f"forum:{route}", args=[self.post.pk])).status_code, 404)
        response = self.client.get(reverse("forum:index"), {"q": self.discussion.title})
        self.assertNotContains(response, self.discussion.get_absolute_url())
        self.category.members.add(self.other)
        self.assertEqual(self.client.get(child.get_absolute_url()).status_code, 200)
        self.assertEqual(self.client.get(self.discussion.get_absolute_url()).status_code, 200)

    def test_registered_user_creates_topic_and_reply_with_audit(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse("forum:discussion-create"), {
            "title": "A new topic", "category": self.category.pk, "content": "A question",
        }, REMOTE_ADDR="192.0.2.5")
        self.assertEqual(response.status_code, 302)
        topic = Discussion.objects.get(title="A new topic")
        self.assertEqual(topic.created_by, self.other)
        self.assertEqual(topic.ip_address, "192.0.2.5")
        response = self.client.post(reverse("forum:reply", args=[topic.slug]), {"content": "A reply"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(topic.posts.count(), 2)

    def test_edit_and_soft_delete_preserve_revision_and_actor(self):
        self.client.force_login(self.author)
        self.client.post(reverse("forum:post-edit", args=[self.post.pk]),
                         {"content": "Edited text"}, REMOTE_ADDR="192.0.2.8")
        revision = ContentRevision.objects.filter(content_type=ContentType.objects.get_for_model(Post),
                                                  object_id=self.post.pk).first()
        self.assertEqual(revision.before["content"], "First post")
        self.assertEqual(revision.after["content"], "Edited text")
        self.assertEqual(revision.actor, self.author)
        self.assertEqual(revision.ip_address, "192.0.2.8")
        self.client.post(reverse("forum:post-delete", args=[self.post.pk]))
        self.assertTrue(Post.all_objects.get(pk=self.post.pk).is_deleted)

    def test_forged_private_group_is_rejected_by_create_form(self):
        self.category.is_restricted = True
        self.category.save()
        self.client.force_login(self.other)
        response = self.client.post(reverse("forum:discussion-create"), {
            "title": "Forbidden topic", "category": self.category.pk, "content": "No access",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Discussion.objects.filter(title="Forbidden topic").exists())

    def test_gcd_record_group_is_reused_and_topic_inherits_link(self):
        from apps.gcd.models import Publisher
        from apps.stddata.models import Country
        country, _ = Country.objects.get_or_create(code="zz-forum", defaults={"name": "Forum test"})
        publisher = Publisher.objects.create(name="Forum publisher", country=country)
        parent = Category.objects.get(slug="gcd-about-publisher")
        self.client.force_login(self.other)
        url = reverse("forum:group-link", args=[parent.slug])
        for _ in range(2):
            response = self.client.post(url, {"object_id": publisher.pk})
            self.assertEqual(response.status_code, 302)
        groups = Category.objects.filter(parent=parent, object_id=publisher.pk)
        self.assertEqual(groups.count(), 1)
        group = groups.get()
        self.assertEqual(len(group.ancestors), 2)
        self.assertEqual(group.gcd_url, publisher.get_absolute_url())
        response = self.client.post(reverse("forum:discussion-create"), {
            "title": "Publisher question", "category": group.pk, "content": "Question",
        })
        self.assertEqual(response.status_code, 302)
        topic = Discussion.objects.get(title="Publisher question")
        self.assertEqual(topic.content_object, publisher)

    def test_gcd_record_group_rejects_unknown_id(self):
        self.client.force_login(self.other)
        parent = Category.objects.get(slug="gcd-about-publisher")
        before = parent.children.count()
        response = self.client.post(reverse("forum:group-link", args=[parent.slug]), {"object_id": 999999999999})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "GCD record not found")
        self.assertEqual(parent.children.count(), before)

    def test_csrf_required_for_mutations(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.other)
        response = client.post(reverse("forum:reply", args=[self.discussion.slug]), {"content": "No token"})
        self.assertEqual(response.status_code, 403)


class MarkdownSafetyTests(TestCase):
    def test_raw_html_and_unsafe_link_are_sanitized(self):
        rendered = str(
            safe_markdown('<script>alert(1)</script> [bad](javascript:alert(1))')
        )
        self.assertNotIn("<script", rendered)
        self.assertNotIn("javascript:", rendered)
        self.assertIn("&lt;script&gt;", rendered)
