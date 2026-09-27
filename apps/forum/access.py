"""One access policy for feeds, forms and direct content endpoints."""
from functools import wraps

from django.shortcuts import render
from django.db.models import Q

from .models import Category, Discussion, Post
from .audit import request_audit
from .utils import get_client_ip


def forum_account_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_active:
            response = render(request, "forum/register_required.html", status=403)
            response["Cache-Control"] = "private, no-store"
            return response
        token = request_audit.set((request.user.pk, get_client_ip(request)))
        try:
            response = view(request, *args, **kwargs)
        finally:
            request_audit.reset(token)
        response["Cache-Control"] = "private, no-store"
        return response
    return wrapped


def accessible_categories(user):
    if user is None or not user.is_authenticated or not user.is_active:
        return Category.objects.none()
    queryset = Category.objects.filter(is_active=True).exclude(parent__is_active=False).exclude(parent__parent__is_active=False)
    if not (user.is_staff or user.is_superuser):
        for prefix in ("", "parent__", "parent__parent__"):
            queryset = queryset.filter(Q(**{prefix + "is_restricted": False}) |
                Q(**{prefix + "members": user}) | Q(**{prefix + "pk__isnull": True}))
    return queryset.distinct()


def accessible_discussions(user):
    return Discussion.objects.filter(category__in=accessible_categories(user))


def accessible_posts(user):
    return Post.objects.filter(discussion__in=accessible_discussions(user))


def category_tree(categories):
    by_id = {category.pk: category for category in categories}
    roots = []
    for category in by_id.values():
        category.tree_children = []
    for category in by_id.values():
        if category.parent_id in by_id:
            by_id[category.parent_id].tree_children.append(category)
        elif not category.parent_id:
            roots.append(category)
    return roots
