from django.contrib import admin
from django.utils import timezone

from .models import Category, Discussion, Post, PostVote, Report, Tag, ContentRevision
from .audit import request_audit
from .utils import get_client_ip


class ContentAdmin(admin.ModelAdmin):
    readonly_fields = (
        "author", "created_by", "updated_by", "ip_address",
        "created_at", "updated_at", "deleted_at", "is_deleted",
    )

    def has_add_permission(self, request):
        return False

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        token = request_audit.set((request.user.pk, get_client_ip(request)))
        try:
            super().save_model(request, obj, form, change)
        finally:
            request_audit.reset(token)

    def delete_model(self, request, obj):
        self.delete_queryset(request, self.model.all_objects.filter(pk=obj.pk))

    def delete_queryset(self, request, queryset):
        token = request_audit.set((request.user.pk, get_client_ip(request)))
        try:
            for obj in queryset:
                obj.updated_by = request.user
                obj.save(update_fields=("updated_by", "updated_at"))
                obj.delete()
        finally:
            request_audit.reset(token)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "position", "is_active", "is_restricted")
    filter_horizontal = ("members",)
    list_filter = ("is_restricted", "parent")
    list_editable = ("position", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "color_code")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Discussion)
class DiscussionAdmin(ContentAdmin):
    list_display = (
        "title",
        "author",
        "category",
        "status",
        "is_pinned",
        "is_locked",
        "is_deleted",
        "created_at",
    )
    list_filter = ("status", "is_pinned", "is_locked", "is_deleted", "category")
    search_fields = ("title", "author__username")
    readonly_fields = ContentAdmin.readonly_fields + ("slug", "content_type", "object_id")
    filter_horizontal = ("tags",)

    def get_queryset(self, request):
        return Discussion.all_objects.select_related("author", "category")


@admin.register(Post)
class PostAdmin(ContentAdmin):
    list_display = ("id", "discussion", "author", "is_deleted", "created_at")
    list_filter = ("is_deleted", "created_at")
    search_fields = ("content", "author__username", "discussion__title")
    readonly_fields = ContentAdmin.readonly_fields + ("discussion", "parent")

    def get_queryset(self, request):
        return Post.all_objects.select_related("author", "discussion")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "reporter", "content_type", "object_id", "status", "created_at")
    list_filter = ("status", "content_type")
    search_fields = ("reason", "reporter__username")
    readonly_fields = (
        "reporter", "content_type", "object_id", "reason", "created_at",
        "reviewed_by", "reviewed_at",
    )

    def has_add_permission(self, request):
        return False

    def save_model(self, request, obj, form, change):
        if "status" in form.changed_data:
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)


admin.site.register(PostVote)


@admin.register(ContentRevision)
class ContentRevisionAdmin(admin.ModelAdmin):
    list_display = ("id", "content_type", "object_id", "actor", "created_at")
    readonly_fields = ("content_type", "object_id", "actor", "ip_address", "created_at", "before", "after")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
