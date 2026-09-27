from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from django.db.models import Count, Exists, F, Max, OuterRef, Q
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_safe, require_http_methods
from django.views.generic import CreateView, ListView, UpdateView

from .forms import (
    GCDGroupForm,
    DiscussionEditForm,
    DiscussionForm,
    PostEditForm,
    PostForm,
    ReportForm,
)
from .models import Category, Discussion, Post, PostVote, Report, ContentRevision
from .access import accessible_categories, accessible_discussions, accessible_posts, category_tree
from .utils import can_moderate, get_client_ip


def _is_htmx(request):
    return request.headers.get("HX-Request") == "true"


def _post_tree(discussion):
    posts = list(
        Post.all_objects.filter(discussion=discussion)
        .select_related("author")
        .annotate(vote_count=Count("votes"))
        .order_by("created_at")
    )
    by_id = {post.pk: post for post in posts}
    roots = []
    for post in posts:
        post.tree_children = []
        post.user_has_voted = False
    for post in posts:
        parent = by_id.get(post.parent_id)
        if parent:
            parent.tree_children.append(post)
        else:
            roots.append(post)
    return roots, posts


class DiscussionListView(ListView):
    template_name = "forum/index.html"
    context_object_name = "discussions"
    paginate_by = 25

    def get_queryset(self):
        queryset = (
            accessible_discussions(self.request.user).select_related(
                "author", "category", "content_type"
            )
            .prefetch_related("tags", "content_object")
            .annotate(
                post_count=Count("posts", filter=Q(posts__is_deleted=False)),
                last_activity=Max(
                    "posts__created_at", filter=Q(posts__is_deleted=False)
                ),
            )
        )
        category = self.kwargs.get("slug") or self.request.GET.get("category")
        if category:
            selected = get_object_or_404(accessible_categories(self.request.user), slug=category)
            queryset = queryset.filter(Q(category=selected) | Q(category__parent=selected) | Q(category__parent__parent=selected))
        query = self.request.GET.get("q", "").strip()[:200]
        if query:
            queryset = queryset.annotate(matching_post=Exists(Post.objects.filter(
                discussion_id=OuterRef("pk"), content__icontains=query
            ))).filter(Q(title__icontains=query) | Q(matching_post=True))
        feed = self.request.GET.get("feed", "latest")
        if feed == "unanswered":
            queryset = queryset.filter(post_count__lte=1)
        elif feed == "mine":
            if not self.request.user.is_authenticated:
                return queryset.none()
            queryset = queryset.filter(author=self.request.user)
        ordering = ("-created_at",) if feed == "new" else ("-last_activity", "-created_at")
        return queryset.order_by("-is_pinned", *ordering, "-pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        categories = list(accessible_categories(self.request.user).select_related("parent", "parent__parent", "content_type").annotate(
            topic_count=Count("discussions", filter=Q(discussions__is_deleted=False), distinct=True)
        ))
        context["categories"] = categories
        context["group_roots"] = category_tree(categories)
        context["active_category"] = self.kwargs.get("slug") or self.request.GET.get("category", "")
        context["selected_category"] = next((category for category in categories
            if category.slug == context["active_category"]), None)
        context["search_query"] = self.request.GET.get("q", "").strip()[:200]
        context["active_feed"] = self.request.GET.get("feed", "latest")
        context["directory"] = self.request.GET.get("view") == "groups"
        context["topic_total"] = sum(category.topic_count for category in categories)
        return context


class DiscussionCreateView(LoginRequiredMixin, CreateView):
    form_class = DiscussionForm
    template_name = "forum/form.html"

    def get_initial(self):
        initial = super().get_initial()
        category = accessible_categories(self.request.user).filter(
            slug=self.request.GET.get("category", "")
        ).first()
        if category:
            initial["category"] = category.pk
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(user=self.request.user, ip_address=get_client_ip(self.request))
        return kwargs


@require_safe
def discussion_detail(request, slug):
    discussion = get_object_or_404(
        accessible_discussions(request.user).select_related(
            "author", "category", "content_type"
        ).prefetch_related("tags"),
        slug=slug,
    )
    view_key = f"forum-viewed-{discussion.pk}"
    if not request.session.get(view_key):
        Discussion.objects.filter(pk=discussion.pk).update(
            views_count=F("views_count") + 1
        )
        request.session[view_key] = True
        discussion.refresh_from_db(fields=("views_count",))

    roots, posts = _post_tree(discussion)
    if request.user.is_authenticated:
        voted_ids = set(
            PostVote.objects.filter(user=request.user, post__in=posts).values_list(
                "post_id", flat=True
            )
        )
        for post in posts:
            post.user_has_voted = post.pk in voted_ids

    return render(
        request,
        "forum/discussion_detail.html",
        {
            "discussion": discussion,
            "post_roots": roots,
            "reply_form": PostForm(discussion=discussion),
            "can_reply": not discussion.is_locked and discussion.status != Discussion.Status.ARCHIVED,
        },
    )


