from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from markdownx.models import MarkdownxField


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        with transaction.atomic(using=self.db):
            objects = list(self)
            for obj in objects:
                obj.delete()
        return len(objects), {self.model._meta.label: len(objects)}

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(is_deleted=False)


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class AuditedContent(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_updated",
    )
    ip_address = models.GenericIPAddressField()
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager.from_queryset(SoftDeleteQuerySet)()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        from .audit import request_audit, snapshot
        using = kwargs.get("using") or self._state.db or "default"
        with transaction.atomic(using=using):
            previous = type(self).all_objects.using(using).select_for_update().filter(pk=self.pk).first() if self.pk else None
            result = super().save(*args, **kwargs)
            current = type(self).all_objects.using(using).get(pk=self.pk)
            before = snapshot(previous) if previous else {}
            after = snapshot(current)
            if before != after:
                actor, ip = request_audit.get() or (self.updated_by_id, None)
                ContentRevision.objects.using(using).create(
                    content_type=ContentType.objects.db_manager(using).get_for_model(self),
                    object_id=self.pk, actor_id=actor, ip_address=ip,
                    before=before, after=after,
                )
            return result

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=("is_deleted", "deleted_at", "updated_at"))

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=("is_deleted", "deleted_at", "updated_at"))


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    color_code = models.CharField(
        max_length=7,
        default="#4F46E5",
        validators=[
            RegexValidator(
                regex=r"^#[0-9A-Fa-f]{6}$",
                message="Use a hexadecimal color such as #4F46E5.",
            )
        ],
    )

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    position = models.PositiveSmallIntegerField(default=0)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    is_restricted = models.BooleanField(default=False)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="forum_groups")
    entity_model = models.CharField(max_length=30, blank=True, choices=(
        ("issue", "Issues"), ("series", "Series"), ("creator", "Authors"), ("publisher", "Publishers")))
    content_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.PROTECT)
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        ordering = ("position", "name")
        verbose_name_plural = "categories"
        constraints = [
            models.CheckConstraint(condition=(Q(content_type__isnull=True, object_id__isnull=True) |
                Q(content_type__isnull=False, object_id__isnull=False)), name="forum_category_link_complete"),
            models.UniqueConstraint(fields=("parent", "content_type", "object_id"), name="forum_category_entity_unique"),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("forum:group", kwargs={"slug": self.slug})

    @property
    def gcd_url(self):
        record = self.content_object
        url = record.get_absolute_url() if record and hasattr(record, "get_absolute_url") else ""
        return url if url.startswith("/") and not url.startswith("//") else ""

    @property
    def ancestors(self):
        result, node, seen = [], self.parent, {self.pk} if self.pk else set()
        while node:
            if node.pk in seen:
                raise ValidationError("A group cannot contain itself.")
            seen.add(node.pk)
            result.insert(0, node)
            node = node.parent
        return result

    def clean(self):
        super().clean()
        depth = len(self.ancestors) + 1
        if depth > 3:
            raise ValidationError({"parent": "Groups support a maximum of three levels."})
        # Reparenting an existing subtree must respect the same limit.
        frontier, seen, height = [self.pk] if self.pk else [], set(), depth
        while frontier:
            if seen.intersection(frontier):
                raise ValidationError("Group hierarchy contains a cycle.")
            seen.update(frontier)
            frontier = list(Category.objects.filter(parent_id__in=frontier).values_list("pk", flat=True))
            height += 1
            if frontier and height > 3:
                raise ValidationError({"parent": "This move would exceed three levels."})
        if self.entity_model and depth != 2:
            raise ValidationError({"entity_model": "Entity sections belong at level two."})
        if bool(self.content_type_id) != bool(self.object_id):
            raise ValidationError("Select both GCD entity type and ID.")
        if self.content_type_id:
            if depth != 3 or self.content_type.app_label != "gcd":
                raise ValidationError("GCD records belong at level three.")
            if self.content_type.model != self.parent.entity_model:
                raise ValidationError("The GCD record type must match its parent section.")
            model = self.content_type.model_class()
            if model is None or not model._default_manager.filter(pk=self.object_id).exists():
                raise ValidationError({"object_id": "GCD record not found."})
        elif self.parent_id and self.parent.entity_model:
            raise ValidationError("This section requires a GCD record ID.")
        if self.pk and self.children.exclude(content_type=None).exists():
            if self.children.exclude(content_type__model=self.entity_model).exists():
                raise ValidationError("The section type cannot conflict with its existing records.")

    def save(self, *args, **kwargs):
        using = kwargs.get("using") or self._state.db or "default"
        with transaction.atomic(using=using):
            # Serialize hierarchy edits; re-read parent chains after taking locks.
            list(Category.objects.using(using).select_for_update().order_by("pk").values_list("pk", flat=True))
            if self.parent_id:
                self.parent = Category.objects.using(using).get(pk=self.parent_id)
            self.full_clean()
            return super().save(*args, **kwargs)


class Discussion(AuditedContent):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"
        ARCHIVED = "archived", "Archived"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="forum_discussions",
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="discussions"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="discussions")
    views_count = models.PositiveIntegerField(default=0)
    is_pinned = models.BooleanField(default=False, db_index=True)
    is_locked = models.BooleanField(default=False)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.OPEN, db_index=True
    )
    content_type = models.ForeignKey(
        ContentType, null=True, blank=True, on_delete=models.SET_NULL
    )
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        ordering = ("-is_pinned", "-created_at")
        indexes = [models.Index(fields=("content_type", "object_id"))]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(content_type__isnull=True, object_id__isnull=True)
                    | Q(content_type__isnull=False, object_id__isnull=False)
                ),
                name="forum_discussion_gcd_link_complete",
            )
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("forum:discussion-detail", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:200] or "discussion"
            if base in {"new", "groups", "posts", "report"}:
                base += "-discussion"
            slug = base
            counter = 2
            while Discussion.all_objects.filter(slug=slug).exclude(pk=self.pk).exists():
                suffix = f"-{counter}"
                slug = f"{base[:220 - len(suffix)]}{suffix}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Post(AuditedContent):
    discussion = models.ForeignKey(
        Discussion, on_delete=models.CASCADE, related_name="posts"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="forum_posts",
    )
    content = MarkdownxField()
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )

    class Meta:
        ordering = ("created_at",)

    def __str__(self):
        return f"Post #{self.pk} in {self.discussion}"


class PostVote(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="forum_post_votes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("post", "user"), name="forum_unique_post_vote"
            )
        ]


class Report(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        REVIEWED = "reviewed", "Reviewed"
        DISMISSED = "dismissed", "Dismissed"
        ACTIONED = "actioned", "Actioned"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="forum_reports",
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    reason = models.TextField(max_length=1000)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.OPEN, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="forum_reports_reviewed",
    )

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("reporter", "content_type", "object_id"),
                name="forum_unique_report_per_content",
            )
        ]
        indexes = [models.Index(fields=("content_type", "object_id"))]

    def __str__(self):
        return f"Report #{self.pk} ({self.get_status_display()})"


class ContentRevision(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.PositiveBigIntegerField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)

    class Meta:
        ordering = ("-created_at",)
