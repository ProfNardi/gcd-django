def get_client_ip(request):
    """Return the peer IP; trust proxy headers only when explicitly configured."""
    from django.conf import settings

    from ipaddress import ip_address

    candidate = request.META.get("REMOTE_ADDR") or "0.0.0.0"
    if getattr(settings, "FORUM_TRUST_X_FORWARDED_FOR", False):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            candidate = forwarded.split(",", 1)[0].strip()
    try:
        return str(ip_address(candidate))
    except ValueError:
        return "0.0.0.0"


def can_moderate(user, content):
    return user.is_authenticated and (
        user.is_staff or user.is_superuser or content.author_id == user.pk
    )
