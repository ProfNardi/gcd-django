from django.urls import path

from . import views
from .access import forum_account_required

app_name = "forum"

urlpatterns = [
    path("", views.DiscussionListView.as_view(), name="index"),
    path("new/", views.DiscussionCreateView.as_view(), name="discussion-create"),
    path("groups/<slug:slug>/", views.DiscussionListView.as_view(), name="group"),
    path("groups/<slug:slug>/link/", views.link_gcd_group, name="group-link"),
    path("posts/<int:pk>/vote/", views.toggle_vote, name="post-vote"),
    path("posts/<int:pk>/edit/", views.PostUpdateView.as_view(), name="post-edit"),
    path("posts/<int:pk>/delete/", views.delete_post, name="post-delete"),
    path("report/<str:kind>/<int:pk>/", views.report_content, name="report"),
    path("<slug:slug>/", views.discussion_detail, name="discussion-detail"),
    path("<slug:slug>/reply/", views.reply, name="reply"),
    path(
        "<slug:slug>/edit/",
        views.DiscussionUpdateView.as_view(),
        name="discussion-edit",
    ),
    path("<slug:slug>/delete/", views.delete_discussion, name="discussion-delete"),
]

# Apply the gate to every endpoint, including HTMX and direct content URLs.
for pattern in urlpatterns:
    pattern.callback = forum_account_required(pattern.callback)