@login_required
@require_POST
def reply(request, slug):
    discussion = get_object_or_404(accessible_discussions(request.user), slug=slug)
    if discussion.is_locked or discussion.status == Discussion.Status.ARCHIVED:
        return HttpResponse("This discussion is locked.", status=403)
    form = PostForm(request.POST, discussion=discussion)
    if not form.is_valid():
        response = render(
            request,
            "forum/_reply_form.html",
            {"discussion": discussion, "reply_form": form},
            status=422,
        )
        response["HX-Retarget"] = "#reply-form-container"
        response["HX-Reswap"] = "outerHTML"
        return response

    post = form.save(commit=False)
    post.discussion = discussion
    post.author = request.user
    post.created_by = request.user
    post.updated_by = request.user
    post.ip_address = get_client_ip(request)
    post.save()
    post.vote_count = 0
    post.user_has_voted = False
    post.tree_children = []
    if _is_htmx(request):
        return render(request, "forum/_post.html", {"post": post, "discussion": discussion, "can_reply": True})
    return redirect(discussion.get_absolute_url())


@login_required
@require_POST
def toggle_vote(request, pk):
    post = get_object_or_404(
        accessible_posts(request.user).select_related("discussion"), pk=pk
    )
    with transaction.atomic():
        vote, created = PostVote.objects.get_or_create(post=post, user=request.user)
        if not created:
            vote.delete()
    post.vote_count = PostVote.objects.filter(post=post).count()
    post.user_has_voted = created
    context = {"post": post}
    if _is_htmx(request):
        return render(request, "forum/_vote_button.html", context)
    return redirect(post.discussion.get_absolute_url())


class AuthorOrStaffMixin(LoginRequiredMixin, UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        return can_moderate(self.request.user, self.get_object())


class DiscussionUpdateView(AuthorOrStaffMixin, UpdateView):
    model = Discussion
    form_class = DiscussionEditForm
    slug_field = "slug"
    template_name = "forum/form.html"

    def get_queryset(self):
        return accessible_discussions(self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class PostUpdateView(AuthorOrStaffMixin, UpdateView):
    model = Post
    form_class = PostEditForm
    template_name = "forum/form.html"

    def get_queryset(self):
        return accessible_posts(self.request.user)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        return response

    def get_success_url(self):
        return self.object.discussion.get_absolute_url()


@login_required
@require_POST
def delete_discussion(request, slug):
    discussion = get_object_or_404(accessible_discussions(request.user), slug=slug)
    if not can_moderate(request.user, discussion):
        return HttpResponse(status=403)
    discussion.updated_by = request.user
    discussion.save(update_fields=("updated_by", "updated_at"))
    discussion.delete()
    messages.success(request, "Discussion removed.")
    return redirect("forum:index")


@login_required
@require_POST
def delete_post(request, pk):
    post = get_object_or_404(
        accessible_posts(request.user).select_related("discussion"), pk=pk
    )
    if not can_moderate(request.user, post):
        return HttpResponse(status=403)
    post.updated_by = request.user
    post.save(update_fields=("updated_by", "updated_at"))
    post.delete()
    if _is_htmx(request):
        response = HttpResponse()
        response["HX-Redirect"] = post.discussion.get_absolute_url()
        return response
    return redirect(post.discussion.get_absolute_url())


@login_required
@require_POST
def report_content(request, kind, pk):
    model = {"discussion": Discussion, "post": Post}.get(kind)
    if model is None:
        raise Http404
    queryset = accessible_posts(request.user) if model is Post else accessible_discussions(request.user)
    content = get_object_or_404(queryset, pk=pk)
    form = ReportForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("A reason is required (maximum 1000 characters).")
    content_type = ContentType.objects.get_for_model(content)
    try:
        with transaction.atomic():
            Report.objects.create(
                reporter=request.user,
                content_type=content_type,
                object_id=content.pk,
                reason=form.cleaned_data["reason"],
            )
    except IntegrityError:
        pass
    messages.success(request, "Thank you. Your report was sent to the moderators.")
    return redirect(
        content.get_absolute_url()
        if kind == "discussion"
        else content.discussion.get_absolute_url()
    )

@login_required
@require_http_methods(["GET", "POST"])
def link_gcd_group(request, slug):
    parent = get_object_or_404(accessible_categories(request.user), slug=slug)
    if not parent.entity_model or len(parent.ancestors) != 1:
        raise Http404
    form = GCDGroupForm(request.POST if request.method == "POST" else None, parent=parent)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            # Serialize creation for this section so simultaneous requests reuse the group.
            list(Category.objects.select_for_update().order_by("pk").values_list("pk", flat=True))
            parent = get_object_or_404(accessible_categories(request.user), pk=parent.pk)
            group, created = Category.objects.get_or_create(
                parent=parent, content_type=form.content_type,
                object_id=form.cleaned_data["object_id"],
                defaults={
                    "name": f"{parent.get_entity_model_display()} #{form.record.pk}"[:100],
                    "slug": f"{parent.slug[:70]}-{parent.entity_model}-{form.record.pk}",
                },
            )
            if created:
                ContentRevision.objects.create(
                    content_type=ContentType.objects.get_for_model(group), object_id=group.pk,
                    actor=request.user, ip_address=get_client_ip(request),
                    after={"name": group.name, "parent_id": group.parent_id,
                           "content_type_id": group.content_type_id, "object_id": group.object_id},
                )
        if not accessible_categories(request.user).filter(pk=group.pk).exists():
            raise Http404
        return redirect(group.get_absolute_url())
    return render(request, "forum/link_group.html", {"form": form, "parent": parent})
